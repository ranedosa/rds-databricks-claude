#!/usr/bin/env python3
import os
import requests

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
CENSUS_BASE_URL = "https://app.getcensus.com/api/v1"

headers = {
    "Authorization": f"Bearer {CENSUS_API_KEY}",
    "Content-Type": "application/json"
}

print("="*80)
print("CHECKING RECENT SYNC B RUNS")
print("="*80)
print()

# Get recent runs for Sync B
sync_id = 3394041
url = f"{CENSUS_BASE_URL}/syncs/{sync_id}/sync_runs"

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        runs = data.get('data', []) if isinstance(data, dict) else data
        
        print(f"Recent runs for Sync B (ID: {sync_id}):")
        print("-"*80)
        
        target_run_id = "426063959"
        found_target = False
        
        for i, run in enumerate(runs[:10], 1):
            run_id = str(run.get('id', ''))
            status = run.get('status', 'unknown')
            created = run.get('created_at', 'N/A')
            completed = run.get('completed_at', 'N/A')
            processed = run.get('records_processed', 0)
            updated = run.get('records_updated', 0)
            failed = run.get('records_failed', 0)
            invalid = run.get('records_invalid', 0)
            
            is_target = run_id == target_run_id
            marker = "👉 TARGET RUN" if is_target else ""
            
            print(f"\n{i}. Run ID: {run_id} {marker}")
            print(f"   Status: {status}")
            print(f"   Started: {created}")
            if completed != 'N/A':
                print(f"   Completed: {completed}")
            print(f"   Records: {processed:,} processed, {updated:,} updated")
            if failed > 0 or invalid > 0:
                print(f"   Errors: {failed:,} failed, {invalid:,} invalid")
            
            if is_target:
                found_target = True
                print()
                print("="*80)
                print("TARGET RUN DETAILS")
                print("="*80)
                print(f"Status: {status.upper()}")
                print(f"Records Processed: {processed:,}")
                print(f"Records Updated: {updated:,}")
                print(f"Records Failed: {failed:,}")
                print(f"Records Invalid: {invalid:,}")
                
                if processed > 0:
                    success_rate = 100 * updated / processed
                    error_rate = 100 * (failed + invalid) / processed
                    print(f"Success Rate: {success_rate:.1f}%")
                    print(f"Error Rate: {error_rate:.1f}%")
                
                print()
                
                if status.lower() == 'completed':
                    print("✅ SYNC COMPLETED SUCCESSFULLY")
                    print()
                    print("Company Name Fix Impact:")
                    print(f"  • {updated:,} properties now have correct company names")
                    print(f"  • Expected ~9,141 (actual: {processed:,})")
                    
                    if 9000 <= processed <= 10000:
                        print(f"  • ✅ Count within expected range")
                    else:
                        print(f"  • ⚠️  Count differs from expected")
                    
                    if error_rate < 1:
                        print(f"  • ✅ Error rate excellent ({error_rate:.1f}%)")
                    else:
                        print(f"  • ⚠️  Error rate higher than expected ({error_rate:.1f}%)")
                    
                elif status.lower() in ['running', 'working']:
                    print("🔄 SYNC STILL RUNNING")
                    print(f"Progress: {processed:,} / ~9,141 expected")
                    
                elif status.lower() == 'failed':
                    print("❌ SYNC FAILED")
                    error_msg = run.get('error_message', 'No error message available')
                    print(f"Error: {error_msg}")
                
                print("="*80)
        
        if not found_target:
            print(f"\n⚠️  Run ID {target_run_id} not found in recent runs")
            print("This could mean:")
            print("  • The run ID is from a different sync")
            print("  • The run is older than the last 10 runs")
            print("  • There was a typo in the run ID")
    else:
        print(f"❌ Error: HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")

except Exception as e:
    print(f"❌ Error: {str(e)}")

print()
