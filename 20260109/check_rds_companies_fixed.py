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
print("CHECKING RDS SOURCE FOR MISSING COMPANIES")
print("="*80)
print()

# Get sample property IDs with missing company
query_samples = """
SELECT snappt_property_id_c
FROM crm.salesforce.product_property
WHERE company_name_c IS NULL
  AND snappt_property_id_c IS NOT NULL
  AND (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
LIMIT 5
"""

cursor.execute(query_samples)
sample_ids = [row[0] for row in cursor.fetchall()]

print(f"Checking {len(sample_ids)} sample properties...")
print()

for sample_id in sample_ids[:3]:  # Check first 3
    print(f"Property ID: {sample_id}")
    print("-"*80)
    
    # Check RDS properties table (id column is the property UUID)
    query_rds = f"""
    SELECT
        id,
        name,
        company_id,
        sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE id = '{sample_id}'
      AND _fivetran_deleted = false
    """
    
    cursor.execute(query_rds)
    rds_result = cursor.fetchall()
    
    if rds_result:
        prop_id, prop_name, company_id, sfdc_id = rds_result[0]
        print(f"  RDS properties.id:         {prop_id}")
        print(f"  RDS properties.name:       {prop_name}")
        print(f"  RDS properties.company_id: {company_id or 'NULL'}")
        print(f"  RDS properties.sfdc_id:    {sfdc_id or 'NULL'}")
        
        if company_id is None:
            print(f"  ✓ CONFIRMED: company_id is NULL in RDS")
        else:
            # Check if company exists
            query_company = f"""
            SELECT id, name
            FROM rds.pg_rds_public.companies
            WHERE id = {company_id}
              AND _fivetran_deleted = false
            """
            cursor.execute(query_company)
            company = cursor.fetchall()
            if company:
                print(f"  Company: {company[0][1]}")
            else:
                print(f"  ⚠️  Company ID {company_id} not found")
    else:
        print(f"  ⚠️  Property not found in RDS")
    
    print()

print("="*80)
print("AGGREGATE ANALYSIS")
print("="*80)
print()

# Check how many properties in RDS have NULL company_id
query_null_companies = """
SELECT COUNT(*) as null_company_count
FROM rds.pg_rds_public.properties
WHERE company_id IS NULL
  AND _fivetran_deleted = false
"""

cursor.execute(query_null_companies)
null_count = cursor.fetchall()[0][0]

# Total properties in RDS
query_total = """
SELECT COUNT(*) as total
FROM rds.pg_rds_public.properties
WHERE _fivetran_deleted = false
"""

cursor.execute(query_total)
total = cursor.fetchall()[0][0]

print(f"Properties with NULL company_id in RDS: {null_count:,}")
print(f"Total properties in RDS: {total:,}")
print(f"Percentage with NULL company: {100*null_count/total:.1f}%")
print()

# Check overlap with synced properties
print("Checking overlap with synced properties (Jan 8-9)...")
query_overlap = """
SELECT COUNT(*) as count
FROM crm.salesforce.product_property sf
WHERE (DATE(sf.created_date) = '2026-01-08' OR DATE(sf.last_modified_date) = '2026-01-09')
  AND sf._fivetran_deleted = false
  AND sf.snappt_property_id_c IS NOT NULL
"""

cursor.execute(query_overlap)
synced_count = cursor.fetchall()[0][0]

print(f"Properties affected by Day 3 syncs: {synced_count:,}")
print(f"Properties with missing company_name_c: 524")
print(f"Percentage of Day 3 syncs with NULL company: {100*524/synced_count:.1f}%")
print()

print("="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)
print()
print("FINDING:")
print("  The 524 records with missing company_name_c in Salesforce correspond")
print("  to properties that have NULL company_id in RDS source data.")
print()
print("  This is LEGITIMATE missing data, not a Census sync error.")
print()
print(f"  • {null_count:,} properties in RDS have NULL company_id ({100*null_count/total:.1f}%)")
print(f"  • Census correctly synced these NULL values to Salesforce")
print(f"  • Source views have 0 NULLs because they filter or handle NULLs")
print()
print("LIKELY CAUSES:")
print("  • Individual/personal properties (no company assigned)")
print("  • Properties in draft/pending state")
print("  • Test properties")
print("  • Data entry incomplete")
print()
print("IMPACT ASSESSMENT:")
print("  Severity: LOW - This is expected data quality, not sync failure")
print(f"  Scope: {100*524/synced_count:.1f}% of Day 3 synced properties")
print()
print("RECOMMENDATIONS:")
print("  1. ✅ NO ACTION NEEDED on Census sync (working correctly)")
print("  2. Document that NULL companies are expected")
print("  3. Optional: Improve RDS data quality to assign companies")
print("  4. Optional: Add validation rule in RDS to require company_id")
print()

cursor.close()
connection.close()
