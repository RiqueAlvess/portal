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
from psycopg2.extras import RealDictCursor, execute_values
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

def carregar_mapeamento_funcionarios(id_empresa):
    """
    Carrega um mapeamento de CODIGO de funcionário para ID no banco de dados
    para agilizar as buscas e evitar consultas repetitivas
    """
    try:
        conexao = obter_conexao_banco()
        cursor = conexao.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, "CODIGO" FROM funcionarios_funcionario 
            WHERE empresa_id = %s
        """, (id_empresa,))
        
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        
        # Criar dicionário para mapeamento rápido
        mapeamento = {r['CODIGO']: r['id'] for r in resultados}
        logger.info(f"Mapeamento carregado com {len(mapeamento)} funcionários")
        
        return mapeamento
    
    except Exception as e:
        logger.error(f"Erro ao carregar mapeamento de funcionários: {str(e)}")
        return {}

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

def mapear_exames_para_esquema_db(dados_exames, id_empresa, codigo_empresa, mapeamento_funcionarios):
    """
    Mapeia todos os dados de exames recebidos para o esquema do banco de dados
    """
    exames_mapeados = []
    exames_com_erro = 0
    
    for dados_exame in dados_exames:
        try:
            codigo_funcionario = dados_exame.get('CODIGOFUNCIONARIO')
            if not codigo_funcionario:
                logger.warning(f"CODIGOFUNCIONARIO ausente no registro, pulando")
                exames_com_erro += 1
                continue
                
            funcionario_id = mapeamento_funcionarios.get(codigo_funcionario)
            
            codigo_exame = dados_exame.get('CODIGOEXAME')
            if not codigo_exame:
                logger.warning(f"CODIGOEXAME ausente para funcionário {codigo_funcionario}, pulando registro")
                exames_com_erro += 1
                continue
            
            exame_mapeado = {
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
                'CPFFUNCIONARIO': dados_exame.get('CPFFUNCIONARIO', ''),
                'MATRICULA': dados_exame.get('MATRICULA', ''),
                'DATAADMISSAO': analisar_data(dados_exame.get('DATAADMISSAO')),
                'NOME': dados_exame.get('NOME', ''),
                'EMAILFUNCIONARIO': dados_exame.get('EMAILFUNCIONARIO', ''),
                'TELEFONEFUNCIONARIO': dados_exame.get('TELEFONEFUNCIONARIO', ''),
                'CODIGOEXAME': codigo_exame,
                'EXAME': dados_exame.get('EXAME', ''),
                'ULTIMOPEDIDO': analisar_data(dados_exame.get('ULTIMOPEDIDO')),
                'DATARESULTADO': analisar_data(dados_exame.get('DATARESULTADO')),
                'PERIODICIDADE': dados_exame.get('PERIODICIDADE') or 12,
                'REFAZER': analisar_data(dados_exame.get('REFAZER')),
            }
            
            exames_mapeados.append(exame_mapeado)
            
        except Exception as e:
            logger.error(f"Erro ao mapear exame: {str(e)}")
            logger.error(f"Dados problemáticos: {dados_exame}")
            exames_com_erro += 1
    
    logger.info(f"Mapeados {len(exames_mapeados)} exames com {exames_com_erro} erros")
    return exames_mapeados

def salvar_exames_em_lote(exames, dry_run=False):
    """
    Salva exames em lote usando o método de UPSERT otimizado
    """
    if not exames:
        return (0, 0, 0)
    
    if dry_run:
        logger.info(f"SIMULAÇÃO: Processaria {len(exames)} registros de exames")
        return (len(exames), 0, 0)
    
    # Tamanho do lote para processamento eficiente
    BATCH_SIZE = 500
    total_inseridos = 0
    total_atualizados = 0
    total_erros = 0
    
    try:
        conexao = obter_conexao_banco()
        
        # Dividir em lotes
        lotes = [exames[i:i + BATCH_SIZE] for i in range(0, len(exames), BATCH_SIZE)]
        logger.info(f"Processando {len(lotes)} lotes de exames (tamanho do lote: {BATCH_SIZE})")
        
        for i, lote in enumerate(lotes):
            try:
                cursor = conexao.cursor()
                
                # Consulta UPSERT para processamento em lote
                consulta_upsert = """
                INSERT INTO convocacao_convocacao (
                    empresa_id, "CODIGOEMPRESA", funcionario_id, "CODIGOFUNCIONARIO",
                    "NOMEABREVIADO", "UNIDADE", "CIDADE", "ESTADO", "BAIRRO", "ENDERECO",
                    "CEP", "CNPJUNIDADE", "SETOR", "CARGO", "CPFFUNCIONARIO", "MATRICULA",
                    "DATAADMISSAO", "NOME", "EMAILFUNCIONARIO", "TELEFONEFUNCIONARIO",
                    "CODIGOEXAME", "EXAME", "ULTIMOPEDIDO", "DATARESULTADO", "PERIODICIDADE", "REFAZER"
                ) VALUES %s
                ON CONFLICT ("CODIGOFUNCIONARIO", "CODIGOEXAME") 
                DO UPDATE SET
                    empresa_id = EXCLUDED.empresa_id,
                    "CODIGOEMPRESA" = EXCLUDED."CODIGOEMPRESA",
                    funcionario_id = EXCLUDED.funcionario_id,
                    "NOMEABREVIADO" = EXCLUDED."NOMEABREVIADO",
                    "UNIDADE" = EXCLUDED."UNIDADE",
                    "CIDADE" = EXCLUDED."CIDADE",
                    "ESTADO" = EXCLUDED."ESTADO",
                    "BAIRRO" = EXCLUDED."BAIRRO",
                    "ENDERECO" = EXCLUDED."ENDERECO",
                    "CEP" = EXCLUDED."CEP",
                    "CNPJUNIDADE" = EXCLUDED."CNPJUNIDADE",
                    "SETOR" = EXCLUDED."SETOR",
                    "CARGO" = EXCLUDED."CARGO",
                    "CPFFUNCIONARIO" = EXCLUDED."CPFFUNCIONARIO",
                    "MATRICULA" = EXCLUDED."MATRICULA",
                    "DATAADMISSAO" = EXCLUDED."DATAADMISSAO",
                    "NOME" = EXCLUDED."NOME",
                    "EMAILFUNCIONARIO" = EXCLUDED."EMAILFUNCIONARIO",
                    "TELEFONEFUNCIONARIO" = EXCLUDED."TELEFONEFUNCIONARIO",
                    "EXAME" = EXCLUDED."EXAME",
                    "ULTIMOPEDIDO" = EXCLUDED."ULTIMOPEDIDO",
                    "DATARESULTADO" = EXCLUDED."DATARESULTADO", 
                    "PERIODICIDADE" = EXCLUDED."PERIODICIDADE",
                    "REFAZER" = EXCLUDED."REFAZER"
                RETURNING 
                    (xmax = 0) AS inserted
                """
                
                # Preparar os valores para inserção em lote
                valores = []
                for exame in lote:
                    valores.append((
                        exame['empresa_id'], exame['CODIGOEMPRESA'], exame['funcionario_id'], exame['CODIGOFUNCIONARIO'],
                        exame['NOMEABREVIADO'], exame['UNIDADE'], exame['CIDADE'], exame['ESTADO'], exame['BAIRRO'], exame['ENDERECO'],
                        exame['CEP'], exame['CNPJUNIDADE'], exame['SETOR'], exame['CARGO'], exame['CPFFUNCIONARIO'], exame['MATRICULA'],
                        exame['DATAADMISSAO'], exame['NOME'], exame['EMAILFUNCIONARIO'], exame['TELEFONEFUNCIONARIO'],
                        exame['CODIGOEXAME'], exame['EXAME'], exame['ULTIMOPEDIDO'], exame['DATARESULTADO'], exame['PERIODICIDADE'], exame['REFAZER']
                    ))
                
                # Executar a operação em lote e obter resultados
                resultados = execute_values(
                    cursor, 
                    consulta_upsert, 
                    valores, 
                    fetch=True
                )
                
                # Contar inserções e atualizações
                inseridos = sum(1 for r in resultados if r[0])
                atualizados = len(resultados) - inseridos
                
                conexao.commit()
                
                total_inseridos += inseridos
                total_atualizados += atualizados
                
                logger.info(f"Lote {i+1}/{len(lotes)}: {inseridos} inseridos, {atualizados} atualizados")
                
            except Exception as e:
                conexao.rollback()
                total_erros += len(lote)
                logger.error(f"Erro ao processar lote {i+1}: {str(e)}")
                continue
                
        conexao.close()
        
        return (total_inseridos, total_atualizados, total_erros)
    
    except Exception as e:
        logger.error(f"Erro de banco de dados: {str(e)}")
        if 'conexao' in locals():
            conexao.close()
        return (0, 0, len(exames))

def processar_exames_empresa(empresa, pedidos_connect, dry_run=False):
    id_empresa = empresa['id']
    codigo_empresa = empresa['CODIGO']
    
    # Carregar pedidos para esta empresa
    pedidos_empresa = [p for p in pedidos_connect if str(p.get('cod_empresa')) == str(codigo_empresa)]
    
    if not pedidos_empresa:
        logger.info(f"Nenhum pedido encontrado para empresa {codigo_empresa}")
        return codigo_empresa, 0, 0, 0
    
    logger.info(f"Processando {len(pedidos_empresa)} pedidos para empresa {codigo_empresa}")
    
    # Pré-carregar mapeamento de funcionários para evitar consultas repetitivas ao BD
    mapeamento_funcionarios = carregar_mapeamento_funcionarios(id_empresa)
    
    # Coletar todos os dados de exames
    todos_exames = []
    solicitacoes_com_erro = 0
    
    for pedido in pedidos_empresa:
        try:
            codigo_solicitacao = pedido.get('cod_solicitacao')
            
            if not codigo_solicitacao:
                logger.warning(f"Código de solicitação ausente para pedido {pedido.get('id_proc')}")
                continue
            
            dados_exame = obter_dados_exame_soc(codigo_empresa, str(codigo_solicitacao))
            
            if dados_exame:
                todos_exames.extend(dados_exame)
            else:
                logger.warning(f"Nenhum dado de exame retornado para solicitação {codigo_solicitacao}")
                solicitacoes_com_erro += 1
            
        except Exception as e:
            logger.error(f"Erro ao processar solicitação {pedido.get('cod_solicitacao')}: {str(e)}")
            solicitacoes_com_erro += 1
    
    if not todos_exames:
        logger.info(f"Nenhum exame encontrado para empresa {codigo_empresa}")
        return codigo_empresa, 0, 0, solicitacoes_com_erro
    
    # Mapear todos os exames para o formato do banco de dados
    exames_mapeados = mapear_exames_para_esquema_db(
        todos_exames, id_empresa, codigo_empresa, mapeamento_funcionarios
    )
    
    # Salvar todos os exames de uma vez
    inseridos, atualizados, erros = salvar_exames_em_lote(exames_mapeados, dry_run)
    
    logger.info(f"Empresa {codigo_empresa}: {inseridos} inseridos, {atualizados} atualizados, {erros} erros, {solicitacoes_com_erro} solicitações com erro")
    return codigo_empresa, inseridos, atualizados, solicitacoes_com_erro + erros

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
        
        total_inseridos = 0
        total_atualizados = 0
        total_erros = 0
        empresas_processadas = 0
        
        for empresa in empresas:
            if not empresa:
                continue
                
            codigo_empresa, inseridos, atualizados, erros = processar_exames_empresa(
                empresa, pedidos_connect, args.dry_run
            )
            
            total_inseridos += inseridos
            total_atualizados += atualizados
            total_erros += erros
            empresas_processadas += 1
            
            logger.info(f"Progresso: {empresas_processadas}/{len(empresas)} empresas processadas")
            logger.info(f"Empresa {codigo_empresa} resultados: {inseridos} inseridos, {atualizados} atualizados, {erros} erros")
        
        hora_fim = datetime.now()
        duracao = (hora_fim - hora_inicio).total_seconds()
        logger.info(f"Importação concluída em {duracao:.2f} segundos")
        logger.info(f"Total de registros: {total_inseridos} inseridos, {total_atualizados} atualizados, {total_erros} erros")
        
        if args.dry_run:
            logger.info("SIMULAÇÃO: Nenhuma alteração real foi feita no banco de dados")
        
    except Exception as e:
        logger.error(f"Importação falhou: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()