"""
Comprehensive Notebook Audit for Databricks Workspace
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict

DATABRICKS_PROFILE = "pat"
DAYS_THRESHOLD = 90

def run_cli(cmd):
    """Execute databricks CLI command"""
    cmd_with_profile = cmd.replace("databricks ", f"databricks --profile {DATABRICKS_PROFILE} ")
    try:
        result = subprocess.run(cmd_with_profile, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except:
                return None
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def count_notebooks_in_directory(path, depth=0, max_depth=10):
    """Recursively count notebooks with progress indicators"""
    if depth > max_depth:
        print(f"  [Max depth reached at {path}]")
        return []

    print(f"{'  ' * depth}Scanning: {path}")
    sys.stdout.flush()

    data = run_cli(f"databricks workspace list '{path}' --output json")

    if not data or not isinstance(data, list):
        return []

    notebooks = []
    directories = []

    for obj in data:
        obj_path = obj.get('path')
        obj_type = obj.get('object_type')

        if obj_type == 'NOTEBOOK':
            notebooks.append({
                "path": obj_path,
                "type": "NOTEBOOK"
            })
        elif obj_type == 'DIRECTORY':
            directories.append(obj_path)

    print(f"{'  ' * depth}  Found: {len(notebooks)} notebooks, {len(directories)} subdirectories")
    sys.stdout.flush()

    # Recurse into subdirectories
    for dir_path in directories:
        notebooks.extend(count_notebooks_in_directory(dir_path, depth + 1, max_depth))

    return notebooks

def audit_notebooks():
    """Audit all notebooks in workspace"""
    print("=" * 80)
    print("NOTEBOOK AUDIT")
    print("=" * 80)
    print("")

    # Start from root directories
    root_dirs = ['/Users', '/Shared', '/Repos', '/data_team']
    all_notebooks = []

    for root_dir in root_dirs:
        print(f"\nScanning root directory: {root_dir}")
        print("-" * 80)
        try:
            notebooks = count_notebooks_in_directory(root_dir, depth=0, max_depth=5)
            all_notebooks.extend(notebooks)
            print(f"  Subtotal for {root_dir}: {len(notebooks)} notebooks")
        except Exception as e:
            print(f"  Error scanning {root_dir}: {e}")

    print("\n" + "=" * 80)
    print(f"TOTAL NOTEBOOKS FOUND: {len(all_notebooks)}")
    print("=" * 80)

    # Group by directory
    by_directory = defaultdict(int)
    for nb in all_notebooks:
        # Get parent directory
        path_parts = nb['path'].rsplit('/', 1)
        parent_dir = path_parts[0] if len(path_parts) > 1 else '/'
        by_directory[parent_dir] += 1

    print("\nTop 20 directories by notebook count:")
    print("-" * 80)
    sorted_dirs = sorted(by_directory.items(), key=lambda x: x[1], reverse=True)[:20]
    for dir_path, count in sorted_dirs:
        print(f"  {count:4d}  {dir_path}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_notebooks": len(all_notebooks),
        "notebooks": all_notebooks,
        "by_directory": dict(by_directory)
    }

    output_file = f"audit_results/notebooks_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nFull results saved to: {output_file}")

    return results

if __name__ == "__main__":
    audit_notebooks()
