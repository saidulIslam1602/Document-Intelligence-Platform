#!/usr/bin/env python3
"""
Test script to verify the Document Intelligence Platform works correctly
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

def test_environment():
    """Test environment setup"""
    print("🔧 Testing Environment Setup...")
    
    # Load environment
    load_dotenv("local.env")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in local.env")
        return False
    
    if not api_key.startswith("sk-"):
        print("❌ Invalid OpenAI API key format")
        return False
    
    print(f"✅ OpenAI API key loaded: {api_key[:20]}...")
    return True

def test_imports():
    """Test all imports work correctly"""
    print("\n📦 Testing Imports...")
    
    try:
        # Test basic imports
        import openai
        import fastapi
        import uvicorn
        print("✅ Basic dependencies imported")
        
        # Test OpenAI client
        from dotenv import load_dotenv
        load_dotenv("local.env")
        api_key = os.getenv("OPENAI_API_KEY")
        
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        
        # Test dashboard import
        sys.path.append('src')
        from web.dashboard import app
        print("✅ Dashboard app imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI Connection...")
    
    try:
        import openai
        from dotenv import load_dotenv
        load_dotenv("local.env")
        api_key = os.getenv("OPENAI_API_KEY")
        
        client = openai.OpenAI(api_key=api_key)
        
        # Test with a simple request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, this is a test."}],
            max_tokens=10
        )
        
        print("✅ OpenAI API connection successful")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        return False

def test_dashboard_functionality():
    """Test dashboard basic functionality"""
    print("\n🌐 Testing Dashboard Functionality...")
    
    try:
        sys.path.append('src')
        from web.dashboard import app, ai_service
        
        # Test AI service initialization
        if hasattr(ai_service, 'openai_client'):
            print("✅ AI service initialized")
        else:
            print("❌ AI service not properly initialized")
            return False
        
        # Test app routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/api/documents/upload", "/api/analytics", "/api/health"]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Document Intelligence Platform - Debug Test Suite")
    print("=" * 60)
    
    tests = [
        test_environment,
        test_imports,
        test_openai_connection,
        test_dashboard_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print("🛑 Test failed, stopping...")
            break
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Platform is ready to launch!")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)