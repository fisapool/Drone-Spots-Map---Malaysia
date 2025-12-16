# Map Access Guide

## Overview
The Drone Spots API includes an interactive map visualization feature that displays drone spots on a 3D map using Cesium.

## Accessing the Map

### Option 1: Via API Endpoint (Recommended)
Once the API is running, access the map at:
- **Local**: `http://localhost:8001/map`
- **From other PC**: `http://192.168.0.145:8001/map`

The map will load with sample data. You can paste JSON data from API responses into the text area and click "Load & Display Spots".

### Option 2: Using the Helper Script
Use the `view_spots_on_map.py` script to fetch data from the API and automatically open the map:

```bash
# Search by address
python view_spots_on_map.py "Kuala Lumpur"

# Search by coordinates
python view_spots_on_map.py --lat 5.737 --lon 100.417

# Load from JSON file
python view_spots_on_map.py --file response.json

# Specify search radius
python view_spots_on_map.py "Kuala Lumpur" --radius 20
```

### Option 3: Direct File Access
Open `map_spots.html` directly in your browser:
- The map will load with sample data
- You can manually paste JSON data from API responses

## Map Features

- **Interactive 3D markers**: Click markers to see detailed spot information
- **Color-coded safety**: 
  - 🟢 Green = High safety (8-10)
  - 🟡 Yellow = Medium safety (5-7)
  - 🔴 Red = Low safety (<5)
- **Sidebar listing**: All spots listed with key details
- **Click to focus**: Click any spot card to zoom and highlight on map
- **No-fly zone warnings**: Spots with nearby no-fly zones are clearly marked
- **External links**: Direct links to Google Maps and OpenStreetMap for each spot

## Getting Data for the Map

### From API Search Endpoint
```bash
# Search and get JSON data
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&radius_km=10" > spots.json

# Then load in map or use:
python view_spots_on_map.py --file spots.json
```

### Direct Browser Access
1. Open `http://192.168.0.145:8001/map` in your browser
2. Make an API call to get spots data
3. Copy the JSON response
4. Paste it into the map's text area
5. Click "Load & Display Spots"

## Configuration

The `view_spots_on_map.py` script uses:
- **API URL**: `http://localhost:8001` (default, or set `API_BASE_URL` environment variable)
- **Port**: 8001 (matches current API setup)

## Notes

- The map uses Cesium for 3D visualization
- No API keys required for the map itself
- Map data is loaded client-side (works offline once loaded)
- The map endpoint is available at `/map` on the API server



