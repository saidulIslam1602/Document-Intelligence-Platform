# Circuit Breaker Usage Guide

## Overview
The circuit breaker pattern prevents cascading failures by automatically stopping requests to failing services, allowing them time to recover.

## How It Works

### States
1. **CLOSED** (Normal)
   - All requests pass through
   - Failures are counted
   - Transitions to OPEN after reaching failure threshold

2. **OPEN** (Failure)
   - All requests fail fast (no execution)
   - Saves resources by not calling failing service
   - Transitions to HALF_OPEN after timeout

3. **HALF_OPEN** (Testing)
   - Allows one request to test if service recovered
   - Success → CLOSED (service recovered)
   - Failure → OPEN (service still failing)

### State Transitions

```
CLOSED ─(failures ≥ threshold)─> OPEN
  ↑                                 │
  │                                 │
  │                          (timeout elapsed)
  │                                 │
  │                                 ↓
  └────(success)──────────── HALF_OPEN
                                    │
                              (failure)
                                    │
                                    ↓
                                  OPEN
```

## Configuration

All circuit breaker settings are configurable via environment variables:

```bash
# Circuit breaker settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5     # Failures before opening
CIRCUIT_BREAKER_TIMEOUT=60.0            # Seconds before trying half-open
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=30.0  # Seconds in half-open state
CIRCUIT_BREAKER_ENABLED=true            # Enable/disable circuit breakers
```

## Basic Usage

### 1. Using the Decorator (Recommended)

```python
from src.shared.resilience import circuit_breaker

@circuit_breaker("external_api", failure_threshold=5, timeout=60.0)
async def call_external_api():
    response = await client.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()
```

### 2. Using CircuitBreaker Directly

```python
from src.shared.resilience import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    name="payment_service",
    failure_threshold=3,
    timeout=30.0
)

# Use it
try:
    result = await breaker.call(payment_service.process, payment_data)
except CircuitBreakerError:
    # Circuit is open, service is down
    return {"error": "Payment service temporarily unavailable"}
```

### 3. Using Convenience Decorators

```python
from src.shared.resilience import (
    form_recognizer_circuit_breaker,
    openai_circuit_breaker,
    database_circuit_breaker,
    redis_circuit_breaker
)

@form_recognizer_circuit_breaker
async def analyze_invoice(document_url: str):
    result = await form_recognizer.analyze_document(document_url)
    return result

@openai_circuit_breaker
async def generate_summary(text: str):
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Summarize: {text}"}]
    )
    return response.choices[0].message.content
```

## Real-World Examples

### Example 1: Form Recognizer with Circuit Breaker

```python
from src.shared.resilience import form_recognizer_circuit_breaker

@form_recognizer_circuit_breaker
async def analyze_invoice_with_protection(document_url: str):
    """
    Analyze invoice with circuit breaker protection
    If Form Recognizer is down, circuit opens and requests fail fast
    """
    poller = await form_recognizer_client.begin_analyze_document_from_url(
        "prebuilt-invoice",
        document_url
    )
    result = await poller.result()
    return result.documents[0]

# Usage
try:
    invoice_data = await analyze_invoice_with_protection(url)
    print(f"Invoice analyzed: {invoice_data}")
except CircuitBreakerError as e:
    print(f"Circuit breaker open: {e}")
    # Fallback: queue for later processing
    await queue_for_retry(url)
```

### Example 2: Database with Circuit Breaker + Retry

```python
from src.shared.resilience import database_circuit_breaker, retry

@database_circuit_breaker
@retry(max_retries=3)
async def save_to_database(data: dict):
    """
    Save to database with circuit breaker + retry
    - Retry handles transient errors (connection timeout, etc.)
    - Circuit breaker prevents repeated failures from cascading
    """
    async with database_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO documents VALUES (?, ?, ?)",
            data["id"], data["name"], data["content"]
        )

# Usage
try:
    await save_to_database(document_data)
except CircuitBreakerError:
    # Database circuit is open
    logger.error("Database is down, circuit breaker open")
    # Fallback: save to temporary storage
    await save_to_temp_storage(document_data)
except RetryExhaustedError:
    # Retry failed but circuit not yet open
    logger.error("Database save failed after retries")
```

