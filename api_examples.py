#!/usr/bin/env python3
"""
Example usage of the Drone Spots API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def example_search_near_me():
    """Search for spots near Sungai Seluang, Kedah"""
    print("=" * 80)
    print("Example 1: Search near Sungai Seluang, Kedah")
    print("=" * 80)
    
    params = {
        "address": "Sungai Seluang, Kedah",
        "radius_km": 15,
        "max_results": 10
    }
    
    response = requests.get(f"{BASE_URL}/search", params=params)
    data = response.json()
    
    print(f"\nQuery Location: {data['query_location']['address']}")
    print(f"Total Spots Found: {data['total_spots_found']}\n")
    
    for i, spot in enumerate(data['spots'][:5], 1):
        print(f"{i}. {spot['name']}")
        print(f"   Type: {spot['spot_type']}")
        print(f"   Distance: {spot['distance_km']} km")
        print(f"   Safety Score: {spot['safety_score']}/10")
        print(f"   Car Accessible: {'Yes' if spot['car_accessible'] else 'No'}")
        if spot['elevation_m']:
            print(f"   Elevation: {spot['elevation_m']} m")
        if spot['no_fly_zones_nearby']:
            print(f"   ⚠️  No-fly zones: {', '.join(spot['no_fly_zones_nearby'])}")
        print(f"   Maps: {spot['google_maps_url']}")
        print()


def example_search_by_state():
    """Search for spots in Kedah state"""
    print("=" * 80)
    print("Example 2: Search in Kedah State")
    print("=" * 80)
    
    params = {
        "state": "Kedah",
        "spot_types": "beach,hill_mountain",
        "radius_km": 20,
        "max_results": 10
    }
    
    response = requests.get(f"{BASE_URL}/search", params=params)
    data = response.json()
    
    print(f"\nQuery Location: {data['query_location']['address']}")
    print(f"Total Spots Found: {data['total_spots_found']}\n")
    
    for i, spot in enumerate(data['spots'][:5], 1):
        print(f"{i}. {spot['name']}")
        print(f"   Type: {spot['spot_type']}")
        print(f"   Distance: {spot['distance_km']} km")
        print(f"   Safety Score: {spot['safety_score']}/10")
        print()


def example_search_near_poi():
    """Search near a specific POI (Gunung Jerai)"""
    print("=" * 80)
    print("Example 3: Search near Gunung Jerai")
    print("=" * 80)
    
    params = {
        "address": "Gunung Jerai",
        "radius_km": 10,
        "spot_types": "hill_mountain,open_field",
        "max_results": 10
    }
    
    response = requests.get(f"{BASE_URL}/search", params=params)
    data = response.json()
    
    print(f"\nQuery Location: {data['query_location']['address']}")
    print(f"Total Spots Found: {data['total_spots_found']}\n")
    
    for i, spot in enumerate(data['spots'][:5], 1):
        print(f"{i}. {spot['name']}")
        print(f"   Type: {spot['spot_type']}")
        print(f"   Elevation: {spot['elevation_m']} m" if spot['elevation_m'] else "   Elevation: N/A")
        print(f"   Safety Score: {spot['safety_score']}/10")
        print()


def example_search_by_coordinates():
    """Search using coordinates (near Alor Setar)"""
    print("=" * 80)
    print("Example 4: Search using coordinates (Alor Setar area)")
    print("=" * 80)
    
    # Alor Setar coordinates
    params = {
        "latitude": 6.1164,
        "longitude": 100.3681,
        "radius_km": 15,
        "max_results": 10
    }
    
    response = requests.get(f"{BASE_URL}/search", params=params)
    data = response.json()
    
    print(f"\nQuery Location: {data['query_location']['address']}")
    print(f"Total Spots Found: {data['total_spots_found']}\n")
    
    for i, spot in enumerate(data['spots'][:5], 1):
        print(f"{i}. {spot['name']}")
        print(f"   Coordinates: {spot['latitude']}, {spot['longitude']}")
        print(f"   Type: {spot['spot_type']}")
        print(f"   Distance: {spot['distance_km']} km")
        print(f"   Safety Score: {spot['safety_score']}/10")
        print()


def example_get_no_fly_zones():
    """Get list of no-fly zones using real APIs"""
    print("=" * 80)
    print("Example 5: Get No-Fly Zones (Real-time from OpenStreetMap)")
    print("=" * 80)
    
    # Get no-fly zones near Alor Setar, Kedah
    params = {
        "latitude": 6.1164,
        "longitude": 100.3681,
        "radius_km": 50
    }
    
    response = requests.get(f"{BASE_URL}/no-fly-zones", params=params)
    data = response.json()
    
    print(f"\nQuery Location: {data['query_location']['latitude']}, {data['query_location']['longitude']}")
    print(f"Search Radius: {data['query_location']['radius_km']} km")
    print(f"\nTotal Airports Found: {data['total_airports']}")
    print(f"Total Military Areas Found: {data['total_military_areas']}")
    
    print("\nAirports (5km no-fly zone):")
    for airport in data['no_fly_zones']['airports'][:10]:  # Show first 10
        print(f"  - {airport['name']}: {airport['lat']:.4f}, {airport['lon']:.4f}")
    
    print("\nMilitary Areas (3km no-fly zone):")
    for military in data['no_fly_zones']['military_areas'][:10]:  # Show first 10
        print(f"  - {military['name']}: {military['lat']:.4f}, {military['lon']:.4f}")
    
    print(f"\nNote: {data['note']}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DRONE SPOTS API - USAGE EXAMPLES")
    print("=" * 80)
    print("\nMake sure the API server is running: python drone_spots_api.py")
    print("=" * 80 + "\n")
    
    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/")
        print("✓ API server is running\n")
        
        example_search_near_me()
        print("\n")
        
        example_search_by_state()
        print("\n")
        
        example_search_near_poi()
        print("\n")
        
        example_search_by_coordinates()
        print("\n")
        
        example_get_no_fly_zones()
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API server.")
        print("Please start the server first: python drone_spots_api.py")
    except Exception as e:
        print(f"❌ Error: {e}")

