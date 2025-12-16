# Drone Spots API - Quick Reference

## Setup & Network Access

### Starting the Server
```bash
python drone_spots_api.py
```

The API binds to `0.0.0.0:8000` by default, making it accessible from:
- **Localhost**: `http://localhost:8000` (same machine only)
- **Network**: `http://<your-ip>:8000` (other devices on same network)

### Finding Your Network IP
```bash
# Use the helper script
python get_network_ip.py

# Or manually (Linux/macOS)
ip addr show | grep "inet " | grep -v 127.0.0.1

# Or (Windows)
ipconfig | findstr IPv4
```

**Note**: Make sure your firewall allows connections on port 8000. See `NETWORK_ACCESS.md` for detailed instructions.

## Base URL
- **Current Running Instance**: `http://localhost:8001` (gunicorn with 25 workers)
- **Default Port**: `8000` (when running `python drone_spots_api.py` directly)
- **Network Access**: `http://<your-ip>:8001` (use `get_network_ip.py` to find)
- **Example Network**: `http://192.168.0.145:8001` (your IP may differ)

**Note**: Your API is currently running on port 8001 via gunicorn. If you start it with `python drone_spots_api.py`, it will use port 8000 by default.

## Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs` or `http://<your-ip>:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc` or `http://<your-ip>:8000/redoc`

---

## Available Endpoints

### 1. Root Endpoint
**GET** `/`

Returns basic API information and available endpoints.

**Example:**
```bash
curl "http://192.168.0.145:8001/"
```

**Response:**
```json
{
  "service": "Malaysia Drone Spots API",
  "version": "1.0.0",
  "description": "Find the best drone flying locations in Malaysia",
  "endpoints": {
    "/search": "Search for drone spots",
    "/docs": "API documentation",
    "/map": "Interactive map visualization"
  }
}
```

---

### 2. Search Endpoint
**GET** `/search`

Main endpoint to search for drone flying spots.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `latitude` | float | No | - | Latitude for 'near me' search |
| `longitude` | float | No | - | Longitude for 'near me' search |
| `address` | string | No | - | Address, POI, or location name |
| `state` | string | No | - | Malaysian state name |
| `district` | string | No | - | District name |
| `radius_km` | float | No | 10.0 | Search radius in kilometers |
| `spot_types` | string | No | - | Comma-separated: `open_field,beach,hill_mountain,scenic_town` |
| `max_results` | int | No | 20 | Maximum number of results |
| `car_accessible_only` | bool | No | false | Filter to show only car-accessible spots |

**Examples:**

1. Search by address:
```bash
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&radius_km=10&max_results=5"
```

2. Search by coordinates:
```bash
curl "http://192.168.0.145:8001/search?latitude=3.1390&longitude=101.6869&radius_km=15"
```

3. Search by state:
```bash
curl "http://192.168.0.145:8001/search?state=Kedah&radius_km=20"
```

4. Filter by spot types:
```bash
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&spot_types=beach,open_field&radius_km=15"
```

5. Car accessible only:
```bash
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&car_accessible_only=true&radius_km=15"
```

**Response Structure:**
```json
{
  "query_location": {
    "latitude": 3.1390,
    "longitude": 101.6869,
    "address": "Kuala Lumpur, Malaysia",
    "state": null,
    "district": null
  },
  "total_spots_found": 15,
  "spots": [
    {
      "name": "Location Name",
      "latitude": 3.1234,
      "longitude": 101.3456,
      "address": "Full address",
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
      "weather": {
        "wind_speed_ms": 5.2,
        "temperature_c": 28.5,
        "is_safe": true,
        "weather_description": "Wind: 5.2 m/s, Temp: 28.5°C, Clear"
      },
      "google_maps_url": "https://www.google.com/maps?q=3.1234,101.3456",
      "openstreetmap_url": "https://www.openstreetmap.org/?mlat=3.1234&mlon=101.3456&zoom=15"
    }
  ],
  "search_radius_km": 15.0
}
```

---

### 3. No-Fly Zones Endpoint
**GET** `/no-fly-zones`

Get list of no-fly zones (airports and military areas) near a location.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `latitude` | float | **Yes** | - | Latitude to search around |
| `longitude` | float | **Yes** | - | Longitude to search around |
| `radius_km` | float | No | 50.0 | Search radius in kilometers |

**Example:**
```bash
curl "http://192.168.0.145:8001/no-fly-zones?latitude=3.1390&longitude=101.6869&radius_km=50"
```

**Response:**
```json
{
  "query_location": {
    "latitude": 3.1390,
    "longitude": 101.6869,
    "radius_km": 50.0
  },
  "no_fly_zones": {
    "airports": [
      {
        "name": "Lapangan Terbang Antarabangsa Kuala Lumpur",
        "lat": 2.7431652,
        "lon": 101.7004552,
        "radius_km": 5.0,
        "type": "airport"
      }
    ],
    "military_areas": [
      {
        "name": "Military Area",
        "lat": 3.0198648,
        "lon": 101.3640533,
        "radius_km": 3.0,
        "type": "military"
      }
    ]
  },
  "total_airports": 3,
  "total_military_areas": 15,
  "note": "Data fetched from OpenStreetMap. Always check with local aviation authorities before flying."
}
```

---

### 4. Spot Types Endpoint
**GET** `/spot-types`

Get available spot types and their descriptions.

**Example:**
```bash
curl "http://192.168.0.145:8001/spot-types"
```

**Response:**
```json
{
  "spot_types": {
    "open_field": {
      "description": "Open fields, parks, sports complexes - great for beginners",
      "examples": "Local sports fields, large empty grounds, parks"
    },
    "beach": {
      "description": "Coastal areas and beaches - expansive views and sunset potential",
      "examples": "Kuala Kedah beaches, coastal stretches"
    },
    "hill_mountain": {
      "description": "Hilly and mountainous regions - excellent elevation and dramatic scenery",
      "examples": "Gunung Jerai, hills around Kedah"
    },
    "scenic_town": {
      "description": "Scenic towns and heritage areas - unique urban/heritage shots",
      "examples": "George Town, historical areas"
    }
  }
}
```

---

### 5. Elevation Path Endpoint
**GET** `/elevation-path`

Analyze elevation along a flight path to detect terrain obstacles.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `start_latitude` | float | **Yes** | - | Starting latitude |
| `start_longitude` | float | **Yes** | - | Starting longitude |
| `end_latitude` | float | **Yes** | - | Ending latitude |
| `end_longitude` | float | **Yes** | - | Ending longitude |
| `flight_altitude_m` | float | No | 50.0 | Flight altitude in meters above ground level |

**Example:**
```bash
curl "http://192.168.0.145:8001/elevation-path?start_latitude=3.1390&start_longitude=101.6869&end_latitude=3.2000&end_longitude=101.7500&flight_altitude_m=50"
```

**Response:**
```json
{
  "start_location": {
    "latitude": 3.1390,
    "longitude": 101.6869
  },
  "end_location": {
    "latitude": 3.2000,
    "longitude": 101.7500
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

---

### 6. Map Endpoint
**GET** `/map`

Serves an interactive HTML map visualization page.

**Example:**
Open in browser:
```
http://192.168.0.145:8001/map
```

Or use curl:
```bash
curl "http://192.168.0.145:8001/map" -o map.html
```

---

## Spot Types

The API supports four types of drone spots:

1. **`open_field`** - Parks, sports fields, recreation areas
2. **`beach`** - Coastal areas and beaches
3. **`hill_mountain`** - Elevated areas and viewpoints
4. **`scenic_town`** - Urban/heritage locations

---

## Response Fields Explained

### Spot Information Fields:
- **`name`**: Location name
- **`latitude/longitude`**: GPS coordinates
- **`address`**: Full address string
- **`spot_type`**: Category (see Spot Types above)
- **`distance_km`**: Distance from query location
- **`car_accessible`**: Boolean indicating car accessibility
- **`car_accessibility`**: Detailed accessibility info (road type, parking, score)
- **`elevation_m`**: Elevation in meters
- **`safety_score`**: Safety score (0-10, higher is better)
- **`no_fly_zones_nearby`**: List of nearby restricted areas
- **`terrain_type`**: Classification (flat, hilly, mountainous, coastal)
- **`weather`**: Weather conditions (wind, temperature, visibility, safety)
- **`google_maps_url`**: Link to Google Maps
- **`openstreetmap_url`**: Link to OpenStreetMap

### Car Accessibility Fields:
- **`accessible`**: Whether accessible by car
- **`distance_to_road_m`**: Distance to nearest road in meters
- **`road_type`**: Road type (motorway, primary, secondary, etc.)
- **`has_parking`**: Whether parking is available nearby
- **`parking_distance_m`**: Distance to nearest parking
- **`accessibility_score`**: Quality score (0-10, higher is better)

### Weather Fields:
- **`wind_speed_ms`**: Wind speed in m/s
- **`wind_deg`**: Wind direction in degrees
- **`temperature_c`**: Temperature in Celsius
- **`humidity`**: Humidity percentage
- **`visibility_m`**: Visibility in meters
- **`weather_main`**: Main weather condition
- **`clouds`**: Cloud coverage percentage
- **`is_safe`**: Whether weather is safe for flying
- **`weather_description`**: Human-readable description

---

## Safety Features

The API automatically checks for:
- ✅ **Airports**: 5km radius no-fly zones
- ✅ **Military Areas**: 3km radius no-fly zones
- ✅ **Weather Conditions**: Wind speed, visibility, precipitation
- ✅ **Terrain Analysis**: Slope and elevation data
- ✅ **Car Accessibility**: Road access and parking availability

---

## Quick Test Script

Run the comprehensive exploration script:
```bash
python3 explore_api.py
```

This will test all endpoints and display their responses.

---

## Error Handling

The API uses standard HTTP status codes:
- **200**: Success
- **400**: Bad Request (validation error, invalid parameters)
- **404**: Not Found (resource not found)
- **500**: Internal Server Error
- **503**: Service Unavailable (external API error)

Error responses include:
```json
{
  "error": "ErrorType",
  "message": "Human-readable error message"
}
```

---

## Notes

- All no-fly zones are fetched from **OpenStreetMap** in real-time
- Weather data requires an OpenWeatherMap API key (optional)
- Results are sorted by safety score, accessibility, and distance
- Data is cached to improve performance
- Always verify with local aviation authorities before flying

---

## Python Client Example

```python
import requests

BASE_URL = "http://192.168.0.145:8001"

# Search for spots
response = requests.get(f"{BASE_URL}/search", params={
    "address": "Kuala Lumpur",
    "radius_km": 15,
    "max_results": 10
})

data = response.json()
for spot in data["spots"]:
    print(f"{spot['name']}: Safety {spot['safety_score']}/10")
```

---

## JavaScript/Fetch Example

```javascript
const BASE_URL = 'http://192.168.0.145:8001';

async function searchSpots(address) {
  const response = await fetch(
    `${BASE_URL}/search?address=${encodeURIComponent(address)}&radius_km=15`
  );
  const data = await response.json();
  return data.spots;
}

// Usage
searchSpots('Kuala Lumpur').then(spots => {
  console.log(`Found ${spots.length} spots`);
});
```
