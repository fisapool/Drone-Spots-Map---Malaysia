#!/bin/bash
# Script to check and optionally stop process on port 8000

echo "Checking what's running on port 8000..."
echo ""

# Check for processes on port 8000
if command -v lsof &> /dev/null; then
    echo "Using lsof:"
    sudo lsof -i :8000
elif command -v ss &> /dev/null; then
    echo "Using ss:"
    ss -tulpn | grep :8000
elif command -v netstat &> /dev/null; then
    echo "Using netstat:"
    sudo netstat -tulpn | grep :8000
fi

echo ""
echo "To stop the process on port 8000, you can:"
echo "1. Find the PID from above"
echo "2. Run: sudo kill <PID>"
echo ""
echo "Or if it's a systemd service:"
echo "   sudo systemctl stop <service-name>"

