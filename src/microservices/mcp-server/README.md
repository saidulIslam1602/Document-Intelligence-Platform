# MCP Server - Document Intelligence Platform

Secure Model Context Protocol (MCP) server for AI agent integration.

## 🔒 Security Features (Newly Implemented!)

### ✅ What's Been Added

This MCP server now includes enterprise-grade security:

1. **JWT Authentication** (`mcp_auth.py`)
   - Valid Bearer tokens required for all operations
   - 24-hour token expiration
   - Secure token generation and validation

2. **Role-Based Access Control (RBAC)** (`mcp_auth.py`)
   - 5 roles: Admin, Developer, Analyst, Viewer, AI Agent
   - Granular permission system
   - Tool and resource-level access control

3. **Rate Limiting** (`mcp_rate_limiter.py`)
   - Redis-backed sliding window algorithm
   - Per-user, per-tool, and global limits
   - Graceful degradation to in-memory fallback

4. **Audit Logging** (`mcp_auth.py`)
   - All tool executions logged
   - Resource access tracking
   - Authentication attempt monitoring

## 📁 Files

- **`main.py`** - Main FastAPI application with secured endpoints
- **`mcp_auth.py`** - Authentication, authorization, and audit logging
- **`mcp_rate_limiter.py`** - Rate limiting implementation
- **`mcp_tools.py`** - MCP tool implementations
- **`mcp_resources.py`** - MCP resource handlers
- **`generate_token.py`** - Helper script to generate JWT tokens
- **`Dockerfile`** - Container configuration

## 🚀 Quick Start

### 1. Generate an Authentication Token

**Option A: Interactive Script**
```bash
cd src/microservices/mcp-server
python generate_token.py
```

**Option B: Get Test Tokens**
```bash
curl http://localhost:8012/mcp/auth/test-tokens
```

**Option C: Python Code**
```python
from mcp_auth import JWTValidator, UserRole

token = JWTValidator.create_token(
    user_id="your_user_id",
    role=UserRole.DEVELOPER
)
print(token)
```

### 2. Test the Server

```bash
# Health check (no auth required)
curl http://localhost:8012/health

# Get your user info (auth required)
TOKEN="your-token-here"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/auth/me

# Execute a tool
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_automation_metrics",
    "parameters": {"time_range": "24h"},
    "context": {}
  }' \
  http://localhost:8012/mcp/tools/execute
```

### 3. Configure Your MCP Client

See the [MCP Client Configuration Guide](../../../docs/MCP_CLIENT_CONFIGURATION_GUIDE.md) for:
- Cursor configuration
- Claude Desktop configuration
- Custom client integration

## 🛠️ Available Tools

The MCP server exposes these tools to AI agents:

| Tool | Description | Required Permission |
|------|-------------|---------------------|
| `extract_invoice_data` | Extract structured invoice data | `mcp:tool:extract_invoice` |
| `validate_invoice` | Validate invoice data | `mcp:tool:validate_invoice` |
| `classify_document` | Classify document type | `mcp:tool:classify_document` |
| `create_fine_tuning_job` | Create Azure OpenAI fine-tuning job | `mcp:tool:create_fine_tuning` |
| `get_automation_metrics` | Get automation metrics | `mcp:tool:get_metrics` |
| `process_m365_document` | Process M365 documents | `mcp:tool:process_m365` |
| `analyze_document_sentiment` | Analyze sentiment | `mcp:tool:analyze_sentiment` |
| `extract_document_entities` | Extract named entities | `mcp:tool:extract_entities` |
| `generate_document_summary` | Generate AI summary | `mcp:tool:generate_summary` |
| `search_documents` | Semantic document search | `mcp:tool:search_documents` |

## 🔐 Role Permissions

### Admin
- **Access**: Full access to all tools and resources
- **Rate Limit**: 500 requests/minute
- **Use Case**: Platform administration and management

### Developer
- **Access**: All processing tools, no admin functions
- **Rate Limit**: 100 requests/minute
- **Use Case**: Development and integration work

### Analyst
- **Access**: Read-only analytics and search
- **Rate Limit**: 100 requests/minute
- **Use Case**: Data analysis and reporting

### Viewer
- **Access**: Limited metrics viewing only
- **Rate Limit**: 100 requests/minute
- **Use Case**: Stakeholder visibility

### AI Agent
- **Access**: Processing tools, no fine-tuning or admin
- **Rate Limit**: 200 requests/minute
- **Use Case**: Autonomous AI agents and bots

## 📊 Rate Limits

| Resource | Limit (per minute) |
|----------|-------------------|
| Global | 1000 |
| Admin user | 500 |
| Developer user | 100 |
| AI Agent | 200 |
| Viewer | 100 |
| **Per-Tool Limits** | |
| Extract invoice | 50 |
| Create fine-tuning | 5 |
| Get metrics | 200 |
| Search | 100 |

