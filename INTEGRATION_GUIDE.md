# Document Intelligence Platform - Integration Guide
## MCP, LangChain, and Enhanced LLMOps Integration

### Version 1.0.0
### Date: December 26, 2025

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MCP Server Integration](#mcp-server-integration)
4. [LangChain Orchestration](#langchain-orchestration)
5. [Enhanced LLMOps](#enhanced-llmops)
6. [Automation Scoring System](#automation-scoring-system)
7. [API Endpoints](#api-endpoints)
8. [Deployment Guide](#deployment-guide)
9. [Testing Strategy](#testing-strategy)
10. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Overview

This integration adds enterprise-grade capabilities to the Document Intelligence Platform:

### New Features
- **MCP (Model Context Protocol) Server**: Exposes platform capabilities as MCP-compliant tools for AI agents
- **LangChain Orchestration**: Advanced workflow management for invoice processing
- **Enhanced LLMOps**: Automation metrics tracking for fine-tuned models
- **Automation Scoring**: Real-time tracking toward 90%+ invoice automation goal

### Key Metrics (Compello AS Target)
- ✅ Invoice Automation Rate: **90%+** (currently tracked)
- ✅ Processing Accuracy: **95%+** for invoice extraction
- ✅ Processing Speed: **< 5 seconds** per invoice (P95)
- ✅ Uptime: **99.9%** reliability

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway (Port 8003)                  │
│           JWT Auth | Rate Limiting | Service Routing            │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
┌───────────────▼───┐  ┌──────▼──────┐  ┌──▼──────────────┐
│  MCP Server       │  │ AI Processing│  │   Analytics     │
│  (Port 8012)      │  │ (Port 8001)  │  │  (Port 8002)    │
│  ┌──────────────┐ │  │ ┌──────────┐ │  │ ┌─────────────┐ │
│  │ MCP Tools    │ │  │ │ Form     │ │  │ │ Automation  │ │
│  │ - Invoice    │ │  │ │ Recogniz.│ │  │ │ Scoring     │ │
│  │ - Validation │ │  │ │ OpenAI   │ │  │ │ - 90% Goal  │ │
│  │ - Classify   │ │  │ │ ML Models│ │  │ │ - Metrics   │ │
│  │ - Fine-tune  │ │  │ └──────────┘ │  │ │ - Insights  │ │
│  │ - Metrics    │ │  │ ┌──────────┐ │  │ └─────────────┘ │
│  │ - M365       │ │  │ │LangChain │ │  │                 │
│  └──────────────┘ │  │ │- Invoice │ │  │                 │
│  ┌──────────────┐ │  │ │  Chain   │ │  │                 │
│  │ MCP Resources│ │  │ │- Analysis│ │  │                 │
│  │ - document:// │ │  │ │  Chain   │ │  │                 │
│  │ - analytics://│ │  │ │- Multi   │ │  │                 │
│  │ - automation//│ │  │ │  Agent   │ │  │                 │
│  │ - invoice://  │ │  │ └──────────┘ │  │                 │
│  └──────────────┘ │  │ ┌──────────┐ │  │                 │
└───────────────────┘  │ │ LLMOps   │ │  └─────────────────┘
                       │ │ Automation│ │
                       │ │ Tracker  │ │
                       │ └──────────┘ │
                       └──────────────┘
```

### Integration Points

1. **MCP Server → Existing Services**
   - Calls AI Processing Service for invoice extraction
   - Calls Data Quality Service for validation
   - Calls Analytics Service for metrics
   - Non-breaking: Uses HTTP requests to existing endpoints

2. **LangChain → Existing Services**
   - Wraps Form Recognizer service
   - Wraps OpenAI service
   - Wraps ML model manager
   - Non-breaking: Extends functionality, doesn't replace

3. **Automation Scoring → Analytics Service**
   - New endpoints added to Analytics Service
   - Stores scores in existing Azure SQL Database
   - Non-breaking: New tables, existing queries unchanged

4. **Enhanced LLMOps → AI Processing Service**
   - New endpoints added to AI Processing Service
   - Tracks model automation metrics
   - Non-breaking: Extends fine-tuning workflows

---

## MCP Server Integration

### Port and Service Information
- **Port**: 8012
- **Container**: `docintel-mcp-server`
- **Service URL**: `http://mcp-server:8012`
- **Protocol Version**: 0.9.0

### Available MCP Tools

#### 1. extract_invoice_data
Extract structured invoice data using Azure Form Recognizer.

**Endpoint**: `POST /mcp/invoice/extract`

**Request**:
```json
{
  "tool_name": "extract_invoice_data",
  "parameters": {
    "document_id": "doc_12345"
  }
}
```

**Response**:
```json
{
  "success": true,
  "document_id": "doc_12345",
  "invoice_data": {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-001",
    "total_amount": 1250.50,
    "invoice_date": "2025-12-25",
    "line_items": [...]
  },
  "confidence": 0.95
}
```

#### 2. validate_invoice
Validate invoice data using data quality rules.

**Endpoint**: `POST /mcp/invoice/validate`

**Request**:
```json
{
  "tool_name": "validate_invoice",
  "parameters": {
    "invoice_data": {
      "vendor_name": "Acme Corp",
      "total_amount": 1250.50
    }
  }
}
```

#### 3. classify_document
Classify document type using ML models.

**Endpoint**: `POST /mcp/document/classify`

#### 4. get_automation_metrics
Get real-time automation metrics.

**Endpoint**: `GET /mcp/metrics/automation?time_range=24h`

**Response**:
```json
{
  "automation_rate": 92.5,
  "total_processed": 1000,
  "fully_automated": 925,
  "requires_review": 75,
  "average_confidence": 0.94,
  "goal_status": {
    "goal": 90.0,
    "is_met": true,
    "message": "🎉 Automation goal achieved!"
  }
}
```

#### 5. create_fine_tuning_job
Create fine-tuning job for model optimization.

**Endpoint**: `POST /mcp/fine-tuning/create-job`

### Available MCP Resources

#### 1. document://{document_id}
Access document data including metadata and processing results.

**URI**: `document://doc_12345`

**Example**:
```bash
curl -X POST http://localhost:8012/mcp/resources/read \
  -H "Content-Type: application/json" \
  -d '{"resource_uri": "document://doc_12345"}'
```

#### 2. analytics://metrics/{time_range}
Access real-time analytics metrics.

**URI**: `analytics://metrics/24h`

#### 3. automation://score/{time_range}
Access automation scoring data.

**URI**: `automation://score/7d`

#### 4. invoice://{document_id}
Access extracted invoice data with validation status.

**URI**: `invoice://doc_12345`

### Integration Example

```python
import httpx

# Example: Using MCP Server to process an invoice
async def process_invoice_with_mcp(document_id: str):
    async with httpx.AsyncClient() as client:
        # Step 1: Extract invoice data
        extract_response = await client.post(
            "http://localhost:8012/mcp/tools/execute",
            json={
                "tool_name": "extract_invoice_data",
                "parameters": {"document_id": document_id}
            }
        )
        invoice_data = extract_response.json()["result"]["invoice_data"]
        
        # Step 2: Validate invoice
        validate_response = await client.post(
            "http://localhost:8012/mcp/tools/execute",
            json={
                "tool_name": "validate_invoice",
                "parameters": {"invoice_data": invoice_data}
            }
        )
        validation_result = validate_response.json()["result"]
        
        # Step 3: Get automation metrics
        metrics_response = await client.get(
            "http://localhost:8012/mcp/metrics/automation",
            params={"time_range": "24h"}
        )
        metrics = metrics_response.json()
        
        return {
            "invoice_data": invoice_data,
            "validation": validation_result,
            "metrics": metrics
        }
```

---

## LangChain Orchestration

### Invoice Processing Chain

The LangChain invoice processing chain orchestrates the complete workflow:

**Workflow**: Upload → Extract → Validate → Classify → Store

**Endpoint**: `POST /process-invoice-langchain`

**Request**:
```json
{
  "document_id": "doc_12345"
}
```

**Response**:
```json
{
  "document_id": "doc_12345",
  "invoice_data": {
    "vendor_name": "Acme Corp",
    "total_amount": 1250.50,
    ...
  },
  "langchain_analysis": {
    "extracted_data": "...",
    "validation_report": "...",
    "classification": "FULLY_AUTOMATED"
  },
  "processing_time": 3.2,
  "timestamp": "2025-12-26T10:30:00Z"
}
```

### Document Analysis Chain

**Workflow**: Retrieve → Summarize → Extract Entities → Generate Insights

**Endpoint**: `POST /analyze-document-langchain`

**Features**:
- AI-powered document summarization
- Named entity extraction (organizations, people, dates, amounts)
- Business insights generation
- Action items identification

### Fine-Tuning Workflow Chain

**Workflow**: Collect Data → Prepare → Train → Evaluate → Deploy

**Endpoint**: `POST /fine-tuning-workflow-langchain`

**Features**:
- Data quality assessment
- Hyperparameter recommendations
- Evaluation strategy definition
- Automated workflow orchestration

### Multi-Agent Document Workflow

**Endpoint**: `POST /process-document-agent`

**Request**:
```json
{
  "document_id": "doc_12345",
  "task_description": "Extract and validate invoice data, then store in database"
}
```

**Features**:
- Orchestrator agent coordinates workflow
- Extraction agent handles data extraction
- Validation agent ensures quality
- Storage agent persists data

---

## Enhanced LLMOps

### Model Automation Tracking

**Endpoint**: `POST /llmops/track-model-metrics`

**Request**:
```json
{
  "model_id": "ft-gpt-35-invoice-2025",
  "model_name": "invoice-extractor-v2",
  "test_documents": ["doc_1", "doc_2", "doc_3", "..."]
}
```

**Response**:
```json
{
  "model_id": "ft-gpt-35-invoice-2025",
  "automation_rate": 94.5,
  "accuracy": 0.96,
  "confidence": 0.95,
  "completeness": 0.97,
  "validation_pass_rate": 95.0,
  "processing_speed": 3.2,
  "cost_per_document": 0.012,
  "documents_processed": 100
}
```

### Model Comparison

**Endpoint**: `POST /llmops/compare-models`

**Request**:
```json
{
  "baseline_model_id": "gpt-35-turbo",
  "fine_tuned_model_id": "ft-gpt-35-invoice-2025",
  "test_documents": ["doc_1", "doc_2", "..."]
}
```

**Response**:
```json
{
  "baseline_metrics": {
    "automation_rate": 85.0,
    "accuracy": 0.88
  },
  "fine_tuned_metrics": {
    "automation_rate": 94.5,
    "accuracy": 0.96
  },
  "improvement": {
    "automation_rate": 9.5,
    "accuracy": 0.08,
    "cost_reduction": 15.0
  },
  "recommendation": "STRONGLY RECOMMENDED: Deploy fine-tuned model",
  "confidence_level": "HIGH"
}
```

### Optimization for Automation Goal

**Endpoint**: `POST /llmops/optimize-for-goal`

**Request**:
```json
{
  "current_model_id": "ft-gpt-35-invoice-2025",
  "target_automation_rate": 90.0
}
```

**Response**:
```json
{
  "current_automation_rate": 94.5,
  "target_automation_rate": 90.0,
  "gap": -4.5,
  "is_achievable": true,
  "recommendations": [
    {
      "area": "confidence",
      "current": 0.95,
      "target": 0.90,
      "action": "Already exceeds target",
      "priority": "low"
    }
  ],
  "fine_tuning_plan": {
    "recommended_training_examples": 100,
    "suggested_hyperparameters": {
      "learning_rate": 0.00005,
      "batch_size": 16,
      "epochs": 2
    },
    "estimated_training_time_hours": 0.4,
    "estimated_cost_usd": 1.6
  }
}
```

### Automation Dashboard

**Endpoint**: `GET /llmops/automation-dashboard?time_range=7d`

**Response**:
```json
{
  "time_range": "7d",
  "trends": [
    {
      "date": "2025-12-20",
      "model_name": "invoice-extractor-v2",
      "automation_rate": 92.5,
      "confidence": 0.94
    }
  ],
  "summary": {
    "current_automation_rate": 94.5,
    "goal_progress": 105.0,
    "total_documents_processed": 5000,
    "active_models": 2
  }
}
```

---

## Automation Scoring System

### Calculate Automation Score

**Endpoint**: `POST /analytics/automation-score`

**Request**:
```json
{
  "invoice_data": {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-001",
    "total_amount": 1250.50,
    "confidence": 0.95
  },
  "validation_result": {
    "is_valid": true,
    "quality_score": 0.97
  }
}
```

**Response**:
```json
{
  "document_id": "doc_12345",
  "confidence_score": 0.95,
  "completeness_score": 0.97,
  "validation_pass": true,
  "automation_score": 0.92,
  "requires_review": false
}
```

### Automation Score Formula

```
automation_score = confidence × completeness × validation_multiplier

where:
- confidence: Form Recognizer confidence (0-1)
- completeness: % of required fields extracted (0-1)
- validation_multiplier: 1.0 if valid, 0.5 if invalid
```

### Automation Metrics

**Endpoint**: `GET /analytics/automation-metrics?time_range=24h`

**Response**:
```json
{
  "automation_rate": 92.5,
  "total_processed": 1000,
  "fully_automated": 925,
  "requires_review": 75,
  "manual_intervention": 15,
  "average_confidence": 0.94,
  "average_completeness": 0.96,
  "validation_pass_rate": 95.0,
  "goal_status": {
    "goal": 90.0,
    "current_rate": 92.5,
    "is_met": true,
    "message": "🎉 Automation goal achieved!"
  }
}
```

### Automation Insights

**Endpoint**: `GET /analytics/automation-insights?time_range=7d`

**Response**:
```json
{
  "insights": [
    {
      "type": "automation_rate",
      "priority": "low",
      "message": "✅ Automation rate (92.5%) exceeds 90% goal",
      "recommendation": "Maintain current quality standards"
    }
  ],
  "current_metrics": {
    "automation_rate": 92.5,
    "average_confidence": 0.94,
    "average_completeness": 0.96
  }
}
```

### Automation Trend

**Endpoint**: `GET /analytics/automation-trend?days=30`

**Response**:
```json
{
  "trend": [
    {
      "date": "2025-12-01",
      "automation_rate": 88.5,
      "total_processed": 100
    },
    {
      "date": "2025-12-02",
      "automation_rate": 90.2,
      "total_processed": 105
    }
  ],
  "summary": {
    "improvement": 4.0,
    "direction": "improving"
  }
}
```

---

## API Endpoints

### Complete API Reference

#### MCP Server (Port 8012)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/capabilities` | GET | Get MCP capabilities |
| `/mcp/tools` | GET | List available tools |
| `/mcp/tools/execute` | POST | Execute a tool |
| `/mcp/resources` | GET | List available resources |
| `/mcp/resources/read` | POST | Read a resource |
| `/mcp/invoice/extract` | POST | Extract invoice data |
| `/mcp/invoice/validate` | POST | Validate invoice |
| `/mcp/document/classify` | POST | Classify document |
| `/mcp/metrics/automation` | GET | Get automation metrics |

#### AI Processing Service (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process-invoice-langchain` | POST | Process invoice with LangChain |
| `/analyze-document-langchain` | POST | Analyze document with LangChain |
| `/fine-tuning-workflow-langchain` | POST | Orchestrate fine-tuning |
| `/process-document-agent` | POST | Process with multi-agent |
| `/llmops/track-model-metrics` | POST | Track model metrics |
| `/llmops/compare-models` | POST | Compare models |
| `/llmops/optimize-for-goal` | POST | Optimize for automation goal |
| `/llmops/automation-dashboard` | GET | Get automation dashboard |

#### Analytics Service (Port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/automation-metrics` | GET | Get automation metrics |
| `/analytics/automation-score` | POST | Calculate automation score |
| `/analytics/automation-insights` | GET | Get automation insights |
| `/analytics/automation-trend` | GET | Get automation trend |

#### API Gateway (Port 8003)

All services accessible through API Gateway:
- `/mcp/*` → MCP Server
- `/process/*` → AI Processing
- `/analytics/*` → Analytics Service
- `/llmops/*` → AI Processing (LLMOps)

---

## Deployment Guide

### Prerequisites

1. **Azure Services**:
   - Azure OpenAI (GPT-4 or GPT-3.5-turbo)
   - Azure Form Recognizer
   - Azure SQL Database
   - Azure Storage Account

2. **Environment Variables**:
```bash
# OpenAI
OPENAI_ENDPOINT=https://your-openai.openai.azure.com
OPENAI_API_KEY=your-api-key
OPENAI_DEPLOYMENT=gpt-4

# Form Recognizer
FORM_RECOGNIZER_ENDPOINT=https://your-form-recognizer.cognitiveservices.azure.com
FORM_RECOGNIZER_KEY=your-key

# Database
SQL_CONNECTION_STRING=your-connection-string

# Redis
REDIS_URL=redis://redis:6379
```

### Deployment Steps

1. **Update Requirements**:
```bash
pip install -r requirements.txt
```

2. **Build Docker Containers**:
```bash
docker-compose build
```

3. **Start Services**:
```bash
docker-compose up -d
```

4. **Verify Health**:
```bash
# Check MCP Server
curl http://localhost:8012/health

# Check API Gateway
curl http://localhost:8003/health

# Check Analytics
curl http://localhost:8002/health
```

5. **Test MCP Integration**:
```bash
# List MCP tools
curl http://localhost:8012/mcp/tools

# Get automation metrics
curl http://localhost:8012/mcp/metrics/automation?time_range=24h
```

### Docker Compose Configuration

The MCP Server has been added to `docker-compose.yml`:

```yaml
mcp-server:
  build:
    context: .
    dockerfile: src/microservices/mcp-server/Dockerfile
  container_name: docintel-mcp-server
  ports:
    - "8012:8012"
  environment:
    - ENVIRONMENT=development
    - REDIS_URL=redis://redis:6379
    - AI_PROCESSING_URL=http://ai-processing:8001
    - ANALYTICS_URL=http://analytics:8002
  depends_on:
    - redis
    - ai-processing
    - analytics
  networks:
    - docintel-network
  restart: unless-stopped
```

---

## Testing Strategy

### Unit Testing

Test individual components:

```bash
# Test MCP tools
pytest tests/test_mcp_tools.py

# Test automation scoring
pytest tests/test_automation_scoring.py

# Test LangChain orchestration
pytest tests/test_langchain_orchestration.py
```

### Integration Testing

Test service interactions:

```python
import httpx
import pytest

@pytest.mark.asyncio
async def test_mcp_invoice_extraction():
    async with httpx.AsyncClient() as client:
        # Upload document
        upload_response = await client.post(
            "http://localhost:8000/documents/upload",
            files={"file": open("test_invoice.pdf", "rb")}
        )
        document_id = upload_response.json()["document_id"]
        
        # Extract via MCP
        extract_response = await client.post(
            "http://localhost:8012/mcp/invoice/extract",
            json={"document_id": document_id}
        )
        
        assert extract_response.status_code == 200
        result = extract_response.json()
        assert "invoice_data" in result
        assert result["confidence"] > 0.8
```

### End-to-End Testing

Test complete workflows:

```bash
# Run comprehensive test suite
pytest tests/test_e2e_invoice_workflow.py -v
```

### Load Testing

```bash
# Test MCP server performance
locust -f tests/load_test_mcp.py --host=http://localhost:8012
```

---

## Monitoring and Troubleshooting

### Health Checks

**MCP Server**:
```bash
curl http://localhost:8012/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "mcp-server",
  "tools_count": 10,
  "resources_count": 7
}
```

### Logging

All services log to stdout/stderr. View logs:

```bash
# MCP Server logs
docker logs docintel-mcp-server -f

# Analytics logs
docker logs docintel-analytics -f

# AI Processing logs
docker logs docintel-ai-processing -f
```

### Common Issues

**Issue 1: MCP Server can't connect to AI Processing**

Solution:
```bash
# Check service is running
docker ps | grep ai-processing

# Check network connectivity
docker exec docintel-mcp-server ping ai-processing

# Verify environment variables
docker exec docintel-mcp-server env | grep AI_PROCESSING_URL
```

**Issue 2: Automation score not calculating**

Solution:
```bash
# Check database connection
docker exec docintel-analytics python -c "from src.shared.storage.sql_service import SQLService; print('DB OK')"

# Verify table exists
docker exec docintel-analytics python -c "from src.microservices.analytics.automation_scoring import AutomationScoringEngine; engine = AutomationScoringEngine(); print('Engine OK')"
```

**Issue 3: LangChain timeout errors**

Solution:
- Increase timeout in `langchain_orchestration.py`
- Check OpenAI API rate limits
- Verify OpenAI endpoint configuration

### Metrics and Alerts

**Prometheus Metrics**:
- `mcp_tool_executions_total`: Total MCP tool executions
- `automation_score_avg`: Average automation score
- `langchain_processing_duration_seconds`: LangChain processing time

**Alerts**:
- Automation rate drops below 90%
- MCP server response time > 10s
- LangChain chain failure rate > 5%

### Performance Tuning

**MCP Server**:
- Adjust connection pool sizes
- Enable caching for frequently accessed resources
- Use async HTTP clients

**LangChain**:
- Reduce token limits for prompts
- Use streaming for long responses
- Cache LLM responses

**Automation Scoring**:
- Batch score calculations
- Use database indexes
- Cache recent metrics

---

## API Authentication

All API endpoints require JWT authentication via the API Gateway:

```bash
# Get JWT token
curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8012/mcp/metrics/automation
```

---

## Success Metrics

Track these KPIs to measure success:

1. **Automation Rate**: >= 90% (Compello goal)
2. **Processing Speed**: < 5 seconds per invoice
3. **Accuracy**: >= 95% for invoice extraction
4. **Cost per Document**: < $0.02
5. **System Uptime**: >= 99.9%

Monitor via:
```bash
curl http://localhost:8002/analytics/automation-metrics
```

---

## Support and Contact

For issues or questions:

- GitHub Issues: [Your Repository]
- Documentation: [Your Docs URL]
- Email: support@compello.com

---

## Changelog

### Version 1.0.0 (2025-12-26)
- ✅ Added MCP Server (Port 8012)
- ✅ Integrated LangChain orchestration
- ✅ Enhanced LLMOps with automation tracking
- ✅ Implemented automation scoring system
- ✅ Updated API Gateway routing
- ✅ Added Docker Compose configuration
- ✅ Created comprehensive documentation

---

## License

Copyright © 2025 Compello AS. All rights reserved.

