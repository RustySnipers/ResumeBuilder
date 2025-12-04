#!/bin/bash
# ResumeBuilder Health Check Script
# Checks the health of all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  ResumeBuilder Health Check${NC}"
echo -e "${BLUE}=================================================${NC}\n"

# Function to check service
check_service() {
    local service_name=$1
    local url=$2

    echo -n "Checking $service_name... "

    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}✗ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check detailed health
check_detailed_health() {
    local url=$1

    echo -e "\nDetailed Health Status:"

    response=$(curl -s "$url" 2>/dev/null || echo '{"error": "Failed to connect"}')

    if command -v jq &> /dev/null; then
        echo "$response" | jq '.'
    else
        echo "$response"
    fi
}

# Check Docker containers
echo -e "${YELLOW}Docker Container Status:${NC}"

if command -v docker &> /dev/null; then
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep resumebuilder; then
        echo ""
    else
        echo -e "${RED}No ResumeBuilder containers running${NC}"
        echo "Start with: docker-compose up -d"
        exit 1
    fi
else
    echo -e "${RED}Docker not installed${NC}"
    exit 1
fi

echo ""

# Check basic connectivity
check_service "API Root" "http://localhost:8000/"
check_service "Health Endpoint" "http://localhost:8000/health"
check_service "Readiness Probe" "http://localhost:8000/health/ready"
check_service "Liveness Probe" "http://localhost:8000/health/live"

# Show detailed health information
check_detailed_health "http://localhost:8000/health"

# Check individual service health
echo -e "\n${YELLOW}Docker Service Health:${NC}"

services=("resumebuilder-api" "resumebuilder-db" "resumebuilder-redis" "resumebuilder-webhook-worker")

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
        health=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "no healthcheck")
        status=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null || echo "unknown")

        if [ "$health" == "healthy" ] || ([ "$health" == "no healthcheck" ] && [ "$status" == "running" ]); then
            echo -e "$service: ${GREEN}✓ $health ($status)${NC}"
        else
            echo -e "$service: ${RED}✗ $health ($status)${NC}"
        fi
    else
        echo -e "$service: ${RED}✗ NOT RUNNING${NC}"
    fi
done

echo -e "\n${BLUE}=================================================${NC}"

# Exit with appropriate code
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    exit 0
else
    echo -e "${RED}✗ System unhealthy${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi
