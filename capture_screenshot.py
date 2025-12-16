#!/usr/bin/env python3
"""
Screenshot capture script for Drone Spots Map
Uses Playwright to capture high-quality screenshots of the map interface.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from playwright.async_api import async_playwright


async def capture_screenshot(
    url: str = "http://localhost:8001/map",
    output_path: str = "demo_screenshot.png",
    width: int = 1920,
    height: int = 1080,
    wait_time: int = 5,
    full_page: bool = False,
    wait_for_map: bool = True
):
    """
    Capture a screenshot of the map page.
    
    Args:
        url: URL to capture (default: http://localhost:8001/map)
        output_path: Path to save the screenshot
        width: Browser window width in pixels
        height: Browser window height in pixels
        wait_time: Time to wait for page to load (seconds)
        full_page: If True, capture full page scroll. If False, capture viewport only.
        wait_for_map: If True, wait for map tiles to load before capturing
    """
    print(f"Starting screenshot capture...")
    print(f"URL: {url}")
    print(f"Output: {output_path}")
    print(f"Resolution: {width}x{height}")
    
    async with async_playwright() as p:
        # Launch browser (use chromium for best compatibility)
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        
        # Create a new context with viewport size
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2  # Higher DPI for better quality
        )
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # Navigate to the page
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for initial load
            print(f"Waiting {wait_time} seconds for page to fully load...")
            await asyncio.sleep(wait_time)
            
            # Wait for map to be ready if requested
            if wait_for_map:
                print("Waiting for map tiles to load...")
                try:
                    # Wait for Leaflet map container to be visible
                    await page.wait_for_selector("#leafletMapContainer", state="visible", timeout=10000)
                    # Wait a bit more for tiles to render
                    await asyncio.sleep(2)
                    print("Map loaded successfully!")
                except Exception as e:
                    print(f"Warning: Could not verify map loaded: {e}")
                    print("Proceeding with screenshot anyway...")
            
            # Take screenshot
            print("Capturing screenshot...")
            await page.screenshot(
                path=output_path,
                full_page=full_page,
                type="png"
            )
            
            print(f"✓ Screenshot saved to: {output_path}")
            
            # Get file size
            file_size = Path(output_path).stat().st_size
            print(f"  File size: {file_size / 1024:.2f} KB")
            
        except Exception as e:
            print(f"✗ Error capturing screenshot: {e}", file=sys.stderr)
            sys.exit(1)
        
        finally:
            # Clean up
            await browser.close()
            print("Browser closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Capture screenshot of Drone Spots Map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default settings)
  python capture_screenshot.py
  
  # Custom URL and output
  python capture_screenshot.py --url http://192.168.0.145:8001/map --output my_screenshot.png
  
  # Full page screenshot
  python capture_screenshot.py --full-page
  
  # Custom resolution
  python capture_screenshot.py --width 2560 --height 1440
  
  # Quick capture (less wait time)
  python capture_screenshot.py --wait-time 2 --no-wait-map
        """
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8001/map",
        help="URL to capture (default: http://localhost:8001/map)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="demo_screenshot.png",
        help="Output file path (default: demo_screenshot.png)"
    )
    
    parser.add_argument(
        "--width", "-w",
        type=int,
        default=1920,
        help="Browser window width in pixels (default: 1920)"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Browser window height in pixels (default: 1080)"
    )
    
    parser.add_argument(
        "--wait-time",
        type=int,
        default=5,
        help="Time to wait for page to load in seconds (default: 5)"
    )
    
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture full page (scrollable content) instead of viewport only"
    )
    
    parser.add_argument(
        "--no-wait-map",
        action="store_true",
        help="Don't wait for map tiles to load (faster but may miss content)"
    )
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(capture_screenshot(
        url=args.url,
                 output_path=args.output,
                 width=args.width,
                 height=args.height,
                 wait_time=args.wait_time,
                 full_page=args.full_page,
                 wait_for_map=not args.no_wait_map
    ))


if __name__ == "__main__":
    main()

