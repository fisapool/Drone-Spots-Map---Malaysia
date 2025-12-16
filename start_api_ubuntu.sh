#!/bin/bash
# Production-ready start script for Drone Spots API on Ubuntu/Linux
# Optimized for multi-worker deployment

echo "=========================================="
echo "Malaysia Drone Spots API - Ubuntu Setup"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if running as root (not recommended for production)
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Warning: Running as root. Consider using a non-root user."
fi

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

# Install dependencies if requirements file exists
if [ -f "requirements_api.txt" ]; then
    echo "📦 Installing/updating dependencies..."
    pip install -r requirements_api.txt --upgrade
    echo ""
fi

# Detect CPU cores for optimal worker count
CPU_CORES=$(nproc)
RECOMMENDED_WORKERS=$((2 * CPU_CORES + 1))

echo "💻 System Information:"
echo "   CPU Cores: $CPU_CORES"
echo "   Recommended Workers: $RECOMMENDED_WORKERS"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from defaults..."
    cat > .env << EOF
# OpenWeatherMap API Key (optional - required for weather data)
OPENWEATHER_API_KEY=

# Performance Settings
# Optimal worker count: (2 * CPU cores) + 1 = $RECOMMENDED_WORKERS
WORKERS=$RECOMMENDED_WORKERS
MAX_CONNECTIONS=200
MAX_KEEPALIVE_CONNECTIONS=100
TIMEOUT=30.0

# Log path (optional)
LOG_PATH=./logs/api.log
EOF
    echo "   Created .env file. Please edit it to add your OPENWEATHER_API_KEY if needed."
    echo ""
fi

# Load environment variables
if [ -f ".env" ]; then
    echo "🔧 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
    echo ""
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Get port from .env or use default
PORT=${PORT:-8001}

echo "🚀 Starting API server..."
echo "   Workers: ${WORKERS:-$RECOMMENDED_WORKERS}"
echo "   Host: 0.0.0.0"
echo "   Port: $PORT"
echo ""
echo "📚 API Documentation: http://localhost:$PORT/docs"
echo "🌐 API Endpoint: http://localhost:$PORT"
echo ""
echo "=========================================="
echo ""

# Start with uvicorn (supports multiple workers on Linux)
# Use uvicorn directly to have control over port and workers
uvicorn drone_spots_api:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers ${WORKERS:-$RECOMMENDED_WORKERS} \
    --log-level info

