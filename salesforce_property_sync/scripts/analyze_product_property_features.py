"""
Analyze crm.sfdc_dbx.product_property_w_features table and compare with current sync
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
print("ANALYZING product_property_w_features TABLE")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# 1. Get schema of product_property_w_features
print("\n" + "="*80)
print("1. SCHEMA OF crm.sfdc_dbx.product_property_w_features")
print("="*80)

cursor.execute("DESCRIBE TABLE crm.sfdc_dbx.product_property_w_features")
features_columns = cursor.fetchall()

print(f"\nTotal columns: {len(features_columns)}\n")
print(f"{'Column Name':<50} {'Type':<30}")
print("-"*80)
for col in features_columns:
    print(f"{col[0]:<50} {col[1]:<30}")

# 2. Compare with product_property_c schema
print("\n" + "="*80)
print("2. SCHEMA OF hive_metastore.salesforce.product_property_c")
print("="*80)

cursor.execute("DESCRIBE TABLE hive_metastore.salesforce.product_property_c")
product_property_c_columns = cursor.fetchall()

print(f"\nTotal columns: {len(product_property_c_columns)}\n")
print(f"{'Column Name':<50} {'Type':<30}")
print("-"*80)
for col in product_property_c_columns[:20]:  # Show first 20
    print(f"{col[0]:<50} {col[1]:<30}")
print(f"... and {len(product_property_c_columns) - 20} more columns")

# 3. Find columns in features table not in product_property_c
features_cols = set([col[0].lower() for col in features_columns])
product_property_c_cols = set([col[0].lower() for col in product_property_c_columns])

missing_in_salesforce = features_cols - product_property_c_cols
extra_in_salesforce = product_property_c_cols - features_cols

print("\n" + "="*80)
print("3. FIELD COMPARISON")
print("="*80)

print(f"\nFields in product_property_w_features NOT in product_property_c:")
print(f"Count: {len(missing_in_salesforce)}")
if missing_in_salesforce:
    for field in sorted(missing_in_salesforce):
        print(f"  - {field}")

print(f"\nFields in product_property_c NOT in product_property_w_features:")
print(f"Count: {len(extra_in_salesforce)}")
if extra_in_salesforce:
    for field in sorted(list(extra_in_salesforce)[:20]):
        print(f"  - {field}")
    if len(extra_in_salesforce) > 20:
        print(f"  ... and {len(extra_in_salesforce) - 20} more")

# 4. Get sample data from product_property_w_features
print("\n" + "="*80)
print("4. SAMPLE DATA FROM product_property_w_features")
print("="*80)

cursor.execute("""
    SELECT *
    FROM crm.sfdc_dbx.product_property_w_features
    LIMIT 3
""")

sample_rows = cursor.fetchall()
column_names = [desc[0] for desc in cursor.description]

print(f"\nShowing {len(sample_rows)} sample records:\n")

for i, row in enumerate(sample_rows, 1):
    print(f"Record {i}:")
    for col_name, value in zip(column_names, row):
        if value is not None and str(value).strip():
            val_str = str(value)[:100]  # Truncate long values
            print(f"  {col_name}: {val_str}")
    print()

# 5. Count records in product_property_w_features
print("\n" + "="*80)
print("5. RECORD COUNTS")
print("="*80)

cursor.execute("SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_w_features")
features_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM hive_metastore.salesforce.product_property_c")
product_property_c_count = cursor.fetchone()[0]

print(f"\nRecords in product_property_w_features: {features_count:,}")
print(f"Records in product_property_c: {product_property_c_count:,}")

# 6. Look for feature-related columns
print("\n" + "="*80)
print("6. FEATURE-RELATED FIELDS IN product_property_w_features")
print("="*80)

feature_fields = [col[0] for col in features_columns if 'feature' in col[0].lower() or
                  'enabled' in col[0].lower() or 'start_date' in col[0].lower() or
                  'updated_date' in col[0].lower()]

print(f"\nFound {len(feature_fields)} feature-related fields:\n")
for field in feature_fields:
    print(f"  - {field}")

# 7. Check if these feature fields exist in product_property_c
print("\n" + "="*80)
print("7. FEATURE FIELDS - SYNC STATUS")
print("="*80)

product_property_c_col_list = [col[0].lower() for col in product_property_c_columns]

print("\nFeature fields and their sync status:\n")
for field in feature_fields:
    exists_in_sf = field.lower() in product_property_c_col_list
    status = "✅ Exists in Salesforce" if exists_in_sf else "❌ NOT in Salesforce"
    print(f"{field:<50} {status}")

# 8. Identify important fields to add
print("\n" + "="*80)
print("8. RECOMMENDED FIELDS TO SYNC")
print("="*80)

print("""
Based on the analysis, these are the key fields you should consider syncing:

HIGH PRIORITY (Product Features):
These fields control which Snappt products/features are enabled for each property.
If these aren't synced, Salesforce won't have visibility into what products are active.

Fields to check and potentially sync:
""")

# Get non-null counts for feature fields
for field in feature_fields[:10]:  # Check first 10 feature fields
    cursor.execute(f"""
        SELECT
            COUNT(*) as total,
            COUNT({field}) as non_null_count
        FROM crm.sfdc_dbx.product_property_w_features
    """)
    result = cursor.fetchone()
    total, non_null = result[0], result[1]
    populated_pct = (non_null / total * 100) if total > 0 else 0

    exists_in_sf = field.lower() in product_property_c_col_list
    status = "✅ In SF" if exists_in_sf else "❌ Missing"

    print(f"  {field:<50} {status} ({non_null:,}/{total:,} = {populated_pct:.1f}% populated)")

cursor.close()
conn.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print("""
Next steps:
1. Review the feature fields that are missing from product_property_c
2. Determine which ones are business-critical
3. Update your Census sync to include these fields
4. Or create a separate sync for feature data
""")
