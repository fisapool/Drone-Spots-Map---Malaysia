#!/usr/bin/env python3
"""
Screen recording script for Drone Spots Map search functionality
Uses Playwright to interact with the search and record the demonstration.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from playwright.async_api import async_playwright


async def perform_search(page, search_query: str, radius_km: float, wait_between_actions: float):
    """
    Perform a single search operation on the page.
    
    Returns:
        int: Number of spots found
    """
    # Find the search input field
    search_input = None
    try:
        search_input = page.get_by_placeholder("Enter address or location")
        if await search_input.count() == 0:
            raise Exception("Not found")
    except:
        try:
            search_input = page.locator('.sidebar input[type="text"]').first
            if await search_input.count() == 0:
                raise Exception("Not found")
        except:
            search_input = page.locator('input[type="text"]').first
    
    # Clear and enter search query
    await search_input.click()
    await asyncio.sleep(0.3)
    await search_input.fill("")  # Clear first
    await asyncio.sleep(0.2)
    await search_input.fill(search_query)
    await asyncio.sleep(wait_between_actions)
    
    # Set the radius
    try:
        radius_input = page.get_by_label("Radius (km)")
        if await radius_input.count() > 0:
            await radius_input.click()
            await asyncio.sleep(0.3)
            await radius_input.fill(str(int(radius_km)))
            await asyncio.sleep(wait_between_actions)
    except:
        pass  # Use default radius
    
    # Click the search button
    try:
        search_button = page.get_by_role("button", name="Search API")
        if await search_button.count() == 0:
            search_button = page.locator('button:has-text("Search API")').first
    except:
        search_button = page.locator('button:has-text("Search API")').first
    
    await search_button.click()
    
    # Wait for results
    max_wait = 30
    wait_interval = 2
    waited = 0
    spots_found = False
    spot_count = 0
    
    while waited < max_wait:
        spot_cards = page.locator('.spot-card')
        spot_count = await spot_cards.count()
        
        if spot_count > 0:
            spots_found = True
            break
        
        await asyncio.sleep(wait_interval)
        waited += wait_interval
        if waited % 6 == 0:
            print(f"    Still waiting... ({waited}s elapsed)")
    
    # Wait for map markers and tiles to render
    await asyncio.sleep(8)
    
    # Final check
    final_spot_count = await page.locator('.spot-card').count()
    return final_spot_count


async def record_search_demo(
    url: str = "http://localhost:8001/map",
    output_path: str = "search_demo.mp4",
    search_query: str = "Kuala Lumpur",
    radius_km: float = 15.0,
    width: int = 1920,
    height: int = 1080,
    wait_between_actions: float = 2.0,
    locations: list = None
):
    """
    Record a demonstration of the search functionality.
    
    Args:
        url: URL to the map page
        output_path: Path to save the video
        search_query: Location to search for (used if locations is None)
        radius_km: Search radius in kilometers (used if locations is None)
        width: Browser window width
        height: Browser window height
        wait_between_actions: Time to wait between actions (seconds)
        locations: List of (location_name, radius_km) tuples to search. If None, uses search_query and radius_km.
    """
    # Prepare locations list
    if locations is None:
        locations = [(search_query, radius_km)]
    
    print(f"Starting search demo recording...")
    print(f"URL: {url}")
    print(f"Locations to visit: {len(locations)}")
    for i, (loc, rad) in enumerate(locations, 1):
        print(f"  {i}. {loc} (radius: {rad} km)")
    print(f"Output: {output_path}")
    print(f"Resolution: {width}x{height}")
    print(f"\n⚠ Note: Make sure the API server is running at {url.replace('/map', '')}")
    print(f"   Each search will wait up to 30 seconds for results to load.\n")
    
    async with async_playwright() as p:
        # Launch browser with video recording enabled
        # Playwright video recording works in headless mode too
        import os
        has_display = os.getenv("DISPLAY") is not None
        
        if not has_display:
            print("No X display detected. Using headless mode (video recording still works).")
        
        print("Launching browser with video recording...")
        # Use headless mode - video recording works perfectly in headless
        browser = await p.chromium.launch(headless=True)
        
        # Create context with video recording
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir="./",  # Save video in current directory
            record_video_size={"width": width, "height": height}
        )
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # Navigate to the map page
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for page to load
            print("Waiting for page to load...")
            await asyncio.sleep(3)
            
            # Wait for map container to be visible
            print("Waiting for map to initialize...")
            await page.wait_for_selector("#leafletMapContainer", state="visible", timeout=10000)
            await asyncio.sleep(2)
            
            # Step 0: Switch to satellite view
            print("Step 0: Switching to satellite view...")
            try:
                satellite_button = page.locator('button#btnSatellite').or_(page.get_by_role("button", name="Satellite"))
                if await satellite_button.count() > 0:
                    await satellite_button.click()
                    await asyncio.sleep(2)  # Wait for satellite tiles to load
                    print("  ✓ Switched to satellite view")
                else:
                    print("  ⚠ Satellite button not found, continuing...")
            except Exception as e:
                print(f"  ⚠ Could not switch to satellite view: {e}")
            
            print(f"\n=== Starting Search Demo ===")
            
            # Loop through multiple locations
            for location_idx, (location_name, location_radius) in enumerate(locations, 1):
                print(f"\n--- Location {location_idx}/{len(locations)}: {location_name} ---")
                
                # Perform search
                print(f"Searching for '{location_name}' (radius: {location_radius} km)...")
                spot_count = await perform_search(page, location_name, location_radius, wait_between_actions)
                
                if spot_count > 0:
                    print(f"  ✓ Found {spot_count} spot(s)!")
                else:
                    print(f"  ⚠ No spots found, but continuing...")
                
                # Show results by interacting with the map
                print("  Demonstrating results on map...")
                await asyncio.sleep(2)
                
                # Try to click on a spot card if available
                spot_cards = page.locator('.spot-card')
                current_spot_count = await spot_cards.count()
                if current_spot_count > 0:
                    print(f"  Clicking on first spot card...")
                    await spot_cards.first.click()
                    await asyncio.sleep(3)  # Wait for map to focus on spot
                    print("  ✓ Map focused on first spot")
                
                # Zoom in to show markers better
                print("  Zooming in to see markers better...")
                try:
                    zoom_in = page.locator('.leaflet-control-zoom-in').first
                    if await zoom_in.count() > 0:
                        # Zoom in multiple times for closer view
                        for i in range(4):  # Zoom in 4 times
                            await zoom_in.click()
                            await asyncio.sleep(1.5)  # Wait between zooms
                        await asyncio.sleep(2)  # Final wait after all zooms
                except:
                    pass  # Zoom not critical
                
                # Show final view of this location
                print(f"  Showing {location_name} results...")
                await asyncio.sleep(4)  # Show results for this location
                
                # If not the last location, prepare for next search
                if location_idx < len(locations):
                    print(f"  Transitioning to next location...")
                    # Zoom out a bit to prepare for next location
                    try:
                        zoom_out = page.locator('.leaflet-control-zoom-out').first
                        if await zoom_out.count() > 0:
                            for i in range(2):  # Zoom out 2 times
                                await zoom_out.click()
                                await asyncio.sleep(1)
                    except:
                        pass
                    await asyncio.sleep(2)  # Brief pause between locations
            
            print(f"\n=== Demo Complete ===")
            
            # Close the page to finalize video recording
            await page.close()
            
            # Close context to ensure video is saved
            await context.close()
            
            # Playwright saves video with a generated name, we need to rename it
            # The video is saved in the record_video_dir with a generated name
            print("\nFinalizing video recording...")
            await asyncio.sleep(1)  # Give time for video to be written
            
            # Find the most recent video file in current directory
            video_files = sorted(Path(".").glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
            if video_files:
                latest_video = video_files[0]
                # Rename to desired output path
                output_file = Path(output_path)
                latest_video.rename(output_file)
                print(f"✓ Video saved to: {output_path}")
                
                # Get file size
                file_size = output_file.stat().st_size
                print(f"  File size: {file_size / (1024*1024):.2f} MB")
                
                # Optionally convert to MP4 if it's webm (requires ffmpeg)
                if output_path.endswith('.mp4') and latest_video.suffix == '.webm':
                    print("\nNote: Video is in WebM format. To convert to MP4, install ffmpeg and run:")
                    print(f"  ffmpeg -i {output_path} -c:v libx264 -c:a aac {output_path.replace('.webm', '.mp4')}")
            else:
                print("⚠ Warning: Could not find recorded video file")
            
        except Exception as e:
            print(f"✗ Error during recording: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        finally:
            # Clean up
            await browser.close()
            print("Browser closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Record a demonstration of the Drone Spots Map search functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default: search for "Kuala Lumpur")
  python record_search_demo.py
  
  # Facebook square format (1080x1080) - recommended for feed
  python record_search_demo.py --facebook
  
  # Facebook vertical format (1080x1920) - for Stories/Reels
  python record_search_demo.py --facebook-vertical
  
  # Facebook landscape format (1280x720)
  python record_search_demo.py --facebook-landscape
  
  # Custom search query
  python record_search_demo.py --query "Penang" --radius 20
  
  # Custom output file
  python record_search_demo.py --output my_demo.mp4
  
  # Higher resolution
  python record_search_demo.py --width 2560 --height 1440
  
  # Faster demo (less wait time)
  python record_search_demo.py --wait-time 1.0
  
  # Multiple locations
  python record_search_demo.py --locations "Kuala Lumpur:15" "Penang:20" "Johor Bahru:15"
        """
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8001/map",
        help="URL to the map page (default: http://localhost:8001/map)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="search_demo.webm",
        help="Output video file path (default: search_demo.webm)"
    )
    
    parser.add_argument(
        "--query", "-q",
        default="Kuala Lumpur",
        help="Search query/location (default: Kuala Lumpur)"
    )
    
    parser.add_argument(
        "--radius", "-r",
        type=float,
        default=15.0,
        help="Search radius in kilometers (default: 15.0)"
    )
    
    parser.add_argument(
        "--width", "-w",
        type=int,
        default=1920,
        help="Video width in pixels (default: 1920)"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Video height in pixels (default: 1080)"
    )
    
    parser.add_argument(
        "--wait-time",
        type=float,
        default=2.0,
        help="Time to wait between actions in seconds (default: 2.0)"
    )
    
    # Facebook video format presets
    parser.add_argument(
        "--facebook",
        action="store_true",
        help="Use Facebook square format (1080x1080) - recommended for feed posts"
    )
    
    parser.add_argument(
        "--facebook-vertical",
        action="store_true",
        help="Use Facebook vertical format (1080x1920) - for Stories/Reels"
    )
    
    parser.add_argument(
        "--facebook-landscape",
        action="store_true",
        help="Use Facebook landscape format (1280x720) - for feed videos"
    )
    
    parser.add_argument(
        "--facebook-hq",
        action="store_true",
        help="Use high-resolution Facebook square format (1920x1920) - for maximum quality"
    )
    
    parser.add_argument(
        "--locations",
        nargs="+",
        help="Multiple locations to visit in format 'location:radius'. Example: --locations 'Kuala Lumpur:15' 'Penang:20'"
    )
    
    args = parser.parse_args()
    
    # Apply Facebook presets
    width = args.width
    height = args.height
    
    if args.facebook_hq:
        width = 1920
        height = 1920
        print("Using high-resolution Facebook square format (1920x1920)")
    elif args.facebook:
        width = 1080
        height = 1080
        print("Using Facebook square format (1080x1080)")
    elif args.facebook_vertical:
        width = 1080
        height = 1920
        print("Using Facebook vertical format (1080x1920) - Stories/Reels")
    elif args.facebook_landscape:
        width = 1280
        height = 720
        print("Using Facebook landscape format (1280x720)")
    
    # Parse locations if provided
    locations = None
    if args.locations:
        locations = []
        for loc_str in args.locations:
            if ':' in loc_str:
                parts = loc_str.rsplit(':', 1)
                loc_name = parts[0].strip()
                try:
                    loc_radius = float(parts[1].strip())
                except ValueError:
                    print(f"Warning: Invalid radius for '{loc_name}', using default {args.radius}")
                    loc_radius = args.radius
            else:
                loc_name = loc_str.strip()
                loc_radius = args.radius
            locations.append((loc_name, loc_radius))
    
    # Run the async function
    asyncio.run(record_search_demo(
        url=args.url,
        output_path=args.output,
        search_query=args.query,
        radius_km=args.radius,
        width=width,
        height=height,
        wait_between_actions=args.wait_time,
        locations=locations
    ))


if __name__ == "__main__":
    main()

