#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
import requests
import time
from urllib.parse import quote
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

parser = argparse.ArgumentParser(description="Importar dados de convocação das APIs Connect e SOC")
parser.add_argument("--empresa", type=str, help="Importar convocações para uma empresa específica")
parser.add_argument("--dry-run", action="store_true", help="Executar em modo de teste sem alterar o banco de dados")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(SCRIPT_DIR).resolve().parent
LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "convocacao_import.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

env_path = BASE_DIR / ".env"
if env_path.exists():
    logger.info(f"Carregando ambiente do arquivo {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(f"Arquivo .env não encontrado em {env_path}")
    load_dotenv()

CONNECT_URL = os.getenv('CONNECT_URL', 'https://www.grsconnect.com.br/')
CONNECT_USERNAME = os.getenv('CONNECT_USERNAME', '1')
CONNECT_PASSWORD = os.getenv('CONNECT_PASSWORD', 'ConnectBI@20482022')

SOC_API_URL = os.getenv('SOC_API_URL', 'https://ws1.soc.com.br/WebSoc')
SOC_EMPRESA = os.getenv('SOC_EMPRESA', '423')
SOC_CODIGO = os.getenv('SOC_CODIGO', '151346')
SOC_CHAVE = os.getenv('SOC_CHAVE', 'b5aa04943cd28ff155ed')

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('EXTERNAL_URL_DB')
if not DATABASE_URL:
    logger.warning("DATABASE_URL e EXTERNAL_URL_DB não encontrados nas variáveis de ambiente.")
    try:
        sys.path.append(str(BASE_DIR))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        from django.conf import settings
        if hasattr(settings, 'DATABASES') and 'default' in settings.DATABASES:
            db_config = settings.DATABASES['default']
            if 'ENGINE' in db_config and 'postgresql' in db_config['ENGINE']:
                DATABASE_URL = f"postgresql://{db_config.get('USER', '')}:{db_config.get('PASSWORD', '')}@{db_config.get('HOST', '')}:{db_config.get('PORT', '5432')}/{db_config.get('NAME', '')}"
                logger.info("DATABASE_URL construído a partir das configurações do Django")
    except Exception as e:
        logger.warning(f"Não foi possível importar as configurações do Django: {str(e)}")

if DATABASE_URL:
    masked_url = DATABASE_URL.replace('://', '://***:***@') if '://' in DATABASE_URL else DATABASE_URL
    logger.info(f"Usando URL do banco de dados: {masked_url}")
else:
    logger.error("Nenhuma URL de banco de dados configurada")
    sys.exit(1)

class LimitadorDeTaxa:
    def __init__(self, max_chamadas_por_segundo=3):
        self.intervalo_minimo = 1.0 / max_chamadas_por_segundo
        self.tempo_ultima_chamada = 0
    
    def esperar(self):
        tempo_atual = time.time()
        tempo_decorrido = tempo_atual - self.tempo_ultima_chamada
        
        if tempo_decorrido < self.intervalo_minimo:
            time.sleep(self.intervalo_minimo - tempo_decorrido)
        
        self.tempo_ultima_chamada = time.time()

limitador_api = LimitadorDeTaxa(max_chamadas_por_segundo=3)

def obter_conexao_banco():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurado")
    return psycopg2.connect(DATABASE_URL)

def obter_empresas_do_banco(codigo_empresa=None):
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)
        
        if codigo_empresa:
            cursor.execute(
                'SELECT id, "CODIGO" FROM dashboard_empresa WHERE "CODIGO" = %s', 
                (codigo_empresa,)
            )
            empresa = cursor.fetchone()
            if not empresa:
                raise ValueError(f"Empresa não encontrada: {codigo_empresa}")
            empresas = [empresa]
        else:
            cursor.execute('SELECT id, "CODIGO" FROM dashboard_empresa WHERE "ATIVO" = true')
            empresas = cursor.fetchall()
        
        cursor.close()
        conexao.close()
        
        return empresas
    
    except Exception as e:
        logger.error(f"Erro ao buscar empresas do banco de dados: {str(e)}")
        raise

def obter_token_connect():
    try:
        limitador_api.esperar()
        
        url = f"{CONNECT_URL}get_token"
        params = {
            'username': CONNECT_USERNAME,
            'password': CONNECT_PASSWORD
        }
        
        logger.info("Solicitando token de autenticação da API Connect")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Falha na solicitação de token da API Connect: {response.status_code}")
        
        token_data = response.json()
        if 'token' not in token_data:
            raise Exception("Token não encontrado na resposta da API Connect")
        
        return token_data['token']
    
    except Exception as e:
        logger.error(f"Erro ao obter token Connect: {str(e)}")
        raise

