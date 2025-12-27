"""Database optimization and utilities"""

from .optimization import (
    create_optimized_engine,
    apply_database_indexes,
    analyze_database,
    vacuum_database,
    get_slow_queries,
    get_table_sizes,
    get_index_usage,
    DATABASE_INDEXES,
    OPTIMIZED_QUERIES,
)

__all__ = [
    'create_optimized_engine',
    'apply_database_indexes',
    'analyze_database',
    'vacuum_database',
    'get_slow_queries',
    'get_table_sizes',
    'get_index_usage',
    'DATABASE_INDEXES',
    'OPTIMIZED_QUERIES',
]

