#!/usr/bin/env python3
"""
Analyze notebook audit data to find top users by notebook count
"""

import json
from collections import Counter
import sys

def extract_user_from_path(path):
    """Extract user email from notebook path"""
    parts = path.split('/')

    # Paths starting with /Users/{email}/
    if len(parts) >= 3 and parts[1] == 'Users':
        return parts[2]

    # For Repos: /Repos/{email}/
    elif len(parts) >= 3 and parts[1] == 'Repos':
        return parts[2]

    # For Shared or other paths
    elif parts[1] == 'Shared':
        return 'Shared'

    # Other cases
    return parts[1] if len(parts) > 1 else 'Unknown'

def analyze_top_creators(json_file):
    """Analyze the notebook audit file and report top creators"""

    with open(json_file, 'r') as f:
        data = json.load(f)

    total_notebooks = data.get('total_notebooks', 0)
    notebooks = data.get('notebooks', [])

    print("=" * 80)
    print("TOP 10 NOTEBOOK CREATORS")
    print("=" * 80)
    print(f"Total notebooks analyzed: {total_notebooks}")
    print("")

    # Count notebooks by user
    user_counts = Counter()

    for notebook in notebooks:
        path = notebook.get('path', '')
        user = extract_user_from_path(path)
        user_counts[user] += 1

    # Get top 10
    top_10 = user_counts.most_common(10)

    print(f"{'Rank':<6} {'Count':<8} {'User'}")
    print("-" * 80)

    for rank, (user, count) in enumerate(top_10, 1):
        percentage = (count / total_notebooks * 100) if total_notebooks > 0 else 0
        print(f"{rank:<6} {count:<8} {user} ({percentage:.1f}%)")

    print("")
    print("=" * 80)

    # Additional statistics
    print(f"\nTotal unique users: {len(user_counts)}")

    # Show distribution
    notebooks_by_top_10 = sum(count for _, count in top_10)
    percentage_by_top_10 = (notebooks_by_top_10 / total_notebooks * 100) if total_notebooks > 0 else 0

    print(f"Notebooks by top 10 users: {notebooks_by_top_10} ({percentage_by_top_10:.1f}%)")
    print(f"Notebooks by other users: {total_notebooks - notebooks_by_top_10} ({100-percentage_by_top_10:.1f}%)")

    return top_10

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "audit_results/notebooks_20251024_143907.json"
    analyze_top_creators(json_file)
