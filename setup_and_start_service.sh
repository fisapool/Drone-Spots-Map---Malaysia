#!/bin/bash
# Quick setup and start script for Drone Spots API systemd service
# This will install the service, enable auto-start on boot, and start it now

echo "=========================================="
echo "Setting up Drone Spots API Service"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

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
    echo "⚠️  Error: Cannot determine actual user. Please run as: sudo -u <your-user> ./setup_and_start_service.sh"
    exit 1
fi

echo "👤 Service will run as user: $ACTUAL_USER"
echo ""

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"
chown $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/logs" 2>/dev/null || true

# Update service file with correct paths and worker count
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|User=.*|User=$ACTUAL_USER|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|Group=.*|Group=$ACTUAL_USER|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|ExecStart=.*|ExecStart=$SCRIPT_DIR/venv/bin/uvicorn drone_spots_api:app --host 0.0.0.0 --port 8001 --workers $RECOMMENDED_WORKERS --log-level info|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|StandardOutput=.*|StandardOutput=append:$SCRIPT_DIR/logs/api-service.log|g" "$SCRIPT_DIR/drone-spots-api.service"
sed -i "s|StandardError=.*|StandardError=append:$SCRIPT_DIR/logs/api-service-error.log|g" "$SCRIPT_DIR/drone-spots-api.service"

# Copy service file to systemd
echo "📋 Installing systemd service..."
sudo cp "$SCRIPT_DIR/drone-spots-api.service" /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/drone-spots-api.service

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
sudo systemctl enable drone-spots-api

# Start the service
echo "🚀 Starting the service..."
sudo systemctl start drone-spots-api

# Wait a moment for service to start
sleep 2

# Check status
echo ""
echo "📊 Service Status:"
sudo systemctl status drone-spots-api --no-pager -l | head -15

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo ""
echo "📝 Service Management:"
echo "   sudo systemctl status drone-spots-api   # Check status"
echo "   sudo systemctl restart drone-spots-api  # Restart service"
echo "   sudo systemctl stop drone-spots-api     # Stop service"
echo ""
echo "📊 View Logs:"
echo "   tail -f $SCRIPT_DIR/logs/api-service.log"
echo "   tail -f $SCRIPT_DIR/logs/api-service-error.log"
echo ""
echo "🌐 API should be available at:"
echo "   http://localhost:8001"
echo "   http://localhost:8001/docs"
echo ""
echo "=========================================="

