# Quick Start: Make API Always Run

## One-Time Setup (Run as sudo)

```bash
cd /home/arif/drones
sudo ./setup_api_service.sh
sudo systemctl enable --now drone-spots-api
```

That's it! The API will now:
- ✅ Start automatically on boot
- ✅ Restart automatically if it crashes
- ✅ Run in the background
- ✅ Use optimal worker count based on your CPU

## Verify It's Running

```bash
# Check status
sudo systemctl status drone-spots-api

# Test the API
curl http://localhost:8001/

# View logs
tail -f logs/api-service.log
```

## Common Commands

```bash
# Start/Stop/Restart
sudo systemctl start drone-spots-api
sudo systemctl stop drone-spots-api
sudo systemctl restart drone-spots-api

# View logs
sudo journalctl -u drone-spots-api -f

# Check if running
systemctl is-active drone-spots-api
```

## API Improvements

The API client now has:
- 🔄 **Automatic retries** (3 attempts with exponential backoff)
- 🏥 **Health checks** before making requests
- 🔗 **Connection pooling** for better performance
- 📝 **Better error messages** with troubleshooting tips

## Troubleshooting

**API not responding?**
```bash
# Check if service is running
sudo systemctl status drone-spots-api

# Check logs
sudo journalctl -u drone-spots-api -n 50

# Restart service
sudo systemctl restart drone-spots-api
```

**Port already in use?**
```bash
# Find what's using port 8001
sudo lsof -i :8001

# Kill the process (replace PID)
sudo kill -9 <PID>
```

For more details, see `API_SERVICE_SETUP.md`

