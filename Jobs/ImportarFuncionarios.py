#!/usr/bin/env python3
"""
Employee Data Import Job

This script fetches employee data from an external API and imports it into the database.
It's designed to run independently of the main application.

Usage:
    python ImportarFuncionarios.py [--all] [--empresa CODIGO]

Options:
    --all           Import all employees, including inactive ones
    --empresa CODE  Import employees for a specific company code

Environment variables:
    SOC_API_URL - Base URL for the SOC API (default: https://ws1.soc.com.br/WebSoc)
    SOC_CODIGO - Code for API authentication
    SOC_CHAVE - API key for authentication
    DATABASE_URL or EXTERNAL_URL_DB - PostgreSQL connection string
"""

import os
import sys
import json
import uuid
import logging
import argparse
import requests
import time
import concurrent.futures
from urllib.parse import quote
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(description="Import employee data from SOC API")
parser.add_argument("--all", action="store_true", help="Import all employees, including inactive ones")
parser.add_argument("--empresa", type=str, help="Import employees for specific company code")
args = parser.parse_args()

# Get the script's directory path
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(SCRIPT_DIR).resolve().parent
LOG_DIR = BASE_DIR / "log"

# Ensure logs directory exists
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "employee_import.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from the .env file
env_path = BASE_DIR / ".env"
if env_path.exists():
    logger.info(f"Loading environment from {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(f".env file not found at {env_path}")
    load_dotenv()  # Try to load from default locations

# API Configuration
SOC_API_URL = os.getenv('SOC_API_URL', 'https://ws1.soc.com.br/WebSoc')
SOC_CODIGO = os.getenv('SOC_CODIGO', '25722')
SOC_CHAVE = os.getenv('SOC_CHAVE', 'b4c740208036d64c467b')

# Database configuration - handle multiple possible env var names
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('EXTERNAL_URL_DB')
if not DATABASE_URL:
    logger.warning("DATABASE_URL and EXTERNAL_URL_DB not found in environment variables.")
    try:
        # Try to import from Django settings as last resort
        sys.path.append(str(BASE_DIR))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        from django.conf import settings
        if hasattr(settings, 'DATABASES') and 'default' in settings.DATABASES:
            db_config = settings.DATABASES['default']
            if 'ENGINE' in db_config and 'postgresql' in db_config['ENGINE']:
                # Construct DATABASE_URL from Django settings
                DATABASE_URL = f"postgresql://{db_config.get('USER', '')}:{db_config.get('PASSWORD', '')}@{db_config.get('HOST', '')}:{db_config.get('PORT', '5432')}/{db_config.get('NAME', '')}"
                logger.info("Constructed DATABASE_URL from Django settings")
    except Exception as e:
        logger.warning(f"Could not import Django settings: {str(e)}")

# Log database connection info (with password masked)
if DATABASE_URL:
    masked_url = DATABASE_URL.replace('://', '://***:***@') if '://' in DATABASE_URL else DATABASE_URL
    logger.info(f"Using database URL: {masked_url}")
else:
    logger.error("No database URL configured")
    sys.exit(1)

class RateLimiter:
    def __init__(self, max_calls_per_second=3):
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call_time = 0
    
    def wait(self):
        current_time = time.time()
        elapsed = current_time - self.last_call_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()

api_rate_limiter = RateLimiter(max_calls_per_second=3)

def get_database_connection():
    """Get a database connection using the DATABASE_URL"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL)

def get_companies_from_db(company_code=None):
    """
    Get companies from the database, either a specific one by code or all active ones.
    
    Args:
        company_code (str, optional): Code of the specific company to fetch.
        
    Returns:
        list: List of company records with id and code.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        if company_code:
            cursor.execute(
                "SELECT id, \"CODIGO\" FROM dashboard_empresa WHERE \"CODIGO\" = %s", 
                (company_code,)
            )
            company = cursor.fetchone()
            if not company:
                raise ValueError(f"Company not found: {company_code}")
            companies = [company]
        else:
            cursor.execute("SELECT id, \"CODIGO\" FROM dashboard_empresa WHERE \"ATIVO\" = true")
            companies = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return companies
    
    except Exception as e:
        logger.error(f"Error fetching companies from database: {str(e)}")
        raise

def get_employee_data(company_code, tipo_saida='json', include_inactive=False):
    """
    Fetch employee data from the SOC API for a specific company.
    
    Args:
        company_code (str): Company code to fetch employees for.
        tipo_saida (str): Output format (json, html, txt, csv, xml).
        include_inactive (bool): Whether to include inactive employees.
        
    Returns:
        dict or list: API response data.
    """
    if not all([SOC_CODIGO, SOC_CHAVE]):
        raise ValueError("Missing API configuration")
    
    try:
        api_rate_limiter.wait()
        
        params = {
            'empresa': str(company_code),
            'codigo': SOC_CODIGO,
            'chave': SOC_CHAVE,
            'tipoSaida': tipo_saida,
            "ativo": "Sim",
            "inativo": "Sim" if include_inactive else "",
            "afastado": "Sim",
            "pendente": "Sim",
            "ferias": "Sim"
        }

        param_json = json.dumps(params, separators=(',', ':'))
        quoted_param = quote(param_json)
        
        url = f"{SOC_API_URL}/exportadados?parametro={quoted_param}"
        logger.info(f"Fetching employee data from API for company {company_code}")
        
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code}")
        
        if tipo_saida == 'json':
            data = response.json()
            if isinstance(data, list):
                logger.info(f"API response: list with {len(data)} items for company {company_code}")
            return data
        return response.text
    
    except Exception as e:
        logger.error(f"Error fetching employee data for company {company_code}: {str(e)}")
        raise

