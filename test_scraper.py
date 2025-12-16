#!/usr/bin/env python3
"""
Test script for web scraper.
Tests on sample URLs and validates output format.
"""

import json
import logging
import sys
from pathlib import Path
from scrape_drone_spots import WebScraper, RobotsChecker, LocationExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_robots_checker():
    """Test robots.txt checker."""
    logger.info("Testing RobotsChecker...")
    checker = RobotsChecker()
    
    # Test a known site
    test_url = "https://www.example.com/page"
    result = checker.can_fetch(test_url)
    logger.info(f"  Can fetch {test_url}: {result}")
    
    logger.info("✓ RobotsChecker test passed\n")
    return True


def test_location_extractor():
    """Test location extraction."""
    logger.info("Testing LocationExtractor...")
    
    # Load config
    config_path = Path("scraper_config.json")
    if not config_path.exists():
        logger.error("scraper_config.json not found")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    extractor = LocationExtractor(config)
    
    # Test coordinate extraction
    test_text = "The location is at 3.1526, 101.7022 which is in Kuala Lumpur."
    coords = extractor.extract_coordinates(test_text)
    logger.info(f"  Extracted coordinates: {coords}")
    assert coords is not None, "Should extract coordinates"
    assert abs(coords[0] - 3.1526) < 0.0001, "Latitude should match"
    assert abs(coords[1] - 101.7022) < 0.0001, "Longitude should match"
    
    # Test location name extraction
    location_names = extractor.extract_location_names(test_text)
    logger.info(f"  Extracted location names: {location_names}")
    assert "Kuala Lumpur" in location_names, "Should find Kuala Lumpur"
    
    logger.info("✓ LocationExtractor test passed\n")
    return True


def test_scraper_on_sample_urls():
    """Test scraper on a few sample URLs."""
    logger.info("Testing scraper on sample URLs...")
    
    # Sample URLs (these should be real URLs that might contain drone spot info)
    # Using example.com as a safe test - in real usage, you'd use actual travel blog URLs
    sample_urls = [
        "https://www.example.com",  # Safe test URL
    ]
    
    config_path = Path("scraper_config.json")
    if not config_path.exists():
        logger.error("scraper_config.json not found")
        return False
    
    scraper = WebScraper(config_path=str(config_path))
    
    # Test blacklist
    test_url = "https://www.facebook.com/somepage"
    is_blacklisted = scraper.is_blacklisted(test_url)
    logger.info(f"  Blacklist check for {test_url}: {is_blacklisted}")
    assert is_blacklisted, "Facebook should be blacklisted"
    
    # Test scraping (on example.com - won't find real locations but tests the flow)
    logger.info("  Note: Testing on example.com (won't find real locations)")
    for url in sample_urls:
        locations = scraper.scrape_page(url)
        logger.info(f"  Found {len(locations)} location(s) on {url}")
    
    logger.info("✓ Scraper test passed\n")
    return True


def test_output_format():
    """Test output JSON format."""
    logger.info("Testing output format...")
    
    # Create sample output
    sample_locations = [
        {
            "name": "Test Location",
            "description": "Test description",
            "latitude": 3.1526,
            "longitude": 101.7022,
            "coordinates_source": "extracted",
            "source_url": "https://example.com/test",
            "source_title": "Test Page",
            "region": "Kuala Lumpur",
            "scraped_date": "2025-01-01T00:00:00",
            "confidence": 0.9
        }
    ]
    
    # Test deduplication
    config_path = Path("scraper_config.json")
    if not config_path.exists():
        logger.error("scraper_config.json not found")
        return False
    
    scraper = WebScraper(config_path=str(config_path))
    unique = scraper.deduplicate_locations(sample_locations * 2)
    logger.info(f"  Deduplication: {len(sample_locations)} unique from {len(sample_locations) * 2} total")
    assert len(unique) == 1, "Should deduplicate correctly"
    
    # Validate structure
    required_fields = [
        "name", "description", "latitude", "longitude",
        "coordinates_source", "source_url", "scraped_date", "confidence"
    ]
    
    for loc in sample_locations:
        for field in required_fields:
            assert field in loc, f"Missing required field: {field}"
    
    logger.info("✓ Output format test passed\n")
    return True


def test_config_loading():
    """Test configuration loading."""
    logger.info("Testing configuration loading...")
    
    config_path = Path("scraper_config.json")
    if not config_path.exists():
        logger.error("scraper_config.json not found")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Check required keys
    required_keys = ["search_queries", "output_file", "rate_limiting"]
    for key in required_keys:
        assert key in config, f"Missing required config key: {key}"
    
    logger.info(f"  Loaded {len(config.get('search_queries', []))} search queries")
    logger.info(f"  Output file: {config.get('output_file')}")
    logger.info("✓ Configuration loading test passed\n")
    return True


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Running web scraper tests")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Robots Checker", test_robots_checker),
        ("Location Extractor", test_location_extractor),
        ("Output Format", test_output_format),
        ("Scraper on Sample URLs", test_scraper_on_sample_urls),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name}: FAILED - {e}", exc_info=True)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())

