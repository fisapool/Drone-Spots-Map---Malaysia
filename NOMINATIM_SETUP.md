# Self-Hosted Nominatim Setup Guide

This guide explains how to set up and use a self-hosted Nominatim instance for the Malaysia Drone Spots API.

## Why Self-Hosted Nominatim?

- **No Rate Limits**: Public Nominatim has rate limits (1 request/second)
- **Faster Response**: Local instance is faster than public API
- **Privacy**: All geocoding happens on your server
- **Control**: Full control over data and updates
- **Malaysia-Focused**: Only imports Malaysia data (faster, smaller)

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM (4GB minimum)
- At least 50GB free disk space
- Ubuntu 22.04 LTS (recommended) or similar Linux distribution

## Quick Setup

### Step 1: Run Setup Script

```bash
# Make script executable
chmod +x setup_nominatim.sh

# Run setup
./setup_nominatim.sh
```

The script will:
- Check Docker installation
- Create `.env` file if it doesn't exist
- Start the Nominatim container
- Begin importing Malaysia OSM data

### Step 2: Monitor Import Progress

The import process takes **2-6 hours** depending on your system. Monitor progress with:

```bash
docker-compose -f docker-compose.nominatim.yml logs -f
```

You'll see progress messages like:
```
[INFO] Importing Malaysia data...
[INFO] Processing nodes: 45% complete
```

### Step 3: Verify Installation

Once import is complete, test the service:

```bash
# Check status
curl http://localhost:8080/status

# Test geocoding (search)
curl "http://localhost:8080/search?q=Kuala+Lumpur&format=json"

# Test reverse geocoding
curl "http://localhost:8080/reverse?lat=3.1390&lon=101.6869&format=json"
```

### Step 4: Configure API to Use Self-Hosted Nominatim

Update your `.env` file:

```bash
# Enable self-hosted Nominatim
USE_SELF_HOSTED_NOMINATIM=true
NOMINATIM_URL=localhost:8080
NOMINATIM_SCHEME=http
```

Restart your API:

```bash
# If using systemd service
sudo systemctl restart drone-spots-api

# Or if running manually
python drone_spots_api.py
```

## Manual Setup (Alternative)

If you prefer manual setup:

### 1. Create Docker Compose File

The `docker-compose.nominatim.yml` file is already created. Review and adjust settings if needed.

### 2. Set Environment Variables

Create or update `.env`:

```bash
NOMINATIM_PASSWORD=your_secure_password_here
NOMINATIM_PORT=8080
POSTGRES_PORT=5433
NOMINATIM_THREADS=4
```

### 3. Start Container

```bash
docker-compose -f docker-compose.nominatim.yml up -d
```

### 4. Monitor Logs

```bash
docker-compose -f docker-compose.nominatim.yml logs -f
```

## Configuration Options

### Environment Variables

Edit `.env` file to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `NOMINATIM_PASSWORD` | `changeme123` | PostgreSQL password (change for production!) |
| `NOMINATIM_PORT` | `8080` | Port for Nominatim API |
| `POSTGRES_PORT` | `5433` | PostgreSQL port (5433 to avoid conflicts) |
| `NOMINATIM_THREADS` | `4` | Number of import threads (adjust based on CPU cores) |

### Performance Tuning

For better performance, adjust in `docker-compose.nominatim.yml`:

```yaml
environment:
  THREADS: 8  # Increase for more CPU cores
  POSTGRES_SHARED_BUFFERS: 2GB  # Increase if you have more RAM
  POSTGRES_EFFECTIVE_CACHE_SIZE: 4GB  # Increase if you have more RAM
```

## Updating Data

Nominatim data should be updated weekly to stay current. To update:

### Option 1: Automatic Updates (Recommended)

Set up a cron job:

```bash
# Edit crontab
crontab -e

# Add weekly update (every Sunday at 2 AM)
0 2 * * 0 cd /home/arif/drones && docker-compose -f docker-compose.nominatim.yml exec nominatim sudo -u nominatim /app/utils/update.php --import-file /app/data/malaysia-updates.osm.pbf
```

### Option 2: Manual Update

```bash
# Download latest Malaysia data
docker-compose -f docker-compose.nominatim.yml exec nominatim \
    sudo -u nominatim /app/utils/update.php --import-file /app/data/malaysia-updates.osm.pbf
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.nominatim.yml logs

# Check if port is already in use
netstat -tulpn | grep 8080
```

### Import Taking Too Long

- Increase `THREADS` in `.env` (but not more than CPU cores)
- Ensure sufficient RAM (8GB+ recommended)
- Check disk space: `df -h`

### API Can't Connect to Nominatim

1. Verify Nominatim is running:
   ```bash
   docker ps | grep nominatim
   ```

2. Test connection:
   ```bash
   curl http://localhost:8080/status
   ```

3. Check firewall:
   ```bash
   sudo ufw allow 8080/tcp
   ```

4. Verify `.env` settings:
   ```bash
   cat .env | grep NOMINATIM
   ```

### Out of Memory

If you get out of memory errors:

1. Reduce `THREADS` in `.env`
2. Reduce PostgreSQL memory settings in `docker-compose.nominatim.yml`
3. Add swap space:
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## Maintenance Commands

```bash
# Start Nominatim
docker-compose -f docker-compose.nominatim.yml start

# Stop Nominatim
docker-compose -f docker-compose.nominatim.yml stop

# Restart Nominatim
docker-compose -f docker-compose.nominatim.yml restart

# View logs
docker-compose -f docker-compose.nominatim.yml logs -f

# Remove everything (WARNING: deletes all data)
docker-compose -f docker-compose.nominatim.yml down -v

# Check container status
docker ps | grep nominatim

# Check disk usage
docker system df
```

## Resource Usage

### Disk Space

- Malaysia OSM data: ~500MB compressed
- After import: ~5-10GB
- With updates: ~15GB over time

### Memory

- Minimum: 4GB RAM
- Recommended: 8GB+ RAM
- During import: Can use up to 6-8GB

### CPU

- Import: Uses all available cores (configurable via THREADS)
- Normal operation: Low CPU usage (<10%)

## Security Considerations

1. **Change Default Password**: Update `NOMINATIM_PASSWORD` in `.env`
2. **Firewall**: Only expose port 8080 if needed externally
3. **Network**: Consider using Docker networks for internal communication
4. **Updates**: Keep Docker images updated

## Switching Between Public and Self-Hosted

You can easily switch between public and self-hosted Nominatim:

### Use Self-Hosted:
```bash
# In .env
USE_SELF_HOSTED_NOMINATIM=true
NOMINATIM_URL=localhost:8080
NOMINATIM_SCHEME=http
```

### Use Public (Default):
```bash
# In .env
USE_SELF_HOSTED_NOMINATIM=false
# Or simply comment out/remove the above lines
```

## Support

For issues:
1. Check logs: `docker-compose -f docker-compose.nominatim.yml logs`
2. Check Nominatim status: `curl http://localhost:8080/status`
3. Review this guide's troubleshooting section
4. Check Nominatim documentation: https://nominatim.org/release-docs/latest/

## Next Steps

Once Nominatim is running:
1. Update your API `.env` to use self-hosted instance
2. Restart your API service
3. Test geocoding to verify it's working
4. Set up automatic weekly updates
5. Monitor performance and adjust settings as needed

