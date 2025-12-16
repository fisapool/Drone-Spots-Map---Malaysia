#!/usr/bin/env python3
"""
Drone Spots API Service for Malaysia
Finds best drone flying locations by analyzing maps and terrain data.
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import httpx
import os
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math
import json
from datetime import datetime
import logging
import time
import asyncio

LOG_PATH = r"c:\Users\MYPC\Documents\drones\.cursor\debug.log"


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    openweather_api_key: Optional[str] = None
    log_path: str = r"c:\Users\MYPC\Documents\drones\.cursor\debug.log"
    # Performance optimization settings
    workers: int = 8  # Number of uvicorn workers (set to 1 for Windows, use 4+ for Linux)
    max_keepalive_connections: int = 100  # HTTP connection pool keepalive limit
    max_connections: int = 200  # Maximum total HTTP connections
    timeout: float = 30.0  # Default HTTP timeout in seconds
    # Nominatim settings (for self-hosted instance)
    nominatim_url: Optional[str] = None  # e.g., "localhost:8080" or "nominatim.example.com"
    nominatim_scheme: str = "http"  # "http" or "https"
    use_self_hosted_nominatim: bool = False  # Set to True to use self-hosted instance
    # OSRM settings (for road distance calculation)
    osrm_url: Optional[str] = None  # e.g., "localhost:5000" or "osrm.example.com"
    osrm_scheme: str = "http"  # "http" or "https"
    use_osrm: bool = True  # Set to False to use geodesic distance instead
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Initialize settings
settings = Settings()

def debug_log(session_id, run_id, hypothesis_id, location, message, data=None):
    """Write debug log entry with centralized error handling"""
    try:
        log_entry = {
            "sessionId": session_id,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass  # Silently fail if logging fails

# #region agent log
debug_log("debug-session", "startup", "A", "drone_spots_api.py:module_load", "Module loading started", {"timestamp": time.time()})
# #endregion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# #region agent log
debug_log("debug-session", "startup", "A", "drone_spots_api.py:logging_config", "Logging configured", {})
# #endregion

# --- Custom Error Classes (Feature 5: Custom Error Classes) ---
class APIError(Exception):
    """Base API error for custom handling."""
    def __init__(self, message: str, status_code: int = 500, error_type: str = "InternalError"):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)

class ExternalAPIError(APIError):
    """Error from an external service (OpenWeatherMap, OSM, Elevation API, etc.)."""
    def __init__(self, message: str, service: str):
        super().__init__(
            message=f"{service} API error: {message}",
            status_code=503,
            error_type="ExternalServiceUnavailable"
        )
        self.service = service

class GeocodingError(APIError):
    """Error in location lookup or coordinate conversion."""
    def __init__(self, message: str):
        super().__init__(
            message=f"Geocoding error: {message}",
            status_code=400,
            error_type="InvalidLocation"
        )

class ValidationError(APIError):
    """Error in request validation."""
    def __init__(self, message: str):
        super().__init__(
            message=f"Validation error: {message}",
            status_code=400,
            error_type="InvalidRequest"
        )
# --- End Custom Error Classes ---

# Initialize geocoder (use self-hosted if configured, otherwise use public Nominatim)
if settings.use_self_hosted_nominatim and settings.nominatim_url:
    geolocator = Nominatim(
        user_agent="malaysia_drone_spots_api",
        domain=settings.nominatim_url,
        scheme=settings.nominatim_scheme
    )
    logger.info(f"Using self-hosted Nominatim at {settings.nominatim_scheme}://{settings.nominatim_url}")
else:
    geolocator = Nominatim(user_agent="malaysia_drone_spots_api")
    logger.info("Using public Nominatim service")

# Shared httpx client for async requests (created on startup, closed on shutdown)
_http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    global _http_client
    _http_client = httpx.AsyncClient(
        timeout=settings.timeout,
        limits=httpx.Limits(
            max_keepalive_connections=settings.max_keepalive_connections,
            max_connections=settings.max_connections
        )
    )
    yield
    # Shutdown
    if _http_client:
        await _http_client.aclose()

app = FastAPI(
    title="Malaysia Drone Spots API",
    description="Find the best drone flying locations in Malaysia using maps and terrain analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Global Exception Handler for Custom Errors
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Catches custom APIError exceptions and returns a structured JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_type,
            "message": exc.message,
        }
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for no-fly zones to avoid repeated API calls
_no_fly_zone_cache = {}

# Cache for weather data (expires after 1 hour)
_weather_cache = {}

# Cache for elevation data (permanent cache - elevation doesn't change)
_elevation_cache = {}

# Cache for car accessibility data (expires after 24 hours)
_car_accessibility_cache = {}

# Cache for road distances (expires after 24 hours)
_road_distance_cache = {}


async def calculate_road_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """
    Calculate road distance between two points using OSRM routing service.
    Falls back to geodesic distance if OSRM is unavailable.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in kilometers, or None if calculation fails
    """
    # Check if OSRM is enabled
    if not settings.use_osrm:
        # Fall back to geodesic distance
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    # Check cache first
    cache_key = f"{round(lat1, 4)}_{round(lon1, 4)}_{round(lat2, 4)}_{round(lon2, 4)}"
    if cache_key in _road_distance_cache:
        return _road_distance_cache[cache_key]
    
    # Determine OSRM URL
    if settings.osrm_url:
        osrm_base = f"{settings.osrm_scheme}://{settings.osrm_url}"
    else:
        # Default to localhost
        osrm_base = "http://localhost:5000"
    
    # OSRM route API endpoint
    # Format: /route/v1/{profile}/{coordinates}?overview=false
    # We use 'driving' profile for car routes
    coordinates = f"{lon1},{lat1};{lon2},{lat2}"
    url = f"{osrm_base}/route/v1/driving/{coordinates}"
    params = {
        "overview": "false",  # We only need distance, not the full route geometry
        "alternatives": "false",
        "steps": "false"
    }
    
    try:
        if _http_client is None:
            # Fall back to geodesic if HTTP client not available
            distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
            return distance
        
        response = await _http_client.get(url, params=params, timeout=5.0)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                # Distance is in meters, convert to kilometers
                distance_m = data["routes"][0]["distance"]
                distance_km = distance_m / 1000.0
                
                # Cache the result
                _road_distance_cache[cache_key] = distance_km
                
                # Also cache reverse direction (same distance)
                reverse_key = f"{round(lat2, 4)}_{round(lon2, 4)}_{round(lat1, 4)}_{round(lon1, 4)}"
                _road_distance_cache[reverse_key] = distance_km
                
                return distance_km
            else:
                # OSRM couldn't find a route, fall back to geodesic
                logger.warning(f"OSRM could not find route between ({lat1}, {lon1}) and ({lat2}, {lon2}), using geodesic distance")
                distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
                return distance
        else:
            # OSRM service error, fall back to geodesic
            logger.warning(f"OSRM service returned status {response.status_code}, using geodesic distance")
            distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
            return distance
    
    except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
        # Network error or other exception, fall back to geodesic
        logger.warning(f"OSRM request failed: {e}, using geodesic distance")
        distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        return distance


# Spot categories
SPOT_CATEGORIES = {
    "open_field": {
        "keywords": ["park", "field", "sports complex", "recreation", "stadium", "playground"],
        "terrain_preference": "flat"
    },
    "beach": {
        "keywords": ["beach", "coast", "seaside", "shore", "pantai"],
        "terrain_preference": "coastal"
    },
    "hill_mountain": {
        "keywords": ["hill", "mountain", "gunung", "peak", "viewpoint", "scenic"],
        "terrain_preference": "elevated"
    },
    "scenic_town": {
        "keywords": ["heritage", "town", "city", "historical", "cultural"],
        "terrain_preference": "urban"
    }
}

# Malaysia-specific known drone spots (for boosting relevance)
# Load from JSON file
def load_malaysian_drone_spots() -> Dict[str, Dict[str, Any]]:
    """Load Malaysian drone spots from JSON file"""
    spots_file = Path(__file__).parent / "malaysian_drone_spots.json"
    try:
        with open(spots_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Malaysian drone spots file not found: {spots_file}. Using empty dict.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Malaysian drone spots JSON: {e}. Using empty dict.")
        return {}
    except Exception as e:
        logger.error(f"Error loading Malaysian drone spots: {e}. Using empty dict.")
        return {}

MALAYSIAN_DRONE_SPOTS = load_malaysian_drone_spots()

# Load Malaysian states/districts/postal codes data
def load_malaysia_postal_codes() -> Dict[str, Any]:
    """Load Malaysian postal codes data from JSON file"""
    postal_file = Path(__file__).parent / "malaysia_states_districts.json"
    try:
        with open(postal_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Create a lookup dictionary: postal_code -> state/district info
            postal_lookup = {}
            for state in data.get('states', []):
                state_name = state.get('name', '')
                # Check postal code ranges
                if 'postal_code_range' in state:
                    range_info = state['postal_code_range']
                    start = int(range_info.get('start', '00000'))
                    end = int(range_info.get('end', '99999'))
                    postal_lookup[f"{start}-{end}"] = {
                        'state': state_name,
                        'code': state.get('code', ''),
                        'range': range_info
                    }
                # Check individual postal codes
                if 'postal_codes' in state:
                    for pc in state['postal_codes']:
                        postal_lookup[pc] = {
                            'state': state_name,
                            'code': state.get('code', ''),
                            'type': 'individual'
                        }
                # Check major city postal codes
                if 'major_city_postal_codes' in state:
                    for city, codes in state['major_city_postal_codes'].items():
                        for pc in codes:
                            if pc not in postal_lookup:
                                postal_lookup[pc] = {
                                    'state': state_name,
                                    'code': state.get('code', ''),
                                    'city': city,
                                    'type': 'major_city'
                                }
                # Check district postal codes
                if 'district_postal_codes' in state:
                    for district, codes in state['district_postal_codes'].items():
                        for pc in codes:
                            if pc not in postal_lookup:
                                postal_lookup[pc] = {
                                    'state': state_name,
                                    'code': state.get('code', ''),
                                    'district': district,
                                    'type': 'district'
                                }
            return {
                'states_data': data.get('states', []),
                'postal_lookup': postal_lookup
            }
    except FileNotFoundError:
        logger.warning(f"Malaysia postal codes file not found: {postal_file}. Postal code validation disabled.")
        return {'states_data': [], 'postal_lookup': {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Malaysia postal codes JSON: {e}. Postal code validation disabled.")
        return {'states_data': [], 'postal_lookup': {}}
    except Exception as e:
        logger.error(f"Error loading Malaysia postal codes: {e}. Postal code validation disabled.")
        return {'states_data': [], 'postal_lookup': {}}

MALAYSIA_POSTAL_DATA = load_malaysia_postal_codes()


def is_within_malaysia(lat: float, lon: float) -> bool:
    """
    Check if coordinates are within Malaysia's boundaries.
    Malaysia consists of:
    - Peninsular Malaysia: ~1.0°N to 7.0°N, 99.5°E to 104.5°E
    - East Malaysia (Sabah/Sarawak): ~0.85°N to 7.36°N, 109.5°E to 119.27°E
    """
    # Peninsular Malaysia
    if 1.0 <= lat <= 7.0 and 99.5 <= lon <= 104.5:
        return True
    
    # East Malaysia (Sabah/Sarawak)
    if 0.85 <= lat <= 7.36 and 109.5 <= lon <= 119.27:
        return True
    
    return False


def is_in_east_malaysia(lat: float, lon: float) -> bool:
    """
    Check if coordinates are in East Malaysia (Sabah/Sarawak).
    East Malaysia: ~0.85°N to 7.36°N, 109.5°E to 119.27°E
    """
    return 0.85 <= lat <= 7.36 and 109.5 <= lon <= 119.27


def is_inappropriate_location(place: Dict, name: str) -> bool:
    """
    Check if a location is inappropriate for drone flying.
    Returns True if the location should be excluded (e.g., companies, factories, offices).
    """
    tags = place.get("tags", {})
    name_lower = name.lower() if name else ""
    
    # Check OSM tags that indicate inappropriate locations
    if "office" in tags:
        return True
    if "industrial" in tags:
        return True
    if "landuse" in tags and tags["landuse"] in ["industrial", "commercial"]:
        return True
    if "amenity" in tags and tags["amenity"] in ["office", "company"]:
        return True
    
    # Check name for company/business indicators
    company_keywords = [
        "technologies", "sdn bhd", "sdn. bhd.", "berhad", "bhd",
        "corporation", "corp", "inc", "ltd", "limited", "company",
        "factory", "manufacturing", "industrial", "headquarters",
        "office", "offices", "commercial", "business park"
    ]
    
    for keyword in company_keywords:
        if keyword in name_lower:
            return True
    
    return False


async def calculate_place_relevance_score(place: Dict, query_lat: float, query_lon: float) -> float:
    """
    Calculate relevance score (0-100) for a place based on multiple factors.
    Higher score = more relevant for drone flying.
    """
    score = 50.0  # Base score
    tags = place.get("tags", {})
    
    # Get place coordinates
    place_lat = None
    place_lon = None
    if "lat" in place and "lon" in place:
        place_lat = place["lat"]
        place_lon = place["lon"]
    elif "center" in place:
        place_lat = place["center"]["lat"]
        place_lon = place["center"]["lon"]
    
    # PENALIZE inappropriate locations (industrial, commercial, offices)
    name = tags.get("name", "") or tags.get("name:en", "")
    name_lower = name.lower() if name else ""
    
    # Heavy penalty for industrial/commercial locations
    if "office" in tags or "industrial" in tags:
        score -= 50
    if tags.get("landuse") in ["industrial", "commercial"]:
        score -= 50
    if tags.get("amenity") in ["office", "company"]:
        score -= 50
    
    # Penalty for company names in the name field
    company_indicators = ["technologies", "sdn bhd", "sdn. bhd.", "berhad", "bhd", 
                          "corporation", "corp", "inc", "ltd", "limited", "company",
                          "factory", "manufacturing", "headquarters"]
    if any(indicator in name_lower for indicator in company_indicators):
        score -= 40
    
    # Distance factor (closer = higher score, up to +30 points)
    if place_lat and place_lon:
        # Use road distance if available, otherwise geodesic
        distance_km = await calculate_road_distance(query_lat, query_lon, place_lat, place_lon)
        if distance_km is None:
            distance_km = geodesic((query_lat, query_lon), (place_lat, place_lon)).kilometers
        if distance_km < 1:
            score += 30
        elif distance_km < 5:
            score += 20
        elif distance_km < 10:
            score += 10
        elif distance_km > 20:
            score -= 10
    
    # Size/importance indicators (larger places = better for drones)
    # Check for area tags or size indicators
    if "area" in tags and tags["area"] == "yes":
        score += 15  # Areas are usually better than points
    if "area:ha" in tags:
        try:
            area_ha = float(tags.get("area:ha", 0))
            if area_ha > 10:
                score += 20
            elif area_ha > 5:
                score += 10
            elif area_ha > 1:
                score += 5
        except (ValueError, TypeError):
            pass
    
    # Popularity/importance indicators
    if "wikipedia" in tags or "wikidata" in tags:
        score += 10  # Notable places
    if "tourism" in tags and tags["tourism"] in ["attraction", "viewpoint"]:
        # Only boost if it's NOT an office/company (already penalized above)
        if not (tags.get("office") or tags.get("landuse") == "industrial"):
            score += 15  # Tourist attractions are often scenic
    if "historic" in tags:
        score += 10  # Historic sites are often photogenic
    
    # Quality indicators
    if "name" in tags and tags["name"]:
        score += 5  # Named places are usually more significant
    if "name:en" in tags:
        score += 3  # English name suggests international recognition
    
    # Negative factors
    if "access" in tags and tags["access"] in ["private", "no"]:
        score -= 20  # Private areas are not accessible
    if "barrier" in tags:
        score -= 10  # Barriers reduce accessibility
    
    # Spot type bonuses
    leisure_type = tags.get("leisure", "")
    if leisure_type in ["park", "recreation_ground", "sports_centre", "stadium"]:
        score += 15  # These are ideal for drones
    if tags.get("natural") == "beach":
        score += 20  # Beaches are excellent for drone photography
    if tags.get("natural") == "peak" or tags.get("tourism") == "viewpoint":
        score += 15  # Viewpoints are great for aerial photography
    
    # Check if near known Malaysian drone spots (boost relevance)
    if place_lat and place_lon:
        for spot_name, spot_data in MALAYSIAN_DRONE_SPOTS.items():
            spot_distance = geodesic((place_lat, place_lon), (spot_data["lat"], spot_data["lon"])).kilometers
            if spot_distance < 5:  # Within 5km of known good spot
                score += 10
                break
    
    return max(0.0, min(100.0, score))


class LocationRequest(BaseModel):
    """Request model for location-based search"""
    latitude: Optional[float] = Field(None, description="Latitude for 'near me' search")
    longitude: Optional[float] = Field(None, description="Longitude for 'near me' search")
    address: Optional[str] = Field(None, description="Address, POI, or location name")
    state: Optional[str] = Field(None, description="Malaysian state name")
    district: Optional[str] = Field(None, description="District name")
    postal_code: Optional[str] = Field(None, description="Malaysian postal code (5 digits)")
    radius_km: float = Field(10.0, description="Search radius in kilometers")
    spot_types: Optional[List[str]] = Field(None, description="Filter by spot types: open_field, beach, hill_mountain, scenic_town")
    max_results: int = Field(20, description="Maximum number of results")


class WeatherInfo(BaseModel):
    """Weather information for a location"""
    wind_speed_ms: Optional[float] = None
    wind_deg: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity: Optional[int] = None
    visibility_m: Optional[int] = None
    weather_main: Optional[str] = None
    clouds: Optional[int] = None
    is_safe: bool = True
    weather_description: Optional[str] = None


class CarAccessibilityInfo(BaseModel):
    """Car accessibility information"""
    accessible: bool
    distance_to_road_m: Optional[float] = None
    road_type: Optional[str] = None  # e.g., "motorway", "primary", "secondary", "tertiary", "unpaved"
    has_parking: Optional[bool] = None
    parking_distance_m: Optional[float] = None
    accessibility_score: float = Field(0.0, ge=0.0, le=10.0)  # 0-10 score for accessibility quality


class SafeAreaPolygon(BaseModel):
    """Safe area polygon definition (GeoJSON format)"""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]  # [[[lon, lat], ...]] - GeoJSON format
    radius_m: Optional[float] = None  # For circular safe areas


class SpotInfo(BaseModel):
    """Drone spot information"""
    name: str
    latitude: float
    longitude: float
    address: str
    spot_type: str
    distance_km: Optional[float] = None
    car_accessible: bool
    car_accessibility: Optional[CarAccessibilityInfo] = None
    elevation_m: Optional[float] = None
    safety_score: float = Field(0.0, ge=0.0, le=10.0)
    no_fly_zones_nearby: List[str] = []
    description: str
    terrain_type: str
    google_maps_url: str
    openstreetmap_url: str
    weather: Optional[WeatherInfo] = None
    safe_area_polygon: Optional[SafeAreaPolygon] = None  # Safe flying area polygon


class ElevationPoint(BaseModel):
    """Elevation point along a flight path"""
    distance_km: float
    elevation_m: float
    latitude: float
    longitude: float


class ElevationPathAnalysis(BaseModel):
    """Elevation path analysis result"""
    max_obstacle_elevation: Optional[float] = None
    min_elevation: Optional[float] = None
    elevation_range: Optional[float] = None
    obstacles: List[ElevationPoint] = []
    safe: bool
    path_distance_km: float
    flight_altitude_m: float
    ground_clearance_m: float
    message: Optional[str] = None


class NoFlyZone(BaseModel):
    """No-fly zone information"""
    name: str
    lat: float
    lon: float
    radius_km: float
    type: str  # "airport" or "military"


class NoFlyZonesResponse(BaseModel):
    """No-fly zones response"""
    airports: List[NoFlyZone]
    military_areas: List[NoFlyZone]


class QueryLocation(BaseModel):
    """Query location information"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response model"""
    query_location: QueryLocation
    total_spots_found: int
    spots: List[SpotInfo]
    search_radius_km: float


