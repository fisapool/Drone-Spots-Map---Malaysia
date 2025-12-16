# Adoptable Features Analysis from Similar Repositories

This document summarizes features we can adopt from the cloned repositories to enhance our drone spots API.

## 1. FastAPI-Air-guardian ⭐ **MOST RELEVANT**

### What We Can Adopt:

#### ✅ **Better FastAPI Structure**
- **Proper error handling** with custom error classes
- **Pydantic schemas** for request/response validation
- **SQLAlchemy models** for database (if we want to add persistence)
- **Async/await patterns** with httpx for external API calls
- **CORS middleware** configuration (we already have this)

**Implementation Ideas:**
```python
# Enhanced error handling
class Errors:
    @staticmethod
    def handle_httpx_error(e):
        logger.error(f"HTTP error: {e}")
        raise HTTPException(status_code=500, detail="External API error")
```

#### ✅ **Database Models for Caching**
- Store frequently accessed spots in a database
- Cache elevation data
- Track search history

#### ✅ **Background Task Processing**
- Use Celery for periodic no-fly zone updates
- Background elevation data fetching
- Cache warming for popular locations

### Code Examples to Adopt:

```python
# Better async patterns
async with httpx.AsyncClient() as client:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
```

---

## 2. dronevision ⭐ **VERY RELEVANT** - Terrain + Weather

### What We Can Adopt:

#### ✅ **GeoJSON Polygon-Based No-Fly Zones**
Currently we use **radius-based** no-fly zones. dronevision uses **GeoJSON polygons** which are more accurate:

```python
# Current: radius-based
airports.append({
    "lat": airport_lat,
    "lon": airport_lon,
    "radius_km": 5
})

# Better: Polygon-based from GeoJSON
# Example from dronevision:
# {
#   "type": "Feature",
#   "geometry": {
#     "type": "Polygon",
#     "coordinates": [[[lon, lat], [lon, lat], ...]]
#   }
# }
```

**Implementation:**
```python
import geopandas as gpd
from shapely.geometry import Point, Polygon

def check_polygon_no_fly_zone(lat, lon, geojson_file):
    """Check if point is inside polygon no-fly zone"""
    point = Point(lon, lat)
    zones = gpd.read_file(geojson_file)
    for idx, zone in zones.iterrows():
        if zone.geometry.contains(point):
            return True
    return False
```

#### ✅ **Weather API Integration**
dronevision uses **pyowm** (OpenWeatherMap) for weather:

```python
import pyowm
owm = pyowm.OWM('api_key')
observation = owm.weather_at_coords(lat, lon)
w = observation.get_weather()
weather = {
    'wind': w.get_wind(),  # {'speed': 4.6, 'deg': 330}
    'humidity': w.get_humidity(),
    'temperature': w.get_temperature('celsius')
}
```

**We can add:**
- Wind speed checking (critical for drones)
- Precipitation probability
- Visibility conditions
- Weather-based safety scoring

#### ✅ **Terrain Path Analysis**
dronevision checks elevation **along a path** (not just single point):

```python
def get_elevation_path(gmaps, points, METERS_LOOK):
    """Get elevation profile along a path"""
    return elevation.elevation_along_path(gmaps, points, METERS_LOOK)
```

**Use case:** Check if there are obstacles along the planned flight path.

#### ✅ **ElasticSearch for Spatial Queries**
For large-scale deployments, ElasticSearch can efficiently query spatial data:
- Geo-shape queries for polygon intersections
- Fast radius searches
- Better than OSM Overpass for frequent queries

---

## 3. drone-flightplan (HOT OSM) ⭐ **TERRAIN FOCUS**

### What We Can Adopt:

#### ✅ **DEM (Digital Elevation Model) Integration**
Use **GeoTIFF raster files** for more accurate terrain data:

```python
from osgeo import gdal
import numpy as np

def get_elevation_from_dem(raster_file, lat, lon):
    """Get elevation from DEM raster file"""
    r = gdal.Open(raster_file)
    band = r.GetRasterBand(1)
    # Transform coordinates to pixel coordinates
    # Read elevation value from raster
    elevation = band.ReadAsArray(x, y, 1, 1)[0][0]
    return elevation
```

**Advantages:**
- More accurate than API calls
- Works offline
- Faster for bulk operations
- Better for terrain analysis

#### ✅ **Terrain Following Algorithms**
For flight planning, maintain constant AGL (Above Ground Level):

```python
def terrain_following_waypoints(waypoints, dem_file, target_agl=50):
    """Adjust waypoint altitudes to maintain constant AGL"""
    for waypoint in waypoints:
        ground_elevation = get_elevation_from_dem(dem_file, waypoint.lat, waypoint.lon)
        waypoint.altitude = ground_elevation + target_agl
    return waypoints
```

#### ✅ **Slope Analysis**
Calculate terrain slope for safety assessment:

```python
def calculate_slope(dem_file, lat, lon, radius_m=100):
    """Calculate maximum slope around a point"""
    # Sample multiple points in radius
    # Calculate elevation gradient
    # Return max slope percentage
    pass
```

**Use case:** Filter out spots with dangerous slopes for takeoff/landing.

---

## 4. Can-I-Drone ⭐ **WEATHER + UI**

### What We Can Adopt:

#### ✅ **Weather API Integration Pattern**
Uses **DarkSky API** (now OpenWeatherMap) for weather:

