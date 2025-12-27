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
