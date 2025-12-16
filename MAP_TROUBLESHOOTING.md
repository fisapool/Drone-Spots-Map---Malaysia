# Map Troubleshooting Guide

## Common Issues and Solutions

### Issue: Map doesn't show after parsing JSON

**Symptoms:**
- JSON parses successfully but no markers appear on map
- Map loads but stays blank
- No error messages shown

**Solutions:**

1. **Check Browser Console**
   - Open browser Developer Tools (F12)
   - Check the Console tab for JavaScript errors
   - Look for errors related to Cesium or JSON parsing

2. **Verify JSON Structure**
   The JSON must have this structure:
   ```json
   {
     "query_location": {
       "latitude": 3.1526,
       "longitude": 101.7022,
       "address": "Kuala Lumpur"
     },
     "spots": [
       {
         "name": "Location Name",
         "latitude": 3.1092,
         "longitude": 101.7288,
         "safety_score": 10.0,
         ...
       }
     ]
   }
   ```

3. **Check if Cesium Library Loads**
   - The map requires Cesium library from CDN
   - Check browser console for network errors
   - Ensure internet connection is active
   - Try refreshing the page

4. **Verify Data Format**
   - Make sure you're pasting the **entire** API response
   - Don't paste just the `spots` array - include `query_location` too
   - Check that `spots` is an array (starts with `[`)

5. **Test with Sample Data**
   - Leave the textarea empty and click "Load & Display Spots"
   - If sample data works, the issue is with your JSON format
   - If sample data doesn't work, there's a map initialization issue

### Issue: "Invalid JSON" Error

**Solutions:**
- Copy the JSON directly from API response (don't modify it)
- Remove any extra text before/after the JSON
- Validate JSON at https://jsonlint.com
- Make sure all quotes are properly escaped

### Issue: "Data does not contain a 'spots' array" Error

**Solutions:**
- You might have copied only part of the API response
- Make sure you copy the **entire** response including:
  - `query_location`
  - `spots` array
  - `total_spots_found`
  - `search_radius_km`

### Issue: Map shows but no markers

**Solutions:**
- Check browser console for errors
- Verify spots array is not empty
- Check that each spot has `latitude` and `longitude`
- Ensure `safety_score` is a number (not null)

### Issue: Cesium library fails to load

**Solutions:**
- Check internet connection
- Try accessing the map from a different network
- Check if CDN is blocked by firewall
- The map requires: `https://cesium.com/downloads/cesiumjs/releases/1.110/Build/Cesium/Cesium.js`

## Getting Help

1. **Open Browser Console** (F12 → Console tab)
2. **Copy any error messages**
3. **Check the status message** below the "Load & Display Spots" button
4. **Verify your JSON** matches the expected format

## Quick Test

1. Open `http://192.168.0.145:8001/map`
2. Leave textarea empty
3. Click "Load & Display Spots"
4. If sample data works, your JSON format is the issue
5. If sample data doesn't work, there's a map/Cesium issue

## Expected Behavior

When JSON is loaded successfully:
- Status message shows: "✓ Successfully loaded X spots"
- Markers appear on the 3D map
- Sidebar shows list of spots
- Map centers on the query location
- You can click markers to see details

