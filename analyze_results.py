#!/usr/bin/env python3
"""Analyze the drone_search_results.json file and provide detailed statistics."""

import json
import sys
from collections import Counter
from datetime import datetime

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def analyze_results(filename="drone_search_results.json"):
    """Analyze the search results JSON file."""
    
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("=" * 80)
    print("DRONE SEARCH RESULTS ANALYSIS")
    print("=" * 80)
    
    # Overall statistics
    print(f"\n[STATISTICS] OVERALL STATISTICS")
    print(f"   Total search categories: {len(data)}")
    
    total_repos = 0
    category_stats = {}
    
    for category, search_data in data.items():
        query = search_data.get("query", "N/A")
        results = search_data.get("results", [])
        count = len(results)
        total_repos += count
        category_stats[category] = {
            "query": query,
            "count": count,
            "repos": results
        }
        print(f"\n   {category}:")
        print(f"      Query: '{query}'")
        print(f"      Repositories found: {count}")
    
    print(f"\n   Total repositories across all searches: {total_repos}")
    
    # Detailed analysis for each category
    print(f"\n{'=' * 80}")
    print("[DETAILED] BREAKDOWN BY CATEGORY")
    print("=" * 80)
    
    for category, stats in category_stats.items():
        print(f"\n[CATEGORY] {category.upper()}")
        print(f"   Search Query: '{stats['query']}'")
        print(f"   Results: {stats['count']} repositories")
        
        if stats['count'] > 0:
            repos = stats['repos']
            
            # Top repositories by stars
            sorted_repos = sorted(repos, key=lambda x: x.get('stargazers_count', 0), reverse=True)
            top_5 = sorted_repos[:5]
            
            print(f"\n   [TOP] Top {min(5, len(top_5))} Repositories (by stars):")
            for i, repo in enumerate(top_5, 1):
                name = repo.get('full_name', 'N/A')
                stars = repo.get('stargazers_count', 0)
                forks = repo.get('forks_count', 0)
                language = repo.get('language', 'N/A')
                description = repo.get('description', 'No description')
                url = repo.get('html_url', '')
                updated = repo.get('updated_at', '')
                
                # Format date
                if updated:
                    try:
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        updated = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                
                print(f"\n      {i}. {name}")
                print(f"         [*] {stars} stars | [F] {forks} forks | [L] {language}")
                print(f"         [Updated] {updated}")
                print(f"         [Desc] {description[:100]}{'...' if len(description) > 100 else ''}")
                print(f"         [URL] {url}")
            
            # Language distribution
            languages = [r.get('language') for r in repos if r.get('language')]
            if languages:
                lang_counter = Counter(languages)
                print(f"\n   [LANGUAGES] Languages used:")
                for lang, count in lang_counter.most_common(5):
                    print(f"      {lang}: {count} repositories")
            
            # Most active (recently updated)
            recent_repos = sorted(repos, key=lambda x: x.get('updated_at', ''), reverse=True)[:3]
            print(f"\n   [RECENT] Most Recently Updated:")
            for repo in recent_repos:
                name = repo.get('full_name', 'N/A')
                updated = repo.get('updated_at', '')
                if updated:
                    try:
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        updated = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                print(f"      {name} - {updated}")
        else:
            print(f"   [WARNING] No repositories found for this search query.")
    
    # Cross-category insights
    print(f"\n{'=' * 80}")
    print("[INSIGHTS] CROSS-CATEGORY INSIGHTS")
    print("=" * 80)
    
    all_repos = []
    for stats in category_stats.values():
        all_repos.extend(stats['repos'])
    
    if all_repos:
        # Most starred overall
        most_starred = max(all_repos, key=lambda x: x.get('stargazers_count', 0))
        print(f"\n   [TOP] Most Starred Repository Overall:")
        print(f"      {most_starred.get('full_name', 'N/A')}")
        print(f"      [*] {most_starred.get('stargazers_count', 0)} stars")
        print(f"      [URL] {most_starred.get('html_url', '')}")
        
        # Language distribution across all
        all_languages = [r.get('language') for r in all_repos if r.get('language')]
        if all_languages:
            lang_counter = Counter(all_languages)
            print(f"\n   [LANGUAGES] Most Common Languages (across all searches):")
            for lang, count in lang_counter.most_common(5):
                percentage = (count / len(all_languages)) * 100
                print(f"      {lang}: {count} repos ({percentage:.1f}%)")
        
        # Total stars and forks
        total_stars = sum(r.get('stargazers_count', 0) for r in all_repos)
        total_forks = sum(r.get('forks_count', 0) for r in all_repos)
        print(f"\n   [STATS] Aggregate Statistics:")
        print(f"      Total stars: {total_stars:,}")
        print(f"      Total forks: {total_forks:,}")
        print(f"      Average stars per repo: {total_stars / len(all_repos):.1f}")
    
    print(f"\n{'=' * 80}")
    print("Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    analyze_results()

