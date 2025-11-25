"""
Monitor Census sync status using Census API
"""
import requests
import json
import os
from datetime import datetime

CENSUS_CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"

def load_census_credentials():
    """Load Census API credentials"""
    if not os.path.exists(CENSUS_CONFIG_PATH):
        print(f"❌ Config file not found: {CENSUS_CONFIG_PATH}")
        return None

    with open(CENSUS_CONFIG_PATH, 'r') as f:
        config = json.load(f)

    if config.get('api_key') == 'YOUR_CENSUS_API_KEY_HERE':
        print(f"❌ Please add your Census API key to: {CENSUS_CONFIG_PATH}")
        print("\nTo get your API key:")
        print("1. Go to https://app.getcensus.com/")
        print("2. Click Settings → API Keys")
        print("3. Create a new API key")
        print("4. Copy it to the config file")
        return None

    return config

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def get_syncs(config):
    """Get all syncs"""
    url = f"{config['api_base_url']}/syncs"
    headers = get_headers(config['api_key'])

    print("\n" + "="*80)
    print("FETCHING CENSUS SYNCS")
    print("="*80)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        syncs = response.json().get('data', [])
        print(f"\nFound {len(syncs)} syncs")

        return syncs
    except requests.exceptions.HTTPError as e:
        print(f"❌ API Error: {e}")
        print(f"Response: {response.text}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def get_sync_runs(config, sync_id, limit=10):
    """Get recent runs for a specific sync"""
    url = f"{config['api_base_url']}/sync_runs"
    headers = get_headers(config['api_key'])
    params = {
        'sync_id': sync_id,
        'order_by': 'created_at',
        'order': 'desc',
        'limit': limit
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        runs = response.json().get('data', [])
        return runs
    except Exception as e:
        print(f"❌ Error fetching runs: {e}")
        return []

def display_syncs(syncs):
    """Display all syncs"""
    print("\n" + "="*80)
    print("ALL CENSUS SYNCS")
    print("="*80)

    if not syncs:
        print("No syncs found")
        return None

    # Look for Salesforce product_property syncs
    salesforce_syncs = []

    for i, sync in enumerate(syncs, 1):
        sync_id = sync.get('id')
        label = sync.get('label', 'Untitled')
        status = sync.get('status', 'unknown')
        destination = sync.get('destination', {}).get('object', {}).get('name', 'Unknown')

        print(f"\n{i}. Sync ID: {sync_id}")
        print(f"   Label: {label}")
        print(f"   Status: {status}")
        print(f"   Destination: {destination}")

        # Check if this is likely our product_property sync
        label_str = (label or '').lower()
        destination_str = (destination or '').lower()
        if 'product_property' in label_str or 'product_property' in destination_str:
            salesforce_syncs.append(sync)
            print(f"   ⭐ THIS LOOKS LIKE YOUR PROPERTY SYNC!")

    return salesforce_syncs

def display_sync_runs(config, sync):
    """Display recent runs for a sync"""
    sync_id = sync.get('id')
    label = sync.get('label', 'Untitled')

    print("\n" + "="*80)
    print(f"RECENT RUNS FOR: {label}")
    print("="*80)

    runs = get_sync_runs(config, sync_id, limit=5)

    if not runs:
        print("No runs found")
        return

    for i, run in enumerate(runs, 1):
        run_id = run.get('id')
        status = run.get('status', 'unknown')
        created_at = run.get('created_at')
        completed_at = run.get('completed_at')

        # Parse dates
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_str = created.strftime('%Y-%m-%d %H:%M:%S')
        except:
            created_str = created_at

        print(f"\n{i}. Run ID: {run_id}")
        print(f"   Status: {status}")
        print(f"   Started: {created_str}")

        if completed_at:
            try:
                completed = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                completed_str = completed.strftime('%Y-%m-%d %H:%M:%S')
                duration = (completed - created).total_seconds()
                print(f"   Completed: {completed_str}")
                print(f"   Duration: {duration:.1f} seconds")
            except:
                print(f"   Completed: {completed_at}")

        # Get stats
        records_processed = run.get('records_processed', 0)
        records_updated = run.get('records_updated', 0)
        records_failed = run.get('records_failed', 0)
        records_invalid = run.get('records_invalid', 0)

        print(f"   📊 Stats:")
        print(f"      Processed: {records_processed:,}")
        print(f"      Updated: {records_updated:,}")
        print(f"      Failed: {records_failed:,}")
        print(f"      Invalid: {records_invalid:,}")

        if status == 'completed':
            print(f"   ✅ SUCCESS")
        elif status == 'failed':
            print(f"   ❌ FAILED")
            error = run.get('error_message')
            if error:
                print(f"   Error: {error}")
        elif status == 'running':
            print(f"   ⏳ IN PROGRESS")

def get_sync_run_details(config, run_id):
    """Get detailed information about a specific run"""
    url = f"{config['api_base_url']}/sync_runs/{run_id}"
    headers = get_headers(config['api_key'])

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json().get('data', {})
    except Exception as e:
        print(f"❌ Error fetching run details: {e}")
        return {}

def monitor_latest_run(config, sync):
    """Monitor the latest run for a sync"""
    sync_id = sync.get('id')
    label = sync.get('label', 'Untitled')

    print("\n" + "="*80)
    print(f"LATEST RUN DETAILS: {label}")
    print("="*80)

    runs = get_sync_runs(config, sync_id, limit=1)

    if not runs:
        print("No runs found")
        return

    latest_run = runs[0]
    run_id = latest_run.get('id')

    # Get full details
    details = get_sync_run_details(config, run_id)

    if not details:
        print("Could not fetch run details")
        return

    # Display comprehensive information
    print(f"\nRun ID: {run_id}")
    print(f"Status: {details.get('status', 'unknown')}")
    print(f"Created: {details.get('created_at')}")
    print(f"Completed: {details.get('completed_at', 'Not yet')}")

    print(f"\n📊 Record Statistics:")
    print(f"  Processed: {details.get('records_processed', 0):,}")
    print(f"  Updated: {details.get('records_updated', 0):,}")
    print(f"  Created: {details.get('records_created', 0):,}")
    print(f"  Failed: {details.get('records_failed', 0):,}")
    print(f"  Invalid: {details.get('records_invalid', 0):,}")

    # Check for errors
    if details.get('records_failed', 0) > 0 or details.get('records_invalid', 0) > 0:
        print(f"\n⚠️  ERRORS DETECTED")
        error_msg = details.get('error_message')
        if error_msg:
            print(f"Error Message: {error_msg}")

        # Try to get error details
        print("\nCheck Census UI for detailed error logs:")
        print(f"https://app.getcensus.com/syncs/{sync_id}/runs/{run_id}")

def main():
    """Main function"""
    print("\n" + "="*80)
    print("CENSUS SYNC MONITOR")
    print("="*80)

    # Load credentials
    config = load_census_credentials()
    if not config:
        return

    print("✅ Credentials loaded")

    # Get all syncs
    syncs = get_syncs(config)

    if not syncs:
        return

    # Display syncs
    salesforce_syncs = display_syncs(syncs)

    # If we found product_property syncs, show their runs
    if salesforce_syncs:
        print("\n" + "="*80)
        print("ANALYZING PRODUCT_PROPERTY SYNCS")
        print("="*80)

        for sync in salesforce_syncs:
            display_sync_runs(config, sync)
            monitor_latest_run(config, sync)
    else:
        print("\n⚠️  No product_property syncs found")
        print("Showing all syncs above - please identify your sync manually")

        # Ask user which sync to monitor
        print("\nTo monitor a specific sync, you can modify the script")
        print("or run: monitor_latest_run(config, syncs[INDEX])")

if __name__ == "__main__":
    main()
