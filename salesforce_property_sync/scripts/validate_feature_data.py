"""
Check if any of today's synced properties should have feature flags enabled
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
print("VALIDATING FEATURE DATA FOR TODAY'S SYNCED PROPERTIES")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Check if any of today's synced properties have features enabled
query = """
SELECT
    sf.name,
    sf.snappt_property_id_c,
    sf.fraud_detection_enabled_c as sf_fraud,
    feat.fraud_enabled as actual_fraud,
    sf.income_verification_enabled_c as sf_iv,
    feat.iv_enabled as actual_iv,
    sf.id_verification_enabled_c as sf_idv,
    feat.idv_enabled as actual_idv,
    feat.payroll_linking_enabled as actual_payroll,
    feat.bank_linking_enabled as actual_bank,
    feat.vor_enabled as actual_vor
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE DATE(sf.created_date) = CURRENT_DATE()
    AND (feat.fraud_enabled = TRUE
         OR feat.iv_enabled = TRUE
         OR feat.idv_enabled = TRUE
         OR feat.payroll_linking_enabled = TRUE
         OR feat.bank_linking_enabled = TRUE
         OR feat.vor_enabled = TRUE)
"""

print("\nChecking if any of today's synced properties should have features enabled...\n")
cursor.execute(query)

results = cursor.fetchall()

if len(results) == 0:
    print("✅ RESULT: No properties synced today should have features enabled")
    print("   All False values are CORRECT - these properties don't have products yet")
    print("\n   ACTION NEEDED: Update Census query for FUTURE syncs to include feature data")
else:
    print(f"⚠️  FOUND {len(results)} properties that SHOULD have features enabled!\n")
    print("These properties were synced with all False but should have TRUE values:\n")

    for row in results:
        print(f"\nProperty: {row[0]}")
        print(f"  ID: {row[1]}")
        if row[3]:  # actual_fraud
            print(f"  Fraud Detection: Synced={row[2]}, Should be={row[3]}")
        if row[5]:  # actual_iv
            print(f"  Income Verification: Synced={row[4]}, Should be={row[5]}")
        if row[7]:  # actual_idv
            print(f"  ID Verification: Synced={row[6]}, Should be={row[7]}")
        if row[8]:  # actual_payroll
            print(f"  Connected Payroll: Synced=False, Should be={row[8]}")
        if row[9]:  # actual_bank
            print(f"  Bank Linking: Synced=False, Should be={row[9]}")
        if row[10]:  # actual_vor
            print(f"  VOR: Synced=False, Should be={row[10]}")

    print(f"\n   ACTION NEEDED: Backfill these {len(results)} properties with correct feature data")

# Also check total counts
cursor.execute("""
    SELECT COUNT(*)
    FROM hive_metastore.salesforce.product_property_c
    WHERE DATE(created_date) = CURRENT_DATE()
""")
total_synced = cursor.fetchone()[0]

print(f"\n{'='*80}")
print("SUMMARY")
print("="*80)
print(f"Total properties synced today: {total_synced:,}")
print(f"Properties that should have features: {len(results):,}")
print(f"Properties with correct all-False: {total_synced - len(results):,}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("""
1. For future syncs: Update Census source query to include product_property_w_features JOIN
   (Query available in /scripts/generate_sync_with_features.py)

2. If properties need backfill: Re-sync with corrected feature data
   (Sample CSV available in /output/sync_payloads/sync_with_features.csv)
""")
