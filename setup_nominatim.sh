#!/bin/bash
set -e

echo "=========================================="
echo "  Self-Hosted Nominatim Setup for Malaysia"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    echo "Please install Docker Compose first."
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from defaults...${NC}"
    cat > .env << 'EOF'
# Nominatim Configuration
NOMINATIM_PASSWORD=changeme123
NOMINATIM_PORT=8080
POSTGRES_PORT=5433
NOMINATIM_THREADS=4

# Drone Spots API Configuration
NOMINATIM_URL=localhost:8080
NOMINATIM_SCHEME=http
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Ask for password if using default
if [ "$NOMINATIM_PASSWORD" = "changeme123" ]; then
    echo -e "${YELLOW}Using default password. For production, change NOMINATIM_PASSWORD in .env${NC}"
    read -p "Press Enter to continue or Ctrl+C to cancel..."
fi

echo ""
echo "Configuration:"
echo "  - Nominatim Port: ${NOMINATIM_PORT:-8080}"
echo "  - PostgreSQL Port: ${POSTGRES_PORT:-5433}"
echo "  - Import Threads: ${NOMINATIM_THREADS:-4}"
echo "  - Data Source: Malaysia, Singapore, and Brunei (malaysia-singapore-brunei-latest.osm.pbf)"
echo ""

# Check if container already exists (both via docker and docker-compose)
# Use grep -q and check exit code to avoid parsing issues
CONTAINER_EXISTS=0
if docker ps -a --format '{{.Names}}' | grep -q "^nominatim$"; then
    CONTAINER_EXISTS=1
fi

if [ "$CONTAINER_EXISTS" = "1" ]; then
    echo -e "${YELLOW}Nominatim container already exists.${NC}"
    
    read -p "Do you want to remove it and start fresh? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping and removing existing container..."
        
        # Try docker-compose down first (for containers created via docker-compose)
        docker-compose -f docker-compose.nominatim.yml down -v 2>&1 || true
        
        # Force remove container directly (handles containers created manually)
        if docker ps -a --format '{{.Names}}' | grep -q "^nominatim$"; then
            echo "Force removing container directly..."
            docker rm -f nominatim 2>&1 || true
        fi
        
        # Wait for Docker to fully process the removal (prevents race condition)
        echo "Waiting for Docker to complete container removal..."
        sleep 2
        
        # Verify container is removed with retries
        MAX_RETRIES=5
        RETRY_COUNT=0
        FINAL_CHECK=1
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if docker ps -a --format '{{.Names}}' | grep -q "^nominatim$"; then
                FINAL_CHECK=1
                RETRY_COUNT=$((RETRY_COUNT + 1))
                sleep 1
            else
                FINAL_CHECK=0
                break
            fi
        done
        
        if [ "$FINAL_CHECK" = "1" ]; then
            echo -e "${RED}Warning: Container still exists after removal attempt.${NC}"
            echo "Please manually remove it with: docker rm -f nominatim"
            exit 1
        fi
        
        echo -e "${GREEN}✓ Removed existing container${NC}"
    else
        echo "Starting existing container..."
        docker-compose -f docker-compose.nominatim.yml up -d
        echo -e "${GREEN}✓ Started existing container${NC}"
        echo ""
        echo "To view logs: docker-compose -f docker-compose.nominatim.yml logs -f"
        exit 0
    fi
fi

echo ""
echo "Starting Nominatim container..."
echo -e "${YELLOW}This will download the Malaysia OSM data and import it.${NC}"
echo -e "${YELLOW}This process can take 2-6 hours depending on your system.${NC}"
echo ""

# Check if port is available
NOMINATIM_PORT=${NOMINATIM_PORT:-8080}
PORT_IN_USE=0

# Check if port is in use by another container
PORT_CONTAINER=$(docker ps --format "{{.Names}}" --filter "publish=$NOMINATIM_PORT" | head -1)
if [ -n "$PORT_CONTAINER" ]; then
    PORT_IN_USE=1
    echo -e "${YELLOW}Warning: Port $NOMINATIM_PORT is already in use by container: $PORT_CONTAINER${NC}"
    echo "Options:"
    echo "  1. Stop the conflicting container: docker stop $PORT_CONTAINER"
    echo "  2. Use a different port by setting NOMINATIM_PORT in .env"
    read -p "Do you want to stop $PORT_CONTAINER? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping $PORT_CONTAINER..."
        docker stop "$PORT_CONTAINER" 2>&1
        sleep 2
    else
        echo -e "${RED}Cannot proceed: Port $NOMINATIM_PORT is in use.${NC}"
        echo "Please stop the conflicting container or change NOMINATIM_PORT in .env"
        exit 1
    fi
fi

# Also check using netstat/ss (for non-Docker processes)
if command -v ss &> /dev/null; then
    if ss -tuln | grep -q ":$NOMINATIM_PORT "; then
        PORT_PROCESS=$(ss -tulnp | grep ":$NOMINATIM_PORT " | head -1)
        if [ -n "$PORT_PROCESS" ] && [ -z "$PORT_CONTAINER" ]; then
            PORT_IN_USE=1
            echo -e "${RED}Error: Port $NOMINATIM_PORT is in use by a non-Docker process.${NC}"
            echo "Please free the port or change NOMINATIM_PORT in .env"
            exit 1
        fi
    fi
fi

# Start the container
docker-compose -f docker-compose.nominatim.yml up -d

echo ""
echo -e "${GREEN}✓ Nominatim container started${NC}"
echo ""

# Wait a moment for container to initialize
sleep 5

# Check container status
if docker ps --format '{{.Names}}' | grep -q "^nominatim$"; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container failed to start. Check logs:${NC}"
    echo "  docker-compose -f docker-compose.nominatim.yml logs"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Monitor import progress:"
echo "   ${GREEN}docker-compose -f docker-compose.nominatim.yml logs -f${NC}"
echo ""
echo "2. Check status (once import is complete):"
echo "   ${GREEN}curl http://localhost:${NOMINATIM_PORT:-8080}/status${NC}"
echo ""
echo "3. Test geocoding:"
echo "   ${GREEN}curl \"http://localhost:${NOMINATIM_PORT:-8080}/search?q=Kuala+Lumpur&format=json\"${NC}"
echo ""
echo "4. Test reverse geocoding:"
echo "   ${GREEN}curl \"http://localhost:${NOMINATIM_PORT:-8080}/reverse?lat=3.1390&lon=101.6869&format=json\"${NC}"
echo ""
echo "5. Stop the service:"
echo "   ${GREEN}docker-compose -f docker-compose.nominatim.yml stop${NC}"
echo ""
echo "6. Start the service:"
echo "   ${GREEN}docker-compose -f docker-compose.nominatim.yml start${NC}"
echo ""
echo "7. View logs:"
echo "   ${GREEN}docker-compose -f docker-compose.nominatim.yml logs -f${NC}"
echo ""
echo -e "${YELLOW}Note: The import process will take several hours.${NC}"
echo -e "${YELLOW}You can continue using the public Nominatim until this is ready.${NC}"
echo ""

