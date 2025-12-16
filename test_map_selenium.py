#!/usr/bin/env python3
"""
Selenium-based test for the drone spots map page.
Tests the map endpoint at http://192.168.0.145:8001/map
"""

import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import sys
import os


class MapPageTest(unittest.TestCase):
    """Test suite for the drone spots map page"""
    
    BASE_URL = "http://192.168.0.145:8001/map"
    _test_counter = 0  # Class variable to track test execution order
    _page_loaded = False  # Track if page has been loaded at least once
    
    @classmethod
    def setUpClass(cls):
        """Set up the WebDriver before all tests"""
        chrome_options = Options()
        # Run in headless mode by default (uncomment to see browser)
        # Check if DISPLAY is set, if not, force headless
        if not os.getenv("DISPLAY"):
            chrome_options.add_argument("--headless")
            print("No DISPLAY environment variable detected, running in headless mode")
        # chrome_options.add_argument("--headless")  # Uncomment to force headless
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # Try to use chromium-browser binary explicitly (for snap installations)
        chromium_paths = [
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium"
        ]
        
        for path in chromium_paths:
            if os.path.exists(path):
                chrome_options.binary_location = path
                break
        
        # Initialize Chrome driver with fallback to Firefox
        cls.driver = None
        try:
            print("Attempting to initialize ChromeDriver...")
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.wait = WebDriverWait(cls.driver, 10)
            print(f"✓ Successfully initialized ChromeDriver with browser: {chrome_options.binary_location or 'default'}")
        except Exception as chrome_error:
            print(f"✗ ChromeDriver initialization failed: {chrome_error}")
            print("\nAttempting to use Firefox as fallback...")
            try:
                firefox_options = FirefoxOptions()
                # firefox_options.add_argument("--headless")  # Uncomment for headless
                cls.driver = webdriver.Firefox(options=firefox_options)
                cls.wait = WebDriverWait(cls.driver, 10)
                print("✓ Successfully initialized Firefox WebDriver")
            except Exception as firefox_error:
                print(f"✗ Firefox WebDriver also failed: {firefox_error}")
                print("\n" + "="*60)
                print("TROUBLESHOOTING STEPS:")
                print("="*60)
                print("1. For Chrome/Chromium:")
                print("   - Install: sudo apt-get install chromium-chromedriver")
                print("   - Check version match: chromedriver --version && chromium-browser --version")
                print("   - For snap Chromium, try: sudo snap connect chromium:audio-record chromium:alsa")
                print("")
                print("2. For Firefox:")
                print("   - Install: sudo apt-get install firefox-geckodriver")
                print("   - Or download: https://github.com/mozilla/geckodriver/releases")
                print("")
                print("3. Display server (for headless):")
                print("   - Install: sudo apt-get install xvfb")
                print("   - Run with: xvfb-run -a python test_map_selenium.py")
                print("")
                print("4. If running in SSH/remote session:")
                print("   - Use X11 forwarding: ssh -X user@host")
                print("   - Or use headless mode (uncomment --headless)")
                print("="*60)
                raise Exception("Failed to initialize any WebDriver. See troubleshooting steps above.")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        if hasattr(cls, 'driver'):
            cls.driver.quit()
    
    def dismiss_alert_if_present(self):
        """Helper method to dismiss any alert dialogs"""
        alert_count = 0
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                alert_count += 1
                print(f"  Note: Alert detected and dismissed: {alert_text[:50]}...")
                alert.accept()
                time.sleep(0.3)
            except:
                break
        
        return alert_count > 0
    
    def setUp(self):
        """Navigate to the map page before each test"""
        MapPageTest._test_counter += 1
        
        # Always navigate to ensure test isolation (each test gets fresh page state)
        # Note: One alert per page load is expected due to WebGL limitations in headless mode
        try:
            self.driver.get(self.BASE_URL)
            MapPageTest._page_loaded = True
        except Exception as e:
            raise
        
        # Wait for page to load and JavaScript to execute
        time.sleep(2)
        
        # Handle any alerts (e.g., WebGL errors in headless mode)
        # Expected: One alert per page load due to WebGL initialization failure in headless mode
        self.dismiss_alert_if_present()
        
        # Wait a bit more and check again for asynchronous alerts
        time.sleep(1)
        self.dismiss_alert_if_present()
    
    def test_page_loads(self):
        """Test that the map page loads successfully"""
        # Dismiss any alerts first
        self.dismiss_alert_if_present()
        
        # Check page title
        self.assertIn("Drone Spots Map", self.driver.title)
        
        # Check that the page loaded (no 404 or error)
        self.assertNotIn("404", self.driver.title)
        self.assertNotIn("Not Found", self.driver.page_source)
    
    def test_header_elements(self):
        """Test that header elements are present"""
        # Check header title
        header = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "header"))
        )
        self.assertIsNotNone(header)
        
        # Check header text
        header_text = header.text
        self.assertIn("Drone Spots", header_text)
    
    def test_view_buttons(self):
        """Test that 2D/3D view buttons are present and clickable"""
        # Find 2D view button
        btn_2d = self.wait.until(
            EC.element_to_be_clickable((By.ID, "btn2D"))
        )
        self.assertIsNotNone(btn_2d)
        self.assertEqual(btn_2d.text, "2D View")
        
        # Find 3D view button
        btn_3d = self.wait.until(
            EC.element_to_be_clickable((By.ID, "btn3D"))
        )
        self.assertIsNotNone(btn_3d)
        self.assertEqual(btn_3d.text, "3D View")
        
        # Test clicking 3D button
        btn_3d.click()
        time.sleep(1)
        # Check that 3D button is now active
        self.assertIn("active", btn_3d.get_attribute("class"))
        
        # Test clicking 2D button
        btn_2d.click()
        time.sleep(1)
        # Check that 2D button is now active
        self.assertIn("active", btn_2d.get_attribute("class"))
    
    def test_globe_container(self):
        """Test that the globe/map container is present"""
        globe_container = self.wait.until(
            EC.presence_of_element_located((By.ID, "globeContainer"))
        )
        self.assertIsNotNone(globe_container)
        
        # Check that container exists and is visible
        self.assertTrue(globe_container.is_displayed())
        
        # Check that container has some content (canvas element)
        # Note: Canvas may not exist in headless mode due to WebGL limitations
        try:
            canvas = globe_container.find_element(By.TAG_NAME, "canvas")
            self.assertIsNotNone(canvas)
        except NoSuchElementException:
            # Canvas might not be present in headless mode (WebGL not available)
            # This is acceptable - the container itself is present which is what we're testing
            print("  Note: Canvas element not found (expected in headless mode without WebGL)")
            # Verify container still exists
            self.assertIsNotNone(globe_container)
    
    def test_sidebar_elements(self):
        """Test that sidebar elements are present"""
        sidebar = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "sidebar"))
        )
        self.assertIsNotNone(sidebar)
        
        # Check API search input
        api_search_input = sidebar.find_element(By.ID, "apiSearchInput")
        self.assertIsNotNone(api_search_input)
        self.assertEqual(api_search_input.get_attribute("placeholder"), 
                        "Enter address or location (e.g., Kuala Lumpur)")
        
        # Check radius input
        radius_input = sidebar.find_element(By.ID, "apiRadiusInput")
        self.assertIsNotNone(radius_input)
        self.assertEqual(radius_input.get_attribute("value"), "15")
        
        # Check API search button
        api_search_btn = sidebar.find_element(By.ID, "apiSearchBtn")
        self.assertIsNotNone(api_search_btn)
        self.assertEqual(api_search_btn.text, "Search API")
        
        # Check JSON input textarea
        json_input = sidebar.find_element(By.ID, "jsonInput")
        self.assertIsNotNone(json_input)
        
        # Check Load & Display Spots button
        load_btn = sidebar.find_element(By.XPATH, "//button[contains(text(), 'Load & Display Spots')]")
        self.assertIsNotNone(load_btn)
        
        # Check search input for filtering
        search_input = sidebar.find_element(By.ID, "searchInput")
        self.assertIsNotNone(search_input)
    
    def test_api_search_input(self):
        """Test API search input functionality"""
        api_search_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "apiSearchInput"))
        )
        
        # Test typing in the input
        test_location = "Kuala Lumpur"
        api_search_input.clear()
        api_search_input.send_keys(test_location)
        
        # Verify the value was set
        self.assertEqual(api_search_input.get_attribute("value"), test_location)
    
    def test_radius_input(self):
        """Test radius input functionality"""
        radius_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "apiRadiusInput"))
        )
        
        # Test changing the radius
        radius_input.clear()
        radius_input.send_keys("20")
        self.assertEqual(radius_input.get_attribute("value"), "20")
    
    def test_json_input(self):
        """Test JSON input textarea"""
        json_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "jsonInput"))
        )
        
        # Test pasting JSON data
        test_json = '{"spots": [{"name": "Test Spot", "latitude": 3.1390, "longitude": 101.6869}]}'
        json_input.clear()
        json_input.send_keys(test_json)
        
        # Verify the value was set
        self.assertIn("Test Spot", json_input.get_attribute("value"))
    
    def test_load_spots_button(self):
        """Test Load & Display Spots button is clickable"""
        load_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Load & Display Spots')]"))
        )
        self.assertIsNotNone(load_btn)
        
        # Button should be clickable (not disabled)
        self.assertTrue(load_btn.is_enabled())
    
    def test_search_filter_input(self):
        """Test search filter input"""
        search_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "searchInput"))
        )
        
        # Test typing in the search input
        test_query = "beach"
        search_input.clear()
        search_input.send_keys(test_query)
        
        # Verify the value was set
        self.assertEqual(search_input.get_attribute("value"), test_query)
    
    def test_page_responsive(self):
        """Test that page elements are properly laid out"""
        # Check that header is visible
        header = self.driver.find_element(By.CLASS_NAME, "header")
        self.assertTrue(header.is_displayed())
        
        # Check that container is present
        container = self.driver.find_element(By.CLASS_NAME, "container")
        self.assertTrue(container.is_displayed())
        
        # Check that sidebar is present
        sidebar = self.driver.find_element(By.CLASS_NAME, "sidebar")
        self.assertTrue(sidebar.is_displayed())
    
    def test_status_messages_exist(self):
        """Test that status message elements exist (even if hidden)"""
        # Check API status message element exists
        api_status = self.driver.find_element(By.ID, "apiStatusMessage")
        self.assertIsNotNone(api_status)
        
        # Check general status message element exists
        status_message = self.driver.find_element(By.ID, "statusMessage")
        self.assertIsNotNone(status_message)
    
    def test_stats_section_exists(self):
        """Test that stats section exists"""
        stats = self.driver.find_element(By.ID, "stats")
        self.assertIsNotNone(stats)
        
        # Check stat elements exist
        total_spots = stats.find_element(By.ID, "totalSpots")
        avg_safety = stats.find_element(By.ID, "avgSafety")
        
        self.assertIsNotNone(total_spots)
        self.assertIsNotNone(avg_safety)


if __name__ == "__main__":
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(MapPageTest)
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

