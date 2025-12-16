#!/usr/bin/env python3
"""
Convert video to Facebook-optimized format
Converts WebM to MP4 with Facebook's recommended settings.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, stdout=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_to_facebook_format(
    input_file: str,
    output_file: str = None,
    format_type: str = "square",
    quality: str = "high"
):
    """
    Convert video to Facebook-optimized format.
    
    Args:
        input_file: Input video file path
        output_file: Output file path (default: input_file with .mp4 extension)
        format_type: "square" (1080x1080), "vertical" (1080x1920), or "landscape" (1280x720)
        quality: "high", "medium", or "low"
    """
    if not check_ffmpeg():
        print("✗ Error: ffmpeg is not installed.")
        print("\nInstall ffmpeg:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        sys.exit(1)
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"✗ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    if output_file is None:
        output_file = str(input_path.with_suffix('.mp4'))
    
    # Facebook format presets
    format_presets = {
        "square": {
            "scale": "1080:1080",
            "description": "Square (1080x1080) - Feed posts"
        },
        "vertical": {
            "scale": "1080:1920",
            "description": "Vertical (1080x1920) - Stories/Reels"
        },
        "landscape": {
            "scale": "1280:720",
            "description": "Landscape (1280x720) - Feed videos"
        }
    }
    
    if format_type not in format_presets:
        print(f"✗ Error: Invalid format type '{format_type}'. Use: square, vertical, or landscape")
        sys.exit(1)
    
    preset = format_presets[format_type]
    print(f"Converting to Facebook format: {preset['description']}")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    
    # Quality presets
    quality_settings = {
        "high": {"crf": "20", "preset": "slow"},
        "medium": {"crf": "23", "preset": "medium"},
        "low": {"crf": "26", "preset": "fast"}
    }
    
    qs = quality_settings.get(quality, quality_settings["medium"])
    
    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vf", f"scale={preset['scale']}:force_original_aspect_ratio=decrease,pad={preset['scale']}:(ow-iw)/2:(oh-ih)/2,setsar=1:1",
        "-r", "30",  # Frame rate
        "-c:v", "libx264",  # Video codec
        "-preset", qs["preset"],  # Encoding preset
        "-crf", qs["crf"],  # Quality
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-c:a", "aac",  # Audio codec
        "-b:a", "128k",  # Audio bitrate
        "-movflags", "+faststart",  # Fast start for web playback
        "-y",  # Overwrite output
        output_file
    ]
    
    print(f"\nRunning conversion (this may take a few minutes)...")
    print(f"Quality: {quality} (CRF {qs['crf']}, preset: {qs['preset']})")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"\n✓ Conversion complete!")
        print(f"  Output: {output_file}")
        
        # Get file size
        output_path = Path(output_file)
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"  File size: {file_size / (1024*1024):.2f} MB")
        
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Conversion failed!")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert video to Facebook-optimized format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert to Facebook square format (default)
  python convert_for_facebook.py input.webm
  
  # Convert to vertical format for Stories/Reels
  python convert_for_facebook.py input.webm --format vertical
  
  # Convert with custom output name
  python convert_for_facebook.py input.webm --output output.mp4
  
  # Convert with lower quality (faster, smaller file)
  python convert_for_facebook.py input.webm --quality low
        """
    )
    
    parser.add_argument(
        "input",
        help="Input video file (WebM, MP4, etc.)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: input filename with .mp4 extension)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["square", "vertical", "landscape"],
        default="square",
        help="Facebook format: square (1080x1080), vertical (1080x1920), or landscape (1280x720) (default: square)"
    )
    
    parser.add_argument(
        "--quality", "-q",
        choices=["high", "medium", "low"],
        default="medium",
        help="Video quality: high (larger file, best quality), medium (balanced), or low (smaller file) (default: medium)"
    )
    
    args = parser.parse_args()
    
    convert_to_facebook_format(
        input_file=args.input,
        output_file=args.output,
        format_type=args.format,
        quality=args.quality
    )


if __name__ == "__main__":
    main()

