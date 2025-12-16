# Malaysia Drone Spots API

A comprehensive API service to find the best drone flying locations in Malaysia by analyzing maps and terrain data. The service uses OpenStreetMap and elevation data to identify suitable spots that are accessible by car.

## Features

- 🔍 **Multiple Search Methods**:
  - Search by coordinates (near me)
  - Search by address or POI name
  - Search by state or district
  - Search near specific locations

- 🗺️ **Map & Terrain Analysis**:
  - Uses OpenStreetMap data for location discovery
  - Elevation data for terrain analysis
  - Terrain type classification (flat, hilly, mountainous, coastal)

- 🚁 **Drone-Specific Features**:
  - No-fly zone detection (airports, military areas)
  - Safety scoring (0-10) with weather integration
  - Car accessibility verification
  - Spot categorization (open fields, beaches, hills, scenic towns)
  - **Weather conditions** (wind speed, visibility, precipitation)
  - **Elevation path analysis** for flight planning

- 📍 **Spot Categories**:
  - **Open Fields/Parks**: Great for beginners
  - **Beaches**: Coastal areas with expansive views
  - **Hills/Mountains**: Elevated areas for dramatic shots
  - **Scenic Towns**: Urban/heritage locations

## Installation

```bash
# Install dependencies
pip install -r requirements_api.txt

# Set up environment variables (optional)
# Create a .env file or export environment variables:
export OPENWEATHER_API_KEY=your_api_key_here  # Optional - for weather data
export WORKERS=4  # Optional - number of workers (default: 1)
export MAX_CONNECTIONS=200  # Optional - max HTTP connections (default: 200)
export MAX_KEEPALIVE_CONNECTIONS=100  # Optional - keepalive connections (default: 100)

# Run the API server
python drone_spots_api.py
```

The API will be available at `http://localhost:8000`

**Note**: Weather data requires an OpenWeatherMap API key. The API will work without it, but weather information will not be available. Get a free API key at https://openweathermap.org/api

### Performance Optimization

The API now includes performance optimizations to handle higher request loads:

- **Multiple Workers**: Configure via `WORKERS` environment variable (default: 1)
  - Windows: Multiple workers not supported, will default to 1
  - Linux/macOS: Set to `(2 * CPU cores) + 1` for optimal performance (e.g., 4-8 workers)
  - Example: `export WORKERS=4` before starting the server

- **Connection Pooling**: Optimized HTTP connection pooling for external APIs
  - `MAX_CONNECTIONS`: Maximum total HTTP connections (default: 200)
  - `MAX_KEEPALIVE_CONNECTIONS`: Keepalive connection limit (default: 100)
  - Reduces connection overhead when making multiple external API calls

**Estimated Capacity**:
- Default (1 worker): ~10-50 requests/minute
- With 4 workers (Linux): ~40-200 requests/minute
- With optimizations: ~100-500 requests/minute (limited by external API rate limits)

**Note**: Actual capacity depends on hardware, network, and external API rate limits (e.g., OpenWeatherMap free tier: 60 req/min).

### Ubuntu/Linux Deployment

Ubuntu fully supports multiple workers for optimal performance. Here are Ubuntu-specific deployment options:

#### Quick Start (Ubuntu)
```bash
# Make the script executable
chmod +x start_api_ubuntu.sh

# Run with auto-detected optimal worker count
./start_api_ubuntu.sh
```

#### Production Deployment (Ubuntu)
For production environments on Ubuntu, use Gunicorn with Uvicorn workers:

```bash
# Install Gunicorn
pip install gunicorn

# Make the production script executable
chmod +x start_api_production_ubuntu.sh

# Run with production settings
./start_api_production_ubuntu.sh
```

