#!/bin/bash
################################################################################
# Document Intelligence Platform - Universal Startup Script
# Handles all modes: Azure OpenAI | Standard OpenAI | Mock Mode
# Auto-detects configuration and starts services accordingly
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║     Document Intelligence Platform - Universal Launcher           ║"
echo "║     Microservices | AI Processing | Analytics | Monitoring        ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

################################################################################
# STEP 1: Environment Detection
################################################################################

echo -e "${BLUE}[1/6] Detecting Environment Configuration...${NC}"

# Check for environment file
ENV_FILE=".env"
if [ -f ".env.local" ]; then
    ENV_FILE=".env.local"
elif [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo -e "${YELLOW}Creating .env from template...${NC}"
        cp env.example .env
    else
        echo -e "${RED}Error: No environment file found${NC}"
        exit 1
    fi
fi

# Load environment
set -a
source "$ENV_FILE" 2>/dev/null || true
set +a

# Detect operational mode
MODE="MOCK"
if [ ! -z "$OPENAI_ENDPOINT" ] && [[ "$OPENAI_ENDPOINT" == *"azure"* ]]; then
    MODE="AZURE"
    echo -e "${GREEN}✓ Mode: Azure OpenAI (Production)${NC}"
elif [ ! -z "$OPENAI_API_KEY" ] && [[ "$OPENAI_API_KEY" == sk-* ]]; then
    MODE="OPENAI"
    echo -e "${GREEN}✓ Mode: Standard OpenAI${NC}"
else
    MODE="MOCK"
    echo -e "${YELLOW}✓ Mode: Mock Services (Free Demo)${NC}"
fi

# Set USE_MOCK_SERVICES based on mode
if [ "$MODE" == "MOCK" ]; then
    export USE_MOCK_SERVICES="true"
else
    export USE_MOCK_SERVICES="${USE_MOCK_SERVICES:-false}"
fi

echo "  Environment: ${ENVIRONMENT:-development}"
echo "  Mock Services: $USE_MOCK_SERVICES"

################################################################################
# STEP 2: Prerequisites Check
################################################################################

echo -e "\n${BLUE}[2/6] Checking Prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker Desktop${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker Compose
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✓ Docker Compose v2 installed${NC}"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✓ Docker Compose v1 installed${NC}"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker ps &> /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Docker daemon not running. Please start Docker and try again${NC}"
    exit 1
fi

################################################################################
# STEP 3: Clean Up
################################################################################

echo -e "\n${BLUE}[3/6] Stopping Existing Services...${NC}"

# Stop services gracefully
$DOCKER_COMPOSE down --remove-orphans 2>/dev/null || true
$DOCKER_COMPOSE -f docker-compose.local.yml down 2>/dev/null || true

echo -e "${GREEN}✓ Previous services stopped${NC}"

################################################################################
# STEP 4: Start Services
################################################################################

echo -e "\n${BLUE}[4/6] Starting Application Services...${NC}"

# Export environment for docker compose
export MODE
export USE_MOCK_SERVICES

# Start all services (they include their own infrastructure)
echo "Building and starting microservices..."
$DOCKER_COMPOSE up -d --build

echo -e "${GREEN}✓ Services starting...${NC}"

# Wait for services to initialize
echo "Waiting for services to initialize (20 seconds)..."
for i in {1..20}; do
    echo -n "."
    sleep 1
done
echo ""

################################################################################
# STEP 5: Health Check
################################################################################

echo -e "\n${BLUE}[5/6] Checking Service Health...${NC}"

# Define services to check
declare -a SERVICES=(
    "8003:API Gateway"
    "8000:Document Ingestion"
    "8001:AI Processing"
    "8002:Analytics"
    "8004:AI Chat"
    "8006:Data Quality"
    "8007:Batch Processor"
    "8008:Data Catalog"
    "8012:MCP Server"
)

HEALTHY=0
TOTAL=0

for service in "${SERVICES[@]}"; do
    IFS=: read -r port name <<< "$service"
    TOTAL=$((TOTAL + 1))
    
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name (port $port)"
        HEALTHY=$((HEALTHY + 1))
    else
        echo -e "${YELLOW}⚠${NC} $name (port $port) - may need more time"
    fi
done

################################################################################
# STEP 6: Display Summary
################################################################################

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    STARTUP COMPLETE                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✓ Services Started:${NC} $HEALTHY/$TOTAL responding"
echo -e "${GREEN}✓ Operational Mode:${NC} $MODE"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📱 SERVICE ENDPOINTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  🌐 API Gateway:           http://localhost:8003"
echo "  📚 API Documentation:     http://localhost:8003/docs"
echo "  📄 Document Ingestion:    http://localhost:8000"
echo "  🤖 AI Processing:         http://localhost:8001"
echo "  📊 Analytics:             http://localhost:8002"
echo "  💬 AI Chat:               http://localhost:8004"
echo "  🔧 MCP Server:            http://localhost:8012"
echo ""
echo "  📈 Prometheus:            http://localhost:9090"
echo "  📊 Grafana:               http://localhost:3000"
echo "  🔍 Jaeger Tracing:        http://localhost:16686"
echo ""
echo -e "${YELLOW}  💻 Frontend (manual start):${NC}"
echo "     cd frontend && npm run dev"
echo "     → Will run on http://localhost:5173"
echo ""

if [ "$MODE" == "MOCK" ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}💡 MOCK MODE ACTIVE${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  ✓ Free demo mode - no API costs"
    echo "  ✓ Simulated AI responses"
    echo "  ✓ Full functionality for demonstrations"
    echo ""
    echo "  To use real AI:"
    echo "    1. Add OpenAI API key to $ENV_FILE"
    echo "    2. Set: USE_MOCK_SERVICES=false"
    echo "    3. Restart: ./start.sh"
    echo ""
elif [ "$MODE" == "OPENAI" ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 REAL AI ACTIVE - Standard OpenAI${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  ✓ Real AI intelligence enabled"
    echo "  ✓ Using OpenAI API"
    echo "  ✓ All features operational"
    echo ""
elif [ "$MODE" == "AZURE" ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}☁️  PRODUCTION MODE - Azure OpenAI${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  ✓ Azure OpenAI enabled"
    echo "  ✓ Enterprise-grade AI"
    echo "  ✓ Full Azure integration"
    echo ""
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🎯 QUICK ACTIONS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  View logs:           docker compose logs -f"
echo "  Check status:        docker compose ps"
echo "  Stop services:       ./stop.sh"
echo "  Restart service:     docker compose restart <service-name>"
echo ""
echo "  Start frontend:      cd frontend && npm install && npm run dev"
echo "                       (opens at http://localhost:5173)"
echo "  Run tests:           ./scripts/run_tests.sh"
echo "  View health:         curl http://localhost:8003/health"
echo ""

if [ $HEALTHY -lt $((TOTAL - 2)) ]; then
    echo -e "${YELLOW}⚠ Some services are still starting. Wait 30 seconds and check:${NC}"
    echo "     docker compose ps"
    echo "     docker compose logs <service-name>"
    echo ""
fi

echo -e "${GREEN}✅ Platform is ready! Open http://localhost:8003/docs to get started${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0