```javascript
// Pattern we can adopt in Python
let darkskyurl = `https://api.darksky.net/forecast/${key}/${lat},${lon}?units=si`;
// Returns: wind speed, precipitation, visibility, temperature
```

**We can add weather filtering:**
- Wind speed < 15 m/s for safe flying
- No precipitation
- Visibility > 5km

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (Low Effort, High Value)

1. **✅ Weather API Integration** (dronevision pattern)
   - Add wind speed, precipitation, visibility to spot info
   - Filter spots by weather conditions
   - Update safety score based on weather

2. **✅ Better Error Handling** (FastAPI-Air-guardian pattern)
   - Custom error classes
   - Better logging
   - Graceful degradation

3. **✅ Elevation Path Analysis** (dronevision)
   - Check elevation along path to spot
   - Detect obstacles/hills in flight path

### Phase 2: Medium Effort (Medium Effort, High Value)

4. **✅ GeoJSON Polygon No-Fly Zones** (dronevision)
   - More accurate than radius-based
   - Support complex shapes
   - Use GeoPandas/Shapely for checking

5. **✅ DEM Integration** (drone-flightplan)
   - Offline terrain data
   - More accurate elevation
   - Slope analysis

### Phase 3: Advanced Features (High Effort, High Value)

6. **✅ Database Caching** (FastAPI-Air-guardian)
   - Cache popular spots
   - Store elevation data
   - Reduce API calls

7. **✅ Background Tasks** (FastAPI-Air-guardian)
   - Periodic no-fly zone updates
   - Weather data refresh
   - Elevation data pre-fetching

---

## Code Snippets to Implement

### 1. Weather Integration

```python
# Add to requirements_api.txt
# pyowm  # or openweathermap API

def get_weather_conditions(lat: float, lon: float) -> Optional[Dict]:
    """Get weather conditions for a location"""
    try:
        # Using OpenWeatherMap API (free tier available)
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": os.getenv("OPENWEATHER_API_KEY"),
            "units": "metric"
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "wind_speed_ms": data["wind"]["speed"],
                "wind_deg": data["wind"].get("deg", 0),
                "temperature_c": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "visibility_m": data.get("visibility", 10000),
                "weather_main": data["weather"][0]["main"],
                "clouds": data["clouds"]["all"]
            }
    except Exception as e:
        logger.error(f"Weather API error: {e}")
    return None

def is_safe_weather(weather: Dict) -> bool:
    """Check if weather conditions are safe for flying"""
    if not weather:
        return True  # Default to safe if weather check fails
    
    wind_safe = weather["wind_speed_ms"] < 15  # 15 m/s = ~33 mph
    visibility_safe = weather["visibility_m"] > 5000  # 5km
    no_precipitation = weather["weather_main"] not in ["Rain", "Snow", "Thunderstorm"]
    
    return wind_safe and visibility_safe and no_precipitation
```

### 2. Polygon No-Fly Zone Checking

```python
# Add to requirements_api.txt
# geopandas
# shapely

def check_polygon_no_fly_zones(lat: float, lon: float, geojson_path: str) -> List[str]:
    """Check if location intersects polygon no-fly zones"""
    from shapely.geometry import Point
    import geopandas as gpd
    
    point = Point(lon, lat)
    violations = []
    
    try:
        zones = gpd.read_file(geojson_path)
        for idx, zone in zones.iterrows():
            if zone.geometry.contains(point):
                name = zone.get("name", "Unknown Zone")
                violations.append(f"{name} (Polygon zone)")
    except Exception as e:
        logger.error(f"Error checking polygon zones: {e}")
    
    return violations
```

### 3. Terrain Path Analysis

```python
def check_elevation_path(
    start_lat: float, 
    start_lon: float,
    end_lat: float,
    end_lon: float,
    flight_altitude_m: float = 50
) -> Dict:
    """Check if there are terrain obstacles along flight path"""
    # Sample multiple points along path
    num_samples = 20
    path_points = []
    
    for i in range(num_samples + 1):
        ratio = i / num_samples
        lat = start_lat + (end_lat - start_lat) * ratio
        lon = start_lon + (end_lon - start_lon) * ratio
        path_points.append((lat, lon))
    
    elevations = [get_elevation(lat, lon) for lat, lon in path_points]
    
    # Check for obstacles
    max_elevation = max([e for e in elevations if e])
    ground_clearance = flight_altitude_m
    
    obstacles = []
    for i, (lat, lon, elev) in enumerate(zip(*zip(*path_points), elevations)):
        if elev and (elev + ground_clearance) > max_elevation:
            obstacles.append({
                "distance_m": i * (distance / num_samples),
                "elevation_m": elev
            })
    
    return {
        "max_obstacle_elevation": max_elevation,
        "obstacles": obstacles,
        "safe": len(obstacles) == 0
    }
```

---

## Summary of Key Adoptions

| Feature | Source | Priority | Effort | Impact |
|---------|--------|----------|--------|--------|
| Weather API | dronevision, Can-I-Drone | High | Low | High |
| Polygon No-Fly Zones | dronevision | High | Medium | High |
| DEM Integration | drone-flightplan | Medium | Medium | High |
| Elevation Path Analysis | dronevision | Medium | Low | Medium |
| Better Error Handling | FastAPI-Air-guardian | High | Low | Medium |
| Database Caching | FastAPI-Air-guardian | Low | High | Medium |
| Background Tasks | FastAPI-Air-guardian | Low | High | Low |

---

## Next Steps

1. **Implement weather integration** (easiest, high impact)
2. **Test polygon no-fly zones** with sample GeoJSON
3. **Add elevation path analysis** for flight planning
4. **Consider DEM integration** for offline use

All cloned repositories are in `cloned_repos/` directory for reference.

