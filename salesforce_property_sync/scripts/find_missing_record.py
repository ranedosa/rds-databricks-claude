"""
Find the 1 missing property that wasn't synced
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
print("FINDING THE MISSING RECORD")
print("="*80)

conn = get_databricks_connection()
cursor = conn.cursor()

# Find properties with no sfdc_id that aren't in product_property_c
query = """
SELECT
    rds.id,
    rds.name,
    rds.status,
    rds.address,
    rds.city,
    rds.state,
    rds.company_id,
    rds.inserted_at,
    rds.updated_at
FROM rds.pg_rds_public.properties rds
LEFT JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE sf.snappt_property_id_c IS NULL
    AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
    AND rds.status != 'DELETED'
ORDER BY rds.updated_at DESC
"""

cursor.execute(query)
results = cursor.fetchall()

print(f"\n✅ Found {len(results)} missing record(s)\n")

if len(results) == 0:
    print("🎉 No missing records! All 1,297 are now synced!")
else:
    for i, row in enumerate(results, 1):
        print(f"{'='*80}")
        print(f"Missing Record #{i}")
        print(f"{'='*80}")
        print(f"Property ID: {row[0]}")
        print(f"Name: {row[1]}")
        print(f"Status: {row[2]}")
        print(f"Address: {row[3]}, {row[4]}, {row[5]}")
        print(f"Company ID: {row[6]}")
        print(f"Created: {row[7]}")
        print(f"Updated: {row[8]}")
        print()

    if len(results) == 1:
        print("="*80)
        print("RECOMMENDATION")
        print("="*80)
        print("""
This single record can be:
1. Manually added to product_property_c via Salesforce UI
2. Synced separately with a single-record CSV
3. Investigated to see why it was excluded

Check if there's anything unusual about this record's data.
""")

cursor.close()
conn.close()