async def get_coordinates_from_query(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    address: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    postal_code: Optional[str] = None
) -> tuple:
    """Get coordinates from various input types using multiple geocoding strategies (async)"""
    # Known locations dictionary (including Malaysian states with their major city coordinates)
    known_locations = {
        "bujang valley archaeological museum": (5.737, 100.417),
        "lembah bujang archaeological museum": (5.737, 100.417),
        "bujang valley": (5.737, 100.417),
        "lembah bujang": (5.737, 100.417),
        # Malaysian states with their major city coordinates
        "sarawak": (1.5587, 110.3444),  # Kuching, Sarawak
        "sabah": (5.9804, 116.0735),  # Kota Kinabalu, Sabah
        "johor": (1.4927, 103.7414),  # Johor Bahru
        "kedah": (6.1254, 100.3673),  # Alor Setar
        "kelantan": (6.1254, 102.2381),  # Kota Bharu
        "melaka": (2.1896, 102.2501),  # Melaka City
        "negeri sembilan": (2.7258, 101.9378),  # Seremban
        "pahang": (3.8167, 103.3333),  # Kuantan
        "penang": (5.4164, 100.3327),  # George Town
        "perak": (4.5921, 101.0901),  # Ipoh
        "perlis": (6.4444, 100.1989),  # Kangar
        "selangor": (3.0738, 101.5183),  # Shah Alam
        "terengganu": (5.3296, 103.1370),  # Kuala Terengganu
        "wilayah persekutuan": (3.1526, 101.7022),  # Kuala Lumpur
        "kuala lumpur": (3.1526, 101.7022),  # Kuala Lumpur
        "labuan": (5.2767, 115.2417),  # Labuan
        "putrajaya": (2.9264, 101.6964),  # Putrajaya
    }
    
    if lat and lon:
        return lat, lon
    
    # Handle postal code search (Malaysian postal codes are 5 digits)
    if postal_code:
        # Clean and validate postal code
        postal_code_clean = postal_code.strip().replace(" ", "").replace("-", "")
        if postal_code_clean.isdigit() and len(postal_code_clean) == 5:
            # First, try to validate and get state/district info from JSON data
            postal_info = None
            postal_lookup = MALAYSIA_POSTAL_DATA.get('postal_lookup', {})
            
            # Check exact match first
            if postal_code_clean in postal_lookup:
                postal_info = postal_lookup[postal_code_clean]
                logger.info(f"Postal code {postal_code_clean} found in database: {postal_info.get('state', 'Unknown')}")
            else:
                # Check if it falls within a known range
                postal_int = int(postal_code_clean)
                for range_key, info in postal_lookup.items():
                    if '-' in range_key:
                        start_str, end_str = range_key.split('-')
                        if start_str.isdigit() and end_str.isdigit():
                            start = int(start_str)
                            end = int(end_str)
                            if start <= postal_int <= end:
                                postal_info = info
                                logger.info(f"Postal code {postal_code_clean} falls within range for {info.get('state', 'Unknown')}")
                                break
            
            # Try geocoding with postal code + Malaysia (or with state if we found it)
            try:
                geocode_query = f"{postal_code_clean}, Malaysia"
                if postal_info and postal_info.get('state'):
                    # Add state for better geocoding accuracy
                    geocode_query = f"{postal_code_clean}, {postal_info['state']}, Malaysia"
                
                location = await asyncio.to_thread(
                    geolocator.geocode, 
                    geocode_query, 
                    timeout=10, 
                    exactly_one=True
                )
                if location and is_within_malaysia(location.latitude, location.longitude):
                    return location.latitude, location.longitude
                elif location:
                    # Location found but outside Malaysia - log warning
                    logger.warning(f"Postal code {postal_code_clean} geocoded to location outside Malaysia: {location.address}")
            except Exception as e:
                logger.warning(f"Postal code geocoding failed: {e}")
            
            # If geocoding failed but we have postal info, we could use a fallback
            # For now, we'll let it fall through to other query strategies
        else:
            logger.warning(f"Invalid postal code format: {postal_code} (expected 5 digits)")
    
    # Check known locations early (especially for state names)
    if address:
        address_lower = address.lower().strip()
        if address_lower in known_locations:
            lat, lon = known_locations[address_lower]
            logger.info(f"Found known location for '{address}': ({lat}, {lon})")
            return lat, lon
    
    query_parts = []
    if address:
        query_parts.append(address)
    if district:
        query_parts.append(district)
    if state:
        query_parts.append(state)
    if postal_code:
        query_parts.append(postal_code)
    
    if not query_parts:
        raise ValueError("Must provide coordinates, address, state, district, or postal code")
    
    # Build comprehensive query list with multiple strategies
    queries = []
    
    # Strategy 1: Full address with state/district context and country
    if state or district:
        context_parts = [p for p in [address, district, state] if p]
        queries.append(", ".join(context_parts) + ", Malaysia")
    
    # Strategy 2: Full address with country
    queries.append(", ".join(query_parts) + ", Malaysia")
    
    # Strategy 3: Full address without country
    queries.append(", ".join(query_parts))
    
    # Strategy 4: Just the address with country (prioritize this for state names)
    if address:
        queries.insert(0, address + ", Malaysia")  # Insert at beginning for priority
        queries.append(address)
    
    # Strategy 5: Try simplified address (remove common suffixes like "Museum", "Archaeological", etc.)
    if address:
        # Remove common location suffixes that might not be in Nominatim
        simplified = address
        for suffix in [" Archaeological Museum", " Museum", " Archaeological Site", " Site"]:
            if simplified.endswith(suffix):
                simplified = simplified[:-len(suffix)].strip()
                if simplified:
                    queries.append(simplified + ", Malaysia")
                    if state:
                        queries.append(simplified + ", " + state + ", Malaysia")
                    break
    
    # Strategy 6: Try with state/district if address contains location name
    if address and (state or district):
        # Extract potential location name (first part before comma or common words)
        location_name = address.split(",")[0].strip() if "," in address else address
        if state:
            queries.append(location_name + ", " + state + ", Malaysia")
        if district:
            queries.append(location_name + ", " + district + ", Malaysia")
    
    # Remove duplicates and None values
    queries = list(dict.fromkeys([q for q in queries if q]))
    
    # Collect all matches with scoring for better ranking
    all_matches = []
    
    # Try queries with exactly_one=True first (more precise) - using async
    for query in queries:
        try:
            location = await asyncio.to_thread(geolocator.geocode, query, timeout=10, exactly_one=True)
            if location:
                # Calculate match quality score
                match_score = 0
                if "Malaysia" in location.address:
                    match_score += 10
                if state and state.lower() in location.address.lower():
                    match_score += 15
                if district and district.lower() in location.address.lower():
                    match_score += 10
                if address and address.lower() in location.address.lower():
                    match_score += 20
                # Bonus for exact query match
                if query.lower() in location.address.lower():
                    match_score += 5
                
                all_matches.append((match_score, location))
        except Exception:
            continue
    
    # If exactly_one=True didn't find good matches, try without exactly_one
    if not all_matches or max([m[0] for m in all_matches]) < 20:
        for query in queries:
            try:
                locations = await asyncio.to_thread(geolocator.geocode, query, timeout=10, exactly_one=False)
                if locations and len(locations) > 0:
                    # Score all results and add to matches
                    for location in locations[:5]:  # Limit to top 5 to avoid too many results
                        match_score = 0
                        if "Malaysia" in location.address:
                            match_score += 10
                        if state and state.lower() in location.address.lower():
                            match_score += 15
                        if district and district.lower() in location.address.lower():
                            match_score += 10
                        if address and address.lower() in location.address.lower():
                            match_score += 20
                        if query.lower() in location.address.lower():
                            match_score += 5
                        
                        all_matches.append((match_score, location))
            except Exception:
                continue
    
    # Sort by match score and return best match
    if all_matches:
        all_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Prefer matches within Malaysia
        for score, location in all_matches:
            if is_within_malaysia(location.latitude, location.longitude):
                return location.latitude, location.longitude
        
        # If no Malaysia match found, return best match but log warning
        best_match = all_matches[0][1]
        if not is_within_malaysia(best_match.latitude, best_match.longitude):
            logger.warning(f"Best geocoding match is outside Malaysia: {best_match.address}")
        return best_match.latitude, best_match.longitude
    
    # All Nominatim queries failed - try known coordinates as final fallback
    if address:
        address_lower = address.lower().strip()
        if address_lower in known_locations:
            lat, lon = known_locations[address_lower]
            return lat, lon
    
    # If known coordinates not found, try OpenStreetMap Overpass API
    
    # Try searching OSM directly by name
    if address:
        # Try alternative names (e.g., Malay translations)
        search_names = [address]
        if "Bujang" in address or "bujang" in address.lower():
            search_names.append("Lembah Bujang")
            search_names.append("Lembah Bujang Archaeological Museum")
        
        overpass_url = "https://overpass-api.de/api/interpreter"
        for search_name in search_names:
            # Search for museums/archaeological sites in Kedah area (where Bujang Valley is located)
            # Kedah bounding box: approximately 5.0°N to 6.5°N, 99.5°E to 101.0°E
            # First try searching for museums/archaeological sites, then filter by name
            query = f"""
            [out:json][timeout:15];
            (
                node["tourism"="museum"](5.0,99.5,6.5,101.0);
                node["historic"](5.0,99.5,6.5,101.0);
                way["tourism"="museum"](5.0,99.5,6.5,101.0);
                way["historic"](5.0,99.5,6.5,101.0);
                relation["tourism"="museum"](5.0,99.5,6.5,101.0);
                relation["historic"](5.0,99.5,6.5,101.0);
            );
            out center meta;
            """
            
            try:
                # Use asyncio for this sync function
                async def _fetch_osm():
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        response = await client.get(overpass_url, params={"data": query})
                        return response
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                response = loop.run_until_complete(_fetch_osm())
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])
                    
                    # Filter elements by name matching with scoring (prioritize better matches)
                    search_name_lower = search_name.lower()
                    search_words = [w for w in search_name_lower.split() if len(w) > 3]  # Important words (>3 chars)
                    best_match = None
                    best_score = 0
                    
                    for element in elements:
                        tags = element.get("tags", {})
                        name = tags.get("name", "") or tags.get("name:en", "")
                        if not name:
                            continue
                        name_lower = name.lower()
                        
                        # Calculate match score
                        score = 0
                        # Exact match gets highest score
                        if search_name_lower == name_lower:
                            score = 100
                        # Contains full search string
                        elif search_name_lower in name_lower:
                            score = 80
                        # Contains all important words (must match at least 2 important words)
                        elif len(search_words) >= 2:
                            matched_words = sum(1 for word in search_words if word in name_lower)
                            if matched_words >= 2:
                                score = 60 + (matched_words * 10)
                        # Contains key location words (Bujang, Valley, Archaeological)
                        elif any(keyword in name_lower for keyword in ["bujang", "valley", "archaeological"]):
                            matched_keywords = sum(1 for keyword in ["bujang", "valley", "archaeological"] if keyword in name_lower)
                            score = 40 + (matched_keywords * 10)
                        
                        # Only consider matches with score >= 50 (good match threshold)
                        if score >= 50 and score > best_score:
                            # Get coordinates
                            if "lat" in element and "lon" in element:
                                lat = element["lat"]
                                lon = element["lon"]
                            elif "center" in element:
                                lat = element["center"]["lat"]
                                lon = element["center"]["lon"]
                            else:
                                continue
                            
                            best_match = (lat, lon, name, score)
                            best_score = score
                    
                    if best_match:
                        lat, lon, matched_name, score = best_match
                        return lat, lon
            except Exception:
                continue
    
    # All queries failed
    raise GeocodingError(f"Location not found: {', '.join(query_parts)}. Tried {len(queries)} different query formats, OSM direct search, and known coordinates.")


