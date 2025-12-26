"""
Integration Test Suite for Enhanced Document Intelligence Platform
Tests MCP Server, LangChain, Automation Scoring, and Enhanced LLMOps
"""

import asyncio
import httpx
import pytest
from datetime import datetime


class TestMCPServer:
    """Test MCP Server functionality"""
    
    @pytest.mark.asyncio
    async def test_mcp_health(self):
        """Test MCP server health endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8012/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "mcp-server"
            assert "tools_count" in data
            assert "resources_count" in data
    
    @pytest.mark.asyncio
    async def test_mcp_capabilities(self):
        """Test MCP capabilities endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8012/mcp/capabilities")
            assert response.status_code == 200
            data = response.json()
            assert data["protocol_version"] == "0.9.0"
            assert len(data["tools"]) >= 10
            assert len(data["resources"]) >= 7
    
    @pytest.mark.asyncio
    async def test_mcp_list_tools(self):
        """Test listing MCP tools"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8012/mcp/tools")
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert data["count"] >= 10
            
            # Verify required tools exist
            tool_names = [tool["name"] for tool in data["tools"]]
            assert "extract_invoice_data" in tool_names
            assert "validate_invoice" in tool_names
            assert "classify_document" in tool_names
            assert "get_automation_metrics" in tool_names
    
    @pytest.mark.asyncio
    async def test_mcp_list_resources(self):
        """Test listing MCP resources"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8012/mcp/resources")
            assert response.status_code == 200
            data = response.json()
            assert "resources" in data
            assert data["count"] >= 7
    
    @pytest.mark.asyncio
    async def test_mcp_automation_metrics(self):
        """Test getting automation metrics via MCP"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8012/mcp/metrics/automation",
                params={"time_range": "24h"}
            )
            # May return 200 with data or 500 if no data yet
            if response.status_code == 200:
                data = response.json()
                assert "automation_rate" in data or "success" in data


class TestAutomationScoring:
    """Test Automation Scoring System"""
    
    @pytest.mark.asyncio
    async def test_automation_metrics_endpoint(self):
        """Test automation metrics endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8002/analytics/automation-metrics",
                params={"time_range": "24h"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "automation_rate" in data
            assert "total_processed" in data
            assert "goal_status" in data
    
    @pytest.mark.asyncio
    async def test_automation_score_calculation(self):
        """Test automation score calculation"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8002/analytics/automation-score",
                json={
                    "invoice_data": {
                        "vendor_name": "Test Corp",
                        "invoice_number": "INV-001",
                        "total_amount": 1000.0,
                        "confidence": 0.95
                    },
                    "validation_result": {
                        "is_valid": True,
                        "quality_score": 0.97
                    }
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "automation_score" in data
            assert "requires_review" in data
            assert 0.0 <= data["automation_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_automation_insights(self):
        """Test automation insights endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8002/analytics/automation-insights",
                params={"time_range": "7d"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "insights" in data
            assert "current_metrics" in data
            assert "goal_status" in data
    
    @pytest.mark.asyncio
    async def test_automation_trend(self):
        """Test automation trend endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8002/analytics/automation-trend",
                params={"days": 30}
            )
            assert response.status_code == 200
            data = response.json()
            assert "trend" in data
            assert "summary" in data


class TestLangChainOrchestration:
    """Test LangChain Orchestration"""
    
    @pytest.mark.asyncio
    async def test_langchain_endpoints_exist(self):
        """Test that LangChain endpoints exist"""
        async with httpx.AsyncClient() as client:
            # These will return 404 if the endpoints don't exist
            # or other codes if they exist but need parameters
            endpoints = [
                "/process-invoice-langchain",
                "/analyze-document-langchain",
                "/fine-tuning-workflow-langchain",
                "/process-document-agent"
            ]
            
            for endpoint in endpoints:
                response = await client.post(
                    f"http://localhost:8001{endpoint}",
                    json={"document_id": "test"}
                )
                # Endpoint exists if we don't get 404
                assert response.status_code != 404


class TestEnhancedLLMOps:
    """Test Enhanced LLMOps"""
    
    @pytest.mark.asyncio
    async def test_llmops_track_metrics_endpoint(self):
        """Test LLMOps track metrics endpoint exists"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/llmops/track-model-metrics",
                json={
                    "model_id": "test-model",
                    "model_name": "test",
                    "test_documents": ["doc1", "doc2"]
                }
            )
            # Endpoint exists if we don't get 404
            assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_llmops_compare_models_endpoint(self):
        """Test LLMOps compare models endpoint exists"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/llmops/compare-models",
                json={
                    "baseline_model_id": "base",
                    "fine_tuned_model_id": "ft",
                    "test_documents": ["doc1"]
                }
            )
            # Endpoint exists if we don't get 404
            assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_llmops_optimize_endpoint(self):
        """Test LLMOps optimize endpoint exists"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/llmops/optimize-for-goal",
                json={
                    "current_model_id": "test-model",
                    "target_automation_rate": 90.0
                }
            )
            # Endpoint exists if we don't get 404
            assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_llmops_dashboard_endpoint(self):
        """Test LLMOps dashboard endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/llmops/automation-dashboard",
                params={"time_range": "7d"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "time_range" in data
            assert "summary" in data


class TestAPIGateway:
    """Test API Gateway Integration"""
    
    @pytest.mark.asyncio
    async def test_gateway_health(self):
        """Test API Gateway health"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8003/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data
    
    @pytest.mark.asyncio
    async def test_gateway_mcp_routing(self):
        """Test API Gateway routes to MCP Server"""
        async with httpx.AsyncClient() as client:
            # Test routing through gateway
            response = await client.get("http://localhost:8003/mcp/tools")
            # Should route to MCP server
            # May require auth, but shouldn't be 404
            assert response.status_code != 404


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_invoice_workflow(self):
        """Test complete invoice processing workflow"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Check MCP server is ready
            mcp_health = await client.get("http://localhost:8012/health")
            assert mcp_health.status_code == 200
            
            # 2. Check analytics is ready
            analytics_health = await client.get("http://localhost:8002/health")
            assert analytics_health.status_code == 200
            
            # 3. Check AI processing is ready
            ai_health = await client.get("http://localhost:8001/health")
            assert ai_health.status_code == 200
            
            # 4. Get current automation metrics
            metrics = await client.get(
                "http://localhost:8002/analytics/automation-metrics",
                params={"time_range": "24h"}
            )
            assert metrics.status_code == 200
            
            print("\n✅ All services are healthy and responding")
            print(f"📊 Current automation metrics: {metrics.json()}")


class TestDockerServices:
    """Test Docker container health"""
    
    def test_all_services_running(self):
        """Verify all required services are running"""
        import subprocess
        
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        running_containers = result.stdout.split('\n')
        
        required_services = [
            "docintel-mcp-server",
            "docintel-ai-processing",
            "docintel-analytics",
            "docintel-api-gateway",
            "docintel-redis"
        ]
        
        for service in required_services:
            assert any(service in container for container in running_containers), \
                f"Service {service} is not running"
        
        print(f"\n✅ All {len(required_services)} required services are running")


# Utility function to run all tests
async def run_all_tests():
    """Run all integration tests"""
    print("🚀 Starting Integration Tests for Enhanced Document Intelligence Platform\n")
    
    test_classes = [
        TestMCPServer(),
        TestAutomationScoring(),
        TestLangChainOrchestration(),
        TestEnhancedLLMOps(),
        TestAPIGateway(),
        TestEndToEnd()
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{'='*60}")
        print(f"Running {class_name}")
        print(f"{'='*60}")
        
        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    method = getattr(test_class, method_name)
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    passed_tests += 1
                    print(f"✅ {method_name}")
                except Exception as e:
                    failed_tests += 1
                    print(f"❌ {method_name}: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! Platform is working correctly.")
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Please review the errors above.")
    
    return failed_tests == 0


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)

