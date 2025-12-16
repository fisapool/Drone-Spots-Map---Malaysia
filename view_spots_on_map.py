#!/usr/bin/env python3
"""
Helper script to view drone spots on an interactive map.
Fetches data from the API and opens it in a browser.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import webbrowser
import sys
import os
from pathlib import Path
import time

# Get API URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
# Use Linux-compatible log path
LOG_PATH = os.getenv("LOG_PATH", "/tmp/drone_spots_debug.log")

# Create a session with retry strategy
def create_session_with_retries():
    """Create a requests session with retry logic"""
    session = requests.Session()
    
    # Retry strategy: exponential backoff
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Wait 1s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["GET", "POST"]  # Only retry safe methods
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Global session for connection pooling
_api_session = None

def get_api_session():
    """Get or create API session with retry logic"""
    global _api_session
    if _api_session is None:
        _api_session = create_session_with_retries()
    return _api_session

def check_api_health(timeout=5):
    """Check if API is healthy and responding"""
    try:
        health_url = f"{API_BASE_URL}/"
        response = requests.get(health_url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

def debug_log(session_id, run_id, hypothesis_id, location, message, data=None):
    """Write debug log entry"""
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

def fetch_spots(address=None, latitude=None, longitude=None, radius_km=15.0, max_retries=3):
    """Fetch drone spots from the API with retry logic"""
    # #region agent log
    session_id = "debug-session"
    run_id = "post-fix"
    debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:entry", "Fetch spots started", {
        "address": address, "latitude": latitude, "longitude": longitude, "radius_km": radius_km
    })
    # #endregion
    
    url = f"{API_BASE_URL}/search"
    params = {"radius_km": radius_km}
    
    if address:
        params["address"] = address
    elif latitude and longitude:
        params["latitude"] = latitude
        params["longitude"] = longitude
    else:
        print("Error: Please provide either an address or latitude/longitude")
        return None
    
    # Check API health first
    print("🔍 Checking API health...")
    if not check_api_health():
        print(f"⚠️  API at {API_BASE_URL} is not responding")
        print("   Attempting to connect anyway (API might be starting up)...")
    else:
        print("✅ API is healthy")
    
    # #region agent log
    start_time = time.time()
    debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:before_request", "Before API request", {
        "url": url, "params": params, "timeout": 90
    })
    # #endregion
    
    # Get session with retry logic
    session = get_api_session()
    
    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                print(f"⏳ Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            
            print(f"📡 Fetching spots from API... (attempt {attempt + 1}/{max_retries})")
            
            # Increased timeout to accommodate: geocoding (~6s) + place search (~15s) + no-fly zones (~3s) + place processing (~40s for 20 places) = ~64s
            # Using 90s to provide comfortable buffer for network variability and slower external APIs
            response = session.get(url, params=params, timeout=90)
            
            # #region agent log
            elapsed = time.time() - start_time
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:after_request", "After API request", {
                "elapsed_seconds": elapsed, "status_code": response.status_code, "attempt": attempt + 1
            })
            # #endregion
            
            response.raise_for_status()
            data = response.json()
            
            # #region agent log
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:success", "Request successful", {
                "total_spots": data.get('total_spots_found', 0), "total_time": time.time() - start_time, "attempt": attempt + 1
            })
            # #endregion
            
            print(f"✅ Found {data.get('total_spots_found', 0)} spots!")
            return data
            
        except requests.exceptions.ConnectionError as e:
            # #region agent log
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:connection_error", "Connection error", {
                "elapsed": time.time() - start_time, "attempt": attempt + 1, "error": str(e)
            })
            # #endregion
            
            if attempt == max_retries - 1:
                print(f"❌ Error: Could not connect to API at {API_BASE_URL}")
                print("   The API might not be running or is unreachable.")
                print("   To start the API:")
                print("   - Run: python3 drone_spots_api.py")
                print("   - Or: ./start_api_ubuntu.sh")
                print("   - Or check systemd: sudo systemctl status drone-spots-api")
                return None
            continue
            
        except requests.exceptions.Timeout as e:
            # #region agent log
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:timeout_error", "Timeout error", {
                "elapsed": time.time() - start_time, "attempt": attempt + 1, "error": str(e)
            })
            # #endregion
            
            if attempt == max_retries - 1:
                print(f"❌ Error: Request timed out after 90 seconds")
                print("   The API might be processing a large query. Try:")
                print("   - Reducing the search radius")
                print("   - Checking API logs for errors")
                return None
            continue
            
        except requests.exceptions.HTTPError as e:
            # #region agent log
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:http_error", "HTTP error", {
                "elapsed": time.time() - start_time, "attempt": attempt + 1, "status_code": e.response.status_code if hasattr(e, 'response') else None, "error": str(e)
            })
            # #endregion
            
            if e.response.status_code in [429, 500, 502, 503, 504]:
                # Retry on these status codes
                if attempt == max_retries - 1:
                    print(f"❌ Error: API returned status {e.response.status_code}")
                    print("   The API might be overloaded. Please try again later.")
                    return None
                continue
            else:
                # Don't retry on other HTTP errors
                print(f"❌ Error: API returned status {e.response.status_code}: {e}")
                return None
                
        except requests.exceptions.RequestException as e:
            # #region agent log
            debug_log(session_id, run_id, "E", "view_spots_on_map.py:fetch_spots:request_error", "Request exception", {
                "error_type": type(e).__name__, "error_msg": str(e), "elapsed": time.time() - start_time, "attempt": attempt + 1
            })
            # #endregion
            
            if attempt == max_retries - 1:
                print(f"❌ Error fetching data: {e}")
                return None
            continue
    
    return None

def load_json_file(filepath):
    """Load JSON data from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {data.get('total_spots_found', 0)} spots from {filepath}")
        return data
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return None

