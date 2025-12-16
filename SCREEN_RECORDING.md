# Screen Recording Guide for Drone Spots Map

This guide explains how to record demonstrations of the search functionality on the Drone Spots Map.

## Available Scripts

### 1. `record_search_demo.py` (Recommended - Automated)

**Playwright-based automated recording** that performs the search automatically and records the entire process.

**Features:**
- ✅ Fully automated - no manual interaction needed
- ✅ Works in headless mode (no display required)
- ✅ Records browser interactions automatically
- ✅ High-quality WebM video output
- ✅ Configurable search queries and parameters

**Usage:**
```bash
# Activate virtual environment
source venv/bin/activate

# Basic usage (default: search for "Kuala Lumpur")
python record_search_demo.py

# Custom search query
python record_search_demo.py --query "Penang" --radius 20

# Custom output file
python record_search_demo.py --output my_demo.webm

# Higher resolution
python record_search_demo.py --width 2560 --height 1440

# Faster demo (less wait time between actions)
python record_search_demo.py --wait-time 1.0
```

**Options:**
- `--url`: Map URL (default: http://localhost:8001/map)
- `--output, -o`: Output video file (default: search_demo.webm)
- `--query, -q`: Search query/location (default: Kuala Lumpur)
- `--radius, -r`: Search radius in kilometers (default: 15.0)
- `--width, -w`: Video width in pixels (default: 1920)
- `--height`: Video height in pixels (default: 1080)
- `--wait-time`: Time to wait between actions in seconds (default: 2.0)

**What it does:**
1. Opens the map page
2. Enters the search query
3. Sets the search radius
4. Clicks the "Search API" button
5. Waits for results to load
6. Demonstrates map interactions
7. Records everything as a video

### 2. `record_with_ffmpeg.py` (Manual Recording)

**FFmpeg-based screen recording** for manual demonstrations where you control the browser.

**Features:**
- ✅ Records your actual screen
- ✅ Full control over the demonstration
- ✅ Requires ffmpeg installation
- ✅ Requires X server/display

**Prerequisites:**
```bash
# Install ffmpeg on Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg
```

**Usage:**
```bash
# Activate virtual environment
source venv/bin/activate

# Record screen (manual demo - you control the browser)
python record_with_ffmpeg.py

# Record with specific duration
python record_with_ffmpeg.py --duration 60

# Custom output file
python record_with_ffmpeg.py --output my_demo.mp4
```

**Note:** This script requires you to manually perform the search while it records your screen. For automated recording, use `record_search_demo.py` instead.

## Facebook Video Formats

The script supports Facebook's recommended video formats:

```bash
# Facebook square format (1080x1080) - Recommended for feed posts
python record_search_demo.py --facebook

# Facebook vertical format (1080x1920) - For Stories/Reels
python record_search_demo.py --facebook-vertical

# Facebook landscape format (1280x720) - For feed videos
python record_search_demo.py --facebook-landscape
```

## Converting WebM to MP4 for Facebook

For optimal Facebook upload, convert WebM to MP4 with Facebook-optimized settings:

```bash
# Install ffmpeg if not already installed
sudo apt install ffmpeg

# Convert to Facebook square format (recommended)
python convert_for_facebook.py search_demo.webm --format square

# Convert to vertical format for Stories/Reels
python convert_for_facebook.py search_demo.webm --format vertical

# Convert with custom quality
python convert_for_facebook.py search_demo.webm --quality high
```

Or manually with ffmpeg:
```bash
# Square format (1080x1080)
ffmpeg -i search_demo.webm -vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1:1" -r 30 -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart search_demo_facebook.mp4
```

## Screenshot Capture

For static screenshots instead of video, use:

```bash
# Activate virtual environment
source venv/bin/activate

# Basic screenshot
python capture_screenshot.py

# Custom settings
python capture_screenshot.py --url http://localhost:8001/map --output screenshot.png --width 2560 --height 1440
```

See `capture_screenshot.py --help` for all options.

## Troubleshooting

### "No X display detected"
- **Solution:** The Playwright script works in headless mode, so this is not an error. Video recording works fine without a display.

### "Browser closed unexpectedly"
- **Solution:** Make sure the API server is running at the specified URL. Check with:
  ```bash
  curl http://localhost:8001/map
  ```

### "Video file not found"
- **Solution:** Playwright saves videos with generated names. The script automatically renames them. If the file is missing, check the current directory for `.webm` files.

### "FFmpeg not found" (for record_with_ffmpeg.py)
- **Solution:** Install ffmpeg:
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```

## Example Workflow

1. **Start the API server:**
   ```bash
   python drone_spots_api.py
   ```

2. **Record automated demo:**
   ```bash
   source venv/bin/activate
   python record_search_demo.py --query "Kuala Lumpur" --output demo.webm
   ```

3. **Convert to MP4 (optional):**
   ```bash
   ffmpeg -i demo.webm -c:v libx264 -c:a aac demo.mp4
   ```

## Video Output Details

- **Format:** WebM (Playwright) or MP4 (FFmpeg)
- **Codec:** VP8/VP9 (WebM) or H.264 (MP4)
- **Quality:** High (2x device scale factor for Playwright)
- **Frame Rate:** 30 fps (FFmpeg) or variable (Playwright)
- **Resolution:** Configurable (default: 1920x1080)

## Requirements

All scripts require:
- Python 3.8+
- Playwright (installed via `pip install playwright && playwright install chromium`)
- Virtual environment (recommended)

For FFmpeg script:
- FFmpeg installed on system
- X server/display (for manual recording)

