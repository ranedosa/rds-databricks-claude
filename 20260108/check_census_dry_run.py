#!/usr/bin/env python3
"""
Check Census sync configurations and recent dry run results
"""
import requests
import json
from datetime import datetime

# Census API configuration
CENSUS_API_TOKEN = "secret-token:HyMHBwFx95V4gdjdqufvfZuz"
CENSUS_BASE_URL = "https://app.getcensus.com/api/v1"

headers = {
    "Authorization": f"Bearer {CENSUS_API_TOKEN}",
    "Content-Type": "application/json"
}

SYNC_A_ID = 3394022  # CREATE sync
SYNC_B_ID = 3394041  # UPDATE sync

print("=" * 80)
print("CENSUS DRY RUN ANALYSIS")
print("=" * 80)
print()

# Function to get sync details
def get_sync_details(sync_id, sync_name):
    print("=" * 80)
    print(f"{sync_name} - Configuration")
    print("=" * 80)

    url = f"{CENSUS_BASE_URL}/syncs/{sync_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        sync = response.json()['data']
        print(f"Sync ID: {sync['id']}")
        print(f"Label: {sync.get('label', 'N/A')}")
        print(f"Status: {sync.get('status', 'N/A')}")
        print(f"Paused: {sync.get('paused', False)}")
        print(f"Operation: {sync.get('operation', 'N/A')}")

        # Check for source table
        source = sync.get('source_attributes', {})
        print(f"\nSource:")
        source_obj = source.get('object', {})
        if isinstance(source_obj, dict):
            source_name = source_obj.get('name', 'N/A')
            print(f"  Object: {source_name}")

            # Check if this is a pilot view
            if 'pilot' in source_name.lower():
                print(f"  ⚠️ WARNING: Syncing from PILOT view, not production view!")
        else:
            print(f"  Object: {source_obj}")

        # Check for filters
        if 'filter' in source and source['filter']:
            print(f"  ⚠️ Filter Present: {source['filter']}")
        else:
            print(f"  Filter: None (syncing all records)")

        # Check destination
        destination = sync.get('destination_attributes', {})
        print(f"\nDestination:")
        dest_obj = destination.get('object', 'N/A')
        if isinstance(dest_obj, dict):
            print(f"  Object: {dest_obj.get('name', 'N/A')}")
        else:
            print(f"  Object: {dest_obj}")
        print(f"  Operation: {destination.get('operation', 'N/A')}")

        # Check mappings count
        mappings = sync.get('mappings', [])
        print(f"\nField Mappings: {len(mappings)} fields")

        print()
        return True
    else:
        print(f"Error fetching sync details: {response.status_code}")
        print(response.text)
        return False

# Function to get recent sync runs
def get_sync_runs(sync_id, sync_name):
    print("=" * 80)
    print(f"{sync_name} - Recent Sync Runs")
    print("=" * 80)

    url = f"{CENSUS_BASE_URL}/syncs/{sync_id}/sync_runs"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        runs = response.json()['data']

        if not runs:
            print("No sync runs found")
            print()
            return

        # Show last 3 runs
        print(f"\nShowing last {min(3, len(runs))} runs:\n")

        for i, run in enumerate(runs[:3], 1):
            run_id = run.get('id', 'N/A')
            status = run.get('status', 'N/A')
            created = run.get('created_at', 'N/A')
            completed = run.get('completed_at', 'N/A')

            # Format timestamps
            if created != 'N/A':
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # Get operation type
            full_sync = run.get('full_sync', False)
            sync_type = "Full Sync" if full_sync else "Incremental"

            # Check if dry run
            dry_run = run.get('dry_run', False)
            if dry_run:
                sync_type += " (DRY RUN)"

            print(f"Run #{i}:")
            print(f"  ID: {run_id}")
            print(f"  Status: {status}")
            print(f"  Type: {sync_type}")
            print(f"  Started: {created}")

            # Get record counts
            records = run.get('records_processed', 0)
            records_updated = run.get('records_updated', 0)
            records_failed = run.get('records_failed', 0)
            records_invalid = run.get('records_invalid', 0)

            print(f"\n  Records:")
            print(f"    Processed: {records}")
            print(f"    Updated: {records_updated}")
            print(f"    Failed: {records_failed}")
            print(f"    Invalid: {records_invalid}")

            # Calculate error rate
            if records > 0:
                error_rate = (records_failed + records_invalid) / records * 100
                print(f"    Error Rate: {error_rate:.1f}%")

            # Show sync stages if available
            if 'sync_stages' in run:
                stages = run['sync_stages']
                print(f"\n  Stages:")
                for stage in stages:
                    stage_name = stage.get('stage', 'Unknown')
                    stage_status = stage.get('status', 'Unknown')
                    print(f"    - {stage_name}: {stage_status}")

            # If this is a dry run, show what would happen
            if dry_run and status == 'completed':
                print(f"\n  ✅ DRY RUN COMPLETE")
                if records_updated > 0:
                    print(f"  Would update {records_updated} records in production")
                if records_failed > 0:
                    print(f"  ⚠️ Would have {records_failed} failures")
                if records_invalid > 0:
                    print(f"  ⚠️ Would have {records_invalid} invalid records")

            print()

    else:
        print(f"Error fetching sync runs: {response.status_code}")
        print(response.text)

    print()

# Check Sync A (CREATE)
get_sync_details(SYNC_A_ID, "SYNC A (CREATE)")
get_sync_runs(SYNC_A_ID, "SYNC A (CREATE)")

# Check Sync B (UPDATE)
get_sync_details(SYNC_B_ID, "SYNC B (UPDATE)")
get_sync_runs(SYNC_B_ID, "SYNC B (UPDATE)")

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print()
print("Key Questions to Answer:")
print("1. Does either sync have filters enabled? (look for ⚠️ Filter Present)")
print("2. What do the dry run results show?")
print("3. Are error rates acceptable (<5%)?")
print("4. How many records would be synced in full run?")
