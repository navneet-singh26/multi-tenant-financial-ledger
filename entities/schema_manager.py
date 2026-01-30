
from django.db import connection
from django.core.management.color import no_style
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages PostgreSQL schema operations for multi-tenant entities.
    """
    
    @staticmethod
    def create_schema(schema_name):
        """
        Create a new PostgreSQL schema for an entity.
        
        Args:
            schema_name (str): Name of the schema to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Check if schema already exists
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [schema_name]
                )
                if cursor.fetchone():
                    logger.warning(f"Schema {schema_name} already exists")
                    return False
                
                # Create the schema
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
                logger.info(f"Created schema: {schema_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def drop_schema(schema_name, cascade=True):
        """
        Drop a PostgreSQL schema.
        
        Args:
            schema_name (str): Name of the schema to drop
            cascade (bool): Whether to cascade the drop operation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                cascade_clause = "CASCADE" if cascade else "RESTRICT"
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" {cascade_clause}')
                logger.info(f"Dropped schema: {schema_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error dropping schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def schema_exists(schema_name):
        """
        Check if a schema exists.
        
        Args:
            schema_name (str): Name of the schema to check
            
        Returns:
            bool: True if schema exists, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [schema_name]
                )
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def create_tables_in_schema(schema_name, app_label='ledger'):
        """
        Create tables for a specific app in the given schema.
        
        Args:
            schema_name (str): Name of the schema
            app_label (str): Django app label
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from django.apps import apps
            from django.db import connection
            
            # Get all models for the app
            app_models = apps.get_app_config(app_label).get_models()
            
            with connection.cursor() as cursor:
                # Set search path to the schema
                cursor.execute(f'SET search_path TO "{schema_name}"')
                
                # Create tables for each model
                for model in app_models:
                    # Get SQL for creating the table
                    with connection.schema_editor() as schema_editor:
                        schema_editor.create_model(model)
                
                logger.info(f"Created tables in schema: {schema_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating tables in schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def set_search_path(schema_name):
        """
        Set the PostgreSQL search path to the given schema.
        
        Args:
            schema_name (str): Name of the schema
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema_name}", public')
                
        except Exception as e:
            logger.error(f"Error setting search path to {schema_name}: {str(e)}")
            raise
    
    @staticmethod
    def get_current_schema():
        """
        Get the current PostgreSQL schema.
        
        Returns:
            str: Current schema name
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_schema()")
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting current schema: {str(e)}")
            return None
    
    @staticmethod
    def list_schemas():
        """
        List all schemas in the database.
        
        Returns:
            list: List of schema names
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name
                    """
                )
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing schemas: {str(e)}")
            return []
    
    @staticmethod
    @transaction.atomic
    def clone_schema(source_schema, target_schema):
        """
        Clone a schema including its structure and data.
        
        Args:
            source_schema (str): Source schema name
            target_schema (str): Target schema name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Create target schema
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"')
                
                # Get all tables in source schema
                cursor.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    """,
                    [source_schema]
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                # Clone each table
                for table in tables:
                    cursor.execute(
                        f'CREATE TABLE "{target_schema}"."{table}" '
                        f'(LIKE "{source_schema}"."{table}" INCLUDING ALL)'
                    )
                    
                    # Copy data
                    cursor.execute(
                        f'INSERT INTO "{target_schema}"."{table}" '
                        f'SELECT * FROM "{source_schema}"."{table}"'
                    )
                
                logger.info(f"Cloned schema from {source_schema} to {target_schema}")
                return True
                
        except Exception as e:
            logger.error(f"Error cloning schema: {str(e)}")
            return False


class SchemaContext:
    """
    Context manager for temporarily switching to a different schema.
    """
    
    def __init__(self, schema_name):
        self.schema_name = schema_name
        self.previous_schema = None
    
    def __enter__(self):
        """Enter the context and switch to the specified schema."""
        self.previous_schema = SchemaManager.get_current_schema()
        SchemaManager.set_search_path(self.schema_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore the previous schema."""
        if self.previous_schema:
            SchemaManager.set_search_path(self.previous_schema)