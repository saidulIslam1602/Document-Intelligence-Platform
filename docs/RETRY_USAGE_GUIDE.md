# Retry Logic Usage Guide

## Overview
The platform now includes comprehensive retry logic with exponential backoff to handle transient failures gracefully.

## Features
- ✅ Exponential backoff with configurable parameters
- ✅ Jitter to prevent thundering herd
- ✅ Configurable retry counts and delays
- ✅ Type-safe configuration
- ✅ Automatic logging and metrics
- ✅ Both sync and async support
- ✅ Decorator and functional API
- ✅ HTTP-specific retry helpers

## Configuration
All retry settings are configurable via environment variables:

```bash
# Retry configuration
RETRY_MAX_RETRIES=3              # Maximum number of retries
RETRY_INITIAL_DELAY=1.0          # Initial delay in seconds
RETRY_MAX_DELAY=60.0             # Maximum delay in seconds
RETRY_EXPONENTIAL_BASE=2.0       # Exponential base (2 = 1s, 2s, 4s, 8s...)
RETRY_JITTER=true                # Add random jitter (prevents thundering herd)
```

## Basic Usage

### 1. Using the Decorator (Recommended)

```python
from src.shared.resilience import retry

# Async function with automatic retry
@retry(max_retries=3, initial_delay=1.0)
async def fetch_user_data(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/users/{user_id}")
        response.raise_for_status()
        return response.json()

# Sync function with automatic retry
@retry(max_retries=3)
def process_file(file_path: str):
    with open(file_path, 'r') as f:
        return f.read()
```

### 2. Using the Functional API

```python
from src.shared.resilience import retry_with_backoff

async def my_function():
    # Your code here
    pass

# Call with retry
result = await retry_with_backoff(
    my_function,
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)
```

### 3. HTTP-Specific Retry

```python
from src.shared.http import get_with_retry, post_with_retry

# GET request with automatic retry
response = await get_with_retry(
    "https://api.example.com/data",
    headers={"Authorization": f"Bearer {token}"}
)

# POST request with automatic retry
response = await post_with_retry(
    "https://api.example.com/process",
    json={"document_id": "123"},
    max_retries=5  # Override default
)
```

## Advanced Usage

### 1. Retry Specific Exceptions Only

```python
from src.shared.resilience import retry
import httpx

@retry(
    max_retries=3,
    retryable_exceptions=(httpx.ConnectError, httpx.TimeoutException)
)
async def fetch_data():
    # Only retries on connection errors and timeouts
    # Other exceptions are raised immediately
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

### 2. Custom Retry Callback

```python
from src.shared.resilience import retry_with_backoff

async def on_retry_callback(attempt: int, exception: Exception, delay: float):
    """Called on each retry attempt"""
    logger.warning(f"Retry {attempt}: {exception}. Waiting {delay}s...")
    
    # Send metrics to monitoring
    await metrics.increment("retry_attempts", tags={"service": "api"})
    
    # Alert on 3rd retry
    if attempt >= 2:
        await send_alert(f"Service degradation: {attempt} retries")

result = await retry_with_backoff(
    my_function,
    max_retries=5,
    on_retry=on_retry_callback
)
```

### 3. HTTP Retry Decorator

```python
from src.shared.resilience import retry_on_http_error

