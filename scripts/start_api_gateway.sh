#!/bin/bash
# Start API Gateway with correct environment configuration

cd "$(dirname "$0")/.."

# Load environment from .env.local if it exists
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
    echo "✓ Environment variables loaded from .env.local"
fi

# Verify OpenAI API key is set
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OpenAI API Key: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
    echo "✓ Using GPT-4 Turbo for enterprise-grade AI capabilities"
else
    echo "⚠️ Warning: OPENAI_API_KEY not set - AI chat will use fallback"
fi

# Ensure Redis configuration for local development
export REDIS_HOST=${REDIS_HOST:-localhost}
export REDIS_PORT=${REDIS_PORT:-6382}

echo "Starting API Gateway..."
echo "- Redis: $REDIS_HOST:$REDIS_PORT"
echo "- AI Model: GPT-4 Turbo (gpt-4-turbo-preview)"

# Kill any existing API Gateway process
pkill -f "uvicorn.*api-gateway" 2>/dev/null || true
sleep 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Start API Gateway
python3 -m uvicorn src.microservices.api-gateway.main:app \
    --host 0.0.0.0 \
    --port 8003 \
    --reload \
    > logs/api-gateway.log 2>&1 &

PID=$!
echo "API Gateway started (PID: $PID)"
echo "Logs: logs/api-gateway.log"

# Wait a moment and check if it's running
sleep 2
if ps -p $PID > /dev/null; then
    echo "✓ API Gateway is running on http://localhost:8003"
    echo "✓ Health check: http://localhost:8003/health"
else
    echo "✗ API Gateway failed to start. Check logs/api-gateway.log"
    exit 1
fi

