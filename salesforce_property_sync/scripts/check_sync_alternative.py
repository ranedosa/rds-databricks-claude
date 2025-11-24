"""
Alternative method to check Census sync using different API endpoints
"""
import requests
import json

CENSUS_CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
SYNC_ID = 3325886

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
print(f"CHECKING SYNC {SYNC_ID} - ALTERNATIVE METHOD")
print("="*80)

# Try different API endpoints
endpoints_to_try = [
    f"/syncs/{SYNC_ID}",
    f"/syncs/{SYNC_ID}/runs",
    f"/syncs/{SYNC_ID}/sync_runs",
    f"/sync_runs?sync_id={SYNC_ID}",
]

for endpoint in endpoints_to_try:
    url = f"{config['api_base_url']}{endpoint}"
    print(f"\n🔍 Trying: {url}")

    try:
        response = requests.get(url, headers=headers)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS!")
            print(f"   Response keys: {list(data.keys())}")

            # Pretty print the response
            print(f"\n   Data:")
            print(json.dumps(data, indent=4, default=str)[:1000])  # First 1000 chars

    except Exception as e:
        print(f"   ❌ Error: {e}")

# Also try to get all sync runs (without filtering by sync_id)
print("\n" + "="*80)
print("TRYING TO GET ALL RECENT SYNC RUNS")
print("="*80)

try:
    url = f"{config['api_base_url']}/sync_runs?limit=20"
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        runs = data.get('data', [])
        print(f"\n✅ Found {len(runs)} recent runs across all syncs")

        # Look for runs from our sync
        our_runs = [r for r in runs if r.get('sync_id') == SYNC_ID]

        if our_runs:
            print(f"\n🎯 Found {len(our_runs)} runs for sync {SYNC_ID}:")
            for run in our_runs:
                print(f"\n  Run ID: {run.get('id')}")
                print(f"  Status: {run.get('status')}")
                print(f"  Created: {run.get('created_at')}")
                print(f"  Records Processed: {run.get('records_processed', 0):,}")
                print(f"  Records Failed: {run.get('records_failed', 0):,}")
        else:
            print(f"\n⚠️  No runs found for sync {SYNC_ID}")
            print("\nThis could mean:")
            print("  1. The sync hasn't run yet")
            print("  2. The sync is still initializing")
            print("  3. The runs use a different sync_id format")

except Exception as e:
    print(f"❌ Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
