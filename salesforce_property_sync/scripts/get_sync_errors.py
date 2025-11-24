"""
Get detailed error information from Census sync run
"""
import requests
import json

CENSUS_CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
SYNC_ID = 3325886
RUN_ID = 404267254

def load_census_credentials():
    with open(CENSUS_CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_headers(api_key):
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

config = load_census_credentials()
headers = get_headers(config['api_key'])

print("\n" + "="*80)
print(f"GETTING DETAILED ERROR INFORMATION")
print("="*80)

# Get run details
url = f"{config['api_base_url']}/syncs/{SYNC_ID}/sync_runs/{RUN_ID}"
print(f"\n🔍 Fetching run details...")

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json().get('data', {})

    print(f"\n✅ Run Details Retrieved\n")
    print("="*80)
    print("SYNC RUN SUMMARY")
    print("="*80)

    print(f"\nRun ID: {data.get('id')}")
    print(f"Sync ID: {data.get('sync_id')}")
    print(f"Status: {data.get('status')}")
    print(f"Triggered: {data.get('sync_trigger_reason', {}).get('ui_detail', 'Unknown')}")

    print(f"\n📊 Statistics:")
    print(f"  Source Records: {data.get('source_record_count', 0):,}")
    print(f"  Records Processed: {data.get('records_processed', 0):,}")
    print(f"  Records Updated: {data.get('records_updated', 0):,}")
    print(f"  ❌ Records Failed: {data.get('records_failed', 0):,}")
    print(f"  Records Invalid: {data.get('records_invalid', 0):,}")

    print(f"\n⏱️  Timing:")
    print(f"  Created: {data.get('created_at')}")
    print(f"  Completed: {data.get('completed_at')}")

    # Error information
    error_code = data.get('error_code')
    error_message = data.get('error_message')
    error_detail = data.get('error_detail')

    if error_code or error_message or error_detail:
        print(f"\n🚨 ERROR INFORMATION:")
        if error_code:
            print(f"  Code: {error_code}")
        if error_message:
            print(f"  Message: {error_message}")
        if error_detail:
            print(f"  Detail: {error_detail}")

    # Full JSON for debugging
    print(f"\n" + "="*80)
    print("FULL RUN DATA (for debugging)")
    print("="*80)
    print(json.dumps(data, indent=2, default=str))

except Exception as e:
    print(f"❌ Error: {e}")

# Try to get error logs/samples
print(f"\n" + "="*80)
print("ATTEMPTING TO GET ERROR SAMPLES")
print("="*80)

error_endpoints = [
    f"/syncs/{SYNC_ID}/sync_runs/{RUN_ID}/errors",
    f"/syncs/{SYNC_ID}/sync_runs/{RUN_ID}/failures",
    f"/syncs/{SYNC_ID}/sync_runs/{RUN_ID}/logs",
]

for endpoint in error_endpoints:
    url = f"{config['api_base_url']}{endpoint}"
    print(f"\n🔍 Trying: {endpoint}")

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS!")
            print(json.dumps(data, indent=2, default=str)[:2000])
        else:
            print(f"   ⚠️  Status: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

print("""
To see detailed error information:

1. Go to Census UI:
   https://app.getcensus.com/workspaces/33026/syncs/3325886/sync-runs/404267254

2. Look for:
   - Rejected Records tab
   - Error messages
   - Validation failures

Common causes of 100% failure:
  ❌ Required field missing in Salesforce
  ❌ Invalid field mapping
  ❌ Sync key field doesn't exist or isn't an External ID
  ❌ Salesforce validation rules blocking inserts
  ❌ Permission issues with Census service account
  ❌ Data type mismatches

Next steps:
  1. Check Census UI for specific error messages
  2. Verify field mappings in Census
  3. Check Salesforce validation rules on Product_Property__c
  4. Ensure reverse_etl_id_c is marked as External ID in Salesforce
""")
