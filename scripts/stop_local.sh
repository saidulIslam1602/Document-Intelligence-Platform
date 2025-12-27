#!/bin/bash

# Stop all local services

echo "Stopping all local services..."

# Stop Python services
for service in api-gateway document-ingestion ai-processing analytics ai-chat mcp-server; do
    if [ -f "/tmp/di-$service.pid" ]; then
        pid=$(cat "/tmp/di-$service.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping $service (PID: $pid)..."
            kill $pid
            rm "/tmp/di-$service.pid"
        fi
    fi
done

# Stop frontend
if [ -f "/tmp/di-frontend.pid" ]; then
    pid=$(cat "/tmp/di-frontend.pid")
    if ps -p $pid > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $pid)..."
        kill $pid
        rm "/tmp/di-frontend.pid"
    fi
fi

# Stop Docker services
echo "Stopping Docker services..."
docker-compose -f docker-compose.local.yml down

echo ""
echo "All services stopped"

