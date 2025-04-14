#!/usr/bin/env python3
"""
Populate NTEP Data Job

Este script lê um dicionário JSON com dados de CNAE e CIDs associados (NTEP)
e faz inserção/atualização (upsert) diretamente no banco usando psycopg2.

Uso:
    python PopulateNTEPData.py

Opções:
    --dry-run (se quiser implementar, similar ao padrão anterior)

Env Vars:
    DATABASE_URL ou EXTERNAL_URL_DB - string de conexão Postgres.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# =============================================
# ============ CONFIGURAÇÕES INICIAIS =========
# =============================================

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "populate_ntep_data.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Carrega .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    logger.info(f"Carregando variáveis de ambiente de {ENV_FILE}")
    load_dotenv(dotenv_path=ENV_FILE)
else:
    logger.warning(f"Arquivo .env não encontrado em {ENV_FILE}, carregando variáveis padrão")
    load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('EXTERNAL_URL_DB')
if not DATABASE_URL:
    logger.error("DATABASE_URL e EXTERNAL_URL_DB não configurados. Encerrando.")
    sys.exit(1)

# Máscara para não expor senhas no log
masked_db_url = DATABASE_URL
if '://' in DATABASE_URL:
    prefix, suffix = DATABASE_URL.split('://', 1)
    masked_db_url = prefix + '://***:***@' + suffix.split('@')[-1]
logger.info(f"Usando database URL: {masked_db_url}")

# =============================================
# ============ DICIONÁRIO JSON DE EXEMPLO =====
# =============================================
json_data = ''

# =============================================
# ============ FUNÇÕES AUXILIARES =============
# =============================================
def get_connection():
    """Retorna uma conexão psycopg2 baseada em DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)

def upsert_cnae(codigo, descricao, cursor):
    """
    Faz upsert na tabela cnae:
      - Inserir se não existir
      - Se existir, atualizar descrição
    Retorna o ID do registro na tabela cnae.
    """
    upsert_query = """
        INSERT INTO cnae (codigo, descricao)
        VALUES (%s, %s)
        ON CONFLICT (codigo) DO UPDATE
        SET descricao = EXCLUDED.descricao
        RETURNING id
    """
    cursor.execute(upsert_query, (codigo, descricao))
    cnae_id = cursor.fetchone()['id']
    return cnae_id

def upsert_ntep(cnae_id, descricao, cids, cursor):
    """
    Faz upsert na tabela ntep:
      - Inserir se não existir (por cnae_id único)
      - Se existir, atualizar campos
    """
    upsert_query = """
        INSERT INTO ntep (cnae_id, descricao, cids)
        VALUES (%s, %s, %s)
        ON CONFLICT (cnae_id)
        DO UPDATE SET 
            descricao = EXCLUDED.descricao,
            cids = EXCLUDED.cids
    """
    cursor.execute(upsert_query, (cnae_id, descricao, cids))

def populate_ntep_data():
    """
    Percorre o dicionário json_data e faz o upsert em cnae e ntep.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            logger.info("Iniciando processo de upsert em CNAE e NTEP...")
            for codigo, valores in json_data.items():
                descricao_cnae = valores.get("descricao", "")
                lista_cids = valores.get("cids", [])

                # Upsert na tabela cnae
                cnae_id = upsert_cnae(codigo, descricao_cnae, cursor)

                # Upsert na tabela ntep
                upsert_ntep(cnae_id, descricao_cnae, lista_cids, cursor)

                logger.info(f"CNAE {codigo} - dados NTEP inseridos/atualizados com sucesso.")
            
            conn.commit()
            logger.info("Transação concluída com sucesso.")
    
    except Exception as e:
        logger.error(f"Erro ao popular dados NTEP: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# =============================================
# ============ FUNÇÃO PRINCIPAL ===============
# =============================================
def main():
    try:
        populate_ntep_data()
    except Exception as e:
        logger.error(f"O job falhou: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
