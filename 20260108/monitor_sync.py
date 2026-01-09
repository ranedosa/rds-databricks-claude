#!/usr/bin/env python3
"""
Monitor Census sync progress in real-time
"""
import requests
import json
import time
from datetime import datetime

CENSUS_API_TOKEN = "secret-token:HyMHBwFx95V4gdjdqufvfZuz"
CENSUS_BASE_URL = "https://app.getcensus.com/api/v1"

headers = {
    "Authorization": f"Bearer {CENSUS_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_latest_run(sync_id, sync_name):
    url = f"{CENSUS_BASE_URL}/syncs/{sync_id}/sync_runs"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        runs = response.json()['data']
        if runs:
            latest = runs[0]

            print("=" * 80)
            print(f"{sync_name} - Latest Run Status")
            print("=" * 80)
            print(f"Run ID: {latest.get('id')}")
            print(f"Status: {latest.get('status')}")
            print(f"Started: {latest.get('created_at', 'N/A')}")

            # Progress
            processed = latest.get('records_processed') or 0
            updated = latest.get('records_updated') or 0
            failed = latest.get('records_failed') or 0
            invalid = latest.get('records_invalid') or 0

            print(f"\nProgress:")
            if processed == 0:
                print(f"  ⏳ Starting up... (no records processed yet)")
            else:
                print(f"  Processed: {processed}")
                print(f"  Updated: {updated}")
                print(f"  Failed: {failed}")
                print(f"  Invalid: {invalid}")

            if processed > 0:
                error_rate = (failed + invalid) / processed * 100
                print(f"  Error Rate: {error_rate:.1f}%")

                if error_rate > 5:
                    print(f"  ⚠️ WARNING: Error rate above 5%!")
                elif error_rate > 0:
                    print(f"  ⚠️ Note: Some errors detected")
                else:
                    print(f"  ✅ No errors so far")

            # Status indicator
            status = latest.get('status')
            if status == 'working':
                print(f"\n🔄 Sync is RUNNING...")
            elif status == 'completed':
                print(f"\n✅ Sync COMPLETED")
            elif status == 'failed':
                print(f"\n❌ Sync FAILED")
            else:
                print(f"\n⏸️ Status: {status}")

            print()
            return latest
    else:
        print(f"Error: {response.status_code}")
        return None

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'b':
        # Monitor Sync B
        print("Monitoring Sync B (UPDATE)...")
        print()
        get_latest_run(3394041, "SYNC B (UPDATE)")
    else:
        # Monitor Sync A (default)
        print("Monitoring Sync A (CREATE)...")
        print()
        get_latest_run(3394022, "SYNC A (CREATE)")
