#!/bin/bash

# Run all services locally for demonstration

set -e

echo "Starting Document Intelligence Platform locally..."
echo "=================================================="

# Load local environment
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
    echo "Loaded .env.local configuration"
else
    echo "Error: .env.local not found. Run ./scripts/local_setup.sh first"
    exit 1
fi

# Check if Docker services are running
echo ""
echo "Checking Docker services..."
if ! docker ps | grep -q "di-postgres-local"; then
    echo "Starting Docker services (Postgres, Redis)..."
    docker-compose -f docker-compose.local.yml up -d
    echo "Waiting for services to be ready..."
    sleep 5
else
    echo "Docker services already running"
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
pip3 list | grep -q fastapi || echo "Warning: Some dependencies may be missing. Run: pip3 install -r requirements.txt"

# Function to start a service in background
start_service() {
    local service_name=$1
    local service_port=$2
    local service_path=$3
    
    echo "Starting $service_name on port $service_port..."
    cd "$service_path"
    PYTHONPATH=/home/saidul/Desktop/compello\ As/Document-Intelligence-Platform \
    python3 main.py > "/tmp/di-$service_name.log" 2>&1 &
    echo $! > "/tmp/di-$service_name.pid"
    cd - > /dev/null
}

# Start API Gateway
start_service "api-gateway" 8003 "src/microservices/api-gateway"
sleep 2

# Start Document Ingestion
start_service "document-ingestion" 8000 "src/microservices/document-ingestion"
sleep 1

# Start AI Processing
start_service "ai-processing" 8001 "src/microservices/ai-processing"
sleep 1

# Start Analytics
start_service "analytics" 8002 "src/microservices/analytics"
sleep 1

# Start AI Chat
start_service "ai-chat" 8004 "src/microservices/ai-chat"
sleep 1

# Start MCP Server
start_service "mcp-server" 8012 "src/microservices/mcp-server"
sleep 2

# Start Frontend
echo "Starting Frontend on port 3000..."
cd frontend
npm run dev > /tmp/di-frontend.log 2>&1 &
echo $! > /tmp/di-frontend.pid
cd - > /dev/null

echo ""
echo "=================================================="
echo "All services started successfully!"
echo "=================================================="
echo ""
echo "Service URLs:"
echo "  Frontend:              http://localhost:3000"
echo "  API Gateway:           http://localhost:8003"
echo "  Document Ingestion:    http://localhost:8000"
echo "  AI Processing:         http://localhost:8001"
echo "  Analytics:             http://localhost:8002"
echo "  AI Chat:               http://localhost:8004"
echo "  MCP Server:            http://localhost:8012"
echo ""
echo "Database & Cache:"
echo "  PostgreSQL:            localhost:5432"
echo "  Redis:                 localhost:6379"
echo ""
echo "Demo Credentials:"
echo "  Email:     demo@example.com"
echo "  Password:  demo123"
echo ""
echo "Logs available at:"
echo "  /tmp/di-*.log"
echo ""
echo "To stop all services:"
echo "  ./scripts/stop_local.sh"
echo ""
echo "Checking service health..."
sleep 5

# Health checks
for port in 8003 8000 8001 8002 8004 8012; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "  Port $port: OK"
    else
        echo "  Port $port: Not ready yet (may need more time)"
    fi
done

echo ""
echo "Open http://localhost:3000 in your browser to start!"

