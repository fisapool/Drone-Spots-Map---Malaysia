#!/bin/bash
# Setup systemd service for Drone Spots API
# This makes the API run automatically on boot and restart on failure

echo "=========================================="
echo "Setting up Drone Spots API as Systemd Service"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if running as root (needed for systemd)
if [ "$EUID" -ne 0 ]; then 
   echo "⚠️  This script needs to be run with sudo for systemd setup"
   echo "   Run: sudo ./setup_api_service.sh"
   exit 1
fi

# Detect CPU cores for optimal worker count
CPU_CORES=$(nproc)
RECOMMENDED_WORKERS=$((2 * CPU_CORES + 1))

echo "💻 System Information:"
echo "   CPU Cores: $CPU_CORES"
echo "   Recommended Workers: $RECOMMENDED_WORKERS"
echo "   Working Directory: $SCRIPT_DIR"
echo ""

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
if [ "$ACTUAL_USER" = "root" ]; then
    echo "⚠️  Error: Cannot determine actual user. Please run as: sudo -u <your-user> ./setup_api_service.sh"
    exit 1
fi

echo "👤 Service will run as user: $ACTUAL_USER"
echo ""

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"
chown $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/logs"

# Update service file with correct paths and worker count
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|User=.*|User=$ACTUAL_USER|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|Group=.*|Group=$ACTUAL_USER|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|ExecStart=.*|ExecStart=$SCRIPT_DIR/venv/bin/uvicorn drone_spots_api:app --host 0.0.0.0 --port 8001 --workers $RECOMMENDED_WORKERS --log-level info|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|StandardOutput=.*|StandardOutput=append:$SCRIPT_DIR/logs/api-service.log|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|StandardError=.*|StandardError=append:$SCRIPT_DIR/logs/api-service-error.log|g" "$SCRIPT_DIR/drone-spots-api.service"

# Copy service file to systemd
echo "📋 Installing systemd service..."
cp "$SCRIPT_DIR/drone-spots-api.service" /etc/systemd/system/
chmod 644 /etc/systemd/system/drone-spots-api.service

# Reload systemd
systemctl daemon-reload

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "📝 Available commands:"
echo "   sudo systemctl start drone-spots-api    # Start the service"
echo "   sudo systemctl stop drone-spots-api     # Stop the service"
echo "   sudo systemctl restart drone-spots-api  # Restart the service"
echo "   sudo systemctl status drone-spots-api   # Check service status"
echo "   sudo systemctl enable drone-spots-api   # Enable auto-start on boot"
echo "   sudo systemctl disable drone-spots-api  # Disable auto-start"
echo ""
echo "📊 View logs:"
echo "   tail -f $SCRIPT_DIR/logs/api-service.log"
echo "   tail -f $SCRIPT_DIR/logs/api-service-error.log"
echo ""
echo "🚀 To start the service now and enable auto-start:"
echo "   sudo systemctl enable --now drone-spots-api"
echo ""
echo "=========================================="

