#!/usr/bin/env python3
"""
Absenteeism Data Import Job

This script fetches absenteeism data from an external API and imports it into the database.
It's designed to run independently of the main application.

Usage:
    python ImportarAbsenteismo.py [--months MONTHS] [--empresa CODIGO]

Options:
    --months MONTHS   Number of months to look back (default: 6)
    --empresa CODE    Import absenteeism for a specific company code

Environment variables:
    SOC_API_URL - Base URL for the SOC API (default: https://ws1.soc.com.br/WebSoc)
    SOC_EMPRESA - Enterprise code for API calls
    SOC_CODIGO - Code for API authentication
    SOC_CHAVE - API key for authentication
    DATABASE_URL or EXTERNAL_URL_DB - PostgreSQL connection string
"""

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

# Parse command line arguments
parser = argparse.ArgumentParser(description="Import absenteeism data from SOC API")
parser.add_argument("--months", type=int, default=6, help="Number of months to look back (default: 6)")
parser.add_argument("--empresa", type=str, help="Import absenteeism for specific company code")
args = parser.parse_args()

# Get the script's directory path
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(SCRIPT_DIR).resolve().parent
LOG_DIR = BASE_DIR / "log"

# Ensure logs directory exists
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "absenteeism_import.log"

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
SOC_EMPRESA = os.getenv('SOC_EMPRESA', '423')
SOC_CODIGO = os.getenv('SOC_CODIGO', '183868')
SOC_CHAVE = os.getenv('SOC_CHAVE', '6dff7b9a8a635edaddf5')

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
    """Simple rate limiter to avoid overwhelming the API"""
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

