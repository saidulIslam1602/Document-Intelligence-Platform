#!/bin/bash

# Local Development Setup Script
# Sets up the project for local demonstration without Azure services

set -e

echo "Setting up local development environment..."
echo "============================================"

# Create local environment file
cat > .env.local << 'EOF'
# Local Development Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Local Database
POSTGRES_DB=documentintelligence
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
SQL_CONNECTION_STRING=postgresql://admin:admin123@localhost:5432/documentintelligence

# Local Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=local-dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Mock Azure Services (will use local alternatives)
USE_MOCK_SERVICES=true
FORM_RECOGNIZER_ENDPOINT=http://localhost:8000/mock/form-recognizer
FORM_RECOGNIZER_KEY=mock-key-for-local-dev
COGNITIVE_SEARCH_ENDPOINT=http://localhost:8000/mock/search
COGNITIVE_SEARCH_KEY=mock-key-for-local-dev

# OpenAI - Add your API key here to enable real AI (or leave empty for mocks)
OPENAI_API_KEY=
OPENAI_ENDPOINT=https://api.openai.com/v1
OPENAI_DEPLOYMENT=gpt-3.5-turbo

# Service URLs
DOCUMENT_INGESTION_URL=http://localhost:8000
AI_PROCESSING_URL=http://localhost:8001
ANALYTICS_URL=http://localhost:8002
API_GATEWAY_URL=http://localhost:8003
AI_CHAT_URL=http://localhost:8004
MCP_SERVER_URL=http://localhost:8012

# Performance Settings
PERF_CACHE_TTL=300
PERF_RATE_LIMIT_REQUESTS_PER_SECOND=100
WORKERS=2
EOF

echo "Created .env.local file"

# Create mock services module
mkdir -p src/shared/mocks
cat > src/shared/mocks/__init__.py << 'EOF'
"""Mock services for local development"""

from .azure_mocks import MockFormRecognizer, MockCognitiveSearch, MockOpenAI

__all__ = ['MockFormRecognizer', 'MockCognitiveSearch', 'MockOpenAI']
EOF

cat > src/shared/mocks/azure_mocks.py << 'EOF'
"""
Mock Azure Services for Local Development
Simulates Azure Form Recognizer, Cognitive Search, and OpenAI
"""

import random
from typing import Dict, Any, List
from datetime import datetime


class MockFormRecognizer:
    """Mock Azure Form Recognizer for local testing"""
    
    def analyze_invoice(self, document_content: bytes) -> Dict[str, Any]:
        """Simulate invoice analysis"""
        return {
            "status": "succeeded",
            "document_type": "invoice",
            "confidence": 0.95,
            "fields": {
                "vendor_name": {
                    "value": "Contoso Ltd.",
                    "confidence": 0.98
                },
                "invoice_id": {
                    "value": f"INV-{random.randint(1000, 9999)}",
                    "confidence": 0.99
                },
                "invoice_date": {
                    "value": "2024-01-15",
                    "confidence": 0.97
                },
                "due_date": {
                    "value": "2024-02-15",
                    "confidence": 0.96
                },
                "total_amount": {
                    "value": round(random.uniform(100, 10000), 2),
                    "confidence": 0.99,
                    "currency": "USD"
                },
                "subtotal": {
                    "value": round(random.uniform(90, 9000), 2),
                    "confidence": 0.98
                },
                "tax": {
                    "value": round(random.uniform(10, 1000), 2),
                    "confidence": 0.97
                },
                "line_items": [
                    {
                        "description": "Professional Services",
                        "quantity": 10,
                        "unit_price": 150.0,
                        "amount": 1500.0
                    },
                    {
                        "description": "Consulting Hours",
                        "quantity": 20,
                        "unit_price": 200.0,
                        "amount": 4000.0
                    }
                ]
            },
            "extracted_text": "Sample invoice text extracted from document",
            "page_count": 1
        }
    
    def analyze_receipt(self, document_content: bytes) -> Dict[str, Any]:
        """Simulate receipt analysis"""
        return {
            "status": "succeeded",
            "document_type": "receipt",
            "confidence": 0.93,
            "fields": {
                "merchant_name": {
                    "value": "Local Store",
                    "confidence": 0.96
                },
                "transaction_date": {
                    "value": datetime.now().strftime("%Y-%m-%d"),
                    "confidence": 0.98
                },
                "total": {
                    "value": round(random.uniform(10, 500), 2),
                    "confidence": 0.99
                },
                "items": [
                    {"description": "Item 1", "price": 25.99},
                    {"description": "Item 2", "price": 45.50}
                ]
            }
        }
    
    def analyze_document(self, document_content: bytes, doc_type: str = "general") -> Dict[str, Any]:
        """Simulate general document analysis"""
        return {
            "status": "succeeded",
            "document_type": doc_type,
            "confidence": 0.90,
            "extracted_text": "This is mock extracted text from the document. It contains sample content for testing.",
            "entities": [
                {"type": "person", "text": "John Doe", "confidence": 0.95},
                {"type": "organization", "text": "Acme Corp", "confidence": 0.92},
                {"type": "date", "text": "2024-01-15", "confidence": 0.98}
            ],
            "key_value_pairs": [
                {"key": "Name", "value": "John Doe"},
                {"key": "Date", "value": "2024-01-15"}
            ]
        }


