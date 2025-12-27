# MCP Client Configuration Guide

Complete guide for connecting AI clients (Cursor, Claude Desktop, custom agents) to your Document Intelligence Platform's MCP Server.

## Table of Contents
1. [Security Overview](#security-overview)
2. [Getting Authentication Tokens](#getting-authentication-tokens)
3. [Cursor Configuration](#cursor-configuration)
4. [Claude Desktop Configuration](#claude-desktop-configuration)
5. [Custom Client Integration](#custom-client-integration)
6. [Testing Your Connection](#testing-your-connection)
7. [Troubleshooting](#troubleshooting)

---

## Security Overview

Your MCP server now implements enterprise-grade security:

### ✅ **Implemented Security Features**

1. **JWT Authentication**
   - All requests require valid Bearer tokens
   - Tokens expire after 24 hours
   - Include user_id, role, and metadata

2. **Role-Based Access Control (RBAC)**
   - **Admin**: Full access to all tools and resources
   - **Developer**: Access to processing tools and resources
   - **Analyst**: Read-only access to analytics
   - **Viewer**: Limited metric viewing
   - **AI Agent**: Specialized role for autonomous agents

3. **Rate Limiting**
   - Global: 1000 requests/minute
   - Per-user: 100-500 requests/minute (based on role)
   - Per-tool: 5-200 requests/minute (based on expense)

4. **Audit Logging**
   - All tool executions logged
   - All resource accesses logged
   - Authentication attempts tracked

### 🔐 **Permission Levels**

| Role | Invoice Extract | Fine-Tuning | Analytics | Admin |
|------|----------------|-------------|-----------|-------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| Developer | ✅ | ✅ | ✅ | ❌ |
| Analyst | ❌ | ❌ | ✅ | ❌ |
| Viewer | ❌ | ❌ | 📊 (Read) | ❌ |
| AI Agent | ✅ | ❌ | ✅ | ❌ |

---

## Getting Authentication Tokens

### Method 1: Using the Test Token Endpoint (Development Only)

**⚠️ Only available in development mode!**

```bash
# Get test tokens for all roles
curl http://localhost:8012/mcp/auth/test-tokens

# Response:
{
  "message": "Test tokens generated for development",
  "tokens": {
    "admin": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "developer": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "analyst": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "viewer": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "ai_agent": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Method 2: Using Python Script

```python
# generate_token.py
from mcp_auth import JWTValidator, UserRole

# Create a token for your user
token = JWTValidator.create_token(
    user_id="your_user_id",
    role=UserRole.DEVELOPER,  # or ADMIN, ANALYST, VIEWER, AI_AGENT
    metadata={"email": "user@company.com"}
)

print(f"Your MCP Token: {token}")
```

Run it:
```bash
cd src/microservices/mcp-server
python generate_token.py
```

### Method 3: Using the Token Creation Endpoint

```bash
# Create a custom token (should be admin-protected in production)
curl -X POST "http://localhost:8012/mcp/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john_doe",
    "role": "developer",
    "metadata": {"department": "engineering"}
  }'
```

---

## Cursor Configuration

Cursor can connect to MCP servers through its settings.

### Step 1: Locate Cursor Settings

**On macOS:**
- Cursor → Settings → Features → Model Context Protocol

**On Linux:**
- File → Preferences → Settings → Features → Model Context Protocol

**On Windows:**
- File → Preferences → Settings → Features → Model Context Protocol

### Step 2: Configure MCP Server

Cursor typically uses a configuration file. Create or edit:

**macOS/Linux:**
```bash
~/.cursor/mcp_config.json
```

**Windows:**
```
%APPDATA%\Cursor\mcp_config.json
```

### Step 3: Add Your MCP Server Configuration

```json
{
  "mcpServers": {
    "document-intelligence": {
      "type": "http",
      "url": "http://localhost:8012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
      },
      "name": "Document Intelligence Platform",
      "description": "AI-powered document processing and analytics",
      "capabilities": {
        "tools": true,
        "resources": true,
        "prompts": false
      }
    }
  }
}
```

### Step 4: Replace YOUR_JWT_TOKEN_HERE

1. Get a token using one of the methods above
2. Copy the token (starts with `eyJ...`)
3. Replace `YOUR_JWT_TOKEN_HERE` in the config
4. Save the file

### Step 5: Restart Cursor

Restart Cursor to load the new MCP configuration.

### Step 6: Verify Connection

In Cursor's chat or command palette, you should now see the Document Intelligence tools available:
- `extract_invoice_data`
- `classify_document`
- `search_documents`
- `get_automation_metrics`
- ... and more

### Example Usage in Cursor

```
You: "Extract data from invoice document INV-12345"

Cursor (using MCP):
1. Calls: extract_invoice_data(document_id="INV-12345")
2. Returns structured invoice data
3. Displays results
```

---

## Claude Desktop Configuration

### Step 1: Locate Claude Desktop Config

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Step 2: Edit Configuration

```json
{
  "mcpServers": {
    "document-intelligence": {
      "url": "http://localhost:8012/mcp",
      "apiKey": "YOUR_JWT_TOKEN_HERE",
      "name": "Document Intelligence",
      "description": "Document processing and analytics platform"
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop.

### Step 4: Test in Claude

```
You: What tools do you have available from Document Intelligence?

Claude: I have access to these tools:
- extract_invoice_data: Extract structured data from invoices
- validate_invoice: Validate invoice data
- classify_document: Identify document types
- get_automation_metrics: View automation performance
... and 6 more tools
```

---

## Custom Client Integration

### Using Python

```python
import httpx
import json

class MCPClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get_capabilities(self):
        """Discover available tools and resources"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/mcp/capabilities",
                headers=self.headers
            )
            return response.json()
    
    async def execute_tool(self, tool_name: str, parameters: dict):
        """Execute an MCP tool"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tools/execute",
                headers=self.headers,
                json={
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "context": {}
                }
            )
            return response.json()
    
    async def read_resource(self, resource_uri: str):
        """Read an MCP resource"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/resources/read",
                headers=self.headers,
                json={
                    "resource_uri": resource_uri,
                    "parameters": {}
                }
            )
            return response.json()

# Usage
async def main():
    client = MCPClient(
        base_url="http://localhost:8012",
        token="eyJhbGci..."  # Your JWT token
    )
    
    # Discover capabilities
    capabilities = await client.get_capabilities()
    print(f"Available tools: {len(capabilities['tools'])}")
    
    # Extract invoice
    result = await client.execute_tool(
        "extract_invoice_data",
        {"document_id": "INV-12345"}
    )
    print(f"Invoice data: {result}")
    
    # Read analytics
    metrics = await client.read_resource("analytics://metrics/24h")
    print(f"Metrics: {metrics}")

# Run
import asyncio
asyncio.run(main())
```

### Using JavaScript/TypeScript

```typescript
class MCPClient {
  constructor(
    private baseUrl: string,
    private token: string
  ) {}

  async getCapabilities() {
    const response = await fetch(`${this.baseUrl}/mcp/capabilities`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.json();
  }

  async executeTool(toolName: string, parameters: object) {
    const response = await fetch(`${this.baseUrl}/mcp/tools/execute`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        tool_name: toolName,
        parameters,
        context: {}
      })
    });
    return response.json();
  }

  async readResource(resourceUri: string) {
    const response = await fetch(`${this.baseUrl}/mcp/resources/read`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        resource_uri: resourceUri,
        parameters: {}
      })
    });
    return response.json();
  }
}

// Usage
const client = new MCPClient('http://localhost:8012', 'your-jwt-token');

// Extract invoice
const result = await client.executeTool('extract_invoice_data', {
  document_id: 'INV-12345'
});
console.log('Invoice:', result);
```

### Using cURL

```bash
# Get your token first
TOKEN="eyJhbGci..."

# Discover capabilities
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/capabilities | jq

# Execute tool
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "extract_invoice_data",
    "parameters": {"document_id": "INV-12345"},
    "context": {}
  }' \
  http://localhost:8012/mcp/tools/execute | jq

# Read resource
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_uri": "analytics://metrics/24h",
    "parameters": {}
  }' \
  http://localhost:8012/mcp/resources/read | jq
```

---

## Testing Your Connection

### 1. Health Check

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

### 2. Test Authentication

```bash
TOKEN="your-token-here"

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/auth/me
```

Expected response:
```json
{
  "user_id": "test_developer",
  "role": "developer",
  "permissions": ["mcp:tool:extract_invoice", "..."],
  "total_permissions": 14
}
```

### 3. Test Rate Limits

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/rate-limits
```

Expected response:
```json
{
  "user_id": "test_developer",
  "role": "developer",
  "rate_limit": {
    "requests_per_minute": 100,
    "remaining": 100,
    "window_seconds": 60
  }
}
```

### 4. List Available Tools

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8012/mcp/tools | jq '.tools[].name'
```

Expected output:
```
"extract_invoice_data"
"validate_invoice"
"classify_document"
"create_fine_tuning_job"
"get_automation_metrics"
...
```

### 5. Execute a Test Tool

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_automation_metrics",
    "parameters": {"time_range": "24h"},
    "context": {}
  }' \
  http://localhost:8012/mcp/tools/execute | jq
```

---

## Troubleshooting

### Issue: "Token has expired"

**Solution:**
- Generate a new token using one of the methods above
- Tokens expire after 24 hours
- Update your MCP client configuration with the new token

### Issue: "Permission denied: mcp:tool:extract_invoice"

**Solution:**
- Check your role: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8012/mcp/auth/me`
- Use a token with appropriate role (developer or admin)
- List your permissions: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8012/mcp/permissions`

### Issue: "Rate limit exceeded"

**Solution:**
- Wait for the retry_after seconds indicated in the error
- Check current limits: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8012/mcp/rate-limits`
- If you're an admin, you have higher limits
- Consider spreading requests over time

### Issue: "Authentication failed"

**Solution:**
- Verify token format: Should start with `eyJ`
- Check Bearer prefix: `Authorization: Bearer eyJ...`
- Ensure no extra spaces or newlines in token
- Generate a fresh token

### Issue: Cursor doesn't show MCP tools

**Solution:**
1. Check Cursor version (MCP support requires recent versions)
2. Verify config file location and syntax
3. Restart Cursor completely
4. Check Cursor console for MCP connection errors
5. Try connecting via Claude Desktop first to verify server works

### Issue: "Connection refused" or timeout

**Solution:**
- Verify MCP server is running: `curl http://localhost:8012/health`
- Check Docker: `docker ps | grep mcp-server`
- Check logs: `docker logs docintel-mcp-server`
- Verify port 8012 is not blocked
- If remote, use correct IP/hostname instead of localhost

---

## Best Practices

### 1. Token Management
- Store tokens securely (environment variables, keychain)
- Rotate tokens regularly
- Use different tokens for different applications
- Never commit tokens to git

### 2. Rate Limiting
- Implement exponential backoff for retries
- Cache responses when possible
- Use batch operations when available
- Monitor rate limit headers

### 3. Error Handling
- Always check response status codes
- Log errors for debugging
- Implement retry logic with backoff
- Handle different error types appropriately

### 4. Monitoring
- Check audit logs regularly
- Monitor rate limit usage
- Track tool execution times
- Set up alerts for failures

---

## Production Deployment

### Security Checklist

- [ ] Disable `/mcp/auth/test-tokens` endpoint
- [ ] Implement proper user management system
- [ ] Use HTTPS with valid SSL certificates
- [ ] Set strong JWT_SECRET_KEY in environment
- [ ] Configure firewall rules (allow only trusted IPs)
- [ ] Enable comprehensive audit logging
- [ ] Set up monitoring and alerting
- [ ] Regular security audits
- [ ] Token rotation policy
- [ ] Rate limit tuning based on usage

### Environment Variables

```bash
# Required
JWT_SECRET_KEY=your-strong-secret-key-here
ENVIRONMENT=production

# Optional
JWT_EXPIRATION_HOURS=24
REDIS_URL=redis://redis:6379
```

---

## Support

For issues or questions:
- Check logs: `docker logs docintel-mcp-server`
- Review audit logs for auth issues
- Test with cURL before trying with clients
- Verify all security features are properly configured

---

## Quick Reference

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/mcp/capabilities` | GET | No | List capabilities |
| `/mcp/tools` | GET | No | List tools |
| `/mcp/tools/execute` | POST | Yes | Execute tool |
| `/mcp/resources/read` | POST | Yes | Read resource |
| `/mcp/auth/token` | POST | No* | Create token |
| `/mcp/auth/test-tokens` | GET | No* | Get test tokens |
| `/mcp/auth/me` | GET | Yes | User info |
| `/mcp/rate-limits` | GET | Yes | Rate limit info |
| `/mcp/permissions` | GET | Yes | Permission info |

\* Should be protected in production

### Rate Limits

| Resource | Limit |
|----------|-------|
| Global | 1000/min |
| Admin | 500/min |
| Developer | 100/min |
| AI Agent | 200/min |
| Viewer | 100/min |
| Fine-tuning | 5/min |
| Invoice Extract | 50/min |

---

**Version:** 1.0.0  
**Last Updated:** December 2025  
**Protocol:** MCP 0.9.0

