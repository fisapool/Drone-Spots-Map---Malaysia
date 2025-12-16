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
    wait_for_map: bool = True,
    search_query: str = None,
    output_dir: str = None
):
    """
    Capture screenshots of the map page, including search results.
    
    Args:
        url: URL to capture (default: http://localhost:8001/map)
        output_path: Path to save the screenshot (or base name if multiple screenshots)
        width: Browser window width in pixels
        height: Browser window height in pixels
        wait_time: Time to wait for page to load (seconds)
        full_page: If True, capture full page scroll. If False, capture viewport only.
        wait_for_map: If True, wait for map tiles to load before capturing
        search_query: Optional search query to test (e.g., "Kuala Lumpur")
        output_dir: Directory to save multiple screenshots (default: same as output_path directory)
    """
    print(f"Starting screenshot capture...")
    print(f"URL: {url}")
    print(f"Resolution: {width}x{height}")
    
    # Determine output directory
    if output_dir is None:
        output_dir = Path(output_path).parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(output_path).stem
    
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
            
            # Screenshot 1: Initial page load
            screenshot_path = output_dir / f"{base_name}_01_initial.png"
            print(f"\n📸 Screenshot 1: Initial page load...")
            await page.screenshot(
                path=str(screenshot_path),
                full_page=full_page,
                type="png"
            )
            file_size = screenshot_path.stat().st_size
            print(f"✓ Saved: {screenshot_path}")
            print(f"  File size: {file_size / 1024:.2f} KB")
            
            # If search query provided, perform search and capture more screenshots
            if search_query:
                print(f"\n🔍 Performing search for: '{search_query}'")
                
                # Find and fill the search input
                try:
                    search_input = await page.wait_for_selector("#apiSearchInput", timeout=5000)
                    # Click to focus, then fill (fill() replaces existing content)
                    await search_input.click()
                    await search_input.fill(search_query)
                    print(f"✓ Entered search query: {search_query}")
                    
                    # Screenshot 2: After entering search query (before clicking search)
                    await asyncio.sleep(0.5)  # Brief pause for UI update
                    screenshot_path = output_dir / f"{base_name}_02_search_entered.png"
                    print(f"\n📸 Screenshot 2: Search query entered...")
                    await page.screenshot(
                        path=str(screenshot_path),
                        full_page=full_page,
                        type="png"
                    )
                    file_size = screenshot_path.stat().st_size
                    print(f"✓ Saved: {screenshot_path}")
                    print(f"  File size: {file_size / 1024:.2f} KB")
                    
                    # Check API base URL before searching
                    api_base_url = await page.evaluate("""() => {
                        return typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : 'not found';
                    }""")
                    print(f"  API Base URL: {api_base_url}")
                    
                    # Click the search button
                    search_btn = await page.wait_for_selector("#apiSearchBtn", timeout=5000)
                    await search_btn.click()
                    print(f"✓ Clicked search button")
                    
                    # Wait for search to complete and results to appear
                    print("⏳ Waiting for search results...")
                    
                    # Monitor search progress with periodic checks
                    async def check_search_status():
                        """Periodically check search status"""
                        for i in range(6):  # Check every 5 seconds for 30 seconds
                            await asyncio.sleep(5)
                            try:
                                status_info = await page.evaluate("""() => {
                                    const spotsList = document.getElementById('spotsList');
                                    const statusMsg = document.getElementById('apiStatusMessage');
                                    const searchBtn = document.getElementById('apiSearchBtn');
                                    
                                    return {
                                        resultCount: spotsList ? spotsList.children.length : 0,
                                        statusText: statusMsg ? statusMsg.textContent.substring(0, 100) : '',
                                        buttonText: searchBtn ? searchBtn.textContent : '',
                                        buttonDisabled: searchBtn ? searchBtn.disabled : true
                                    };
                                }""")
                                print(f"  [{i*5+5}s] Status: {status_info['statusText'] or 'No status'} | Button: {status_info['buttonText']} | Results: {status_info['resultCount']}")
                            except:
                                pass
                    
                    # Start monitoring in background
                    monitor_task = asyncio.create_task(check_search_status())
                    
                    # Wait for either spots list to populate OR error message OR button to re-enable (search complete)
                    try:
                        # Wait for search to complete (button re-enables) OR results to appear OR error
                        # Use a simpler condition: wait for button to re-enable OR results to appear
                        await page.wait_for_function(
                            """() => {
                                const spotsList = document.getElementById('spotsList');
                                const statusMsg = document.getElementById('apiStatusMessage');
                                const searchBtn = document.getElementById('apiSearchBtn');
                                
                                // Check if search completed (button re-enabled and not "Searching...")
                                const searchComplete = searchBtn && !searchBtn.disabled && searchBtn.textContent !== 'Searching...';
                                
                                // Check if results appeared
                                const hasResults = spotsList && spotsList.children.length > 0;
                                
                                // Check if error message is shown (red color or error text)
                                const statusColor = statusMsg ? window.getComputedStyle(statusMsg).color : '';
                                const hasError = statusMsg && statusMsg.style.display !== 'none' && 
                                               (statusMsg.textContent.includes('Error') || 
                                                statusMsg.textContent.includes('✗') ||
                                                statusColor === 'rgb(220, 53, 69)');
                                
                                // Check if success message is shown (green color or success text)
                                const hasSuccess = statusMsg && statusMsg.style.display !== 'none' && 
                                                  (statusMsg.textContent.includes('Found') || 
                                                   statusMsg.textContent.includes('✓') ||
                                                   statusColor === 'rgb(40, 167, 69)');
                                
                                // Return true if search completed OR results appeared OR error/success shown
                                return searchComplete || hasResults || hasError || hasSuccess;
                            }""",
                            timeout=30000
                        )
                        
                        # Cancel monitoring task
                        monitor_task.cancel()
                        try:
                            await monitor_task
                        except asyncio.CancelledError:
                            pass
                        
                        # Check what happened
                        status_info = await page.evaluate("""() => {
                            const spotsList = document.getElementById('spotsList');
                            const statusMsg = document.getElementById('apiStatusMessage');
                            const searchBtn = document.getElementById('apiSearchBtn');
                            
                            return {
                                resultCount: spotsList ? spotsList.children.length : 0,
                                statusText: statusMsg ? statusMsg.textContent : '',
                                statusVisible: statusMsg ? statusMsg.style.display !== 'none' : false,
                                statusColor: statusMsg ? window.getComputedStyle(statusMsg).color : '',
                                buttonText: searchBtn ? searchBtn.textContent : ''
                            };
                        }""")
                        
                        print(f"  Status: {status_info['statusText'][:100] if status_info['statusText'] else 'No status'}")
                        print(f"  Button: {status_info['buttonText']}")
                        
                        if status_info['resultCount'] > 0:
                            print(f"✓ Search results found! ({status_info['resultCount']} spots)")
                            
                            # Wait a bit more for map markers to render
                            await asyncio.sleep(2)
                            
                            # Screenshot 3: Search results found
                            screenshot_path = output_dir / f"{base_name}_03_search_results.png"
                            print(f"\n📸 Screenshot 3: Search results found...")
                            await page.screenshot(
                                path=str(screenshot_path),
                                full_page=full_page,
                                type="png"
                            )
                            file_size = screenshot_path.stat().st_size
                            print(f"✓ Saved: {screenshot_path}")
                            print(f"  File size: {file_size / 1024:.2f} KB")
                            print(f"  Found {status_info['resultCount']} spot(s)")
                            
                            # Screenshot 4: Close-up of results list (optional)
                            try:
                                spots_list = await page.query_selector("#spotsList")
                                if spots_list:
                                    await asyncio.sleep(0.5)
                                    screenshot_path = output_dir / f"{base_name}_04_results_list.png"
                                    print(f"\n📸 Screenshot 4: Results list detail...")
                                    await spots_list.screenshot(path=str(screenshot_path), type="png")
                                    file_size = screenshot_path.stat().st_size
                                    print(f"✓ Saved: {screenshot_path}")
                                    print(f"  File size: {file_size / 1024:.2f} KB")
                            except Exception as e:
                                print(f"  Note: Could not capture results list detail: {e}")
                        else:
                            # No results but search completed - might be an error or no results found
                            error_text = status_info['statusText']
                            if 'Error' in error_text or '✗' in error_text:
                                print(f"⚠️  Search failed: {error_text[:200]}")
                            else:
                                print(f"⚠️  Search completed but no results found")
                                print(f"  Status: {error_text[:200]}")
                            
                            # Screenshot 3: After search (with error or no results)
                            await asyncio.sleep(1)
                            screenshot_path = output_dir / f"{base_name}_03_search_after.png"
                            print(f"\n📸 Screenshot 3: After search attempt...")
                            await page.screenshot(
                                path=str(screenshot_path),
                                full_page=full_page,
                                type="png"
                            )
                            file_size = screenshot_path.stat().st_size
                            print(f"✓ Saved: {screenshot_path}")
                            print(f"  File size: {file_size / 1024:.2f} KB")
                            
                            # Check console for errors
                            console_logs = await page.evaluate("""() => {
                                // Try to get console errors if available
                                return 'Console logs not accessible in this context';
                            }""")
                            
                    except Exception as e:
                        # Search might have failed or timed out
                        # Cancel monitoring task
                        monitor_task.cancel()
                        try:
                            await monitor_task
                        except asyncio.CancelledError:
                            pass
                        
                        print(f"⚠️  Search timeout or error: {e}")
                        print("  Taking screenshot anyway...")
                        
                        # Get current status
                        try:
                            status_info = await page.evaluate("""() => {
                                const spotsList = document.getElementById('spotsList');
                                const statusMsg = document.getElementById('apiStatusMessage');
                                return {
                                    resultCount: spotsList ? spotsList.children.length : 0,
                                    statusText: statusMsg ? statusMsg.textContent : '',
                                    statusVisible: statusMsg ? statusMsg.style.display !== 'none' : false
                                };
                            }""")
                            print(f"  Current status: {status_info['statusText'][:200] if status_info['statusText'] else 'No status'}")
                            print(f"  Results: {status_info['resultCount']}")
                        except:
                            pass
                        
                        await asyncio.sleep(2)
                        screenshot_path = output_dir / f"{base_name}_03_search_after.png"
                        print(f"\n📸 Screenshot 3: After search attempt...")
                        await page.screenshot(
                            path=str(screenshot_path),
                            full_page=full_page,
                            type="png"
                        )
                        file_size = screenshot_path.stat().st_size
                        print(f"✓ Saved: {screenshot_path}")
                        print(f"  File size: {file_size / 1024:.2f} KB")
                        
                except Exception as e:
                    print(f"⚠️  Error during search: {e}")
                    print("  Continuing with initial screenshot only...")
            
            print(f"\n✅ Screenshot capture complete!")
            print(f"   Output directory: {output_dir}")
            
        except Exception as e:
            print(f"✗ Error capturing screenshot: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
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
  
  # Capture screenshots including search results
  python capture_screenshot.py --search "Kuala Lumpur" --output screenshot.png
  
  # Multiple screenshots with custom output directory
  python capture_screenshot.py --search "Penang" --output-dir screenshots/
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
    
    parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="Search query to test (e.g., 'Kuala Lumpur'). If provided, will capture multiple screenshots including search results."
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save multiple screenshots (default: same directory as output file)"
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
        wait_for_map=not args.no_wait_map,
        search_query=args.search,
        output_dir=args.output_dir
    ))


if __name__ == "__main__":
    main()

