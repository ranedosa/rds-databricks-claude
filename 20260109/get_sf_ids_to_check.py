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
print("SALESFORCE IDs TO CHECK MANUALLY")
print("="*80)
print()

# Get Salesforce IDs for known broken properties
query = """
SELECT
    sf.id as salesforce_id,
    sf.name as property_name,
    sf.company_name_c as current_sf_company,
    c.name as expected_company,
    sf.snappt_property_id_c
FROM crm.salesforce.product_property sf
INNER JOIN rds.pg_rds_public.properties p
    ON sf.snappt_property_id_c = p.id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
    AND c._fivetran_deleted = false
WHERE sf.name IN (
    'Hardware',
    'Rowan',
    'Skymor Wesley Chapel',
    'The Storey',
    'South and Twenty'
)
AND sf._fivetran_deleted = false
"""

cursor.execute(query)
results = cursor.fetchall()

print("Known Properties to Check:")
print("-"*80)

for sf_id, prop_name, current_company, expected_company, snappt_id in results:
    print(f"\nProperty: {prop_name}")
    print(f"  Salesforce ID: {sf_id}")
    print(f"  Snappt Property ID: {snappt_id}")
    print(f"  Current company_name_c: {current_company or 'NULL'}")
    print(f"  Expected company: {expected_company or 'NULL'}")
    print(f"  Status: {'❌ WRONG' if current_company == prop_name else '✅ CORRECT' if current_company == expected_company else '❓ CHECK'}")

print()
print("="*80)
print("HOW TO CHECK IN SALESFORCE:")
print("="*80)
print()
print("1. Go to Salesforce")
print("2. In the search bar at top, paste one of the Salesforce IDs above")
print("3. Open the Product_Property__c record")
print("4. Look at the Company_Name__c field")
print("5. Compare with the 'Expected company' above")
print()
print("Example: For 'Hardware' property:")
print("  • If Company_Name__c = 'Hardware' → ❌ Sync didn't work")
print("  • If Company_Name__c = 'Greystar' → ✅ Sync worked!")
print()

# Also get a couple of records that were recently modified
print("-"*80)
print("\nRecently Modified Records (for comparison):")
print("-"*80)

query_recent = """
SELECT
    sf.id as salesforce_id,
    sf.name as property_name,
    sf.company_name_c as current_company,
    sf.last_modified_date
FROM crm.salesforce.product_property sf
WHERE DATE(sf.last_modified_date) >= '2026-01-09'
  AND sf._fivetran_deleted = false
ORDER BY sf.last_modified_date DESC
LIMIT 5
"""

cursor.execute(query_recent)
recent = cursor.fetchall()

for sf_id, prop_name, company, modified in recent:
    status = "❌ BROKEN" if prop_name == company else "✅ LOOKS OK"
    print(f"\n  SF ID: {sf_id}")
    print(f"  Property: {prop_name[:50]}")
    print(f"  Company: {company or 'NULL'}")
    print(f"  Modified: {modified}")
    print(f"  {status}")

cursor.close()
connection.close()
