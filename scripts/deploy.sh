#!/bin/bash
# ResumeBuilder Production Deployment Script
# This script deploys the ResumeBuilder application using Docker Compose

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  ResumeBuilder Production Deployment${NC}"
echo -e "${BLUE}  Version: 1.7.0-phase7${NC}"
echo -e "${BLUE}=================================================${NC}\n"

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7]${NC} Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if using docker-compose or docker compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}\n"

# Step 2: Check environment file
echo -e "${YELLOW}[2/7]${NC} Checking environment configuration..."

cd "$PROJECT_ROOT"

if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from template..."

    if [ -f .env.docker ]; then
        cp .env.docker .env
        echo -e "${GREEN}✓ Created .env from .env.docker template${NC}"
        echo -e "${YELLOW}⚠ IMPORTANT: Edit .env and set the following:${NC}"
        echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
        echo "  - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
        echo "  - ANTHROPIC_API_KEY (from console.anthropic.com)"
        echo ""
        read -p "Press Enter to continue after updating .env, or Ctrl+C to exit..."
    else
        echo -e "${RED}Error: .env.docker template not found${NC}"
        exit 1
    fi
fi

# Verify critical environment variables
if ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo -e "${RED}Warning: ANTHROPIC_API_KEY not configured in .env${NC}"
fi

echo -e "${GREEN}✓ Environment configuration checked${NC}\n"

# Step 3: Build Docker images
echo -e "${YELLOW}[3/7]${NC} Building Docker images..."

$DOCKER_COMPOSE build --no-cache

echo -e "${GREEN}✓ Docker images built successfully${NC}\n"

# Step 4: Start services
echo -e "${YELLOW}[4/7]${NC} Starting services..."

$DOCKER_COMPOSE up -d

echo -e "${GREEN}✓ Services started${NC}\n"

# Step 5: Wait for services to be healthy
echo -e "${YELLOW}[5/7]${NC} Waiting for services to be healthy..."

MAX_WAIT=120  # 2 minutes
WAIT_TIME=0
INTERVAL=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if $DOCKER_COMPOSE ps | grep -q "unhealthy"; then
        echo -e "${YELLOW}⏳ Services starting... (${WAIT_TIME}s/${MAX_WAIT}s)${NC}"
        sleep $INTERVAL
        WAIT_TIME=$((WAIT_TIME + INTERVAL))
    else
        ALL_HEALTHY=true

        # Check if database is healthy
        if ! docker inspect resumebuilder-db --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            ALL_HEALTHY=false
        fi

        # Check if Redis is healthy
        if ! docker inspect resumebuilder-redis --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            ALL_HEALTHY=false
        fi

        # Check if API is healthy
        if ! docker inspect resumebuilder-api --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            ALL_HEALTHY=false
        fi

        if $ALL_HEALTHY; then
            echo -e "${GREEN}✓ All services are healthy${NC}\n"
            break
        else
            echo -e "${YELLOW}⏳ Services starting... (${WAIT_TIME}s/${MAX_WAIT}s)${NC}"
            sleep $INTERVAL
            WAIT_TIME=$((WAIT_TIME + INTERVAL))
        fi
    fi
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}Warning: Services may not be fully healthy after ${MAX_WAIT}s${NC}"
    echo "Check service status with: $DOCKER_COMPOSE ps"
    echo "Check logs with: $DOCKER_COMPOSE logs"
fi

# Step 6: Run database migrations
echo -e "${YELLOW}[6/7]${NC} Running database migrations..."

$DOCKER_COMPOSE exec -T api alembic upgrade head

echo -e "${GREEN}✓ Database migrations completed${NC}\n"

# Step 7: Verify deployment
echo -e "${YELLOW}[7/7]${NC} Verifying deployment..."

# Check API health endpoint
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API health check passed${NC}"
else
    echo -e "${RED}⚠ API health check failed${NC}"
    echo "Check logs with: $DOCKER_COMPOSE logs api"
fi

# Display service status
echo -e "\n${BLUE}=================================================${NC}"
echo -e "${BLUE}  Deployment Summary${NC}"
echo -e "${BLUE}=================================================${NC}\n"

echo "Service Status:"
$DOCKER_COMPOSE ps

echo -e "\n${GREEN}✓ Deployment completed successfully!${NC}\n"

echo "Access the application:"
echo "  - API: http://localhost:8000"
echo "  - Health Check: http://localhost:8000/health"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - OpenAPI Spec: http://localhost:8000/openapi.json"

echo -e "\nUseful commands:"
echo "  - View logs: $DOCKER_COMPOSE logs -f"
echo "  - View API logs: $DOCKER_COMPOSE logs -f api"
echo "  - View webhook worker logs: $DOCKER_COMPOSE logs -f webhook-worker"
echo "  - Stop services: $DOCKER_COMPOSE down"
echo "  - Restart services: $DOCKER_COMPOSE restart"
echo "  - Check health: ./scripts/health_check.sh"

echo -e "\n${YELLOW}⚠ Next Steps:${NC}"
echo "  1. Test the API health endpoint: curl http://localhost:8000/health"
echo "  2. Register a user: curl -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{...}'"
echo "  3. Review logs for any warnings or errors"
echo "  4. Set up monitoring and alerting"
echo "  5. Configure backups for database and Redis"

echo -e "\n${BLUE}=================================================${NC}\n"
