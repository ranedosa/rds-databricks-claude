"""
Generate sync payload WITH product feature data from product_property_w_features
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
print("GENERATING SYNC PAYLOAD WITH PRODUCT FEATURES")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Query that includes feature data
query = """
SELECT
    -- Property identifiers
    CAST(rds.id AS STRING) as snappt_property_id_c,
    CAST(rds.id AS STRING) as reverse_etl_id_c,

    -- Basic property info
    rds.name,
    rds.entity_name as entity_name_c,
    rds.address as address_street_s,
    rds.city as address_city_s,
    rds.state as address_state_code_s,
    rds.zip as address_postal_code_s,
    rds.phone as phone_c,
    rds.email as email_c,
    rds.website as website_c,
    rds.logo as logo_c,
    rds.unit as unit_c,
    rds.status as status_c,
    CAST(rds.company_id AS STRING) as company_id_c,
    rds.company_short_id as company_short_id_c,
    rds.short_id as short_id_c,
    rds.bank_statement as bank_statement_c,
    rds.paystub as paystub_c,
    rds.unit_is_required as unit_is_required_c,
    rds.phone_is_required as phone_is_required_c,
    rds.identity_verification_enabled as identity_verification_enabled_c,

    -- Product feature flags from product_property_w_features
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
    feat.vor_updated_at as vor_updated_date_c,

    -- Required for Salesforce
    FALSE as not_orphan_record_c,
    TRUE as trigger_rollups_c

FROM rds.pg_rds_public.properties rds
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
LEFT JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE sf.snappt_property_id_c IS NULL
    AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
    AND rds.status = 'ACTIVE'
ORDER BY rds.updated_at DESC
"""

print("\nExecuting query to extract properties with feature data...")
cursor.execute(query)

# Get column names and results
columns = [desc[0] for desc in cursor.description]
results = cursor.fetchall()

print(f"Found {len(results):,} properties\n")

# Show feature data stats
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
print("FEATURE ENABLEMENT STATISTICS")
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
output_path = "/Users/danerosa/rds_databricks_claude/output/sync_payloads/sync_with_features.csv"
print(f"\n\nSaving to: {output_path}")

with open(output_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(results)

print(f"✅ Saved {len(results):,} records with full feature data!")

# Show sample
print("\n" + "="*80)
print("SAMPLE RECORD WITH FEATURE DATA")
print("="*80)

if results:
    sample = results[0]
    print(f"\nProperty: {sample[columns.index('name')]}")
    print(f"  Fraud Detection: {sample[fraud_idx]}")
    print(f"  Income Verification: {sample[iv_idx]}")
    print(f"  ID Verification: {sample[idv_idx]}")
    print(f"  Connected Payroll: {sample[payroll_idx]}")
    print(f"  Bank Linking: {sample[bank_idx]}")
    print(f"  VOR: {sample[vor_idx]}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print(f"""
Next steps:
1. Review the CSV: {output_path}
2. Upload to Census for syncing properties WITH feature data
3. This will properly populate all product enablement fields
""")
