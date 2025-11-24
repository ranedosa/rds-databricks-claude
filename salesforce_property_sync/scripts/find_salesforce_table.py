"""
Find the correct location of Salesforce product_property_c table
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
print("FINDING SALESFORCE PRODUCT_PROPERTY_C TABLE")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Check schemas in crm catalog
print("\n1. Checking schemas in 'crm' catalog...")
try:
    cursor.execute("SHOW SCHEMAS IN crm")
    schemas = cursor.fetchall()
    print(f"\nFound {len(schemas)} schemas in 'crm':")
    for schema in schemas:
        print(f"  - {schema[0]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check if hive_metastore.salesforce exists
print("\n2. Checking hive_metastore.salesforce...")
try:
    cursor.execute("SHOW TABLES IN hive_metastore.salesforce")
    tables = cursor.fetchall()
    print(f"\nFound {len(tables)} tables in hive_metastore.salesforce:")
    for table in tables[:10]:  # Show first 10
        print(f"  - {table[1]}")
    if len(tables) > 10:
        print(f"  ... and {len(tables) - 10} more")

    # Check if product_property_c exists
    has_product_property = any('product_property_c' in str(table[1]) for table in tables)
    if has_product_property:
        print(f"\n✅ product_property_c found in hive_metastore.salesforce")
except Exception as e:
    print(f"❌ Error: {e}")

# Try to find product_property_c in any location
print("\n3. Searching for product_property_c table...")
locations_to_check = [
    "hive_metastore.salesforce.product_property_c",
    "crm.salesforce.product_property_c",
    "crm.sfdc.product_property_c",
]

for location in locations_to_check:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {location}")
        count = cursor.fetchone()[0]
        print(f"✅ Found: {location} ({count:,} records)")
    except Exception as e:
        print(f"❌ Not found: {location}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("""
Based on the results above, use the table location that EXISTS for your notebook.
The notebook currently references 'crm.salesforce.product_property_c' but this may need
to be changed to 'hive_metastore.salesforce.product_property_c' if that's where the data is.
""")