@retry_on_http_error(
    max_retries=5,
    status_codes=(500, 502, 503, 504, 429)  # Retry on these HTTP codes
)
async def fetch_document(doc_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/docs/{doc_id}")
        response.raise_for_status()
        return response.json()
```

### 4. Connection Error Retry

```python
from src.shared.resilience import retry_on_connection_error

@retry_on_connection_error(max_retries=5)
async def connect_to_database():
    """Retries on connection errors only"""
    return await database.connect()
```

## Real-World Examples

### Example 1: MCP Server Tool with Retry

```python
from src.shared.http import post_with_retry
from src.shared.resilience import retry

class MCPTools:
    @retry(max_retries=3)
    async def extract_invoice_data(self, document_id: str):
        """Extract invoice data with automatic retry"""
        response = await post_with_retry(
            f"{self.ai_processing_url}/process/invoice/extract",
            json={"document_id": document_id},
            timeout=30.0
        )
        return response.json()
```

### Example 2: Form Recognizer with Retry

```python
from src.shared.resilience import retry
from azure.core.exceptions import ServiceRequestError

@retry(
    max_retries=5,
    initial_delay=2.0,
    max_delay=60.0,
    retryable_exceptions=(ServiceRequestError,)
)
async def analyze_invoice_with_retry(document_url: str):
    """Analyze invoice with Form Recognizer, retry on transient errors"""
    poller = await form_recognizer_client.begin_analyze_document_from_url(
        "prebuilt-invoice",
        document_url
    )
    return await poller.result()
```

### Example 3: Database Operations with Retry

```python
from src.shared.resilience import retry
import pyodbc

@retry(
    max_retries=3,
    retryable_exceptions=(pyodbc.OperationalError,)
)
async def save_to_database(data: dict):
    """Save to database with retry on transient errors"""
    async with database_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO invoices VALUES (?, ?, ?)",
            data["id"], data["amount"], data["vendor"]
        )
```

### Example 4: External API with Rate Limiting

```python
from src.shared.resilience import retry
import httpx

async def on_rate_limit(attempt: int, exception: Exception, delay: float):
    """Handle rate limiting specially"""
    if isinstance(exception, httpx.HTTPStatusError):
        if exception.response.status_code == 429:
            # Extract Retry-After header
            retry_after = exception.response.headers.get("Retry-After", delay)
            logger.warning(f"Rate limited. Waiting {retry_after}s")

@retry(
    max_retries=5,
    initial_delay=5.0,  # Longer initial delay for rate limits
    max_delay=300.0,    # Up to 5 minutes
    retryable_exceptions=(httpx.HTTPStatusError,),
    on_retry=on_rate_limit
)
async def call_rate_limited_api(endpoint: str):
    """Call API with retry and rate limit handling"""
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        response.raise_for_status()
        return response.json()
```

## Best Practices

### 1. Choose Appropriate Retry Counts
```python
# Fast APIs: fewer retries
@retry(max_retries=2)
async def fetch_cached_data():
    pass

# External APIs: more retries
@retry(max_retries=5)
async def fetch_external_api():
    pass

# Critical operations: many retries
@retry(max_retries=10, max_delay=300.0)
async def process_payment():
    pass
```

### 2. Set Appropriate Timeouts
```python
# Use with HTTP timeouts
response = await get_with_retry(
    url,
    timeout=30.0,      # 30s timeout per attempt
    max_retries=3      # Total: up to 90s + backoff time
)
```

### 3. Retry Only Transient Errors
```python
# ✅ Good: Retry transient errors only
@retry(retryable_exceptions=(
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.HTTPStatusError,  # 5xx errors
))
async def fetch_data():
    pass

# ❌ Bad: Retrying all exceptions
@retry(retryable_exceptions=(Exception,))  # Don't do this!
async def fetch_data():
    pass
```

### 4. Add Jitter for High-Traffic Systems
```python
# Prevents thundering herd problem
@retry(
    max_retries=3,
    jitter=True  # Randomizes delay slightly
)
async def high_traffic_operation():
    pass
```

### 5. Monitor Retry Metrics
```python
async def monitored_retry(attempt: int, exception: Exception, delay: float):
    """Track retry metrics"""
    await metrics.increment("service.retries", tags={
        "service": "form_recognizer",
        "attempt": attempt,
        "exception": type(exception).__name__
    })
    
    # Alert on excessive retries
    if attempt >= 3:
        await alerts.send("High retry rate detected")

@retry(on_retry=monitored_retry)
async def important_operation():
    pass
