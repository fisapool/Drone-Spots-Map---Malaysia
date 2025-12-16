#!/bin/bash
# Production deployment script for Ubuntu using Gunicorn + Uvicorn workers
# Recommended for high-traffic production environments

echo "=========================================="
echo "Drone Spots API - Production Deployment"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo ""
elif [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
    echo ""
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
    echo ""
fi

# Check if gunicorn is installed
if ! python -c "import gunicorn" 2>/dev/null; then
    echo "📦 Installing Gunicorn..."
    pip install gunicorn
    echo ""
fi

# Install API dependencies
if [ -f "requirements_api.txt" ]; then
    echo "📦 Installing/updating dependencies..."
    pip install -r requirements_api.txt --upgrade
    echo ""
fi

# Detect CPU cores
CPU_CORES=$(nproc)
RECOMMENDED_WORKERS=$((2 * CPU_CORES + 1))

echo "💻 System Information:"
echo "   CPU Cores: $CPU_CORES"
echo "   Recommended Workers: $RECOMMENDED_WORKERS"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Using default settings."
    echo "   Create .env file to customize configuration."
    echo ""
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Use recommended workers if not set
WORKERS=${WORKERS:-$RECOMMENDED_WORKERS}

# Create logs directory
mkdir -p logs

# Get port from .env or use default
PORT=${PORT:-8001}

echo "🚀 Starting production server with Gunicorn..."
echo "   Workers: $WORKERS"
echo "   Host: 0.0.0.0"
echo "   Port: $PORT"
echo ""
echo "📚 API Documentation: http://localhost:$PORT/docs"
echo "🌐 API Endpoint: http://localhost:$PORT"
echo ""
echo "💡 Tips:"
echo "   - Use a reverse proxy (nginx) in front for SSL/load balancing"
echo "   - Consider using systemd service for auto-start"
echo "   - Monitor logs in ./logs/ directory"
echo ""
echo "=========================================="
echo ""

# Start with Gunicorn + Uvicorn workers (production-grade)
# Use python -m gunicorn to ensure we use the venv's gunicorn
python -m gunicorn drone_spots_api:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info

