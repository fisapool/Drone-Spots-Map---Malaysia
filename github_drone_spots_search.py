#!/usr/bin/env python3
"""
GitHub Repository Search for Drone Spots
Searches GitHub repositories for drone spot data, location information, and related code.
"""

import json
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubSearch:
    """Search GitHub repositories for drone spot related content."""
    
    def __init__(self, token: Optional[str] = None, rate_limit_delay: float = 1.0):
        """
        Initialize GitHub search.
        
        Args:
            token: GitHub personal access token (optional, increases rate limit)
            rate_limit_delay: Delay between requests in seconds
        """
        self.token = token
        self.rate_limit_delay = rate_limit_delay
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "drone-spots-searcher/1.0"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def search_repositories(self, query: str, max_results: int = 30, language: str = None) -> List[Dict]:
        """
        Search GitHub repositories.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            language: Filter by programming language (optional)
        
        Returns:
            List of repository dictionaries
        """
        repos = []
        per_page = min(100, max_results)  # GitHub allows up to 100 per page
        pages_needed = (max_results + per_page - 1) // per_page
        
        search_query = query
        if language:
            search_query = f"{query} language:{language}"
        
        for page in range(1, pages_needed + 1):
            try:
                url = f"{self.base_url}/search/repositories"
                params = {
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page
                }
                
                logger.info(f"Searching GitHub: {query} (page {page})")
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                for item in items:
                    repo_info = {
                        "name": item.get("full_name"),
                        "description": item.get("description"),
                        "url": item.get("html_url"),
                        "api_url": item.get("url"),
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at"),
                        "topics": item.get("topics", []),
                        "size": item.get("size", 0)
                    }
                    repos.append(repo_info)
                    
                    if len(repos) >= max_results:
                        break
                
                # Rate limiting
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                if remaining < 10:
                    logger.warning(f"Low rate limit remaining: {remaining}")
                
                time.sleep(self.rate_limit_delay)
                
                if len(repos) >= max_results:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error searching GitHub: {e}")
                break
        
        logger.info(f"Found {len(repos)} repositories for query: {query}")
        return repos
    
    def get_repository_files(self, repo_full_name: str, path: str = "", file_extensions: List[str] = None) -> List[Dict]:
        """
        Get files from a repository.
        
        Args:
            repo_full_name: Repository full name (e.g., "user/repo")
            path: Path in repository (default: root)
            file_extensions: Filter by file extensions (e.g., [".json", ".csv"])
        
        Returns:
            List of file dictionaries
        """
        files = []
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{path}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            items = response.json()
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                if item.get("type") == "file":
                    file_name = item.get("name", "")
                    # Filter by extension if specified
                    if file_extensions:
                        if not any(file_name.endswith(ext) for ext in file_extensions):
                            continue
                    
                    files.append({
                        "name": file_name,
                        "path": item.get("path"),
                        "url": item.get("html_url"),
                        "download_url": item.get("download_url"),
                        "size": item.get("size", 0),
                        "sha": item.get("sha")
                    })
                elif item.get("type") == "dir":
                    # Recursively search subdirectories (limit depth)
                    if path.count("/") < 2:  # Limit recursion depth
                        sub_files = self.get_repository_files(repo_full_name, item.get("path", ""), file_extensions)
                        files.extend(sub_files)
            
            time.sleep(self.rate_limit_delay)
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting files from {repo_full_name}/{path}: {e}")
        
        return files
    
    def search_code(self, query: str, max_results: int = 30) -> List[Dict]:
        """
        Search code in repositories.
        
        Args:
            query: Code search query
            max_results: Maximum number of results
        
        Returns:
            List of code match dictionaries
        """
        results = []
        per_page = min(100, max_results)
        pages_needed = (max_results + per_page - 1) // per_page
        
        for page in range(1, pages_needed + 1):
            try:
                url = f"{self.base_url}/search/code"
                params = {
                    "q": query,
                    "per_page": per_page,
                    "page": page
                }
                
                logger.info(f"Searching code: {query} (page {page})")
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                for item in items:
                    result = {
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "repository": item.get("repository", {}).get("full_name"),
                        "repository_url": item.get("repository", {}).get("html_url"),
                        "url": item.get("html_url"),
                        "sha": item.get("sha")
                    }
                    results.append(result)
                    
                    if len(results) >= max_results:
                        break
                
                time.sleep(self.rate_limit_delay)
                
                if len(results) >= max_results:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error searching code: {e}")
                break
        
        logger.info(f"Found {len(results)} code matches for query: {query}")
        return results