def parse_date(date_str):
    """
    Parse a date string to a Python date object.
    
    Args:
        date_str (str): Date string in various formats.
        
    Returns:
        date: Python date object or None if parsing fails.
    """
    if not date_str or date_str == "None" or date_str == "null":
        return None
    
    try:
        if '/' in date_str:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        elif '-' in date_str:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return None
    except (ValueError, TypeError):
        return None

def parse_int(value):
    """
    Parse a value to an integer.
    
    Args:
        value: Value to parse.
        
    Returns:
        int: Parsed integer or None if parsing fails.
    """
    if value in (None, "", "None", "null"):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def map_employee_to_db_schema(employee_data, company_id, company_code):
    """
    Map API employee data to database schema.
    
    Args:
        employee_data (dict): Employee data from API.
        company_id (str): Database ID of the company.
        company_code (str): Company code.
        
    Returns:
        dict: Mapped employee record.
    """
    try:
        return {
            'empresa_id': company_id,
            'CODIGOEMPRESA': company_code,
            'NOMEEMPRESA': employee_data.get('NOMEEMPRESA', ''),
            'CODIGO': employee_data.get('CODIGO', ''),
            'NOME': employee_data.get('NOME', ''),
            'CODIGOUNIDADE': employee_data.get('CODIGOUNIDADE', ''),
            'NOMEUNIDADE': employee_data.get('NOMEUNIDADE', ''),
            'CODIGOSETOR': employee_data.get('CODIGOSETOR', ''),
            'NOMESETOR': employee_data.get('NOMESETOR', ''),
            'CODIGOCARGO': employee_data.get('CODIGOCARGO', ''),
            'NOMECARGO': employee_data.get('NOMECARGO', ''),
            'CBOCARGO': employee_data.get('CBOCARGO', ''),
            'CCUSTO': employee_data.get('CCUSTO', ''),
            'NOMECENTROCUSTO': employee_data.get('NOMECENTROCUSTO', ''),
            'MATRICULAFUNCIONARIO': employee_data.get('MATRICULAFUNCIONARIO', ''),
            'CPF': employee_data.get('CPF', ''),
            'RG': employee_data.get('RG', ''),
            'UFRG': employee_data.get('UFRG', ''),
            'ORGAOEMISSORRG': employee_data.get('ORGAOEMISSORRG', ''),
            'SITUACAO': employee_data.get('SITUACAO', ''),
            'SEXO': parse_int(employee_data.get('SEXO')),
            'PIS': employee_data.get('PIS', ''),
            'CTPS': employee_data.get('CTPS', ''),
            'SERIECTPS': employee_data.get('SERIECTPS', ''),
            'ESTADOCIVIL': parse_int(employee_data.get('ESTADOCIVIL')),
            'TIPOCONTATACAO': parse_int(employee_data.get('TIPOCONTATACAO')),
            'DATA_NASCIMENTO': parse_date(employee_data.get('DATA_NASCIMENTO')),
            'DATA_ADMISSAO': parse_date(employee_data.get('DATA_ADMISSAO')),
            'DATA_DEMISSAO': parse_date(employee_data.get('DATA_DEMISSAO')),
            'ENDERECO': employee_data.get('ENDERECO', ''),
            'NUMERO_ENDERECO': employee_data.get('NUMERO_ENDERECO', ''),
            'BAIRRO': employee_data.get('BAIRRO', ''),
            'CIDADE': employee_data.get('CIDADE', ''),
            'UF': employee_data.get('UF', ''),
            'CEP': employee_data.get('CEP', ''),
            'TELEFONERESIDENCIAL': employee_data.get('TELEFONERESIDENCIAL', ''),
            'TELEFONECELULAR': employee_data.get('TELEFONECELULAR', ''),
            'EMAIL': employee_data.get('EMAIL', ''),
            'DEFICIENTE': 1 if employee_data.get('DEFICIENTE', 'N').upper() == 'S' else 0,
            'DEFICIENCIA': employee_data.get('DEFICIENCIA', ''),
            'NM_MAE_FUNCIONARIO': employee_data.get('NM_MAE_FUNCIONARIO', ''),
            'DATAULTALTERACAO': parse_date(employee_data.get('DATAULTALTERACAO')),
            'MATRICULARH': employee_data.get('MATRICULARH', ''),
            'COR': parse_int(employee_data.get('COR')),
            'ESCOLARIDADE': parse_int(employee_data.get('ESCOLARIDADE')),
            'NATURALIDADE': employee_data.get('NATURALIDADE', ''),
            'RAMAL': employee_data.get('RAMAL', ''),
            'REGIMEREVEZAMENTO': parse_int(employee_data.get('REGIMEREVEZAMENTO')),
            'REGIMETRABALHO': employee_data.get('REGIMETRABALHO', ''),
            'TELCOMERCIAL': employee_data.get('TELCOMERCIAL', ''),
            'TURNOTRABALHO': parse_int(employee_data.get('TURNOTRABALHO')),
        }
    except Exception as e:
        logger.error(f"Error mapping employee data: {str(e)}")
        raise