Or manually:
```bash
# Set optimal worker count (2 * CPU cores + 1)
export WORKERS=9  # For 4-core system: (2*4)+1 = 9

# Start with Gunicorn
gunicorn drone_spots_api:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

#### Ubuntu Systemd Service (Recommended for Production)
Create a systemd service file for auto-start and management:

```bash
# Create service file
sudo nano /etc/systemd/system/drone-spots-api.service
```

Add the following content:
```ini
[Unit]
Description=Malaysia Drone Spots API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/drones
Environment="PATH=/path/to/venv/bin"
Environment="WORKERS=9"
Environment="OPENWEATHER_API_KEY=your_key_here"
ExecStart=/path/to/venv/bin/gunicorn drone_spots_api:app \
    --workers 9 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable drone-spots-api
sudo systemctl start drone-spots-api
sudo systemctl status drone-spots-api
```

#### Ubuntu with Nginx Reverse Proxy
For production with SSL and load balancing:

1. Install Nginx:
```bash
sudo apt update
sudo apt install nginx
```

2. Create Nginx configuration:
```nginx
# /etc/nginx/sites-available/drone-spots-api
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable and reload:
```bash
sudo ln -s /etc/nginx/sites-available/drone-spots-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Examples

### 1. Search Near Sungai Seluang, Kedah

```bash
curl "http://localhost:8000/search?address=Sungai%20Seluang,%20Kedah&radius_km=15&max_results=10"
```

### 2. Search by State

```bash
curl "http://localhost:8000/search?state=Kedah&spot_types=beach,hill_mountain&radius_km=20"
```

### 3. Search Near POI (Gunung Jerai)

```bash
curl "http://localhost:8000/search?address=Gunung%20Jerai&radius_km=10&spot_types=hill_mountain"
```

### 4. Search Using Coordinates

```bash
curl "http://localhost:8000/search?latitude=6.1164&longitude=100.3681&radius_km=15"
```

### 5. Search by District

```bash
curl "http://localhost:8000/search?district=Alor%20Setar&radius_km=10"
```

### 6. Search Only Car-Accessible Spots

```bash
curl "http://localhost:8000/search?address=Kuala%20Lumpur&radius_km=15&car_accessible_only=true"
```

### 7. Analyze Elevation Path

```bash
curl "http://localhost:8000/elevation-path?start_latitude=6.1164&start_longitude=100.3681&end_latitude=6.2000&end_longitude=100.4000&flight_altitude_m=50"
```

## API Endpoints

### GET `/search`

Search for drone flying spots.

**Query Parameters:**
- `latitude` (float, optional): Latitude for 'near me' search
- `longitude` (float, optional): Longitude for 'near me' search
- `address` (string, optional): Address, POI, or location name
- `state` (string, optional): Malaysian state name
- `district` (string, optional): District name
- `radius_km` (float, default=10.0): Search radius in kilometers
- `spot_types` (string, optional): Comma-separated types: `open_field,beach,hill_mountain,scenic_town`
- `max_results` (int, default=20): Maximum number of results
- `car_accessible_only` (bool, default=false): Filter to show only car-accessible spots

**Response:**
```json
{
  "query_location": {
    "latitude": 6.1164,
    "longitude": 100.3681,
    "address": "Sungai Seluang, Kedah",
    "state": null,
    "district": null
  },
  "total_spots_found": 15,
  "spots": [
    {
      "name": "Taman Rekreasi Sungai Seluang",
      "latitude": 6.1234,
      "longitude": 100.3456,
      "address": "Sungai Seluang, Kedah, Malaysia",
      "spot_type": "open_field",
      "distance_km": 2.5,
      "car_accessible": true,
      "car_accessibility": {
        "accessible": true,
        "distance_to_road_m": 45.2,
        "road_type": "primary",
        "has_parking": true,
        "parking_distance_m": 120.5,
        "accessibility_score": 9.5
      },
      "elevation_m": 15.2,
      "safety_score": 9.5,
      "no_fly_zones_nearby": [],
      "description": "Open field location suitable for drone flying",
      "terrain_type": "flat",
      "google_maps_url": "https://www.google.com/maps?q=6.1234,100.3456",
      "openstreetmap_url": "https://www.openstreetmap.org/?mlat=6.1234&mlon=100.3456&zoom=15"
    }
  ],
  "search_radius_km": 15.0
}
```

### GET `/no-fly-zones`

Get list of known no-fly zones in Malaysia.

### GET `/spot-types`

Get available spot types and descriptions.

### GET `/elevation-path`

Analyze elevation along a flight path to detect terrain obstacles.

**Query Parameters:**
- `start_latitude` (float, required): Starting latitude
- `start_longitude` (float, required): Starting longitude
- `end_latitude` (float, required): Ending latitude
- `end_longitude` (float, required): Ending longitude
- `flight_altitude_m` (float, default=50.0): Flight altitude in meters above ground level

**Response:**
```json
{
  "start_location": {
    "latitude": 6.1164,
    "longitude": 100.3681
  },
  "end_location": {
    "latitude": 6.2000,
    "longitude": 100.4000
  },
  "path_analysis": {
    "max_obstacle_elevation": 245.3,
    "min_elevation": 12.5,
    "elevation_range": 232.8,
    "obstacles": [],
    "safe": true,
    "path_distance_km": 12.5,
    "flight_altitude_m": 50.0,
    "ground_clearance_m": 50.0
  }
}
```

## Response Fields

- **name**: Location name
- **latitude/longitude**: GPS coordinates
- **address**: Full address
- **spot_type**: Category (open_field, beach, hill_mountain, scenic_town)
- **distance_km**: Distance from query location
- **car_accessible**: Whether accessible by car (boolean)
- **car_accessibility**: Detailed car accessibility information (object)
  - **accessible**: Whether accessible by car
  - **distance_to_road_m**: Distance to nearest road in meters
  - **road_type**: Type of nearest road (e.g., "motorway", "primary", "secondary", "tertiary")
  - **has_parking**: Whether parking is available nearby
  - **parking_distance_m**: Distance to nearest parking in meters (if available)
  - **accessibility_score**: Accessibility quality score (0-10, higher is better)
- **elevation_m**: Elevation in meters
- **safety_score**: Safety score (0-10, higher is better)
- **no_fly_zones_nearby**: List of nearby no-fly zones
- **terrain_type**: Terrain classification
- **weather**: Weather information object (if available)
  - **wind_speed_ms**: Wind speed in m/s
  - **wind_deg**: Wind direction in degrees
  - **temperature_c**: Temperature in Celsius
  - **humidity**: Humidity percentage
  - **visibility_m**: Visibility in meters
  - **weather_main**: Main weather condition
  - **clouds**: Cloud coverage percentage
  - **is_safe**: Whether weather conditions are safe for flying
  - **weather_description**: Human-readable weather description
- **google_maps_url**: Link to Google Maps
- **openstreetmap_url**: Link to OpenStreetMap

## Safety Features

The API checks for:
- **Airports**: 5km radius no-fly zones (fetched from OpenStreetMap)
- **Military Areas**: 3km radius no-fly zones (fetched from OpenStreetMap)
- **Weather Conditions**: Wind speed, visibility, and precipitation
  - Safe wind speed: < 15 m/s (~33 mph)
  - Safe visibility: > 5km
  - No precipitation (rain, snow, thunderstorms)
- **Safety Scoring**: Based on proximity to no-fly zones, elevation, and weather conditions
- **Elevation Path Analysis**: Detects terrain obstacles along planned flight paths

## No-Fly Zones

The API dynamically fetches no-fly zones from **OpenStreetMap** using the Overpass API:
- **Airports**: All airports and aerodromes within the search radius
- **Military Areas**: All military installations and restricted areas

No-fly zones are fetched in real-time based on your search location, ensuring up-to-date information.

### Get No-Fly Zones Endpoint

```bash
# Get no-fly zones near a location
curl "http://localhost:8000/no-fly-zones?latitude=6.1164&longitude=100.3681&radius_km=50"
```

This endpoint returns all airports and military areas within the specified radius, fetched from OpenStreetMap.

## Running Examples

```bash
# Make sure API is running first
python drone_spots_api.py