async def get_airports_from_osm(lat: float, lon: float, radius_km: float = 50) -> List[Dict]:
    """Get airports from OpenStreetMap using Overpass API"""
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    airports_start = time.time()
    debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:entry", "get_airports_from_osm started", {
        "lat": lat, "lon": lon, "radius_km": radius_km
    })
    # #endregion
    
    airports = []
    overpass_url = "https://overpass-api.de/api/interpreter"
    radius_m = int(radius_km * 1000)
    
    query = f"""
    [out:json][timeout:25];
    (
        node["aeroway"="aerodrome"](around:{radius_m},{lat},{lon});
        node["aeroway"="airport"](around:{radius_m},{lat},{lon});
        way["aeroway"="aerodrome"](around:{radius_m},{lat},{lon});
        way["aeroway"="airport"](around:{radius_m},{lat},{lon});
        relation["aeroway"="aerodrome"](around:{radius_m},{lat},{lon});
        relation["aeroway"="airport"](around:{radius_m},{lat},{lon});
    );
    out center meta;
    """
    
    try:
        # #region agent log
        api_start = time.time()
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:before_api", "Before Overpass API call for airports")
        # #endregion
        
        if _http_client is None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(overpass_url, params={"data": query})
        else:
            response = await _http_client.get(overpass_url, params={"data": query})
        
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:after_api", "After Overpass API call for airports", {
            "elapsed": time.time() - api_start, "status_code": response.status_code
        })
        # #endregion
        if response.status_code == 200:
            data = response.json()
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name") or tags.get("name:en") or "Unknown Airport"
                
                # Get coordinates
                if "lat" in element and "lon" in element:
                    airport_lat = element["lat"]
                    airport_lon = element["lon"]
                elif "center" in element:
                    airport_lat = element["center"]["lat"]
                    airport_lon = element["center"]["lon"]
                else:
                    continue
                
                airports.append({
                    "name": name,
                    "lat": airport_lat,
                    "lon": airport_lon,
                    "radius_km": 5,  # Standard airport no-fly zone
                    "type": "airport"
                })
    except httpx.HTTPStatusError as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:error", "Error in get_airports_from_osm", {
            "error": str(e), "elapsed": time.time() - airports_start
        })
        # #endregion
        logger.error(f"Error fetching airports from OSM: {e}")
        raise ExternalAPIError(f"HTTP Error {e.response.status_code}", service="OpenStreetMap Overpass")
    except httpx.RequestError as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:error", "Network error in get_airports_from_osm", {
            "error": str(e), "elapsed": time.time() - airports_start
        })
        # #endregion
        logger.error(f"Network error fetching airports from OSM: {e}")
        raise ExternalAPIError(f"Network error: {str(e)}", service="OpenStreetMap Overpass")
    except Exception as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:error", "Unexpected error in get_airports_from_osm", {
            "error": str(e), "elapsed": time.time() - airports_start
        })
        # #endregion
        logger.error(f"Unexpected error fetching airports from OSM: {e}")
        raise ExternalAPIError(f"Unexpected error: {str(e)}", service="OpenStreetMap Overpass")
    
    # #region agent log
    debug_log(session_id, run_id, "B", "drone_spots_api.py:get_airports_from_osm:exit", "get_airports_from_osm complete", {
        "total_elapsed": time.time() - airports_start, "airports_found": len(airports)
    })
    # #endregion
    
    return airports


