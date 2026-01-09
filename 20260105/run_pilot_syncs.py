"""
Run Pilot Syncs - Trigger Sync A and Sync B for pilot testing
"""
import requests
import json
import sys
import time
import os

CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
SCRIPTS_DIR = "/Users/danerosa/rds_databricks_claude/20260105"

def load_config():
    """Load Census API credentials"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def trigger_sync(config, sync_id, sync_name):
    """Trigger a sync run"""
    url = f"{config['api_base_url']}/syncs/{sync_id}/trigger"
    headers = get_headers(config['api_key'])

    print(f"\n🚀 Triggering {sync_name}...")
    print(f"   Sync ID: {sync_id}")

    try:
        response = requests.post(url, headers=headers, json={"force_full_sync": False})
        response.raise_for_status()
        run = response.json()

        print(f"✅ {sync_name} triggered successfully!")
        print(f"   Run ID: {run.get('sync_run_id', 'N/A')}")

        return run.get('sync_run_id')

    except requests.exceptions.RequestException as e:
        print(f"❌ Error triggering {sync_name}: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None

def get_sync_status(config, sync_id):
    """Get sync run status"""
    url = f"{config['api_base_url']}/syncs/{sync_id}/sync_runs"
    headers = get_headers(config['api_key'])

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        runs = response.json()

        if runs.get('data') and len(runs['data']) > 0:
            latest_run = runs['data'][0]
            return {
                'status': latest_run.get('status'),
                'records_processed': latest_run.get('records_processed', 0),
                'records_updated': latest_run.get('records_updated', 0),
                'records_failed': latest_run.get('records_failed', 0),
                'error_message': latest_run.get('error_message')
            }

        return None

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Error checking status: {e}")
        return None

def monitor_sync(config, sync_id, sync_name, max_wait_minutes=10):
    """Monitor sync until completion"""
    print(f"\n📊 Monitoring {sync_name}...")

    max_wait_seconds = max_wait_minutes * 60
    start_time = time.time()
    check_interval = 10  # seconds

    while (time.time() - start_time) < max_wait_seconds:
        status_info = get_sync_status(config, sync_id)

        if not status_info:
            print(f"⚠️  No status available yet, waiting...")
            time.sleep(check_interval)
            continue

        status = status_info['status']
        print(f"\r   Status: {status} | Processed: {status_info['records_processed']} | " +
              f"Updated: {status_info['records_updated']} | Failed: {status_info['records_failed']}", end='')

        if status in ['completed', 'success']:
            print(f"\n✅ {sync_name} completed successfully!")
            print(f"   Records Processed: {status_info['records_processed']}")
            print(f"   Records Updated: {status_info['records_updated']}")
            print(f"   Records Failed: {status_info['records_failed']}")
            return True

        elif status in ['failed', 'cancelled']:
            print(f"\n❌ {sync_name} failed!")
            if status_info['error_message']:
                print(f"   Error: {status_info['error_message']}")
            return False

        time.sleep(check_interval)

    print(f"\n⚠️  Timeout waiting for {sync_name} to complete")
    return False

def main():
    """Main function"""
    print("\n" + "="*80)
    print("RUN PILOT SYNCS - Testing 100 Properties (50 CREATE + 50 UPDATE)")
    print("="*80)

    try:
        config = load_config()

        # Read sync IDs
        sync_a_path = os.path.join(SCRIPTS_DIR, 'sync_a_id.txt')
        sync_b_path = os.path.join(SCRIPTS_DIR, 'sync_b_id.txt')

        if not os.path.exists(sync_a_path) or not os.path.exists(sync_b_path):
            print(f"\n❌ Sync IDs not found. Run configure_all_syncs.py first!")
            sys.exit(1)

        with open(sync_a_path, 'r') as f:
            sync_a_id = f.read().strip()
        with open(sync_b_path, 'r') as f:
            sync_b_id = f.read().strip()

        print(f"\n✅ Found Sync A (CREATE) ID: {sync_a_id}")
        print(f"✅ Found Sync B (UPDATE) ID: {sync_b_id}")

        # Confirm before running
        print(f"\n⚠️  This will sync 100 properties to Salesforce:")
        print(f"   - 50 CREATE (new properties)")
        print(f"   - 50 UPDATE (existing properties)")
        print(f"\nContinue? (yes/no): ", end='')

        confirm = input().strip().lower()
        if confirm not in ['yes', 'y']:
            print(f"\n❌ Cancelled by user")
            sys.exit(0)

        # Run Sync A (CREATE)
        print("\n" + "="*80)
        print("PILOT TEST 1: CREATE 50 Properties (Sync A)")
        print("="*80)

        run_a_id = trigger_sync(config, sync_a_id, "Sync A (CREATE)")
        if not run_a_id:
            print(f"\n❌ Failed to trigger Sync A")
            sys.exit(1)

        success_a = monitor_sync(config, sync_a_id, "Sync A (CREATE)")

        # Run Sync B (UPDATE)
        print("\n" + "="*80)
        print("PILOT TEST 2: UPDATE 50 Properties (Sync B)")
        print("="*80)

        run_b_id = trigger_sync(config, sync_b_id, "Sync B (UPDATE)")
        if not run_b_id:
            print(f"\n❌ Failed to trigger Sync B")
            sys.exit(1)

        success_b = monitor_sync(config, sync_b_id, "Sync B (UPDATE)")

        # Summary
        print("\n" + "="*80)
        print("PILOT TEST RESULTS")
        print("="*80)

        print(f"\nSync A (CREATE): {'✅ SUCCESS' if success_a else '❌ FAILED'}")
        print(f"Sync B (UPDATE): {'✅ SUCCESS' if success_b else '❌ FAILED'}")

        if success_a and success_b:
            print(f"\n✅ Both pilot syncs completed successfully!")
            print(f"\n📋 Next Steps:")
            print(f"   1. Check Salesforce for new/updated records")
            print(f"   2. Run validation queries in Databricks")
            print(f"   3. Make GO/NO-GO decision for full rollout")
        else:
            print(f"\n❌ One or more pilot syncs failed. Review errors before proceeding.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
