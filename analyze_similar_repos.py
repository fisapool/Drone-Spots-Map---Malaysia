#!/usr/bin/env python3
"""
Analyze similar GitHub repositories found during search.
Extracts key information for comparison with our drone spots API.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def load_repos_from_file(filepath: str) -> List[Dict]:
    """Load repository data from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filepath}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {filepath}: {e}", file=sys.stderr)
        return []

def extract_key_info(repo: Dict) -> Dict[str, Any]:
    """Extract key information from a repository dictionary."""
    return {
        "name": repo.get("full_name", "N/A"),
        "description": repo.get("description", "No description"),
        "url": repo.get("html_url", ""),
        "stars": repo.get("stargazers_count", 0),
        "language": repo.get("language", "N/A"),
        "updated": repo.get("updated_at", "N/A")[:10] if repo.get("updated_at") else "N/A",
        "license": repo.get("license", {}).get("name", "N/A") if repo.get("license") else "N/A"
    }

def analyze_similarity(repo: Dict, keywords: List[str]) -> int:
    """Score how similar a repo is to our project based on keywords."""
    score = 0
    text = f"{repo.get('name', '')} {repo.get('description', '')}".lower()
    
    similarity_keywords = [
        "openstreetmap", "osm", "map", "location", "finder", "spot",
        "terrain", "elevation", "python", "api", "fastapi",
        "no-fly", "airspace", "safety", "drone flying"
    ]
    
    for keyword in similarity_keywords:
        if keyword in text:
            score += 1
    
    return score

def main():
    """Main analysis function."""
    repo_files = [
        "drone_repos_nofly.json",
        "drone_repos_planning.json",
        "drone_repos_airspace.json",
        "drone_repos_osm_simple.json",
        "terrain_analysis_repos.json"
    ]
    
    all_repos = []
    
    # Load all repositories (skip missing files)
    for filepath in repo_files:
        if Path(filepath).exists():
            repos = load_repos_from_file(filepath)
            all_repos.extend(repos)
    
    # Remove duplicates based on full_name
    seen = set()
    unique_repos = []
    for repo in all_repos:
        name = repo.get("full_name", "")
        if name and name not in seen:
            seen.add(name)
            unique_repos.append(repo)
    
    print(f"Total unique repositories found: {len(unique_repos)}\n")
    
    # Analyze and score similarity
    scored_repos = []
    for repo in unique_repos:
        score = analyze_similarity(repo, [])
        info = extract_key_info(repo)
        info["similarity_score"] = score
        scored_repos.append(info)
    
    # Sort by similarity score and stars
    scored_repos.sort(key=lambda x: (-x["similarity_score"], -x["stars"]))
    
    # Print top 15 most similar
    print("=" * 100)
    print("TOP 15 MOST SIMILAR REPOSITORIES")
    print("=" * 100)
    print()
    
    for i, repo in enumerate(scored_repos[:15], 1):
        print(f"[{i}] {repo['name']}")
        print(f"    Description: {repo['description'][:100]}...")
        print(f"    Stars: {repo['stars']} | Language: {repo['language']} | License: {repo['license']}")
        print(f"    Similarity Score: {repo['similarity_score']}/15")
        print(f"    URL: {repo['url']}")
        print(f"    Updated: {repo['updated']}")
        print()
    
    # Statistics
    python_repos = [r for r in scored_repos if r["language"] == "Python"]
    api_repos = [r for r in scored_repos if (r["description"] and "api" in r["description"].lower()) or "api" in r["name"].lower()]
    osm_repos = [r for r in scored_repos if (r["description"] and ("osm" in r["description"].lower() or "openstreetmap" in r["description"].lower()))]
    
    print("=" * 100)
    print("STATISTICS")
    print("=" * 100)
    print(f"Python repositories: {len(python_repos)}")
    print(f"API-related repositories: {len(api_repos)}")
    print(f"OpenStreetMap-related repositories: {len(osm_repos)}")
    print(f"Repositories with 10+ stars: {len([r for r in scored_repos if r['stars'] >= 10])}")
    print()
    
    # Save detailed analysis
    output_file = "similar_repos_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_repos": len(scored_repos),
            "top_similar": scored_repos[:20],
            "statistics": {
                "python_repos": len(python_repos),
                "api_repos": len(api_repos),
                "osm_repos": len(osm_repos)
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Detailed analysis saved to: {output_file}")

if __name__ == "__main__":
    main()

