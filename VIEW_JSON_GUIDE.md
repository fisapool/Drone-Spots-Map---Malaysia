# How to View JSON Responses in Readable Format

## Method 1: Using Python's json.tool (Built-in)

```bash
# Format JSON from a curl command
curl "http://localhost:8001/search?address=Kuala%20Lumpur&radius_km=10&max_results=5" | python3 -m json.tool

# Or save to file first, then format
curl "http://localhost:8001/search?address=Kuala%20Lumpur" > response.json
python3 -m json.tool response.json
```

## Method 2: Using jq (Recommended - Most Powerful)

First install jq:
```bash
sudo apt install jq  # Ubuntu/Debian
```

Then use it:
```bash
# Format JSON
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq .

# Extract specific fields
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq '.spots[0].name'
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq '.spots[] | {name, safety_score, car_accessible}'

# Pretty print with colors
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq -C .
```

## Method 3: Using the view_json.py Script

```bash
# Pipe curl output
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | python3 view_json.py

# Format a saved JSON file
python3 view_json.py response.json
```

## Method 4: Using explore_api.py (Already Formatted)

The `explore_api.py` script already formats JSON nicely:
```bash
python3 explore_api.py
```

## Method 5: Browser Extensions

Install a JSON formatter extension in your browser:
- Chrome: "JSON Formatter" or "JSON Viewer"
- Firefox: "JSONView"

Then open the API URL directly:
```
http://localhost:8001/search?address=Kuala%20Lumpur&radius_km=10
```

## Method 6: Using Python Interactive

```python
import json
import requests

response = requests.get("http://localhost:8001/search", params={
    "address": "Kuala Lumpur",
    "radius_km": 10
})
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

## Method 7: Save and View in VS Code / Editor

```bash
# Save to file
curl "http://localhost:8001/search?address=Kuala%20Lumpur" > response.json

# Open in your editor (VS Code, etc.)
code response.json
```

Most editors will auto-format JSON when you open it.

## Quick Examples

### Format the last command's output:
If you just ran a curl command and got unformatted JSON, you can:
```bash
# Re-run with formatting
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | python3 -m json.tool
```

### View specific parts:
```bash
# Just the spots array
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq '.spots'

# Just spot names and safety scores
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq '.spots[] | {name, safety_score}'

# Count spots
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | jq '.total_spots_found'
```

## Recommended Setup

For the best experience, install `jq`:
```bash
sudo apt install jq
```

Then create an alias in your `~/.bashrc`:
```bash
alias json='python3 -m json.tool'
```

Or use jq directly (it's more powerful):
```bash
alias j='jq .'
```

Then you can simply:
```bash
curl "http://localhost:8001/search?address=Kuala%20Lumpur" | j
```

