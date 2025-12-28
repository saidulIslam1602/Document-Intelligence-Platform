# Complete API Architecture & Communication Flow
**Document Intelligence Platform - Comprehensive Endpoint & Integration Analysis**

Generated: December 28, 2025  
Total Services: 14 microservices  
Total Endpoints: 150+  
Total Code Lines: 11,629 lines (main.py files only)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL CLIENTS                                │
│  React Frontend (port 3001) │ Mobile Apps │ Claude Desktop │ API Keys   │
└────────────────────┬────────────────────────────────────────────────────┘
                     │ HTTPS
                     ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (port 8003)                              │
│  • JWT Authentication • Rate Limiting • Circuit Breaker                 │
│  • Request Routing • Load Balancing • CORS                              │
└───┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┘
    │         │         │         │         │         │         │
    ↓         ↓         ↓         ↓         ↓         ↓         ↓
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Document││AI Proc-││Analyti-││AI Chat ││MCP     ││Data    ││Batch   │
│Ingest  ││essing  ││cs      ││        ││Server  ││Quality ││Process │
│:8000   ││:8001   ││:8002   ││:8004   ││:8012   ││:8006   ││:8007   │
└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘
    │         │         │         │         │         │         │
    └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
                                  ↓
         ┌───────────────────────────────────────────┐
         │      SHARED INFRASTRUCTURE                │
         │  PostgreSQL DB │ Redis Cache │ Storage   │
         │  :5432         │ :6379       │ (Blob)    │
         └───────────────────────────────────────────┘
```

---

## 📡 Frontend → Backend Communication

### Frontend Configuration
**File:** `frontend/src/services/api.ts`

```typescript
const API_URL = 'http://localhost:8003'  // API Gateway

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
})

// Automatic JWT token injection
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Frontend API Calls by Page

| Frontend Page | Endpoint Called | Method | Purpose |
|--------------|----------------|--------|---------|
| **Documents.tsx** | `/documents` | GET | List documents |
| | `/documents/{id}` | GET | Get document details |
| | `/documents/{id}` | DELETE | Delete document |
| **Dashboard.tsx** | `/analytics/automation-metrics` | GET | Automation metrics |
| | `/documents?limit=5` | GET | Recent documents |
| **Chat.tsx** | `/chat/message` | POST | Send chat message |
| **Entities.tsx** | `/entities` | GET | List extracted entities |
| **ProcessingPipeline.tsx** | `/processing/jobs?limit=10` | GET | Processing jobs |
| **MCPTools.tsx** | `/mcp/tools` | GET | List MCP tools |
| | `/mcp/execute-tool` | POST | Execute MCP tool |
| **Login.tsx** | `/auth/login` | POST | User authentication |
| **Analytics.tsx** | `/analytics/automation-metrics` | GET | Analytics data |
| **Admin.tsx** | `/admin/health` | GET | System health |
| | `/admin/users` | GET | User management |
| | `/admin/logs?limit=10` | GET | System logs |
| **AuditLogs.tsx** | `/audit/logs` | GET | Audit trail |
| **Search.tsx** | `/search?{params}` | GET | Search documents |

---

## 🚪 API Gateway Endpoints (Port 8003)

**Service:** `src/microservices/api-gateway/main.py` (2,301 lines)

### Health & Monitoring
```
GET  /health                    → System health check
GET  /health/live               → Liveness probe
GET  /health/ready              → Readiness probe
GET  /circuit-breakers          → Circuit breaker status
POST /circuit-breakers/{name}/reset → Reset breaker
POST /circuit-breakers/reset-all → Reset all breakers
GET  /rate-limiters             → Rate limiter status
POST /rate-limiters/{name}/reset → Reset limiter
POST /rate-limiters/reset-all   → Reset all limiters
GET  /rate-limit                → Check rate limit
```

### Authentication & Authorization
```
POST /auth/login                → User login (JWT token)
POST /auth/register             → User registration
POST /auth/refresh              → Refresh JWT token
POST /auth/logout               → User logout
GET  /auth/me                   → Get current user
POST /api-keys                  → Create API key
GET  /api-keys                  → List API keys
DELETE /api-keys/{id}           → Revoke API key
```

### Document Management
```
GET  /documents                 → List documents
GET  /documents/{id}            → Get document details
POST /documents/upload          → Upload document (forwards to document-ingestion:8000)
DELETE /documents/{id}          → Delete document (forwards to document-ingestion:8000)
GET  /entities                  → Get extracted entities
```

### Analytics
```
GET /analytics/automation-metrics → Automation metrics (forwards to analytics:8002)
```

### AI Chat
```
POST /chat/message              → Send chat message (forwards to ai-chat:8004)
```

### Service Routing Map
```python
SERVICE_URLS = {
    "document-ingestion": "http://document-ingestion:8000",
    "ai-processing": "http://ai-processing:8001",
    "analytics": "http://analytics:8002",
    "ai-chat": "http://ai-chat:8004",
    "performance-dashboard": "http://performance-dashboard:8005",
    "data-quality": "http://data-quality:8006",
    "batch-processor": "http://batch-processor:8007",
    "data-catalog": "http://data-catalog:8008",
    "migration-service": "http://migration-service:8009",
    "fabric-integration": "http://fabric-integration:8010",
    "demo-service": "http://demo-service:8011",
    "mcp-server": "http://mcp-server:8012"
}
```

---

## 📄 Document Ingestion Service (Port 8000)

**Service:** `src/microservices/document-ingestion/main.py` (1,321 lines)

### Endpoints
```
GET  /health                    → Health check
POST /documents/upload          → Upload single document
POST /documents/batch-upload    → Upload 10-15 documents
GET  /documents/{id}/status     → Get processing status
GET  /documents                 → List user documents
DELETE /documents/{id}          → Delete document
```

### Processing Flow
```
1. Client uploads file → API Gateway :8003
2. API Gateway forwards → Document Ingestion :8000
3. Document Ingestion:
   - Validates file (size, type)
   - Uploads to blob storage (Azure/Local)
   - Stores metadata in PostgreSQL
   - Creates processing job
   - Publishes event to Event Hub
   - Calls AI Processing :8001 via HTTP
4. Returns document_id to client
```

### Key Operations
```python
# Store document in PostgreSQL
sql_service.store_document({
    "document_id": document_id,
    "user_id": user_id,
    "file_name": file.filename,
    "file_size": file_size,
    "status": "uploaded"
})

# Schedule AI processing
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ai-processing:8001/process",
        json={"document_id": document_id, "user_id": user_id}
    )
```

---

## 🤖 AI Processing Service (Port 8001)

**Service:** `src/microservices/ai-processing/main.py` (1,500+ lines)

### Endpoints
```
GET  /health                    → Health check
POST /process                   → Process document with AI
POST /batch-process             → Batch processing
POST /classify                  → Document classification
POST /sentiment                 → Sentiment analysis
POST /qa                        → Question answering
POST /entities                  → Named entity recognition
POST /summarize                 → Text summarization
POST /models/train              → Train custom model
POST /process-invoice-langchain → LangChain invoice processing
POST /analyze-document-langchain → LangChain document analysis
POST /fine-tuning-workflow-langchain → Fine-tuning workflow
POST /process-document-agent    → Agent-based processing
POST /process-intelligent       → Intelligent routing
GET  /routing/statistics        → Routing statistics
POST /llmops/track-model-metrics → Track model metrics
POST /llmops/compare-models     → Compare models
POST /llmops/optimize-for-goal  → Optimize for goal
GET  /llmops/automation-dashboard → LLMOps dashboard
GET  /models/status             → Model status
```

### AI Processing Flow
```
1. Receives document_id from document-ingestion
2. Retrieves document from PostgreSQL/Storage
3. Extracts text using OCR (if PDF/image)
4. Routes to appropriate AI model:
   - OpenAI GPT-4 for invoices
   - Azure Form Recognizer for structured docs
   - Custom models for specific types
5. Extracts entities (dates, amounts, vendors, etc.)
6. Validates extracted data
7. Stores results in invoice_extractions table
8. Returns processing result
```

### Database Tables Used
```sql
-- Main extraction table (36 columns)
invoice_extractions (
    id, document_id, user_id,
    invoice_number, invoice_date, due_date,
    vendor_name, vendor_address, vendor_tax_id,
    customer_name, customer_address,
    total_amount, tax_amount, subtotal_amount,
    currency, payment_terms, line_items,
    confidence_score, processing_time,
    created_at, updated_at, ...
)
```

---

## 📊 Analytics Service (Port 8002)

**Service:** `src/microservices/analytics/main.py` (1,800+ lines)

### Endpoints
```
GET  /health                    → Health check
GET  /health/live               → Liveness probe
GET  /health/ready              → Readiness probe
GET  /dashboard                 → HTML dashboard
GET  /analytics/realtime        → Real-time analytics
POST /analytics/historical      → Historical data
GET  /metrics/performance       → Performance metrics
GET  /analytics/business-intelligence → BI insights
GET  /alerts                    → Active alerts
POST /alerts/acknowledge/{id}   → Acknowledge alert
POST /alerts/rules              → Create alert rule
POST /analytics/store-metric    → Store metric
GET  /analytics/metrics         → Get metrics
POST /analytics/store-data-lake → Store to data lake
GET  /analytics/data-lake/files → List data lake files
GET  /analytics/processing-jobs/{user_id} → User jobs
POST /analytics/powerbi/push-metrics → Push to Power BI
POST /analytics/powerbi/push-user-activity → Push activity
POST /analytics/powerbi/create-dataset → Create dataset
GET  /monitoring/health         → Monitoring health
GET  /monitoring/alerts         → Monitoring alerts
POST /monitoring/alert-rules    → Alert rules
GET  /analytics/automation-metrics → Automation metrics ⭐
POST /analytics/automation-score → Calculate automation score
POST /analytics/automation-score-batch → Batch scoring
GET  /analytics/automation-insights → Automation insights
GET  /analytics/automation-trend → Automation trend
GET  /monitoring/metrics        → System metrics
```

### Automation Scoring Engine
```python
class AutomationScoringEngine:
    def calculate_automation_score(self, document_id: str):
        # Fetch extraction results from invoice_extractions
        results = sql_service.execute_query(
            "SELECT * FROM invoice_extractions WHERE document_id = ?",
            (document_id,)
        )
        
        # Calculate automation score (0-100%)
        score = self._calculate_score(results)
        
        # Store automation score
        sql_service.execute_query(
            "INSERT INTO automation_scores (...) VALUES (...)",
            (document_id, score, ...)
        )
        
        return score
```

---

## 💬 AI Chat Service (Port 8004)

**Service:** `src/microservices/ai-chat/main.py` (953 lines)

### Endpoints
```
POST /chat/message              → Send chat message
GET  /chat/conversations        → List conversations
GET  /chat/conversations/{id}/messages → Get messages
DELETE /chat/conversations/{id} → Delete conversation
GET  /health                    → Health check
```

### Chat Flow
```
1. User sends message via frontend
2. API Gateway forwards to ai-chat:8004
3. AI Chat Service:
   - Retrieves conversation history from PostgreSQL
   - Adds user message to context
   - Calls OpenAI GPT-4 API
   - Stores messages in conversations table
4. Returns AI response to user
```

### Database Operations
```python
# Store conversation message
sql_service.store_conversation_message({
    "conversation_id": conversation_id,
    "user_id": user_id,
    "role": "user",
    "content": message,
    "timestamp": datetime.utcnow()
})

# Get conversation history
conversations = sql_service.get_user_conversations(user_id, limit=10)
```

---

## 🔌 MCP Server (Port 8012)

**Service:** `src/microservices/mcp-server/main.py` (1,228 lines)

### MCP Protocol Endpoints
```
GET  /health                    → Health check
GET  /mcp/capabilities          → MCP capabilities
GET  /mcp/tools                 → List available tools
POST /mcp/tools/execute         → Execute tool
GET  /mcp/resources             → List resources
POST /mcp/resources/read        → Read resource
POST /mcp/invoice/extract       → Extract invoice data
POST /mcp/invoice/validate      → Validate invoice
POST /mcp/document/classify     → Classify document
GET  /mcp/metrics/automation    → Automation metrics
POST /mcp/fine-tuning/create-job → Create fine-tuning job
POST /mcp/m365/process-document → Process M365 document
POST /mcp/initialize            → Initialize MCP session
POST /mcp/tools/list            → List tools (protocol)
POST /mcp/tools/call            → Call tool (protocol)
POST /mcp/resources/list        → List resources (protocol)
POST /mcp/resources/read        → Read resource (protocol)
POST /mcp/auth/token            → Get auth token
GET  /mcp/auth/test-tokens      → Test tokens
GET  /mcp/auth/me               → Get current user
GET  /mcp/rate-limits           → Get rate limits
GET  /mcp/permissions           → Get permissions
```

### MCP Service Orchestration
```python
# MCP tool execution orchestrates calls to other services
SERVICE_URLS = {
    "ai-processing": "http://ai-processing:8001",
    "data-quality": "http://data-quality:8006",
    "analytics": "http://analytics:8002",
    "document-ingestion": "http://document-ingestion:8000",
    "ai-chat": "http://ai-chat:8004"
}

# Example: Extract invoice via MCP tool
@app.post("/mcp/invoice/extract")
async def extract_invoice(document_id: str):
    # Call AI Processing service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVICE_URLS['ai-processing']}/process",
            json={"document_id": document_id}
        )
    return response.json()
```

---

## ✅ Data Quality Service (Port 8006)

**Service:** `src/microservices/data-quality/main.py` (703 lines)

### Endpoints
```
GET  /health                    → Health check
POST /validate/document         → Validate document data
POST /validate/analytics        → Validate analytics data
POST /quality/metrics           → Quality metrics
POST /quality/report            → Generate quality report
GET  /profile/{table_name}      → Profile database table
GET  /quality/dashboard         → Quality dashboard
GET  /quality/alerts            → Quality alerts
```

### Data Validation Flow
```
1. Receives validation request
2. Queries data from PostgreSQL
3. Performs validation checks:
   - Completeness (missing fields)
   - Accuracy (data format)
   - Consistency (cross-field validation)
   - Timeliness (data freshness)
4. Calculates quality score
5. Stores quality metrics
6. Returns validation report
```

---

## 📦 Batch Processor Service (Port 8007)

**Service:** `src/microservices/batch-processor/main.py` (349 lines)

### Endpoints
```
GET  /health                    → Health check
GET  /pipelines                 → List pipelines
GET  /pipelines/{name}          → Get pipeline details
POST /pipelines/{name}/execute  → Execute pipeline
GET  /executions/{id}           → Get execution status
GET  /executions                → List executions
POST /process/documents         → Process documents batch
POST /process/analytics         → Process analytics batch
POST /process/users             → Process users batch
GET  /monitoring/dashboard      → Monitoring dashboard
GET  /monitoring/health         → Health status
```

### Batch Processing Pipelines
```
1. document-processing-pipeline
   - Processes multiple documents
   - Calls ai-processing for each
   - Aggregates results

2. analytics-aggregation-pipeline
   - Aggregates analytics data
   - Calculates metrics
   - Updates dashboards

3. data-quality-pipeline
   - Validates data quality
   - Generates reports
   - Triggers alerts
```

---

## 📚 Data Catalog Service (Port 8008)

**Service:** `src/microservices/data-catalog/main.py` (480 lines)

### Endpoints
```
GET  /health                    → Health check
POST /assets                    → Register data asset
GET  /assets                    → List assets
GET  /assets/{id}               → Get asset details
POST /lineage/relationships     → Create lineage relationship
GET  /lineage/{id}              → Get asset lineage
GET  /lineage/flow/{source}/{target} → Get lineage flow
POST /search                    → Search assets
GET  /impact/{id}               → Get impact analysis
GET  /dashboard/overview        → Dashboard overview
GET  /dashboard/lineage-graph   → Lineage graph
```

---

## 🎯 Performance Dashboard (Port 8005)

**Service:** `src/microservices/performance-dashboard/main.py` (296 lines)

### Endpoints
```
GET  /                          → HTML dashboard
GET  /api/system-metrics        → System metrics
GET  /api/performance-summary   → Performance summary
POST /api/optimize-memory       → Optimize memory
GET  /api/cache-stats           → Cache statistics
GET  /health                    → Health check
GET  /api/health                → API health check
```

---

## 🔐 Shared Modules - How Services Communicate

### 1. Database Layer (`src/shared/storage/sql_service.py`)

All services use SQLService for PostgreSQL operations:

```python
from src.shared.storage.sql_service import SQLService

# Initialize in each service
sql_service = SQLService(config.sql_connection_string)

# Common operations
sql_service.execute_query(query, params)  # SELECT queries
sql_service.execute_non_query(query, params)  # INSERT/UPDATE
sql_service.store_document(document_data)
sql_service.get_user_documents(user_id, limit)
sql_service.store_processing_job(...)
sql_service.get_metrics(metric_name, hours)
```

**PostgreSQL Connection:**
```
Database: documentintelligence
Host: postgres (docker) or localhost
Port: 5432
User: admin
Password: admin123
```

### 2. Cache Layer (`src/shared/cache/redis_cache.py`)

```python
from src.shared.cache.redis_cache import RedisCache, cache_result

cache = RedisCache(redis_url="redis://redis:6379")

# Decorator for caching
@cache_result(ttl=300)
async def get_document(document_id: str):
    return sql_service.get_document(document_id)
```

### 3. Authentication (`src/shared/auth/jwt_auth.py`)

```python
from src.shared.auth.jwt_auth import create_token, verify_token

# Generate JWT token
token = create_token(user_id="user123", role="admin")

# Verify token
payload = verify_token(token)
```

### 4. Monitoring (`src/shared/monitoring/metrics.py`)

```python
from src.shared.monitoring.metrics import monitor_performance

@monitor_performance(threshold=2.0)
async def process_document(document_id: str):
    # Automatically tracks execution time
    pass
```

---

## 🔄 Complete Request Flow Example

### Upload & Process Invoice

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Frontend Upload                                            │
│ React App → POST /documents/upload                                 │
│ Headers: Authorization: Bearer <JWT_TOKEN>                         │
│ Body: multipart/form-data (file)                                   │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: API Gateway (Port 8003)                                    │
│ • Validates JWT token                                              │
│ • Checks rate limit (Redis)                                        │
│ • Forwards to document-ingestion:8000                              │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Document Ingestion (Port 8000)                             │
│ • Validates file (size, type)                                      │
│ • Uploads to blob storage (Azure/Local)                            │
│ • Stores in PostgreSQL: documents table                            │
│ • Creates processing job                                           │
│ • Calls ai-processing:8001 via HTTP                                │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: AI Processing (Port 8001)                                  │
│ • Retrieves document from storage                                  │
│ • Extracts text (OCR if needed)                                    │
│ • Routes to GPT-4 / Form Recognizer                                │
│ • Extracts invoice entities:                                       │
│   - invoice_number, invoice_date, vendor_name                      │
│   - total_amount, tax_amount, line_items                           │
│ • Stores in PostgreSQL: invoice_extractions table (36 columns)     │
│ • Returns processing result                                        │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Analytics Calculation (Port 8002)                          │
│ • Automation engine calculates score                               │
│ • Queries invoice_extractions table                                │
│ • Calculates automation percentage                                 │
│ • Stores in automation_scores table                                │
│ • Updates dashboard metrics                                        │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: Response to Frontend                                       │
│ Returns: {                                                          │
│   "document_id": "uuid-1234",                                      │
│   "status": "uploaded",                                            │
│   "message": "Document uploaded successfully",                     │
│   "entities_extracted": 25                                         │
│ }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

### Core Tables

```sql
-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(100),
    blob_path VARCHAR(1000),
    document_type VARCHAR(50),
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Invoice extractions table (36 columns)
CREATE TABLE invoice_extractions (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    vendor_name VARCHAR(500),
    vendor_address TEXT,
    vendor_tax_id VARCHAR(100),
    vendor_phone VARCHAR(50),
    vendor_email VARCHAR(200),
    customer_name VARCHAR(500),
    customer_address TEXT,
    customer_tax_id VARCHAR(100),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(200),
    total_amount DECIMAL(15,2),
    tax_amount DECIMAL(15,2),
    subtotal_amount DECIMAL(15,2),
    discount_amount DECIMAL(15,2),
    shipping_amount DECIMAL(15,2),
    currency VARCHAR(10),
    payment_terms VARCHAR(200),
    payment_method VARCHAR(100),
    purchase_order_number VARCHAR(100),
    bank_account VARCHAR(100),
    line_items JSONB,
    notes TEXT,
    confidence_score DECIMAL(5,2),
    processing_time DECIMAL(10,2),
    model_used VARCHAR(100),
    extraction_method VARCHAR(100),
    validation_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    reviewed_at TIMESTAMP
);

-- Automation scores table
CREATE TABLE automation_scores (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    completeness DECIMAL(5,2),
    accuracy DECIMAL(5,2),
    confidence DECIMAL(5,2),
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations table (AI Chat)
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages table (AI Chat)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    conversation_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);

-- Processing jobs table
CREATE TABLE processing_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    document_id VARCHAR(100),
    status VARCHAR(50),
    progress INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔍 Service-to-Service Communication Matrix

| From Service | To Service | Protocol | Endpoint | Purpose |
|-------------|-----------|----------|----------|---------|
| **API Gateway** | Document Ingestion | HTTP | POST /documents/upload | Forward upload |
| **API Gateway** | Analytics | HTTP | GET /analytics/automation-metrics | Get metrics |
| **API Gateway** | AI Chat | HTTP | POST /chat/message | Forward message |
| **Document Ingestion** | AI Processing | HTTP | POST /process | Trigger processing |
| **MCP Server** | AI Processing | HTTP | POST /process | Orchestrate processing |
| **MCP Server** | Data Quality | HTTP | POST /validate/document | Validate data |
| **MCP Server** | Analytics | HTTP | GET /analytics/metrics | Get analytics |
| **Batch Processor** | AI Processing | HTTP | POST /process | Batch processing |
| **All Services** | PostgreSQL | TCP | :5432 | Database operations |
| **All Services** | Redis | TCP | :6379 | Caching |

---

## 📈 Performance & Monitoring

### Prometheus Metrics
```yaml
# Exposed by all services
- http_requests_total
- http_request_duration_seconds
- http_requests_in_progress
- cache_hits_total
- cache_misses_total
- database_query_duration_seconds
- document_processing_duration_seconds
- ai_model_inference_duration_seconds
```

### Health Check Pattern
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "service-name",
        "version": "2.0.0",
        "checks": {
            "database": check_database(),
            "cache": check_redis(),
            "storage": check_storage()
        }
    }
```

---

## 🔒 Security Architecture

### Authentication Flow
```
1. User login → POST /auth/login
2. API Gateway validates credentials (PostgreSQL)
3. Returns JWT token (expires in 1 hour)
4. Client stores token in localStorage
5. All subsequent requests include: Authorization: Bearer <token>
6. API Gateway validates JWT on every request
7. Token refresh via POST /auth/refresh
```

### Rate Limiting
```python
# Redis-based rate limiting
@rate_limit(requests=100, window=60)  # 100 req/min
async def endpoint():
    pass

# Per-user limits
RATE_LIMITS = {
    "free": 10,      # 10 req/min
    "pro": 100,      # 100 req/min
    "enterprise": 1000  # 1000 req/min
}
```

---

## 🚀 Key Integration Points

### 1. **Document Upload Pipeline**
```
Frontend → API Gateway → Document Ingestion → AI Processing → Analytics
```

### 2. **Chat Pipeline**
```
Frontend → API Gateway → AI Chat → OpenAI API → PostgreSQL
```

### 3. **MCP Tool Execution**
```
Claude Desktop → MCP Server → Multiple Services → Response
```

### 4. **Batch Processing**
```
Scheduler → Batch Processor → AI Processing → Data Quality → Analytics
```

### 5. **Analytics Dashboard**
```
Frontend → API Gateway → Analytics → PostgreSQL → Automation Engine
```

---

## 📊 Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Microservices** | 14 |
| **Total API Endpoints** | 150+ |
| **Total Code Lines** | 11,629 (main.py files) |
| **Database Tables** | 15+ |
| **External APIs** | 3 (OpenAI, Azure Form Recognizer, Azure Storage) |
| **Frontend Pages** | 20+ |
| **Shared Modules** | 8 (auth, cache, storage, monitoring, etc.) |
| **Docker Services** | 18 (14 app + 4 infra) |
| **Total HTTP Calls** | Varies (100-1000+ per upload) |

---

## 🎯 Critical Paths for Interview Demo

### 1. **Document Upload & Processing**
- Frontend uploads PDF → API Gateway → Document Ingestion
- Extracts 25+ entities → Stores in PostgreSQL
- **Demo Point:** Show real-time entity extraction

### 2. **Automation Metrics**
- Analytics service calculates 90%+ automation
- **Demo Point:** Display automation dashboard

### 3. **MCP Protocol Integration**
- Claude Desktop executes MCP tools
- **Demo Point:** Run extract-invoice tool

### 4. **AI Chat Assistance**
- Ask questions about documents
- **Demo Point:** Query "What's the total amount on invoice X?"

---

## 🔧 Local Development URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| API Gateway | http://localhost:8003 |
| Document Ingestion | http://localhost:8000 |
| AI Processing | http://localhost:8001 |
| Analytics | http://localhost:8002 |
| AI Chat | http://localhost:8004 |
| Performance Dashboard | http://localhost:8005 |
| Data Quality | http://localhost:8006 |
| Batch Processor | http://localhost:8007 |
| Data Catalog | http://localhost:8008 |
| MCP Server | http://localhost:8012 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

**Document Status:** ✅ Complete  
**Last Updated:** December 28, 2025  
**Author:** System Analysis Agent  
**Purpose:** Compello AS Interview Preparation
