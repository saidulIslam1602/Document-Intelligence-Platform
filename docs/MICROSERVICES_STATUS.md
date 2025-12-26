# Microservices Status and Access Guide

## Currently Working Microservices

### Document Ingestion Service
- **Status**: FULLY OPERATIONAL
- **Port**: 8000
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Features**:
  - Single document upload
  - Batch upload (10-15 documents)
  - Document status tracking
  - File validation and processing

**Endpoints**:
- POST /documents/upload - Upload single document
- POST /documents/batch-upload - Upload multiple documents (10-15)
- GET /documents/{document_id}/status - Check document status
- GET /health - Health check

---

## Monitoring and Infrastructure Services

### Prometheus (Metrics)
- **Status**: RUNNING
- **Port**: 9090
- **URL**: http://localhost:9090
- **Purpose**: Metrics collection and monitoring

### Grafana (Dashboards)
- **Status**: RUNNING
- **Port**: 3000
- **URL**: http://localhost:3000
- **Purpose**: Visualization dashboards
- **Default Credentials**: admin/admin

### Jaeger (Tracing)
- **Status**: RUNNING
- **Port**: 16686
- **URL**: http://localhost:16686
- **Purpose**: Distributed tracing

### Elasticsearch
- **Status**: RUNNING
- **Port**: 9200
- **URL**: http://localhost:9200
- **Purpose**: Log storage and search

### Kibana (Logs)
- **Status**: RUNNING
- **Port**: 5601
- **URL**: http://localhost:5601
- **Purpose**: Log visualization and analysis

### Redis (Cache)
- **Status**: RUNNING
- **Port**: 6382
- **Purpose**: Caching and session storage

---

## Microservices Requiring Fixes

The following microservices need additional configuration to start properly:

### AI Processing Service
- **Port**: 8001
- **Status**: Restarting (import errors)
- **Issue**: Module import path issues
- **Planned Features**: Document AI processing, OCR, form recognition

### Analytics Service
- **Port**: 8002
- **Status**: Restarting
- **Planned Features**: Analytics and reporting

### API Gateway
- **Port**: 8003
- **Status**: Restarting
- **Planned Features**: Unified API gateway, routing, authentication

### AI Chat Service
- **Port**: 8004
- **Status**: Restarting
- **Planned Features**: AI-powered chat interface

### Performance Dashboard
- **Port**: 8005
- **Status**: Starting
- **Planned Features**: Performance metrics dashboard

### Data Quality Service
- **Port**: 8006
- **Status**: Restarting
- **Planned Features**: Data quality checks and validation

### Batch Processor
- **Port**: 8007
- **Status**: Restarting
- **Planned Features**: Batch processing workflows

### Data Catalog
- **Port**: 8008
- **Status**: Restarting
- **Planned Features**: Data catalog and lineage tracking

---

## Quick Start Guide

### 1. Upload a Single Document

```bash
curl -X POST "http://localhost:8000/documents/upload?document_type=invoice" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

### 2. Upload Multiple Documents (Batch)

```bash
curl -X POST "http://localhost:8000/documents/batch-upload?document_type=invoice" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf"
```

### 3. Check Document Status

```bash
curl http://localhost:8000/documents/{document_id}/status
```

### 4. View API Documentation

Open in browser: http://localhost:8000/docs

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User/Client                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         Document Ingestion Service (Port 8000)              │
│         - Single Upload                                     │
│         - Batch Upload (10-15 docs)                         │
│         - Validation & Storage                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
│  - Blob Storage (files)                                     │
│  - SQL Database (metadata)                                  │
│  - Data Lake (analytics)                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 Monitoring Stack                            │
│  - Prometheus (metrics)                                     │
│  - Grafana (dashboards)                                     │
│  - Jaeger (tracing)                                         │
│  - Elasticsearch + Kibana (logs)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Development Mode

Currently running in development mode:
- No authentication required
- Azure services optional
- Local file storage
- All operations logged

---

## Next Steps

To enable additional microservices:
1. Fix module import paths in each service
2. Configure Azure service connections (optional)
3. Rebuild and restart services
4. Test each endpoint

---

## Support

- **Documentation**: docs/ directory
- **Logs**: `docker logs docintel-<service-name>`
- **Health Checks**: `http://localhost:<port>/health`
- **API Docs**: `http://localhost:<port>/docs`

