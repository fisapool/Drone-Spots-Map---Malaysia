# OSRM Setup for Road Distance Calculation

This guide explains how to set up OSRM (Open Source Routing Machine) to calculate road distances instead of straight-line distances.

## Quick Start

1. **Start OSRM service:**
   ```bash
   docker compose -f docker-compose.osrm.yml up -d
   ```

2. **Wait for processing** (first time only, takes ~10-30 minutes depending on your system):
   - The service will extract, partition, and customize the OSM data
   - Check logs: `docker logs -f osrm`
   - Once you see "Processing complete!" and the server starts, it's ready

3. **Configure the API** (optional):
   - By default, the API will use OSRM at `http://localhost:5000`
   - To use a different OSRM instance, set environment variables:
     ```bash
     OSRM_URL=your-osrm-host:5000
     OSRM_SCHEME=http  # or https
     USE_OSRM=true
     ```

4. **Disable OSRM** (fallback to geodesic distance):
   ```bash
   USE_OSRM=false
   ```

## How It Works

- The API will automatically use OSRM for road distance calculations when available
- If OSRM is unavailable or can't find a route, it falls back to geodesic (straight-line) distance
- Road distances are cached to improve performance
- The distance shown in the API response (`distance_km`) will be the road distance

## Troubleshooting

- **OSRM not responding**: Check if the container is running: `docker ps | grep osrm`
- **Slow processing**: The first-time OSM data processing can take 10-30 minutes. Be patient.
- **Out of memory (Killed)**: 
  - The MLD algorithm requires significant memory (8GB+ recommended)
  - If you see "Killed" during customization, try:
    1. Increase memory limits in `docker-compose.osrm.yml` (currently set to 8G)
    2. Use the CH algorithm instead (more memory-efficient):
       ```bash
       docker compose -f docker-compose.osrm.ch.yml up -d
       ```
    3. Clear and restart: `docker compose -f docker-compose.osrm.yml down -v && docker compose -f docker-compose.osrm.yml up -d`
- **Port conflicts**: Change `OSRM_PORT` environment variable if port 5000 is already in use
- **"Could not find any metrics for MLD"**: The data processing was incomplete. Clear the volume and restart:
  ```bash
  docker compose -f docker-compose.osrm.yml down -v
  docker compose -f docker-compose.osrm.yml up -d
  ```

## Algorithm Options

- **MLD (Multi-Level Dijkstra)**: Default, faster queries but requires more memory (8GB+)
  - Use: `docker-compose.osrm.yml`
- **CH (Contraction Hierarchies)**: More memory-efficient, slightly slower queries (6GB+)
  - Use: `docker-compose.osrm.ch.yml`

## Testing

Test OSRM is working:
```bash
curl "http://localhost:5000/route/v1/driving/101.6869,3.1390;101.6869,3.1390?overview=false"
```

You should get a JSON response with route information.

