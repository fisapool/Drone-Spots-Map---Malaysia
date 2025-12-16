#!/bin/bash
# Script to run Selenium tests for the map page

echo "========================================="
echo "Running Selenium Tests for Map Page"
echo "========================================="
echo ""

# Check for display server
if [ -z "$DISPLAY" ] && ! command -v xvfb-run &> /dev/null; then
    echo "Warning: No display server detected and xvfb-run not available"
    echo "For headless testing, install: sudo apt-get install xvfb"
    echo "Or run with: xvfb-run -a $0"
    echo ""
fi

# Check if ChromeDriver is installed
if ! command -v chromedriver &> /dev/null; then
    echo "Warning: ChromeDriver not found in PATH"
    echo "Please install ChromeDriver:"
    echo "  Ubuntu/Debian: sudo apt-get install chromium-chromedriver"
    echo "  Or download from: https://chromedriver.chromium.org/"
    echo ""
else
    echo "✓ ChromeDriver found: $(chromedriver --version 2>/dev/null | head -1)"
fi

# Check if Chrome/Chromium is installed
if command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium found: $(chromium-browser --version 2>/dev/null | head -1)"
elif command -v google-chrome &> /dev/null; then
    echo "✓ Chrome found: $(google-chrome --version 2>/dev/null | head -1)"
elif command -v chromium &> /dev/null; then
    echo "✓ Chromium (snap) found: $(chromium --version 2>/dev/null | head -1)"
else
    echo "Warning: Chrome/Chromium browser not found"
    echo "Please install Chrome or Chromium browser"
    echo ""
fi

# Check for Firefox/GeckoDriver as fallback
if command -v geckodriver &> /dev/null; then
    echo "✓ GeckoDriver found: $(geckodriver --version 2>/dev/null | head -1)"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q selenium>=4.15.0

# Run the tests
echo ""
echo "Running tests..."
echo "Target URL: http://192.168.0.145:8001/map"
echo ""

# Check if we should run headless
if [ "$1" == "--headless" ] || [ -z "$DISPLAY" ]; then
    if command -v xvfb-run &> /dev/null; then
        echo "Running in headless mode with xvfb..."
        xvfb-run -a python test_map_selenium.py
    else
        echo "Running tests (no display server - may fail if browser needs GUI)..."
        python test_map_selenium.py
    fi
else
    python test_map_selenium.py
fi

EXIT_CODE=$?

echo ""
echo "========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Tests completed successfully"
else
    echo "✗ Tests failed with exit code: $EXIT_CODE"
fi
echo "========================================="

exit $EXIT_CODE

