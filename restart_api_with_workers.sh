#!/bin/bash
# Restart API with multiple workers support

echo "=========================================="
echo "Restarting API with Multiple Workers"
echo "=========================================="
echo ""

# Load environment variables
if [ -f ".env" ]; then
    source .env
    export $(cat .env | grep -v '^#' | xargs)
fi

# Get worker count from .env or calculate
CPU_CORES=$(nproc)
RECOMMENDED_WORKERS=$((2 * CPU_CORES + 1))
WORKERS=${WORKERS:-$RECOMMENDED_WORKERS}

echo "💻 System Information:"
echo "   CPU Cores: $CPU_CORES"
echo "   Workers: $WORKERS"
echo ""

# Find and stop existing API process on port 8001
echo "🛑 Stopping existing API on port 8001..."
PIDS=$(ps aux | grep "uvicorn.*8001" | grep -v grep | awk '{print $2}')
if [ ! -z "$PIDS" ]; then
    echo "   Found processes: $PIDS"
    kill $PIDS 2>/dev/null
    sleep 2
    # Force kill if still running
    PIDS=$(ps aux | grep "uvicorn.*8001" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PIDS" ]; then
        kill -9 $PIDS 2>/dev/null
    fi
    echo "   ✅ Stopped"
else
    echo "   ℹ️  No existing process found"
fi

echo ""

# Activate virtual environment and start with workers
echo "🚀 Starting API with $WORKERS workers on port 8001..."
echo ""

cd /home/arif/drones
source venv/bin/activate

# Start with uvicorn using workers flag
uvicorn drone_spots_api:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers $WORKERS \
    --log-level info &

sleep 3

# Verify it's running
if ps aux | grep -q "uvicorn.*8001.*workers"; then
    echo ""
    echo "✅ API started successfully!"
    echo "   Workers: $WORKERS"
    echo "   Port: 8001"
    echo "   URL: http://192.168.0.145:8001"
    echo "   Docs: http://192.168.0.145:8001/docs"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "⚠️  API may not have started. Check logs above."
    echo "=========================================="
fi

