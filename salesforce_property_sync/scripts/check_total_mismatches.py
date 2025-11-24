"""
Check total mismatches across ALL properties in Salesforce
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
print("CHECKING TOTAL FEATURE MISMATCHES ACROSS ALL PROPERTIES")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Count total properties with ANY mismatch
query = """
SELECT
    COUNT(*) as total_mismatches
FROM crm.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE
    -- Any mismatch in feature data
    (sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
     OR sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
     OR sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
     OR sf.idv_only_enabled_c != COALESCE(feat.idv_only_enabled, FALSE)
     OR sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
     OR sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
     OR sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE))
"""

print("\nQuerying crm.sfdc_dbx.product_property_feature_sync view...\n")
cursor.execute(query)

result = cursor.fetchone()
total_mismatches = result[0]

print(f"Total properties with feature mismatches: {total_mismatches:,}")

# Break down by when created
cursor.execute("""
SELECT
    CASE
        WHEN DATE(sf.created_date) = CURRENT_DATE() THEN 'Today'
        WHEN DATE(sf.created_date) >= CURRENT_DATE() - INTERVAL 7 DAYS THEN 'Last 7 days (not today)'
        WHEN DATE(sf.created_date) >= CURRENT_DATE() - INTERVAL 30 DAYS THEN 'Last 30 days (not last 7)'
        ELSE 'Older than 30 days'
    END as time_period,
    COUNT(*) as mismatch_count
FROM crm.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE
    (sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
     OR sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
     OR sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
     OR sf.idv_only_enabled_c != COALESCE(feat.idv_only_enabled, FALSE)
     OR sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
     OR sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
     OR sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE))
GROUP BY 1
ORDER BY
    CASE
        WHEN time_period = 'Today' THEN 1
        WHEN time_period = 'Last 7 days (not today)' THEN 2
        WHEN time_period = 'Last 30 days (not last 7)' THEN 3
        ELSE 4
    END
""")

breakdown = cursor.fetchall()

print("\n" + "="*80)
print("BREAKDOWN BY TIME PERIOD")
print("="*80)
print(f"\n{'Time Period':<30} {'Mismatch Count':>15}")
print("-"*50)

for row in breakdown:
    print(f"{row[0]:<30} {row[1]:>15,}")

# Product-specific breakdown
cursor.execute("""
SELECT
    SUM(CASE WHEN sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
        THEN 1 ELSE 0 END) as fraud_mismatches,
    SUM(CASE WHEN sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
        THEN 1 ELSE 0 END) as iv_mismatches,
    SUM(CASE WHEN sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
        THEN 1 ELSE 0 END) as idv_mismatches,
    SUM(CASE WHEN sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
        THEN 1 ELSE 0 END) as payroll_mismatches,
    SUM(CASE WHEN sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
        THEN 1 ELSE 0 END) as bank_mismatches,
    SUM(CASE WHEN sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE)
        THEN 1 ELSE 0 END) as vor_mismatches
FROM crm.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE
    (sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
     OR sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
     OR sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
     OR sf.idv_only_enabled_c != COALESCE(feat.idv_only_enabled, FALSE)
     OR sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
     OR sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
     OR sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE))
""")

products = cursor.fetchone()

print("\n" + "="*80)
print("MISMATCHES BY PRODUCT")
print("="*80)
print(f"\nFraud Detection: {products[0]:,} properties")
print(f"Income Verification: {products[1]:,} properties")
print(f"ID Verification: {products[2]:,} properties")
print(f"Connected Payroll: {products[3]:,} properties")
print(f"Bank Linking: {products[4]:,} properties")
print(f"Verification of Rent: {products[5]:,} properties")

cursor.close()
conn.close()

print("\n" + "="*80)
print("CENSUS SYNC EXPECTATIONS")
print("="*80)
print(f"""
Census dry run showed: 2,815 updates

This analysis shows: {total_mismatches:,} mismatches

Expected result:
- If Census = {total_mismatches:,}: ✅ Perfect match!
- If Census > {total_mismatches:,}: ⚠️  Census may be updating some records unnecessarily
- If Census < {total_mismatches:,}: ⚠️  Census may not be catching all mismatches

The sync will fix ALL {total_mismatches:,} properties with incorrect feature data!
""")
