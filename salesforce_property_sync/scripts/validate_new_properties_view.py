"""
Validate the new_properties_with_features view after creation
"""
from databricks import sql
import os

DATABRICKS_SERVER_HOSTNAME = "dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

def get_databricks_connection():
    return sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

print("\n" + "="*80)
print("VALIDATING NEW PROPERTIES WITH FEATURES VIEW")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Test 1: Check if view exists
print("\n1. Checking if view exists...")
try:
    cursor.execute("DESCRIBE TABLE crm.sfdc_dbx.new_properties_with_features")
    columns = cursor.fetchall()
    print(f"✅ View exists with {len(columns)} columns")
except Exception as e:
    print(f"❌ Error: View doesn't exist or can't be accessed")
    print(f"   {e}")
    exit(1)

# Test 2: Count records
print("\n2. Counting new properties...")
cursor.execute("""
    SELECT COUNT(*) as total
    FROM crm.sfdc_dbx.new_properties_with_features
""")
total = cursor.fetchone()[0]
print(f"✅ Found {total:,} properties ready to sync")

if total == 0:
    print("\n⚠️  Warning: No new properties found!")
    print("   This could mean:")
    print("   - All properties are already in Salesforce (good!)")
    print("   - Or there's an issue with the view query")
elif total > 1000:
    print(f"\n⚠️  Warning: Large number of properties ({total:,})")
    print("   Consider syncing in batches or checking why so many are missing")

# Test 3: Feature data statistics
print("\n3. Checking feature data...")
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as fraud_enabled,
        SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as iv_enabled,
        SUM(CASE WHEN id_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as idv_enabled,
        SUM(CASE WHEN connected_payroll_enabled_c = TRUE THEN 1 ELSE 0 END) as payroll_enabled,
        SUM(CASE WHEN bank_linking_enabled_c = TRUE THEN 1 ELSE 0 END) as bank_enabled,
        SUM(CASE WHEN verification_of_rent_enabled_c = TRUE THEN 1 ELSE 0 END) as vor_enabled
    FROM crm.sfdc_dbx.new_properties_with_features
""")

stats = cursor.fetchone()
print(f"\nFeature enablement breakdown:")
print(f"  Total properties: {stats[0]:,}")
print(f"  Fraud Detection: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
print(f"  Income Verification: {stats[2]:,} ({stats[2]/stats[0]*100:.1f}%)")
print(f"  ID Verification: {stats[3]:,} ({stats[3]/stats[0]*100:.1f}%)")
print(f"  Connected Payroll: {stats[4]:,} ({stats[4]/stats[0]*100:.1f}%)")
print(f"  Bank Linking: {stats[5]:,} ({stats[5]/stats[0]*100:.1f}%)")
print(f"  Verification of Rent: {stats[6]:,} ({stats[6]/stats[0]*100:.1f}%)")

# Test 4: Check for missing required fields
print("\n4. Checking data quality...")
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN name IS NULL OR name = '' THEN 1 ELSE 0 END) as missing_name,
        SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as missing_id,
        SUM(CASE WHEN address_city_s IS NULL THEN 1 ELSE 0 END) as missing_city,
        SUM(CASE WHEN address_state_code_s IS NULL THEN 1 ELSE 0 END) as missing_state
    FROM crm.sfdc_dbx.new_properties_with_features
""")

quality = cursor.fetchone()
issues = []
if quality[1] > 0:
    issues.append(f"  - {quality[1]:,} properties missing name")
if quality[2] > 0:
    issues.append(f"  - {quality[2]:,} properties missing ID")
if quality[3] > 0:
    issues.append(f"  - {quality[3]:,} properties missing city")
if quality[4] > 0:
    issues.append(f"  - {quality[4]:,} properties missing state")

if issues:
    print("⚠️  Data quality issues found:")
    for issue in issues:
        print(issue)
else:
    print("✅ No data quality issues found")

# Test 5: Sample records
print("\n5. Sample records...")
cursor.execute("""
    SELECT
        snappt_property_id_c,
        name,
        address_city_s,
        address_state_code_s,
        fraud_detection_enabled_c,
        income_verification_enabled_c
    FROM crm.sfdc_dbx.new_properties_with_features
    LIMIT 5
""")

samples = cursor.fetchall()
print(f"\nShowing {len(samples)} sample properties:")
for i, row in enumerate(samples, 1):
    print(f"\n{i}. {row[1]}")
    print(f"   ID: {row[0]}")
    print(f"   Location: {row[2]}, {row[3]}")
    print(f"   Fraud: {row[4]}, IV: {row[5]}")

# Test 6: Verify exclusion logic
print("\n6. Verifying exclusion logic...")
cursor.execute("""
    SELECT COUNT(*)
    FROM rds.pg_rds_public.properties rds
    INNER JOIN hive_metastore.salesforce.product_property_c sf
        ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
    INNER JOIN crm.sfdc_dbx.new_properties_with_features new
        ON CAST(rds.id AS STRING) = new.snappt_property_id_c
""")

overlap = cursor.fetchone()[0]
if overlap > 0:
    print(f"❌ Error: {overlap:,} properties are in BOTH Salesforce AND the new properties view!")
    print("   This shouldn't happen - view query may need fixing")
else:
    print("✅ No overlap - view correctly excludes existing Salesforce properties")

cursor.close()
conn.close()

print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

if total == 0:
    print("\n✅ View is working correctly")
    print("📊 No new properties to sync (all are already in Salesforce)")
    print("\n🎯 NEXT STEPS:")
    print("   - View is ready for Census")
    print("   - Configure Census when new properties appear")
elif total > 0 and overlap == 0 and not issues:
    print(f"\n✅ View is working correctly")
    print(f"📊 {total:,} properties ready to sync to Salesforce")
    print("\n🎯 NEXT STEPS:")
    print("   1. Proceed to Census configuration")
    print("   2. Create Census model from this view")
    print("   3. Set up INSERT sync to Salesforce")
    print("   4. Test with first 10 records")
    print("   5. Schedule daily sync")
else:
    print(f"\n⚠️  View has issues that need attention")
    print("   - Review the warnings above")
    print("   - Fix data quality issues")
    print("   - Re-run this validation")

print("\n" + "="*80)
