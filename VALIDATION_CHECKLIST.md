# Validation Checklist - Enhanced Document Intelligence Platform

Use this checklist to verify that all new features are working correctly.

## ✅ Pre-Deployment Validation

### 1. Environment Setup
- [ ] `.env` file created with all required variables
- [ ] Azure OpenAI credentials configured
- [ ] Azure Form Recognizer credentials configured
- [ ] Azure SQL Database connection string set
- [ ] Redis connection configured

### 2. Docker Services
```bash
# Check all services are running
docker-compose ps
```

Expected services:
- [ ] `docintel-mcp-server` (Port 8012) - Up
- [ ] `docintel-ai-processing` (Port 8001) - Up
- [ ] `docintel-analytics` (Port 8002) - Up
- [ ] `docintel-api-gateway` (Port 8003) - Up
- [ ] `docintel-document-ingestion` (Port 8000) - Up
- [ ] `docintel-redis` (Port 6379) - Up

## ✅ MCP Server Validation

### Health Check
```bash
curl http://localhost:8012/health
```
- [ ] Status: `healthy`
- [ ] Service: `mcp-server`
- [ ] `tools_count` >= 10
- [ ] `resources_count` >= 7

### MCP Capabilities
```bash
curl http://localhost:8012/mcp/capabilities
```
- [ ] Protocol version: `0.9.0`
- [ ] Tools count >= 10
- [ ] Resources count >= 7
- [ ] Capabilities include: `tools`, `resources`, `logging`

### MCP Tools
```bash
curl http://localhost:8012/mcp/tools
```
Required tools present:
- [ ] `extract_invoice_data`
- [ ] `validate_invoice`
- [ ] `classify_document`
- [ ] `create_fine_tuning_job`
- [ ] `get_automation_metrics`
- [ ] `process_m365_document`
- [ ] `analyze_document_sentiment`
- [ ] `extract_document_entities`
- [ ] `generate_document_summary`
- [ ] `search_documents`

### MCP Resources
```bash
curl http://localhost:8012/mcp/resources
```
Required resources present:
- [ ] `document://{document_id}`
- [ ] `analytics://metrics/{time_range}`
- [ ] `automation://score/{time_range}`
- [ ] `invoice://{document_id}`
- [ ] `fine-tuning://job/{job_id}`
- [ ] `quality://validation/{document_id}`
- [ ] `search://index/{index_name}`

### MCP Tool Execution
```bash
curl -X POST http://localhost:8012/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_automation_metrics",
    "parameters": {"time_range": "24h"}
  }'
```
- [ ] Executes without error (may return empty data if no invoices processed yet)
- [ ] Returns JSON with `success` or `result` field

## ✅ Automation Scoring Validation

### Automation Metrics Endpoint
```bash
curl http://localhost:8002/analytics/automation-metrics?time_range=24h
```
Response should include:
- [ ] `automation_rate` (number)
- [ ] `total_processed` (number)
- [ ] `fully_automated` (number)
- [ ] `requires_review` (number)
- [ ] `average_confidence` (number)
- [ ] `goal_status` (object with `goal`, `is_met`, `message`)

### Automation Score Calculation
```bash
curl -X POST http://localhost:8002/analytics/automation-score \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_data": {
      "vendor_name": "Test Corp",
      "invoice_number": "INV-001",
      "total_amount": 1000.0,
      "invoice_date": "2025-12-26",
      "confidence": 0.95
    },
    "validation_result": {
      "is_valid": true,
      "quality_score": 0.97
    }
  }'
```
- [ ] Returns `automation_score` between 0 and 1
- [ ] Returns `confidence_score`
- [ ] Returns `completeness_score`
- [ ] Returns `requires_review` (boolean)
- [ ] Score is calculated correctly: confidence × completeness × validation

### Automation Insights
```bash
curl http://localhost:8002/analytics/automation-insights?time_range=7d
```
- [ ] Returns `insights` array
- [ ] Returns `current_metrics` object
- [ ] Returns `goal_status` object

### Automation Trend
```bash
curl http://localhost:8002/analytics/automation-trend?days=30
```
- [ ] Returns `trend` array
- [ ] Returns `summary` with `improvement` and `direction`

## ✅ LangChain Orchestration Validation

### AI Processing Service Health
```bash
curl http://localhost:8001/health
```
- [ ] Status: `healthy`
- [ ] Service: `ai-processing`
- [ ] AI services available: `openai`, `form_recognizer`, `ml_models`

### LangChain Endpoints Exist
Test that endpoints exist (will need valid document_id for actual processing):