def generate_date_intervals(months_back=6):
    """
    Generate a list of date intervals (30-day periods) going back a specified number of months
    
    Args:
        months_back (int): Number of months to look back
        
    Returns:
        list: List of tuples (start_date, end_date) in 'dd/mm/yyyy' format
    """
    intervals = []
    today = date.today()
    
    # Generate intervals in 30-day chunks, going back from today
    end_date = today
    for _ in range(months_back * 30 // 30):  # Convert months to 30-day chunks
        start_date = end_date - timedelta(days=29)  # 30 days including end date
        intervals.append((
            start_date.strftime('%d/%m/%Y'),
            end_date.strftime('%d/%m/%Y')
        ))
        end_date = start_date - timedelta(days=1)
    
    return intervals

def get_companies_from_db(company_code=None):
    """
    Get companies from the database, either a specific one by code or all active ones.
    
    Args:
        company_code (str, optional): Code of the specific company to fetch.
        
    Returns:
        list: List of company records with id and code.
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        if company_code:
            cursor.execute(
                'SELECT id, "CODIGO" FROM dashboard_empresa WHERE "CODIGO" = %s', 
                (company_code,)
            )
            company = cursor.fetchone()
            if not company:
                raise ValueError(f"Company not found: {company_code}")
            companies = [company]
        else:
            cursor.execute('SELECT id, "CODIGO" FROM dashboard_empresa WHERE "ATIVO" = true')
            companies = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return companies
    
    except Exception as e:
        logger.error(f"Error fetching companies from database: {str(e)}")
        raise

def get_next_generic_employee_counter():
    """
    Get the next available counter for 'nomegenerico' employees
    
    Returns:
        int: Next available counter for generic employee names
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Query to find the highest existing counter
        cursor.execute("""
            SELECT "NOME" 
            FROM funcionarios_funcionario 
            WHERE "NOME" LIKE 'nomegenerico%'
            ORDER BY "NOME" DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not result:
            return 1
        
        try:
            # Extract the numeric part after 'nomegenerico'
            counter_str = result['NOME'].replace('nomegenerico', '')
            return int(counter_str) + 1 if counter_str.isdigit() else 1
        except (ValueError, AttributeError, KeyError):
            return 1
    
    except Exception as e:
        logger.error(f"Error getting next generic employee counter: {str(e)}")
        return 1  # Default to 1 if there's an error

def create_generic_employee(company_id, company_code, name):
    """
    Create a generic employee record for a company
    
    Args:
        company_id (int): Database ID of the company
        company_code (str): Company code
        name (str): Name to use for the generic employee
        
    Returns:
        dict: Newly created employee record or None if failed
    """
    today = date.today()
    default_birth_date = date(1980, 1, 1)  # Default birth date
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Get company name
        cursor.execute('SELECT "RAZAOSOCIAL" FROM dashboard_empresa WHERE id = %s', (company_id,))
        company = cursor.fetchone()
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return None
        
        company_name = company['RAZAOSOCIAL']
        
        # Generate a unique employee code
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM funcionarios_funcionario 
            WHERE "CODIGOEMPRESA" = %s
        """, (company_code,))
        
        count_result = cursor.fetchone()
        employee_code = f"GEN{count_result['count'] + 1:06d}" if count_result else "GEN000001"
        
        # Check if employee code already exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM funcionarios_funcionario 
            WHERE "CODIGOEMPRESA" = %s AND "CODIGO" = %s
        """, (company_code, employee_code))
        
        code_check = cursor.fetchone()
        if code_check and code_check['count'] > 0:
            # Append timestamp to ensure uniqueness
            timestamp = int(time.time())
            employee_code = f"GEN{timestamp}"
        
        # Generate a unique matricula
        matricula = f"semmatricula{int(time.time())}"
        
        # Insert new generic employee
        cursor.execute("""
            INSERT INTO funcionarios_funcionario (
                empresa_id, "CODIGOEMPRESA", "NOMEEMPRESA", "CODIGO", "NOME",
                "CPF", "SEXO", "DATA_NASCIMENTO", "DATA_ADMISSAO", "MATRICULAFUNCIONARIO"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, "NOME", "MATRICULAFUNCIONARIO"
        """, (
            company_id, company_code, company_name, employee_code, name,
            f"000.000.000-{int(time.time()) % 100:02d}", 1, default_birth_date, today, matricula
        ))
        
        new_employee = cursor.fetchone()
        connection.commit()
        
        logger.info(f"Created generic employee '{name}' with matricula '{matricula}' for company {company_code}")
        
        cursor.close()
        connection.close()
        
        return new_employee
    
    except Exception as e:
        logger.error(f"Error creating generic employee: {str(e)}")
        if 'connection' in locals() and connection:
            connection.rollback()
        return None

def get_absenteeism_data(company_code, date_start, date_end, tipo_saida='json'):
    """
    Fetch absenteeism data from the SOC API for a specific company and date range.
    
    Args:
        company_code (str): Company code to fetch data for
        date_start (str): Start date in dd/mm/yyyy format
        date_end (str): End date in dd/mm/yyyy format
        tipo_saida (str): Output format (json, html, txt, csv, xml)
        
    Returns:
        dict or list: API response data
    """
    if not all([SOC_EMPRESA, SOC_CODIGO, SOC_CHAVE]):
        raise ValueError("Missing API configuration")
    
    try:
        api_rate_limiter.wait()
        
        params = {
            'empresa': SOC_EMPRESA,
            'codigo': SOC_CODIGO,
            'chave': SOC_CHAVE,
            'tipoSaida': tipo_saida,
            'empresaTrabalho': company_code,
            'dataInicio': date_start,
            'dataFim': date_end
        }

        param_json = json.dumps(params, separators=(',', ':'))
        quoted_param = quote(param_json)
        
        url = f"{SOC_API_URL}/exportadados?parametro={quoted_param}"
        logger.info(f"Fetching absenteeism data from API for company {company_code} from {date_start} to {date_end}")
        
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"API response: {response.text}")
            raise Exception(f"API request failed: {response.status_code}")
        
        if tipo_saida == 'json':
            data = response.json()
            if isinstance(data, list):
                logger.info(f"API response: list with {len(data)} items for company {company_code}")
            elif isinstance(data, dict):
                logger.info(f"API response: dict with keys {list(data.keys())}")
            return data
        return response.text
    
    except Exception as e:
        logger.error(f"Error fetching absenteeism data for company {company_code}: {str(e)}")
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

def map_absenteeism_to_db_schema(item_data, company_id, company_code):
    """
    Map API absenteeism data to database schema.
    
    Args:
        item_data (dict): Absenteeism data from API
        company_id (int): Database ID of the company
        company_code (str): Company code
        
    Returns:
        dict: Mapped absenteeism record
    """
    try:
        # Extract the fields from the API response
        return {
            'empresa_id': company_id,
            'codigo_empresa': company_code,
            'MATRICULA_FUNC': item_data.get('MATRICULA_FUNC', ''),
            'NOME_FUNCIONARIO': item_data.get('NOME_FUNCIONARIO', ''),
            'UNIDADE': item_data.get('UNIDADE', ''),
            'SETOR': item_data.get('SETOR', ''),
            'DT_NASCIMENTO': parse_date(item_data.get('DT_NASCIMENTO')),
            'SEXO': parse_int(item_data.get('SEXO', 0)),
            'TIPO_ATESTADO': parse_int(item_data.get('TIPO_ATESTADO', 0)),
            'DT_INICIO_ATESTADO': parse_date(item_data.get('DT_INICIO_ATESTADO')),
            'DT_FIM_ATESTADO': parse_date(item_data.get('DT_FIM_ATESTADO')),
            'HORA_INICIO_ATESTADO': item_data.get('HORA_INICIO_ATESTADO', ''),
            'HORA_FIM_ATESTADO': item_data.get('HORA_FIM_ATESTADO', ''),
            'DIAS_AFASTADOS': parse_int(item_data.get('DIAS_AFASTADOS')),
            'HORAS_AFASTADO': item_data.get('HORAS_AFASTADO', ''),
            'CID_PRINCIPAL': item_data.get('CID_PRINCIPAL', ''),
            'DESCRICAO_CID': item_data.get('DESCRICAO_CID', ''),
            'GRUPO_PATOLOGICO': item_data.get('GRUPO_PATOLOGICO', ''),
            'TIPO_LICENCA': item_data.get('TIPO_LICENCA', '')
        }
    except Exception as e:
        logger.error(f"Error mapping absenteeism data: {str(e)}")
        raise

def find_employee_by_matricula(matricula, company_code):
    """
    Find an employee by matricula and company code
    
    Args:
        matricula (str): Employee matricula
        company_code (str): Company code
        
    Returns:
        dict: Employee record or None if not found
    """
    if not matricula or not company_code:
        return None
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, "NOME", "DATA_NASCIMENTO", "SEXO"
            FROM funcionarios_funcionario 
            WHERE "MATRICULAFUNCIONARIO" = %s AND "CODIGOEMPRESA" = %s
        """, (matricula, company_code))
        
        employee = cursor.fetchone()
        cursor.close()
        connection.close()
        
        return employee
    
    except Exception as e:
        logger.error(f"Error finding employee with matricula {matricula}: {str(e)}")
        return None

def process_absenteeism_data(api_data, company_id, company_code):
    """
    Process the absenteeism data from the API and prepare it for database insertion
    
    Args:
        api_data (dict or list): API response data
        company_id (int): Database ID of the company
        company_code (str): Company code
        
    Returns:
        list: List of absenteeism records ready for database insertion
    """
    absenteeism_records = []
    generic_employee_counter = get_next_generic_employee_counter()
    
    try:
        # Handle different API response formats
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
            if not data_list and api_data:
                # Single record as a dict
                data_list = [api_data]
                
        if not data_list:
            logger.info(f"No absenteeism data found for company {company_code}")
            return []

        for i, item in enumerate(data_list):
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item in data: {type(item)}")
                continue
                
            try:
                # Map the API data to our schema
                absenteeism = map_absenteeism_to_db_schema(item, company_id, company_code)
                
                # Skip if missing required fields
                if not absenteeism['DT_INICIO_ATESTADO'] or not absenteeism['DT_FIM_ATESTADO']:
                    logger.warning(f"Skipping record missing required date fields: {item}")
                    continue
                
                # Calculate days absent if not provided
                if not absenteeism['DIAS_AFASTADOS'] and absenteeism['DT_INICIO_ATESTADO'] and absenteeism['DT_FIM_ATESTADO']:
                    delta = absenteeism['DT_FIM_ATESTADO'] - absenteeism['DT_INICIO_ATESTADO']
                    absenteeism['DIAS_AFASTADOS'] = delta.days + 1
                
                # Link to existing employee if matricula is provided
                if absenteeism['MATRICULA_FUNC']:
                    employee = find_employee_by_matricula(absenteeism['MATRICULA_FUNC'], company_code)
                    if employee:
                        absenteeism['funcionario_id'] = employee['id']
                        
                        # Update with employee data if not provided in the API
                        if not absenteeism['NOME_FUNCIONARIO']:
                            absenteeism['NOME_FUNCIONARIO'] = employee['NOME']
                        if not absenteeism['DT_NASCIMENTO'] and employee['DATA_NASCIMENTO']:
                            absenteeism['DT_NASCIMENTO'] = employee['DATA_NASCIMENTO']
                        if not absenteeism['SEXO'] and employee['SEXO']:
                            absenteeism['SEXO'] = employee['SEXO']
                    else:
                        # Missing employee - we'll handle this later
                        logger.warning(f"Employee with matricula {absenteeism['MATRICULA_FUNC']} not found")
                
                # Add to our records list
                absenteeism_records.append(absenteeism)
                
            except Exception as e:
                logger.error(f"Error processing absenteeism record: {str(e)}")
                continue
                
        # Process records with missing employee matricula
        for record in absenteeism_records:
            if not record.get('funcionario_id') and not record.get('MATRICULA_FUNC'):
                # Create a generic employee for records without matricula
                generic_name = f"nomegenerico{generic_employee_counter}"
                new_employee = create_generic_employee(company_id, company_code, generic_name)
                
                if new_employee:
                    record['funcionario_id'] = new_employee['id']
                    record['MATRICULA_FUNC'] = new_employee['MATRICULAFUNCIONARIO']
                    if not record['NOME_FUNCIONARIO']:
                        record['NOME_FUNCIONARIO'] = new_employee['NOME']
                    generic_employee_counter += 1
        
        logger.info(f"Processed {len(absenteeism_records)} absenteeism records for company {company_code}")
        return absenteeism_records
    
    except Exception as e:
        logger.error(f"Error processing absenteeism data for company {company_code}: {str(e)}")
        raise

def save_absenteeism_to_database(records):
    """
    Save absenteeism records to the database
    
    Args:
        records (list): List of absenteeism records
        
    Returns:
        tuple: (inserted, updated, errors) counts
    """
    if not records:
        return (0, 0, 0)
    
    inserted = 0
    updated = 0
    errors = 0
    
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        for record in records:
            try:
                # Check for existing record by date range and employee
                if record.get('funcionario_id'):
                    cursor.execute("""
                        SELECT id FROM absenteismo_absenteismo
                        WHERE funcionario_id = %s 
                          AND "DT_INICIO_ATESTADO" = %s
                          AND "DT_FIM_ATESTADO" = %s
                    """, (
                        record['funcionario_id'],
                        record['DT_INICIO_ATESTADO'],
                        record['DT_FIM_ATESTADO']
                    ))
                elif record.get('MATRICULA_FUNC'):
                    cursor.execute("""
                        SELECT id FROM absenteismo_absenteismo
                        WHERE "MATRICULA_FUNC" = %s 
                          AND codigo_empresa = %s
                          AND "DT_INICIO_ATESTADO" = %s
                          AND "DT_FIM_ATESTADO" = %s
                    """, (
                        record['MATRICULA_FUNC'],
                        record['codigo_empresa'],
                        record['DT_INICIO_ATESTADO'],
                        record['DT_FIM_ATESTADO']
                    ))
                else:
                    # No way to uniquely identify - skip duplicate check
                    existing_id = None
                    
                existing = cursor.fetchone() if 'cursor' in locals() else None
                
                if existing:
                    # Update existing record
                    query_parts = []
                    params = []
                    
                    for key, value in record.items():
                        if key != 'id' and key != 'data_criacao' and key != 'data_atualizacao':
                            query_parts.append(f'"{key}" = %s')
                            params.append(value)
                    
                    params.append(existing['id'])
                    
                    update_query = f"""
                    UPDATE absenteismo_absenteismo SET 
                        {", ".join(query_parts)}
                    WHERE id = %s
                    """
                    
                    cursor.execute(update_query, params)
                    updated += 1
                else:
                    # Insert new record
                    record_keys = [k for k in record.keys() if k != 'id' and k != 'data_criacao' and k != 'data_atualizacao']
                    placeholders = ["%s"] * len(record_keys)
                    
                    insert_query = f"""
                    INSERT INTO absenteismo_absenteismo (
                        {", ".join([f'"{k}"' for k in record_keys])},
                        data_criacao, 
                        data_atualizacao
                    ) VALUES (
                        {", ".join(placeholders)},
                        NOW(),
                        NOW()
                    )
                    """
                    
                    cursor.execute(insert_query, [record[k] for k in record_keys])
                    inserted += 1
                
                connection.commit()
                
            except Exception as e:
                connection.rollback()
                errors += 1
                logger.error(f"Error saving absenteeism record: {str(e)}")
                logger.error(f"Record data: {record}")
                continue
        
        cursor.close()
        connection.close()
        
        return (inserted, updated, errors)
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        if 'connection' in locals() and connection:
            connection.rollback()
        raise

def process_company(company, date_intervals):
    """
    Process absenteeism data for a single company across multiple date intervals
    
    Args:
        company (dict): Company record with id and code
        date_intervals (list): List of (start_date, end_date) tuples
        
    Returns:
        tuple: (company_code, processed, errors) counts
    """
    company_id = company['id']
    company_code = company['CODIGO']
    
    total_processed = 0
    total_errors = 0
    
    logger.info(f"Processing company {company_code} with {len(date_intervals)} date intervals")
    
    for i, (start_date, end_date) in enumerate(date_intervals):
        try:
            logger.info(f"Fetching interval {i+1}/{len(date_intervals)}: {start_date} to {end_date}")
            api_data = get_absenteeism_data(company_code, start_date, end_date)
            
            # Process data and save to database
            records = process_absenteeism_data(api_data, company_id, company_code)
            
            if records:
                inserted, updated, errors = save_absenteeism_to_database(records)
                total_processed += inserted + updated
                total_errors += errors
                
                logger.info(f"Results for interval {start_date} to {end_date}: "
                           f"{inserted} inserted, {updated} updated, {errors} errors")
            else:
                logger.info(f"No records to process for interval {start_date} to {end_date}")
                
        except Exception as e:
            logger.error(f"Error processing interval {start_date} to {end_date} for company {company_code}: {str(e)}")
            total_errors += 1
            continue
    
    return company_code, total_processed, total_errors

def main():
    """Main job execution function"""
    start_time = datetime.now()
    logger.info(f"Absenteeism import job started at {start_time}")
    
    try:
        # Generate date intervals
        date_intervals = generate_date_intervals(months_back=args.months)
        logger.info(f"Using {len(date_intervals)} date intervals covering {args.months} months")
        
        # Get companies to process
        companies = get_companies_from_db(args.empresa) if args.empresa else get_companies_from_db()
        logger.info(f"Processing {len(companies)} companies")
        
        total_processed = 0
        total_errors = 0
        processed_companies = 0
        
        for company in companies:
            if not company:
                continue
                
            company_code, processed, errors = process_company(company, date_intervals)
            
            total_processed += processed
            total_errors += errors
            processed_companies += 1
            
            logger.info(f"Progress: {processed_companies}/{len(companies)} companies processed")
            logger.info(f"Company {company_code} results: {processed} records processed, {errors} errors")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Import completed in {duration:.2f} seconds")
        logger.info(f"Total records: {total_processed} processed, {total_errors} errors")
        
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()