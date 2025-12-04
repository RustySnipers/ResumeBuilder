#!/bin/bash
# ResumeBuilder Management Script
# Manage the deployed application

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check for docker-compose or docker compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Function to display usage
usage() {
    echo -e "${BLUE}ResumeBuilder Management Script${NC}\n"
    echo "Usage: $0 {start|stop|restart|status|logs|backup|clean|shell}"
    echo ""
    echo "Commands:"
    echo "  start      - Start all services"
    echo "  stop       - Stop all services"
    echo "  restart    - Restart all services"
    echo "  status     - Show service status and health"
    echo "  logs       - Show logs (use -f to follow)"
    echo "  backup     - Backup database"
    echo "  clean      - Stop and remove all containers, volumes, and images"
    echo "  shell      - Open shell in API container"
    echo ""
    exit 1
}

# Function to start services
start_services() {
    echo -e "${BLUE}Starting ResumeBuilder services...${NC}\n"
    $DOCKER_COMPOSE up -d
    echo -e "\n${GREEN}✓ Services started${NC}"
    echo "Check status with: $0 status"
}

# Function to stop services
stop_services() {
    echo -e "${BLUE}Stopping ResumeBuilder services...${NC}\n"
    $DOCKER_COMPOSE down
    echo -e "\n${GREEN}✓ Services stopped${NC}"
}

# Function to restart services
restart_services() {
    echo -e "${BLUE}Restarting ResumeBuilder services...${NC}\n"
    $DOCKER_COMPOSE restart
    echo -e "\n${GREEN}✓ Services restarted${NC}"
    echo "Check status with: $0 status"
}

# Function to show status
show_status() {
    echo -e "${BLUE}ResumeBuilder Service Status:${NC}\n"

    # Show container status
    $DOCKER_COMPOSE ps

    echo -e "\n${BLUE}Health Status:${NC}\n"

    # Check health
    ./scripts/health_check.sh
}

# Function to show logs
show_logs() {
    if [ "$2" == "-f" ]; then
        echo -e "${BLUE}Following logs (Ctrl+C to exit)...${NC}\n"
        $DOCKER_COMPOSE logs -f
    else
        echo -e "${BLUE}Recent logs:${NC}\n"
        $DOCKER_COMPOSE logs --tail=100
    fi
}

# Function to backup database
backup_database() {
    echo -e "${BLUE}Backing up PostgreSQL database...${NC}\n"

    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="./backups"
    backup_file="${backup_dir}/resumebuilder_${timestamp}.sql"

    # Create backup directory
    mkdir -p "$backup_dir"

    # Perform backup
    docker exec resumebuilder-db pg_dump -U postgres -d resumebuilder > "$backup_file"

    # Compress backup
    gzip "$backup_file"

    echo -e "${GREEN}✓ Database backup created: ${backup_file}.gz${NC}"

    # Show backup size
    size=$(du -h "${backup_file}.gz" | cut -f1)
    echo "Backup size: $size"

    # Keep only last 7 backups
    echo "Cleaning old backups (keeping last 7)..."
    ls -t "${backup_dir}"/resumebuilder_*.sql.gz | tail -n +8 | xargs -r rm
    echo -e "${GREEN}✓ Old backups cleaned${NC}"
}

# Function to clean everything
clean_all() {
    echo -e "${RED}WARNING: This will remove all containers, volumes, and data!${NC}"
    read -p "Are you sure? (type 'yes' to confirm): " confirm

    if [ "$confirm" == "yes" ]; then
        echo -e "${BLUE}Cleaning ResumeBuilder deployment...${NC}\n"

        # Stop and remove containers
        $DOCKER_COMPOSE down -v

        # Remove images
        echo "Removing Docker images..."
        docker images | grep resumebuilder | awk '{print $3}' | xargs -r docker rmi -f

        echo -e "\n${GREEN}✓ Cleanup completed${NC}"
    else
        echo "Cleanup cancelled"
    fi
}

# Function to open shell
open_shell() {
    echo -e "${BLUE}Opening shell in API container...${NC}\n"
    docker exec -it resumebuilder-api /bin/bash
}

# Main script
if [ $# -lt 1 ]; then
    usage
fi

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    backup)
        backup_database
        ;;
    clean)
        clean_all
        ;;
    shell)
        open_shell
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}\n"
        usage
        ;;
esac