```bash
# Invoice processing with LangChain
curl -X POST http://localhost:8001/process-invoice-langchain \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test"}'
```
- [ ] Endpoint exists (not 404)

```bash
# Document analysis with LangChain
curl -X POST http://localhost:8001/analyze-document-langchain \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test"}'
```
- [ ] Endpoint exists (not 404)

```bash
# Fine-tuning workflow with LangChain
curl -X POST http://localhost:8001/fine-tuning-workflow-langchain \
  -H "Content-Type: application/json" \
  -d '{
    "training_data_sample": "test",
    "model_type": "gpt-3.5-turbo"
  }'
```
- [ ] Endpoint exists (not 404)

```bash
# Multi-agent processing
curl -X POST http://localhost:8001/process-document-agent \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test",
    "task_description": "Extract and validate invoice data"
  }'
```
- [ ] Endpoint exists (not 404)

## ✅ Enhanced LLMOps Validation

### Track Model Metrics Endpoint
```bash
curl -X POST http://localhost:8001/llmops/track-model-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "test-model",
    "model_name": "test",
    "test_documents": ["doc1", "doc2"]
  }'
```
- [ ] Endpoint exists (not 404)
- [ ] Returns model metrics structure

### Compare Models Endpoint
```bash
curl -X POST http://localhost:8001/llmops/compare-models \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_model_id": "base",
    "fine_tuned_model_id": "ft",
    "test_documents": ["doc1"]
  }'
```
- [ ] Endpoint exists (not 404)
- [ ] Returns comparison structure with `baseline_metrics`, `fine_tuned_metrics`, `improvement`

### Optimize for Goal Endpoint
```bash
curl -X POST http://localhost:8001/llmops/optimize-for-goal \
  -H "Content-Type: application/json" \
  -d '{
    "current_model_id": "test-model",
    "target_automation_rate": 90.0
  }'
```
- [ ] Endpoint exists (not 404)
- [ ] Returns recommendations and fine-tuning plan

### Automation Dashboard Endpoint
```bash
curl http://localhost:8001/llmops/automation-dashboard?time_range=7d
```
- [ ] Returns dashboard data with `trends` and `summary`

## ✅ API Gateway Integration Validation

### Gateway Health
```bash
curl http://localhost:8003/health
```
- [ ] Status: `healthy`
- [ ] Services health includes: `document-ingestion`, `ai-processing`, `analytics`, `mcp-server`

### Gateway Routes to MCP
```bash
curl http://localhost:8003/mcp/tools
```
- [ ] Routes correctly to MCP Server
- [ ] Returns list of tools

### Gateway Routes to Analytics
```bash
curl http://localhost:8003/analytics/automation-metrics?time_range=24h
```
- [ ] Routes correctly to Analytics Service
- [ ] Returns automation metrics

### Gateway Routes to LLMOps
```bash
curl http://localhost:8003/llmops/automation-dashboard?time_range=7d
```
- [ ] Routes correctly to AI Processing Service
- [ ] Returns dashboard data

## ✅ Database Validation

### Automation Scores Table
```sql
-- Connect to SQL Database and verify table exists
SELECT COUNT(*) FROM automation_scores;
```
- [ ] Table `automation_scores` exists
- [ ] Columns: `id`, `document_id`, `confidence_score`, `completeness_score`, `validation_pass`, `automation_score`, `requires_review`, `created_at`
- [ ] Indexes exist on `document_id`, `created_at`, `automation_score`

### Model Metrics Table
```sql
SELECT COUNT(*) FROM model_automation_metrics;
```
- [ ] Table `model_automation_metrics` exists
- [ ] Columns include: `model_id`, `model_name`, `automation_rate`, `accuracy`, `confidence`, etc.
- [ ] Indexes exist on `model_id`, `timestamp`

## ✅ Integration Tests

### Run Test Suite
```bash
python tests/test_integration.py
```
Expected results:
- [ ] TestMCPServer: All tests pass
- [ ] TestAutomationScoring: All tests pass
- [ ] TestLangChainOrchestration: All tests pass
- [ ] TestEnhancedLLMOps: All tests pass
- [ ] TestAPIGateway: All tests pass
- [ ] TestEndToEnd: All tests pass
- [ ] TestDockerServices: All tests pass

### With Pytest
```bash
pytest tests/test_integration.py -v
```
- [ ] All tests marked as `PASSED`
- [ ] No tests marked as `FAILED`

## ✅ End-to-End Workflow Validation

### Complete Invoice Processing
```bash
# 1. Upload a test invoice (if you have one)
# 2. Extract via MCP
# 3. Validate
# 4. Calculate automation score
# 5. Check metrics
```

Using Python:
```python
import httpx
import asyncio

async def test_e2e():
    async with httpx.AsyncClient() as client:
        # 1. Get automation metrics
        metrics = await client.get(
            "http://localhost:8002/analytics/automation-metrics",
            params={"time_range": "24h"}
        )
        print(f"✅ Automation Rate: {metrics.json()['automation_rate']}%")
        
        # 2. Check MCP capabilities
        caps = await client.get("http://localhost:8012/mcp/capabilities")
        print(f"✅ MCP Tools: {len(caps.json()['tools'])}")
        
        # 3. Check LLMOps dashboard
        dashboard = await client.get(
            "http://localhost:8001/llmops/automation-dashboard",
            params={"time_range": "7d"}
        )
        print(f"✅ LLMOps Dashboard: {dashboard.json()['summary']}")

asyncio.run(test_e2e())
```
- [ ] All endpoints respond successfully
- [ ] Data is consistent across services

## ✅ Performance Validation

### Response Times
Test that endpoints respond within acceptable time:

- [ ] MCP health check < 1s
- [ ] Automation metrics < 2s
- [ ] MCP tool execution < 10s (depends on complexity)
- [ ] LangChain processing < 30s (depends on document size)

### Load Test (Optional)
```bash
# Simple load test with curl
for i in {1..10}; do
  curl -w "@curl-format.txt" -o /dev/null -s \
    http://localhost:8012/mcp/metrics/automation?time_range=24h &
done
wait
```
- [ ] All requests complete successfully
- [ ] No timeout errors

## ✅ Documentation Validation

### Files Present
- [ ] `INTEGRATION_GUIDE.md` exists and is complete
- [ ] `QUICK_START.md` exists and is readable
- [ ] `IMPLEMENTATION_SUMMARY.md` exists
- [ ] `ENHANCEMENTS_README.md` exists
- [ ] `VALIDATION_CHECKLIST.md` exists (this file)

### Documentation Accuracy
- [ ] All endpoints documented match actual implementation
- [ ] Code examples work as shown
- [ ] Port numbers are correct (MCP: 8012, Analytics: 8002, etc.)

## ✅ Security Validation

### Authentication
```bash
# Try accessing without auth (should fail or prompt for auth)
curl http://localhost:8012/mcp/tools
```
- [ ] API Gateway enforces authentication
- [ ] Services behind gateway are protected

### CORS
- [ ] CORS headers are present
- [ ] CORS allows necessary origins

### Secrets Management
- [ ] No secrets in code or config files
- [ ] Secrets loaded from environment variables
- [ ] Azure Key Vault configured (if in production)

## ✅ Monitoring Validation

### Prometheus Metrics
```bash
curl http://localhost:9090
```
- [ ] Prometheus is running
- [ ] Targets are being scraped

### Grafana Dashboards
```bash
open http://localhost:3000
```
- [ ] Grafana is accessible
- [ ] Default credentials work (admin/admin)

### Logs
```bash
docker-compose logs mcp-server --tail=50
```
- [ ] Logs are being generated
- [ ] No critical errors in logs
- [ ] Log format is structured

## ✅ Final Checklist

Before marking as production-ready:

- [ ] All service health checks pass
- [ ] MCP Server operational with all tools
- [ ] Automation scoring tracking correctly
- [ ] LangChain orchestration working
- [ ] Enhanced LLMOps functional
- [ ] API Gateway routing correctly
- [ ] Database tables created
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Performance acceptable
- [ ] Security configured
- [ ] Monitoring operational

## 🎯 Target Metrics Achieved

Verify these Compello AS targets:

- [ ] **Automation Rate**: Currently **≥ 90%** (Target: 90%+)
- [ ] **Processing Speed**: Average **< 5 seconds** (Target: < 5s)
- [ ] **Accuracy**: Achieving **≥ 95%** (Target: 95%+)
- [ ] **Uptime**: System **≥ 99.9%** available (Target: 99.9%+)

## 📊 Sign-Off

Once all items are checked:

**Validated By**: ___________________  
**Date**: ___________________  
**Environment**: ☐ Development  ☐ Staging  ☐ Production  
**Status**: ☐ Ready for Deployment  ☐ Needs Review  

## 🆘 Troubleshooting

If any checks fail, see:
- `INTEGRATION_GUIDE.md` Section 10: Monitoring and Troubleshooting
- `QUICK_START.md` Troubleshooting section
- Service logs: `docker-compose logs [service-name] -f`

---

**Platform Version**: 1.0.0  
**Validation Date**: December 26, 2025  
**Next Review**: _________________

