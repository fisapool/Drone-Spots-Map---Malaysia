# Drone-Spots-Map---Malaysia

A comprehensive web application for finding the best drone flying locations in Malaysia. The system analyzes maps, terrain data, and safety factors to recommend optimal spots for drone operations.

## 🎯 Features

- **Interactive Map Interface**: Visualize drone spots on an interactive map with multiple view modes (Standard, Satellite, Facebook HQ)
- **Smart Search**: Search by address or coordinates with customizable radius
- **Safety Scoring**: Each spot is rated based on safety factors, accessibility, and nearby no-fly zones
- **Real-time Data**: Integrates with OpenStreetMap, Nominatim, and OSRM for accurate geocoding and routing
- **RESTful API**: FastAPI backend with comprehensive endpoints for programmatic access
- **Multiple View Modes**: Switch between standard map, satellite view, and Facebook HQ view
- **Car Accessibility**: Filter spots by car accessibility
- **Distance Calculation**: Accurate road distance calculations using OSRM

## 📸 Screenshots

![Drone Spots Map Demo](demo_screenshot.png)

## 🎥 Demo Videos

### Facebook HQ View Demo (Complete)
Watch the complete demonstration of the Facebook HQ view mode:

**MP4 (Recommended):** [search_demo_facebook_hq.mp4](search_demo_facebook_hq.mp4)  
**WebM:** [search_demo_facebook_hq.webm](search_demo_facebook_hq.webm)

### Facebook View Demo
Standard Facebook view demonstration:

**MP4 (Recommended):** [search_demo_facebook.mp4](search_demo_facebook.mp4)  
**WebM:** [search_demo_facebook.webm](search_demo_facebook.webm)

### Satellite View Demo
Satellite view mode demonstration:

**MP4 (Recommended):** [search_demo_satellite.mp4](search_demo_satellite.mp4)  
**WebM:** [search_demo_satellite.webm](search_demo_satellite.webm)

### Standard Search Demo
Basic search functionality demonstration:

**MP4 (Recommended):** [search_demo.mp4](search_demo.mp4)  
**WebM:** [search_demo.webm](search_demo.webm)

> **Note:** To convert WebM files to MP4, see [CONVERT_TO_MP4.md](CONVERT_TO_MP4.md)

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (for optional services)
- Node.js (optional, for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/fisapool/Drone-Spots-Map---Malaysia.git
   cd Drone-Spots-Map---Malaysia
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements_api.txt
   ```

3. **Set up environment variables** (optional)
   Create a `.env` file:
   ```bash
   OPENWEATHER_API_KEY=your_key_here
   NOMINATIM_URL=localhost:8080
   OSRM_URL=localhost:5000
   ```

4. **Start the API service**
   ```bash
   # For Linux/Ubuntu
   ./start_api_ubuntu.sh
   
   # Or run directly
   python drone_spots_api.py
   ```

5. **Access the map**
   Open your browser and navigate to:
   ```
   http://localhost:8001/map
   ```

## 📖 Usage

### Using the Web Interface

1. Open the map at `http://localhost:8001/map`
2. Use the search box to enter an address (e.g., "Kuala Lumpur")
3. Adjust the search radius if needed
4. Click "Search" to find drone spots
5. Click on markers to see detailed information
6. Use view controls to switch between map types

### Using the API

#### Search by Address
```bash
curl "http://localhost:8001/search?address=Kuala%20Lumpur&radius_km=10"
```

#### Search by Coordinates
```bash
curl "http://localhost:8001/search?latitude=3.1526&longitude=101.7022&radius_km=10"
```

#### Get Spot Details
```bash
curl "http://localhost:8001/spot?latitude=3.1526&longitude=101.7022"
```

### Using Python Scripts

```bash
# View spots on map automatically
python view_spots_on_map.py "Kuala Lumpur"

# Search with custom radius
python view_spots_on_map.py "Kuala Lumpur" --radius 20

# Load from JSON file
python view_spots_on_map.py --file response.json
```

## 🏗️ Architecture

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Geopy**: Geocoding and distance calculations
- **Nominatim**: OpenStreetMap geocoding service
- **OSRM**: Open Source Routing Machine for road distances

### Frontend
- **Leaflet.js**: Interactive map library
- **Vanilla JavaScript**: No framework dependencies
- **Responsive Design**: Works on desktop and mobile

### Services (Optional)
- **Nominatim**: Self-hosted geocoding (via Docker)
- **OSRM**: Self-hosted routing (via Docker)

## 📚 Documentation

- [API Quick Reference](API_QUICK_REFERENCE.md)
- [API Service Setup](API_SERVICE_SETUP.md)
- [How to Use Map](HOW_TO_USE_MAP.md)
- [Nominatim Setup](NOMINATIM_SETUP.md)
- [OSRM Setup](OSRM_SETUP.md)
- [Network Access](NETWORK_ACCESS.md)
- [Troubleshooting](MAP_TROUBLESHOOTING.md)

## 🔧 Configuration

### API Settings

The API can be configured via environment variables or `.env` file:

```bash
# OpenWeatherMap API key (optional)
OPENWEATHER_API_KEY=your_key

# Self-hosted Nominatim (optional)
NOMINATIM_URL=localhost:8080
USE_SELF_HOSTED_NOMINATIM=true

# Self-hosted OSRM (optional)
OSRM_URL=localhost:5000
USE_OSRM=true

# Performance settings
WORKERS=8
MAX_KEEPALIVE_CONNECTIONS=100
MAX_CONNECTIONS=200
TIMEOUT=30.0
```

## 🐳 Docker Services

### Run Nominatim (Optional)
```bash
docker-compose -f docker-compose.nominatim.yml up -d
```

### Run OSRM (Optional)
```bash
docker-compose -f docker-compose.osrm.yml up -d
```

## 🧪 Testing

```bash
# Test the API
curl http://localhost:8001/

# Test search endpoint
curl "http://localhost:8001/search?address=Kuala%20Lumpur"

# Run map tests
./run_map_tests.sh
```

## 📊 API Endpoints

- `GET /` - API health check
- `GET /search` - Search for drone spots by address or coordinates
- `GET /spot` - Get detailed information about a specific spot
- `GET /map` - Interactive map interface
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- OpenStreetMap for map data
- Nominatim for geocoding
- OSRM for routing
- Leaflet.js for map visualization
- FastAPI for the backend framework

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: Make sure to comply with local drone regulations and obtain necessary permissions before flying in any location.