Rate limit info is returned in response headers:
- `X-RateLimit-Limit`: Your rate limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Window`: Window size in seconds

## 🔍 Audit Logs

All MCP operations are logged with:
- User ID and role
- Tool/resource accessed
- Parameters used
- Success/failure status
- Execution time
- Timestamp

Logs are available in:
1. Application logs (stdout)
2. Docker logs: `docker logs docintel-mcp-server`
3. (Future) Azure Monitor / Application Insights

## 🌐 API Endpoints

### Public Endpoints (No Auth)

- `GET /health` - Health check
- `GET /mcp/capabilities` - List capabilities
- `GET /mcp/tools` - List available tools
- `GET /mcp/resources` - List available resources
- `GET /mcp/auth/test-tokens` - Get test tokens (dev only)

### Protected Endpoints (Auth Required)

- `POST /mcp/tools/execute` - Execute a tool
- `POST /mcp/resources/read` - Read a resource
- `GET /mcp/auth/me` - Get current user info
- `GET /mcp/rate-limits` - Get rate limit info
- `GET /mcp/permissions` - List permissions

### Convenience Endpoints

- `POST /mcp/invoice/extract` - Extract invoice
- `POST /mcp/invoice/validate` - Validate invoice
- `POST /mcp/document/classify` - Classify document
- `GET /mcp/metrics/automation` - Get automation metrics
- `POST /mcp/fine-tuning/create-job` - Create fine-tuning job
- `POST /mcp/m365/process-document` - Process M365 document

## 🔧 Configuration

### Environment Variables

Required:
```bash
JWT_SECRET_KEY=your-strong-secret-key-here
ENVIRONMENT=development  # or production
```

Optional:
```bash
JWT_EXPIRATION_HOURS=24
REDIS_URL=redis://redis:6379
AI_PROCESSING_URL=http://ai-processing:8001
DATA_QUALITY_URL=http://data-quality:8006
ANALYTICS_URL=http://analytics:8002
DOCUMENT_INGESTION_URL=http://document-ingestion:8000
AI_CHAT_URL=http://ai-chat:8004
```

### Docker Deployment

The MCP server is deployed via docker-compose:

```yaml
mcp-server:
  build:
    context: .
    dockerfile: src/microservices/mcp-server/Dockerfile
  ports:
    - "8012:8012"
  environment:
    - ENVIRONMENT=development
    - REDIS_URL=redis://redis:6379
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

## 🧪 Testing

### Run Unit Tests

```bash
# Test authentication
cd src/microservices/mcp-server
python -m pytest test_mcp_auth.py

# Test rate limiting
python mcp_rate_limiter.py

# Test token generation
python generate_token.py
```

### Manual Testing

```bash
# 1. Get a test token
TOKEN=$(curl -s http://localhost:8012/mcp/auth/test-tokens | jq -r '.tokens.developer')

# 2. Test authentication
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/auth/me

# 3. Test rate limits
for i in {1..5}; do
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8012/mcp/rate-limits
  sleep 1
done

# 4. Test tool execution
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"get_automation_metrics","parameters":{"time_range":"24h"},"context":{}}' \
  http://localhost:8012/mcp/tools/execute
```

## 🐛 Troubleshooting

### "Token has expired"
Generate a new token - they expire after 24 hours.

### "Permission denied"
Check your role has the required permission:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/permissions
```

### "Rate limit exceeded"
Wait for the retry_after period or check your limits:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/rate-limits
```

### "Authentication failed"
- Verify token format (starts with `eyJ`)
- Check Bearer prefix in Authorization header
- Generate a fresh token

### Server not responding
```bash
# Check if running
docker ps | grep mcp-server

# Check logs
docker logs docintel-mcp-server

# Restart
docker-compose restart mcp-server
```

## 📚 Additional Documentation

- [Complete MCP Client Configuration Guide](../../../docs/MCP_CLIENT_CONFIGURATION_GUIDE.md)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Main Project README](../../../README.md)

## 🔐 Security Best Practices

1. **Never commit tokens to git**
2. **Use strong JWT_SECRET_KEY in production**
3. **Disable test token endpoint in production**
4. **Rotate tokens regularly**
5. **Monitor audit logs**
6. **Use HTTPS in production**
7. **Implement IP whitelisting for production**
8. **Regular security audits**

## 🚨 Production Checklist

Before deploying to production:

- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Disable `/mcp/auth/test-tokens` endpoint
- [ ] Enable HTTPS
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Configure proper logging to Azure Monitor
- [ ] Implement user management system
- [ ] Review and adjust rate limits
- [ ] Set up token rotation policy

## 📞 Support

For issues or questions:
1. Check the logs: `docker logs docintel-mcp-server`
2. Review the [Configuration Guide](../../../docs/MCP_CLIENT_CONFIGURATION_GUIDE.md)
3. Test with cURL before using with clients
4. Check audit logs for authentication issues

---

**Version**: 2.0.0 (Security Update)  
**Port**: 8012  
**Protocol**: MCP 0.9.0  
**Last Updated**: December 2025

