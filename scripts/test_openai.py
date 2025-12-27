#!/usr/bin/env python3
"""
Test OpenAI Integration
Verifies that OpenAI API key works correctly
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv('.env.local')

from openai import OpenAI

def test_openai_connection():
    """Test OpenAI API connection"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    print("Testing OpenAI Integration")
    print("=" * 50)
    print(f"API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")
    print(f"Using Mock Services: {os.getenv('USE_MOCK_SERVICES', 'false')}")
    print()
    
    if not api_key or not api_key.startswith('sk-'):
        print("ERROR: No valid OpenAI API key found")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
        print()
        
        # Test chat completion
        print("Testing chat completion...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for document processing."},
                {"role": "user", "content": "Extract the key information from this invoice: Invoice #12345, Vendor: Acme Corp, Amount: $1,500, Date: 2024-01-15"}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        print("SUCCESS: OpenAI API is working!")
        print()
        print("Response:")
        print("-" * 50)
        print(response.choices[0].message.content)
        print("-" * 50)
        print()
        print(f"Model: {response.model}")
        print(f"Tokens used: {response.usage.total_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print()
        
        return True
        
    except Exception as e:
        print(f"ERROR: OpenAI API call failed")
        print(f"Error: {str(e)}")
        return False

def test_mock_services():
    """Test mock OpenAI services"""
    print()
    print("Testing Mock Services")
    print("=" * 50)
    
    try:
        from src.shared.mocks.azure_mocks import MockOpenAI
        
        mock = MockOpenAI()
        response = mock.chat_completion([
            {"role": "user", "content": "What is this invoice about?"}
        ])
        
        print("Mock response:")
        print(response['choices'][0]['message']['content'])
        print()
        return True
    except Exception as e:
        print(f"ERROR: Mock services failed: {e}")
        return False

if __name__ == "__main__":
    print()
    print("╔═══════════════════════════════════════════════╗")
    print("║   OpenAI Integration Test Suite              ║")
    print("╚═══════════════════════════════════════════════╝")
    print()
    
    # Test real OpenAI
    openai_works = test_openai_connection()
    
    # Test mock services
    mock_works = test_mock_services()
    
    # Summary
    print()
    print("╔═══════════════════════════════════════════════╗")
    print("║   Test Results Summary                        ║")
    print("╚═══════════════════════════════════════════════╝")
    print()
    print(f"✓ Real OpenAI API:  {'WORKING' if openai_works else 'FAILED'}")
    print(f"✓ Mock Services:    {'WORKING' if mock_works else 'FAILED'}")
    print()
    
    if openai_works:
        print("✅ Your OpenAI integration is ready!")
        print("   Services will use real AI intelligence.")
    else:
        print("⚠️  OpenAI API not working. Services will use mocks.")
    
    print()
    sys.exit(0 if openai_works or mock_works else 1)

