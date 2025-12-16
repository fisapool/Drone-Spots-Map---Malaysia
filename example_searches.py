#!/usr/bin/env python3
"""
Example script showing how to search for drone-related repositories.
Run this to get started with common drone-related searches.
"""

from github_repo_search import GitHubRepoSearcher
import json

def run_example_searches():
    """Run example searches related to drone spots and regulations."""
    
    # Initialize searcher (add token if you have one)
    # searcher = GitHubRepoSearcher(token="YOUR_TOKEN_HERE")
    searcher = GitHubRepoSearcher()
    
    # Define search queries related to your needs
    searches = [
        {
            "name": "Drone Regulations",
            "query": "drone regulations malaysia",
            "max": 10
        },
        {
            "name": "No-Fly Zones",
            "query": "no-fly zones drone API",
            "max": 10
        },
        {
            "name": "Drone Mapping",
            "query": "drone mapping openstreetmap",
            "max": 10
        },
        {
            "name": "Flight Planning",
            "query": "drone flight planning",
            "max": 10
        },
        {
            "name": "Airspace Data",
            "query": "airspace data API",
            "max": 10
        },
        {
            "name": "DJI SDK",
            "query": "DJI SDK python",
            "max": 10
        },
        {
            "name": "Google Earth Integration",
            "query": "google earth API python",
            "max": 10
        }
    ]
    
    all_results = {}
    
    for search in searches:
        print(f"\n{'='*80}")
        print(f"Searching: {search['name']}")
        print(f"Query: {search['query']}")
        print(f"{'='*80}\n")
        
        results = searcher.search(
            query=search['query'],
            max_results=search.get('max', 10)
        )
        
        all_results[search['name']] = {
            'query': search['query'],
            'results': results
        }
        
        # Display top 5 results
        searcher.print_results(results, limit=5)
        
        print(f"\nTotal found: {len(results)} repositories")
    
    # Save all results
    try:
        with open("drone_search_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print("All results saved to drone_search_results.json")
        print(f"{'='*80}")
    except (IOError, OSError) as e:
        print(f"\nError saving results: {e}")

if __name__ == "__main__":
    run_example_searches()