async def get_military_areas_from_osm(lat: float, lon: float, radius_km: float = 50) -> List[Dict]:
    """Get military areas from OpenStreetMap using Overpass API"""
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    military_start = time.time()
    debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:entry", "get_military_areas_from_osm started", {
        "lat": lat, "lon": lon, "radius_km": radius_km
    })
    # #endregion
    
    military_areas = []
    overpass_url = "https://overpass-api.de/api/interpreter"
    radius_m = int(radius_km * 1000)
    
    query = f"""
    [out:json][timeout:25];
    (
        node["military"](around:{radius_m},{lat},{lon});
        node["landuse"="military"](around:{radius_m},{lat},{lon});
        way["military"](around:{radius_m},{lat},{lon});
        way["landuse"="military"](around:{radius_m},{lat},{lon});
        relation["military"](around:{radius_m},{lat},{lon});
        relation["landuse"="military"](around:{radius_m},{lat},{lon});
    );
    out center meta;
    """
    
    try:
        # #region agent log
        api_start = time.time()
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:before_api", "Before Overpass API call for military")
        # #endregion
        
        if _http_client is None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(overpass_url, params={"data": query})
        else:
            response = await _http_client.get(overpass_url, params={"data": query})
        
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:after_api", "After Overpass API call for military", {
            "elapsed": time.time() - api_start, "status_code": response.status_code
        })
        # #endregion
        if response.status_code == 200:
            data = response.json()
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name") or tags.get("name:en") or "Military Area"
                
                # Get coordinates
                if "lat" in element and "lon" in element:
                    mil_lat = element["lat"]
                    mil_lon = element["lon"]
                elif "center" in element:
                    mil_lat = element["center"]["lat"]
                    mil_lon = element["center"]["lon"]
                else:
                    continue
                
                military_areas.append({
                    "name": name,
                    "lat": mil_lat,
                    "lon": mil_lon,
                    "radius_km": 3,  # Standard military area no-fly zone
                    "type": "military"
                })
    except httpx.HTTPStatusError as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:error", "Error in get_military_areas_from_osm", {
            "error": str(e), "elapsed": time.time() - military_start
        })
        # #endregion
        logger.error(f"Error fetching military areas from OSM: {e}")
        raise ExternalAPIError(f"HTTP Error {e.response.status_code}", service="OpenStreetMap Overpass")
    except httpx.RequestError as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:error", "Network error in get_military_areas_from_osm", {
            "error": str(e), "elapsed": time.time() - military_start
        })
        # #endregion
        logger.error(f"Network error fetching military areas from OSM: {e}")
        raise ExternalAPIError(f"Network error: {str(e)}", service="OpenStreetMap Overpass")
    except Exception as e:
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:error", "Unexpected error in get_military_areas_from_osm", {
            "error": str(e), "elapsed": time.time() - military_start
        })
        # #endregion
        logger.error(f"Unexpected error fetching military areas from OSM: {e}")
        raise ExternalAPIError(f"Unexpected error: {str(e)}", service="OpenStreetMap Overpass")
    
    # #region agent log
    debug_log(session_id, run_id, "B", "drone_spots_api.py:get_military_areas_from_osm:exit", "get_military_areas_from_osm complete", {
        "total_elapsed": time.time() - military_start, "military_found": len(military_areas)
    })
    # #endregion
    
    return military_areas


async def get_no_fly_zones_for_area(lat: float, lon: float, radius_km: float = 50) -> NoFlyZonesResponse:
    """Get all no-fly zones for a given area using real APIs"""
    cache_key = f"{round(lat, 2)}_{round(lon, 2)}_{int(radius_km)}"
    
    if cache_key in _no_fly_zone_cache:
        return _no_fly_zone_cache[cache_key]
    
    airports_raw = await get_airports_from_osm(lat, lon, radius_km)
    military_areas_raw = await get_military_areas_from_osm(lat, lon, radius_km)
    
    # Convert to Pydantic models
    airports = [NoFlyZone(**airport) for airport in airports_raw]
    military_areas = [NoFlyZone(**military) for military in military_areas_raw]
    
    result = NoFlyZonesResponse(
        airports=airports,
        military_areas=military_areas
    )
    
    _no_fly_zone_cache[cache_key] = result
    return result


async def check_no_fly_zones(lat: float, lon: float, search_radius_km: float = 50, pre_fetched_zones: Optional[NoFlyZonesResponse] = None) -> List[str]:
    """Check if location is near no-fly zones using real APIs
    
    Args:
        lat: Latitude of the location to check
        lon: Longitude of the location to check
        search_radius_km: Radius to search for no-fly zones (if pre_fetched_zones not provided)
        pre_fetched_zones: Optional pre-fetched no-fly zones dict with "airports" and "military_areas" keys
    """
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    nofly_func_start = time.time()
    debug_log(session_id, run_id, "B", "drone_spots_api.py:check_no_fly_zones:entry", "check_no_fly_zones started", {
        "lat": lat, "lon": lon, "search_radius_km": search_radius_km, "has_pre_fetched": pre_fetched_zones is not None
    })
    # #endregion
    
    nearby_zones = []
    
    # Use pre-fetched zones if provided, otherwise fetch them
    if pre_fetched_zones:
        no_fly_zones = pre_fetched_zones
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:check_no_fly_zones:using_prefetched", "Using pre-fetched zones", {
            "airports": len(no_fly_zones.airports), "military": len(no_fly_zones.military_areas)
        })
        # #endregion
    else:
        # #region agent log
        get_zones_start = time.time()
        debug_log(session_id, run_id, "B", "drone_spots_api.py:check_no_fly_zones:before_get_zones", "Before get_no_fly_zones_for_area")
        # #endregion
        
        # Get no-fly zones for the area
        no_fly_zones = await get_no_fly_zones_for_area(lat, lon, search_radius_km)
        
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:check_no_fly_zones:after_get_zones", "After get_no_fly_zones_for_area", {
            "elapsed": time.time() - get_zones_start, "airports": len(no_fly_zones.airports), 
            "military": len(no_fly_zones.military_areas)
        })
        # #endregion
    
    # Check airports
    for airport in no_fly_zones.airports:
        distance = geodesic((lat, lon), (airport.lat, airport.lon)).kilometers
        if distance <= airport.radius_km:
            nearby_zones.append(f"{airport.name} (Airport, {distance:.1f}km away)")
    
    # Check military areas
    for military in no_fly_zones.military_areas:
        distance = geodesic((lat, lon), (military.lat, military.lon)).kilometers
        if distance <= military.radius_km:
            nearby_zones.append(f"{military.name} (Military Area, {distance:.1f}km away)")
    
    # #region agent log
    debug_log(session_id, run_id, "B", "drone_spots_api.py:check_no_fly_zones:exit", "check_no_fly_zones complete", {
        "total_elapsed": time.time() - nofly_func_start, "nearby_zones_count": len(nearby_zones)
    })
    # #endregion
    
    return nearby_zones


async def get_elevation(lat: float, lon: float) -> Optional[float]:
    """Get elevation using OpenElevation API. Returns None on error (elevation is optional)."""
    # Check cache first (cache key with 3 decimal precision ~100m)
    cache_key = f"{round(lat, 3)}_{round(lon, 3)}"
    if cache_key in _elevation_cache:
        return _elevation_cache[cache_key]
    
    try:
        url = "https://api.open-elevation.com/api/v1/lookup"
        payload = {"locations": [{"latitude": lat, "longitude": lon}]}
        if _http_client is None:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
        else:
            response = await _http_client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            elevation = data["results"][0].get("elevation")
            # Cache the result
            if elevation is not None:
                _elevation_cache[cache_key] = elevation
            return elevation
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Elevation API HTTP error: {e.response.status_code} - {e}")
        return None  # Elevation is optional, return None on error
    except httpx.RequestError as e:
        logger.warning(f"Elevation API network error: {e}")
        return None  # Elevation is optional, return None on error
    except Exception as e:
        logger.warning(f"Unexpected error getting elevation: {e}")
        return None  # Elevation is optional, return None on error


async def get_weather_conditions(lat: float, lon: float) -> Optional[Dict]:
    """Get weather conditions for a location using OpenWeatherMap API"""
    cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
    
    # Check cache (expires after 1 hour)
    if cache_key in _weather_cache:
        cached_data, cached_time = _weather_cache[cache_key]
        if (datetime.now().timestamp() - cached_time) < 3600:  # 1 hour
            return cached_data
    
    api_key = settings.openweather_api_key
    if not api_key:
        logger.warning("OPENWEATHER_API_KEY not set, weather data unavailable")
        return None
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric"
        }
        if _http_client is None:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
        else:
            response = await _http_client.get(url, params=params)
        response.raise_for_status()
        
        if response.status_code == 200:
            data = response.json()
            weather_data = {
                "wind_speed_ms": data.get("wind", {}).get("speed"),
                "wind_deg": data.get("wind", {}).get("deg", 0),
                "temperature_c": data.get("main", {}).get("temp"),
                "humidity": data.get("main", {}).get("humidity"),
                "visibility_m": data.get("visibility", 10000) if data.get("visibility") else 10000,
                "weather_main": data.get("weather", [{}])[0].get("main") if data.get("weather") else None,
                "clouds": data.get("clouds", {}).get("all", 0)
            }
            
            # Cache the result
            _weather_cache[cache_key] = (weather_data, datetime.now().timestamp())
            return weather_data
    except httpx.HTTPStatusError as e:
        logger.warning(f"Weather API HTTP error: {e.response.status_code} - {e}")
        return None  # Weather is optional, return None on error
    except httpx.RequestError as e:
        logger.warning(f"Weather API network error: {e}")
        return None  # Weather is optional, return None on error
    except Exception as e:
        logger.warning(f"Unexpected error getting weather: {e}")
        return None  # Weather is optional, return None on error


def is_safe_weather(weather: Optional[Dict]) -> bool:
    """Check if weather conditions are safe for flying"""
    if not weather:
        return True  # Default to safe if weather check fails
    
    wind_safe = weather.get("wind_speed_ms", 0) < 15  # 15 m/s = ~33 mph
    visibility_safe = weather.get("visibility_m", 10000) > 5000  # 5km
    no_precipitation = weather.get("weather_main", "") not in ["Rain", "Snow", "Thunderstorm", "Drizzle"]
    
    return wind_safe and visibility_safe and no_precipitation


async def check_elevation_path(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    flight_altitude_m: float = 50
) -> ElevationPathAnalysis:
    """Check if there are terrain obstacles along flight path"""
    num_samples = 20
    path_points = []
    
    # Calculate distance for path analysis
    total_distance = geodesic((start_lat, start_lon), (end_lat, end_lon)).kilometers
    
    # Sample multiple points along path
    for i in range(num_samples + 1):
        ratio = i / num_samples
        lat = start_lat + (end_lat - start_lat) * ratio
        lon = start_lon + (end_lon - start_lon) * ratio
        path_points.append((lat, lon))
    
    # Get elevations for all points concurrently
    # Use return_exceptions=True to handle individual failures gracefully
    elevation_tasks = [get_elevation(lat, lon) for lat, lon in path_points]
    elevation_results = await asyncio.gather(*elevation_tasks, return_exceptions=True)
    
    # Filter out exceptions and None values, keeping only valid elevations
    elevations = [e for e in elevation_results if not isinstance(e, Exception) and e is not None]
    
    # Filter out None values
    valid_elevations = [e for e in elevations if e is not None]
    
    if not valid_elevations:
        return ElevationPathAnalysis(
            max_obstacle_elevation=None,
            obstacles=[],
            safe=True,
            path_distance_km=total_distance,
            message="Elevation data unavailable for path",
            flight_altitude_m=flight_altitude_m,
            ground_clearance_m=flight_altitude_m
        )
    
    max_elevation = max(valid_elevations)
    min_elevation = min(valid_elevations)
    ground_clearance = flight_altitude_m
    
    # Check for obstacles (points where elevation + clearance exceeds max)
    obstacles = []
    for i, (lat, lon, elev) in enumerate(zip(*zip(*path_points), elevations)):
        if elev is not None:
            distance_along_path = (i / num_samples) * total_distance
            # Check if this point would be an obstacle
            if elev + ground_clearance > max_elevation + ground_clearance * 0.5:
                obstacles.append(ElevationPoint(
                    distance_km=round(distance_along_path, 2),
                    elevation_m=round(elev, 1),
                    latitude=lat,
                    longitude=lon
                ))
    
    return ElevationPathAnalysis(
        max_obstacle_elevation=round(max_elevation, 1),
        min_elevation=round(min_elevation, 1),
        elevation_range=round(max_elevation - min_elevation, 1),
        obstacles=obstacles,
        safe=len(obstacles) == 0,
        path_distance_km=round(total_distance, 2),
        flight_altitude_m=flight_altitude_m,
        ground_clearance_m=ground_clearance
    )


