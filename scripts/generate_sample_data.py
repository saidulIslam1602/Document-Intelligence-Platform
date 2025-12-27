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
