#!/usr/bin/env python3
import os
from databricks import sql

host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")
connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/95a8f5979c3f8740",
    access_token=os.getenv("DATABRICKS_TOKEN")
)
cursor = connection.cursor()

print("="*80)
print("CHECKING IF SYNC B COVERS SYNC A RECORDS")
print("="*80)
print()

# Check if the 574 properties created on Jan 8 are now in properties_to_update view
print("Question: Are the 574 properties created on Jan 8 now in properties_to_update?")
print("-"*80)

# Get sample of properties created on Jan 8
query_jan8 = """
SELECT snappt_property_id_c
FROM crm.salesforce.product_property
WHERE DATE(created_date) = '2026-01-08'
  AND _fivetran_deleted = false
LIMIT 10
"""

cursor.execute(query_jan8)
jan8_samples = [row[0] for row in cursor.fetchall()]

print(f"\nGot {len(jan8_samples)} sample properties created on Jan 8")

# Check if they're in properties_to_update view
query_check = f"""
SELECT COUNT(*) as count
FROM crm.sfdc_dbx.properties_to_update
WHERE rds_property_id IN ({','.join([f"'{id}'" for id in jan8_samples])})
"""

cursor.execute(query_check)
count_in_update_view = cursor.fetchall()[0][0]

print(f"Found in properties_to_update view: {count_in_update_view}/{len(jan8_samples)}")
print()

if count_in_update_view == len(jan8_samples):
    print("✅ YES - All Jan 8 created properties are now in properties_to_update")
    print()
    print("This means:")
    print("  • Sync B will update ALL properties including the 574 from Sync A")
    print("  • You can SKIP re-running Sync A")
    print("  • Just run Sync B and it will fix all ~9,715 company names")
elif count_in_update_view > 0:
    print("⚠️  PARTIAL - Some Jan 8 properties in update view")
    print()
    print("This suggests:")
    print("  • Most will be covered by Sync B")
    print("  • May need to run both syncs to be safe")
else:
    print("❌ NO - Jan 8 properties NOT in properties_to_update")
    print()
    print("This means:")
    print("  • You NEED to run both Sync A and Sync B")
    print("  • Sync A is still needed for the 574 properties")

print()
print("-"*80)

# Also check the view definitions
print("\nView Logic Check:")
print("-"*80)

print("\nproperties_to_create logic:")
print("  • Finds properties NOT YET in Salesforce (sf.id IS NULL)")
print("  • Since we already created 574 on Jan 8, they now exist in SF")
print("  • So they should NOT appear in properties_to_create anymore")

print("\nproperties_to_update logic:")
print("  • Finds properties ALREADY in Salesforce")
print("  • The 574 properties created Jan 8 now exist in SF")
print("  • So they SHOULD appear in properties_to_update")

# Check actual counts
print()
print("-"*80)
print("Actual View Counts:")
print("-"*80)

query_counts = """
SELECT 'properties_to_create' as view_name, COUNT(*) as count
FROM crm.sfdc_dbx.properties_to_create
UNION ALL
SELECT 'properties_to_update' as view_name, COUNT(*) as count
FROM crm.sfdc_dbx.properties_to_update
"""

cursor.execute(query_counts)
counts = cursor.fetchall()

for view_name, count in counts:
    print(f"  {view_name:<30} {count:>6,} records")

print()
print("="*80)
print("RECOMMENDATION")
print("="*80)
print()

if count_in_update_view == len(jan8_samples):
    print("✅ SKIP Sync A, ONLY run Sync B")
    print()
    print("Reasoning:")
    print("  • The 574 properties from Jan 8 now exist in Salesforce")
    print("  • They've moved from properties_to_create to properties_to_update")
    print("  • Sync B will update all ~9,715 properties (9,141 + 574)")
    print("  • Running Sync A would be redundant (it would find 0 new records)")
    print()
    print("Time saved: ~30-45 minutes")
else:
    print("⚠️  RUN BOTH Sync A and Sync B to be safe")
    print()
    print("Reasoning:")
    print("  • Not all Jan 8 properties found in properties_to_update")
    print("  • Better to run both syncs to ensure complete coverage")

print()

cursor.close()
connection.close()