class DroneSpotsGitHubSearcher:
    """Main class for searching GitHub for drone spot data."""
    
    def __init__(self, config_path: str = "github_search_config.json", token: Optional[str] = None):
        """Initialize searcher with configuration."""
        self.config_path = Path(config_path)
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                "search_queries": [
                    "drone spots malaysia",
                    "drone locations malaysia",
                    "malaysia drone flying spots",
                    "drone photography locations",
                    "fpv drone spots malaysia"
                ],
                "code_search_queries": [
                    "latitude longitude malaysia drone",
                    "drone spot coordinates",
                    "malaysia drone locations json"
                ],
                "file_extensions": [".json", ".csv", ".geojson", ".kml"],
                "output_file": "github_drone_spots.json",
                "max_repos_per_query": 20,
                "max_code_results_per_query": 10
            }
            # Save default config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Created default config at {config_path}")
        
        self.github = GitHubSearch(token=token, rate_limit_delay=1.0)
        self.found_repos = []
        self.found_code = []
        self.found_files = []
    
    def search_repositories(self) -> List[Dict]:
        """Search for repositories related to drone spots."""
        all_repos = []
        queries = self.config.get("search_queries", [])
        max_per_query = self.config.get("max_repos_per_query", 20)
        
        for query in queries:
            logger.info(f"\n=== Searching repositories: {query} ===")
            repos = self.github.search_repositories(
                query,
                max_results=max_per_query
            )
            all_repos.extend(repos)
            time.sleep(2)  # Delay between queries
        
        # Deduplicate by repository name
        seen = set()
        unique_repos = []
        for repo in all_repos:
            if repo["name"] not in seen:
                seen.add(repo["name"])
                unique_repos.append(repo)
        
        self.found_repos = unique_repos
        logger.info(f"\nFound {len(unique_repos)} unique repositories")
        return unique_repos
    
    def search_code(self) -> List[Dict]:
        """Search for code containing drone spot data."""
        all_code = []
        queries = self.config.get("code_search_queries", [])
        max_per_query = self.config.get("max_code_results_per_query", 10)
        
        for query in queries:
            logger.info(f"\n=== Searching code: {query} ===")
            results = self.github.search_code(query, max_results=max_per_query)
            all_code.extend(results)
            time.sleep(2)
        
        self.found_code = all_code
        logger.info(f"\nFound {len(all_code)} code matches")
        return all_code
    
    def find_data_files(self, repos: List[Dict] = None) -> List[Dict]:
        """Find data files (JSON, CSV, etc.) in repositories."""
        if repos is None:
            repos = self.found_repos
        
        all_files = []
        file_extensions = self.config.get("file_extensions", [".json", ".csv"])
        
        logger.info(f"\n=== Searching for data files in {len(repos)} repositories ===")
        
        for i, repo in enumerate(repos[:20], 1):  # Limit to top 20 repos
            repo_name = repo["name"]
            logger.info(f"[{i}/{min(20, len(repos))}] Searching files in: {repo_name}")
            
            files = self.github.get_repository_files(
                repo_name,
                file_extensions=file_extensions
            )
            
            for file_info in files:
                file_info["repository"] = repo_name
                file_info["repository_url"] = repo["url"]
                file_info["repository_stars"] = repo.get("stars", 0)
            
            all_files.extend(files)
            
            if len(all_files) > 100:  # Limit total files
                break
        
        self.found_files = all_files
        logger.info(f"\nFound {len(all_files)} data files")
        return all_files
    
    def save_results(self, output_file: str = None):
        """Save search results to JSON file."""
        if output_file is None:
            output_file = self.config.get("output_file", "github_drone_spots.json")
        
        output = {
            "metadata": {
                "search_date": datetime.now().isoformat(),
                "total_repositories": len(self.found_repos),
                "total_code_matches": len(self.found_code),
                "total_data_files": len(self.found_files)
            },
            "repositories": self.found_repos,
            "code_matches": self.found_code,
            "data_files": self.found_files
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Saved results to {output_file}")
        logger.info(f"   - {len(self.found_repos)} repositories")
        logger.info(f"   - {len(self.found_code)} code matches")
        logger.info(f"   - {len(self.found_files)} data files")
    
    def run(self, output_file: str = None):
        """Run complete search process."""
        logger.info("Starting GitHub search for drone spots...")
        
        # Search repositories
        self.search_repositories()
        
        # Search code
        self.search_code()
        
        # Find data files in repositories
        self.find_data_files()
        
        # Save results
        self.save_results(output_file)
        
        logger.info("\n✅ GitHub search complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search GitHub repositories for drone spot data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python github_drone_spots_search.py
  
  # With GitHub token (increases rate limit)
  python github_drone_spots_search.py --token YOUR_GITHUB_TOKEN
  
  # Custom config and output
  python github_drone_spots_search.py --config custom_config.json --output results.json
  
  # Search repositories only
  python github_drone_spots_search.py --repos-only
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="github_search_config.json",
        help="Path to configuration file (default: github_search_config.json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: from config)"
    )
    
    parser.add_argument(
        "--token", "-t",
        default=None,
        help="GitHub personal access token (optional, increases rate limit)"
    )
    
    parser.add_argument(
        "--repos-only",
        action="store_true",
        help="Only search repositories, skip code and file search"
    )
    
    args = parser.parse_args()
    
    # Run searcher
    searcher = DroneSpotsGitHubSearcher(config_path=args.config, token=args.token)
    
    if args.repos_only:
        searcher.search_repositories()
        searcher.save_results(args.output)
    else:
        searcher.run(output_file=args.output)
    
    return 0


if __name__ == "__main__":
    exit(main())

