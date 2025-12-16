#!/usr/bin/env python3
"""
Simple script to parse JSON data and display it on the map.
Shows different ways to get and parse data for the map.
"""

import requests
import json
import webbrowser
from pathlib import Path

# API base URL - change if your API is on a different port
API_URL = "http://192.168.0.145:8001"

def parse_json_from_api(address="Kuala Lumpur", radius_km=10):
    """Fetch and parse JSON from API"""
    print(f"🔍 Fetching spots near '{address}'...")
    
    response = requests.get(f"{API_URL}/search", params={
        "address": address,
        "radius_km": radius_km,
        "max_results": 5
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data.get('total_spots_found', 0)} spots")
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        return None

def parse_json_from_file(filepath):
    """Parse JSON from a file"""
    print(f"📄 Reading JSON from {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Parsed {len(data.get('spots', []))} spots from file")
    return data

def parse_json_from_string(json_string):
    """Parse JSON from a string"""
    print("📝 Parsing JSON string...")
    
    try:
        data = json.loads(json_string)
        print(f"✅ Parsed {len(data.get('spots', []))} spots from string")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None

def display_on_map(data):
    """Open map and display the data"""
    if not data or 'spots' not in data:
        print("❌ Invalid data: missing 'spots' array")
        return
    
    # Save to temporary file
    temp_file = Path("map_data_temp.json")
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n📊 Data Summary:")
    print(f"   Query Location: {data.get('query_location', {}).get('address', 'Unknown')}")
    print(f"   Total Spots: {len(data.get('spots', []))}")
    print(f"   Search Radius: {data.get('search_radius_km', 0)} km")
    
    # Open map
    map_url = f"{API_URL}/map"
    print(f"\n🌐 Opening map: {map_url}")
    webbrowser.open(map_url)
    
    print(f"\n📋 Instructions:")
    print(f"   1. The map should open in your browser")
    print(f"   2. Find the 'Load JSON Data' textarea")
    print(f"   3. Copy and paste the JSON below:")
    print(f"\n{'='*60}")
    print(json.dumps(data, indent=2))
    print(f"{'='*60}")
    print(f"\n   4. Click 'Load & Display Spots'")
    print(f"\n💡 Tip: Or use view_spots_on_map.py for automatic loading!")

def main():
    """Main function with examples"""
    import sys
    
    print("="*60)
    print("  Map Data Parser - Drone Spots API")
    print("="*60)
    print()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file" and len(sys.argv) > 2:
            # Parse from file
            data = parse_json_from_file(sys.argv[2])
        elif sys.argv[1] == "--address" and len(sys.argv) > 2:
            # Parse from API
            address = sys.argv[2]
            radius = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--radius" else 10.0
            data = parse_json_from_api(address, radius)
        else:
            # Treat as address
            data = parse_json_from_api(sys.argv[1])
    else:
        # Default: fetch from API
        print("No arguments provided. Fetching sample data...")
        data = parse_json_from_api("Kuala Lumpur", 10)
    
    if data:
        display_on_map(data)
    else:
        print("\n❌ Failed to parse data. Please check:")
        print("   1. API is running")
        print("   2. JSON format is correct")
        print("   3. File exists (if using --file)")

if __name__ == "__main__":
    main()