class MockCognitiveSearch:
    """Mock Azure Cognitive Search for local testing"""
    
    def __init__(self):
        self.documents = []
    
    def index_document(self, doc_id: str, content: Dict[str, Any]) -> bool:
        """Simulate document indexing"""
        self.documents.append({
            "id": doc_id,
            "content": content,
            "indexed_at": datetime.now().isoformat()
        })
        return True
    
    def search(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Simulate search"""
        results = []
        for doc in self.documents[:5]:
            results.append({
                "id": doc["id"],
                "score": random.uniform(0.7, 1.0),
                "content": doc["content"],
                "highlights": [f"...{query}..."]
            })
        return results
    
    def get_suggestions(self, query: str) -> List[str]:
        """Simulate search suggestions"""
        return [f"{query} invoice", f"{query} receipt", f"{query} document"]


class MockOpenAI:
    """Mock OpenAI API for local testing"""
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """Simulate chat completion"""
        last_message = messages[-1]["content"] if messages else ""
        
        response_text = f"This is a mock response to: '{last_message[:50]}...'. "
        response_text += "In a production environment with OpenAI API key, this would provide intelligent analysis of your documents."
        
        return {
            "id": f"mock-{random.randint(1000, 9999)}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
        }
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Simulate entity extraction"""
        return [
            {"type": "PERSON", "text": "John Smith", "confidence": 0.95},
            {"type": "ORGANIZATION", "text": "Acme Corporation", "confidence": 0.92},
            {"type": "DATE", "text": "January 15, 2024", "confidence": 0.98},
            {"type": "MONEY", "text": "$1,500.00", "confidence": 0.99}
        ]
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """Simulate document classification"""
        doc_types = ["invoice", "receipt", "contract", "report", "letter"]
        return {
            "type": random.choice(doc_types),
            "confidence": random.uniform(0.85, 0.99)
        }
    
    def summarize(self, text: str) -> str:
        """Simulate text summarization"""
        return "This is a mock summary of the document. It would normally provide a concise overview of the main points."
EOF

# Create sample data generator
cat > scripts/generate_sample_data.py << 'EOF'
#!/usr/bin/env python3
"""Generate sample data for local demonstration"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_sample_documents():
    """Create sample document files"""
    samples_dir = Path("data/samples")
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample invoice data
    invoice_data = {
        "invoice_id": "INV-2024-001",
        "vendor": "Contoso Ltd.",
        "date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": 5500.00,
        "items": [
            {"description": "Professional Services", "quantity": 10, "rate": 150, "amount": 1500},
            {"description": "Consulting Hours", "quantity": 20, "rate": 200, "amount": 4000}
        ]
    }
    
    with open(samples_dir / "sample_invoice.json", "w") as f:
        json.dump(invoice_data, f, indent=2)
    
    # Sample receipt data
    receipt_data = {
        "receipt_id": "REC-2024-001",
        "merchant": "Local Store",
        "date": "2024-01-20",
        "total": 125.50,
        "items": [
            {"item": "Office Supplies", "price": 45.99},
            {"item": "Equipment", "price": 79.51}
        ]
    }
    
    with open(samples_dir / "sample_receipt.json", "w") as f:
        json.dump(receipt_data, f, indent=2)
    
    print(f"Created sample documents in {samples_dir}")

def create_sample_users():
    """Create sample user data"""
    users_dir = Path("data/samples")
    users_dir.mkdir(parents=True, exist_ok=True)
    
    users = [
        {
            "email": "demo@example.com",
            "username": "demo",
            "password": "demo123",
            "role": "admin"
        },
        {
            "email": "user@example.com",
            "username": "user",
            "password": "user123",
            "role": "user"
        }
    ]
    
    with open(users_dir / "sample_users.json", "w") as f:
        json.dump(users, f, indent=2)
    
    print(f"Created sample users: demo@example.com / demo123")

if __name__ == "__main__":
    print("Generating sample data...")
    create_sample_documents()
    create_sample_users()
    print("Sample data generation complete!")
EOF

chmod +x scripts/generate_sample_data.py

# Generate sample data
python3 scripts/generate_sample_data.py

# Create docker-compose for local development
cat > docker-compose.local.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: di-postgres-local
    environment:
      POSTGRES_DB: documentintelligence
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin123
    ports:
      - "5432:5432"
    volumes:
      - postgres-local-data:/var/lib/postgresql/data
    networks:
      - di-local-network

  redis:
    image: redis:7-alpine
    container_name: di-redis-local
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-local-data:/data
    networks:
      - di-local-network

networks:
  di-local-network:
    driver: bridge

volumes:
  postgres-local-data:
  redis-local-data:
EOF

echo ""
echo "============================================"
echo "Local setup complete!"
echo "============================================"
echo ""
echo "Created files:"
echo "  - .env.local (environment configuration)"
echo "  - docker-compose.local.yml (local services)"
echo "  - src/shared/mocks/ (mock Azure services)"
echo "  - data/samples/ (sample documents)"
echo ""
echo "Next steps:"
echo "  1. Start local services: docker-compose -f docker-compose.local.yml up -d"
echo "  2. Export environment: export \$(cat .env.local | grep -v '^#' | xargs)"
echo "  3. Run services with: ./scripts/run_local.sh"
echo ""
echo "Demo credentials:"
echo "  Email: demo@example.com"
echo "  Password: demo123"
echo ""
echo "OpenAI API Key:"
echo "  - Leave empty to use mock responses"
echo "  - Or set in .env.local: OPENAI_API_KEY=your-key-here"
echo ""