def obter_pedidos_exames(token):
    try:
        limitador_api.esperar()
        
        url = f"{CONNECT_URL}get_ped_proc"
        params = {'token': token}
        
        logger.info("Buscando pedidos de exames da API Connect")
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Falha na solicitação de pedidos de exames da API Connect: {response.status_code}")
        
        try:
            pedidos = response.json()
            if not isinstance(pedidos, list):
                raise Exception("Formato de resposta inesperado, esperava uma lista")
            
            logger.info(f"Recebidos {len(pedidos)} pedidos de exames da API Connect")
            return pedidos
        except json.JSONDecodeError:
            raise Exception("Resposta JSON inválida da API Connect")
    
    except Exception as e:
        logger.error(f"Erro ao obter pedidos de exames da API Connect: {str(e)}")
        raise

def obter_dados_exame_soc(codigo_empresa, codigo_solicitacao):
    if not all([SOC_EMPRESA, SOC_CODIGO, SOC_CHAVE]):
        raise ValueError("Configuração da API SOC ausente")
    
    try:
        limitador_api.esperar()
        
        params = {
            'empresa': SOC_EMPRESA,
            'codigo': SOC_CODIGO,
            'chave': SOC_CHAVE,
            'tipoSaida': 'json',
            'empresaTrabalho': codigo_empresa,
            'codigoSolicitacao': codigo_solicitacao
        }

        param_json = json.dumps(params, separators=(',', ':'))
        quoted_param = quote(param_json)
        
        url = f"{SOC_API_URL}/exportadados?parametro={quoted_param}"
        logger.info(f"Buscando dados de exame da API SOC para empresa {codigo_empresa}, solicitação {codigo_solicitacao}")
        
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"Resposta da API SOC: {response.text}")
            raise Exception(f"Falha na solicitação da API SOC: {response.status_code}")
        
        data = response.json()
        if not data:
            logger.warning(f"Nenhum dado de exame retornado para empresa {codigo_empresa}, solicitação {codigo_solicitacao}")
            return []
        
        if isinstance(data, list):
            logger.info(f"Resposta da API SOC: lista com {len(data)} itens")
            return data
        elif isinstance(data, dict):
            if 'data' in data and isinstance(data['data'], list):
                logger.info(f"Resposta da API SOC: dicionário com lista de dados de {len(data['data'])} itens")
                return data['data']
            logger.info(f"Resposta da API SOC: dicionário com chaves {list(data.keys())}")
            return [data]
        
        logger.warning(f"Formato de resposta inesperado da API SOC: {type(data)}")
        return []
    
    except Exception as e:
        logger.error(f"Erro ao buscar dados de exame da API SOC para empresa {codigo_empresa}: {str(e)}")
        return []

def analisar_data(data_str):
    if not data_str or data_str == "None" or data_str == "null":
        return None
    
    try:
        if '/' in data_str:
            return datetime.strptime(data_str, '%d/%m/%Y').date()
        elif '-' in data_str:
            return datetime.strptime(data_str, '%Y-%m-%d').date()
        return None
    except (ValueError, TypeError):
        return None

