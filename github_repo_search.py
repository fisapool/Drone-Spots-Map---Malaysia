#!/usr/bin/env python3
"""
GitHub Repository Search Script
Searches GitHub repositories based on keywords and filters results.
"""

import requests
import json
import sys
from typing import List, Dict, Optional
from datetime import datetime


class GitHubRepoSearcher:
    """Search GitHub repositories using the GitHub API."""
    
    BASE_URL = "https://api.github.com/search/repositories"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the searcher.
        
        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            # Support both classic tokens (token) and fine-grained tokens (Bearer)
            if token.startswith("ghp_") or token.startswith("gho_") or token.startswith("ghu_"):
                self.headers["Authorization"] = f"Bearer {token}"
            else:
                self.headers["Authorization"] = f"token {token}"
    
    def search(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
        max_results: Optional[int] = None
    ) -> List[Dict]:
        """
        Search GitHub repositories.
        
        Args:
            query: Search query (e.g., "drone regulations", "no-fly zones")
            sort: Sort by "stars", "forks", "help-wanted-issues", "updated"
            order: "asc" or "desc"
            per_page: Results per page (max 100)
            max_results: Maximum number of results to return (None for all)
        
        Returns:
            List of repository dictionaries
        """
        all_results = []
        page = 1
        
        while True:
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": min(per_page, 100),
                "page": page
            }
            
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                
                # Handle rate limiting
                if response.status_code == 403:
                    rate_limit = response.headers.get("X-RateLimit-Remaining", "0")
                    reset_time = response.headers.get("X-RateLimit-Reset", "0")
                    print(f"Rate limit exceeded. Remaining: {rate_limit}", file=sys.stderr)
                    if reset_time != "0":
                        reset_dt = datetime.fromtimestamp(int(reset_time))
                        print(f"Rate limit resets at: {reset_dt}", file=sys.stderr)
                    break
                
                if response.status_code == 429:
                    print("Too many requests. Please wait before trying again.", file=sys.stderr)
                    break
                
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if "message" in data and "items" not in data:
                    print(f"API Error: {data.get('message', 'Unknown error')}", file=sys.stderr)
                    break
                
                if "items" not in data:
                    break
                
                items = data["items"]
                if not items:
                    break
                
                all_results.extend(items)
                
                # Check if we've reached max_results
                if max_results and len(all_results) >= max_results:
                    all_results = all_results[:max_results]
                    break
                
                # Check if there are more pages
                if len(items) < per_page:
                    break
                
                page += 1
                
                # Rate limiting: be respectful
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                if remaining < 10:
                    print(f"Warning: Rate limit low ({remaining} remaining)")
                    break
                    
            except requests.exceptions.Timeout:
                print("Request timeout. Please try again later.", file=sys.stderr)
                break
            except requests.exceptions.RequestException as e:
                print(f"Error searching GitHub: {e}", file=sys.stderr)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        if "message" in error_data:
                            print(f"API message: {error_data['message']}", file=sys.stderr)
                    except:
                        pass
                break
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing response: {e}", file=sys.stderr)
                break
        
        return all_results
    
    def format_result(self, repo: Dict) -> str:
        """Format a repository result for display."""
        name = repo.get("full_name", "N/A")
        description = repo.get("description", "No description")
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        language = repo.get("language", "N/A")
        url = repo.get("html_url", "")
        updated = repo.get("updated_at", "")
        
        # Parse date
        if updated:
            try:
                # Handle ISO format with Z or timezone
                if updated.endswith("Z"):
                    updated_clean = updated.replace("Z", "+00:00")
                else:
                    updated_clean = updated
                dt = datetime.fromisoformat(updated_clean)
                updated = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError) as e:
                # If parsing fails, keep original format
                pass
        
        return f"""
{'='*80}
Repository: {name}
Description: {description}
Stars: {stars} | Forks: {forks} | Language: {language}
Updated: {updated}
URL: {url}
{'='*80}
"""
    
    def print_results(self, results: List[Dict], limit: Optional[int] = None):
        """Print formatted results."""
        if not results:
            print("No repositories found.")
            return
        
        display_results = results[:limit] if limit else results
        
        print(f"\nFound {len(results)} repository(ies). Showing top {len(display_results)}:\n")
        
        for i, repo in enumerate(display_results, 1):
            print(f"[{i}] {self.format_result(repo)}")
    
    def save_results(self, results: List[Dict], filename: str = "github_search_results.json"):
        """Save results to a JSON file."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {filename}")
        except (IOError, OSError) as e:
            print(f"Error saving results to {filename}: {e}", file=sys.stderr)


def main():
    """Main function with example searches."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Search GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example searches:
  python github_repo_search.py "drone regulations"
  python github_repo_search.py "no-fly zones" --max 10
  python github_repo_search.py "drone mapping" --sort updated
  python github_repo_search.py "malaysia drone" --save results.json
        """
    )
    
    parser.add_argument(
        "query",
        help="Search query (e.g., 'drone regulations', 'no-fly zones')"
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (optional, for higher rate limits)"
    )
    parser.add_argument(
        "--max",
        type=int,
        help="Maximum number of results to return"
    )
    parser.add_argument(
        "--sort",
        choices=["stars", "forks", "help-wanted-issues", "updated"],
        default="stars",
        help="Sort results by (default: stars)"
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sort order (default: desc)"
    )
    parser.add_argument(
        "--save",
        metavar="FILE",
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--display",
        type=int,
        help="Number of results to display (default: all)"
    )
    
    args = parser.parse_args()
    
    # Initialize searcher
    searcher = GitHubRepoSearcher(token=args.token)
    
    # Perform search
    print(f"Searching GitHub for: '{args.query}'...")
    results = searcher.search(
        query=args.query,
        sort=args.sort,
        order=args.order,
        max_results=args.max
    )
    
    # Display results
    searcher.print_results(results, limit=args.display)
    
    # Save if requested
    if args.save:
        searcher.save_results(results, args.save)


if __name__ == "__main__":
    main()

