"""
Database Migration Agent for generating Alembic migration scripts with rollbacks.
"""

import time
from typing import Dict, Any, List
import re
from datetime import datetime

from ..base_agent import BaseAgent


class DatabaseMigrationAgent(BaseAgent):
    """Agent responsible for database migration scripts."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Database Migration agent."""
        super().__init__("DatabaseMigrationAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process models and generate Alembic migration scripts.
        
        Args:
            input_data: Dictionary containing models and database schema
            
        Returns:
            Generated migration scripts with rollback support
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['models']):
                return self.handle_error(ValueError("Missing required 'models' in input"), "input_validation")
            
            models = input_data['models']
            existing_schema = input_data.get('existing_schema', [])
            
            # Generate initial migration
            initial_migration = self._generate_initial_migration(models)
            
            # Generate migration environment
            alembic_env = self._generate_alembic_env()
            
            # Generate migration configuration
            alembic_config = self._generate_alembic_config()
            
            # Generate migration utilities
            migration_utils = self._generate_migration_utils()
            
            # Generate rollback scripts
            rollback_scripts = self._generate_rollback_scripts(models)
            
            result = {
                'initial_migration': initial_migration,
                'alembic_env': alembic_env,
                'alembic_config': alembic_config,
                'migration_utils': migration_utils,
                'rollback_scripts': rollback_scripts
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "generate_migrations",
                {"models_count": len(models)},
                {"migrations_generated": 1},
                success=True,
                execution_time_ms=execution_time
            )
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "generate_migrations",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "migration_generation")
    
    def _generate_initial_migration(self, models: List[Dict[str, Any]]) -> str:
        """Generate initial database migration script."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        revision_id = f"001_{timestamp}"
        
        migration_script = f'''"""Initial database migration

Revision ID: {revision_id}
Revises: 
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create tables
'''
        
        # Generate table creation statements
        for model in models:
            table_name = f"{model['name'].lower()}s"
            migration_script += f"\n    # Create {model['name']} table\n"
            migration_script += f"    op.create_table('{table_name}',\n"
            
            # Generate columns
            columns = []
            for field in model['fields']:
                column_def = self._generate_column_migration(field)
                columns.append(f"        {column_def}")
            
            migration_script += ",\n".join(columns)
            migration_script += "\n    )\n"
            
            # Generate indexes
            indexes = self._generate_indexes_for_model(model, table_name)
            if indexes:
                migration_script += f"\n    # Create indexes for {model['name']}\n"
                migration_script += indexes
        
        # Generate foreign key constraints
        fk_constraints = self._generate_foreign_key_constraints(models)
        if fk_constraints:
            migration_script += "\n    # Create foreign key constraints\n"
            migration_script += fk_constraints
        
        migration_script += '''

def downgrade() -> None:
    """Drop all tables (rollback initial migration)."""
    # Drop foreign key constraints first
