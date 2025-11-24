"""
Quick check for specific Census sync: 3325886
"""
import requests
import json
import os
from datetime import datetime

CENSUS_CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
SYNC_ID = 3325886  # Your specific sync ID

def load_census_credentials():
    """Load Census API credentials"""
    with open(CENSUS_CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def get_sync_details(config, sync_id):
    """Get sync details"""
    url = f"{config['api_base_url']}/syncs/{sync_id}"
    headers = get_headers(config['api_key'])

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('data', {})
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

def get_sync_runs(config, sync_id, limit=5):
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
        return response.json().get('data', [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def format_timestamp(timestamp):
    """Format ISO timestamp to readable string"""
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

def main():
    print("\n" + "="*80)
    print(f"MONITORING CENSUS SYNC: {SYNC_ID}")
    print("="*80)

    # Load credentials
    config = load_census_credentials()
    print("✅ Credentials loaded")

    # Get sync details
    print("\n" + "="*80)
    print("SYNC DETAILS")
    print("="*80)

    sync = get_sync_details(config, SYNC_ID)

    if sync:
        print(f"\nSync ID: {sync.get('id')}")
        print(f"Label: {sync.get('label', 'Untitled')}")
        print(f"Status: {sync.get('status', 'unknown')}")
        print(f"Paused: {sync.get('paused', False)}")

        # Source info
        source = sync.get('source', {})
        print(f"\nSource:")
        print(f"  Type: {source.get('type', 'Unknown')}")

        # Destination info
        destination = sync.get('destination', {})
        print(f"\nDestination:")
        print(f"  Type: {destination.get('type', 'Unknown')}")
        dest_obj = destination.get('object', {})
        print(f"  Object: {dest_obj.get('name', 'Unknown')}")

    # Get recent runs
    print("\n" + "="*80)
    print("RECENT SYNC RUNS")
    print("="*80)

    runs = get_sync_runs(config, SYNC_ID, limit=10)

    if not runs:
        print("\n⚠️  No runs found yet")
        print("The sync may not have run yet, or it's still initializing.")
        return

    print(f"\nFound {len(runs)} recent runs:\n")

    for i, run in enumerate(runs, 1):
        run_id = run.get('id')
        status = run.get('status', 'unknown')
        created_at = format_timestamp(run.get('created_at'))
        completed_at = format_timestamp(run.get('completed_at'))

        # Calculate duration
        duration = "N/A"
        if run.get('created_at') and run.get('completed_at'):
            try:
                created = datetime.fromisoformat(run.get('created_at').replace('Z', '+00:00'))
                completed = datetime.fromisoformat(run.get('completed_at').replace('Z', '+00:00'))
                duration_sec = (completed - created).total_seconds()
                duration = f"{duration_sec:.1f}s"
            except:
                pass

        print(f"{i}. Run #{run_id}")
        print(f"   Status: {status}")
        print(f"   Started: {created_at}")
        print(f"   Completed: {completed_at}")
        print(f"   Duration: {duration}")

        # Stats
        records_processed = run.get('records_processed', 0)
        records_updated = run.get('records_updated', 0)
        records_failed = run.get('records_failed', 0)
        records_invalid = run.get('records_invalid', 0)

        print(f"   📊 Records:")
        print(f"      Processed: {records_processed:,}")
        print(f"      Updated/Created: {records_updated:,}")
        print(f"      Failed: {records_failed:,}")
        print(f"      Invalid: {records_invalid:,}")

        # Status indicator
        if status == 'completed':
            if records_failed == 0 and records_invalid == 0:
                print(f"   ✅ SUCCESS - All records synced!")
            else:
                print(f"   ⚠️  COMPLETED WITH ERRORS")
        elif status == 'failed':
            print(f"   ❌ FAILED")
            error = run.get('error_message')
            if error:
                print(f"   Error: {error}")
        elif status == 'working':
            print(f"   ⏳ IN PROGRESS")
        elif status == 'cancelled':
            print(f"   🚫 CANCELLED")

        print()

    # Show latest run in detail
    if runs:
        latest = runs[0]
        print("="*80)
        print("LATEST RUN SUMMARY")
        print("="*80)

        print(f"\nRun ID: {latest.get('id')}")
        print(f"Status: {latest.get('status')}")
        print(f"URL: https://app.getcensus.com/workspaces/33026/syncs/{SYNC_ID}/sync-runs/{latest.get('id')}")

        if latest.get('status') == 'completed':
            total = latest.get('records_processed', 0)
            failed = latest.get('records_failed', 0) + latest.get('records_invalid', 0)
            success = total - failed

            print(f"\n📈 Results:")
            print(f"   Total: {total:,} records")
            print(f"   Success: {success:,} records ({success/total*100 if total > 0 else 0:.1f}%)")
            if failed > 0:
                print(f"   Failed: {failed:,} records ({failed/total*100 if total > 0 else 0:.1f}%)")
                print(f"\n⚠️  Check Census UI for error details")

if __name__ == "__main__":
    main()