def map_api_to_db_schema(api_data, company_id, company_code):
    """
    Map API response data to database schema for all employees.
    
    Args:
        api_data (dict or list): API response data.
        company_id (str): Database ID of the company.
        company_code (str): Company code.
        
    Returns:
        list: List of employee records ready for database insertion.
    """
    employees = []
    
    try:
        data_list = []
        if isinstance(api_data, list):
            data_list = api_data
        elif isinstance(api_data, dict) and 'data' in api_data:
            data_list = api_data.get('data', [])
        elif isinstance(api_data, dict):
            for key, value in api_data.items():
                if isinstance(value, list):
                    data_list = value
                    break
            if not data_list:
                data_list = [api_data]
        
        for item in data_list:
            if not isinstance(item, dict):
                continue
            
            try:
                employee = map_employee_to_db_schema(item, company_id, company_code)
                employees.append(employee)
            except Exception as e:
                logger.error(f"Error processing employee {item.get('NOME', 'Unknown')}: {str(e)}")
        
        logger.info(f"Processed {len(employees)} employees for company {company_code}")
        return employees
    
    except Exception as e:
        logger.error(f"Error mapping API data to DB schema for company {company_code}: {str(e)}")
        raise

def save_employees_to_database(employees, company_code):
    """
    Save employee data to database using efficient batch processing.
    
    Args:
        employees (list): List of employee records.
        company_code (str): Company code.
        
    Returns:
        tuple: (total_inserted, total_updated, total_errors) counts.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    if not employees:
        return (0, 0, 0)
    
    total_processed = 0
    total_errors = 0
    
    # Agrupar em lotes maiores para processamento eficiente
    batch_size = 500  # Aumentado para reduzir o número de operações de banco
    batches = [employees[i:i + batch_size] for i in range(0, len(employees), batch_size)]
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        for batch in batches:
            try:
                # Preparar para upsert em lote usando uma única query
                upsert_query = """
                INSERT INTO funcionarios_funcionario (
                    empresa_id, "CODIGOEMPRESA", "NOMEEMPRESA", "CODIGO", "NOME", 
                    "CODIGOUNIDADE", "NOMEUNIDADE", "CODIGOSETOR", "NOMESETOR", 
                    "CODIGOCARGO", "NOMECARGO", "CBOCARGO", "CCUSTO", "NOMECENTROCUSTO", 
                    "MATRICULAFUNCIONARIO", "CPF", "RG", "UFRG", "ORGAOEMISSORRG", 
                    "SITUACAO", "SEXO", "PIS", "CTPS", "SERIECTPS", "ESTADOCIVIL", 
                    "TIPOCONTATACAO", "DATA_NASCIMENTO", "DATA_ADMISSAO", "DATA_DEMISSAO", 
                    "ENDERECO", "NUMERO_ENDERECO", "BAIRRO", "CIDADE", "UF", "CEP", 
                    "TELEFONERESIDENCIAL", "TELEFONECELULAR", "EMAIL", "DEFICIENTE", 
                    "DEFICIENCIA", "NM_MAE_FUNCIONARIO", "DATAULTALTERACAO", "MATRICULARH", 
                    "COR", "ESCOLARIDADE", "NATURALIDADE", "RAMAL", "REGIMEREVEZAMENTO", 
                    "REGIMETRABALHO", "TELCOMERCIAL", "TURNOTRABALHO"
                ) VALUES %s
                ON CONFLICT ("CPF") 
                WHERE "CPF" != ''
                DO UPDATE SET
                    empresa_id = EXCLUDED.empresa_id,
                    "CODIGOEMPRESA" = EXCLUDED."CODIGOEMPRESA",
                    "NOMEEMPRESA" = EXCLUDED."NOMEEMPRESA",
                    "CODIGO" = EXCLUDED."CODIGO",
                    "NOME" = EXCLUDED."NOME",
                    "CODIGOUNIDADE" = EXCLUDED."CODIGOUNIDADE",
                    "NOMEUNIDADE" = EXCLUDED."NOMEUNIDADE",
                    "CODIGOSETOR" = EXCLUDED."CODIGOSETOR",
                    "NOMESETOR" = EXCLUDED."NOMESETOR",
                    "CODIGOCARGO" = EXCLUDED."CODIGOCARGO",
                    "NOMECARGO" = EXCLUDED."NOMECARGO",
                    "CBOCARGO" = EXCLUDED."CBOCARGO",
                    "CCUSTO" = EXCLUDED."CCUSTO",
                    "NOMECENTROCUSTO" = EXCLUDED."NOMECENTROCUSTO",
                    "MATRICULAFUNCIONARIO" = EXCLUDED."MATRICULAFUNCIONARIO",
                    "RG" = EXCLUDED."RG",
                    "UFRG" = EXCLUDED."UFRG",
                    "ORGAOEMISSORRG" = EXCLUDED."ORGAOEMISSORRG",
                    "SITUACAO" = EXCLUDED."SITUACAO",
                    "SEXO" = EXCLUDED."SEXO",
                    "PIS" = EXCLUDED."PIS",
                    "CTPS" = EXCLUDED."CTPS",
                    "SERIECTPS" = EXCLUDED."SERIECTPS",
                    "ESTADOCIVIL" = EXCLUDED."ESTADOCIVIL",
                    "TIPOCONTATACAO" = EXCLUDED."TIPOCONTATACAO",
                    "DATA_NASCIMENTO" = EXCLUDED."DATA_NASCIMENTO",
                    "DATA_ADMISSAO" = EXCLUDED."DATA_ADMISSAO",
                    "DATA_DEMISSAO" = EXCLUDED."DATA_DEMISSAO",
                    "ENDERECO" = EXCLUDED."ENDERECO",
                    "NUMERO_ENDERECO" = EXCLUDED."NUMERO_ENDERECO",
                    "BAIRRO" = EXCLUDED."BAIRRO",
                    "CIDADE" = EXCLUDED."CIDADE",
                    "UF" = EXCLUDED."UF",
                    "CEP" = EXCLUDED."CEP",
                    "TELEFONERESIDENCIAL" = EXCLUDED."TELEFONERESIDENCIAL",
                    "TELEFONECELULAR" = EXCLUDED."TELEFONECELULAR",
                    "EMAIL" = EXCLUDED."EMAIL",
                    "DEFICIENTE" = EXCLUDED."DEFICIENTE",
                    "DEFICIENCIA" = EXCLUDED."DEFICIENCIA",
                    "NM_MAE_FUNCIONARIO" = EXCLUDED."NM_MAE_FUNCIONARIO",
                    "DATAULTALTERACAO" = EXCLUDED."DATAULTALTERACAO",
                    "MATRICULARH" = EXCLUDED."MATRICULARH",
                    "COR" = EXCLUDED."COR",
                    "ESCOLARIDADE" = EXCLUDED."ESCOLARIDADE",
                    "NATURALIDADE" = EXCLUDED."NATURALIDADE",
                    "RAMAL" = EXCLUDED."RAMAL",
                    "REGIMEREVEZAMENTO" = EXCLUDED."REGIMEREVEZAMENTO",
                    "REGIMETRABALHO" = EXCLUDED."REGIMETRABALHO",
                    "TELCOMERCIAL" = EXCLUDED."TELCOMERCIAL",
                    "TURNOTRABALHO" = EXCLUDED."TURNOTRABALHO";
                """
                
                # Extrair valores na ordem correta
                values = []
                for employee in batch:
                    values.append((
                        employee['empresa_id'], employee['CODIGOEMPRESA'], employee['NOMEEMPRESA'], 
                        employee['CODIGO'], employee['NOME'], employee['CODIGOUNIDADE'], 
                        employee['NOMEUNIDADE'], employee['CODIGOSETOR'], employee['NOMESETOR'], 
                        employee['CODIGOCARGO'], employee['NOMECARGO'], employee['CBOCARGO'], 
                        employee['CCUSTO'], employee['NOMECENTROCUSTO'], employee['MATRICULAFUNCIONARIO'], 
                        employee['CPF'], employee['RG'], employee['UFRG'], employee['ORGAOEMISSORRG'], 
                        employee['SITUACAO'], employee['SEXO'], employee['PIS'], employee['CTPS'], 
                        employee['SERIECTPS'], employee['ESTADOCIVIL'], employee['TIPOCONTATACAO'], 
                        employee['DATA_NASCIMENTO'], employee['DATA_ADMISSAO'], employee['DATA_DEMISSAO'], 
                        employee['ENDERECO'], employee['NUMERO_ENDERECO'], employee['BAIRRO'], 
                        employee['CIDADE'], employee['UF'], employee['CEP'], employee['TELEFONERESIDENCIAL'], 
                        employee['TELEFONECELULAR'], employee['EMAIL'], employee['DEFICIENTE'], 
                        employee['DEFICIENCIA'], employee['NM_MAE_FUNCIONARIO'], employee['DATAULTALTERACAO'], 
                        employee['MATRICULARH'], employee['COR'], employee['ESCOLARIDADE'], 
                        employee['NATURALIDADE'], employee['RAMAL'], employee['REGIMEREVEZAMENTO'], 
                        employee['REGIMETRABALHO'], employee['TELCOMERCIAL'], employee['TURNOTRABALHO']
                    ))
                
                # Executar a operação em lote
                execute_values(cursor, upsert_query, values)
                connection.commit()
                
                total_processed += len(batch)
                logger.info(f"Batch processed successfully: {len(batch)} employees for company {company_code}")
                
            except Exception as e:
                connection.rollback()
                total_errors += len(batch)
                logger.error(f"Error processing batch for company {company_code}: {str(e)}")
        
        cursor.close()
        connection.close()
        
        logger.info(f"Database update completed for company {company_code}: {total_processed} processed, {total_errors} errors")
        return (total_processed, 0, total_errors)  # O segundo número era "updated", mas agora não diferenciamos mais
    
    except Exception as e:
        logger.error(f"Database error for company {company_code}: {str(e)}")
        raise

def process_company(company, include_inactive=False):
    """
    Process a single company, fetching and saving employee data.
    
    Args:
        company (dict): Company record with id and code.
        include_inactive (bool): Whether to include inactive employees.
        
    Returns:
        tuple: (company_code, inserted, updated, errors) counts.
    """
    company_id = company['id']
    company_code = company['CODIGO']
    
    try:
        api_data = get_employee_data(
            company_code=company_code,
            tipo_saida='json',
            include_inactive=include_inactive
        )
        
        employees = map_api_to_db_schema(api_data, company_id, company_code)
        
        if employees:
            processed, updated, errors = save_employees_to_database(employees, company_code)
            return company_code, processed, updated, errors
        else:
            return company_code, 0, 0, 0
    
    except Exception as e:
        logger.error(f"Failed to process company {company_code}: {str(e)}")
        return company_code, 0, 0, 0

def main():
    """Main job execution function"""
    start_time = datetime.now()
    logger.info(f"Employee import job started at {start_time}")
    
    try:
        companies = get_companies_from_db(args.empresa) if args.empresa else get_companies_from_db()
        
        total_processed = 0
        total_updated = 0
        total_errors = 0
        processed_companies = 0
        
        for company in companies:
            if not company:
                continue
                
            company_code, processed, updated, errors = process_company(
                company, include_inactive=args.all
            )
            
            total_processed += processed
            total_updated += updated
            total_errors += errors
            processed_companies += 1
            
            logger.info(f"Progress: {processed_companies}/{len(companies)} companies processed")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Import completed in {duration:.2f} seconds")
        logger.info(f"Total employees: {total_processed} processed, {total_errors} errors")
        
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()