async def search_places_nearby(
    lat: float,
    lon: float,
    radius_km: float,
    spot_types: Optional[List[str]] = None
) -> List[Dict]:
    """Search for places using Overpass API (OpenStreetMap)"""
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    search_start = time.time()
    debug_log(session_id, run_id, "D", "drone_spots_api.py:search_places_nearby:entry", "search_places_nearby started", {
        "lat": lat, "lon": lon, "radius_km": radius_km, "spot_types": spot_types
    })
    # #endregion
    
    # Check if we're in East Malaysia (Sabah/Sarawak) - increase radius for better coverage
    is_east_malaysia = is_in_east_malaysia(lat, lon)
    if is_east_malaysia:
        # Increase radius by 50% for East Malaysia due to lower OSM coverage
        radius_km = radius_km * 1.5
        logger.info(f"East Malaysia detected - increasing search radius to {radius_km:.1f}km for better coverage")
    
    places = []
    
    # Overpass API query for Malaysia
    overpass_url = "https://overpass-api.de/api/interpreter"
    radius_m = int(radius_km * 1000)
    
    # Build consolidated query with union statement - combines all searches into single request
    query_parts = []
    
    # Open field searches - ENHANCED with more OSM tags
    if not spot_types or "open_field" in spot_types:
        query_parts.extend([
            f'node["leisure"="park"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="recreation_ground"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="sports_centre"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="stadium"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="pitch"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="playground"](around:{radius_m},{lat},{lon});',
            f'way["leisure"="park"](around:{radius_m},{lat},{lon});',
            f'way["leisure"="recreation_ground"](around:{radius_m},{lat},{lon});',
            f'way["leisure"="sports_centre"](around:{radius_m},{lat},{lon});',
            f'way["leisure"="stadium"](around:{radius_m},{lat},{lon});',
            # Add open spaces
            f'way["landuse"="meadow"](around:{radius_m},{lat},{lon});',
            f'way["landuse"="grass"](around:{radius_m},{lat},{lon});',
            f'way["natural"="grassland"](around:{radius_m},{lat},{lon});',
        ])
    
    # Beach searches - ENHANCED with more OSM tags
    if not spot_types or "beach" in spot_types:
        query_parts.extend([
            f'node["natural"="beach"](around:{radius_m},{lat},{lon});',
            f'node["leisure"="beach_resort"](around:{radius_m},{lat},{lon});',
            f'way["natural"="beach"](around:{radius_m},{lat},{lon});',
            f'way["natural"="coastline"](around:{radius_m},{lat},{lon});',
            f'node["tourism"="beach"](around:{radius_m},{lat},{lon});',
        ])
    
    # Hill/mountain searches - ENHANCED with more OSM tags
    if not spot_types or "hill_mountain" in spot_types:
        query_parts.extend([
            f'node["natural"="peak"](around:{radius_m},{lat},{lon});',
            f'node["tourism"="viewpoint"](around:{radius_m},{lat},{lon});',
            f'way["natural"="peak"](around:{radius_m},{lat},{lon});',
            f'way["natural"="ridge"](around:{radius_m},{lat},{lon});',
            f'node["natural"="volcano"](around:{radius_m},{lat},{lon});',
            # Add lookout points
            f'node["tourism"="attraction"]["attraction"="viewpoint"](around:{radius_m},{lat},{lon});',
        ])
    
    # Scenic town searches - ENHANCED with more OSM tags
    if not spot_types or "scenic_town" in spot_types:
        query_parts.extend([
            f'node["tourism"="attraction"](around:{radius_m},{lat},{lon});',
            f'node["historic"](around:{radius_m},{lat},{lon});',
            f'way["tourism"="attraction"](around:{radius_m},{lat},{lon});',
            f'way["historic"](around:{radius_m},{lat},{lon});',
            # Add monuments and landmarks
            f'node["historic"="monument"](around:{radius_m},{lat},{lon});',
            f'node["historic"="memorial"](around:{radius_m},{lat},{lon});',
            f'node["tourism"="museum"](around:{radius_m},{lat},{lon});',
            f'node["tourism"="gallery"](around:{radius_m},{lat},{lon});',
        ])
    
    # Generic open spaces (always included)
    query_parts.extend([
        f'node["landuse"="recreation_ground"](around:{radius_m},{lat},{lon});',
        f'way["landuse"="recreation_ground"](around:{radius_m},{lat},{lon});',
        f'node["amenity"="parking"](around:{radius_m},{lat},{lon});',
    ])
    
    # Additional broader queries for East Malaysia (Sabah/Sarawak) with lower OSM coverage
    # These include more generic tags that might exist even if specific tags don't
    if is_east_malaysia:
        query_parts.extend([
            # More generic natural features
            f'node["natural"](around:{radius_m},{lat},{lon});',
            f'way["natural"](around:{radius_m},{lat},{lon});',
            # Any tourism-related places
            f'node["tourism"](around:{radius_m},{lat},{lon});',
            f'way["tourism"](around:{radius_m},{lat},{lon});',
            # Any leisure areas
            f'node["leisure"](around:{radius_m},{lat},{lon});',
            f'way["leisure"](around:{radius_m},{lat},{lon});',
            # Landuse areas that might be open
            f'way["landuse"](around:{radius_m},{lat},{lon});',
            # Places with names (might be scenic even if not specifically tagged)
            f'node["name"](around:{radius_m},{lat},{lon});',
            f'way["name"](around:{radius_m},{lat},{lon});',
        ])
    
    # Combine all queries into a single union statement
    if query_parts:
        # #region agent log
        query_start = time.time()
        debug_log(session_id, run_id, "D", "drone_spots_api.py:search_places_nearby:before_query", "Before consolidated Overpass query", {
            "total_query_parts": len(query_parts)
        })
        # #endregion
        
        query = f"""
        [out:json][timeout:25];
        (
            {"".join(query_parts)}
        );
        out center meta;
        """
        
        try:
            if _http_client is None:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(overpass_url, params={"data": query})
            else:
                response = await _http_client.get(overpass_url, params={"data": query})
            
            # #region agent log
            debug_log(session_id, run_id, "D", "drone_spots_api.py:search_places_nearby:after_query", "After consolidated Overpass query", {
                "elapsed": time.time() - query_start, "status_code": response.status_code
            })
            # #endregion
            if response.status_code == 200:
                data = response.json()
                if "elements" in data:
                    places.extend(data["elements"])
        except httpx.HTTPStatusError as e:
            logger.warning(f"Overpass API HTTP error: {e.response.status_code} - {e}")
        except httpx.RequestError as e:
            logger.warning(f"Overpass API network error: {e}")
        except Exception as e:
            logger.warning(f"Overpass API error: {e}")
    
    # Fallback: If we're in East Malaysia and got very few results, try a broader search
    if is_east_malaysia and len(places) < 5:
        logger.info(f"East Malaysia: Only {len(places)} places found, trying broader fallback search")
        fallback_query_parts = [
            # Very broad queries - any named place
            f'node["name"](around:{int(radius_m * 1.5)},{lat},{lon});',
            f'way["name"](around:{int(radius_m * 1.5)},{lat},{lon});',
            # Any place with tourism tag
            f'node["tourism"](around:{int(radius_m * 1.5)},{lat},{lon});',
            f'way["tourism"](around:{int(radius_m * 1.5)},{lat},{lon});',
        ]
        
        fallback_query = f"""
        [out:json][timeout:30];
        (
            {"".join(fallback_query_parts)}
        );
        out center meta;
        """
        
        try:
            if _http_client is None:
                async with httpx.AsyncClient(timeout=35.0) as client:
                    response = await client.get(overpass_url, params={"data": fallback_query})
            else:
                response = await _http_client.get(overpass_url, params={"data": fallback_query})
            
            if response.status_code == 200:
                data = response.json()
                if "elements" in data:
                    fallback_places = data["elements"]
                    logger.info(f"East Malaysia fallback search found {len(fallback_places)} additional places")
                    places.extend(fallback_places)
        except Exception as e:
            logger.warning(f"East Malaysia fallback search error: {e}")
    
    # Deduplicate by coordinates
    seen = set()
    unique_places = []
    for place in places:
        if "lat" in place and "lon" in place:
            key = (round(place["lat"], 4), round(place["lon"], 4))
            if key not in seen:
                seen.add(key)
                unique_places.append(place)
        elif "center" in place:
            key = (round(place["center"]["lat"], 4), round(place["center"]["lon"], 4))
            if key not in seen:
                seen.add(key)
                unique_places.append(place)
    
    # Filter to only include places within Malaysia
    unique_places = [
        place for place in unique_places
        if (
            ("lat" in place and "lon" in place and is_within_malaysia(place["lat"], place["lon"])) or
            ("center" in place and is_within_malaysia(place["center"]["lat"], place["center"]["lon"]))
        )
    ]
    places_after_malaysia_filter = len(unique_places)
    
    # Filter out places without names (usually less significant)
    # BUT allow places with good leisure/natural tags even without names
    # Expanded to include more types of open spaces and recreational areas
    # For East Malaysia, be more lenient since OSM coverage is lower
    unique_places = [
        place for place in unique_places 
        if (
            place.get("tags", {}).get("name") or 
            place.get("tags", {}).get("name:en") or
            # Allow unnamed places with good tags for drone spots
            place.get("tags", {}).get("leisure") in ["park", "recreation_ground", "beach_resort", "sports_centre", "stadium", "pitch", "playground"] or
            place.get("tags", {}).get("natural") in ["beach", "peak", "grassland", "meadow"] or
            place.get("tags", {}).get("tourism") in ["attraction", "viewpoint"] or
            place.get("tags", {}).get("landuse") in ["meadow", "grass", "recreation_ground"] or
            place.get("tags", {}).get("historic") or  # Historic sites are often scenic
            # For East Malaysia, be more lenient - allow any place with leisure, natural, tourism, or landuse tags
            (is_east_malaysia and (
                place.get("tags", {}).get("leisure") or
                place.get("tags", {}).get("natural") or
                place.get("tags", {}).get("tourism") or
                place.get("tags", {}).get("landuse") in ["meadow", "grass", "recreation_ground", "forest", "farmland"]
            ))
        )
    ]
    places_after_name_filter = len(unique_places)
    
    # FILTER OUT inappropriate locations (companies, factories, offices)
    unique_places = [
        place for place in unique_places
        if not is_inappropriate_location(place, place.get("tags", {}).get("name", "") or place.get("tags", {}).get("name:en", ""))
    ]
    places_after_inappropriate_filter = len(unique_places)
    
    # Calculate relevance scores and rank places
    scored_places = []
    for place in unique_places:
        # Get coordinates for scoring
        place_lat = None
        place_lon = None
        if "lat" in place and "lon" in place:
            place_lat = place["lat"]
            place_lon = place["lon"]
        elif "center" in place:
            place_lat = place["center"]["lat"]
            place_lon = place["center"]["lon"]
        
        if place_lat and place_lon:
            relevance_score = await calculate_place_relevance_score(place, lat, lon)
            scored_places.append((relevance_score, place))
        else:
            # If no coordinates, give low score but don't exclude
            scored_places.append((20.0, place))
    
    # Sort by relevance score (highest first)
    scored_places.sort(key=lambda x: x[0], reverse=True)
    
    # Filter out very low relevance scores (< 5) to improve result quality
    # Lowered from 10 to 5 to allow more valid spots through, especially for areas with fewer OSM entries
    # Base score is 50, so even with penalties, most valid places should score > 5
    # This helps in areas where OSM data might be sparse
    # For East Malaysia, use even lower threshold (3) due to lower OSM coverage
    relevance_threshold = 3 if is_east_malaysia else 5
    filtered_places = [place for score, place in scored_places if score >= relevance_threshold]
    
    # #region agent log
    debug_log(session_id, run_id, "D", "drone_spots_api.py:search_places_nearby:exit", "search_places_nearby complete", {
        "total_elapsed": time.time() - search_start, 
        "raw_places_from_api": len(places),
        "unique_places_after_dedup": len(unique_places),
        "places_after_malaysia_filter": places_after_malaysia_filter,
        "places_after_name_filter": places_after_name_filter,
        "places_after_inappropriate_filter": places_after_inappropriate_filter,
        "scored_places": len(scored_places),
        "filtered_places_after_relevance": len(filtered_places),
        "total_query_parts": len(query_parts),
        "search_location": f"{lat},{lon}",
        "radius_km": radius_km
    })
    # #endregion
    
    # Log warning if no places found
    if len(filtered_places) == 0:
        logger.warning(f"No places found for location {lat},{lon} with radius {radius_km}km. "
                      f"Raw places: {len(places)}, After dedup: {len(unique_places)}, "
                      f"After Malaysia filter: {places_after_malaysia_filter}, "
                      f"After name filter: {places_after_name_filter}, "
                      f"After inappropriate filter: {places_after_inappropriate_filter}, "
                      f"Scored: {len(scored_places)}")
    
    return filtered_places


