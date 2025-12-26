"""
Teradata Migration Service
Handles migration from Teradata to Azure SQL Database
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import pyodbc
from azure.storage.blob import BlobServiceClient
from azure.storage.file.datalake import DataLakeServiceClient

from src.shared.config.settings import config_manager
from src.shared.storage.sql_service import SQLService

class MigrationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class TeradataTable:
    table_name: str
    schema_name: str
    column_count: int
    row_count: int
    size_mb: float
    last_modified: datetime
    columns: List[Dict[str, Any]]

@dataclass
class MigrationJob:
    job_id: str
    source_system: str
    target_system: str
    status: MigrationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress_percentage: float = 0.0
    tables_migrated: int = 0
    total_tables: int = 0

class TeradataMigrator:
    """Teradata to Azure SQL Database migration service"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        self.sql_service = SQLService(self.config.sql_connection_string)
        self.data_lake_service = DataLakeServiceClient.from_connection_string(
            self.config.data_lake_connection_string
        )
        
        # Teradata connection parameters
        self.teradata_config = {
            'host': self.config.teradata_host,
            'user': self.config.teradata_user,
            'password': self.config.teradata_password,
            'database': self.config.teradata_database
        }
    
    async def analyze_teradata_schema(self, schema_name: str = None) -> List[TeradataTable]:
        """Analyze Teradata schema and return table information"""
        try:
            self.logger.info(f"Analyzing Teradata schema: {schema_name or 'ALL'}")
            
            # Connect to Teradata
            conn_str = f"DRIVER={{Teradata}};DBCNAME={self.teradata_config['host']};UID={self.teradata_config['user']};PWD={self.teradata_config['password']}"
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                
                # Query to get table information
                query = """
                SELECT 
                    DatabaseName,
                    TableName,
                    ColumnCount,
                    RowCount,
                    TableSizeKB,
                    LastAccessTimeStamp
                FROM DBC.TablesV 
                WHERE TableKind = 'T'
                """
                
                if schema_name:
                    query += f" AND DatabaseName = '{schema_name}'"
                
                cursor.execute(query)
                tables = []
                
                for row in cursor.fetchall():
                    # Get column details
                    column_query = f"""
                    SELECT 
                        ColumnName,
                        ColumnType,
                        ColumnLength,
                        Nullable,
                        DefaultValue
                    FROM DBC.ColumnsV 
                    WHERE DatabaseName = '{row[0]}' 
                    AND TableName = '{row[1]}'
                    ORDER BY ColumnId
                    """
                    
                    cursor.execute(column_query)
                    columns = []
                    for col_row in cursor.fetchall():
                        columns.append({
                            'name': col_row[0],
                            'type': col_row[1],
                            'length': col_row[2],
                            'nullable': col_row[3] == 'Y',
                            'default_value': col_row[4]
                        })
                    
                    table = TeradataTable(
                        table_name=row[1],
                        schema_name=row[0],
                        column_count=row[2],
                        row_count=row[3],
                        size_mb=row[4] / 1024,
                        last_modified=row[5],
                        columns=columns
                    )
                    tables.append(table)
            
            self.logger.info(f"Found {len(tables)} tables in Teradata")
            return tables
            
        except Exception as e:
            self.logger.error(f"Error analyzing Teradata schema: {str(e)}")
            raise
    
    def convert_teradata_to_azure_sql(self, teradata_table: TeradataTable) -> str:
        """Convert Teradata DDL to Azure SQL DDL"""
        ddl = f"CREATE TABLE [{teradata_table.schema_name}].[{teradata_table.table_name}] (\n"
        
        column_definitions = []
        for col in teradata_table.columns:
            # Convert Teradata types to SQL Server types
            sql_type = self._convert_data_type(col['type'], col['length'])
            
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default_value']}" if col['default_value'] else ""
            
            column_def = f"    [{col['name']}] {sql_type} {nullable}{default}"
            column_definitions.append(column_def)
        
        ddl += ",\n".join(column_definitions)
        ddl += "\n);"
        
        return ddl
    
    def _convert_data_type(self, teradata_type: str, length: int) -> str:
        """Convert Teradata data types to SQL Server data types"""
        type_mapping = {
            'CHAR': f'CHAR({length})',
            'VARCHAR': f'VARCHAR({length})',
            'LONG VARCHAR': 'NVARCHAR(MAX)',
            'CLOB': 'NVARCHAR(MAX)',
            'INTEGER': 'INT',
            'BIGINT': 'BIGINT',
            'SMALLINT': 'SMALLINT',
            'DECIMAL': 'DECIMAL(18,2)',
            'NUMERIC': 'NUMERIC(18,2)',
            'FLOAT': 'FLOAT',
            'REAL': 'REAL',
            'DOUBLE PRECISION': 'FLOAT',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'TIMESTAMP': 'DATETIME2',
            'TIMESTAMP WITH TIME ZONE': 'DATETIMEOFFSET',
            'BLOB': 'VARBINARY(MAX)',
            'BYTE': 'VARBINARY(MAX)',
            'VARBYTE': 'VARBINARY(MAX)'
        }
        
        return type_mapping.get(teradata_type.upper(), 'NVARCHAR(MAX)')
    
    async def migrate_table_data(self, teradata_table: TeradataTable, 
                                batch_size: int = 10000) -> Dict[str, Any]:
        """Migrate data from Teradata table to Azure SQL Database"""
        try:
            self.logger.info(f"Starting data migration for table: {teradata_table.table_name}")
            
            # Create target table
            ddl = self.convert_teradata_to_azure_sql(teradata_table)
            await self.sql_service.execute_non_query(ddl)
            
            # Migrate data in batches
            conn_str = f"DRIVER={{Teradata}};DBCNAME={self.teradata_config['host']};UID={self.teradata_config['user']};PWD={self.teradata_config['password']}"
            
            with pyodbc.connect(conn_str) as source_conn:
                source_cursor = source_conn.cursor()
                
                # Get total row count
                count_query = f"SELECT COUNT(*) FROM {teradata_table.schema_name}.{teradata_table.table_name}"
                source_cursor.execute(count_query)
                total_rows = source_cursor.fetchone()[0]
                
                # Migrate data in batches
                offset = 0
                migrated_rows = 0
                
                while offset < total_rows:
                    # Fetch batch from Teradata
                    data_query = f"""
                    SELECT * FROM {teradata_table.schema_name}.{teradata_table.table_name}
                    ORDER BY 1
                    OFFSET {offset} ROWS
                    FETCH NEXT {batch_size} ROWS ONLY
                    """
                    
                    source_cursor.execute(data_query)
                    rows = source_cursor.fetchall()
                    
                    if not rows:
                        break
                    
                    # Insert batch into Azure SQL
                    await self._insert_batch(teradata_table, rows)
                    
                    migrated_rows += len(rows)
                    offset += batch_size
                    
                    self.logger.info(f"Migrated {migrated_rows}/{total_rows} rows for {teradata_table.table_name}")
            
            return {
                'table_name': teradata_table.table_name,
                'total_rows': total_rows,
                'migrated_rows': migrated_rows,
                'status': 'completed'
            }
            
        except Exception as e:
            self.logger.error(f"Error migrating table {teradata_table.table_name}: {str(e)}")
            raise
    
    async def _insert_batch(self, teradata_table: TeradataTable, rows: List[tuple]):
        """Insert a batch of rows into Azure SQL Database with actual data validation"""
        if not rows:
            return
        
        try:
            # Validate table structure exists
            await self._ensure_table_exists(teradata_table)
            
            # Build INSERT statement with proper parameterized queries
            column_names = [col['name'] for col in teradata_table.columns]
            column_types = [col['type'] for col in teradata_table.columns]
            
            # Create parameterized placeholders for SQL injection prevention
            param_placeholders = ', '.join(['?' for _ in column_names])
            
            insert_sql = f"""
            INSERT INTO [{teradata_table.schema_name}].[{teradata_table.table_name}]
            ({', '.join([f'[{name}]' for name in column_names])})
            VALUES ({param_placeholders})
            """
            
            # Validate and transform data before insertion
            validated_rows = []
            for row in rows:
                validated_row = self._validate_and_transform_row(row, column_types)
                validated_rows.append(validated_row)
            
            # Execute batch insert with actual data
            await self.sql_service.execute_non_query(insert_sql, validated_rows)
            
            self.logger.info(f"Successfully inserted {len(validated_rows)} rows into {teradata_table.table_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to insert batch into {teradata_table.table_name}: {str(e)}")
            raise
    
    async def _ensure_table_exists(self, teradata_table: TeradataTable):
        """Ensure the target table exists in Azure SQL Database"""
        try:
            # Check if table exists
            check_sql = """
            SELECT COUNT(*) as table_count
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """
            
            result = await self.sql_service.execute_query(check_sql, (teradata_table.schema_name, teradata_table.table_name))
            
            if result[0]['table_count'] == 0:
                # Create table if it doesn't exist
                await self._create_target_table(teradata_table)
                
        except Exception as e:
            self.logger.error(f"Failed to ensure table exists: {str(e)}")
            raise
    
    async def _create_target_table(self, teradata_table: TeradataTable):
        """Create the target table in Azure SQL Database"""
        try:
            # Build CREATE TABLE statement
            column_definitions = []
            for col in teradata_table.columns:
                sql_type = self._map_teradata_to_sql_type(col['type'])
                column_definitions.append(f"[{col['name']}] {sql_type}")
            
            create_sql = f"""
            CREATE TABLE [{teradata_table.schema_name}].[{teradata_table.table_name}] (
                {', '.join(column_definitions)}
            )
            """
            
            await self.sql_service.execute_non_query(create_sql)
            self.logger.info(f"Created table {teradata_table.table_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create table: {str(e)}")
            raise
    
    def _validate_and_transform_row(self, row: tuple, column_types: List[str]) -> tuple:
        """Validate and transform row data according to column types"""
        try:
            validated_row = []
            for i, (value, col_type) in enumerate(zip(row, column_types)):
                if value is None:
                    validated_row.append(None)
                elif col_type in ['VARCHAR', 'CHAR', 'TEXT']:
                    validated_row.append(str(value))
                elif col_type in ['INTEGER', 'BIGINT', 'SMALLINT']:
                    validated_row.append(int(value))
                elif col_type in ['DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE']:
                    validated_row.append(float(value))
                elif col_type in ['DATE']:
                    validated_row.append(value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value))
                elif col_type in ['TIMESTAMP', 'DATETIME']:
                    validated_row.append(value.isoformat() if hasattr(value, 'isoformat') else str(value))
                else:
                    validated_row.append(str(value))
            
            return tuple(validated_row)
            
        except Exception as e:
            self.logger.error(f"Failed to validate row data: {str(e)}")
            raise
    
    def _map_teradata_to_sql_type(self, teradata_type: str) -> str:
        """Map Teradata data types to Azure SQL Database types"""
        type_mapping = {
            'VARCHAR': 'NVARCHAR(MAX)',
            'CHAR': 'NCHAR(255)',
            'INTEGER': 'INT',
            'BIGINT': 'BIGINT',
            'SMALLINT': 'SMALLINT',
            'DECIMAL': 'DECIMAL(18,2)',
            'NUMERIC': 'NUMERIC(18,2)',
            'FLOAT': 'FLOAT',
            'DOUBLE': 'FLOAT',
            'DATE': 'DATE',
            'TIMESTAMP': 'DATETIME2',
            'TIME': 'TIME'
        }
        
        return type_mapping.get(teradata_type.upper(), 'NVARCHAR(MAX)')
    
    async def create_migration_job(self, source_schema: str, target_schema: str) -> MigrationJob:
        """Create a new migration job"""
        job_id = f"teradata_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        job = MigrationJob(
            job_id=job_id,
            source_system="Teradata",
            target_system="Azure SQL Database",
            status=MigrationStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Store job in database
        await self.sql_service.execute_non_query("""
            INSERT INTO migration_jobs (job_id, source_system, target_system, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (job.job_id, job.source_system, job.target_system, job.status.value, job.created_at))
        
        return job
    
    async def execute_migration(self, job_id: str, schema_name: str) -> Dict[str, Any]:
        """Execute the migration job"""
        try:
            # Update job status
            await self.sql_service.execute_non_query("""
                UPDATE migration_jobs 
                SET status = ?, started_at = ?
                WHERE job_id = ?
            """, (MigrationStatus.IN_PROGRESS.value, datetime.now(), job_id))
            
            # Analyze source schema
            tables = await self.analyze_teradata_schema(schema_name)
            
            # Update total tables count
            await self.sql_service.execute_non_query("""
                UPDATE migration_jobs 
                SET total_tables = ?
                WHERE job_id = ?
            """, (len(tables), job_id))
            
            # Migrate each table
            migrated_tables = []
            for i, table in enumerate(tables):
                try:
                    result = await self.migrate_table_data(table)
                    migrated_tables.append(result)
                    
                    # Update progress
                    progress = ((i + 1) / len(tables)) * 100
                    await self.sql_service.execute_non_query("""
                        UPDATE migration_jobs 
                        SET progress_percentage = ?, tables_migrated = ?
                        WHERE job_id = ?
                    """, (progress, i + 1, job_id))
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate table {table.table_name}: {str(e)}")
                    continue
            
            # Update job status to completed
            await self.sql_service.execute_non_query("""
                UPDATE migration_jobs 
                SET status = ?, completed_at = ?
                WHERE job_id = ?
            """, (MigrationStatus.COMPLETED.value, datetime.now(), job_id))
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'tables_migrated': len(migrated_tables),
                'total_tables': len(tables),
                'migrated_tables': migrated_tables
            }
            
        except Exception as e:
            # Update job status to failed
            await self.sql_service.execute_non_query("""
                UPDATE migration_jobs 
                SET status = ?, error_message = ?
                WHERE job_id = ?
            """, (MigrationStatus.FAILED.value, str(e), job_id))
            
            self.logger.error(f"Migration job {job_id} failed: {str(e)}")
            raise
    
    async def get_migration_status(self, job_id: str) -> Optional[MigrationJob]:
        """Get migration job status"""
        try:
            result = await self.sql_service.execute_query("""
                SELECT job_id, source_system, target_system, status, created_at, 
                       started_at, completed_at, error_message, progress_percentage,
                       tables_migrated, total_tables
                FROM migration_jobs 
                WHERE job_id = ?
            """, (job_id,))
            
            if result:
                row = result[0]
                return MigrationJob(
                    job_id=row[0],
                    source_system=row[1],
                    target_system=row[2],
                    status=MigrationStatus(row[3]),
                    created_at=row[4],
                    started_at=row[5],
                    completed_at=row[6],
                    error_message=row[7],
                    progress_percentage=row[8],
                    tables_migrated=row[9],
                    total_tables=row[10]
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting migration status: {str(e)}")
            return None