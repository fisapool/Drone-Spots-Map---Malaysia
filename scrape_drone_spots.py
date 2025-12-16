#!/usr/bin/env python3
"""
Web Scraper for Drone Spots Discovery
Searches for and extracts drone spot information from travel blogs.
"""

import json
import re
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from googlesearch import search as google_search
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check robots.txt compliance before scraping."""
    
    def __init__(self):
        self.robots_cache = {}
        self.user_agent = "drone_spots_scraper/1.0"
    
    def can_fetch(self, url: str, user_agent: str = None) -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string (default: self.user_agent)
        
        Returns:
            True if allowed, False if disallowed, True if robots.txt unavailable
        """
        if user_agent is None:
            user_agent = self.user_agent
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = urljoin(base_url, "/robots.txt")
        
        # Check cache
        cache_key = (base_url, user_agent)
        if cache_key in self.robots_cache:
            rp = self.robots_cache[cache_key]
        else:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                self.robots_cache[cache_key] = rp
            except Exception as e:
                logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                # If robots.txt is unavailable, assume allowed
                return True
        
        return rp.can_fetch(user_agent, url)


class GoogleSearchModule:
    """Search Google for relevant travel blog pages with improved strategy."""
    
    def __init__(self, max_results: int = 20, language: str = "en", region: str = "my"):
        self.max_results = max_results
        self.language = language
        self.region = region
        self.search_cache = {}  # Cache search results
    
    def search(self, query: str, num_results: int = None, use_cache: bool = True) -> List[str]:
        """
        Search Google for pages related to the query with improved error handling.
        
        Args:
            query: Search query
            num_results: Number of results to return (default: self.max_results)
            use_cache: Whether to use cached results
        
        Returns:
            List of URLs
        """
        if num_results is None:
            num_results = self.max_results
        
        # Check cache
        if use_cache and query in self.search_cache:
            logger.debug(f"Using cached results for: {query}")
            return self.search_cache[query][:num_results]
        
        urls = []
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Searching Google for: {query} (attempt {attempt + 1}/{max_attempts})")
                
                # Add delay between attempts
                if attempt > 0:
                    delay = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                # Use googlesearch-python library with timeout
                search_results = google_search(
                    query,
                    num_results=num_results * 2,  # Get more to account for filtering
                    lang=self.language,
                    region=self.region,
                    timeout=10,
                    sleep_interval=1  # Be respectful with delays
                )
                
                for url in search_results:
                    if url and url not in urls:
                        urls.append(url)
                        if len(urls) >= num_results:
                            break
                
                if urls:
                    logger.info(f"Found {len(urls)} URLs for query: {query}")
                    # Cache successful results
                    if use_cache:
                        self.search_cache[query] = urls
                    break
                else:
                    logger.warning(f"No URLs found for query: {query} (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.warning(f"Error searching Google for '{query}' (attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    logger.error(f"Failed to search Google for '{query}' after {max_attempts} attempts")
        
        return urls
    
    def search_with_fallback(self, query: str, num_results: int = None) -> List[str]:
        """
        Search with multiple query variations as fallback.
        
        Args:
            query: Base search query
            num_results: Number of results to return
        
        Returns:
            List of unique URLs
        """
        all_urls = []
        
        # Try original query
        urls = self.search(query, num_results)
        all_urls.extend(urls)
        
        # If no results, try variations
        if not urls:
            variations = [
                f"{query} site:blogspot.com",
                f"{query} site:wordpress.com",
                f"{query} site:tumblr.com",
                f"{query} travel blog",
                f"{query} guide"
            ]
            
            for variation in variations[:2]:  # Try first 2 variations
                variation_num = (num_results // 2) if num_results else 10
                urls = self.search(variation, variation_num)
                all_urls.extend(urls)
                if len(all_urls) >= num_results:
                    break
                time.sleep(2)  # Delay between variation searches
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls[:num_results] if num_results else unique_urls


class LocationExtractor:
    """Extract location information from HTML content."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.malaysian_cities = config.get("location_patterns", {}).get("malaysian_cities", [])
        self.coordinate_patterns = config.get("location_patterns", {}).get("coordinate_patterns", [])
        self.geocoder = None
        if config.get("geocoding", {}).get("use_nominatim", True):
            user_agent = config.get("geocoding", {}).get("nominatim_user_agent", "drone_spots_scraper/1.0")
            self.geocoder = Nominatim(user_agent=user_agent)
    
    def extract_coordinates(self, text: str, soup: BeautifulSoup = None) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from text and HTML using multiple strategies.
        
        Args:
            text: Text to search for coordinates
            soup: BeautifulSoup object for meta tag extraction
        
        Returns:
            Tuple of (latitude, longitude) or None
        """
        # Strategy 1: Check meta tags for coordinates
        if soup:
            # Check geo.position meta tag
            geo_pos = soup.find('meta', attrs={'name': 'geo.position'})
            if geo_pos and geo_pos.get('content'):
                try:
                    coords = geo_pos['content'].split(';')
                    if len(coords) == 2:
                        lat, lon = float(coords[0].strip()), float(coords[1].strip())
                        if 0 <= lat <= 7 and 99 <= lon <= 120:
                            return (lat, lon)
                except (ValueError, IndexError):
                    pass
            
            # Check JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Check for geo coordinates
                        if 'geo' in data:
                            geo = data['geo']
                            if isinstance(geo, dict):
                                lat = geo.get('latitude') or geo.get('@latitude')
                                lon = geo.get('longitude') or geo.get('@longitude')
                                if lat and lon:
                                    lat, lon = float(lat), float(lon)
                                    if 0 <= lat <= 7 and 99 <= lon <= 120:
                                        return (lat, lon)
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
        
        # Strategy 2: Pattern 1 - Decimal degrees (e.g., "3.1526, 101.7022" or "3.1526 101.7022")
        pattern1 = r'(\d{1,2}\.\d{4,6})[,\s]+(\d{2,3}\.\d{4,6})'
        matches = re.findall(pattern1, text)
        if matches:
            for match in matches:
                try:
                    lat, lon = float(match[0]), float(match[1])
                    # Validate: Malaysia is roughly 0-7°N, 99-120°E
                    if 0 <= lat <= 7 and 99 <= lon <= 120:
                        return (lat, lon)
                except ValueError:
                    continue
        
        # Strategy 3: Pattern 2 - Degrees minutes seconds (e.g., "3°9'15\"N, 101°42'8\"E")
        pattern2 = r"(\d{1,2})°(\d{1,2})'(\d{1,2})\"[\s]*([NS])[,\s]+(\d{2,3})°(\d{1,2})'(\d{1,2})\"[\s]*([EW])"
        matches = re.findall(pattern2, text)
        if matches:
            for match in matches:
                try:
                    lat_d, lat_m, lat_s, lat_dir = match[0:4]
                    lon_d, lon_m, lon_s, lon_dir = match[4:8]
                    lat = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
                    lon = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600
                    if lat_dir == 'S':
                        lat = -lat
                    if lon_dir == 'W':
                        lon = -lon
                    # Validate: Malaysia is roughly 0-7°N, 99-120°E
                    if 0 <= lat <= 7 and 99 <= lon <= 120:
                        return (lat, lon)
                except (ValueError, IndexError):
                    continue
        
        # Strategy 4: Google Maps URL pattern
        maps_pattern = r'(?:maps\.google\.|google\.com/maps).*[?&]q=([+-]?\d+\.\d+),([+-]?\d+\.\d+)'
        matches = re.findall(maps_pattern, text)
        if matches:
            for match in matches:
                try:
                    lat, lon = float(match[0]), float(match[1])
                    if 0 <= lat <= 7 and 99 <= lon <= 120:
                        return (lat, lon)
                except ValueError:
                    continue
        
        return None
    
    def extract_location_names(self, text: str, soup: BeautifulSoup = None) -> List[str]:
        """
        Extract Malaysian location names from text and HTML with improved patterns.
        
        Args:
            text: Text to search
            soup: BeautifulSoup object for meta tag extraction
        
        Returns:
            List of found location names (ordered by frequency/importance)
        """
        found_locations = []
        text_lower = text.lower()
        
        # Strategy 1: Check meta tags and structured data
        if soup:
            # Check location meta tags
            location_meta = soup.find('meta', attrs={'name': re.compile(r'location|place|address', re.I)})
            if location_meta and location_meta.get('content'):
                meta_text = location_meta['content']
                for city in self.malaysian_cities:
                    if city.lower() in meta_text.lower() and city not in found_locations:
                        found_locations.append(city)
        
        # Strategy 2: Extract from text with context awareness
        location_scores = {}
        for city in self.malaysian_cities:
            city_lower = city.lower()
            # Check for exact word matches (avoid partial matches)
            pattern = r'\b' + re.escape(city_lower) + r'\b'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Score based on frequency and context
                score = len(matches)
                # Boost score if near drone-related keywords
                drone_keywords = ['drone', 'aerial', 'flying', 'spot', 'location', 'photography', 'video']
                for keyword in drone_keywords:
                    if keyword in text_lower:
                        # Check if city appears near keyword (within 50 chars)
                        keyword_pos = text_lower.find(keyword)
                        if keyword_pos != -1:
                            context = text_lower[max(0, keyword_pos-50):keyword_pos+50]
                            if city_lower in context:
                                score += 2
                
                location_scores[city] = score
        
        # Sort by score and return
        sorted_locations = sorted(location_scores.items(), key=lambda x: x[1], reverse=True)
        found_locations.extend([loc for loc, score in sorted_locations])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_locations = []
        for loc in found_locations:
            loc_lower = loc.lower()
            if loc_lower not in seen:
                seen.add(loc_lower)
                unique_locations.append(loc)
        
        return unique_locations
    
    def geocode_location(self, location_name: str, timeout: int = 10) -> Optional[Tuple[float, float]]:
        """
        Geocode a location name to coordinates using Nominatim.
        
        Args:
            location_name: Name of the location
            timeout: Timeout in seconds
        
        Returns:
            Tuple of (latitude, longitude) or None
        """
        if not self.geocoder:
            return None
        
        try:
            # Add "Malaysia" to improve accuracy
            query = f"{location_name}, Malaysia"
            location = self.geocoder.geocode(query, timeout=timeout, exactly_one=True)
            if location:
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding error for '{location_name}': {e}")
        except Exception as e:
            logger.warning(f"Unexpected geocoding error for '{location_name}': {e}")
        
        return None
    
    def extract_locations(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """
        Extract location data from parsed HTML.
        
        Args:
            soup: BeautifulSoup object
            url: Source URL
        
        Returns:
            List of location dictionaries
        """
        locations = []
        
        # Get page title
        title_elem = soup.find('title')
        page_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Get main content
        content_selectors = [
            'article', '.post-content', '.entry-content', 'main', '.content',
            '[role="main"]', '.main-content'
        ]
        content_text = ""
        content_elem = None
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            # Fallback: get body text
            body = soup.find('body')
            if body:
                content_elem = body
        
        if content_elem:
            content_text = content_elem.get_text(separator=' ', strip=True)
        
        # Also extract from meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content_text = meta_desc['content'] + " " + content_text
        
        # Extract coordinates (pass soup for meta tag checking)
        coords = self.extract_coordinates(content_text, soup)
        coordinates_source = "extracted" if coords else None
        
        # Extract location names (pass soup for meta tag checking)
        location_names = self.extract_location_names(content_text, soup)
        
        # If we have coordinates, create a location entry
        if coords:
            # Try to find a name for this location
            name = "Unnamed Location"
            if location_names:
                name = location_names[0]
            elif page_title:
                # Extract location from title if possible
                title_locations = self.extract_location_names(page_title)
                if title_locations:
                    name = title_locations[0]
            
            # Extract description (first 500 chars of content)
            description = content_text[:500].strip() if content_text else ""
            if not description:
                description = f"Drone spot location found at {url}"
            
            locations.append({
                "name": name,
                "description": description,
                "latitude": coords[0],
                "longitude": coords[1],
                "coordinates_source": coordinates_source,
                "source_url": url,
                "source_title": page_title,
                "region": location_names[0] if location_names else None,
                "scraped_date": datetime.now().isoformat(),
                "confidence": 0.9 if location_names else 0.7
            })
        
        # If we have location names but no coordinates, try to geocode
        elif location_names:
            for loc_name in location_names[:3]:  # Limit to first 3 to avoid too many geocoding calls
                coords = self.geocode_location(loc_name)
                if coords:
                    # Extract description
                    description = content_text[:500].strip() if content_text else ""
                    if not description:
                        description = f"Drone spot location: {loc_name}"
                    
                    locations.append({
                        "name": loc_name,
                        "description": description,
                        "latitude": coords[0],
                        "longitude": coords[1],
                        "coordinates_source": "geocoded",
                        "source_url": url,
                        "source_title": page_title,
                        "region": loc_name,
                        "scraped_date": datetime.now().isoformat(),
                        "confidence": 0.8
                    })
                    break  # Only geocode the first matching location
        
        # If no coordinates or location names, but content suggests drone spots
        if not locations and content_text:
            # Enhanced drone-related keyword detection
            drone_keywords = [
                'drone', 'aerial', 'flying', 'spot', 'location', 'photography',
                'quadcopter', 'uav', 'fpv', 'dji', 'mavic', 'phantom',
                'aerial photography', 'drone video', 'drone footage',
                'best place to fly', 'drone friendly', 'legal to fly'
            ]
            
            # Count keyword matches for confidence scoring
            keyword_matches = sum(1 for keyword in drone_keywords if keyword in content_text.lower())
            
            # Check if content is drone-related (at least 2 keywords or strong indicators)
            is_drone_related = (
                keyword_matches >= 2 or
                any(phrase in content_text.lower() for phrase in ['drone spot', 'aerial view', 'fly drone'])
            )
            
            if is_drone_related:
                # Try to extract any location mention even if not in our list
                # Look for common location patterns
                location_patterns = [
                    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:beach|hill|mountain|park|tower|bridge|temple|mosque|lake|river)',
                    r'(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                ]
                
                extracted_region = None
                for pattern in location_patterns:
                    matches = re.findall(pattern, content_text)
                    if matches:
                        extracted_region = matches[0]
                        break
                
                # Calculate confidence based on keyword density and location presence
                confidence = min(0.5, 0.2 + (keyword_matches * 0.05))
                if extracted_region:
                    confidence += 0.1
                
                # Create entry with improved description extraction
                # Try to get a better description (first meaningful paragraph)
                description = ""
                paragraphs = content_elem.find_all(['p', 'div']) if content_elem else []
                for para in paragraphs[:3]:  # Check first 3 paragraphs
                    para_text = para.get_text(strip=True)
                    if len(para_text) > 50 and any(kw in para_text.lower() for kw in drone_keywords[:5]):
                        description = para_text[:500]
                        break
                
                if not description:
                    description = content_text[:500].strip()
                
                locations.append({
                    "name": page_title or extracted_region or "Potential Drone Spot",
                    "description": description,
                    "latitude": None,
                    "longitude": None,
                    "coordinates_source": "none",
                    "source_url": url,
                    "source_title": page_title,
                    "region": extracted_region,
                    "scraped_date": datetime.now().isoformat(),
                    "confidence": confidence,
                    "keyword_matches": keyword_matches
                })
        
        return locations


class WebScraper:
    """Main web scraper class."""
    
    def __init__(self, config_path: str = "scraper_config.json"):
        """Initialize scraper with configuration."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.robots_checker = RobotsChecker()
        self.search_module = GoogleSearchModule(
            max_results=self.config.get("google_search", {}).get("max_results_per_query", 20),
            language=self.config.get("google_search", {}).get("language", "en"),
            region=self.config.get("google_search", {}).get("region", "my")
        )
        self.use_fallback_search = self.config.get("google_search", {}).get("use_fallback", True)
        self.location_extractor = LocationExtractor(self.config)
        
        self.rate_limit_delay = self.config.get("rate_limiting", {}).get("delay_between_requests", 3)
        self.page_delay = self.config.get("rate_limiting", {}).get("delay_between_pages", 2)
        self.max_retries = self.config.get("rate_limiting", {}).get("max_retries", 3)
        self.timeout = self.config.get("rate_limiting", {}).get("timeout", 30)
        self.user_agents = self.config.get("user_agents", [])
        self.blacklist_domains = set(self.config.get("blacklist_domains", []))
        self.blacklist_urls = set(self.config.get("blacklist_urls", []))
        
        self.scraped_locations = []
        self.processed_urls = set()
    
    def is_blacklisted(self, url: str) -> bool:
        """Check if URL is in blacklist."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check domain blacklist
        for blacklisted in self.blacklist_domains:
            if blacklisted.lower() in domain:
                return True
        
        # Check URL blacklist
        url_lower = url.lower()
        for blacklisted in self.blacklist_urls:
            if blacklisted.lower() in url_lower:
                return True
        
        return False
    
    def get_user_agent(self) -> str:
        """Get a random user agent."""
        import random
        if self.user_agents:
            return random.choice(self.user_agents)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page.
        
        Args:
            url: URL to fetch
        
        Returns:
            BeautifulSoup object or None if failed
        """
        headers = {
            'User-Agent': self.get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.content, 'lxml')
                return soup
            
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error fetching {url}: {e} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        
        return None
    
    def scrape_page(self, url: str) -> List[Dict]:
        """
        Scrape a single page for location data.
        
        Args:
            url: URL to scrape
        
        Returns:
            List of location dictionaries
        """
        if url in self.processed_urls:
            return []
        
        if self.is_blacklisted(url):
            logger.info(f"Skipping blacklisted URL: {url}")
            return []
        
        # Check robots.txt
        if not self.robots_checker.can_fetch(url, self.get_user_agent()):
            logger.info(f"Robots.txt disallows scraping: {url}")
            return []
        
        logger.info(f"Scraping: {url}")
        
        soup = self.fetch_page(url)
        if not soup:
            return []
        
        # Extract locations
        locations = self.location_extractor.extract_locations(soup, url)
        
        self.processed_urls.add(url)
        
        if locations:
            logger.info(f"Found {len(locations)} location(s) on {url}")
        else:
            logger.debug(f"No locations found on {url}")
        
        # Rate limiting
        time.sleep(self.page_delay)
        
        return locations
    
    def search_and_scrape(self) -> List[Dict]:
        """
        Search for pages and scrape them.
        
        Returns:
            List of all found locations
        """
        all_locations = []
        search_queries = self.config.get("search_queries", [])
        
        for query in search_queries:
            logger.info(f"\n=== Processing query: {query} ===")
            
            # Search for URLs (use fallback if enabled)
            if self.use_fallback_search:
                urls = self.search_module.search_with_fallback(query)
            else:
                urls = self.search_module.search(query)
            
            # Filter and scrape each URL
            for url in urls:
                if self.is_blacklisted(url):
                    continue
                
                locations = self.scrape_page(url)
                all_locations.extend(locations)
                
                # Rate limiting between pages
                time.sleep(self.rate_limit_delay)
            
            # Delay between queries
            time.sleep(self.rate_limit_delay * 2)
        
        return all_locations
    
    def deduplicate_locations(self, locations: List[Dict]) -> List[Dict]:
        """
        Remove duplicate locations based on coordinates or name+region.
        
        Args:
            locations: List of location dictionaries
        
        Returns:
            Deduplicated list
        """
        seen = set()
        unique_locations = []
        
        for loc in locations:
            # Create a key for deduplication
            if loc.get("latitude") and loc.get("longitude"):
                # Use coordinates (rounded to 4 decimal places ~11m precision)
                key = (
                    round(loc["latitude"], 4),
                    round(loc["longitude"], 4)
                )
            else:
                # Use name + region
                key = (
                    loc.get("name", "").lower().strip(),
                    loc.get("region", "").lower().strip()
                )
            
            if key not in seen:
                seen.add(key)
                unique_locations.append(loc)
            else:
                logger.debug(f"Skipping duplicate: {loc.get('name', 'Unknown')}")
        
        return unique_locations
    
    def save_results(self, locations: List[Dict], output_file: str = None):
        """
        Save scraped locations to JSON file.
        
        Args:
            locations: List of location dictionaries
            output_file: Output file path (default: from config)
        """
        if output_file is None:
            output_file = self.config.get("output_file", "scraped_drone_spots.json")
        
        # Deduplicate
        unique_locations = self.deduplicate_locations(locations)
        
        # Prepare output structure
        output = {
            "metadata": {
                "scrape_date": datetime.now().isoformat(),
                "total_spots": len(unique_locations),
                "sources": list(self.processed_urls),
                "queries_processed": len(self.config.get("search_queries", []))
            },
            "spots": unique_locations
        }
        
        # Save to file
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Saved {len(unique_locations)} unique locations to {output_file}")
        logger.info(f"   Processed {len(self.processed_urls)} URLs")
    
    def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """
        Scrape a list of URLs directly (useful for known URLs).
        
        Args:
            urls: List of URLs to scrape
        
        Returns:
            List of location dictionaries
        """
        all_locations = []
        
        logger.info(f"Scraping {len(urls)} URLs directly...")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Processing: {url}")
            locations = self.scrape_page(url)
            all_locations.extend(locations)
            
            # Rate limiting
            if i < len(urls):
                time.sleep(self.rate_limit_delay)
        
        return all_locations
    
    def run(self, output_file: str = None, urls: List[str] = None):
        """
        Run the complete scraping process.
        
        Args:
            output_file: Optional output file path
            urls: Optional list of URLs to scrape directly (skips search)
        """
        logger.info("Starting web scraper for drone spots...")
        logger.info(f"Configuration loaded from: scraper_config.json")
        
        if urls:
            # Scrape provided URLs directly
            logger.info(f"Scraping {len(urls)} provided URLs...")
            locations = self.scrape_urls(urls)
        else:
            # Search and scrape
            locations = self.search_and_scrape()
        
        # Save results
        self.save_results(locations, output_file)
        
        logger.info("\n✅ Scraping complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web scraper for drone spots discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (uses scraper_config.json)
  python scrape_drone_spots.py
  
  # Custom config file
  python scrape_drone_spots.py --config custom_config.json
  
  # Custom output file
  python scrape_drone_spots.py --output my_spots.json
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="scraper_config.json",
        help="Path to configuration file (default: scraper_config.json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: from config)"
    )
    
    parser.add_argument(
        "--urls", "-u",
        nargs="+",
        default=None,
        help="Direct URLs to scrape (skips Google search)"
    )
    
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback search variations"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1
    
    # Run scraper
    scraper = WebScraper(config_path=args.config)
    
    # Disable fallback if requested
    if args.no_fallback:
        scraper.use_fallback_search = False
    
    scraper.run(output_file=args.output, urls=args.urls)
    
    return 0


if __name__ == "__main__":
    exit(main())

