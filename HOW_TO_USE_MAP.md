# How to Parse and Use Data with the Map

## Quick Methods

### Method 1: Direct Browser Access (Easiest)

1. **Open the map in your browser:**
   ```
   http://192.168.0.145:8001/map
   ```
   (Or `http://localhost:8001/map` from the same machine)

2. **Get JSON data from API:**
   - Use the search box in the map interface, OR
   - Copy JSON from API response and paste it

3. **Paste JSON in the textarea:**
   - Find the "Load JSON Data" section
   - Paste your JSON response
   - Click "Load & Display Spots"

### Method 2: Using the Helper Script (Automated)

```bash
# Search by address and auto-open map
python3 view_spots_on_map.py "Kuala Lumpur"

# Search by coordinates
python3 view_spots_on_map.py --lat 5.737 --lon 100.417

# Load from saved JSON file
python3 view_spots_on_map.py --file response.json

# With custom radius
python3 view_spots_on_map.py "Kuala Lumpur" --radius 20
```

### Method 3: Fetch JSON and Paste Manually

```bash
# Get JSON from API
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&radius_km=10" > spots.json

# Open the map
# Then copy the contents of spots.json and paste into the map's textarea
```

## JSON Format Required

The map expects JSON in this format:

```json
{
  "query_location": {
    "latitude": 3.1526,
    "longitude": 101.7022,
    "address": "Kuala Lumpur"
  },
  "total_spots_found": 5,
  "spots": [
    {
      "name": "Location Name",
      "latitude": 3.1092,
      "longitude": 101.7288,
      "safety_score": 10.0,
      "car_accessible": true,
      "spot_type": "open_field",
      "distance_km": 5.63,
      "no_fly_zones_nearby": []
    }
  ],
  "search_radius_km": 10.0
}
```

## Step-by-Step: Parse JSON in Map

### Step 1: Get JSON Data

**Option A: From API Response**
```bash
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur" | python3 -m json.tool
```

**Option B: From explore_api.py**
```bash
python3 explore_api.py
# Copy the JSON output from the search endpoint
```

**Option C: Use the map's built-in search**
- Open the map
- Use the search box at the top
- Enter address and click "Search"
- Data loads automatically!

### Step 2: Parse in Map

1. **Open map**: `http://192.168.0.145:8001/map`

2. **Find the textarea** labeled "Load JSON Data"

3. **Paste your JSON** (the entire API response)

4. **Click "Load & Display Spots"**

5. **The map will:**
   - Parse the JSON
   - Extract spots array
   - Display markers on the map
   - Show spots in the sidebar

## Python Script to Parse and Display

```python
import requests
import json
import webbrowser
from pathlib import Path

# Fetch data from API
response = requests.get("http://192.168.0.145:8001/search", params={
    "address": "Kuala Lumpur",
    "radius_km": 10
})

data = response.json()

# Save to file
with open("spots.json", "w") as f:
    json.dump(data, f, indent=2)

# Open map (will use sample data, but you can paste the JSON)
map_url = "http://192.168.0.145:8001/map"
webbrowser.open(map_url)

print("Map opened! Paste this JSON into the textarea:")
print(json.dumps(data, indent=2))
```

## Using view_spots_on_map.py (Recommended)

This script automatically fetches data and opens the map:

```bash
# Install dependencies if needed
pip install requests

# Run the script
python3 view_spots_on_map.py "Kuala Lumpur"

# The script will:
# 1. Fetch data from API
# 2. Parse the JSON
# 3. Inject it into the map HTML
# 4. Open the map in your browser
# 5. Display all spots automatically
```

## Map Features After Parsing

Once JSON is parsed and loaded:

- **3D Markers**: Each spot appears as a marker on the globe
- **Color Coding**: 
  - Green = High safety (8-10)
  - Yellow = Medium safety (5-7)
  - Red = Low safety (<5)
- **Click Markers**: See detailed information popup
- **Sidebar List**: All spots listed with details
- **Filter**: Filter spots by safety score or type
- **Links**: Direct links to Google Maps and OpenStreetMap

## Troubleshooting

### "Invalid JSON" Error

- Make sure you copied the **entire** API response
- Remove any terminal prompts or extra text
- Validate JSON at https://jsonlint.com
- The JSON should start with `{` and end with `}`

### "Data does not contain a 'spots' array"

- You need the full API response, not just part of it
- Make sure `spots` is an array: `"spots": [...]`
- Check that `query_location` is also included

### Map Shows But No Markers

- Check browser console (F12) for errors
- Verify coordinates are valid numbers
- Make sure spots array is not empty
- Try refreshing the page

## Quick Example

```bash
# 1. Get JSON
curl "http://192.168.0.145:8001/search?address=Kuala%20Lumpur&radius_km=10&max_results=5" > response.json

# 2. Open map
# Navigate to: http://192.168.0.145:8001/map

# 3. Copy JSON content
cat response.json

# 4. Paste into map's textarea and click "Load & Display Spots"
```

Or use the automated script:
```bash
python3 view_spots_on_map.py "Kuala Lumpur" --radius 10
```

## Access from Other Devices

The map is accessible from any device on your network:

1. **Find your server IP:**
   ```bash
   python3 get_network_ip.py
   ```

2. **Open on another device:**
   ```
   http://192.168.0.145:8001/map
   ```

3. **Parse JSON the same way:**
   - Paste JSON in textarea
   - Or use the built-in search box
   - Click "Load & Display Spots"

The map will parse and display the data on any device!


