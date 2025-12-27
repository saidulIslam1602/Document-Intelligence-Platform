#!/bin/bash
################################################################################
# Document Intelligence Platform - Universal Stop Script
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║     Document Intelligence Platform - Shutdown                     ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect docker compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Docker Compose not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Stopping all services...${NC}"

# Stop main services
if [ -f "docker-compose.yml" ]; then
    $DOCKER_COMPOSE -f docker-compose.yml down
fi

# Stop local infrastructure
if [ -f "docker-compose.local.yml" ]; then
    $DOCKER_COMPOSE -f docker-compose.local.yml down
fi

# Stop production services if running
if [ -f "docker-compose.prod.yml" ]; then
    $DOCKER_COMPOSE -f docker-compose.prod.yml down 2>/dev/null || true
fi

# Kill any remaining Python processes
echo -e "${YELLOW}Cleaning up background processes...${NC}"
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "python.*run.py" 2>/dev/null || true

# Clean up PID files
rm -f /tmp/di-*.pid 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
echo ""
echo "To start again: ./start.sh"
echo ""

