"""
Database Optimization Utilities
Includes indexing strategies, query optimization, and connection pooling
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Index, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)


# Production-optimized database indexes
DATABASE_INDEXES = [
    # Documents table indexes
    {
        'table': 'documents',
        'name': 'idx_documents_user_id',
        'columns': ['user_id'],
        'description': 'Fast lookup by user',
    },
    {
        'table': 'documents',
        'name': 'idx_documents_status',
        'columns': ['status'],
        'description': 'Filter by processing status',
    },
    {
        'table': 'documents',
        'name': 'idx_documents_created_at',
        'columns': ['created_at DESC'],
        'description': 'Sort by creation date',
    },
    {
        'table': 'documents',
        'name': 'idx_documents_type',
        'columns': ['document_type'],
        'description': 'Filter by document type',
    },
    {
        'table': 'documents',
        'name': 'idx_documents_user_status',
        'columns': ['user_id', 'status'],
        'description': 'Composite index for user + status queries',
    },
    
    # Entities table indexes
    {
        'table': 'entities',
        'name': 'idx_entities_document_id',
        'columns': ['document_id'],
        'description': 'Fast lookup by document',
    },
    {
        'table': 'entities',
        'name': 'idx_entities_type',
        'columns': ['entity_type'],
        'description': 'Filter by entity type',
    },
    {
        'table': 'entities',
        'name': 'idx_entities_confidence',
        'columns': ['confidence DESC'],
        'description': 'Sort by confidence score',
    },
    
    # Processing logs table indexes
    {
        'table': 'processing_logs',
        'name': 'idx_logs_document_id',
        'columns': ['document_id'],
        'description': 'Fast lookup by document',
    },
    {
        'table': 'processing_logs',
        'name': 'idx_logs_timestamp',
        'columns': ['timestamp DESC'],
        'description': 'Sort by timestamp',
    },
    {
        'table': 'processing_logs',
        'name': 'idx_logs_level',
        'columns': ['log_level'],
        'description': 'Filter by log level',
    },
    
    # API keys table indexes
    {
        'table': 'api_keys',
        'name': 'idx_api_keys_user_id',
        'columns': ['user_id'],
        'description': 'Fast lookup by user',
    },
    {
        'table': 'api_keys',
        'name': 'idx_api_keys_key_hash',
        'columns': ['key_hash'],
        'description': 'Fast authentication lookup',
    },
    
    # Audit logs table indexes
    {
        'table': 'audit_logs',
        'name': 'idx_audit_user_id',
        'columns': ['user_id'],
        'description': 'Fast lookup by user',
    },
    {
        'table': 'audit_logs',
        'name': 'idx_audit_timestamp',
        'columns': ['timestamp DESC'],
        'description': 'Sort by timestamp',
    },
    {
        'table': 'audit_logs',
        'name': 'idx_audit_action',
        'columns': ['action'],
        'description': 'Filter by action type',
    },
]


# Optimized query patterns for common operations
OPTIMIZED_QUERIES = {
    'get_user_documents': """
        SELECT d.id, d.filename, d.status, d.created_at, d.file_size
        FROM documents d
        WHERE d.user_id = :user_id
        ORDER BY d.created_at DESC
        LIMIT :limit OFFSET :offset
    """,
    
    'get_document_with_entities': """
        SELECT d.*, 
               json_agg(e.*) FILTER (WHERE e.id IS NOT NULL) as entities
        FROM documents d
        LEFT JOIN entities e ON d.id = e.document_id
        WHERE d.id = :document_id
        GROUP BY d.id
    """,
    
    'get_dashboard_stats': """
        SELECT 
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as documents_today,
            COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
            COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
            AVG(processing_time) as avg_processing_time
        FROM documents
        WHERE user_id = :user_id
    """,
    
    'get_top_document_types': """
        SELECT document_type, COUNT(*) as count
        FROM documents
        WHERE user_id = :user_id
        GROUP BY document_type
        ORDER BY count DESC
        LIMIT 10
    """,
}


def create_optimized_engine(connection_string: str, **kwargs):
    """
    Create SQLAlchemy engine with production optimizations
    
    Features:
    - Connection pooling
    - Statement caching
    - Optimized pool settings
    """
    return create_engine(
        connection_string,
        poolclass=QueuePool,
        pool_size=20,  # Maximum 20 connections
        max_overflow=40,  # Allow up to 40 additional connections during spikes
        pool_timeout=30,  # Wait 30 seconds for connection
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Verify connection health before use
        echo=False,  # Disable SQL logging in production
        future=True,
        **kwargs
    )


def apply_database_indexes(connection_string: str):
    """
    Apply all production indexes to database
    Should be run during deployment/migration
    """
    engine = create_optimized_engine(connection_string)
    
    logger.info("🔧 Applying database indexes for production optimization...")
    
    with engine.connect() as conn:
        applied_count = 0
        skipped_count = 0
        
        for index_config in DATABASE_INDEXES:
            try:
                # Check if index exists
                check_query = text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = '{index_config['name']}'
                    )
                """)
                
                result = conn.execute(check_query)
                exists = result.scalar()
                
                if exists:
                    logger.debug(f"Index {index_config['name']} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Create index
                columns = ', '.join(index_config['columns'])
                create_query = text(f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_config['name']}
                    ON {index_config['table']} ({columns})
                """)
                
                conn.execute(create_query)
                conn.commit()
                
                logger.info(f"✅ Created index: {index_config['name']} - {index_config['description']}")
                applied_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to create index {index_config['name']}: {e}")
                conn.rollback()
        
        logger.info(f"✅ Applied {applied_count} indexes, skipped {skipped_count} existing")
    
    engine.dispose()


def analyze_database(connection_string: str):
    """
    Run ANALYZE on all tables to update statistics
    Helps query planner make better decisions
    """
    engine = create_optimized_engine(connection_string)
    
    logger.info("📊 Analyzing database tables...")
    
    with engine.connect() as conn:
        conn.execute(text("ANALYZE"))
        conn.commit()
    
    logger.info("✅ Database analysis complete")
    engine.dispose()


def vacuum_database(connection_string: str):
    """
    Run VACUUM on database to reclaim storage and improve performance
    Should be run during low-traffic periods
    """
    engine = create_optimized_engine(connection_string)
    
    logger.info("🧹 Vacuuming database...")
    
    with engine.connect() as conn:
        # VACUUM cannot run inside a transaction
        conn.execute(text("COMMIT"))
        conn.execute(text("VACUUM ANALYZE"))
    
    logger.info("✅ Database vacuum complete")
    engine.dispose()


def get_slow_queries(connection_string: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get slowest queries from pg_stat_statements
    Requires pg_stat_statements extension
    """
    engine = create_optimized_engine(connection_string)
    
    query = text("""
        SELECT 
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            max_exec_time,
            rows
        FROM pg_stat_statements
        ORDER BY mean_exec_time DESC
        LIMIT :limit
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'limit': limit})
        slow_queries = [dict(row) for row in result]
    
    engine.dispose()
    return slow_queries


def get_table_sizes(connection_string: str) -> List[Dict[str, Any]]:
    """Get size of each table for storage optimization"""
    engine = create_optimized_engine(connection_string)
    
    query = text("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        tables = [dict(row) for row in result]
    
    engine.dispose()
    return tables


def get_index_usage(connection_string: str) -> List[Dict[str, Any]]:
    """Get index usage statistics to identify unused indexes"""
    engine = create_optimized_engine(connection_string)
    
    query = text("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        indexes = [dict(row) for row in result]
    
    engine.dispose()
    return indexes


# Query optimization hints
QUERY_OPTIMIZATION_TIPS = """
Production Database Optimization Tips:

1. Use Indexes:
   - Add indexes on frequently queried columns
   - Use composite indexes for multi-column queries
   - Don't over-index (slows down writes)

2. Query Patterns:
   - Use LIMIT for pagination
   - Avoid SELECT * (specify columns)
   - Use JOINs instead of multiple queries
   - Use WHERE conditions before JOINs

3. Connection Pooling:
   - Reuse connections (don't open/close frequently)
   - Set appropriate pool size (typically 10-20)
   - Use pool_pre_ping to handle stale connections

4. Caching:
   - Cache frequently accessed data (Redis)
   - Set appropriate TTLs
   - Invalidate cache on updates

5. Monitoring:
   - Track slow queries (>100ms)
   - Monitor connection pool usage
   - Watch for N+1 query problems
   - Use EXPLAIN ANALYZE for complex queries

6. Maintenance:
   - Run VACUUM ANALYZE regularly
   - Update table statistics
   - Remove unused indexes
   - Archive old data

7. Cost Optimization:
   - Use read replicas for reporting
   - Compress large columns
   - Archive historical data
   - Use appropriate data types (INT vs BIGINT)
"""