def obter_funcionario_por_codigo(id_empresa, codigo_funcionario):
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id FROM funcionarios_funcionario 
            WHERE "CODIGO" = %s AND empresa_id = %s
        """, (codigo_funcionario, id_empresa))
        
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        
        return resultado['id'] if resultado else None
    
    except Exception as e:
        logger.error(f"Erro ao encontrar funcionário pelo CODIGO {codigo_funcionario}: {str(e)}")
        return None

def buscar_funcionario_por_cpf_ou_matricula(id_empresa, dados_exame):
    if not dados_exame.get('CPF_FUNCIONARIO') and not dados_exame.get('MATRICULA'):
        return None
    
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)
        
        if dados_exame.get('CPF_FUNCIONARIO'):
            cursor.execute("""
                SELECT id, "CODIGO" FROM funcionarios_funcionario 
                WHERE "CPF" = %s AND empresa_id = %s
            """, (dados_exame['CPF_FUNCIONARIO'], id_empresa))
            resultado = cursor.fetchone()
            if resultado:
                cursor.close()
                conexao.close()
                return resultado
        
        if dados_exame.get('MATRICULA'):
            cursor.execute("""
                SELECT id, "CODIGO" FROM funcionarios_funcionario 
                WHERE "MATRICULAFUNCIONARIO" = %s AND empresa_id = %s
            """, (dados_exame['MATRICULA'], id_empresa))
            resultado = cursor.fetchone()
            if resultado:
                cursor.close()
                conexao.close()
                return resultado
        
        cursor.close()
        conexao.close()
        return None
    
    except Exception as e:
        logger.error(f"Erro ao buscar funcionário por CPF ou matrícula: {str(e)}")
        return None

def mapear_exame_para_esquema_db(dados_exame, id_empresa, codigo_empresa):
    try:
        codigo_funcionario = dados_exame.get('CODIGO_FUNCIONARIO')
        funcionario_id = None
        
        # Se não tiver código de funcionário, tenta encontrar por CPF ou matrícula
        if not codigo_funcionario:
            funcionario = buscar_funcionario_por_cpf_ou_matricula(id_empresa, dados_exame)
            if funcionario:
                funcionario_id = funcionario['id']
                codigo_funcionario = funcionario['CODIGO']
                logger.info(f"Funcionário encontrado por CPF/matrícula: {codigo_funcionario}")
            else:
                logger.warning(f"Não foi possível encontrar um funcionário válido para o exame, pulando registro")
                return None
        else:
            funcionario_id = obter_funcionario_por_codigo(id_empresa, codigo_funcionario)
        
        if not funcionario_id:
            logger.warning(f"Funcionário com código {codigo_funcionario} não encontrado no banco de dados")
        
        codigo_exame = dados_exame.get('CODIGO_EXAME')
        if not codigo_exame:
            logger.warning(f"Código do exame ausente para funcionário {codigo_funcionario}, pulando registro")
            return None
        
        return {
            'empresa_id': id_empresa,
            'CODIGOEMPRESA': codigo_empresa,
            'funcionario_id': funcionario_id,
            'CODIGOFUNCIONARIO': codigo_funcionario,
            'NOMEABREVIADO': dados_exame.get('NOMEABREVIADO', ''),
            'UNIDADE': dados_exame.get('UNIDADE', ''),
            'CIDADE': dados_exame.get('CIDADE', ''),
            'ESTADO': dados_exame.get('ESTADO', ''),
            'BAIRRO': dados_exame.get('BAIRRO', ''),
            'ENDERECO': dados_exame.get('ENDERECO', ''),
            'CEP': dados_exame.get('CEP', ''),
            'CNPJUNIDADE': dados_exame.get('CNPJUNIDADE', ''),
            'SETOR': dados_exame.get('SETOR', ''),
            'CARGO': dados_exame.get('CARGO', ''),
            'CPFFUNCIONARIO': dados_exame.get('CPF_FUNCIONARIO', ''),
            'MATRICULA': dados_exame.get('MATRICULA', ''),
            'DATAADMISSAO': analisar_data(dados_exame.get('DATA_ADMISSAO')),
            'NOME': dados_exame.get('NOME_FUNCIONARIO', ''),
            'EMAILFUNCIONARIO': dados_exame.get('EMAIL_FUNCIONARIO', ''),
            'TELEFONEFUNCIONARIO': dados_exame.get('TELEFONE_FUNCIONARIO', ''),
            'CODIGOEXAME': codigo_exame,
            'EXAME': dados_exame.get('NOME_EXAME', ''),
            'ULTIMOPEDIDO': analisar_data(dados_exame.get('ULTIMO_PEDIDO')),
            'DATARESULTADO': analisar_data(dados_exame.get('DATA_RESULTADO')),
            'PERIODICIDADE': dados_exame.get('PERIODICIDADE') or 12,
            'REFAZER': analisar_data(dados_exame.get('DATA_REFAZER')),
        }
    except Exception as e:
        logger.error(f"Erro ao mapear dados do exame: {str(e)}")
        logger.error(f"Dados problemáticos: {dados_exame}")
        return None

def salvar_exames_no_banco(exames, dry_run=False):
    if not exames:
        return (0, 0, 0)
    
    inseridos = 0
    atualizados = 0
    erros = 0
    
    if dry_run:
        logger.info(f"SIMULAÇÃO: Processaria {len(exames)} registros de exames")
        for exame in exames:
            logger.info(f"SIMULAÇÃO: Processaria exame {exame.get('CODIGOEXAME')} para funcionário {exame.get('CODIGOFUNCIONARIO')}")
        return (len(exames), 0, 0)
    
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)
        
        for exame in exames:
            try:
                if exame is None:
                    continue
                    
                if not exame.get('CODIGOFUNCIONARIO') or not exame.get('CODIGOEXAME'):
                    logger.warning("Campos obrigatórios ausentes, pulando registro")
                    erros += 1
                    continue
                
                cursor.execute("""
                    SELECT id FROM convocacao_convocacao
                    WHERE "CODIGOFUNCIONARIO" = %s AND "CODIGOEXAME" = %s
                """, (exame['CODIGOFUNCIONARIO'], exame['CODIGOEXAME']))
                
                existente = cursor.fetchone()
                
                if existente:
                    campos_atualizacao = []
                    valores_atualizacao = []
                    
                    for chave, valor in exame.items():
                        if chave not in ('id', 'CODIGOFUNCIONARIO', 'CODIGOEXAME'):
                            campos_atualizacao.append(f'"{chave}" = %s')
                            valores_atualizacao.append(valor)
                    
                    valores_atualizacao.append(existente['id'])
                    
                    consulta_atualizacao = f"""
                    UPDATE convocacao_convocacao
                    SET {', '.join(campos_atualizacao)}
                    WHERE id = %s
                    """
                    
                    cursor.execute(consulta_atualizacao, valores_atualizacao)
                    atualizados += 1
                else:
                    campos = [f'"{k}"' for k in exame.keys() if k != 'id']
                    placeholders = ['%s'] * len(campos)
                    
                    consulta_insercao = f"""
                    INSERT INTO convocacao_convocacao
                    ({', '.join(campos)})
                    VALUES ({', '.join(placeholders)})
                    """
                    
                    valores = [v for k, v in exame.items() if k != 'id']
                    cursor.execute(consulta_insercao, valores)
                    inseridos += 1
                
                conexao.commit()
                
            except Exception as e:
                conexao.rollback()
                erros += 1
                logger.error(f"Erro ao salvar registro de exame: {str(e)}")
                logger.error(f"Registro problemático: {exame}")
                continue
        
        cursor.close()
        conexao.close()
        
        return (inseridos, atualizados, erros)
    
    except Exception as e:
        logger.error(f"Erro de banco de dados: {str(e)}")
        if 'conexao' in locals() and conexao:
            conexao.rollback()
        raise

def processar_exames_empresa(empresa, pedidos_connect, dry_run=False):
    id_empresa = empresa['id']
    codigo_empresa = empresa['CODIGO']
    
    pedidos_empresa = [pedido for pedido in pedidos_connect if str(pedido.get('cod_empresa')) == str(codigo_empresa)]
    
    if not pedidos_empresa:
        logger.info(f"Nenhum pedido encontrado para empresa {codigo_empresa}")
        return codigo_empresa, 0, 0
    
    logger.info(f"Processando {len(pedidos_empresa)} pedidos para empresa {codigo_empresa}")
    
    total_processados = 0
    total_erros = 0
    
    for pedido in pedidos_empresa:
        try:
            codigo_solicitacao = pedido.get('cod_solicitacao')
            
            if not codigo_solicitacao:
                logger.warning(f"Código de solicitação ausente para pedido {pedido.get('id_proc')}")
                continue
            
            dados_exame = obter_dados_exame_soc(codigo_empresa, str(codigo_solicitacao))
            
            if not dados_exame:
                logger.warning(f"Nenhum dado de exame retornado para empresa {codigo_empresa}, solicitação {codigo_solicitacao}")
                continue
            
            exames_mapeados = []
            for item in dados_exame:
                exame_mapeado = mapear_exame_para_esquema_db(item, id_empresa, codigo_empresa)
                if exame_mapeado:
                    exames_mapeados.append(exame_mapeado)
            
            inseridos, atualizados, erros = salvar_exames_no_banco(exames_mapeados, dry_run)
            
            total_processados += inseridos + atualizados
            total_erros += erros
            
            logger.info(f"Solicitação {codigo_solicitacao} processada para empresa {codigo_empresa}: {inseridos} inseridos, {atualizados} atualizados, {erros} erros")
            
        except Exception as e:
            logger.error(f"Erro ao processar pedido para empresa {codigo_empresa}: {str(e)}")
            total_erros += 1
            continue
    
    return codigo_empresa, total_processados, total_erros

def verificar_tabelas_banco():
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'convocacao_convocacao'
            );
        """)
        
        tabela_existe = cursor.fetchone()[0]
        
        if not tabela_existe:
            logger.warning("Tabela convocacao_convocacao não existe - criando")
            
            cursor.execute("""
                CREATE TABLE convocacao_convocacao (
                    id SERIAL PRIMARY KEY,
                    empresa_id INTEGER NOT NULL REFERENCES dashboard_empresa(id),
                    "CODIGOEMPRESA" VARCHAR(20) NOT NULL,
                    funcionario_id INTEGER REFERENCES funcionarios_funcionario(id),
                    "CODIGOFUNCIONARIO" VARCHAR(50) NOT NULL,
                    "NOMEABREVIADO" VARCHAR(100),
                    "UNIDADE" VARCHAR(100),
                    "CIDADE" VARCHAR(100),
                    "ESTADO" VARCHAR(2),
                    "BAIRRO" VARCHAR(100),
                    "ENDERECO" VARCHAR(200),
                    "CEP" VARCHAR(10),
                    "CNPJUNIDADE" VARCHAR(20),
                    "SETOR" VARCHAR(100),
                    "CARGO" VARCHAR(100),
                    "CPFFUNCIONARIO" VARCHAR(20),
                    "MATRICULA" VARCHAR(30),
                    "DATAADMISSAO" DATE,
                    "NOME" VARCHAR(120),
                    "EMAILFUNCIONARIO" VARCHAR(100),
                    "TELEFONEFUNCIONARIO" VARCHAR(20),
                    "CODIGOEXAME" VARCHAR(50) NOT NULL,
                    "EXAME" VARCHAR(100),
                    "ULTIMOPEDIDO" DATE,
                    "DATARESULTADO" DATE,
                    "PERIODICIDADE" INTEGER,
                    "REFAZER" DATE,
                    UNIQUE("CODIGOFUNCIONARIO", "CODIGOEXAME")
                );
                
                CREATE INDEX convocacao_empresa_idx ON convocacao_convocacao(empresa_id);
                CREATE INDEX convocacao_funcionario_idx ON convocacao_convocacao(funcionario_id);
                CREATE INDEX convocacao_cod_funcionario_idx ON convocacao_convocacao("CODIGOFUNCIONARIO");
                CREATE INDEX convocacao_cod_exame_idx ON convocacao_convocacao("CODIGOEXAME");
            """)
            conexao.commit()
            logger.info("Tabela convocacao_convocacao criada com sucesso")
        
        cursor.close()
        conexao.close()
        return True
        
    except Exception as e:
        logger.error(f"Erro de inicialização do banco de dados: {str(e)}")
        if 'conexao' in locals() and conexao:
            conexao.rollback()
        return False

