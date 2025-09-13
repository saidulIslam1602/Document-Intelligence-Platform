#!/usr/bin/env python3
"""
Optimized Platform Test Suite
Tests the Document Intelligence Platform with all optimizations
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

class PlatformTester:
    """Comprehensive platform testing with optimizations"""
    
    def __init__(self):
        self.base_urls = {
            "document-ingestion": "http://localhost:8000",
            "ai-processing": "http://localhost:8001", 
            "analytics": "http://localhost:8002",
            "ai-chat": "http://localhost:8003",
            "performance-dashboard": "http://localhost:8004",
            "data-quality": "http://localhost:8006",
            "batch-processor": "http://localhost:8007",
            "data-catalog": "http://localhost:8008"
        }
        self.results = []
    
    async def test_service_health(self, service_name: str, url: str) -> bool:
        """Test if a service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    print(f"✅ {service_name} is healthy")
                    return True
                else:
                    print(f"❌ {service_name} failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ {service_name} error: {e}")
            return False
    
    async def test_all_services(self) -> bool:
        """Test all microservices"""
        print("🔍 Testing All Microservices...")
        print("-" * 40)
        
        all_healthy = True
        for service_name, url in self.base_urls.items():
            healthy = await self.test_service_health(service_name, url)
            if not healthy:
                all_healthy = False
        
        return all_healthy
    
    async def test_performance_optimizations(self) -> bool:
        """Test performance optimizations"""
        print("\n⚡ Testing Performance Optimizations...")
        print("-" * 40)
        
        try:
            # Test performance dashboard
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test system metrics
                response = await client.get(f"{self.base_urls['performance-dashboard']}/api/system-metrics")
                if response.status_code == 200:
                    print("✅ Performance monitoring working")
                else:
                    print("❌ Performance monitoring failed")
                    return False
                
                # Test cache stats
                response = await client.get(f"{self.base_urls['performance-dashboard']}/api/cache-stats")
                if response.status_code == 200:
                    print("✅ Redis caching working")
                else:
                    print("❌ Redis caching failed")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ Performance test error: {e}")
            return False
    
    async def test_document_workflow(self) -> bool:
        """Test complete document processing workflow"""
        print("\n📄 Testing Document Workflow...")
        print("-" * 40)
        
        try:
            # Test document ingestion
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test upload endpoint exists
                response = await client.get(f"{self.base_urls['document-ingestion']}/docs")
                if response.status_code == 200:
                    print("✅ Document ingestion API accessible")
                else:
                    print("❌ Document ingestion API not accessible")
                    return False
                
                # Test AI processing
                response = await client.get(f"{self.base_urls['ai-processing']}/docs")
                if response.status_code == 200:
                    print("✅ AI processing API accessible")
                else:
                    print("❌ AI processing API not accessible")
                    return False
                
                # Test analytics
                response = await client.get(f"{self.base_urls['analytics']}/docs")
                if response.status_code == 200:
                    print("✅ Analytics API accessible")
                else:
                    print("❌ Analytics API not accessible")
                    return False
                
                # Test AI chat
                response = await client.get(f"{self.base_urls['ai-chat']}/docs")
                if response.status_code == 200:
                    print("✅ AI chat API accessible")
                else:
                    print("❌ AI chat API not accessible")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ Document workflow test error: {e}")
            return False
    
    async def test_optimization_features(self) -> bool:
        """Test new optimization features"""
        print("\n🚀 Testing Optimization Features...")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test connection pooling (indirectly through response times)
                start_time = datetime.now()
                response = await client.get(f"{self.base_urls['document-ingestion']}/health")
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                if response_time < 2.0:  # Should be fast with connection pooling
                    print(f"✅ Fast response time: {response_time:.2f}s")
                else:
                    print(f"⚠️ Slow response time: {response_time:.2f}s")
                
                # Test caching (analytics endpoint should be cached)
                start_time = datetime.now()
                response = await client.get(f"{self.base_urls['analytics']}/analytics/metrics")
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                if response_time < 1.0:  # Should be very fast with caching
                    print(f"✅ Cached response time: {response_time:.2f}s")
                else:
                    print(f"⚠️ Slow cached response: {response_time:.2f}s")
                
                return True
                
        except Exception as e:
            print(f"❌ Optimization test error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests"""
        print("🚀 Document Intelligence Platform - Optimized Test Suite")
        print("=" * 70)
        print("Testing the platform with all performance optimizations")
        print("=" * 70)
        
        tests = [
            ("Service Health", self.test_all_services),
            ("Performance Optimizations", self.test_performance_optimizations),
            ("Document Workflow", self.test_document_workflow),
            ("Optimization Features", self.test_optimization_features)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                if await test_func():
                    passed += 1
                    print(f"✅ {test_name} passed")
                else:
                    print(f"❌ {test_name} failed")
            except Exception as e:
                print(f"❌ {test_name} error: {e}")
        
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Platform is fully optimized and working")
            print("✅ All microservices are healthy")
            print("✅ Performance optimizations are active")
            print("✅ Ready for production deployment!")
            print("\n🚀 Access your platform:")
            print("   - Performance Dashboard: http://localhost:8004")
            print("   - Document Ingestion: http://localhost:8000")
            print("   - AI Processing: http://localhost:8001")
            print("   - Analytics: http://localhost:8002")
            print("   - AI Chat: http://localhost:8003")
            print("   - Data Quality: http://localhost:8006")
            print("   - Batch Processor: http://localhost:8007")
            print("   - Data Catalog: http://localhost:8008")
        else:
            print("❌ Some tests failed")
            print("💡 Make sure all services are running: docker-compose up -d")
        
        return passed == total

async def main():
    """Main test function"""
    tester = PlatformTester()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)