```

## Configuration Examples

### Development Environment
```bash
# Fast failures for development
RETRY_MAX_RETRIES=2
RETRY_INITIAL_DELAY=0.5
RETRY_MAX_DELAY=5.0
RETRY_EXPONENTIAL_BASE=2.0
RETRY_JITTER=false
```

### Production Environment
```bash
# More resilient for production
RETRY_MAX_RETRIES=5
RETRY_INITIAL_DELAY=2.0
RETRY_MAX_DELAY=60.0
RETRY_EXPONENTIAL_BASE=2.0
RETRY_JITTER=true
```

### High-Availability Environment
```bash
# Maximum resilience
RETRY_MAX_RETRIES=10
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=300.0
RETRY_EXPONENTIAL_BASE=2.0
RETRY_JITTER=true
```

## Backoff Calculation

With default settings (`initial_delay=1.0`, `exponential_base=2.0`):

| Attempt | Delay (without jitter) | Cumulative Time |
|---------|------------------------|-----------------|
| 1       | 1s                     | 1s              |
| 2       | 2s                     | 3s              |
| 3       | 4s                     | 7s              |
| 4       | 8s                     | 15s             |
| 5       | 16s                    | 31s             |
| 6       | 32s                    | 63s             |
| 7       | 60s (max)              | 123s            |

With jitter enabled, each delay is multiplied by a random factor between 0.5 and 1.5.

## Testing

### Testing with Retry Logic

```python
import pytest
from src.shared.resilience import retry, RetryExhaustedError

@pytest.mark.asyncio
async def test_retry_success_after_failures():
    """Test successful retry after transient failures"""
    call_count = 0
    
    @retry(max_retries=3, initial_delay=0.1)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Transient error")
        return "success"
    
    result = await flaky_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    """Test retry exhaustion"""
    @retry(max_retries=2, initial_delay=0.1)
    async def always_fails():
        raise ConnectionError("Always fails")
    
    with pytest.raises(RetryExhaustedError):
        await always_fails()
```

## Migration Guide

### Before (Manual Retry)
```python
async def fetch_data():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            return response.json()
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
```

### After (Automatic Retry)
```python
from src.shared.http import get_with_retry

async def fetch_data():
    response = await get_with_retry(url)
    return response.json()
```

## Troubleshooting

### Problem: Too Many Retries
**Solution**: Reduce `max_retries` or increase `initial_delay`

### Problem: Retries Too Slow
**Solution**: Reduce `max_delay` or `exponential_base`

### Problem: Thundering Herd
**Solution**: Enable `jitter=true`

### Problem: Not Retrying on Specific Error
**Solution**: Add exception to `retryable_exceptions` tuple

### Problem: Retrying Non-Transient Errors
**Solution**: Specify only transient exceptions in `retryable_exceptions`

## Monitoring

Track these metrics to monitor retry effectiveness:

- `retry_attempts_total`: Total number of retry attempts
- `retry_success_rate`: Percentage of retries that eventually succeed
- `retry_exhausted_total`: Number of times all retries exhausted
- `retry_delay_seconds`: Time spent in retry delays

## Performance Impact

**Positive impacts:**
- ✅ Improved reliability (handles transient failures)
- ✅ Better user experience (automatic recovery)
- ✅ Reduced manual intervention

**Considerations:**
- ⚠️ Increased latency for failed requests
- ⚠️ More load on downstream services
- ⚠️ Potential for cascading failures (use jitter!)

## Summary

The retry logic system provides:

- ✅ **Automatic retry** with exponential backoff
- ✅ **Configurable** via environment variables
- ✅ **Type-safe** configuration
- ✅ **HTTP-optimized** helpers
- ✅ **Flexible** decorator and functional APIs
- ✅ **Observable** with logging and callbacks
- ✅ **Production-ready** with jitter support

Use it everywhere you interact with external services for maximum reliability!

