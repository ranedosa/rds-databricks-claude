"""
Validate Census sync results in Databricks
"""
from databricks import sql
import os
from datetime import datetime

DATABRICKS_SERVER_HOSTNAME = "dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

def get_databricks_connection():
    """Create a Databricks SQL connection"""
    return sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

print("\n" + "="*80)
print("VALIDATING CENSUS SYNC RESULTS")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# 1. Check how many records were created today in product_property_c
print("\n" + "="*80)
print("1. RECORDS CREATED IN product_property_c TODAY")
print("="*80)

query1 = """
SELECT COUNT(*) as records_created_today
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
  AND reverse_etl_id_c IS NOT NULL
"""

cursor.execute(query1)
result = cursor.fetchone()
records_created = result[0]

print(f"\n✅ Records created today: {records_created:,}")

if records_created == 0:
    print("\n⚠️  No records found. The sync may have failed or not run yet.")
elif records_created < 50:
    print(f"\n📊 Partial sync detected - only {records_created} records")
    print("   This suggests a test batch was synced successfully!")
elif records_created >= 1297:
    print("\n🎉 FULL SYNC COMPLETED! All 1,297 records synced!")
else:
    print(f"\n📊 {records_created} records synced")
    print(f"   Progress: {records_created}/1,297 ({records_created/1297*100:.1f}%)")

# 2. Check field population
print("\n" + "="*80)
print("2. FIELD VALIDATION")
print("="*80)

query2 = """
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT snappt_property_id_c) as unique_snappt_ids,
    COUNT(DISTINCT reverse_etl_id_c) as unique_reverse_etl_ids,
    SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as missing_snappt_id,
    SUM(CASE WHEN reverse_etl_id_c IS NULL THEN 1 ELSE 0 END) as missing_reverse_etl_id,
    SUM(CASE WHEN snappt_property_id_c = reverse_etl_id_c THEN 1 ELSE 0 END) as matching_ids
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
"""

cursor.execute(query2)
result = cursor.fetchone()

print(f"\nTotal synced: {result[0]:,}")
print(f"Unique snappt_property_id_c: {result[1]:,}")
print(f"Unique reverse_etl_id_c: {result[2]:,}")
print(f"Missing snappt_property_id_c: {result[3]:,}")
print(f"Missing reverse_etl_id_c: {result[4]:,}")
print(f"IDs match (snappt = reverse_etl): {result[5]:,}")

if result[3] == 0 and result[4] == 0:
    print("\n✅ All required fields populated correctly!")
else:
    print("\n⚠️  Some fields are missing - check field mappings")

# 3. Sample records
print("\n" + "="*80)
print("3. SAMPLE SYNCED RECORDS")
print("="*80)

query3 = """
SELECT
    id,
    name,
    snappt_property_id_c,
    reverse_etl_id_c,
    status_c,
    company_name_c,
    created_date
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
ORDER BY created_date DESC
LIMIT 5
"""

cursor.execute(query3)
results = cursor.fetchall()

print(f"\nShowing {len(results)} sample records:\n")

for i, row in enumerate(results, 1):
    print(f"{i}. Property: {row[1]}")
    print(f"   Salesforce ID: {row[0]}")
    print(f"   Snappt Property ID: {row[2]}")
    print(f"   Reverse ETL ID: {row[3]}")
    print(f"   Status: {row[4]}")
    print(f"   Company: {row[5]}")
    print(f"   Created: {row[6]}")
    print()

# 4. Check RDS linkage
print("\n" + "="*80)
print("4. RDS LINKAGE VALIDATION")
print("="*80)

query4 = """
SELECT COUNT(*) as linked_count
FROM rds.pg_rds_public.properties rds
INNER JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE DATE(sf.created_date) = CURRENT_DATE()
"""

cursor.execute(query4)
result = cursor.fetchone()
linked_count = result[0]

print(f"\n✅ Records properly linked to RDS: {linked_count:,}")

