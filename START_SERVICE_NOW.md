# Start API Service in Background with Auto-Start on Boot

The systemd service is already configured. Run these commands to complete the setup:

## Quick Setup (Run these commands):

```bash
cd /home/arif/drones

# Update and install the service file
sudo cp drone-spots-api.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable drone-spots-api

# Start the service now
sudo systemctl start drone-spots-api

# Check status
sudo systemctl status drone-spots-api
```

## Or use the automated script:

```bash
cd /home/arif/drones
sudo ./setup_and_start_service.sh
```

## Verify it's running:

```bash
# Check service status
sudo systemctl status drone-spots-api

# Check if port 8001 is listening
ss -tuln | grep 8001

# Test the API
curl http://localhost:8001/

# View logs
tail -f logs/api-service.log
```

## Service Management Commands:

```bash
# Start/Stop/Restart
sudo systemctl start drone-spots-api
sudo systemctl stop drone-spots-api
sudo systemctl restart drone-spots-api

# Enable/Disable auto-start on boot
sudo systemctl enable drone-spots-api   # Already enabled
sudo systemctl disable drone-spots-api  # To disable

# View logs
tail -f logs/api-service.log
tail -f logs/api-service-error.log
sudo journalctl -u drone-spots-api -f
```

## What this does:

✅ Runs API in background as a systemd service  
✅ Auto-starts on system boot/reboot  
✅ Auto-restarts if the service crashes  
✅ Logs to `logs/api-service.log` and `logs/api-service-error.log`  
✅ Uses 25 workers (optimized for 12 CPU cores)  
✅ Runs on port 8001

