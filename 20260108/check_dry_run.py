#!/usr/bin/env python3
"""
Check if the last sync was a dry run
"""
import requests

CENSUS_API_TOKEN = "secret-token:HyMHBwFx95V4gdjdqufvfZuz"
url = "https://app.getcensus.com/api/v1/syncs/3394022/sync_runs"

headers = {"Authorization": f"Bearer {CENSUS_API_TOKEN}"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    runs = response.json()['data']
    if runs:
        latest = runs[0]

        print("=" * 80)
        print("LAST SYNC RUN DETAILS")
        print("=" * 80)
        print()
        print(f"Run ID: {latest.get('id')}")
        print(f"Status: {latest.get('status')}")
        print(f"Started: {latest.get('created_at')}")
        print()
        print(f"🔍 DRY RUN: {latest.get('dry_run')}")
        print(f"Full Sync: {latest.get('full_sync')}")
        print()
        print(f"Records Processed: {latest.get('records_processed')}")
        print(f"Records Updated: {latest.get('records_updated')}")
        print(f"Records Failed: {latest.get('records_failed')}")
        print(f"Records Invalid: {latest.get('records_invalid')}")
        print()

        if latest.get('dry_run'):
            print("⚠️⚠️⚠️ THIS WAS A DRY RUN ⚠️⚠️⚠️")
            print()
            print("The sync ran in test mode and DID NOT create records in Salesforce.")
            print()
            print("To run for real:")
            print("1. Go to Census UI: https://app.getcensus.com/syncs/3394022")
            print("2. Turn OFF 'Dry Run' mode")
            print("3. Trigger sync again")
        else:
            print("✅ This was a REAL sync (not dry run)")
            print()
            print("If records aren't showing up, possible reasons:")
            print("1. Sync delay (check Salesforce in 5-10 minutes)")
            print("2. Data went to wrong Salesforce org")
            print("3. Salesforce validation rules blocked them")
else:
    print(f"Error: {response.status_code}")
