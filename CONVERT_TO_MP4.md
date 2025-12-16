# Convert WebM Videos to MP4

This guide will help you convert the demo videos from WebM to MP4 format for better compatibility.

## Quick Start

### Step 1: Install ffmpeg

```bash
sudo apt install ffmpeg
```

### Step 2: Convert Videos

**Option A: Using Python script (recommended)**
```bash
python3 convert_webm_to_mp4.py
```

**Option B: Using shell script**
```bash
./convert_all_videos.sh
```

**Option C: Manual conversion**
```bash
ffmpeg -i search_demo_facebook_hq.webm -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart -y search_demo_facebook_hq.mp4
ffmpeg -i search_demo_facebook.webm -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart -y search_demo_facebook.mp4
ffmpeg -i search_demo_satellite.webm -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart -y search_demo_satellite.mp4
ffmpeg -i search_demo.webm -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart -y search_demo.mp4
```

## What Gets Converted

The scripts will convert these files:
- `search_demo_facebook_hq.webm` → `search_demo_facebook_hq.mp4`
- `search_demo_facebook.webm` → `search_demo_facebook.mp4`
- `search_demo_satellite.webm` → `search_demo_satellite.mp4`
- `search_demo.webm` → `search_demo.mp4`

## After Conversion

Once converted, you can:
1. Add the MP4 files to git: `git add search_demo*.mp4`
2. Update README.md to reference MP4 files instead of (or in addition to) WebM
3. Commit and push: `git commit -m "Add MP4 versions of demo videos" && git push`

## Troubleshooting

**ffmpeg not found?**
- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

**Conversion fails?**
- Check that input files exist: `ls -lh search_demo*.webm`
- Verify ffmpeg is installed: `ffmpeg -version`
- Check disk space: `df -h .`

**Large file sizes?**
- Use lower quality: Edit the script and change `-crf 23` to `-crf 28` (higher number = smaller file, lower quality)

