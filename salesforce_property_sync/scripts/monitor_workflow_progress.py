"""
Monitor Salesforce workflow progress (product_property_c → property_c)
"""
from databricks import sql
import os
import time

DATABRICKS_SERVER_HOSTNAME = "dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

def get_databricks_connection():
    return sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

def check_workflow_progress():
    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Count records in product_property_c created today
    cursor.execute("""
        SELECT COUNT(*)
        FROM hive_metastore.salesforce.product_property_c
        WHERE DATE(created_date) = CURRENT_DATE()
    """)
    total_staging = cursor.fetchone()[0]

    # Count records that have flowed to property_c
    cursor.execute("""
        SELECT COUNT(*)
        FROM hive_metastore.salesforce.product_property_c pp
        INNER JOIN hive_metastore.salesforce.property_c p
            ON pp.sf_property_id_c = p.id
        WHERE DATE(pp.created_date) = CURRENT_DATE()
    """)
    completed = cursor.fetchone()[0]

    # Count orphans (not yet processed)
    cursor.execute("""
        SELECT COUNT(*)
        FROM hive_metastore.salesforce.product_property_c pp
        WHERE DATE(pp.created_date) = CURRENT_DATE()
          AND (pp.sf_property_id_c IS NULL OR pp.sf_property_id_c = '')
    """)
    orphans = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return total_staging, completed, orphans

print("\n" + "="*80)
print("MONITORING SALESFORCE WORKFLOW PROGRESS")
print("="*80)
print("\nWatching for product_property_c → property_c workflow completion...")
print("Press Ctrl+C to stop monitoring\n")

try:
    while True:
        total, completed, orphans = check_workflow_progress()

        if total == 0:
            print("No records found. Exiting.")
            break

        percentage = (completed / total * 100) if total > 0 else 0
        remaining = total - completed

        print(f"\rProgress: {completed:,}/{total:,} ({percentage:.1f}%) | " +
              f"Remaining: {remaining:,} | Orphans: {orphans:,}    ", end='', flush=True)

        if completed == total:
            print("\n\n✅ WORKFLOW COMPLETE! All records processed.")
            break

        time.sleep(10)  # Check every 10 seconds

except KeyboardInterrupt:
    print("\n\nMonitoring stopped.")

print("\n" + "="*80)
print("Final Status:")
total, completed, orphans = check_workflow_progress()
print(f"  Total staged: {total:,}")
print(f"  Completed: {completed:,}")
print(f"  Remaining: {total - completed:,}")
print("="*80)
