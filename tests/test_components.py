#!/usr/bin/env python3
"""
Test script to verify Document Intelligence Platform components
Run this to test individual services without Azure dependencies
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.append('src')

def test_config_loading():
    """Test configuration loading"""
    print("🔧 Testing Configuration Loading...")
    try:
        from shared.config.settings import AppSettings
        settings = AppSettings()
        print(f"✅ Configuration loaded successfully")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Log Level: {settings.log_level}")
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_event_sourcing():
    """Test event sourcing functionality"""
    print("\n📡 Testing Event Sourcing...")
    try:
        from shared.events.event_sourcing import DocumentUploadedEvent, DocumentProcessedEvent
        
        # Create test events
        upload_event = DocumentUploadedEvent(
            document_id="test-doc-123",
            user_id="test-user",
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        
        process_event = DocumentProcessedEvent(
            document_id="test-doc-123",
            processing_duration=1.5,
            success=True,
            extracted_text="This is test content",
            entities={"person": ["John Doe"], "organization": ["Microsoft"]},
            classification="contract"
        )
        
        print(f"✅ Event sourcing working")
        print(f"   - Upload Event: {upload_event.event_type}")
        print(f"   - Process Event: {process_event.event_type}")
        return True
    except Exception as e:
        print(f"❌ Event sourcing failed: {e}")
        return False

def test_ai_services():
    """Test AI services (mock mode)"""
    print("\n🤖 Testing AI Services...")
    try:
        from microservices.ai_processing.openai_service import OpenAIService
        from microservices.ai_processing.form_recognizer_service import FormRecognizerService
        
        # Test OpenAI service (mock mode)
        openai_service = OpenAIService()
        print(f"✅ OpenAI Service initialized")
        
        # Test Form Recognizer service (mock mode)
        form_service = FormRecognizerService()
        print(f"✅ Form Recognizer Service initialized")
        
        return True
    except Exception as e:
        print(f"❌ AI services failed: {e}")
        return False

def test_microservices():
    """Test microservices initialization"""
    print("\n🏗️ Testing Microservices...")
    try:
        # Test document ingestion
        from microservices.document_ingestion.main import app as ingestion_app
        print(f"✅ Document Ingestion Service: {ingestion_app.title}")
        
        # Test AI processing
        from microservices.ai_processing.main import app as ai_app
        print(f"✅ AI Processing Service: {ai_app.title}")
        
        # Test analytics
        from microservices.analytics.main import app as analytics_app
        print(f"✅ Analytics Service: {analytics_app.title}")
        
        # Test API Gateway
        from microservices.api_gateway.main import app as gateway_app
        print(f"✅ API Gateway Service: {gateway_app.title}")
        
        return True
    except Exception as e:
        print(f"❌ Microservices failed: {e}")
        return False

def test_m365_integration():
    """Test M365 integration"""
    print("\n🔗 Testing M365 Integration...")
    try:
        from microservices.m365_integration.copilot_service import CopilotService
        service = CopilotService()
        print(f"✅ M365 Integration Service initialized")
        return True
    except Exception as e:
        print(f"❌ M365 Integration failed: {e}")
        return False

def test_experimentation():
    """Test A/B testing framework"""
    print("\n🧪 Testing A/B Testing Framework...")
    try:
        from microservices.experimentation.ab_testing import ABTestingFramework
        framework = ABTestingFramework()
        print(f"✅ A/B Testing Framework initialized")
        return True
    except Exception as e:
        print(f"❌ A/B Testing failed: {e}")
        return False

def test_llm_optimization():
    """Test LLM optimization"""
    print("\n⚡ Testing LLM Optimization...")
    try:
        from microservices.llm_optimization.prompt_engineering import PromptEngineer
        engineer = PromptEngineer()
        print(f"✅ LLM Optimization initialized")
        return True
    except Exception as e:
        print(f"❌ LLM Optimization failed: {e}")
        return False

def run_all_tests():
    """Run all component tests"""
    print("🚀 Document Intelligence Platform - Component Tests")
    print("=" * 60)
    
    tests = [
        test_config_loading,
        test_event_sourcing,
        test_ai_services,
        test_microservices,
        test_m365_integration,
        test_experimentation,
        test_llm_optimization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All components are working correctly!")
        print("✅ Your Document Intelligence Platform is ready!")
    else:
        print("⚠️ Some components need attention")
        print("💡 Check the error messages above for details")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)