def categorize_spot(place: Dict, name: str) -> str:
    """Categorize a spot based on its properties"""
    name_lower = name.lower() if name else ""
    tags = place.get("tags", {})
    
    # EXCLUDE inappropriate locations first
    if is_inappropriate_location(place, name):
        # Return a special category that can be filtered out, or default to open_field
        # but with very low relevance
        return "open_field"  # Will be filtered by relevance score
    
    # Check tags and name for keywords
    for category, info in SPOT_CATEGORIES.items():
        for keyword in info["keywords"]:
            if keyword in name_lower or any(keyword in str(v).lower() for v in tags.values()):
                return category
    
    # Default categorization based on OSM tags
    if "leisure" in tags:
        if tags["leisure"] in ["park", "recreation_ground"]:
            return "open_field"
    if "natural" in tags:
        if tags["natural"] == "beach":
            return "beach"
        if tags["natural"] == "peak":
            return "hill_mountain"
    
    # More specific tourism categorization - only scenic if it's actually scenic
    if "tourism" in tags:
        tourism_type = tags["tourism"]
        # Only categorize as scenic_town if it's a legitimate scenic/tourist location
        if tourism_type in ["attraction", "viewpoint", "museum", "gallery", "monument", "memorial"]:
            # Double-check it's not a company/office
            if not is_inappropriate_location(place, name):
                return "scenic_town"
        # Don't categorize generic "tourism" tags as scenic_town
    
    return "open_field"  # Default


def generate_location_name(place: Dict, address: Optional[str] = None, spot_type: Optional[str] = None) -> str:
    """
    Generate a meaningful name for a location when no name is available.
    Uses address, OSM tags, and spot type to create a descriptive name.
    """
    tags = place.get("tags", {})
    
    # Try to extract name from OSM tags first
    if "name" in tags and tags["name"]:
        return tags["name"]
    if "name:en" in tags and tags["name:en"]:
        return tags["name:en"]
    
    # Try to get name from address if available
    if address:
        # Extract meaningful parts from address
        # Address format is usually: "Street/Place, Area, City, State, Postal Code, Country"
        address_parts = [part.strip() for part in address.split(",")]
        
        # Skip country (last part) and postal code (usually 5 digits)
        # Look for meaningful location names
        for part in address_parts[:-2]:  # Exclude postal code and country
            # Skip generic terms
            if part.lower() not in ["malaysia", "malaysia"] and len(part) > 3:
                # Check if it looks like a place name (not just a road type)
                if not any(road_type in part.lower() for road_type in ["jalan", "road", "street", "st", "ave", "avenue", "blvd", "boulevard"]):
                    # Capitalize properly
                    name_parts = part.split()
                    capitalized = " ".join(word.capitalize() for word in name_parts)
                    return capitalized
    
    # Use OSM tags to generate a name
    leisure = tags.get("leisure", "")
    natural = tags.get("natural", "")
    amenity = tags.get("amenity", "")
    landuse = tags.get("landuse", "")
    tourism = tags.get("tourism", "")
    
    # Build name from tags
    name_parts = []
    
    if leisure:
        leisure_names = {
            "park": "Park",
            "recreation_ground": "Recreation Ground",
            "sports_centre": "Sports Centre",
            "stadium": "Stadium",
            "pitch": "Sports Pitch",
            "playground": "Playground"
        }
        name_parts.append(leisure_names.get(leisure, leisure.replace("_", " ").title()))
    
    if natural:
        natural_names = {
            "beach": "Beach",
            "peak": "Peak",
            "ridge": "Ridge",
            "volcano": "Volcano"
        }
        name_parts.append(natural_names.get(natural, natural.replace("_", " ").title()))
    
    if tourism:
        tourism_names = {
            "attraction": "Attraction",
            "viewpoint": "Viewpoint",
            "museum": "Museum",
            "gallery": "Gallery"
        }
        name_parts.append(tourism_names.get(tourism, tourism.replace("_", " ").title()))
    
    if amenity:
        amenity_names = {
            "parking": "Parking Area"
        }
        if amenity in amenity_names:
            name_parts.append(amenity_names[amenity])
    
    if landuse:
        landuse_names = {
            "meadow": "Meadow",
            "grass": "Grassland",
            "recreation_ground": "Recreation Area"
        }
        if landuse in landuse_names:
            name_parts.append(landuse_names[landuse])
    
    # If we have name parts, combine them
    if name_parts:
        return " ".join(name_parts)
    
    # Use spot type as fallback
    if spot_type:
        spot_type_names = {
            "open_field": "Open Field",
            "beach": "Beach Area",
            "hill_mountain": "Scenic Viewpoint",
            "scenic_town": "Scenic Location"
        }
        return spot_type_names.get(spot_type, spot_type.replace("_", " ").title())
    
    # Last resort: use address first part or coordinates
    if address:
        first_part = address.split(",")[0].strip()
        if first_part and len(first_part) > 3:
            return first_part
    
    return "Unnamed Location"


async def calculate_slope(
    lat: float, 
    lon: float, 
    radius_m: float = 100,
    num_samples: int = 8
) -> Dict[str, Any]:
    """
    Calculate terrain slope around a point (Feature 6: Slope Analysis).
    
    Args:
        lat: Latitude of the center point
        lon: Longitude of the center point
        radius_m: Radius in meters to sample around the point
        num_samples: Number of sample points around the circle
    
    Returns:
        Dictionary with max_slope_percent, safe flag, and elevation_samples count
    """
    # Get center elevation and all sample elevations in parallel
    # Calculate all sample points first
    sample_points = []
    for angle in range(0, 360, 360 // num_samples):
        # Calculate point at radius using geodesic
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate offset in meters
        offset_lat = radius_m * math.cos(angle_rad) / 111320.0  # meters to degrees (approximate)
        offset_lon = radius_m * math.sin(angle_rad) / (111320.0 * math.cos(math.radians(lat)))
        
        sample_lat = lat + offset_lat
        sample_lon = lon + offset_lon
        sample_points.append((sample_lat, sample_lon))
    
    # Get all elevations in parallel (center + all samples)
    elevation_tasks = [get_elevation(lat, lon)]  # Center elevation
    elevation_tasks.extend([get_elevation(sample_lat, sample_lon) for sample_lat, sample_lon in sample_points])
    
    elevation_results = await asyncio.gather(*elevation_tasks, return_exceptions=True)
    
    # Extract center elevation
    center_elev = elevation_results[0]
    if center_elev is None or isinstance(center_elev, Exception):
        return {"max_slope_percent": None, "safe": True, "elevation_samples": 0}
    
    # Extract sample elevations
    elevations = []
    for elev in elevation_results[1:]:
        if elev is not None and not isinstance(elev, Exception):
            elevations.append(elev)
    
    if len(elevations) < 3:
        return {"max_slope_percent": None, "safe": True, "elevation_samples": len(elevations)}
    
    # Calculate max slope
    max_slope = 0.0
    for elev in elevations:
        # Calculate slope as percentage: (elevation_diff / horizontal_distance) * 100
        elevation_diff = abs(elev - center_elev)
        slope_percent = (elevation_diff / radius_m) * 100
        max_slope = max(max_slope, slope_percent)
    
    # Consider >30% slope as unsafe for takeoff/landing
    return {
        "max_slope_percent": round(max_slope, 1),
        "safe": max_slope < 30.0,
        "elevation_samples": len(elevations)
    }


def calculate_safety_score(
    lat: float,
    lon: float,
    no_fly_zones: List[str],
    elevation: Optional[float],
    weather: Optional[Dict] = None,
    slope_data: Optional[Dict[str, Any]] = None
) -> float:
    """Calculate safety score (0-10) with slope analysis integration"""
    score = 10.0
    
    # Deduct for no-fly zones
    if no_fly_zones:
        score -= len(no_fly_zones) * 3.0
    
    # Bonus for elevation (hills are often safer)
    if elevation and elevation > 100:
        score += 1.0
    
    # Adjust for slope (Feature 6: Slope Analysis integration)
    if slope_data:
        max_slope = slope_data.get("max_slope_percent")
        if max_slope is not None:
            if max_slope > 30:
                score -= 3.0  # Dangerous slope
            elif max_slope > 20:
                score -= 1.5  # Moderate slope
            elif max_slope > 10:
                score -= 0.5  # Slight slope
            # Safe slopes (<10%) don't affect score
    
    # Adjust for weather conditions
    if weather:
        weather_safe = is_safe_weather(weather)
        if not weather_safe:
            # Deduct points for unsafe weather
            wind_speed = weather.get("wind_speed_ms", 0)
            if wind_speed > 15:
                score -= 2.0
            elif wind_speed > 10:
                score -= 1.0
            
            if weather.get("weather_main") in ["Rain", "Snow", "Thunderstorm"]:
                score -= 2.0
            
            visibility = weather.get("visibility_m", 10000)
            if visibility < 5000:
                score -= 1.0
        else:
            # Small bonus for good weather
            score += 0.5
    
    return max(0.0, min(10.0, score))


def generate_safe_area_polygon(lat: float, lon: float, safety_score: float, radius_m: Optional[float] = None) -> Optional[SafeAreaPolygon]:
    """
    Generate a safe area polygon for a drone spot.
    
    Args:
        lat: Latitude of the spot
        lon: Longitude of the spot
        safety_score: Safety score (0-10)
        radius_m: Optional radius in meters. If None, determined by safety score.
    
    Returns:
        SafeAreaPolygon if safety_score >= 7, None otherwise
    """
    # Only generate safe areas for high-safety spots
    if safety_score < 7:
        return None
    
    # Determine radius based on safety score if not provided
    if radius_m is None:
        if safety_score >= 9:
            radius_m = 1000  # 1km for very safe spots
        elif safety_score >= 8:
            radius_m = 750   # 750m for safe spots
        else:
            radius_m = 500   # 500m for moderately safe spots
    
    # Generate circular polygon (GeoJSON format)
    num_points = 32  # Number of points to approximate circle
    coordinates = []
    
    for i in range(num_points + 1):
        angle = (i / num_points) * 2 * math.pi
        # Convert radius from meters to degrees (approximate)
        # 1 degree latitude ≈ 111,320 meters
        radius_deg_lat = radius_m / 111320.0
        # Longitude conversion depends on latitude
        radius_deg_lon = radius_m / (111320.0 * math.cos(math.radians(lat)))
        
        offset_lat = lat + radius_deg_lat * math.cos(angle)
        offset_lon = lon + radius_deg_lon * math.sin(angle)
        coordinates.append([offset_lon, offset_lat])  # GeoJSON format: [lon, lat]
    
    # Close the polygon (first point = last point)
    coordinates.append(coordinates[0])
    
    return SafeAreaPolygon(
        type="Polygon",
        coordinates=[coordinates],
        radius_m=radius_m
    )


async def check_car_accessible(lat: float, lon: float) -> CarAccessibilityInfo:
    """
    Check if location is accessible by car with detailed information.
    Returns a dictionary with accessibility details including road type, parking, and distance.
    """
    # #region agent log
    debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:entry", "check_car_accessible called", {"lat": lat, "lon": lon})
    # #endregion
    
    cache_key = f"{round(lat, 4)}_{round(lon, 4)}"
    
    # Check cache
    if cache_key in _car_accessibility_cache:
        # #region agent log
        debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:cache_hit", "Cache hit", {"cache_key": cache_key})
        # #endregion
        return _car_accessibility_cache[cache_key]
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Query for roads within 1km (increased from 500m for better coverage)
    # Also check for parking areas
    # Simplified query to avoid timeouts - check roads first, then parking separately if needed
    query = f"""
    [out:json][timeout:10];
    (
        way["highway"](around:1000,{lat},{lon});
    );
    out center meta;
    """
    
    result = CarAccessibilityInfo(
        accessible=False,
        distance_to_road_m=None,
        road_type=None,
        has_parking=False,
        parking_distance_m=None,
        accessibility_score=0.0
    )
    
    try:
        # #region agent log
        debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:before_api", "Before Overpass API call", {"overpass_url": overpass_url, "query_length": len(query)})
        # #endregion
        
        api_start_time = time.time()
        if _http_client is None:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(overpass_url, params={"data": query})
        else:
            response = await _http_client.get(overpass_url, params={"data": query})
        api_elapsed = time.time() - api_start_time
        
        # #region agent log
        debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:after_api", "After Overpass API call", {"status_code": response.status_code, "elapsed": api_elapsed})
        # #endregion
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            
            # #region agent log
            debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:parsing", "Parsing API response", {"elements_count": len(elements)})
            # #endregion
            
            # Separate roads and parking
            roads = []
            parking_areas = []
            
            for element in elements:
                tags = element.get("tags", {})
                
                # Check if it's a road
                if "highway" in tags:
                    # Get coordinates
                    if "lat" in element and "lon" in element:
                        road_lat = element["lat"]
                        road_lon = element["lon"]
                    elif "center" in element:
                        road_lat = element["center"]["lat"]
                        road_lon = element["center"]["lon"]
                    else:
                        continue
                    
                    # Calculate distance
                    distance = geodesic((lat, lon), (road_lat, road_lon)).meters
                    roads.append({
                        "distance_m": distance,
                        "type": tags.get("highway", "unknown"),
                        "surface": tags.get("surface", "unknown"),
                        "lat": road_lat,
                        "lon": road_lon
                    })
            
            # Now check for parking separately (simpler query)
            if roads:  # Only check parking if we found roads
                parking_query = f"""
                [out:json][timeout:5];
                (
                    node["amenity"="parking"](around:500,{lat},{lon});
                    way["amenity"="parking"](around:500,{lat},{lon});
                );
                out center;
                """
                try:
                    if _http_client is None:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            parking_response = await client.get(overpass_url, params={"data": parking_query})
                    else:
                        parking_response = await _http_client.get(overpass_url, params={"data": parking_query})
                    if parking_response.status_code == 200:
                        parking_data = parking_response.json()
                        for element in parking_data.get("elements", []):
                            if "lat" in element and "lon" in element:
                                park_lat = element["lat"]
                                park_lon = element["lon"]
                            elif "center" in element:
                                park_lat = element["center"]["lat"]
                                park_lon = element["center"]["lon"]
                            else:
                                continue
                            distance = geodesic((lat, lon), (park_lat, park_lon)).meters
                            parking_areas.append(distance)
                except Exception as park_err:
                    # #region agent log
                    debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:parking_error", "Error fetching parking", {"error": str(park_err)})
                    # #endregion
                    pass  # Parking check is optional
            
            # Find nearest road
            if roads:
                # Sort by distance
                roads.sort(key=lambda x: x["distance_m"])
                nearest_road = roads[0]
                
                # Check for parking
                has_parking = False
                parking_distance_m = None
                if parking_areas:
                    nearest_parking = min(parking_areas)
                    has_parking = True
                    parking_distance_m = round(nearest_parking, 1)
                
                # Calculate accessibility score (0-10)
                score = 10.0
                
                # Deduct for distance to road
                distance_to_road_m = round(nearest_road["distance_m"], 1)
                if nearest_road["distance_m"] > 500:
                    score -= 3.0
                elif nearest_road["distance_m"] > 200:
                    score -= 1.5
                elif nearest_road["distance_m"] > 100:
                    score -= 0.5
                
                # Road type scoring (better roads = higher score)
                road_type = nearest_road["type"]
                if road_type in ["motorway", "trunk", "primary"]:
                    score += 1.0  # Bonus for major roads
                elif road_type in ["secondary", "tertiary"]:
                    pass  # No change
                elif road_type in ["unclassified", "residential", "service"]:
                    score -= 1.0
                elif road_type in ["track", "path"]:
                    score -= 2.0
                
                # Surface quality
                surface = nearest_road.get("surface", "").lower()
                if "unpaved" in surface or "dirt" in surface or "gravel" in surface:
                    score -= 1.5
                elif "paved" in surface or "asphalt" in surface or "concrete" in surface:
                    score += 0.5
                
                # Parking bonus
                if has_parking:
                    if parking_distance_m and parking_distance_m < 100:
                        score += 1.5
                    elif parking_distance_m and parking_distance_m < 200:
                        score += 1.0
                    elif parking_distance_m and parking_distance_m < 300:
                        score += 0.5
                else:
                    score -= 0.5  # Small penalty for no parking
                
                accessibility_score = max(0.0, min(10.0, score))
                
                result = CarAccessibilityInfo(
                    accessible=True,
                    distance_to_road_m=distance_to_road_m,
                    road_type=road_type,
                    has_parking=has_parking,
                    parking_distance_m=parking_distance_m,
                    accessibility_score=accessibility_score
                )
            else:
                # No roads found
                result = CarAccessibilityInfo(
                    accessible=False,
                    accessibility_score=0.0
                )
                
    except Exception as e:
        # #region agent log
        debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:error", "Error in check_car_accessible", {"error": str(e), "error_type": type(e).__name__})
        # #endregion
        logger.warning(f"Error checking car accessibility: {e}")
        # Default to accessible but with low score if check fails
        result = CarAccessibilityInfo(
            accessible=True,
            accessibility_score=5.0
        )
    
    # Cache the result
    _car_accessibility_cache[cache_key] = result
    
    # #region agent log
    debug_log("debug-session", "runtime", "C", "drone_spots_api.py:check_car_accessible:exit", "check_car_accessible returning", {"result": result})
    # #endregion
    
    return result


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Malaysia Drone Spots API",
        "version": "1.0.0",
        "description": "Find the best drone flying locations in Malaysia",
        "endpoints": {
            "/search": "Search for drone spots",
            "/docs": "API documentation",
            "/map": "Interactive map visualization",
            "/json-viewer": "JSON viewer for testing API from other devices"
        }
    }


