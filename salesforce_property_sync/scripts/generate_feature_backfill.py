"""
Generate backfill CSV for the 1,296 properties synced today with correct feature data
"""
from databricks import sql
import os
import csv

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
print("GENERATING FEATURE DATA BACKFILL FOR TODAY'S SYNCED PROPERTIES")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Query for properties synced today with correct feature data
query = """
SELECT
    -- Identifiers for Census upsert
    sf.snappt_property_id_c,
    sf.reverse_etl_id_c,

    -- Property info (for reference)
    sf.name,

    -- Product feature flags from product_property_w_features (corrected data)
    COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
    feat.fraud_enabled_at as fraud_detection_start_date_c,
    feat.fraud_updated_at as fraud_detection_updated_date_c,

    COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
    feat.iv_enabled_at as income_verification_start_date_c,
    feat.iv_updated_at as income_verification_updated_date_c,

    COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
    feat.idv_enabled_at as id_verification_start_date_c,
    feat.idv_updated_at as id_verification_updated_date_c,

    COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
    feat.idv_only_enabled_at as idv_only_start_date_c,
    feat.idv_only_updated_at as idv_only_updated_date_c,

    COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
    feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
    feat.payroll_linking_updated_at as connected_payroll_updated_date_c,

    COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
    feat.bank_linking_enabled_at as bank_linking_start_date_c,
    feat.bank_linking_updated_at as bank_linking_updated_date_c,

    COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
    feat.vor_enabled_at as vor_start_date_c,
    feat.vor_updated_at as vor_updated_date_c

FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE DATE(sf.created_date) = CURRENT_DATE()
ORDER BY sf.name
"""

print("\nExecuting query to get today's synced properties with correct feature data...\n")
cursor.execute(query)

# Get column names and results
columns = [desc[0] for desc in cursor.description]
results = cursor.fetchall()

print(f"Found {len(results):,} properties to backfill\n")

# Calculate feature statistics
feat_stats = {
    'fraud_enabled': 0,
    'iv_enabled': 0,
    'idv_enabled': 0,
    'payroll_enabled': 0,
    'bank_enabled': 0,
    'vor_enabled': 0
}

fraud_idx = columns.index('fraud_detection_enabled_c')
iv_idx = columns.index('income_verification_enabled_c')
idv_idx = columns.index('id_verification_enabled_c')
payroll_idx = columns.index('connected_payroll_enabled_c')
bank_idx = columns.index('bank_linking_enabled_c')
vor_idx = columns.index('verification_of_rent_enabled_c')

for row in results:
    if row[fraud_idx]: feat_stats['fraud_enabled'] += 1
    if row[iv_idx]: feat_stats['iv_enabled'] += 1
    if row[idv_idx]: feat_stats['idv_enabled'] += 1
    if row[payroll_idx]: feat_stats['payroll_enabled'] += 1
    if row[bank_idx]: feat_stats['bank_enabled'] += 1
    if row[vor_idx]: feat_stats['vor_enabled'] += 1

print("="*80)
print("FEATURE ENABLEMENT STATISTICS (CORRECTED DATA)")
print("="*80)
total = len(results)
print(f"\nOut of {total:,} properties:")
print(f"  Fraud Detection enabled: {feat_stats['fraud_enabled']:,} ({feat_stats['fraud_enabled']/total*100:.1f}%)")
print(f"  Income Verification enabled: {feat_stats['iv_enabled']:,} ({feat_stats['iv_enabled']/total*100:.1f}%)")
print(f"  ID Verification enabled: {feat_stats['idv_enabled']:,} ({feat_stats['idv_enabled']/total*100:.1f}%)")
print(f"  Connected Payroll enabled: {feat_stats['payroll_enabled']:,} ({feat_stats['payroll_enabled']/total*100:.1f}%)")
print(f"  Bank Linking enabled: {feat_stats['bank_enabled']:,} ({feat_stats['bank_enabled']/total*100:.1f}%)")
print(f"  Verification of Rent enabled: {feat_stats['vor_enabled']:,} ({feat_stats['vor_enabled']/total*100:.1f}%)")

# Save to CSV
output_path = "/Users/danerosa/rds_databricks_claude/output/sync_payloads/feature_backfill_20251121.csv"
print(f"\n\nSaving to: {output_path}")

with open(output_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(results)

print(f"✅ Saved {len(results):,} records with corrected feature data!")

# Show comparison
print("\n" + "="*80)
print("COMPARISON: CURRENT vs CORRECT")
print("="*80)

cursor.execute("""
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN sf.fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as current_fraud,
    SUM(CASE WHEN feat.fraud_enabled = TRUE THEN 1 ELSE 0 END) as actual_fraud,
    SUM(CASE WHEN sf.income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as current_iv,
    SUM(CASE WHEN feat.iv_enabled = TRUE THEN 1 ELSE 0 END) as actual_iv
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE DATE(sf.created_date) = CURRENT_DATE()
""")

comparison = cursor.fetchone()
print(f"\nTotal properties: {comparison[0]:,}")
print(f"\nFraud Detection:")
print(f"  Currently in Salesforce: {comparison[1]:,} enabled")
print(f"  Should be: {comparison[2]:,} enabled")
print(f"  Missing: {comparison[2] - comparison[1]:,} properties")

print(f"\nIncome Verification:")
print(f"  Currently in Salesforce: {comparison[3]:,} enabled")
print(f"  Should be: {comparison[4]:,} enabled")
print(f"  Missing: {comparison[4] - comparison[3]:,} properties")

cursor.close()
conn.close()

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print(f"""
1. Upload this CSV to Census: {output_path}

2. Configure Census sync as UPDATE operation:
   - Sync Key: Reverse_ETL_ID__c (or snappt_property_id_c)
   - Sync Behavior: UPDATE existing records
   - Map feature fields to their Salesforce counterparts

3. Run the sync to update all {total:,} properties with correct feature data

4. This will fix the {comparison[2] - comparison[1]:,} properties missing Fraud Detection
   and {comparison[4] - comparison[3]:,} properties missing Income Verification flags
""")
