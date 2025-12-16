# API Service Setup Guide

This guide explains how to set up the Drone Spots API to run automatically as a systemd service, ensuring it's always available.

## Quick Setup

1. **Install the systemd service:**
   ```bash
   sudo ./setup_api_service.sh
   ```

2. **Start and enable the service:**
   ```bash
   sudo systemctl enable --now drone-spots-api
   ```

3. **Check status:**
   ```bash
   sudo systemctl status drone-spots-api
   ```

## Service Management Commands

### Start/Stop/Restart
```bash
sudo systemctl start drone-spots-api    # Start the service
sudo systemctl stop drone-spots-api     # Stop the service
sudo systemctl restart drone-spots-api  # Restart the service
```

### Enable/Disable Auto-Start
```bash
sudo systemctl enable drone-spots-api   # Enable auto-start on boot
sudo systemctl disable drone-spots-api  # Disable auto-start
```

### Check Status
```bash
sudo systemctl status drone-spots-api   # Detailed status
systemctl is-active drone-spots-api     # Quick check (active/inactive)
```

## Viewing Logs

### Real-time logs
```bash
# Service logs
tail -f logs/api-service.log
tail -f logs/api-service-error.log

# Or use journalctl (systemd logs)
sudo journalctl -u drone-spots-api -f
```

### Recent logs
```bash
sudo journalctl -u drone-spots-api -n 50  # Last 50 lines
sudo journalctl -u drone-spots-api --since "1 hour ago"
```

## Service Features

- **Auto-restart**: Service automatically restarts if it crashes
- **Auto-start on boot**: Starts automatically when system boots
- **Resource limits**: Memory and file descriptor limits configured
- **Logging**: All output logged to `logs/api-service.log`
- **Multi-worker**: Uses optimal number of workers based on CPU cores

## Troubleshooting

### Service won't start
1. Check logs: `sudo journalctl -u drone-spots-api -n 50`
2. Verify virtual environment exists: `ls -la venv/bin/uvicorn`
3. Check permissions: `ls -la /home/arif/drones`
4. Test manually: `./start_api_ubuntu.sh`

### Service keeps restarting
1. Check error logs: `tail -f logs/api-service-error.log`
2. Verify port 8001 is available: `sudo netstat -tulpn | grep 8001`
3. Check for Python errors in logs

### Port already in use
```bash
# Find process using port 8001
sudo lsof -i :8001

# Kill the process (replace PID with actual process ID)
sudo kill -9 <PID>
```

## Manual Service File Location

The service file is installed at:
- `/etc/systemd/system/drone-spots-api.service`

To edit it:
```bash
sudo nano /etc/systemd/system/drone-spots-api.service
sudo systemctl daemon-reload
sudo systemctl restart drone-spots-api
```

## API Improvements

The API client (`view_spots_on_map.py`) now includes:

1. **Retry Logic**: Automatically retries failed requests (3 attempts)
2. **Exponential Backoff**: Waits longer between retries (2s, 4s, 8s)
3. **Health Checks**: Checks API health before making requests
4. **Connection Pooling**: Reuses connections for better performance
5. **Better Error Messages**: More helpful error messages with troubleshooting tips

## Testing the API

After starting the service, test it:
```bash
# Check if API is responding
curl http://localhost:8001/

# Test search endpoint
curl "http://localhost:8001/search?address=Kuala%20Lumpur&radius_km=10"

# View API docs
xdg-open http://localhost:8001/docs
```

## Uninstalling the Service

To remove the systemd service:
```bash
sudo systemctl stop drone-spots-api
sudo systemctl disable drone-spots-api
sudo rm /etc/systemd/system/drone-spots-api.service
sudo systemctl daemon-reload
```