@app.get("/map", response_class=HTMLResponse)
async def get_map():
    """Serve the interactive map HTML page"""
    map_file = Path(__file__).parent / "map_spots.html"
    
    if not map_file.exists():
        raise HTTPException(status_code=404, detail="Map file not found")
    
    with open(map_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)


@app.get("/json-viewer", response_class=HTMLResponse)
async def get_json_viewer():
    """Serve the JSON viewer HTML page for testing API from other devices"""
    viewer_file = Path(__file__).parent / "json_viewer.html"
    
    if not viewer_file.exists():
        raise HTTPException(status_code=404, detail="JSON viewer file not found")
    
    with open(viewer_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)


async def process_single_place_parallel(
    place: Dict,
    idx: int,
    query_lat: float,
    query_lon: float,
    radius_km: float,
    pre_fetched_no_fly_zones: NoFlyZonesResponse,
    car_accessible_only: bool,
    endpoint_start: float,
    session_id: str,
    run_id: str
) -> Optional[SpotInfo]:
    """
    Process a single place with all async operations running in parallel.
    This significantly speeds up processing by running all API calls concurrently.
    """
    try:
        # Get coordinates
        if "lat" in place and "lon" in place:
            place_lat = place["lat"]
            place_lon = place["lon"]
        elif "center" in place:
            place_lat = place["center"]["lat"]
            place_lon = place["center"]["lon"]
        else:
            return None
        
        # Get name and categorize (synchronous operations)
        tags = place.get("tags", {})
        name = tags.get("name", tags.get("name:en", None))
        spot_type = categorize_spot(place, name or "")
        
        # Run all async operations in parallel
        distance_task = calculate_road_distance(query_lat, query_lon, place_lat, place_lon)
        elevation_task = get_elevation(place_lat, place_lon)
        weather_task = get_weather_conditions(place_lat, place_lon)
        slope_task = calculate_slope(place_lat, place_lon, radius_m=100, num_samples=8)
        car_accessibility_task = check_car_accessible(place_lat, place_lon)
        reverse_geocode_task = asyncio.to_thread(
            geolocator.reverse, f"{place_lat}, {place_lon}", timeout=5
        )
        
        # Wait for all operations in parallel with timeout
        # Set a reasonable timeout per place (30 seconds should be enough)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    distance_task,
                    elevation_task,
                    weather_task,
                    slope_task,
                    car_accessibility_task,
                    reverse_geocode_task,
                    return_exceptions=True
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            # If timeout, return None to skip this place
            logger.warning(f"Timeout processing place {idx} at ({place_lat}, {place_lon})")
            return None
        
        distance, elevation, weather_data, slope_data, car_accessibility_data, location = results
        
        # Handle exceptions
        if distance is None or isinstance(distance, Exception):
            distance = geodesic((query_lat, query_lon), (place_lat, place_lon)).kilometers
        elif isinstance(distance, Exception):
            distance = geodesic((query_lat, query_lon), (place_lat, place_lon)).kilometers
        
        if isinstance(elevation, Exception):
            elevation = None
        
        if isinstance(weather_data, Exception):
            weather_data = None
        
        if isinstance(slope_data, Exception):
            slope_data = None
        
        if isinstance(car_accessibility_data, Exception):
            car_accessible = True
            car_accessibility_data = CarAccessibilityInfo(accessible=True, accessibility_score=5.0)
        else:
            car_accessible = car_accessibility_data.accessible
        
        if isinstance(location, Exception):
            location = None
        
        # Filter by car accessibility if requested (early exit)
        if car_accessible_only and not car_accessible:
            return None
        
        # Check no-fly zones (synchronous operation on pre-fetched data)
        no_fly_zones = await check_no_fly_zones(
            place_lat, place_lon, 
            search_radius_km=max(radius_km, 50), 
            pre_fetched_zones=pre_fetched_no_fly_zones
        )
        
        # Calculate safety score
        safety_score = calculate_safety_score(
            place_lat, place_lon, no_fly_zones, elevation, weather_data, slope_data
        )
        
        # Get address
        address_str = location.address if location else f"{place_lat}, {place_lon}"
        
        # Generate name if needed
        if not name or name == "Unnamed Location":
            name = generate_location_name(place, address_str, spot_type)
        
        # Determine terrain type
        terrain_type = "flat"
        if elevation:
            if elevation > 500:
                terrain_type = "mountainous"
            elif elevation > 100:
                terrain_type = "hilly"
        if spot_type == "beach":
            terrain_type = "coastal"
        
        # Weather info
        weather_safe = is_safe_weather(weather_data) if weather_data else True
        weather_info = None
        if weather_data:
            weather_description = []
            if weather_data.get("wind_speed_ms"):
                weather_description.append(f"Wind: {weather_data['wind_speed_ms']:.1f} m/s")
            if weather_data.get("temperature_c"):
                weather_description.append(f"Temp: {weather_data['temperature_c']:.1f}°C")
            if weather_data.get("weather_main"):
                weather_description.append(weather_data["weather_main"])
            
            weather_info = WeatherInfo(
                wind_speed_ms=weather_data.get("wind_speed_ms"),
                wind_deg=weather_data.get("wind_deg"),
                temperature_c=weather_data.get("temperature_c"),
                humidity=weather_data.get("humidity"),
                visibility_m=weather_data.get("visibility_m"),
                weather_main=weather_data.get("weather_main"),
                clouds=weather_data.get("clouds"),
                is_safe=weather_safe,
                weather_description=", ".join(weather_description) if weather_description else None
            )
        
        # Generate safe area polygon
        safe_area_polygon = generate_safe_area_polygon(place_lat, place_lon, safety_score)
        
        # Create spot info
        spot = SpotInfo(
            name=name,
            latitude=place_lat,
            longitude=place_lon,
            address=address_str,
            spot_type=spot_type,
            distance_km=round(distance, 2),
            car_accessible=car_accessible,
            car_accessibility=car_accessibility_data,
            elevation_m=round(elevation, 1) if elevation else None,
            safety_score=round(safety_score, 1),
            no_fly_zones_nearby=no_fly_zones,
            description=f"{spot_type.replace('_', ' ').title()} location suitable for drone flying",
            terrain_type=terrain_type,
            google_maps_url=f"https://www.google.com/maps?q={place_lat},{place_lon}",
            openstreetmap_url=f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}&zoom=15",
            weather=weather_info,
            safe_area_polygon=safe_area_polygon
        )
        
        return spot
    except Exception as e:
        logger.warning(f"Error processing place {idx}: {e}")
        return None