# In another terminal, run examples
python api_examples.py
```

## Map Visualization

View drone spots on an interactive map! The map visualization shows all spots with color-coded markers based on safety scores.

### Quick Start

1. **Open the map directly**: Simply open `map_spots.html` in your web browser
   - The map will load with sample data from Bujang Valley
   - You can paste JSON data from API responses into the text area and click "Load & Display Spots"

2. **Use the helper script** to fetch from API and open automatically:
```bash
# Search by address
python view_spots_on_map.py "Bujang Valley Archaeological Museum"

# Search by coordinates
python view_spots_on_map.py --lat 5.737 --lon 100.417

# Load from JSON file
python view_spots_on_map.py --file response.json

# Specify search radius
python view_spots_on_map.py "Kuala Lumpur" --radius 20
```

### Map Features

- **Interactive markers**: Click markers to see detailed spot information
- **Color-coded safety**: 
  - 🟢 Green = High safety (8-10)
  - 🟡 Yellow = Medium safety (5-7)
  - 🔴 Red = Low safety (<5)
- **Sidebar listing**: All spots listed with key details
- **Click to focus**: Click any spot card to zoom and highlight on map
- **No-fly zone warnings**: Spots with nearby no-fly zones are clearly marked
- **External links**: Direct links to Google Maps and OpenStreetMap for each spot

The map uses Leaflet (OpenStreetMap) and requires no API keys - it works completely offline once loaded!

## Notes

- **Real-time Data**: All no-fly zones are fetched from OpenStreetMap in real-time, not hardcoded
- **Geocoding**: Improved geocoding handles various location formats (addresses, POIs, landmarks)
- Always verify with local aviation authorities before flying
- No-fly zones are based on OpenStreetMap data - check official sources for accuracy
- Terrain data may have limitations in remote areas
- **Enhanced Car Accessibility**: 
  - Checks road types (motorway, primary, secondary, etc.)
  - Verifies parking availability nearby
  - Calculates distance to nearest road
  - Provides accessibility score (0-10) based on road quality, distance, and parking
  - Results are sorted to prioritize easily accessible spots
  - Filter results to show only car-accessible spots with `car_accessible_only=true`

## Technologies Used

- **FastAPI**: Modern Python web framework
- **OpenStreetMap/Overpass API**: 
  - Location and map data
  - Airport and aerodrome data
  - Military area data
  - Road and accessibility data
- **OpenElevation API**: Elevation data
- **OpenWeatherMap API**: Weather conditions (wind, temperature, visibility, precipitation)
- **Geopy/Nominatim**: Geocoding and reverse geocoding

## New Features (v1.1.0)

### Weather Integration
- Real-time weather data for each spot
- Weather-based safety assessment
- Wind speed, visibility, and precipitation checking
- Weather data cached for 1 hour to reduce API calls

### Elevation Path Analysis
- Analyze terrain along flight paths
- Detect obstacles and elevation changes
- Plan safe flight routes with terrain clearance
- Sample multiple points along path for accurate analysis

### Enhanced Error Handling
- Improved logging for debugging
- Better error messages for external API failures
- Graceful degradation when services are unavailable

## New Features (v1.2.0)

### Enhanced Car Accessibility
- **Detailed Road Analysis**: Checks road types (motorway, primary, secondary, etc.) and surface quality
- **Parking Detection**: Identifies nearby parking areas and calculates distance
- **Accessibility Scoring**: Provides a 0-10 accessibility score based on:
  - Distance to nearest road
  - Road type and quality (paved vs unpaved)
  - Parking availability and proximity
- **Smart Filtering**: Filter results to show only car-accessible spots with `car_accessible_only=true`
- **Improved Ranking**: Results are automatically sorted to prioritize easily accessible spots
- **Performance**: Car accessibility data is cached to reduce API calls

## License

This is a tool for finding drone spots. Always follow local regulations and obtain necessary permissions before flying.

