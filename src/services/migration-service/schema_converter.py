"""
Schema Converter Service
Converts legacy database schemas to Azure SQL Database schemas
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re
from azure.storage.blob import BlobServiceClient

from ...shared.config.settings import config_manager
from ...shared.storage.sql_service import SQLService

class DatabaseType(Enum):
    TERADATA = "teradata"
    NETEZZA = "netezza"
    ORACLE = "oracle"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQL_SERVER = "sql_server"

@dataclass
class ColumnDefinition:
    name: str
    data_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None
    is_unique: bool = False
    is_identity: bool = False
    check_constraint: Optional[str] = None

@dataclass
class TableDefinition:
    name: str
    schema_name: str
    columns: List[ColumnDefinition]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    indexes: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    table_type: str = "TABLE"
    comment: Optional[str] = None

class SchemaConverter:
    """Converts legacy database schemas to Azure SQL Database schemas"""
    
    def __init__(self):
        self.config = config_manager.get_azure_config()
        self.logger = logging.getLogger(__name__)
        self.sql_service = SQLService(self.config.sql_connection_string)
        
        # Data type mapping for different databases
        self.type_mappings = {
            DatabaseType.TERADATA: {
                'CHAR': 'CHAR',
                'VARCHAR': 'VARCHAR',
                'LONG VARCHAR': 'NVARCHAR(MAX)',
                'CLOB': 'NVARCHAR(MAX)',
                'INTEGER': 'INT',
                'BIGINT': 'BIGINT',
                'SMALLINT': 'SMALLINT',
                'DECIMAL': 'DECIMAL',
                'NUMERIC': 'NUMERIC',
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
            },
            DatabaseType.NETEZZA: {
                'VARCHAR': 'VARCHAR',
                'NVARCHAR': 'NVARCHAR',
                'CHAR': 'CHAR',
                'NCHAR': 'NCHAR',
                'TEXT': 'NVARCHAR(MAX)',
                'NTEXT': 'NVARCHAR(MAX)',
                'INTEGER': 'INT',
                'BIGINT': 'BIGINT',
                'SMALLINT': 'SMALLINT',
                'TINYINT': 'TINYINT',
                'DECIMAL': 'DECIMAL',
                'NUMERIC': 'NUMERIC',
                'FLOAT': 'FLOAT',
                'REAL': 'REAL',
                'DOUBLE': 'FLOAT',
                'DATE': 'DATE',
                'TIME': 'TIME',
                'TIMESTAMP': 'DATETIME2',
                'TIMESTAMPTZ': 'DATETIMEOFFSET',
                'BLOB': 'VARBINARY(MAX)',
                'BYTE': 'VARBINARY(MAX)',
                'VARBYTE': 'VARBINARY(MAX)',
                'BOOLEAN': 'BIT'
            },
            DatabaseType.ORACLE: {
                'VARCHAR2': 'NVARCHAR',
                'CHAR': 'NCHAR',
                'NCHAR': 'NCHAR',
                'NVARCHAR2': 'NVARCHAR',
                'CLOB': 'NVARCHAR(MAX)',
                'NCLOB': 'NVARCHAR(MAX)',
                'NUMBER': 'DECIMAL',
                'INTEGER': 'INT',
                'FLOAT': 'FLOAT',
                'BINARY_FLOAT': 'REAL',
                'BINARY_DOUBLE': 'FLOAT',
                'DATE': 'DATETIME2',
                'TIMESTAMP': 'DATETIME2',
                'TIMESTAMP WITH TIME ZONE': 'DATETIMEOFFSET',
                'TIMESTAMP WITH LOCAL TIME ZONE': 'DATETIMEOFFSET',
                'BLOB': 'VARBINARY(MAX)',
                'BFILE': 'VARBINARY(MAX)',
                'RAW': 'VARBINARY',
                'LONG RAW': 'VARBINARY(MAX)'
            },
            DatabaseType.MYSQL: {
                'VARCHAR': 'NVARCHAR',
                'CHAR': 'NCHAR',
                'TEXT': 'NVARCHAR(MAX)',
                'LONGTEXT': 'NVARCHAR(MAX)',
                'TINYINT': 'TINYINT',
                'SMALLINT': 'SMALLINT',
                'MEDIUMINT': 'INT',
                'INT': 'INT',
                'BIGINT': 'BIGINT',
                'DECIMAL': 'DECIMAL',
                'FLOAT': 'FLOAT',
                'DOUBLE': 'FLOAT',
                'DATE': 'DATE',
                'TIME': 'TIME',
                'DATETIME': 'DATETIME2',
                'TIMESTAMP': 'DATETIME2',
                'YEAR': 'SMALLINT',
                'BLOB': 'VARBINARY(MAX)',
                'LONGBLOB': 'VARBINARY(MAX)',
                'JSON': 'NVARCHAR(MAX)'
            },
            DatabaseType.POSTGRESQL: {
                'VARCHAR': 'NVARCHAR',
                'CHAR': 'NCHAR',
                'TEXT': 'NVARCHAR(MAX)',
                'SMALLINT': 'SMALLINT',
                'INTEGER': 'INT',
                'BIGINT': 'BIGINT',
                'DECIMAL': 'DECIMAL',
                'NUMERIC': 'NUMERIC',
                'REAL': 'REAL',
                'DOUBLE PRECISION': 'FLOAT',
                'MONEY': 'DECIMAL(19,4)',
                'DATE': 'DATE',
                'TIME': 'TIME',
                'TIMESTAMP': 'DATETIME2',
                'TIMESTAMPTZ': 'DATETIMEOFFSET',
                'INTERVAL': 'NVARCHAR(50)',
                'BOOLEAN': 'BIT',
                'BYTEA': 'VARBINARY(MAX)',
                'JSON': 'NVARCHAR(MAX)',
                'JSONB': 'NVARCHAR(MAX)',
                'UUID': 'UNIQUEIDENTIFIER'
            }
        }
    
    def convert_ddl(self, source_ddl: str, source_type: DatabaseType, 
                   target_schema: str = "dbo") -> str:
        """Convert DDL from source database to Azure SQL Database DDL"""
        try:
            self.logger.info(f"Converting DDL from {source_type.value} to Azure SQL Database")
            
            # Parse the source DDL
            parsed_ddl = self._parse_ddl(source_ddl, source_type)
            
            # Convert to Azure SQL DDL
            azure_ddl = self._generate_azure_ddl(parsed_ddl, target_schema)
            
            return azure_ddl
            
        except Exception as e:
            self.logger.error(f"Error converting DDL: {str(e)}")
            raise
    
    def _parse_ddl(self, ddl: str, source_type: DatabaseType) -> TableDefinition:
        """Parse DDL string into structured format"""
        # This is a simplified parser - in production, you'd use a proper SQL parser
        ddl = ddl.strip().upper()
        
        # Extract table name
        table_match = re.search(r'CREATE\s+TABLE\s+(\w+)\.(\w+)', ddl)
        if not table_match:
            table_match = re.search(r'CREATE\s+TABLE\s+(\w+)', ddl)
            if table_match:
                schema_name = "dbo"
                table_name = table_match.group(1)
            else:
                raise ValueError("Could not extract table name from DDL")
        else:
            schema_name = table_match.group(1)
            table_name = table_match.group(2)
        
        # Extract columns (simplified - would need more robust parsing)
        columns = self._extract_columns(ddl, source_type)
        
        # Extract constraints
        primary_keys = self._extract_primary_keys(ddl)
        foreign_keys = self._extract_foreign_keys(ddl)
        indexes = self._extract_indexes(ddl)
        constraints = self._extract_constraints(ddl)
        
        return TableDefinition(
            name=table_name,
            schema_name=schema_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            constraints=constraints
        )
    
    def _extract_columns(self, ddl: str, source_type: DatabaseType) -> List[ColumnDefinition]:
        """Extract column definitions from DDL"""
        columns = []
        
        # Find the column definitions section
        start_match = re.search(r'CREATE\s+TABLE\s+\w+(?:\.\w+)?\s*\(', ddl)
        if not start_match:
            return columns
        
        start_pos = start_match.end()
        
        # Find the end of column definitions
        paren_count = 1
        pos = start_pos
        while pos < len(ddl) and paren_count > 0:
            if ddl[pos] == '(':
                paren_count += 1
            elif ddl[pos] == ')':
                paren_count -= 1
            pos += 1
        
        column_section = ddl[start_pos:pos-1]
        
        # Split by commas and parse each column
        column_lines = [line.strip() for line in column_section.split(',') if line.strip()]
        
        for line in column_lines:
            if line.startswith('PRIMARY KEY') or line.startswith('FOREIGN KEY') or line.startswith('CONSTRAINT'):
                continue
            
            column = self._parse_column_definition(line, source_type)
            if column:
                columns.append(column)
        
        return columns
    
    def _parse_column_definition(self, line: str, source_type: DatabaseType) -> Optional[ColumnDefinition]:
        """Parse a single column definition line"""
        try:
            # Split by spaces
            parts = line.split()
            if len(parts) < 2:
                return None
            
            name = parts[0].strip('`"[]')
            
            # Find data type
            data_type = parts[1].upper()
            
            # Extract length/precision
            length = None
            precision = None
            scale = None
            
            if '(' in data_type:
                type_parts = data_type.split('(')
                data_type = type_parts[0]
                params = type_parts[1].rstrip(')')
                
                if ',' in params:
                    precision, scale = map(int, params.split(','))
                else:
                    length = int(params)
            
            # Check for constraints
            nullable = 'NOT NULL' not in line.upper()
            is_primary_key = 'PRIMARY KEY' in line.upper()
            is_unique = 'UNIQUE' in line.upper()
            is_identity = 'IDENTITY' in line.upper() or 'AUTO_INCREMENT' in line.upper()
            
            # Extract default value
            default_value = None
            default_match = re.search(r'DEFAULT\s+([^,\s]+)', line, re.IGNORECASE)
            if default_match:
                default_value = default_match.group(1)
            
            return ColumnDefinition(
                name=name,
                data_type=data_type,
                length=length,
                precision=precision,
                scale=scale,
                nullable=nullable,
                default_value=default_value,
                is_primary_key=is_primary_key,
                is_unique=is_unique,
                is_identity=is_identity
            )
            
        except Exception as e:
            self.logger.warning(f"Could not parse column definition: {line} - {str(e)}")
            return None
    
    def _extract_primary_keys(self, ddl: str) -> List[str]:
        """Extract primary key columns"""
        primary_keys = []
        
        # Look for PRIMARY KEY constraint
        pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', ddl, re.IGNORECASE)
        if pk_match:
            pk_columns = [col.strip().strip('`"[]') for col in pk_match.group(1).split(',')]
            primary_keys.extend(pk_columns)
        
        return primary_keys
    
    def _extract_foreign_keys(self, ddl: str) -> List[Dict[str, str]]:
        """Extract foreign key constraints"""
        foreign_keys = []
        
        # Look for FOREIGN KEY constraints
        fk_matches = re.finditer(r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)\s*\(([^)]+)\)', ddl, re.IGNORECASE)
        
        for match in fk_matches:
            fk_columns = [col.strip().strip('`"[]') for col in match.group(1).split(',')]
            ref_table = match.group(2)
            ref_columns = [col.strip().strip('`"[]') for col in match.group(3).split(',')]
            
            for i, fk_col in enumerate(fk_columns):
                foreign_keys.append({
                    'column': fk_col,
                    'referenced_table': ref_table,
                    'referenced_column': ref_columns[i] if i < len(ref_columns) else ref_columns[0]
                })
        
        return foreign_keys
    
    def _extract_indexes(self, ddl: str) -> List[Dict[str, Any]]:
        """Extract index definitions"""
        indexes = []
        
        # Look for INDEX definitions
        index_matches = re.finditer(r'INDEX\s+(\w+)\s*\(([^)]+)\)', ddl, re.IGNORECASE)
        
        for match in index_matches:
            index_name = match.group(1)
            index_columns = [col.strip().strip('`"[]') for col in match.group(2).split(',')]
            
            indexes.append({
                'name': index_name,
                'columns': index_columns,
                'unique': False
            })
        
        return indexes
    
    def _extract_constraints(self, ddl: str) -> List[Dict[str, Any]]:
        """Extract check constraints"""
        constraints = []
        
        # Look for CHECK constraints
        check_matches = re.finditer(r'CHECK\s*\(([^)]+)\)', ddl, re.IGNORECASE)
        
        for match in check_matches:
            constraints.append({
                'type': 'CHECK',
                'definition': match.group(1)
            })
        
        return constraints
    
    def _generate_azure_ddl(self, table_def: TableDefinition, target_schema: str) -> str:
        """Generate Azure SQL Database DDL from parsed table definition"""
        ddl_parts = []
        
        # CREATE TABLE statement
        ddl_parts.append(f"CREATE TABLE [{target_schema}].[{table_def.name}] (")
        
        # Column definitions
        column_definitions = []
        for col in table_def.columns:
            col_def = self._generate_column_definition(col)
            column_definitions.append(f"    {col_def}")
        
        ddl_parts.append(",\n".join(column_definitions))
        
        # Primary key constraint
        if table_def.primary_keys:
            pk_columns = ", ".join([f"[{col}]" for col in table_def.primary_keys])
            ddl_parts.append(f",\n    CONSTRAINT PK_{table_def.name} PRIMARY KEY ({pk_columns})")
        
        # Foreign key constraints
        for fk in table_def.foreign_keys:
            fk_def = f"CONSTRAINT FK_{table_def.name}_{fk['column']} FOREIGN KEY ([{fk['column']}]) REFERENCES [{target_schema}].[{fk['referenced_table']}] ([{fk['referenced_column']}])"
            ddl_parts.append(f",\n    {fk_def}")
        
        ddl_parts.append("\n);")
        
        # Indexes
        for index in table_def.indexes:
            index_columns = ", ".join([f"[{col}]" for col in index['columns']])
            unique_keyword = "UNIQUE " if index['unique'] else ""
            index_ddl = f"CREATE {unique_keyword}INDEX IX_{table_def.name}_{index['name']} ON [{target_schema}].[{table_def.name}] ({index_columns});"
            ddl_parts.append(f"\n{index_ddl}")
        
        return "\n".join(ddl_parts)
    
    def _generate_column_definition(self, col: ColumnDefinition) -> str:
        """Generate column definition for Azure SQL Database"""
        # Convert data type
        azure_type = self._convert_data_type(col.data_type, col.length, col.precision, col.scale)
        
        # Build column definition
        col_def = f"[{col.name}] {azure_type}"
        
        # Add NOT NULL constraint
        if not col.nullable:
            col_def += " NOT NULL"
        
        # Add IDENTITY
        if col.is_identity:
            col_def += " IDENTITY(1,1)"
        
        # Add default value
        if col.default_value:
            col_def += f" DEFAULT {col.default_value}"
        
        return col_def
    
    def _convert_data_type(self, source_type: str, length: Optional[int] = None, 
                          precision: Optional[int] = None, scale: Optional[int] = None) -> str:
        """Convert data type to Azure SQL Database type"""
        source_type = source_type.upper()
        
        # Handle common type mappings
        if source_type in ['VARCHAR', 'NVARCHAR']:
            if length:
                return f"NVARCHAR({length})"
            else:
                return "NVARCHAR(255)"
        
        elif source_type in ['CHAR', 'NCHAR']:
            if length:
                return f"NCHAR({length})"
            else:
                return "NCHAR(1)"
        
        elif source_type in ['DECIMAL', 'NUMERIC']:
            if precision and scale:
                return f"DECIMAL({precision},{scale})"
            else:
                return "DECIMAL(18,2)"
        
        elif source_type in ['FLOAT', 'DOUBLE']:
            return "FLOAT"
        
        elif source_type in ['INT', 'INTEGER']:
            return "INT"
        
        elif source_type in ['BIGINT']:
            return "BIGINT"
        
        elif source_type in ['SMALLINT']:
            return "SMALLINT"
        
        elif source_type in ['TINYINT']:
            return "TINYINT"
        
        elif source_type in ['BIT', 'BOOLEAN']:
            return "BIT"
        
        elif source_type in ['DATE']:
            return "DATE"
        
        elif source_type in ['TIME']:
            return "TIME"
        
        elif source_type in ['DATETIME', 'TIMESTAMP']:
            return "DATETIME2"
        
        elif source_type in ['TEXT', 'LONGTEXT', 'CLOB', 'NCLOB']:
            return "NVARCHAR(MAX)"
        
        elif source_type in ['BLOB', 'LONGBLOB', 'BYTEA']:
            return "VARBINARY(MAX)"
        
        elif source_type in ['JSON', 'JSONB']:
            return "NVARCHAR(MAX)"
        
        elif source_type in ['UUID']:
            return "UNIQUEIDENTIFIER"
        
        else:
            # Default to NVARCHAR(MAX) for unknown types
            return "NVARCHAR(MAX)"
    
    async def validate_converted_schema(self, ddl: str) -> Dict[str, Any]:
        """Validate the converted DDL syntax"""
        try:
            # Basic syntax validation
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': []
            }
            
            # Check for common issues
            if 'CREATE TABLE' not in ddl.upper():
                validation_result['errors'].append("Missing CREATE TABLE statement")
                validation_result['is_valid'] = False
            
            if 'PRIMARY KEY' not in ddl.upper():
                validation_result['warnings'].append("No primary key defined - consider adding one")
            
            if 'IDENTITY' not in ddl.upper() and 'AUTO_INCREMENT' not in ddl.upper():
                validation_result['suggestions'].append("Consider adding IDENTITY columns for better performance")
            
            # Check for reserved keywords
            reserved_keywords = ['ORDER', 'GROUP', 'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE']
            for keyword in reserved_keywords:
                if f'[{keyword}]' in ddl.upper():
                    validation_result['warnings'].append(f"Column name '{keyword}' is a reserved keyword - consider renaming")
            
            return validation_result
            
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'suggestions': []
            }
    
    async def save_converted_schema(self, ddl: str, filename: str) -> str:
        """Save converted DDL to blob storage"""
        try:
            blob_client = BlobServiceClient.from_connection_string(
                self.config.storage_connection_string
            )
            
            container_name = "migration-schemas"
            blob_name = f"converted-schemas/{filename}"
            
            # Create container if it doesn't exist
            try:
                blob_client.create_container(container_name)
            except Exception as e:
                self.logger.info(f"Container {container_name} already exists or creation failed: {str(e)}")
            
            # Upload the DDL
            blob_client = blob_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(ddl, overwrite=True)
            
            return f"Schema saved to: {container_name}/{blob_name}"
            
        except Exception as e:
            self.logger.error(f"Error saving converted schema: {str(e)}")
            raise