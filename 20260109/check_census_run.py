#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime

# Census API setup
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
CENSUS_BASE_URL = "https://app.getcensus.com/api/v1"

headers = {
    "Authorization": f"Bearer {CENSUS_API_KEY}",
    "Content-Type": "application/json"
}

print("="*80)
print("CENSUS SYNC RUN STATUS - Run ID: 426063959")
print("="*80)
print()

# Get sync run details
run_id = "426063959"
url = f"{CENSUS_BASE_URL}/sync_runs/{run_id}"

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        run = response.json()
        
        print("Sync Run Details:")
        print("-"*80)
        print(f"  Run ID: {run.get('id')}")
        print(f"  Sync ID: {run.get('sync_id')}")
        print(f"  Status: {run.get('status')}")
        print(f"  Started: {run.get('created_at')}")
        
        if run.get('completed_at'):
            print(f"  Completed: {run.get('completed_at')}")
        
        print()
        print("Record Statistics:")
        print("-"*80)
        
        records_processed = run.get('records_processed', 0)
        records_updated = run.get('records_updated', 0)
        records_failed = run.get('records_failed', 0)
        records_invalid = run.get('records_invalid', 0)
        
        print(f"  Records Processed: {records_processed:,}")
        print(f"  Records Updated: {records_updated:,}")
        print(f"  Records Failed: {records_failed:,}")
        print(f"  Records Invalid: {records_invalid:,}")
        
        if records_processed > 0:
            success_rate = 100 * (records_updated) / records_processed
            error_rate = 100 * (records_failed + records_invalid) / records_processed
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Error Rate: {error_rate:.1f}%")
        
        print()
        
        # Status interpretation
        status = run.get('status', '').upper()
        
        if status == 'COMPLETED':
            print("✅ SYNC COMPLETED SUCCESSFULLY")
            print()
            print(f"Summary: Updated {records_updated:,} records")
            if records_failed > 0 or records_invalid > 0:
                print(f"  ⚠️  {records_failed + records_invalid} records had issues")
        elif status == 'RUNNING' or status == 'WORKING':
            print("🔄 SYNC IN PROGRESS")
            print()
            print(f"Progress: {records_processed:,} records processed so far")
        elif status == 'FAILED':
            print("❌ SYNC FAILED")
            print()
            print(f"Error: {run.get('error_message', 'Unknown error')}")
        elif status == 'CANCELLED':
            print("⚠️  SYNC CANCELLED")
        else:
            print(f"Status: {status}")
        
        print()
        
        # Check if this is Sync B
        sync_id = run.get('sync_id')
        if sync_id == 3394041:
            print("✅ This is Sync B (UPDATE)")
            print(f"   Expected: ~9,141 records")
            print(f"   Actual: {records_processed:,} processed, {records_updated:,} updated")
            
            if records_updated >= 9000:
                print(f"   ✅ Count matches expected range")
            else:
                print(f"   ⚠️  Lower than expected - may need investigation")
        
        # Get error details if any
        if records_failed > 0 or records_invalid > 0:
            print()
            print("Error Details:")
            print("-"*80)
            
            # Try to get error samples
            errors_url = f"{CENSUS_BASE_URL}/sync_runs/{run_id}/records?status=failed"
            errors_response = requests.get(errors_url, headers=headers)
            
            if errors_response.status_code == 200:
                errors = errors_response.json()
                if errors:
                    print(f"Sample errors (first 5):")
                    for i, error in enumerate(errors[:5], 1):
                        print(f"  {i}. {error.get('error_message', 'Unknown error')}")
            else:
                print(f"  Could not retrieve error details")
        
    elif response.status_code == 404:
        print("❌ Run ID not found")
        print()
        print("This could mean:")
        print("  • The run ID is incorrect")
        print("  • The run hasn't started yet")
        print("  • You don't have access to this sync")
    elif response.status_code == 401:
        print("❌ Authentication failed")
        print()
        print("Check that CENSUS_API_KEY environment variable is set correctly")
    else:
        print(f"❌ Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Error checking Census run: {str(e)}")
    print()
    print("Trying alternative method...")
    
    # Alternative: Check via sync ID
    print()
    print("Checking Sync B (ID: 3394041) recent runs:")
    print("-"*80)
    
    sync_url = f"{CENSUS_BASE_URL}/syncs/3394041/sync_runs"
    try:
        sync_response = requests.get(sync_url, headers=headers)
        if sync_response.status_code == 200:
            runs = sync_response.json()
            
            # Find our run
            for run in runs[:10]:  # Check last 10 runs
                if str(run.get('id')) == run_id:
                    print(f"Found run {run_id}:")
                    print(f"  Status: {run.get('status')}")
                    print(f"  Records Processed: {run.get('records_processed', 0):,}")
                    print(f"  Records Updated: {run.get('records_updated', 0):,}")
                    break
        else:
            print(f"Could not retrieve sync runs: HTTP {sync_response.status_code}")
    except Exception as e2:
        print(f"Error: {str(e2)}")

print()
print("="*80)
