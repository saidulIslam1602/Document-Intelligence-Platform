#!/usr/bin/env python3
"""
Test script to verify API endpoints
Run this to test the microservices locally
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

async def test_document_ingestion_api():
    """Test document ingestion API"""
    print("📤 Testing Document Ingestion API...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8001/health")
            if response.status_code == 200:
                print("✅ Document Ingestion API is running")
                return True
            else:
                print(f"❌ Document Ingestion API failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Document Ingestion API error: {e}")
        return False

async def test_ai_processing_api():
    """Test AI processing API"""
    print("🤖 Testing AI Processing API...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8002/health")
            if response.status_code == 200:
                print("✅ AI Processing API is running")
                return True
            else:
                print(f"❌ AI Processing API failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ AI Processing API error: {e}")
        return False

async def test_analytics_api():
    """Test analytics API"""
    print("📊 Testing Analytics API...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8003/health")
            if response.status_code == 200:
                print("✅ Analytics API is running")
                return True
            else:
                print(f"❌ Analytics API failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Analytics API error: {e}")
        return False

async def test_api_gateway():
    """Test API Gateway"""
    print("🚪 Testing API Gateway...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ API Gateway is running")
                return True
            else:
                print(f"❌ API Gateway failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ API Gateway error: {e}")
        return False

async def run_api_tests():
    """Run all API tests"""
    print("🧪 API Endpoint Tests")
    print("=" * 40)
    
    tests = [
        test_api_gateway,
        test_document_ingestion_api,
        test_ai_processing_api,
        test_analytics_api
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 API Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All APIs are working correctly!")
    else:
        print("⚠️ Some APIs need attention")
        print("💡 Make sure to start the services with: docker-compose up -d")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_api_tests())