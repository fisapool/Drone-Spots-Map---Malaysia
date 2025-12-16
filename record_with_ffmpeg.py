#!/usr/bin/env python3
"""
Screen recording script using ffmpeg for Drone Spots Map search functionality
This script opens the browser and uses ffmpeg to record the screen.
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_ffmpeg_instructions():
    """Print instructions for installing ffmpeg."""
    print("\n" + "="*60)
    print("FFmpeg is not installed. To install it:")
    print("="*60)
    print("\nOn Ubuntu/Debian:")
    print("  sudo apt update")
    print("  sudo apt install ffmpeg")
    print("\nOn Fedora/RHEL:")
    print("  sudo dnf install ffmpeg")
    print("\nOn macOS (with Homebrew):")
    print("  brew install ffmpeg")
    print("\nAfter installation, run this script again.")
    print("="*60 + "\n")


async def open_browser_and_wait(url, width=1920, height=1080):
    """Open browser and keep it open for recording."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": width, "height": height}
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # Wait for initial load
        
        print(f"Browser opened at {url}")
        print("Browser will stay open for recording...")
        print("Press Ctrl+C to stop recording and close browser")
        
        # Keep browser open
        try:
            await asyncio.sleep(3600)  # Keep open for up to 1 hour
        except KeyboardInterrupt:
            print("\nClosing browser...")
        finally:
            await browser.close()


def record_screen_ffmpeg(output_path="search_demo.mp4", duration=None, display=None):
    """
    Record screen using ffmpeg.
    
    Args:
        output_path: Path to save the video
        duration: Duration in seconds (None = until interrupted)
        display: X11 display (None = auto-detect)
    """
    if not check_ffmpeg():
        install_ffmpeg_instructions()
        sys.exit(1)
    
    # Detect display
    if display is None:
        display = ":0"  # Default X11 display
    
    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-f", "x11grab",  # X11 screen capture
        "-s", "1920x1080",  # Screen size
        "-r", "30",  # Frame rate
        "-i", f"{display}+0,0",  # Display and position
        "-c:v", "libx264",  # Video codec
        "-preset", "medium",  # Encoding preset
        "-crf", "23",  # Quality (lower = better, 18-28 is good range)
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-y",  # Overwrite output file
    ]
    
    if duration:
        cmd.extend(["-t", str(duration)])
    
    cmd.append(output_path)
    
    print(f"Starting screen recording...")
    print(f"Output: {output_path}")
    print(f"Display: {display}")
    print(f"Resolution: 1920x1080 @ 30fps")
    if duration:
        print(f"Duration: {duration} seconds")
    else:
        print("Duration: Until interrupted (Ctrl+C)")
    print("\nRecording started. Perform your search demonstration now...")
    print("Press Ctrl+C to stop recording\n")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Recording saved to: {output_path}")
        
        # Get file size
        file_size = Path(output_path).stat().st_size
        print(f"  File size: {file_size / (1024*1024):.2f} MB")
    except KeyboardInterrupt:
        print("\n\nRecording stopped by user.")
        # FFmpeg should handle cleanup
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error during recording: {e}", file=sys.stderr)
        sys.exit(1)


async def interactive_demo(url, search_query="Kuala Lumpur", radius_km=15.0):
    """Open browser and perform search interactively."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            print(f"Opening {url}...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            print(f"\n=== Ready for Search Demo ===")
            print(f"Search query: {search_query}")
            print(f"Radius: {radius_km} km")
            print(f"\nThe browser is now open.")
            print(f"Please perform the search manually while ffmpeg records.")
            print(f"Press Enter when you're done with the demo...")
            
            # Wait for user to press Enter
            input()
            
        finally:
            await browser.close()
            print("Browser closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Record screen using ffmpeg while demonstrating search functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record screen (manual demo)
  python record_with_ffmpeg.py
  
  # Record with specific duration
  python record_with_ffmpeg.py --duration 60
  
  # Custom output file
  python record_with_ffmpeg.py --output my_demo.mp4
  
  # Open browser automatically and wait for manual demo
  python record_with_ffmpeg.py --auto-browser
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        default="search_demo.mp4",
        help="Output video file (default: search_demo.mp4)"
    )
    
    parser.add_argument(
        "--duration", "-d",
        type=int,
        help="Recording duration in seconds (default: until interrupted)"
    )
    
    parser.add_argument(
        "--display",
        help="X11 display (default: :0)"
    )
    
    parser.add_argument(
        "--auto-browser",
        action="store_true",
        help="Automatically open browser and wait for manual demo"
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8001/map",
        help="Map URL (default: http://localhost:8001/map)"
    )
    
    parser.add_argument(
        "--query", "-q",
        default="Kuala Lumpur",
        help="Search query for reference (default: Kuala Lumpur)"
    )
    
    parser.add_argument(
        "--radius", "-r",
        type=float,
        default=15.0,
        help="Search radius in km for reference (default: 15.0)"
    )
    
    args = parser.parse_args()
    
    if args.auto_browser:
        # Open browser and wait, then record
        print("This mode will open the browser first, then start recording.")
        print("You'll need to run ffmpeg in another terminal or use the Playwright recording script instead.")
        print("\nFor automated recording, use: python record_search_demo.py")
        print("\nOpening browser for manual demo...")
        asyncio.run(interactive_demo(args.url, args.query, args.radius))
    else:
        # Just record the screen
        record_screen_ffmpeg(
            output_path=args.output,
            duration=args.duration,
            display=args.display
        )


if __name__ == "__main__":
    main()