if linked_count == records_created:
    print("✅ Perfect! All synced records are linked to RDS")
else:
    print(f"⚠️  Linkage issue: {records_created} created but only {linked_count} linked")

# 5. Show linked records sample
print("\n" + "="*80)
print("5. SAMPLE LINKED RECORDS (RDS ↔ Salesforce)")
print("="*80)

query5 = """
SELECT
    rds.id as rds_id,
    rds.name as rds_name,
    rds.status as rds_status,
    sf.id as sf_id,
    sf.name as sf_name,
    sf.status_c as sf_status
FROM rds.pg_rds_public.properties rds
INNER JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE DATE(sf.created_date) = CURRENT_DATE()
LIMIT 5
"""

cursor.execute(query5)
results = cursor.fetchall()

print(f"\nShowing {len(results)} linked records:\n")

for i, row in enumerate(results, 1):
    print(f"{i}. RDS Property: {row[1]} (Status: {row[2]})")
    print(f"   → Salesforce: {row[4]} (Status: {row[5]})")
    print(f"   RDS ID: {row[0]}")
    print(f"   SF ID: {row[3]}")
    print()

# 6. Check if workflows created property_c records
print("\n" + "="*80)
print("6. PROPERTY_C WORKFLOW VALIDATION")
print("="*80)

query6 = """
SELECT COUNT(*) as property_c_count
FROM hive_metastore.salesforce.product_property_c pp
INNER JOIN hive_metastore.salesforce.property_c p
    ON pp.sf_property_id_c = p.id
WHERE DATE(pp.created_date) = CURRENT_DATE()
"""

cursor.execute(query6)
result = cursor.fetchone()
property_c_count = result[0]

print(f"\n✅ Records flowed to property_c: {property_c_count:,}")

if property_c_count == records_created:
    print("✅ Perfect! All product_property_c records created property_c records")
elif property_c_count == 0:
    print("⚠️  No property_c records yet. Workflows may still be processing.")
    print("   Wait 10-15 minutes and check again.")
elif property_c_count < records_created:
    print(f"⏳ Partial completion: {property_c_count}/{records_created}")
    print("   Workflows may still be processing remaining records")

# 7. Check for any failures or orphans
print("\n" + "="*80)
print("7. ORPHAN/FAILURE CHECK")
print("="*80)

query7 = """
SELECT COUNT(*) as orphans
FROM hive_metastore.salesforce.product_property_c pp
LEFT JOIN hive_metastore.salesforce.property_c p
    ON pp.sf_property_id_c = p.id
WHERE DATE(pp.created_date) = CURRENT_DATE()
  AND pp.sf_property_id_c IS NULL
"""

cursor.execute(query7)
result = cursor.fetchone()
orphans = result[0]

if orphans == 0:
    print(f"\n✅ No orphan records (all have sf_property_id_c)")
else:
    print(f"\n⚠️  {orphans} orphan records (missing sf_property_id_c)")
    print("   These records haven't been picked up by workflows yet")

# 8. Overall summary
print("\n" + "="*80)
print("OVERALL SUMMARY")
print("="*80)

print(f"""
📊 Sync Results:
   ✓ Records synced to product_property_c: {records_created:,}
   ✓ Records linked to RDS: {linked_count:,}
   ✓ Records in property_c: {property_c_count:,}
   ✓ Orphan records: {orphans:,}
""")

if records_created >= 1297:
    print("🎉 FULL SYNC COMPLETE!")
    print("   All 1,297 properties have been synced successfully!")
elif records_created > 0:
    remaining = 1297 - records_created
    print(f"📈 Progress: {records_created:,}/1,297 ({records_created/1297*100:.1f}%)")
    print(f"   Remaining: {remaining:,} properties")
    print(f"   Batches remaining: ~{remaining//50 + 1}")
else:
    print("⚠️  No records found. Sync may not have run successfully.")

cursor.close()
conn.close()

print("\n" + "="*80)
print("VALIDATION COMPLETE")
print("="*80)
