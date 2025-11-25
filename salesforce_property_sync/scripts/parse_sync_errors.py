"""
Parse and display sync error details
"""
import requests
import json
from collections import Counter

CENSUS_CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
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
print(f"PARSING SYNC ERROR DETAILS")
print("="*80)

# Get all records with their statuses
url = f"{config['api_base_url']}/sync_runs/{RUN_ID}/records?limit=1000"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    records = data.get('data', [])

    print(f"\n✅ Retrieved {len(records)} record details\n")

    # Analyze statuses
    statuses = Counter([r.get('status') for r in records])

    print("="*80)
    print("STATUS BREAKDOWN")
    print("="*80)
    for status, count in statuses.items():
        print(f"  {status}: {count:,} records")

    # Get unique error messages
    error_messages = {}
    for record in records:
        status = record.get('status')
        if status == 'rejected':
            msg = record.get('status_message', '')
            # Extract the key part of the error
            if msg not in error_messages:
                error_messages[msg] = 0
            error_messages[msg] += 1

    print("\n" + "="*80)
    print("ERROR MESSAGES")
    print("="*80)

    for i, (msg, count) in enumerate(error_messages.items(), 1):
        print(f"\n{i}. Error affecting {count:,} records:")
        print(f"   {msg[:500]}")  # First 500 chars

    # Show sample rejected records
    print("\n" + "="*80)
    print("SAMPLE REJECTED RECORDS (First 3)")
    print("="*80)

    rejected = [r for r in records if r.get('status') == 'rejected'][:3]

    for i, record in enumerate(rejected, 1):
        print(f"\n{i}. Record ID: {record.get('identifier')}")
        print(f"   Status: {record.get('status')}")
        print(f"   Error Message:")
        print(f"   {record.get('status_message', 'No message')}")

        print(f"\n   Record Data (sample fields):")
        payload = record.get('record_payload', {})
        for key in ['name', 'snappt_property_id_c', 'status_c', 'company_name_c']:
            if key in payload:
                print(f"     {key}: {payload[key]}")

    # Analyze the specific error
    print("\n" + "="*80)
    print("ERROR ANALYSIS")
    print("="*80)

    if rejected:
        error_msg = rejected[0].get('status_message', '')

        if 'CANNOT_EXECUTE_FLOW_TRIGGER' in error_msg:
            print("\n🚨 ROOT CAUSE: Salesforce Flow Failure")
            print("\nThe issue is:")
            print("  ❌ A Salesforce Flow is blocking the inserts")

            if 'Limit Exceeded' in error_msg:
                print("  ❌ The Flow is hitting Salesforce governor limits")

            if 'Product Property | After | Rollup Flow' in error_msg:
                print("\n📋 Flow Name: 'Product Property | After | Rollup Flow'")

            print("\n" + "-"*80)
            print("EXPLANATION")
            print("-"*80)
            print("""
When you insert records into product_property_c, a Salesforce Flow
called "Product Property | After | Rollup Flow" automatically triggers.

This flow is likely performing calculations, rollups, or other operations.
However, it's hitting Salesforce governor limits when processing 1,297
records at once.

Salesforce Governor Limits that might be exceeded:
  - Total number of SOQL queries (101 limit)
  - Total number of DML statements (150 limit)
  - Total number of records processed by DML (10,000 limit)
  - CPU time limit (10,000ms for synchronous)
  - Heap size limit (6MB for synchronous)
""")

            print("\n" + "-"*80)
            print("SOLUTIONS")
            print("-"*80)
            print("""
Option 1: Sync in Smaller Batches (RECOMMENDED)
  - Instead of 1,297 records, sync 50-100 at a time
  - This prevents the Flow from hitting limits
  - More reliable but takes longer

Option 2: Disable/Modify the Flow Temporarily
  - Ask Salesforce admin to temporarily disable the Flow
  - Sync all records
  - Re-enable the Flow
  - Note: This skips the rollup calculations during sync

Option 3: Optimize the Flow
  - Have Salesforce admin review the Flow
  - Optimize queries and DML operations
  - Use bulkification best practices
  - Make it more efficient

Option 4: Use Asynchronous Processing
  - Modify the Flow to run asynchronously
  - Or use a separate process for the rollups
  - This avoids synchronous limits
""")

            print("\n" + "-"*80)
            print("RECOMMENDED NEXT STEP")
            print("-"*80)
            print("""
TRY SYNCING IN SMALLER BATCHES:

1. In Census, edit your sync
2. Add a limit to process fewer records per run
3. Try syncing 50-100 records first
4. If successful, you can increase batch size
5. Or run the sync multiple times with filters

This is the safest approach that doesn't require Salesforce changes.
""")

else:
    print("\n❌ Could not retrieve record details")

print("\n" + "="*80)
print("FULL ERROR MESSAGE")
print("="*80)

if rejected:
    print(rejected[0].get('status_message', ''))
