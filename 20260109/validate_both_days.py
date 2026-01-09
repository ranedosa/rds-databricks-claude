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
print("COMPLETE DAY 3 VALIDATION - SYNC A (Jan 8) + SYNC B (Jan 9)")
print("="*80)
print()

# Sync A results (Jan 8)
print("SYNC A (CREATE) - January 8, 2026:")
print("-"*80)
query_creates = """
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE DATE(created_date) = '2026-01-08' AND _fivetran_deleted = false
"""
cursor.execute(query_creates)
sync_a_creates = cursor.fetchall()[0][0]
print(f"  Creates: {sync_a_creates:,}")
print(f"  Expected: 574-690")
print(f"  Status: {'✅ SUCCESS' if 574 <= sync_a_creates <= 690 else '⚠️ OUTSIDE RANGE'}")
print()

# Sync B results (Jan 9)
print("SYNC B (UPDATE) - January 9, 2026:")
print("-"*80)
query_updates = """
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = '2026-01-09'
  AND DATE(created_date) != '2026-01-09'
  AND _fivetran_deleted = false
"""
cursor.execute(query_updates)
sync_b_updates = cursor.fetchall()[0][0]
print(f"  Updates: {sync_b_updates:,}")
print(f"  Expected: 7,500-7,820")
print(f"  Status: {'✅ SUCCESS' if 7500 <= sync_b_updates <= 7820 else '⚠️ OUTSIDE RANGE'}")
print()

# Total records now
print("CURRENT STATE:")
print("-"*80)
query_total = """
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false
"""
cursor.execute(query_total)
total = cursor.fetchall()[0][0]
print(f"  Total Records: {total:,}")
print(f"  Expected: 18,450-18,560")
print(f"  Status: {'✅ WITHIN RANGE' if 18450 <= total <= 18560 else '⚠️ OUTSIDE RANGE'}")
print()

# Combined impact
print("="*80)
print("COMBINED IMPACT:")
print("="*80)
combined = sync_a_creates + sync_b_updates
print(f"  Total records affected: {combined:,}")
print(f"    - Sync A (creates): {sync_a_creates:,}")
print(f"    - Sync B (updates): {sync_b_updates:,}")
print()

# Check for data quality issues on both days
print("DATA QUALITY CHECK:")
print("-"*80)
query_issues = """
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
  AND _fivetran_deleted = false
  AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
"""
cursor.execute(query_issues)
issues = cursor.fetchall()[0][0]
print(f"  Records with missing fields: {issues}")
print(f"  Status: {'✅ NO ISSUES' if issues == 0 else '⚠️ NEEDS INVESTIGATION'}")
print()

# Overall assessment
print("="*80)
print("OVERALL DAY 3 ASSESSMENT:")
print("="*80)
success = (
    574 <= sync_a_creates <= 690 and
    7500 <= sync_b_updates <= 7820 and
    18450 <= total <= 18560 and
    issues == 0
)
print(f"  Status: {'✅ SUCCESS - Day 3 rollout complete!' if success else '⚠️ NEEDS REVIEW'}")
print()

if not success:
    print("ITEMS TO INVESTIGATE:")
    if not (574 <= sync_a_creates <= 690):
        print(f"  - Sync A creates ({sync_a_creates:,}) outside expected range")
    if not (7500 <= sync_b_updates <= 7820):
        print(f"  - Sync B updates ({sync_b_updates:,}) outside expected range")
    if not (18450 <= total <= 18560):
        print(f"  - Total records ({total:,}) outside expected range")
    if issues > 0:
        print(f"  - {issues} records have data quality issues")

cursor.close()
connection.close()
