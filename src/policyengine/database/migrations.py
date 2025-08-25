"""Database migration utilities for PolicyEngine.

This module provides functions to handle database schema updates.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


def migrate_add_user_table(engine: Engine) -> None:
    """Add user table and created_by fields to existing tables.
    
    This migration:
    1. Creates the users table
    2. Adds created_by foreign key to all tables that track creation
    
    Args:
        engine: SQLAlchemy engine connected to the database
    """
    
    # Check if migration is needed
    with engine.connect() as conn:
        # Check if users table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ))
        if result.fetchone():
            logger.info("Users table already exists, skipping migration")
            return
    
    logger.info("Starting user table migration...")
    
    with engine.begin() as conn:
        # Create users table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR NOT NULL UNIQUE,
                name VARCHAR,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_admin BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                api_key VARCHAR UNIQUE,
                api_key_created_at DATETIME,
                metadata_json TEXT
            )
        """))
        
        # Add index on email
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        ))
        
        # Add index on api_key
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)"
        ))
        
        # Add created_by columns to existing tables if they don't exist
        tables_to_update = [
            'simulations',
            'datasets', 
            'scenarios',
            'parameters',
            'parameter_changes'
        ]
        
        for table in tables_to_update:
            # Check if table exists
            result = conn.execute(text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            ))
            if not result.fetchone():
                logger.info(f"Table {table} does not exist, skipping")
                continue
                
            # Check if created_by column already exists
            result = conn.execute(text(
                f"PRAGMA table_info({table})"
            ))
            columns = [row[1] for row in result]
            
            if 'created_by' not in columns:
                logger.info(f"Adding created_by column to {table}")
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN created_by VARCHAR REFERENCES users(id)"
                ))
            else:
                logger.info(f"Column created_by already exists in {table}")
    
    logger.info("User table migration completed successfully")


def run_all_migrations(engine: Engine) -> None:
    """Run all database migrations in order.
    
    Args:
        engine: SQLAlchemy engine connected to the database
    """
    migrate_add_user_table(engine)
    # Add future migrations here