def main():
    hora_inicio = datetime.now()
    logger.info(f"Job de importação de convocações iniciado em {hora_inicio}")
    
    if not verificar_tabelas_banco():
        logger.error("Verificação de tabelas do banco de dados falhou, abortando")
        sys.exit(1)
    
    try:
        token = obter_token_connect()
        
        pedidos_connect = obter_pedidos_exames(token)
        
        empresas = obter_empresas_do_banco(args.empresa) if args.empresa else obter_empresas_do_banco()
        logger.info(f"Processando {len(empresas)} empresas")
        
        total_processados = 0
        total_erros = 0
        empresas_processadas = 0
        
        for empresa in empresas:
            if not empresa:
                continue
                
            codigo_empresa, processados, erros = processar_exames_empresa(empresa, pedidos_connect, args.dry_run)
            
            total_processados += processados
            total_erros += erros
            empresas_processadas += 1
            
            logger.info(f"Progresso: {empresas_processadas}/{len(empresas)} empresas processadas")
            logger.info(f"Empresa {codigo_empresa} resultados: {processados} registros processados, {erros} erros")
        
        hora_fim = datetime.now()
        duracao = (hora_fim - hora_inicio).total_seconds()
        logger.info(f"Importação concluída em {duracao:.2f} segundos")
        logger.info(f"Total de registros: {total_processados} processados, {total_erros} erros")
        
        if args.dry_run:
            logger.info("SIMULAÇÃO: Nenhuma alteração real foi feita no banco de dados")
        
    except Exception as e:
        logger.error(f"Importação falhou: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()