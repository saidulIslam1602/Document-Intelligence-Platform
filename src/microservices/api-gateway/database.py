"""
Database service for API Gateway - PostgreSQL integration
Stores documents and extracted data with industry-standard schema
"""
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)

class DocumentDatabase:
    """PostgreSQL database service for document management"""
    
    def __init__(self):
        """Initialize database connection"""
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5434')),
            'database': os.getenv('POSTGRES_DB', 'documentintelligence'),
            'user': os.getenv('POSTGRES_USER', 'admin'),
            'password': os.getenv('POSTGRES_PASSWORD', 'admin123')
        }
        self._init_tables()
    
    def get_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _init_tables(self):
        """Initialize database tables with industry-standard schema"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(50) PRIMARY KEY,
                    filename VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50),
                    document_type VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    user_id VARCHAR(100),
                    confidence_score DECIMAL(5,4)
                )
            """)
            
            # Invoice extraction table (industry standard)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoice_extractions (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(50) REFERENCES documents(id) ON DELETE CASCADE,
                    
                    -- Core Invoice Fields
                    invoice_number VARCHAR(100),
                    invoice_date DATE,
                    due_date DATE,
                    purchase_order_number VARCHAR(100),
                    
                    -- Vendor Information
                    vendor_name VARCHAR(500),
                    vendor_address TEXT,
                    vendor_tax_id VARCHAR(100),
                    vendor_email VARCHAR(200),
                    vendor_phone VARCHAR(50),
                    
                    -- Customer/Buyer Information
                    customer_name VARCHAR(500),
                    customer_address TEXT,
                    customer_tax_id VARCHAR(100),
                    
                    -- Financial Details
                    currency_code VARCHAR(10) DEFAULT 'USD',
                    subtotal DECIMAL(15,2),
                    tax_amount DECIMAL(15,2),
                    discount_amount DECIMAL(15,2),
                    shipping_amount DECIMAL(15,2),
                    total_amount DECIMAL(15,2) NOT NULL,
                    amount_paid DECIMAL(15,2),
                    balance_due DECIMAL(15,2),
                    
                    -- Tax Details
                    tax_rate DECIMAL(5,2),
                    tax_type VARCHAR(50),
                    
                    -- Payment Terms
                    payment_terms VARCHAR(200),
                    payment_method VARCHAR(100),
                    
                    -- Banking Details
                    bank_account_number VARCHAR(100),
                    bank_routing_number VARCHAR(100),
                    bank_name VARCHAR(200),
                    
                    -- Line Items (stored as JSON for flexibility)
                    line_items JSONB,
                    
                    -- Metadata
                    notes TEXT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence_score DECIMAL(5,4),
                    
                    UNIQUE(document_id)
                )
            """)
            
            # Document entities table (for NER - Named Entity Recognition)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_entities (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(50) REFERENCES documents(id) ON DELETE CASCADE,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_value TEXT NOT NULL,
                    confidence_score DECIMAL(5,4),
                    start_position INTEGER,
                    end_position INTEGER,
                    page_number INTEGER,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
                CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents(uploaded_at DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
                CREATE INDEX IF NOT EXISTS idx_invoice_invoice_date ON invoice_extractions(invoice_date);
                CREATE INDEX IF NOT EXISTS idx_invoice_vendor_name ON invoice_extractions(vendor_name);
                CREATE INDEX IF NOT EXISTS idx_invoice_total_amount ON invoice_extractions(total_amount);
                CREATE INDEX IF NOT EXISTS idx_entities_document_id ON document_entities(document_id);
                CREATE INDEX IF NOT EXISTS idx_entities_type ON document_entities(entity_type);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            raise
    
    def insert_document(self, document_data: Dict[str, Any]) -> bool:
        """Insert a new document"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO documents 
                (id, filename, file_type, document_type, status, file_size, user_id, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                document_data['id'],
                document_data['filename'],
                document_data.get('file_type', 'unknown'),
                document_data.get('document_type', 'invoice'),
                document_data.get('status', 'processed'),
                document_data.get('file_size', 0),
                document_data.get('user_id', 'demo1234'),
                document_data.get('confidence_score', 0.85)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            return False
    
    def insert_invoice_extraction(self, extraction_data: Dict[str, Any]) -> bool:
        """Insert invoice extraction data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO invoice_extractions 
                (document_id, invoice_number, invoice_date, due_date, purchase_order_number,
                 vendor_name, vendor_address, vendor_tax_id, vendor_email, vendor_phone,
                 customer_name, customer_address, customer_tax_id,
                 currency_code, subtotal, tax_amount, discount_amount, shipping_amount,
                 total_amount, amount_paid, balance_due, tax_rate, tax_type,
                 payment_terms, payment_method, bank_account_number, bank_routing_number,
                 bank_name, line_items, notes, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET
                    invoice_number = EXCLUDED.invoice_number,
                    total_amount = EXCLUDED.total_amount
            """, (
                extraction_data['document_id'],
                extraction_data.get('invoice_number'),
                extraction_data.get('invoice_date'),
                extraction_data.get('due_date'),
                extraction_data.get('purchase_order_number'),
                extraction_data.get('vendor_name'),
                extraction_data.get('vendor_address'),
                extraction_data.get('vendor_tax_id'),
                extraction_data.get('vendor_email'),
                extraction_data.get('vendor_phone'),
                extraction_data.get('customer_name'),
                extraction_data.get('customer_address'),
                extraction_data.get('customer_tax_id'),
                extraction_data.get('currency_code', 'USD'),
                extraction_data.get('subtotal'),
                extraction_data.get('tax_amount'),
                extraction_data.get('discount_amount'),
                extraction_data.get('shipping_amount'),
                extraction_data.get('total_amount'),
                extraction_data.get('amount_paid'),
                extraction_data.get('balance_due'),
                extraction_data.get('tax_rate'),
                extraction_data.get('tax_type'),
                extraction_data.get('payment_terms'),
                extraction_data.get('payment_method'),
                extraction_data.get('bank_account_number'),
                extraction_data.get('bank_routing_number'),
                extraction_data.get('bank_name'),
                json.dumps(extraction_data.get('line_items', [])),
                extraction_data.get('notes'),
                extraction_data.get('confidence_score', 0.85)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to insert invoice extraction: {e}")
            return False
    
    def get_documents(self, limit: int = 100, offset: int = 0, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of documents"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT id, filename, file_type, document_type, status, file_size, 
                       uploaded_at, processed_at, confidence_score
                FROM documents
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY uploaded_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            documents = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convert to list of dicts
            return [dict(doc) for doc in documents]
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
    def get_document_count(self, user_id: Optional[str] = None) -> int:
        """Get total document count"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM documents WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    def get_document_with_extraction(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document with full invoice extraction data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    d.*,
                    i.invoice_number, i.invoice_date, i.due_date, i.purchase_order_number,
                    i.vendor_name, i.vendor_address, i.vendor_tax_id, i.vendor_email, i.vendor_phone,
                    i.customer_name, i.customer_address, i.customer_tax_id,
                    i.currency_code, i.subtotal, i.tax_amount, i.discount_amount, i.shipping_amount,
                    i.total_amount, i.amount_paid, i.balance_due, i.tax_rate, i.tax_type,
                    i.payment_terms, i.payment_method, i.bank_account_number, i.bank_routing_number,
                    i.bank_name, i.line_items, i.notes
                FROM documents d
                LEFT JOIN invoice_extractions i ON d.id = i.document_id
                WHERE d.id = %s
            """, (document_id,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get document with extraction: {e}")
            return None
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary for dashboard"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_count,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
                    COUNT(CASE WHEN DATE(uploaded_at) = CURRENT_DATE THEN 1 END) as uploaded_today,
                    AVG(confidence_score) as avg_confidence
                FROM documents
            """)
            
            summary = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    SUM(total_amount) as total_invoice_amount,
                    AVG(total_amount) as avg_invoice_amount,
                    COUNT(*) as invoice_count
                FROM invoice_extractions
            """)
            
            invoice_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                **dict(summary),
                **dict(invoice_stats)
            }
        except Exception as e:
            logger.error(f"Failed to get analytics summary: {e}")
            return {}

# Global database instance
db = DocumentDatabase()