@app.get("/search", response_model=SearchResponse)
async def search_drone_spots(
    latitude: Optional[float] = Query(None, description="Latitude for 'near me' search"),
    longitude: Optional[float] = Query(None, description="Longitude for 'near me' search"),
    address: Optional[str] = Query(None, description="Address, POI, or location name"),
    state: Optional[str] = Query(None, description="Malaysian state name"),
    district: Optional[str] = Query(None, description="District name"),
    postal_code: Optional[str] = Query(None, description="Malaysian postal code (5 digits, e.g., '50000')"),
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    spot_types: Optional[str] = Query(None, description="Comma-separated spot types: open_field,beach,hill_mountain,scenic_town"),
    max_results: int = Query(20, description="Maximum number of results"),
    car_accessible_only: bool = Query(False, description="Filter to show only car-accessible spots")
):
    """
    Search for drone flying spots in Malaysia.
    
    You can search by:
    - Coordinates (latitude, longitude) for 'near me'
    - Address or POI name
    - State name
    - District name
    - Postal code (5 digits, e.g., '50000' for Kuala Lumpur)
    
    Returns spots with terrain analysis, safety scores, and no-fly zone information.
    """
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    endpoint_start = time.time()
    debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:entry", "Search endpoint started", {
        "address": address, "latitude": latitude, "longitude": longitude, "radius_km": radius_km, "max_results": max_results, "car_accessible_only": car_accessible_only
    })
    # #endregion
    
    try:
        # Parse spot types
        spot_types_list = None
        if spot_types:
            spot_types_list = [s.strip() for s in spot_types.split(",")]
        
        # #region agent log
        coord_start = time.time()
        debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:before_coords", "Before get_coordinates_from_query")
        # #endregion
        
        # Get coordinates from query
        query_lat, query_lon = await get_coordinates_from_query(
            lat=latitude,
            lon=longitude,
            address=address,
            state=state,
            district=district,
            postal_code=postal_code
        )
        
        # Validate coordinates are within Malaysia
        if not is_within_malaysia(query_lat, query_lon):
            raise ValidationError(
                f"Coordinates ({query_lat}, {query_lon}) are outside Malaysia. "
                "Please provide a location within Malaysia."
            )
        
        # #region agent log
        debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:after_coords", "After get_coordinates_from_query", {
            "elapsed": time.time() - coord_start, "query_lat": query_lat, "query_lon": query_lon
        })
        # #endregion
        
        # #region agent log
        places_start = time.time()
        debug_log(session_id, run_id, "D", "drone_spots_api.py:search_drone_spots:before_search_places", "Before search_places_nearby")
        # #endregion
        
        # Detect if query is a state-level search and increase radius accordingly
        malaysian_states = [
            "sarawak", "sabah", "johor", "kedah", "kelantan", "melaka", "malacca",
            "negeri sembilan", "pahang", "penang", "pulau pinang", "perak",
            "perlis", "selangor", "terengganu", "wilayah persekutuan",
            "kuala lumpur", "labuan", "putrajaya"
        ]
        
        query_lower = ""
        if address:
            query_lower = address.lower().strip()
        elif state:
            query_lower = state.lower().strip()
        
        is_state_query = query_lower in malaysian_states
        
        # Check if we're in East Malaysia and adjust radius if needed
        is_east_malaysia = is_in_east_malaysia(query_lat, query_lon)
        if is_east_malaysia and radius_km < 15:
            # For East Malaysia, use minimum 15km radius for better coverage
            radius_km = max(radius_km, 15.0)
            logger.info(f"East Malaysia detected - using minimum radius of {radius_km}km")
        
        # For state-level queries, use a much larger radius (50km minimum)
        if is_state_query:
            radius_km = max(radius_km, 50.0)
            logger.info(f"State-level query detected ({query_lower}) - using minimum radius of {radius_km}km")
        
        # Search for places
        places = await search_places_nearby(
            lat=query_lat,
            lon=query_lon,
            radius_km=radius_km,
            spot_types=spot_types_list
        )
        
        # #region agent log
        debug_log(session_id, run_id, "D", "drone_spots_api.py:search_drone_spots:after_search_places", "After search_places_nearby", {
            "elapsed": time.time() - places_start, "places_found": len(places), "processing_count": min(len(places), max_results)
        })
        # #endregion
        
        # Fetch no-fly zones once for the entire search area (optimization: avoid fetching per place)
        # Use a radius that covers all places: search radius + buffer for no-fly zone detection
        nofly_search_radius = max(radius_km, 50)  # At least 50km to catch nearby zones
        # #region agent log
        nofly_bulk_start = time.time()
        debug_log(session_id, run_id, "B", "drone_spots_api.py:search_drone_spots:before_bulk_nofly", "Fetching no-fly zones once for entire search area", {
            "query_lat": query_lat, "query_lon": query_lon, "search_radius": nofly_search_radius
        })
        # #endregion
        pre_fetched_no_fly_zones = await get_no_fly_zones_for_area(query_lat, query_lon, nofly_search_radius)
        # #region agent log
        debug_log(session_id, run_id, "B", "drone_spots_api.py:search_drone_spots:after_bulk_nofly", "Fetched no-fly zones for entire area", {
            "elapsed": time.time() - nofly_bulk_start, "airports": len(pre_fetched_no_fly_zones.airports),
            "military": len(pre_fetched_no_fly_zones.military_areas)
        })
        # #endregion
        
        # Process places into spots in parallel for better performance
        # Limit concurrent processing to avoid overwhelming APIs
        MAX_CONCURRENT_PLACES = 10
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PLACES)
        
        async def process_place_with_limit(place, idx):
            """Process a place with concurrency limit"""
            async with semaphore:
                return await process_single_place_parallel(
                    place, idx, query_lat, query_lon, radius_km,
                    pre_fetched_no_fly_zones, car_accessible_only, endpoint_start,
                    session_id, run_id
                )
        
        # Process all places in parallel
        processing_tasks = [
            process_place_with_limit(place, idx)
            for idx, place in enumerate(places[:max_results])
        ]
        
        # #region agent log
        processing_start = time.time()
        debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:before_parallel_processing", "Starting parallel processing", {
            "total_places": min(len(places), max_results), "max_concurrent": MAX_CONCURRENT_PLACES
        })
        # #endregion
        
        # Set overall timeout for processing all places (60 seconds max)
        try:
            spots_results = await asyncio.wait_for(
                asyncio.gather(*processing_tasks, return_exceptions=True),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout processing all places after 60 seconds")
            # Return partial results if any completed
            spots_results = []
        
        # #region agent log
        debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:after_parallel_processing", "Parallel processing complete", {
            "elapsed": time.time() - processing_start, "results_count": len(spots_results)
        })
        # #endregion
        
        # Filter out None results and exceptions
        spots = [
            spot for spot in spots_results 
            if spot is not None and not isinstance(spot, Exception)
        ]
        
        
        # Sort by combined relevance score (safety + accessibility + distance-based relevance)
        # Distance-based relevance: closer spots get higher priority
        for spot in spots:
            # Calculate distance-based relevance (closer = more relevant)
            # Max distance relevance is 100, decreases by 5 points per km
            distance_relevance = max(0, 100 - ((spot.distance_km or 0) * 5))
            # Store as a temporary attribute for sorting
            spot._distance_relevance = distance_relevance
        
        # Sort by: safety score (40%), distance relevance (30%), car accessibility (20%), distance (10%)
        spots.sort(key=lambda x: (
            -(x.safety_score * 4.0),  # Safety is most important
            -(x._distance_relevance * 0.3),  # Distance relevance (closer = better)
            -(x.car_accessibility.accessibility_score if x.car_accessibility else 0.0) * 2.0,  # Car accessibility
            x.distance_km or 0  # Final tie-breaker: actual distance
        ))
        
        # Clean up temporary attribute
        for spot in spots:
            if hasattr(spot, '_distance_relevance'):
                delattr(spot, '_distance_relevance')
        
        # #region agent log
        debug_log(session_id, run_id, "A", "drone_spots_api.py:search_drone_spots:endpoint_complete", "Search endpoint complete", {
            "total_spots": len(spots), "total_elapsed": time.time() - endpoint_start
        })
        # #endregion
        
        return SearchResponse(
            query_location=QueryLocation(
                postal_code=postal_code,
                latitude=query_lat,
                longitude=query_lon,
                address=address or f"{query_lat}, {query_lon}",
                state=state,
                district=district
            ),
            total_spots_found=len(spots),
            spots=spots,
            search_radius_km=radius_km
        )
    
    except (GeocodingError, ValidationError) as e:
        # Re-raise custom errors (they'll be handled by the global exception handler)
        raise
    except APIError as e:
        # Re-raise custom API errors
        raise
    except ValueError as e:
        logger.error(f"ValueError in search_drone_spots: {e}")
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in search_drone_spots: {e}", exc_info=True)
        raise APIError(f"An unexpected error occurred during search: {str(e)}", status_code=500)


@app.get("/no-fly-zones")
async def get_no_fly_zones(
    latitude: float = Query(..., description="Latitude to search around"),
    longitude: float = Query(..., description="Longitude to search around"),
    radius_km: float = Query(50.0, description="Search radius in kilometers")
):
    """Get list of no-fly zones near a location using real APIs"""
    try:
        no_fly_zones = await get_no_fly_zones_for_area(latitude, longitude, radius_km)
        return {
            "query_location": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km
            },
            "no_fly_zones": no_fly_zones.model_dump(),
            "total_airports": len(no_fly_zones.airports),
            "total_military_areas": len(no_fly_zones.military_areas),
            "note": "Data fetched from OpenStreetMap. Always check with local aviation authorities before flying."
        }
    except APIError as e:
        # Re-raise custom API errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_no_fly_zones: {e}", exc_info=True)
        raise APIError(f"Error fetching no-fly zones: {str(e)}", status_code=500)


@app.get("/spot-types")
async def get_spot_types():
    """Get available spot types and their descriptions"""
    return {
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


@app.get("/elevation-path")
async def get_elevation_path(
    start_latitude: float = Query(..., description="Starting latitude"),
    start_longitude: float = Query(..., description="Starting longitude"),
    end_latitude: float = Query(..., description="Ending latitude"),
    end_longitude: float = Query(..., description="Ending longitude"),
    flight_altitude_m: float = Query(50.0, description="Flight altitude in meters above ground level")
):
    """
    Analyze elevation along a flight path to detect obstacles.
    
    This endpoint checks if there are terrain obstacles along a planned flight path
    by sampling elevation data at multiple points between start and end coordinates.
    """
    try:
        path_analysis = check_elevation_path(
            start_lat=start_latitude,
            start_lon=start_longitude,
            end_lat=end_latitude,
            end_lon=end_longitude,
            flight_altitude_m=flight_altitude_m
        )
        
        return {
            "start_location": {
                "latitude": start_latitude,
                "longitude": start_longitude
            },
            "end_location": {
                "latitude": end_latitude,
                "longitude": end_longitude
            },
            "path_analysis": path_analysis
        }
    except APIError as e:
        # Re-raise custom API errors
        raise
    except Exception as e:
        logger.error(f"Error in get_elevation_path: {e}", exc_info=True)
        raise APIError(f"Error analyzing elevation path: {str(e)}", status_code=500)


if __name__ == "__main__":
    # #region agent log
    debug_log("debug-session", "startup", "A", "drone_spots_api.py:main:entry", "Main entry point reached", {})
    # #endregion
    
    try:
        import uvicorn
        import sys
        # #region agent log
        debug_log("debug-session", "startup", "A", "drone_spots_api.py:main:before_uvicorn", "Before uvicorn.run", {
            "host": "0.0.0.0", 
            "port": 8000,
            "workers": settings.workers,
            "max_connections": settings.max_connections,
            "max_keepalive": settings.max_keepalive_connections
        })
        # #endregion
        
        # Note: Workers are not supported on Windows. Use workers > 1 only on Linux/macOS.
        # For Windows, use a reverse proxy (nginx) or run multiple processes manually.
        # For production on Linux, workers should be set to (2 * CPU cores) + 1
        if settings.workers > 1 and sys.platform == "win32":
            logger.warning(f"Multiple workers ({settings.workers}) not supported on Windows. Using 1 worker. For better performance on Windows, use WSL or deploy on Linux.")
            workers = 1
        else:
            workers = settings.workers
        
        # When using multiple workers, uvicorn requires the app as an import string
        # When using a single worker, we can pass the app object directly
        if workers > 1:
            # Use import string format for multiple workers
            uvicorn.run(
                "drone_spots_api:app",  # Import string format
                host="0.0.0.0", 
                port=8000,
                workers=workers,
                log_level="info"
            )
        else:
            # Single worker mode - can use app object directly
            uvicorn.run(
                app,  # App object
                host="0.0.0.0", 
                port=8000,
                log_level="info"
            )
    except Exception as e:
        # #region agent log
        debug_log("debug-session", "startup", "A", "drone_spots_api.py:main:error", "Error starting server", {"error": str(e), "error_type": type(e).__name__})
        # #endregion
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise

