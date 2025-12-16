# Selenium Test Suite for Map Page

## Overview
Comprehensive Selenium-based test suite for the drone spots map page at `http://192.168.0.145:8001/map`.

## Test Coverage
The test suite includes 13 test cases covering:
- ✅ Page loading and title verification
- ✅ Header elements presence
- ✅ 2D/3D view button functionality
- ✅ Globe/map container presence
- ✅ Sidebar elements (API search, radius input, JSON input, buttons)
- ✅ Input field interactions
- ✅ Responsive layout checks
- ✅ Status message elements
- ✅ Stats section verification

## Prerequisites

### Required Software
1. **Python 3.12+** with virtual environment
2. **ChromeDriver** (must match Chromium version)
3. **Chromium/Chrome browser**

### Installation

```bash
# Install ChromeDriver (Ubuntu/Debian)
sudo apt-get install chromium-chromedriver

# Verify versions match
chromedriver --version
chromium-browser --version

# Install Python dependencies
pip install -r requirements.txt
```

## Running Tests

### Option 1: Using the Test Runner Script
```bash
./run_map_tests.sh
```

### Option 2: Direct Python Execution
```bash
# With display (visible browser)
python test_map_selenium.py

# Headless mode (no display required)
DISPLAY= python test_map_selenium.py

# Or using xvfb for headless
xvfb-run -a python test_map_selenium.py
```

### Option 3: Using Virtual Environment
```bash
source venv/bin/activate
python test_map_selenium.py
```

## Test Configuration

### Base URL
Default: `http://192.168.0.145:8001/map`

To change the URL, modify the `BASE_URL` constant in `test_map_selenium.py`:
```python
BASE_URL = "http://your-url:port/map"
```

### Headless Mode
The test automatically detects if a display server is available:
- **With DISPLAY**: Runs with visible browser
- **Without DISPLAY**: Automatically runs in headless mode

To force headless mode, uncomment this line in `test_map_selenium.py`:
```python
chrome_options.add_argument("--headless")
```

## Known Issues & Solutions

### WebGL Errors in Headless Mode
The map uses WebGL for 3D rendering, which may not work in headless mode. The tests handle this gracefully by:
- Automatically dismissing WebGL error alerts
- Verifying container presence even if canvas isn't rendered
- All tests pass successfully despite WebGL limitations

### ChromeDriver Version Mismatch
If you see "session not created" errors:
```bash
# Check versions
chromedriver --version
chromium-browser --version

# They should match (e.g., both 143.x.x.x)
# If not, reinstall:
sudo apt-get remove chromium-chromedriver
sudo apt-get install chromium-chromedriver
```

### Firefox Fallback
The test suite includes automatic fallback to Firefox if Chrome fails:
- Install GeckoDriver: `sudo apt-get install firefox-geckodriver`
- Or download from: https://github.com/mozilla/geckodriver/releases

## Test Results

### Expected Output
```
No DISPLAY environment variable detected, running in headless mode
Attempting to initialize ChromeDriver...
✓ Successfully initialized ChromeDriver with browser: /usr/bin/chromium-browser
  Note: Alert detected and dismissed: Error initializing map: Error creating WebGL conte...
...
----------------------------------------------------------------------
Ran 13 tests in 38.004s

OK
```

### Exit Codes
- `0`: All tests passed
- `1`: One or more tests failed

## Troubleshooting

### "ChromeDriver not found"
```bash
sudo apt-get install chromium-chromedriver
export PATH=$PATH:/usr/bin
```

### "Chrome instance exited"
- Check ChromeDriver and Chromium versions match
- Try running with visible browser (set DISPLAY)
- For snap Chromium, may need permissions: `sudo snap connect chromium:audio-record chromium:alsa`

### "No display server"
- Install xvfb: `sudo apt-get install xvfb`
- Run with: `xvfb-run -a python test_map_selenium.py`
- Or use headless mode (automatic when DISPLAY not set)

## CI/CD Integration

The test suite is designed for CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Selenium Tests
  run: |
    sudo apt-get install -y chromium-chromedriver xvfb
    xvfb-run -a python test_map_selenium.py
```

## Files

- `test_map_selenium.py` - Main test suite
- `run_map_tests.sh` - Test runner script with dependency checks
- `requirements.txt` - Python dependencies (includes selenium)

## Notes

- Tests use WebDriverWait for reliable element detection
- Alert dialogs are automatically handled
- WebGL limitations in headless mode are gracefully handled
- All tests are isolated and can run independently
- Test timeout: 10 seconds per element wait

