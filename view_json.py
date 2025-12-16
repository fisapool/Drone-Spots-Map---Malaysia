#!/usr/bin/env python3
"""
Quick script to format and display JSON from API responses or files.
Usage:
    python view_json.py                    # Reads from stdin
    python view_json.py < file.json       # Reads from file
    curl ... | python view_json.py        # Pipes curl output
"""

import json
import sys

def format_json(data):
    """Format JSON with proper indentation"""
    try:
        if isinstance(data, str):
            # Try to parse as JSON string
            parsed = json.loads(data)
        else:
            parsed = data
        
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}\n\nRaw data:\n{data}"
    except Exception as e:
        return f"Error: {e}\n\nRaw data:\n{data}"

if __name__ == "__main__":
    # Read from stdin or command line argument
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = f.read()
    else:
        # Read from stdin
        data = sys.stdin.read()
    
    print(format_json(data))

