#!/usr/bin/env python3
"""
Remove Pending Employees Job

This script removes employees with status 'Pendente' from the database.
It's designed to run independently of the main application.

Usage:
    python RemoverFuncionariosPendentes.py [--dry-run]

Options:
    --dry-run       Run in test mode without actually deleting records

Environment variables:
    DATABASE_URL or EXTERNAL_URL_DB - PostgreSQL connection string
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(description="Remove employees with 'Pendente' status from database")
parser.add_argument("--dry-run", action="store_true", help="Run in test mode without actually deleting records")
args = parser.parse_args()

# Get the script's directory path
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(SCRIPT_DIR).resolve().parent
LOG_DIR = BASE_DIR / "log"

# Ensure logs directory exists
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "remove_pending_employees.log"

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

def get_database_connection():
    """Get a database connection using the DATABASE_URL"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL)

def get_pending_employees_count():
    """
    Get the count of employees with status 'Pendente'.
    
    Returns:
        int: The number of pending employees.
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM funcionarios_funcionario
            WHERE "SITUACAO" = 'Pendente'
        """)
        
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        cursor.close()
        connection.close()
        
        return count
    
    except Exception as e:
        logger.error(f"Error getting pending employees count: {str(e)}")
        raise

def get_pending_employees_by_company():
    """
    Get the count of pending employees grouped by company.
    
    Returns:
        list: List of dictionaries with company info and employee count.
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                e."RAZAOSOCIAL" as empresa_nome,
                e."CODIGO" as empresa_codigo,
                COUNT(*) AS employees_count
            FROM funcionarios_funcionario f
            JOIN dashboard_empresa e ON f.empresa_id = e.id
            WHERE f."SITUACAO" = 'Pendente'
            GROUP BY e."RAZAOSOCIAL", e."CODIGO"
            ORDER BY employees_count DESC
        """)
        
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting pending employees by company: {str(e)}")
        raise

def remove_pending_employees(dry_run=False):
    """
    Remove employees with status 'Pendente' from the database.
    
    Args:
        dry_run (bool): If True, only simulate the deletion without actually removing records.
        
    Returns:
        int: The number of employees removed or that would be removed in dry run mode.
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        if dry_run:
            # Just count the records
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM funcionarios_funcionario
                WHERE "SITUACAO" = 'Pendente'
            """)
            result = cursor.fetchone()
            count = result['count'] if result else 0
        else:
            # Get the IDs before deletion (for logging purposes)
            cursor.execute("""
                SELECT id, "CODIGO", "NOME", "CODIGOEMPRESA", "NOMEEMPRESA"
                FROM funcionarios_funcionario
                WHERE "SITUACAO" = 'Pendente'
            """)
            
            pending_employees = cursor.fetchall()
            count = len(pending_employees)
            
            # Log the employees that will be removed
            for emp in pending_employees:
                logger.info(f"Removing employee: {emp['NOME']} (ID: {emp['id']}, Code: {emp['CODIGO']}) from company {emp['NOMEEMPRESA']} ({emp['CODIGOEMPRESA']})")
            
            # Delete the records
            cursor.execute("""
                DELETE FROM funcionarios_funcionario
                WHERE "SITUACAO" = 'Pendente'
            """)
            
            # Commit the transaction
            connection.commit()
            logger.info(f"Deletion transaction committed - {count} records removed")
        
        cursor.close()
        connection.close()
        
        return count
    
    except Exception as e:
        logger.error(f"Error removing pending employees: {str(e)}")
        if 'connection' in locals() and connection:
            connection.rollback()
        raise

def main():
    """Main job execution function"""
    start_time = datetime.now()
    
    if args.dry_run:
        logger.info("Starting in DRY RUN mode - no records will be deleted")
    else:
        logger.info("Starting in LIVE mode - records will be PERMANENTLY deleted")
    
    try:
        # Get statistics before removal
        total_pending = get_pending_employees_count()
        logger.info(f"Found {total_pending} employees with 'Pendente' status")
        
        # Get breakdown by company
        company_stats = get_pending_employees_by_company()
        if company_stats:
            logger.info("Breakdown by company:")
            for stat in company_stats:
                logger.info(f"  - {stat['empresa_nome']} ({stat['empresa_codigo']}): {stat['employees_count']} employees")
        
        if total_pending == 0:
            logger.info("No 'Pendente' employees found, nothing to do.")
            return
        
        # Confirm if not in dry run mode
        if not args.dry_run:
            # Remove pending employees
            removed_count = remove_pending_employees(dry_run=False)
            logger.info(f"Successfully removed {removed_count} employees with 'Pendente' status")
        else:
            # Simulate removal in dry run mode
            would_remove_count = remove_pending_employees(dry_run=True)
            logger.info(f"DRY RUN: Would remove {would_remove_count} employees with 'Pendente' status")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Job completed in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()