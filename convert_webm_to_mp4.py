#!/usr/bin/env python3
"""
Convert all WebM demo videos to MP4 format
Simple conversion script for GitHub repository
"""

import subprocess
import sys
from pathlib import Path


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_webm_to_mp4(input_file: str, output_file: str = None):
    """Convert WebM file to MP4 format."""
    if not check_ffmpeg():
        print("✗ Error: ffmpeg is not installed.")
        print("\nPlease install ffmpeg first:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"✗ Error: Input file not found: {input_file}")
        return False
    
    if output_file is None:
        output_file = str(input_path.with_suffix('.mp4'))
    
    print(f"Converting: {input_file} -> {output_file}")
    
    # Simple conversion command - preserves quality and format
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:v", "libx264",  # H.264 video codec (widely compatible)
        "-preset", "medium",  # Encoding speed/quality balance
        "-crf", "23",  # Quality (18-28, lower = better quality)
        "-c:a", "aac",  # AAC audio codec
        "-b:a", "128k",  # Audio bitrate
        "-movflags", "+faststart",  # Fast start for web playback
        "-y",  # Overwrite output file if exists
        output_file
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Success: {output_file}")
        
        # Show file size
        output_path = Path(output_file)
        if output_path.exists():
            input_size = input_path.stat().st_size / (1024*1024)
            output_size = output_path.stat().st_size / (1024*1024)
            print(f"  Size: {input_size:.2f} MB -> {output_size:.2f} MB")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Conversion failed: {e.stderr}")
        return False


def main():
    """Convert all search_demo*.webm files to MP4."""
    current_dir = Path(".")
    webm_files = list(current_dir.glob("search_demo*.webm"))
    
    if not webm_files:
        print("No search_demo*.webm files found in current directory.")
        return
    
    print(f"Found {len(webm_files)} WebM file(s) to convert:\n")
    
    success_count = 0
    for webm_file in sorted(webm_files):
        if convert_webm_to_mp4(str(webm_file)):
            success_count += 1
        print()  # Empty line between conversions
    
    print(f"\n{'='*50}")
    print(f"Conversion complete: {success_count}/{len(webm_files)} files converted")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