def open_map_with_data(data):
    """Open the map HTML file and inject the data"""
    # Try to use the improved temp version first, fallback to regular version
    map_file = Path(__file__).parent / "map_spots_temp.html"
    if not map_file.exists():
        map_file = Path(__file__).parent / "map_spots.html"
    
    if not map_file.exists():
        print(f"Error: map_spots.html or map_spots_temp.html not found")
        return
    
    # Read the HTML file
    with open(map_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace the sample data with actual data
    json_data = json.dumps(data, indent=2)
    
    # Find and replace the sampleData assignment
    import re
    # Match the entire sampleData constant definition (multiline)
    # Updated pattern to handle more flexible whitespace
    pattern = r'const sampleData\s*=\s*\{[\s\S]*?\};'
    # Convert Python dict to JavaScript object (JSON is valid JS)
    replacement = f'const sampleData = {json_data};'
    
    html_content = re.sub(pattern, replacement, html_content)
    
    # Write to a temporary file (always use temp version for consistency)
    temp_file = Path(__file__).parent / "map_spots_temp.html"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Open in browser
    file_url = f"file://{temp_file.absolute()}"
    print(f"Opening map in browser: {file_url}")
    webbrowser.open(file_url)
    
    print("\n✓ Map opened! The data has been loaded automatically.")
    print("  The map will display all spots when it finishes loading.")
    print("  You can close this script - the map will continue to work in your browser.")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 view_spots_on_map.py <address> [--radius <km>]")
        print("  python3 view_spots_on_map.py --lat <latitude> --lon <longitude> [--radius <km>]")
        print("  python3 view_spots_on_map.py --file <json_file>")
        print("  ./view_spots_on_map.py <address> [--radius <km>]  # If executable")
        print("\nExamples:")
        print("  python3 view_spots_on_map.py 'Bujang Valley Archaeological Museum'")
        print("  python3 view_spots_on_map.py 'Kuala Lumpur' --radius 20")
        print("  python3 view_spots_on_map.py --lat 5.737 --lon 100.417 --radius 15")
        print("  python3 view_spots_on_map.py --file response.json")
        sys.exit(1)
    
    data = None
    
    if sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("Error: --file requires a file path")
            sys.exit(1)
        filepath = sys.argv[2]
        data = load_json_file(filepath)
    elif sys.argv[1] == "--lat" and len(sys.argv) >= 4:
        lat = float(sys.argv[2])
        lon = float(sys.argv[3])
        radius = float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[4] == "--radius" else 15.0
        data = fetch_spots(latitude=lat, longitude=lon, radius_km=radius)
    else:
        # Treat as address
        # Extract radius if present, and remove it from address parts
        radius = 15.0
        address_parts = []
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--radius":
                if i + 1 < len(sys.argv):
                    try:
                        radius = float(sys.argv[i + 1])
                        i += 2  # Skip both --radius and its value
                        continue
                    except ValueError:
                        print(f"Error: Invalid radius value: {sys.argv[i + 1]}")
                        sys.exit(1)
                else:
                    print("Error: --radius requires a value")
                    sys.exit(1)
            else:
                address_parts.append(sys.argv[i])
                i += 1
        
        address = " ".join(address_parts)
        if not address:
            print("Error: Please provide an address")
            sys.exit(1)
        
        data = fetch_spots(address=address, radius_km=radius)
    
    if data:
        open_map_with_data(data)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

