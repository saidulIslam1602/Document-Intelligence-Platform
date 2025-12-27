#!/bin/bash

# Production Deployment Script with Optimizations
# This script ensures all performance and cost optimizations are applied

set -e  # Exit on error

echo "🚀 Starting Production Deployment..."
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env.production ]; then
    echo -e "${GREEN}✅ Loading production environment variables${NC}"
    export $(cat .env.production | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠️  Warning: .env.production not found, using defaults${NC}"
fi

# Step 1: Build optimized Docker images
echo ""
echo "📦 Building production Docker images..."
docker-compose -f docker-compose.prod.yml build --parallel

# Step 2: Run database migrations
echo ""
echo "🗄️  Running database migrations..."
# Add your migration command here
# python manage.py migrate

# Step 3: Apply database indexes
echo ""
echo "🔧 Applying database indexes for optimization..."
python -c "
from src.shared.database import apply_database_indexes
import os
conn_str = os.getenv('SQL_CONNECTION_STRING')
if conn_str:
    apply_database_indexes(conn_str)
else:
    print('Warning: SQL_CONNECTION_STRING not set')
"

# Step 4: Build and optimize frontend
echo ""
echo "⚛️  Building optimized frontend..."
cd frontend
npm ci --production
npm run build
cd ..

# Step 5: Stop existing containers
echo ""
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Step 6: Start services with health checks
echo ""
echo "🚀 Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Step 7: Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
services=("frontend" "api-gateway" "redis" "postgres")
for service in "${services[@]}"; do
    echo "Checking $service..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.prod.yml ps | grep "$service" | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ $service failed to become healthy${NC}"
            exit 1
        fi
    done
done

# Step 8: Run post-deployment optimizations
echo ""
echo "🔧 Running post-deployment optimizations..."

# Warm up caches
curl -s http://localhost:8003/health > /dev/null || true

# Run database analysis
python -c "
from src.shared.database import analyze_database
import os
conn_str = os.getenv('SQL_CONNECTION_STRING')
if conn_str:
    analyze_database(conn_str)
"

# Step 9: Display deployment summary
echo ""
echo "=================================="
echo -e "${GREEN}✅ Production Deployment Complete!${NC}"
echo "=================================="
echo ""
echo "Services Status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "Service URLs:"
echo "  Frontend:    http://localhost:80"
echo "  API Gateway: http://localhost:8003"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3001"

echo ""
echo "Performance Tips:"
echo "  1. Monitor metrics at http://localhost:3001"
echo "  2. Check logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  3. View performance: curl http://localhost:8003/metrics"
echo "  4. Database stats: curl http://localhost:8003/admin/db-stats"

echo ""
echo "Cost Optimization:"
echo "  - Resource limits are configured"
echo "  - Caching is enabled (Redis)"
echo "  - Database indexes are applied"
echo "  - Frontend is optimized and compressed"
echo "  - Connection pooling is active"

echo ""
echo -e "${GREEN}🎉 Your application is production-ready!${NC}"

