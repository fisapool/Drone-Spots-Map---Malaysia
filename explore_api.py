#!/usr/bin/env python3
"""
Comprehensive API exploration script for the Drone Spots API.
Tests all endpoints and displays their responses in a readable format.
"""

import requests
import json
import socket
import sys
from typing import Dict, Any

def get_network_ip():
    """Get the local network IP address for accessing from other devices"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

# Auto-detect network IP or use localhost
# Set USE_NETWORK_IP=True to use network IP (accessible from other devices)
USE_NETWORK_IP = False  # Change to True to use network IP

# Default port - change if your API runs on a different port
API_PORT = 8001  # Your API is running on port 8001 (gunicorn with 25 workers)

if USE_NETWORK_IP:
    network_ip = get_network_ip()
    if network_ip:
        BASE_URL = f"http://{network_ip}:{API_PORT}"
        print(f"🌐 Using network IP: {BASE_URL} (accessible from other devices)")
    else:
        BASE_URL = f"http://localhost:{API_PORT}"
        print("⚠️  Could not detect network IP, using localhost")
else:
    BASE_URL = f"http://localhost:{API_PORT}"  # Update API_PORT if your API runs on a different port

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")

def pretty_print_json(data: Dict[Any, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))

def test_endpoint(method: str, endpoint: str, params: Dict = None, description: str = None):
    """Test an API endpoint and display results"""
    url = f"{BASE_URL}{endpoint}"
    
    if description:
        print_subsection(description)
    
    print(f"Request: {method} {url}")
    if params:
        print(f"Parameters: {params}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=params, timeout=30)
        else:
            print(f"⚠️  Unsupported method: {method}")
            return None
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("Response:")
                pretty_print_json(data, indent=2)
                return data
            except json.JSONDecodeError:
                print(f"Response (non-JSON):\n{response.text[:500]}")
                return response.text
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                pretty_print_json(error_data, indent=2)
            except:
                print(response.text[:500])
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not connect to {BASE_URL}")
        print("   Make sure the API server is running!")
        return None
    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout: Request took longer than 30 seconds")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def explore_root():
    """Explore the root endpoint"""
    print_section("1. ROOT ENDPOINT")
    return test_endpoint("GET", "/", description="API Root - Service Information")

def explore_spot_types():
    """Explore the spot-types endpoint"""
    print_section("2. SPOT TYPES ENDPOINT")
    return test_endpoint("GET", "/spot-types", description="Get Available Spot Types")

def explore_no_fly_zones():
    """Explore the no-fly-zones endpoint"""
    print_section("3. NO-FLY ZONES ENDPOINT")
    
    # Test with Bujang Valley coordinates
    params = {
        "latitude": 5.737,
        "longitude": 100.417,
        "radius_km": 50
    }
    return test_endpoint("GET", "/no-fly-zones", params=params, 
                        description="Check NFZ Proximity (Bujang Valley area)")

def explore_search_basic():
    """Explore basic search functionality"""
    print_section("4. SEARCH ENDPOINT - Basic Examples")
    
    # Example 1: Search by address (POI)
    test_endpoint("GET", "/search", 
                 params={"address": "Bujang Valley Archaeological Museum", "radius_km": 5, "max_results": 5},
                 description="Example 1: Search by Address (POI)")
    
    # Example 2: Search by coordinates
    test_endpoint("GET", "/search",
                 params={"latitude": 5.737, "longitude": 100.417, "radius_km": 10, "max_results": 5},
                 description="Example 2: Search by Coordinates")
    
    # Example 3: Search by state/district
    test_endpoint("GET", "/search",
                 params={"state": "Kedah", "district": "Kuala Muda", "radius_km": 20, "max_results": 5},
                 description="Example 3: Search by State/District")

def explore_search_advanced():
    """Explore advanced search features"""
    print_section("5. SEARCH ENDPOINT - Advanced Features")
    
    # Filter by spot types and car accessible
    test_endpoint("GET", "/search",
                 params={
                     "latitude": 5.737,
                     "longitude": 100.417,
                     "radius_km": 10,
                     "spot_types": "open_field,beach",
                     "car_accessible_only": True,
                     "max_results": 5
                 },
                 description="Filter by Spot Types & Car Accessible Only")
    
    # Car accessible only
    test_endpoint("GET", "/search",
                 params={
                     "address": "Bujang Valley Archaeological Museum",
                     "radius_km": 10,
                     "car_accessible_only": True,
                     "max_results": 5
                 },
                 description="Car Accessible Only Filter")

def explore_elevation_path():
    """Explore elevation path analysis"""
    print_section("6. ELEVATION PATH ENDPOINT")
    
    # Analyze a path near Bujang Valley
    params = {
        "start_latitude": 5.73,
        "start_longitude": 100.41,
        "end_latitude": 5.735,
        "end_longitude": 100.42,
        "flight_altitude_m": 50
    }
    return test_endpoint("GET", "/elevation-path", params=params,
                        description="Elevation Path Analysis (Check for Obstacles)")

def explore_map_endpoint():
    """Explore the map endpoint"""
    print_section("7. MAP ENDPOINT")
    print_subsection("Interactive Map (HTML Response)")
    print(f"Request: GET {BASE_URL}/map")
    print("\nThe /map endpoint serves an interactive HTML page.")
    print(f"Open in browser: {BASE_URL}/map")
    
    try:
        response = requests.get(f"{BASE_URL}/map", timeout=10)
        if response.status_code == 200:
            print(f"✅ Map page is available ({len(response.text)} bytes)")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        else:
            print(f"⚠️  Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def explore_docs():
    """Explore API documentation"""
    print_section("8. API DOCUMENTATION")
    print(f"Swagger UI: {BASE_URL}/docs")
    print(f"ReDoc: {BASE_URL}/redoc")
    print("\nThese endpoints provide interactive API documentation.")

def generate_curl_examples():
    """Generate curl examples for all endpoints"""
    print_section("9. CURL EXAMPLES")
    
    examples = [
        ("Root Endpoint", f'curl "{BASE_URL}/"'),
        ("Spot Types", f'curl "{BASE_URL}/spot-types"'),
        ("No-Fly Zones", f'curl "{BASE_URL}/no-fly-zones?latitude=5.737&longitude=100.417&radius_km=50"'),
        ("Search by Address (POI)", f'curl "{BASE_URL}/search?address=Bujang%20Valley%20Archaeological%20Museum&radius_km=5&max_results=5"'),
        ("Search by Coordinates", f'curl "{BASE_URL}/search?latitude=5.737&longitude=100.417&radius_km=10"'),
        ("Search by State/District", f'curl "{BASE_URL}/search?state=Kedah&district=Kuala%20Muda&radius_km=20"'),
        ("Filter by Spot Types & Car Accessible", f'curl "{BASE_URL}/search?latitude=5.737&longitude=100.417&radius_km=10&spot_types=open_field,beach&car_accessible_only=true"'),
        ("Car Accessible Only", f'curl "{BASE_URL}/search?address=Bujang%20Valley%20Archaeological%20Museum&car_accessible_only=true&radius_km=10"'),
        ("Elevation Path", f'curl "{BASE_URL}/elevation-path?start_latitude=5.73&start_longitude=100.41&end_latitude=5.735&end_longitude=100.42&flight_altitude_m=50"'),
    ]
    
    for description, command in examples:
        print(f"\n{description}:")
        print(f"  {command}")

def main():
    """Main exploration function"""
    print("\n" + "=" * 80)
    print("  DRONE SPOTS API - COMPREHENSIVE EXPLORATION")
    print("=" * 80)
    print(f"\nAPI Base URL: {BASE_URL}")
    
    # Show network access info
    network_ip = get_network_ip()
    if network_ip and BASE_URL.startswith("http://localhost"):
        print(f"\n💡 Network Access:")
        print(f"   To access from other devices, use: http://{network_ip}:{API_PORT}")
        print(f"   (Set USE_NETWORK_IP=True in this script to use network IP)")
    
    print(f"\nTesting all available endpoints...\n")
    
    # Test connectivity first
    root_data = explore_root()
    if not root_data:
        print("\n❌ Cannot connect to API server. Please check:")
        print(f"   1. Is the server running? (python drone_spots_api.py)")
        print(f"   2. Is the base URL correct? (currently: {BASE_URL})")
        print(f"   3. Is there a firewall blocking the connection?")
        return
    
    # Explore all endpoints
    explore_spot_types()
    explore_no_fly_zones()
    explore_search_basic()
    explore_search_advanced()
    explore_elevation_path()
    explore_map_endpoint()
    explore_docs()
    generate_curl_examples()
    
    print_section("EXPLORATION COMPLETE")
    print("\n✅ All endpoints explored!")
    print(f"\n💡 Tips:")
    print(f"   - View interactive docs at: {BASE_URL}/docs")
    print(f"   - View map visualization at: {BASE_URL}/map")
    print(f"   - Check README_API.md for detailed documentation")
    print("\n")

if __name__ == "__main__":
    main()