### Example 3: Multiple Services with Circuit Breakers

```python
from src.shared.resilience import circuit_breaker, CircuitBreakerError

class DocumentProcessor:
    @circuit_breaker("form_recognizer")
    async def extract_data(self, url: str):
        return await form_recognizer.analyze(url)
    
    @circuit_breaker("openai")
    async def generate_summary(self, text: str):
        return await openai.complete(text)
    
    @circuit_breaker("database")
    async def save_result(self, data: dict):
        return await database.insert(data)
    
    async def process_document(self, url: str):
        """Process with circuit breaker protection at each step"""
        try:
            # Step 1: Extract data
            data = await self.extract_data(url)
        except CircuitBreakerError:
            logger.error("Form Recognizer circuit open, using fallback")
            data = await self.fallback_extract(url)
        
        try:
            # Step 2: Generate summary
            summary = await self.generate_summary(data["text"])
        except CircuitBreakerError:
            logger.warning("OpenAI circuit open, skipping summary")
            summary = "Summary unavailable"
        
        try:
            # Step 3: Save result
            await self.save_result({"data": data, "summary": summary})
        except CircuitBreakerError:
            logger.error("Database circuit open, queuing for later")
            await self.queue_for_later(data, summary)
        
        return {"status": "completed", "data": data}
```

## Monitoring

### Check Circuit Breaker States

```bash
# Get all circuit breaker states
curl http://localhost:8003/circuit-breakers | jq

# Response:
{
  "timestamp": "2025-12-26T10:00:00Z",
  "summary": {
    "total_breakers": 5,
    "open": 1,
    "half_open": 0,
    "closed": 4,
    "health": "degraded"
  },
  "breakers": {
    "form_recognizer": {
      "name": "form_recognizer",
      "state": "closed",
      "failure_count": 0,
      "failure_threshold": 3,
      "total_requests": 1523,
      "total_successes": 1520,
      "total_failures": 3,
      "total_rejections": 0,
      "success_rate": 99.8,
      "rejection_rate": 0.0
    },
    "openai": {
      "name": "openai",
      "state": "open",
      "failure_count": 0,
      "failure_threshold": 3,
      "total_requests": 834,
      "total_successes": 750,
      "total_failures": 34,
      "total_rejections": 50,
      "success_rate": 89.9,
      "rejection_rate": 6.0,
      "time_until_retry": 45.3
    }
  }
}
```

### Reset Circuit Breaker

```bash
# Reset specific circuit breaker
curl -X POST http://localhost:8003/circuit-breakers/openai/reset

# Reset all circuit breakers (use with caution!)
curl -X POST http://localhost:8003/circuit-breakers/reset-all
```

### Programmatic Monitoring

```python
from src.shared.resilience import CircuitBreakerRegistry

# Get all circuit breakers
breakers = CircuitBreakerRegistry.get_all()

# Check specific breaker state
openai_breaker = CircuitBreakerRegistry.get("openai")
state = openai_breaker.get_state()

if state["state"] == "open":
    logger.error(f"OpenAI circuit is open! Time until retry: {state['time_until_retry']}s")
    # Send alert
    await send_alert("OpenAI circuit breaker opened")

# Get all states
all_states = CircuitBreakerRegistry.get_all_states()
for name, state in all_states.items():
    print(f"{name}: {state['state']} (success_rate: {state['success_rate']:.1f}%)")
```

## Best Practices

### 1. Choose Appropriate Thresholds

```python
# Fast APIs with high availability: Low threshold
@circuit_breaker("cache_service", failure_threshold=2, timeout=10.0)
async def get_from_cache(key: str):
    return await cache.get(key)

# External APIs with occasional issues: Medium threshold
@circuit_breaker("payment_api", failure_threshold=5, timeout=60.0)
async def process_payment(data: dict):
    return await payment_service.process(data)

# Critical internal services: High threshold
@circuit_breaker("database", failure_threshold=10, timeout=120.0)
async def query_database(sql: str):
    return await database.execute(sql)
```

### 2. Provide Fallbacks

```python
@circuit_breaker("recommendation_service")
async def get_recommendations(user_id: str):
    try:
        return await recommendation_api.get(user_id)
    except CircuitBreakerError:
        # Fallback: return default recommendations
        logger.warning(f"Recommendation service circuit open for user {user_id}")
        return await get_default_recommendations()
```

### 3. Combine with Retry Logic

```python
from src.shared.resilience import circuit_breaker, retry

# Circuit breaker first, then retry
# This prevents retries when circuit is open
@circuit_breaker("external_api")
@retry(max_retries=3)
async def call_api():
    return await api.call()
```

### 4. Monitor and Alert

```python
# Periodic health check
async def check_circuit_breakers():
    states = CircuitBreakerRegistry.get_all_states()
    
    open_breakers = [
        name for name, state in states.items()
        if state["state"] == "open"
    ]
    
    if open_breakers:
        await send_alert(
            f"Circuit breakers OPEN: {', '.join(open_breakers)}",
            severity="high"
        )
    
    # Check success rates
    low_success = [
        name for name, state in states.items()
        if state["success_rate"] < 95.0 and state["total_requests"] > 100
    ]
    
    if low_success:
        await send_warning(
            f"Low success rates: {', '.join(low_success)}"
        )
```

### 5. Log State Transitions

Circuit breaker automatically logs state transitions:

```
INFO:  CircuitBreaker 'openai': CLOSED (normal operation)
ERROR: CircuitBreaker 'openai': CLOSED → OPEN (threshold reached: 3/3)
INFO:  CircuitBreaker 'openai': OPEN → HALF_OPEN (testing service)
INFO:  CircuitBreaker 'openai': HALF_OPEN → CLOSED (service recovered)
```

## Configuration Examples

### Development
```bash
# Fast recovery for development
CIRCUIT_BREAKER_FAILURE_THRESHOLD=2
CIRCUIT_BREAKER_TIMEOUT=10.0
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=5.0
```

### Production
```bash
# More lenient for production
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60.0
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=30.0
```

### High Availability
```bash
# Very lenient, only for critical issues
CIRCUIT_BREAKER_FAILURE_THRESHOLD=10
CIRCUIT_BREAKER_TIMEOUT=300.0
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=60.0
```

## Metrics to Track

Track these circuit breaker metrics:

- `circuit_breaker_state` (gauge): Current state (0=closed, 1=half_open, 2=open)
- `circuit_breaker_requests_total` (counter): Total requests
- `circuit_breaker_failures_total` (counter): Total failures
- `circuit_breaker_rejections_total` (counter): Requests rejected (circuit open)
- `circuit_breaker_state_transitions_total` (counter): State transitions
- `circuit_breaker_success_rate` (gauge): Success rate percentage

## Troubleshooting

### Problem: Circuit keeps opening
**Solution**: 
- Check if underlying service is actually failing
- Increase failure_threshold
- Investigate root cause of failures

### Problem: Circuit opens too late
**Solution**:
- Decrease failure_threshold
- Reduce timeout value
- Add retry logic before circuit breaker

### Problem: Circuit doesn't close after recovery
**Solution**:
- Check half_open_timeout setting
- Manually reset circuit breaker
- Verify service is actually recovered

### Problem: Too many rejections
**Solution**:
- Circuit is protecting you! Fix the underlying service
- Implement fallback mechanisms
- Queue requests for later processing

## Summary

Circuit breaker provides:
- ✅ **Fail-fast** behavior when services are down
- ✅ **Automatic recovery** detection
- ✅ **Cascading failure prevention**
- ✅ **Resource protection** (don't waste time on failing calls)
- ✅ **Monitoring** via state tracking
- ✅ **Configurable** thresholds and timeouts

Use it everywhere you interact with external services or dependencies that can fail!

