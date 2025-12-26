# 🚀 Enterprise Document Intelligence & Analytics Platform

[![CI/CD Pipeline](https://github.com/saidulIslam1602/Document-Intelligence-Platform/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/saidulIslam1602/Document-Intelligence-Platform/actions)
[![Azure](https://img.shields.io/badge/Azure-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

A comprehensive, production-ready document processing and analytics platform built on Microsoft Azure. This solution demonstrates advanced microservices architecture, AI/ML capabilities with custom model fine-tuning, intelligent document routing, real-time analytics, database migration tools, and enterprise integration capabilities.

> **Production Ready**: Fully implemented with Azure integration, comprehensive error handling, SQL persistence, real-time monitoring, Docker containerization, intelligent routing system, and production-grade resilience patterns.

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Microservices](#-microservices-overview)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Key Features

### Core Capabilities

#### AI-Powered Document Processing
- **Azure OpenAI Integration**: GPT-4/GPT-4o for document understanding and analysis
- **Azure Form Recognizer**: Advanced OCR, layout analysis, and custom model training
- **Custom ML Models**: Support for Hugging Face models (BERT, BART, DistilBERT, RoBERTa)
- **Intelligent Document Routing**: Automatic selection of optimal processing mode based on complexity analysis

#### Fine-Tuning & LLMOps
- **Azure OpenAI Fine-Tuning**: Industry-specific model customization workflows
- **Automated Training Pipelines**: End-to-end workflow orchestration with quality assessment
- **Real-Time Monitoring**: WebSocket-based training dashboards with live metrics
- **Model Evaluation**: Comprehensive accuracy, precision, recall, and F1-score tracking
- **LLMOps Automation**: Enhanced model lifecycle management with automation metrics

#### LangChain Orchestration
- **Invoice Processing Chain**: Automated upload → extract → validate → classify → store workflow
- **Document Analysis Chain**: Intelligent document summarization and entity extraction
- **Fine-Tuning Workflow Chain**: Automated data preparation, training, and evaluation
- **Multi-Agent Workflow**: Coordinated processing with specialized agents

#### Intelligent Chat & RAG
- **RAG-Based Q&A**: Retrieval-augmented generation for document queries
- **Conversation History**: Multi-turn dialogue management
- **Document Context**: Semantic search with Azure Cognitive Search
- **Streaming Responses**: Real-time answer generation

### Enterprise Architecture

#### Microservices & Event-Driven Design
- **14 Independent Microservices**: Fully containerized with Docker
- **Event Sourcing**: Complete audit trail with domain events
- **CQRS Pattern**: Separate read/write models for optimal performance
- **Service Mesh**: API Gateway for centralized routing and authentication

#### Resilience & Performance
- **Circuit Breaker Pattern**: Prevents cascading failures across services
- **Retry Logic**: Exponential backoff for transient failure handling
- **Connection Pooling**: Optimized database connections with configurable limits
- **HTTP/2 Support**: Enhanced connection efficiency
- **Rate Limiting**: Token bucket algorithm for API quota management
- **Health Checks**: Kubernetes-ready liveness and readiness probes

#### Monitoring & Observability
- **Real-Time Dashboards**: WebSocket-based performance monitoring
- **Prometheus Integration**: Time-series metrics collection
- **Centralized Logging**: Azure Monitor and Application Insights
- **Performance Tracking**: Request latency, throughput, error rates

### Security & Compliance

- **Azure Key Vault**: Centralized secret management with DefaultAzureCredential
- **JWT Authentication**: Secure API access with role-based authorization (RBAC)
- **Encryption**: TLS 1.3 for data in transit, AES-256 for data at rest
- **Data Lineage**: Complete audit trail and relationship mapping
- **Event Sourcing**: Immutable event log for compliance

### Integration & Migration

#### MCP (Model Context Protocol) Server
- **AI-Native Tools**: Expose platform capabilities to Claude, ChatGPT, and other AI agents
- **MCP 0.9.1 Protocol**: Standard compliance with REST endpoints
- **Tool Library**: Invoice extraction, validation, classification, automation metrics
- **Resource Access**: Documents, analytics, automation scores, fine-tuning jobs

#### Database Migration Tools
- **Teradata Migration**: Schema and data migration with teradatasql driver
- **Netezza Migration**: Data warehouse migration support
- **Oracle Migration**: Database and stored procedure conversion with cx_Oracle
- **Schema Converter**: Automated DDL translation across database platforms

#### Microsoft Fabric Integration
- **OneLake**: Unified data lake with Delta Lake support
- **Fabric Data Warehouse**: Serverless SQL pools with auto-scaling
- **Real-Time Intelligence**: KQL queries and stream processing
- **Data Warehouse**: Advanced analytics capabilities

#### M365 Integration
- **Outlook Connector**: Email processing automation
- **Teams Bot**: Document collaboration and chat
- **SharePoint Sync**: Document library integration
- **OneDrive**: Personal file management

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT INTELLIGENCE PLATFORM                    │
│                         (Production-Ready)                           │
├─────────────────────────────────────────────────────────────────────┤
│  Client Layer                                                       │
│  ├── Web Dashboard (FastAPI + Jinja2)                              │
│  ├── API Service (REST)                                            │
│  └── WebSocket Connections (Real-time updates)                     │
├─────────────────────────────────────────────────────────────────────┤
│  Gateway & Load Balancing                                          │
│  ├── Nginx (Rate Limiting, SSL/TLS Termination)                    │
│  └── API Gateway (Authentication, Routing, Rate Limiting)          │
├─────────────────────────────────────────────────────────────────────┤
│  Microservices Layer (14 Services)                                 │
│  ├── Document Ingestion (8000) - Upload, validation                │
│  ├── AI Processing (8001) - AI/ML, fine-tuning, LangChain          │
│  ├── Analytics (8002) - Metrics, automation scoring                │
│  ├── API Gateway (8003) - Auth, routing, validation                │
│  ├── AI Chat (8004) - RAG-based Q&A                                │
│  ├── Batch Processor (8005) - Bulk operations, ETL                 │
│  ├── Data Quality (8006) - Validation, quality scoring             │
│  ├── Data Catalog (8007) - Metadata, lineage tracking              │
│  ├── Performance Dashboard (8008) - Real-time monitoring           │
│  ├── Migration Service - Database migration tools                  │
│  ├── MCP Server (8012) - Model Context Protocol                    │
│  ├── LLM Optimization - Prompt engineering                         │
│  ├── M365 Integration - Microsoft 365 connectors                   │
│  └── Experimentation - A/B testing framework                       │
├─────────────────────────────────────────────────────────────────────┤
│  AI/ML Layer                                                        │
│  ├── Azure OpenAI (GPT-4o, GPT-4o-mini, Embeddings)                │
│  ├── Azure Form Recognizer (Layout, Custom Models)                 │
│  ├── Hugging Face Models (BERT, BART, DistilBERT, RoBERTa)         │
│  └── Azure Cognitive Search (Vector, Semantic, Hybrid)             │
├─────────────────────────────────────────────────────────────────────┤
│  Shared Infrastructure                                              │
│  ├── Intelligent Router - Complexity-based routing                 │
│  ├── HTTP Client Pool - Connection pooling with HTTP/2             │
│  ├── Circuit Breaker - Fault tolerance                             │
│  ├── Retry Logic - Exponential backoff                             │
│  ├── Rate Limiter - Token bucket algorithm                         │
│  ├── Health Monitor - Kubernetes probes                            │
│  └── Caching Layer - Redis for hot data                            │
├─────────────────────────────────────────────────────────────────────┤
│  Event & Messaging                                                  │
│  ├── Azure Event Hubs (Event streaming)                            │
│  ├── Azure Service Bus (Message queuing)                           │
│  ├── Event Sourcing (Domain events, audit trail)                   │
│  └── Redis (Caching, Pub/Sub)                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Data Layer                                                         │
│  ├── Azure SQL Database (Primary storage, connection pooling)      │
│  ├── Azure Blob Storage (Document storage, tiered)                 │
│  ├── Azure Data Lake Gen2 (Analytics, raw/curated zones)           │
│  └── Microsoft Fabric (OneLake, Data Warehouse)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Monitoring & Security                                              │
│  ├── Azure Key Vault (Secret management)                           │
│  ├── Azure Monitor (Application Insights, Log Analytics)           │
│  ├── Prometheus (Metrics collection)                               │
│  └── RBAC & Azure AD (Authentication, authorization)               │
└─────────────────────────────────────────────────────────────────────┘
```

### Architectural Patterns

- **Microservices**: 14 independent, scalable services with clear boundaries
- **Event-Driven**: Asynchronous communication via Azure Event Hubs and Service Bus
- **Event Sourcing**: Complete audit trail with immutable domain events
- **CQRS**: Separate read/write models for optimal performance
- **API Gateway**: Centralized authentication, rate limiting, and routing
- **Circuit Breaker**: Fault tolerance with automatic failure detection
- **Connection Pooling**: Optimized database connections with configurable limits
- **Caching Strategy**: Redis for hot data, reducing database load
- **Health Checks**: Liveness and readiness probes for Kubernetes
- **Retry Logic**: Exponential backoff for transient failures
- **Rate Limiting**: Token bucket algorithm for API quota management

---

## 📦 Microservices Overview

### Core Processing Services

#### 1. Document Ingestion Service
**Port**: 8000 | **Tech**: FastAPI, Azure Blob Storage

- Document upload and validation (PDF, DOCX, images)
- Metadata extraction and storage
- Azure Blob Storage integration (Hot/Cool/Archive tiers)
- Event publishing for processing pipeline

#### 2. AI Processing Service
**Port**: 8001 | **Tech**: Azure OpenAI, Form Recognizer, LangChain

- Azure OpenAI integration (GPT-4o, embeddings, fine-tuning)
- Azure Form Recognizer (layout analysis, custom models)
- LangChain orchestration (invoice, document analysis workflows)
- Fine-tuning workflow orchestration
- ML model inference (BERT, BART, DistilBERT)
- Enhanced LLMOps with automation tracking
- Intelligent document routing integration

#### 3. Analytics Service
**Port**: 8002 | **Tech**: Pandas, Azure Synapse, Power BI

- Real-time metrics aggregation
- Automation scoring system
- Power BI integration
- Custom report generation
- Statistical analysis and trend detection

#### 4. AI Chat Service
**Port**: 8004 | **Tech**: RAG, Vector Search, GPT-4o

- Conversational AI with RAG architecture
- Document Q&A with context retrieval
- Conversation history management
- Semantic search integration
- Streaming response generation

### Gateway & Infrastructure Services

#### 5. API Gateway Service
**Port**: 8003 | **Tech**: FastAPI, JWT, Rate Limiting

- JWT-based authentication
- Role-based access control (RBAC)
- Request validation with Pydantic
- Service routing and load balancing
- Rate limiting (configurable per client)
- Circuit breaker and retry status endpoints

#### 6. Batch Processor Service
**Port**: 8005 | **Tech**: Celery, Azure Data Factory

- Bulk document processing
- ETL pipeline orchestration
- Scheduled job execution
- Data transformation workflows
- Error handling and retry logic

### Data & Quality Services

#### 7. Data Quality Service
**Port**: 8006 | **Tech**: Great Expectations, Pandas

- Data validation rules engine
- Quality scoring and metrics
- Anomaly detection
- Data profiling and statistics
- Automated quality reports

#### 8. Data Catalog Service
**Port**: 8007 | **Tech**: Apache Atlas concepts, NetworkX

- Metadata management and discovery
- Data lineage tracking (upstream/downstream)
- Relationship mapping and visualization
- Business glossary
- Data governance compliance

### Monitoring & Optimization Services

#### 9. Performance Dashboard Service
**Port**: 8008 | **Tech**: WebSocket, FastAPI, Prometheus

- Real-time metrics via WebSocket
- System health monitoring
- Prometheus metrics integration
- Alert management
- Performance percentiles (P50, P95, P99)

#### 10. LLM Optimization Service
**Tech**: OpenAI, Prompt Engineering

- Advanced prompt templates
- Chain-of-thought reasoning
- Few-shot learning
- Prompt validation and security
- Reusable template library

### Integration Services

#### 11. MCP Server
**Port**: 8012 | **Tech**: FastAPI, MCP Protocol 0.9.1

- Model Context Protocol implementation
- AI-native tools for external agents
- Invoice extraction, validation, classification
- Automation metrics exposure
- Resource access (documents, analytics, jobs)

#### 12. M365 Integration Service
**Tech**: Microsoft Graph API

- Outlook email processing
- Teams bot integration
- SharePoint document sync
- OneDrive file management
- M365 Copilot extensions

### Enterprise Services

#### 13. Experimentation Service
**Tech**: Statsmodels, SciPy

- A/B testing framework
- Statistical significance testing
- Bayesian analysis
- Experiment tracking
- Traffic splitting

#### 14. Migration Service
**Tech**: pyodbc, teradatasql, cx_Oracle

- Teradata to Azure SQL migration
- Netezza data warehouse migration
- Oracle database migration
- Schema converter (automated DDL translation)
- Data validation and integrity checks

---

## 🛠️ Technology Stack

### Core Technologies

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.11+ |
| **Web Framework** | FastAPI, Uvicorn |
| **Data Validation** | Pydantic, Pydantic-Settings |
| **Async Runtime** | asyncio, httpx, aiofiles |
| **Containerization** | Docker, Docker Compose |
| **IaC** | Azure Bicep |
| **CI/CD** | GitHub Actions |

### Azure Services

| Service | Purpose |
|---------|---------|
| **Azure OpenAI** | GPT-4o, GPT-4o-mini, embeddings, fine-tuning |
| **Azure Form Recognizer** | OCR, layout analysis, custom models |
| **Azure SQL Database** | Primary data storage with connection pooling |
| **Azure Blob Storage** | Document storage (Hot/Cool/Archive) |
| **Azure Data Lake Gen2** | Analytics data storage |
| **Azure Key Vault** | Secret management with DefaultAzureCredential |
| **Azure Event Hubs** | Event streaming |
| **Azure Service Bus** | Message queuing |
| **Azure Cognitive Search** | Vector search, semantic search, hybrid retrieval |
| **Azure Monitor** | Application Insights, Log Analytics |
| **Microsoft Fabric** | OneLake, Data Warehouse, Real-time Intelligence |

### Data & Analytics

| Technology | Use Case |
|------------|----------|
| **Pandas** | Data manipulation and analysis |
| **NumPy** | Numerical computing |
| **Polars** | High-performance DataFrames |
| **PyArrow** | Columnar data processing |
| **NetworkX** | Graph analysis for lineage tracking |
| **SciPy** | Statistical analysis |

### AI/ML Libraries

| Library | Purpose |
|---------|---------|
| **Transformers** | Hugging Face model integration |
| **Torch** | Deep learning |
| **TensorFlow** | ML model training |
| **Scikit-learn** | Classical machine learning |
| **LangChain** | LLM orchestration and chains |
| **LangChain-OpenAI** | Azure OpenAI integration |
| **TikToken** | Token counting |

### Database Drivers

| Driver | Database |
|--------|----------|
| **pyodbc** | Azure SQL, SQL Server |
| **teradatasql** | Teradata migration |
| **cx_Oracle** | Oracle migration |
| **psycopg2-binary** | PostgreSQL |
| **PyMySQL** | MySQL |

### Infrastructure & Monitoring

| Technology | Purpose |
|------------|---------|
| **Redis** | Caching, Pub/Sub |
| **Prometheus** | Metrics collection |
| **Nginx** | Load balancing, SSL termination |
| **Docker** | Containerization |
| **Docker Compose** | Local orchestration |

### Testing & Quality

| Tool | Purpose |
|------|---------|
| **pytest** | Unit and integration testing |
| **pytest-asyncio** | Async test support |
| **pytest-cov** | Code coverage |
| **httpx** | HTTP client testing |

---

## 🚀 Getting Started

### Prerequisites

- **Azure Subscription** with contributor access
- **Python 3.11+** installed
- **Docker Desktop** (latest version)
- **Azure CLI** installed
- **Git** for version control
- **Minimum 4GB RAM** for local development

### Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/saidulIslam1602/Document-Intelligence-Platform.git
cd Document-Intelligence-Platform
```

#### 2. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit with your Azure credentials
nano .env
```

**Required Environment Variables**:

```bash
# Azure Services
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_ACCOUNT_KEY=your_storage_key
AZURE_SQL_SERVER=your_sql_server.database.windows.net
AZURE_SQL_DATABASE=your_database
AZURE_SQL_USERNAME=your_username
AZURE_SQL_PASSWORD=your_password

# Azure OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_DEPLOYMENT=gpt-4o

# Azure Form Recognizer
FORM_RECOGNIZER_ENDPOINT=https://your-formrecognizer.cognitiveservices.azure.com/
FORM_RECOGNIZER_KEY=your_form_recognizer_key

# Security
JWT_SECRET_KEY=your-secret-key-here
KEY_VAULT_URL=https://your-keyvault.vault.azure.net/

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# For testing only
pip install -r requirements-test.txt
```

#### 4. Start Services with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

#### 5. Access the Platform

- **Web Dashboard**: http://localhost:5000
- **API Documentation**: http://localhost:8003/docs
- **Performance Dashboard**: http://localhost:8008
- **Prometheus Metrics**: http://localhost:9090
- **MCP Server**: http://localhost:8012

### Azure Deployment

#### 1. Deploy Infrastructure

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "your-subscription-id"

# Deploy using Bicep
az deployment group create \
  --resource-group document-intelligence-rg \
  --template-file infrastructure/main.bicep \
  --parameters environment=production

# Or use deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

#### 2. Configure Secrets

```bash
# Set Key Vault secrets
az keyvault secret set \
  --vault-name your-keyvault \
  --name "openai-api-key" \
  --value "your-openai-key"
```

#### 3. Run Database Migrations

```bash
# Execute SQL schema migrations
python -m alembic upgrade head
```

### Testing

```bash
# Run all unit tests (skip integration tests)
pytest tests/ -m "not integration" -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_unit.py -v

# Quick validation
python tests/quick_test.py
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

### Quick Start Guides
- **[Quick Start](docs/QUICK_START.md)** - Get started in 5 minutes
- **[Quick Start: Intelligent Routing](docs/QUICK_START_INTELLIGENT_ROUTING.md)** - Intelligent routing setup

### Complete Guides
- **[Integration Guide](docs/INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Intelligent Routing Guide](docs/INTELLIGENT_ROUTING_GUIDE.md)** - Routing system documentation
- **[Azure Deployment Guide](docs/COMPREHENSIVE_AZURE_GUIDE.md)** - Detailed Azure deployment

### Implementation Documentation
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Complete implementation details
- **[Enhancements README](docs/ENHANCEMENTS_README.md)** - v2.0 feature overview
- **[Validation Checklist](docs/VALIDATION_CHECKLIST.md)** - Pre-deployment validation

### Technical Guides
- **[Retry Logic Usage](docs/RETRY_USAGE_GUIDE.md)** - Retry pattern implementation
- **[Circuit Breaker Usage](docs/CIRCUIT_BREAKER_USAGE_GUIDE.md)** - Circuit breaker pattern
- **[CI/CD Fix Documentation](docs/CI_CD_FIX.md)** - CI/CD pipeline configuration

### Analysis & Reports
- **[Comprehensive Analysis](docs/COMPREHENSIVE_ANALYSIS_AND_ENHANCEMENTS.md)** - Platform analysis
- **[Implementation Progress](docs/IMPLEMENTATION_PROGRESS.md)** - Progress tracking
- **[Project Completion Report](docs/PROJECT_COMPLETION_REPORT.md)** - Achievement summary

---

## 📁 Project Structure

```
Document-Intelligence-Platform/
├── docs/                          # Comprehensive documentation (15+ guides)
├── infrastructure/                # Azure Bicep IaC templates
├── nginx/                         # Load balancer configuration
├── monitoring/                    # Prometheus configuration
├── scripts/                       # Deployment & utility scripts
├── src/
│   ├── microservices/             # 14 microservices
│   │   ├── document-ingestion/    # Upload & validation
│   │   ├── ai-processing/         # AI/ML, fine-tuning, LangChain
│   │   ├── analytics/             # Metrics, automation scoring
│   │   ├── ai-chat/               # RAG-based chat
│   │   ├── api-gateway/           # Auth, routing, rate limiting
│   │   ├── batch-processor/       # Bulk operations
│   │   ├── data-quality/          # Validation, quality scoring
│   │   ├── data-catalog/          # Metadata, lineage
│   │   ├── performance-dashboard/ # Real-time monitoring
│   │   ├── mcp-server/            # Model Context Protocol
│   │   ├── llm-optimization/      # Prompt engineering
│   │   ├── m365-integration/      # Microsoft 365 connectors
│   │   ├── experimentation/       # A/B testing
│   │   └── data-pipeline/         # Stream processing
│   ├── services/                  # Enterprise services
│   │   ├── migration-service/     # Database migration tools
│   │   ├── fabric-integration/    # Microsoft Fabric
│   │   └── demo-service/          # PoC framework
│   ├── shared/                    # Shared libraries
│   │   ├── auth/                  # Authentication
│   │   ├── cache/                 # Redis caching
│   │   ├── config/                # Configuration management
│   │   ├── events/                # Event sourcing
│   │   ├── health/                # Health check system
│   │   ├── http/                  # HTTP client pool
│   │   ├── monitoring/            # Performance monitoring
│   │   ├── rate_limiting/         # Rate limiter
│   │   ├── resilience/            # Circuit breaker, retry
│   │   ├── routing/               # Intelligent router
│   │   ├── services/              # Common services
│   │   ├── storage/               # SQL, Blob, Data Lake
│   │   └── utils/                 # Utilities
│   └── web/                       # Web applications
├── tests/                         # Test suite
│   ├── test_unit.py               # Unit tests
│   ├── test_integration.py        # Integration tests
│   ├── quick_test.py              # Quick validation
│   └── demo_script.py             # Demo script
├── docker-compose.yml             # Local development
├── requirements.txt               # Python dependencies
├── requirements-test.txt          # Test dependencies
├── setup.cfg                      # Pytest configuration
└── README.md                      # This file
```

---

## 🤝 Contributing

We welcome contributions to improve the Document Intelligence Platform!

### How to Contribute

1. **Fork the Repository**
```bash
git clone https://github.com/saidulIslam1602/Document-Intelligence-Platform.git
cd Document-Intelligence-Platform
```

2. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

3. **Make Your Changes**
- Follow Python PEP 8 style guidelines
- Add comprehensive docstrings
- Include type hints
- Write unit tests for new features
- Update documentation

4. **Run Tests**
```bash
pytest tests/ -m "not integration" -v
```

5. **Commit Your Changes**
```bash
git add .
git commit -m "Add feature: description"
```

6. **Push to Your Fork**
```bash
git push origin feature/your-feature-name
```

7. **Open a Pull Request**
- Provide clear description
- Reference related issues
- Ensure CI/CD pipeline passes

### Development Guidelines

- **Code Style**: Follow PEP 8, use type hints
- **Documentation**: Update README and inline docs
- **Testing**: Maintain test coverage
- **Commits**: Use descriptive commit messages
- **Security**: Never commit secrets or credentials

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ❌ Liability
- ❌ Warranty

---

## 🌟 Key Differentiators

### Production-Ready Implementation
- Complete Azure integration with Key Vault
- Comprehensive error handling and logging
- SQL-based persistence for all workflows
- Docker containerization for all 14 microservices
- Production-grade resilience patterns

### Advanced Architecture
- True microservices with independent deployability
- Event-driven design with Event Hubs and Service Bus
- Intelligent document routing with complexity analysis
- Connection pooling and HTTP/2 support
- Circuit breaker and retry mechanisms
- Health checks for Kubernetes
- Rate limiting with token bucket algorithm

### AI/ML Capabilities
- Custom Azure OpenAI fine-tuning workflows
- RAG-based intelligent chat
- LangChain orchestration for complex workflows
- Multi-model support (GPT-4o, BERT, BART, DistilBERT)
- Real-time training monitoring via WebSockets
- Automated model evaluation and deployment

### Enterprise Features
- Database migration tools (Teradata, Netezza, Oracle)
- Microsoft Fabric integration (OneLake, Data Warehouse)
- Data lineage tracking and cataloging
- M365 integration (Teams, Outlook, SharePoint)
- A/B testing framework
- PoC generation tools

---

## 💼 Use Cases

### Financial Services
- Invoice processing automation
- Contract analysis and risk assessment
- Regulatory compliance checking
- Fraud detection in financial documents

### Healthcare
- Medical records extraction
- Clinical notes structuring
- Insurance claims processing
- HIPAA-compliant document handling

### Legal
- Contract review automation
- Due diligence document analysis
- Legal research and case law search
- E-discovery at scale

### Manufacturing
- Quality report analysis
- Maintenance log insights
- Supply chain documentation
- Compliance tracking

### Retail
- Product catalog extraction
- Customer feedback analysis
- Supplier invoice automation
- Inventory documentation

---

## 🎯 Roadmap

### Completed ✅
- [x] 14 microservices implementation
- [x] Azure OpenAI fine-tuning integration
- [x] RAG-based chat functionality
- [x] LangChain orchestration
- [x] Intelligent document routing
- [x] Database migration tools
- [x] Microsoft Fabric integration
- [x] MCP Server implementation
- [x] Resilience patterns (circuit breaker, retry, rate limiting)
- [x] Health check system
- [x] Real-time performance monitoring
- [x] Azure Key Vault integration
- [x] Docker containerization
- [x] CI/CD pipeline
- [x] Comprehensive documentation

### In Progress 🚧
- [ ] Azure Container Apps deployment
- [ ] Power BI embedded dashboards
- [ ] Advanced security features
- [ ] Multi-language support

### Future Enhancements 📋
- [ ] Kubernetes orchestration
- [ ] GraphQL API
- [ ] Advanced AI agents
- [ ] Edge computing support

---

## 📞 Support & Contact

### Getting Help
- **Documentation**: Browse the [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/saidulIslam1602/Document-Intelligence-Platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/saidulIslam1602/Document-Intelligence-Platform/discussions)

### Connect
- **GitHub**: [@saidulIslam1602](https://github.com/saidulIslam1602)
- **LinkedIn**: [Md Saidul Islam](https://www.linkedin.com/in/mdsaidulislam1602/)

---

## ⭐ Star This Repository!

If you find this project helpful:
- ⭐ **Star** the repository
- 🍴 **Fork** for your own projects
- 📢 **Share** with your network
- 🐛 **Report** issues or bugs
- 💡 **Suggest** new features

---

**Built with ❤️ for the Azure and AI/ML community**

![GitHub stars](https://img.shields.io/github/stars/saidulIslam1602/Document-Intelligence-Platform?style=social)
![GitHub forks](https://img.shields.io/github/forks/saidulIslam1602/Document-Intelligence-Platform?style=social)

**Last Updated**: December 2025
