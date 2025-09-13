#!/bin/bash

echo "🚀 Starting Document Intelligence Platform"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Start all services
echo "📦 Starting all microservices..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
python3 test_platform_optimized.py

echo ""
echo "🎉 Platform is ready!"
echo "📊 Performance Dashboard: http://localhost:8004"
echo "📄 Document Ingestion: http://localhost:8000"
echo "🤖 AI Processing: http://localhost:8001"
echo "📈 Analytics: http://localhost:8002"
echo "💬 AI Chat: http://localhost:8003"
echo ""
echo "🛑 To stop: docker-compose down"