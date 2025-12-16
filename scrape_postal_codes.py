#!/usr/bin/env python3
"""
Add Malaysian postal codes to malaysia_states_districts.json
Uses known postal code ranges and Wikipedia data if available.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# User agent for Wikipedia
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Known postal code ranges by state (Wikipedia data)
POSTAL_CODE_RANGES = {
    "Johor": {"start": "80000", "end": "86999"},
    "Kedah": {"start": "05000", "end": "09810"},
    "Kelantan": {"start": "15000", "end": "18500"},
    "Malacca": {"start": "75000", "end": "78309"},
    "Negeri Sembilan": {"start": "70000", "end": "73999"},
    "Pahang": {"start": "25000", "end": "28800"},
    "Penang": {"start": "10000", "end": "14400"},
    "Perak": {"start": "30000", "end": "36810"},
    "Perlis": {"start": "01000", "end": "02800"},
    "Sabah": {"start": "88000", "end": "91309"},
    "Sarawak": {"start": "93000", "end": "98859"},
    "Selangor": {"start": "40000", "end": "48300"},
    "Terengganu": {"start": "20000", "end": "24300"},
    "Federal Territory of Kuala Lumpur": {"start": "50000", "end": "60000"},
    "Federal Territory of Labuan": {"start": "87000", "end": "87033"},
    "Federal Territory of Putrajaya": {"start": "62000", "end": "62988"},
}

# Sample postal codes for major cities/districts (from common knowledge)
MAJOR_CITY_POSTAL_CODES = {
    "Johor": {
        "Johor Bahru": ["80000", "81300"],
        "Batu Pahat": ["83000"],
        "Muar": ["84000"],
        "Kluang": ["86000"],
        "Segamat": ["85000"],
        "Kulai": ["81000"],
    },
    "Kedah": {
        "Alor Setar": ["05000", "05400"],
        "Sungai Petani": ["08000"],
        "Kulim": ["09000"],
        "Langkawi": ["07000"],
    },
    "Kelantan": {
        "Kota Bharu": ["15000", "15100"],
        "Pasir Mas": ["17000"],
        "Gua Musang": ["18300"],
    },
    "Malacca": {
        "Malacca City": ["75000", "75300"],
        "Alor Gajah": ["78000"],
        "Jasin": ["77000"],
    },
    "Negeri Sembilan": {
        "Seremban": ["70000", "70100"],
        "Nilai": ["71800"],
        "Port Dickson": ["71000"],
        "Kuala Pilah": ["72000"],
    },
    "Pahang": {
        "Kuantan": ["25000", "25100"],
        "Temerloh": ["28000"],
        "Bentong": ["28700"],
        "Raub": ["27600"],
        "Cameron Highlands": ["39000"],
    },
    "Penang": {
        "George Town": ["10000", "10100", "10200", "10300", "10400"],
        "Butterworth": ["12000", "12100"],
        "Bayan Lepas": ["11900"],
        "Bukit Mertajam": ["14000"],
    },
    "Perak": {
        "Ipoh": ["30000", "30100", "30200", "30300", "30400", "30500", "30600", "30700", "30800", "30900", "31000", "31100", "31200", "31300", "31400", "31500", "31600", "31700", "31800", "31900", "32000"],
        "Taiping": ["34000"],
        "Sitiawan": ["32000"],
        "Teluk Intan": ["36000"],
        "Kuala Kangsar": ["33000"],
        "Kampar": ["31900"],
    },
    "Perlis": {
        "Kangar": ["01000"],
        "Arau": ["02600"],
    },
    "Sabah": {
        "Kota Kinabalu": ["88000", "88100", "88200", "88300", "88400", "88500", "88600", "88700", "88800", "88900"],
        "Sandakan": ["90000", "90100"],
        "Tawau": ["91000"],
        "Lahad Datu": ["91100"],
        "Keningau": ["89000"],
    },
    "Sarawak": {
        "Kuching": ["93000", "93100", "93200", "93300", "93400", "93500", "93600", "93700", "93800", "93900"],
        "Miri": ["98000"],
        "Sibu": ["96000"],
        "Bintulu": ["97000"],
        "Limbang": ["98700"],
    },
    "Selangor": {
        "Shah Alam": ["40000", "40100", "40200", "40300", "40400", "40500", "40600", "40700", "40800", "40900"],
        "Klang": ["41000", "41100", "41200", "41300", "41400", "41500", "41600", "41700", "41800", "41900"],
        "Petaling Jaya": ["46000", "46100", "46200", "46300", "46400", "46500", "46600", "46700", "46800", "46900"],
        "Subang Jaya": ["47500", "47600"],
        "Ampang": ["68000"],
        "Kajang": ["43000"],
    },
    "Terengganu": {
        "Kuala Terengganu": ["20000", "20100", "20200", "20300", "20400", "20500", "20600", "20700", "20800", "20900"],
        "Kemaman": ["24000"],
        "Dungun": ["23000"],
    },
    "Federal Territory of Kuala Lumpur": {
        "Kuala Lumpur": ["50000", "50050", "50100", "50150", "50200", "50250", "50300", "50350", "50400", "50450", "50500", "50550", "50600", "50650", "50700", "50750", "50800", "50850", "50900", "50950", "51000", "51050", "51100", "51150", "51200", "51250", "51300", "51350", "51400", "51450", "51500", "51550", "51600", "51650", "51700", "51750", "51800", "51850", "51900", "51950", "52000", "52050", "52100", "52150", "52200", "52250", "52300", "52350", "52400", "52450", "52500", "52550", "52600", "52650", "52700", "52750", "52800", "52850", "52900", "52950", "53000", "53050", "53100", "53150", "53200", "53250", "53300", "53350", "53400", "53450", "53500", "53550", "53600", "53650", "53700", "53750", "53800", "53850", "53900", "53950", "54000", "54050", "54100", "54150", "54200", "54250", "54300", "54350", "54400", "54450", "54500", "54550", "54600", "54650", "54700", "54750", "54800", "54850", "54900", "54950", "55000", "55050", "55100", "55150", "55200", "55250", "55300", "55350", "55400", "55450", "55500", "55550", "55600", "55650", "55700", "55750", "55800", "55850", "55900", "55950", "56000", "56050", "56100", "56150", "56200", "56250", "56300", "56350", "56400", "56450", "56500", "56550", "56600", "56650", "56700", "56750", "56800", "56850", "56900", "56950", "57000", "57050", "57100", "57150", "57200", "57250", "57300", "57350", "57400", "57450", "57500", "57550", "57600", "57650", "57700", "57750", "57800", "57850", "57900", "57950", "58000", "58050", "58100", "58150", "58200", "58250", "58300", "58350", "58400", "58450", "58500", "58550", "58600", "58650", "58700", "58750", "58800", "58850", "58900", "58950", "59000", "59050", "59100", "59150", "59200", "59250", "59300", "59350", "59400", "59450", "59500", "59550", "59600", "59650", "59700", "59750", "59800", "59850", "59900", "59950", "60000"],
    },
    "Federal Territory of Labuan": {
        "Labuan": ["87000", "87010", "87020", "87030", "87033"],
    },
    "Federal Territory of Putrajaya": {
        "Putrajaya": ["62000", "62100", "62200", "62300", "62400", "62500", "62600", "62700", "62800", "62900", "62988"],
    },
}

def try_scrape_wikipedia() -> Dict[str, List[str]]:
    """
    Try to scrape postal codes from Wikipedia (optional, may fail).
    Returns a dict mapping state names to lists of postal codes.
    """
    postal_data = {}
    
    try:
        url = "https://en.wikipedia.org/wiki/List_of_postal_codes_in_Malaysia"
        logger.info(f"Attempting to scrape from {url}...")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # Simple regex-based extraction (no BeautifulSoup needed)
        content = response.text
        
        # Find postal codes (5 digits) in the content
        postal_codes = re.findall(r'\b\d{5}\b', content)
        
        # Group by state based on ranges
        for state_name, range_info in POSTAL_CODE_RANGES.items():
            start = int(range_info["start"])
            end = int(range_info["end"])
            state_codes = [code for code in postal_codes if start <= int(code) <= end]
            if state_codes:
                postal_data[state_name] = sorted(list(set(state_codes)))[:100]  # Limit to 100 per state
        
        if postal_data:
            logger.info(f"Successfully extracted postal codes from Wikipedia")
    except Exception as e:
        logger.warning(f"Could not scrape Wikipedia: {e}")
    
    return postal_data

def update_json_with_postal_codes(json_file: Path):
    """
    Update the JSON file with postal code information.
    """
    # Load existing JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Try to get postal codes from Wikipedia
    scraped_codes = try_scrape_wikipedia()
    
    # Update each state with postal codes
    for state in data['states']:
        state_name = state['name']
        
        # Get postal code range
        if state_name in POSTAL_CODE_RANGES:
            state['postal_code_range'] = POSTAL_CODE_RANGES[state_name]
        
        # Get scraped postal codes if available
        if state_name in scraped_codes:
            state['postal_codes'] = scraped_codes[state_name]
        
        # Add major city postal codes
        if state_name in MAJOR_CITY_POSTAL_CODES:
            state['major_city_postal_codes'] = MAJOR_CITY_POSTAL_CODES[state_name]
            
            # Create district postal code mapping
            district_postal_codes = {}
            for city, codes in MAJOR_CITY_POSTAL_CODES[state_name].items():
                # Try to match city to district
                for district in state.get('districts', []):
                    if district.lower() in city.lower() or city.lower() in district.lower():
                        if district not in district_postal_codes:
                            district_postal_codes[district] = []
                        district_postal_codes[district].extend(codes)
                        break
                
                # Also check major_cities
                if city in state.get('major_cities', []):
                    # Find corresponding district
                    for district in state.get('districts', []):
                        if district.lower() in city.lower() or city.lower() in district.lower():
                            if district not in district_postal_codes:
                                district_postal_codes[district] = []
                            district_postal_codes[district].extend(codes)
                            break
            
            if district_postal_codes:
                # Remove duplicates and sort
                for district in district_postal_codes:
                    district_postal_codes[district] = sorted(list(set(district_postal_codes[district])))
                state['district_postal_codes'] = district_postal_codes
    
    # Update metadata
    data['metadata']['last_updated'] = time.strftime("%Y-%m-%d")
    data['metadata']['postal_codes_included'] = True
    data['metadata']['postal_code_source'] = "Wikipedia and known ranges"
    
    # Save updated JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Updated {json_file} with postal code data")
    
    # Print summary
    states_with_codes = sum(1 for state in data['states'] if 'postal_codes' in state or 'major_city_postal_codes' in state)
    logger.info(f"Added postal codes to {states_with_codes} states")

def main():
    """Main function"""
    json_file = Path(__file__).parent / "malaysia_states_districts.json"
    
    if not json_file.exists():
        logger.error(f"JSON file not found: {json_file}")
        return
    
    logger.info("Starting postal code update...")
    
    # Update JSON file
    update_json_with_postal_codes(json_file)
    
    logger.info("Postal code update complete!")

if __name__ == "__main__":
    main()
