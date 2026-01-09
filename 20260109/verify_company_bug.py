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
print("VERIFYING COMPANY_NAME BUG HYPOTHESIS")
print("="*80)
print()

# Query to check if company_name_c matches property name or actual company name
query = """
SELECT
    sf.name as salesforce_property_name,
    sf.company_name_c as salesforce_company_name,
    p.name as rds_property_name,
    c.name as actual_company_name,
    CASE
        WHEN sf.company_name_c = p.name THEN 'BUG_CONFIRMED_PROPERTY_NAME'
        WHEN sf.company_name_c = c.name THEN 'CORRECT_COMPANY_NAME'
        WHEN sf.company_name_c IS NULL AND p.name IS NULL THEN 'PROPERTY_NAME_NULL'
        WHEN sf.company_name_c IS NULL AND c.name IS NULL THEN 'COMPANY_NAME_NULL'
        WHEN sf.company_name_c IS NULL THEN 'SF_NULL_BUT_DATA_EXISTS'
        ELSE 'OTHER'
    END as status
FROM crm.salesforce.product_property sf
INNER JOIN rds.pg_rds_public.properties p
    ON sf.snappt_property_id_c = p.id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
    AND c._fivetran_deleted = false
WHERE (DATE(sf.created_date) = '2026-01-08'
   OR DATE(sf.last_modified_date) = '2026-01-09')
  AND sf._fivetran_deleted = false
LIMIT 50
"""

cursor.execute(query)
results = cursor.fetchall()

# Analyze results
status_counts = {}
for row in results:
    status = row[4]
    status_counts[status] = status_counts.get(status, 0) + 1

print("Sample Analysis (first 50 records):")
print("-"*80)
for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {status:<35} {count:>3} records")

print()
print("Sample Records:")
print("-"*80)
print(f"{'SF Property Name':<30} {'SF Company':<30} {'RDS Property':<30} {'Actual Company':<30} {'Status':<25}")
print("-"*140)

for row in results[:15]:
    sf_prop = (row[0][:27] + "...") if row[0] and len(str(row[0])) > 30 else (row[0] or "NULL")
    sf_comp = (row[1][:27] + "...") if row[1] and len(str(row[1])) > 30 else (row[1] or "NULL")
    rds_prop = (row[2][:27] + "...") if row[2] and len(str(row[2])) > 30 else (row[2] or "NULL")
    actual_comp = (row[3][:27] + "...") if row[3] and len(str(row[3])) > 30 else (row[3] or "NULL")
    status = row[4]
    print(f"{str(sf_prop):<30} {str(sf_comp):<30} {str(rds_prop):<30} {str(actual_comp):<30} {status:<25}")

print()
print("="*80)
print("BUG VERIFICATION RESULT")
print("="*80)
print()

if 'BUG_CONFIRMED_PROPERTY_NAME' in status_counts:
    print(f"🔴 BUG CONFIRMED!")
    print(f"   {status_counts['BUG_CONFIRMED_PROPERTY_NAME']} records have property name as company name")
    print()
elif 'SF_NULL_BUT_DATA_EXISTS' in status_counts:
    print(f"⚠️  PARTIAL BUG CONFIRMED!")
    print(f"   {status_counts.get('SF_NULL_BUT_DATA_EXISTS', 0)} records have NULL in SF but data exists in RDS")
    print()
    print("   This suggests the view ISN'T syncing company names correctly")
    print()
elif 'PROPERTY_NAME_NULL' in status_counts:
    print(f"ℹ️  ALTERNATE THEORY:")
    print(f"   {status_counts.get('PROPERTY_NAME_NULL', 0)} records have NULL property names")
    print()
    print("   The view uses p.name AS company_name,")
    print("   so when property.name is NULL, company_name becomes NULL")
    print()
else:
    print(f"✅ NO BUG DETECTED (or different issue)")
    print()

print("Status breakdown from sample:")
for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    pct = 100 * count / len(results)
    print(f"  {status:<35} {count:>3} ({pct:>5.1f}%)")

cursor.close()
connection.close()