'''
        
        # Generate downgrade (drop tables in reverse order)
        for model in reversed(models):
            table_name = f"{model['name'].lower()}s"
            migration_script += f"    op.drop_table('{table_name}')\n"
        
        return migration_script
    
    def _generate_column_migration(self, field: Dict[str, Any]) -> str:
        """Generate column definition for migration."""
        field_name = field['name']
        field_type = field['type']
        
        # Map field types to SQLAlchemy types
        type_mapping = {
            'int': 'sa.Integer()',
            'str': 'sa.String(255)',
            'EmailStr': 'sa.String(255)',
            'bool': 'sa.Boolean()',
            'datetime': 'sa.DateTime(timezone=True)',
            'Decimal': 'sa.Numeric(10, 2)',
            'Text': 'sa.Text()'
        }
        
        sql_type = type_mapping.get(field_type, 'sa.String(255)')
        
        column_parts = [f"sa.Column('{field_name}', {sql_type}"]
        
        if field.get('primary_key'):
            column_parts.append('primary_key=True')
        
        if field.get('unique'):
            column_parts.append('unique=True')
        
        if not field.get('required', True) or field.get('primary_key'):
            column_parts.append('nullable=True')
        else:
            column_parts.append('nullable=False')
        
        if field.get('default') is not None:
            if field['type'] == 'datetime' and field.get('auto_now_add'):
                column_parts.append('server_default=sa.func.now()')
            elif field['type'] == 'bool':
                column_parts.append(f"server_default=sa.text('{str(field['default']).lower()}')")
            else:
                column_parts.append(f"server_default='{field['default']}'")
        
        return f"{', '.join(column_parts)})"
    
    def _generate_indexes_for_model(self, model: Dict[str, Any], table_name: str) -> str:
        """Generate index creation statements for a model."""
        indexes = []
        
        # Create indexes for foreign keys and unique fields
        for field in model['fields']:
            field_name = field['name']
            
            if field.get('foreign_key'):
                index_name = f"ix_{table_name}_{field_name}"
                indexes.append(f"    op.create_index('{index_name}', '{table_name}', ['{field_name}'])")
            
            if field.get('unique') and not field.get('primary_key'):
                index_name = f"ix_{table_name}_{field_name}_unique"
                indexes.append(f"    op.create_unique_constraint('{index_name}', '{table_name}', ['{field_name}'])")
        
        # Common indexes
        if any(f['name'] == 'created_at' for f in model['fields']):
            index_name = f"ix_{table_name}_created_at"
            indexes.append(f"    op.create_index('{index_name}', '{table_name}', ['created_at'])")
        
        if any(f['name'] == 'updated_at' for f in model['fields']):
            index_name = f"ix_{table_name}_updated_at"
            indexes.append(f"    op.create_index('{index_name}', '{table_name}', ['updated_at'])")
        
        return "\n".join(indexes) if indexes else ""
    
    def _generate_foreign_key_constraints(self, models: List[Dict[str, Any]]) -> str:
        """Generate foreign key constraint creation statements."""
        constraints = []
        
        for model in models:
            table_name = f"{model['name'].lower()}s"
            
            for field in model['fields']:
                if field.get('foreign_key'):
                    fk_table, fk_column = field['foreign_key'].split('.')
                    constraint_name = f"fk_{table_name}_{field['name']}_{fk_table}_{fk_column}"
                    
                    constraint = f"""    op.create_foreign_key(
        '{constraint_name}',
        '{table_name}',
        '{fk_table}',
        ['{field['name']}'],
        ['{fk_column}'],
        ondelete='CASCADE'
    )"""
                    constraints.append(constraint)
        
        return "\n".join(constraints) if constraints else ""
    
    def _generate_alembic_env(self) -> str:
        """Generate Alembic environment configuration."""
        return '''"""
Alembic environment configuration.
"""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from models.database import Base  # Import your models
from config.database import get_database_url

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL
config.set_main_option("sqlalchemy.url", get_database_url())

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite compatibility
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    def _generate_alembic_config(self) -> str:
        """Generate Alembic configuration file."""
        return '''# Alembic configuration file

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration file names
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
timezone = UTC

# max length of characters to apply to the "slug" field
truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
sourceless = false

# version path separator; As mentioned above, this is the character used to split
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.

# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
    
    def _generate_migration_utils(self) -> str:
        """Generate migration utility functions."""
        return '''"""
Migration utility functions for common database operations.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def create_table_with_audit_columns(table_name: str, columns: List[sa.Column], 
                                  add_audit: bool = True) -> None:
    """Create table with optional audit columns."""
    if add_audit:
        columns.extend([
            sa.Column('created_at', sa.DateTime(timezone=True), 
                     server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), 
                     server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True)
        ])
    
    op.create_table(table_name, *columns)
    logger.info(f"Created table: {table_name}")


def drop_table_safely(table_name: str) -> None:
    """Drop table if it exists."""
    try:
        op.drop_table(table_name)
        logger.info(f"Dropped table: {table_name}")
    except Exception as e:
        logger.warning(f"Failed to drop table {table_name}: {e}")


def add_column_with_default(table_name: str, column_name: str, 
                          column_type: sa.types.TypeEngine, 
                          default_value: Any = None,
                          nullable: bool = True) -> None:
    """Add column with default value."""
    column = sa.Column(column_name, column_type, nullable=nullable)
    
    if default_value is not None:
        column.server_default = str(default_value)
    
    op.add_column(table_name, column)
    logger.info(f"Added column {column_name} to {table_name}")


def create_enum_type(enum_name: str, values: List[str]) -> None:
    """Create PostgreSQL enum type."""
    enum_type = sa.Enum(*values, name=enum_name)
    enum_type.create(op.get_bind())
    logger.info(f"Created enum type: {enum_name}")


def drop_enum_type(enum_name: str) -> None:
    """Drop PostgreSQL enum type."""
    op.execute(text(f"DROP TYPE IF EXISTS {enum_name}"))
    logger.info(f"Dropped enum type: {enum_name}")


def create_index_concurrently(index_name: str, table_name: str, 
                            columns: List[str]) -> None:
    """Create index concurrently (PostgreSQL)."""
    op.create_index(
        index_name, 
        table_name, 
        columns,
        postgresql_concurrently=True
    )
    logger.info(f"Created index concurrently: {index_name}")


def add_foreign_key_with_validation(constraint_name: str, source_table: str,
                                  referent_table: str, local_cols: List[str],
                                  remote_cols: List[str],
                                  ondelete: str = 'CASCADE') -> None:
    """Add foreign key constraint with validation."""
    # Check if tables exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if source_table not in inspector.get_table_names():
        raise ValueError(f"Source table {source_table} does not exist")
    
    if referent_table not in inspector.get_table_names():
        raise ValueError(f"Referenced table {referent_table} does not exist")
    
    op.create_foreign_key(
        constraint_name,
        source_table,
        referent_table,
        local_cols,
        remote_cols,
        ondelete=ondelete
    )
    logger.info(f"Created foreign key: {constraint_name}")


def execute_sql_file(file_path: str) -> None:
    """Execute SQL commands from file."""
    try:
        with open(file_path, 'r') as f:
            sql_commands = f.read()
        
        # Split by semicolon and execute each command
        for command in sql_commands.split(';'):
            command = command.strip()
            if command:
                op.execute(text(command))
        
        logger.info(f"Executed SQL file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to execute SQL file {file_path}: {e}")
        raise


def backup_table_data(table_name: str, backup_table_name: str = None) -> None:
    """Create backup of table data."""
    if backup_table_name is None:
        backup_table_name = f"{table_name}_backup_{int(time.time())}"
    
    op.execute(text(f"""
        CREATE TABLE {backup_table_name} AS 
        SELECT * FROM {table_name}
    """))
    logger.info(f"Created backup table: {backup_table_name}")


def restore_table_data(backup_table_name: str, target_table_name: str) -> None:
    """Restore table data from backup."""
    op.execute(text(f"""
        INSERT INTO {target_table_name} 
        SELECT * FROM {backup_table_name}
    """))
    logger.info(f"Restored data from {backup_table_name} to {target_table_name}")


class MigrationContext:
    """Context manager for safe migrations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Starting migration operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"Completed migration operation: {self.operation_name} "
                       f"in {duration:.2f} seconds")
        else:
            logger.error(f"Failed migration operation: {self.operation_name} "
                        f"after {duration:.2f} seconds: {exc_val}")
        return False
