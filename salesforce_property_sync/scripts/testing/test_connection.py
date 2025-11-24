#!/usr/bin/env python3
"""Test Databricks workspace connection and list available resources."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

print("=" * 80)
print("DATABRICKS WORKSPACE CONNECTION TEST")
print("=" * 80)

# Test 1: Get current user info
try:
    current_user = w.current_user.me()
    print(f"\n✓ Connected successfully!")
    print(f"  User: {current_user.user_name}")
    print(f"  User ID: {current_user.id}")
except Exception as e:
    print(f"\n✗ Connection failed: {e}")
    exit(1)

# Test 2: List workspaces/notebooks
print("\n" + "=" * 80)
print("NOTEBOOKS AND DIRECTORIES")
print("=" * 80)
try:
    # List workspace items from root
    items = list(w.workspace.list("/", recursive=False))
    if items:
        for item in items[:20]:  # Show first 20 items
            icon = "📁" if item.object_type.value == "DIRECTORY" else "📓"
            print(f"{icon} {item.path} ({item.object_type.value})")
        if len(items) > 20:
            print(f"... and {len(items) - 20} more items")
    else:
        print("No items found in root directory")
except Exception as e:
    print(f"Error listing workspace: {e}")

# Test 3: List clusters
print("\n" + "=" * 80)
print("CLUSTERS")
print("=" * 80)
try:
    clusters = list(w.clusters.list())
    if clusters:
        for cluster in clusters:
            state = cluster.state.value if cluster.state else "UNKNOWN"
            print(f"  • {cluster.cluster_name} (ID: {cluster.cluster_id})")
            print(f"    State: {state}")
            if cluster.spark_version:
                print(f"    Spark: {cluster.spark_version}")
    else:
        print("No clusters found")
except Exception as e:
    print(f"Error listing clusters: {e}")

# Test 4: List jobs
print("\n" + "=" * 80)
print("JOBS")
print("=" * 80)
try:
    jobs = list(w.jobs.list(limit=10))
    if jobs:
        for job in jobs:
            print(f"  • {job.settings.name if job.settings else 'Unnamed'} (ID: {job.job_id})")
    else:
        print("No jobs found")
except Exception as e:
    print(f"Error listing jobs: {e}")

# Test 5: List recent notebooks
print("\n" + "=" * 80)
print("SEARCHING FOR NOTEBOOKS")
print("=" * 80)
try:
    # Try to find notebooks in common locations
    common_paths = ["/Users", "/Shared", "/Repos"]
    notebook_count = 0

    for base_path in common_paths:
        try:
            items = list(w.workspace.list(base_path, recursive=True))
            notebooks = [item for item in items if item.object_type.value == "NOTEBOOK"]
            if notebooks:
                print(f"\nFound {len(notebooks)} notebook(s) in {base_path}:")
                for nb in notebooks[:10]:  # Show first 10
                    print(f"  📓 {nb.path}")
                if len(notebooks) > 10:
                    print(f"  ... and {len(notebooks) - 10} more")
                notebook_count += len(notebooks)
        except Exception as e:
            # Path might not exist, skip it
            pass

    if notebook_count == 0:
        print("No notebooks found in common locations")
    else:
        print(f"\nTotal notebooks found: {notebook_count}")

except Exception as e:
    print(f"Error searching notebooks: {e}")

print("\n" + "=" * 80)
print("CONNECTION TEST COMPLETE")
print("=" * 80)
