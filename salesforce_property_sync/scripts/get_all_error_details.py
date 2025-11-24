"""
Comprehensive attempt to get error details from Census API
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
print(f"COMPREHENSIVE ERROR DETAIL SEARCH")
print("="*80)

# Try many different endpoint patterns
endpoints_to_try = [
    # Run details
    (f"/sync_runs/{RUN_ID}", "Direct run access"),
    (f"/syncs/{SYNC_ID}/sync_runs/{RUN_ID}", "Via sync path"),

    # Error/rejection endpoints
    (f"/sync_runs/{RUN_ID}/errors", "Run errors"),
    (f"/sync_runs/{RUN_ID}/rejected_records", "Rejected records"),
    (f"/sync_runs/{RUN_ID}/failed_records", "Failed records"),
    (f"/sync_runs/{RUN_ID}/failures", "Failures"),

    # Via sync path
    (f"/syncs/{SYNC_ID}/runs/{RUN_ID}/errors", "Sync run errors"),
    (f"/syncs/{SYNC_ID}/runs/{RUN_ID}/rejected_records", "Sync rejected records"),

    # Operations endpoints
    (f"/sync_runs/{RUN_ID}/operations", "Operations"),
    (f"/sync_runs/{RUN_ID}/records", "Records"),

    # Logs
    (f"/sync_runs/{RUN_ID}/logs", "Logs"),
    (f"/sync_runs/{RUN_ID}/log_entries", "Log entries"),
]

successful_endpoints = []

for endpoint, description in endpoints_to_try:
    url = f"{config['api_base_url']}{endpoint}"
    print(f"\n{'='*80}")
    print(f"📍 {description}")
    print(f"   {endpoint}")

    try:
        response = requests.get(url, headers=headers)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print(f"   ✅ SUCCESS!")
            data = response.json()

            successful_endpoints.append((endpoint, data))

            # Show keys
            if isinstance(data, dict):
                print(f"   Keys: {list(data.keys())}")

                # If there's a 'data' key, show its structure
                if 'data' in data:
                    data_content = data['data']
                    if isinstance(data_content, list) and len(data_content) > 0:
                        print(f"   Data is a list with {len(data_content)} items")
                        print(f"   First item keys: {list(data_content[0].keys()) if isinstance(data_content[0], dict) else 'Not a dict'}")
                    elif isinstance(data_content, dict):
                        print(f"   Data keys: {list(data_content.keys())}")

            # Print first 1500 chars
            print(f"\n   Preview:")
            print(json.dumps(data, indent=2, default=str)[:1500])

        elif response.status_code == 401:
            print(f"   ❌ Authentication error")
        elif response.status_code == 403:
            print(f"   ❌ Permission denied")
        elif response.status_code == 404:
            print(f"   ⚠️  Not found")
        else:
            print(f"   ⚠️  Unexpected status")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

# Summary
print(f"\n" + "="*80)
print("SUMMARY")
print("="*80)

if successful_endpoints:
    print(f"\n✅ Found {len(successful_endpoints)} working endpoints:")
    for endpoint, data in successful_endpoints:
        print(f"  - {endpoint}")

    # Try to extract error information from successful responses
    print(f"\n" + "="*80)
    print("ANALYZING RESPONSES FOR ERROR INFORMATION")
    print("="*80)

    for endpoint, data in successful_endpoints:
        print(f"\n📊 From {endpoint}:")

        # Look for error-related fields
        error_fields = ['error', 'errors', 'error_message', 'error_detail', 'error_code',
                       'rejected', 'failed', 'rejection_reason', 'failure_reason']

        def find_errors(obj, path=""):
            """Recursively search for error information"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if this key contains error info
                    if any(err_field in key.lower() for err_field in error_fields):
                        print(f"   Found error field: {current_path}")
                        print(f"   Value: {json.dumps(value, default=str)[:500]}")

                    # Recurse
                    find_errors(value, current_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj[:3]):  # Only check first 3 items
                    find_errors(item, f"{path}[{i}]")

        find_errors(data)
else:
    print("\n❌ No working endpoints found for error details")

# Try one more thing - get the full sync run data we got before
print(f"\n" + "="*80)
print("GETTING FULL SYNC RUN DATA")
print("="*80)

try:
    url = f"{config['api_base_url']}/syncs/{SYNC_ID}/sync_runs"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        runs = data.get('data', [])

        # Find our run
        our_run = next((r for r in runs if r.get('id') == RUN_ID), None)

        if our_run:
            print(f"\n✅ Found run {RUN_ID}")
            print(f"\nFull run data:")
            print(json.dumps(our_run, indent=2, default=str))

            # Look for any error information
            print(f"\n" + "="*80)
            print("ERROR ANALYSIS FROM RUN DATA")
            print("="*80)

            if our_run.get('error_message'):
                print(f"❌ Error Message: {our_run.get('error_message')}")
            if our_run.get('error_detail'):
                print(f"❌ Error Detail: {our_run.get('error_detail')}")
            if our_run.get('error_code'):
                print(f"❌ Error Code: {our_run.get('error_code')}")

            # Check if there's any other information
            print(f"\n📊 All fields in run:")
            for key, value in our_run.items():
                if 'error' in key.lower() or 'fail' in key.lower() or 'invalid' in key.lower():
                    print(f"  {key}: {value}")

except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("""
Unfortunately, the Census API doesn't seem to expose detailed error messages
through the API endpoints I can access.

The error details are only available in the Census UI at:
https://app.getcensus.com/workspaces/33026/syncs/3325886/sync-runs/404267254

Please check that page and look for:
1. "Rejected Records" tab or similar
2. Error messages for sample records
3. Any validation failures

Share the error message here and I can help fix it!
""")
