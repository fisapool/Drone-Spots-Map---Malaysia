# How to Run the Drone Spots API

## Quick Start

### Method 1: Direct Python (Simple)

```bash
cd /home/arif/drones
python3 drone_spots_api.py
```

The API will start on `http://0.0.0.0:8000` (accessible from all network interfaces).

### Method 2: Using Virtual Environment (Recommended)

```bash
cd /home/arif/drones

# Activate virtual environment
source venv/bin/activate

# Run the API
python3 drone_spots_api.py
```

### Method 3: Using Uvicorn Directly

```bash
cd /home/arif/drones
source venv/bin/activate

# Single worker
uvicorn drone_spots_api:app --host 0.0.0.0 --port 8000

# Multiple workers (Linux/macOS only)
uvicorn drone_spots_api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Method 4: Using Gunicorn (Production)

```bash
cd /home/arif/drones
source venv/bin/activate

# With multiple workers
gunicorn drone_spots_api:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

## Access the API

Once running, access the API at:

- **Localhost**: `http://localhost:8000`
- **Network**: `http://192.168.0.145:8000` (or your network IP)
- **API Docs**: `http://localhost:8000/docs`
- **JSON Viewer**: `http://localhost:8000/json-viewer`
- **Interactive Map**: `http://localhost:8000/map`

## Check if API is Running

```bash
# Test the API
curl http://localhost:8000/

# Or check if port is in use
lsof -i :8000
# Or
netstat -tuln | grep 8000
```

## Stop the API

Press `Ctrl+C` in the terminal where it's running.

If running in background, find and kill the process:
```bash
# Find the process
ps aux | grep drone_spots_api

# Kill it (replace PID with actual process ID)
kill <PID>
```

## Troubleshooting

### Port Already in Use

If you get "Address already in use":
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process (replace PID)
kill <PID>

# Or use a different port by modifying drone_spots_api.py
# Change port=8000 to port=8002
```

### Permission Denied

```bash
# Make sure you have permissions
chmod +x drone_spots_api.py
```

### Module Not Found

```bash
# Install dependencies
pip install -r requirements_api.txt

# Or if using venv
source venv/bin/activate
pip install -r requirements_api.txt
```

## Running in Background

### Using nohup

```bash
nohup python3 drone_spots_api.py > api.log 2>&1 &
```

### Using screen

```bash
screen -S api
python3 drone_spots_api.py
# Press Ctrl+A then D to detach
# Reattach with: screen -r api
```

### Using tmux

```bash
tmux new -s api
python3 drone_spots_api.py
# Press Ctrl+B then D to detach
# Reattach with: tmux attach -t api
```

## Environment Variables

You can configure the API using environment variables:

```bash
# Set OpenWeather API key (optional)
export OPENWEATHER_API_KEY=your_key_here

# Set number of workers (Linux/macOS)
export WORKERS=4

# Set max connections
export MAX_CONNECTIONS=200

# Then run
python3 drone_spots_api.py
```

Or create a `.env` file:
```bash
OPENWEATHER_API_KEY=your_key_here
WORKERS=4
MAX_CONNECTIONS=200
```

## Current Status

Your API is currently running on **port 8001** via gunicorn with 25 workers.

To run a new instance on port 8000:
1. Stop any process on port 8000 (if needed)
2. Run: `python3 drone_spots_api.py`

Or continue using the existing instance on port 8001.