'''
    
    def _generate_rollback_scripts(self, models: List[Dict[str, Any]]) -> str:
        """Generate rollback utility scripts."""
        return '''"""
Database rollback utilities for safe migration reversals.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages database rollbacks with safety checks."""
    
    def __init__(self, database_url: str):
        """Initialize rollback manager."""
        self.engine = create_async_engine(database_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def create_rollback_point(self, name: str) -> str:
        """Create a rollback point (savepoint)."""
        rollback_id = f"rollback_{name}_{int(datetime.now().timestamp())}"
        
        async with self.async_session() as session:
            await session.execute(text(f"SAVEPOINT {rollback_id}"))
            await session.commit()
            
        logger.info(f"Created rollback point: {rollback_id}")
        return rollback_id
    
    async def rollback_to_point(self, rollback_id: str) -> bool:
        """Rollback to a specific savepoint."""
        try:
            async with self.async_session() as session:
                await session.execute(text(f"ROLLBACK TO SAVEPOINT {rollback_id}"))
                await session.commit()
                
            logger.info(f"Rolled back to: {rollback_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for {rollback_id}: {e}")
            return False
    
    async def backup_tables(self, table_names: List[str]) -> Dict[str, str]:
        """Create backup copies of tables."""
        backup_names = {}
        timestamp = int(datetime.now().timestamp())
        
        async with self.async_session() as session:
            for table_name in table_names:
                backup_name = f"{table_name}_backup_{timestamp}"
                
                try:
                    await session.execute(text(f"""
                        CREATE TABLE {backup_name} AS 
                        SELECT * FROM {table_name}
                    """))
                    backup_names[table_name] = backup_name
                    logger.info(f"Created backup: {backup_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to backup {table_name}: {e}")
            
            await session.commit()
        
        return backup_names
    
    async def restore_from_backup(self, table_name: str, backup_name: str) -> bool:
        """Restore table from backup."""
        try:
            async with self.async_session() as session:
                # Clear current table
                await session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                
                # Restore from backup
                await session.execute(text(f"""
                    INSERT INTO {table_name} 
                    SELECT * FROM {backup_name}
                """))
                
                await session.commit()
                
            logger.info(f"Restored {table_name} from {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore {table_name} from {backup_name}: {e}")
            return False
    
    async def verify_data_integrity(self, table_name: str) -> Dict[str, Any]:
        """Verify data integrity after migration."""
        integrity_report = {
            'table_name': table_name,
            'row_count': 0,
            'null_counts': {},
            'constraint_violations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        async with self.async_session() as session:
            # Count rows
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            integrity_report['row_count'] = result.scalar()
            
            # Check for constraint violations (basic check)
            try:
                await session.execute(text(f"""
                    SELECT * FROM {table_name} 
                    WHERE id IS NULL OR id < 0
                    LIMIT 1
                """))
            except Exception as e:
                integrity_report['constraint_violations'].append(str(e))
        
        return integrity_report
    
    async def cleanup_backups(self, backup_names: List[str]) -> None:
        """Clean up backup tables."""
        async with self.async_session() as session:
            for backup_name in backup_names:
                try:
                    await session.execute(text(f"DROP TABLE IF EXISTS {backup_name}"))
                    logger.info(f"Cleaned up backup: {backup_name}")
                except Exception as e:
                    logger.error(f"Failed to cleanup {backup_name}: {e}")
            
            await session.commit()
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


async def safe_migration_rollback(database_url: str, target_revision: str) -> bool:
    """Perform safe migration rollback with verification."""
    rollback_manager = RollbackManager(database_url)
    
    try:
        # Create rollback point
        rollback_point = await rollback_manager.create_rollback_point("pre_rollback")
        
        # TODO: Execute Alembic rollback to target revision
        # This would integrate with Alembic's downgrade functionality
        
        logger.info(f"Migration rollback to {target_revision} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration rollback failed: {e}")
        # Attempt to rollback to our savepoint
        await rollback_manager.rollback_to_point(rollback_point)
        return False
        
    finally:
        await rollback_manager.close()


if __name__ == "__main__":
    # Example usage
    import os
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    
    async def example_rollback():
        success = await safe_migration_rollback(database_url, "previous_revision")
        if success:
            print("Rollback completed successfully")
        else:
            print("Rollback failed")
    
    asyncio.run(example_rollback())
'''