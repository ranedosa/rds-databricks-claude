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

print("Checking update activity across multiple days...")
print("="*80)

# Check updates by day for past week
query = """
SELECT
    DATE(last_modified_date) as update_date,
    COUNT(*) as update_count
FROM crm.salesforce.product_property
WHERE last_modified_date >= '2026-01-06'
  AND last_modified_date < '2026-01-10'
  AND _fivetran_deleted = false
GROUP BY DATE(last_modified_date)
ORDER BY update_date DESC
"""

cursor.execute(query)
results = cursor.fetchall()

print(f"\nUpdates by date:")
for date, count in results:
    print(f"  {date}: {count:,} updates")

# Check if there were updates that weren't created on same day
print(f"\n" + "="*80)
print("Checking records updated on Jan 8 but created before Jan 8...")
query = """
SELECT COUNT(*) as updates_to_existing
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = '2026-01-08'
  AND DATE(created_date) < '2026-01-08'
  AND _fivetran_deleted = false
"""
cursor.execute(query)
updates_existing = cursor.fetchall()[0][0]
print(f"  Updates to existing records (Jan 8): {updates_existing:,}")

cursor.close()
connection.close()
