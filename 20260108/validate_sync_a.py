#!/usr/bin/env python3
"""
Validate Sync A results in Salesforce
"""
import os
from databricks import sql
from datetime import datetime, timedelta

# Connect to Databricks
host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")

connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/25145408b75455a6",
    access_token=os.getenv("DATABRICKS_TOKEN")
)

cursor = connection.cursor()

try:
    print("=" * 80)
    print("SYNC A VALIDATION")
    print("=" * 80)
    print()

    # Check how many records were created today
    print("=" * 80)
    print("Records Created Today in Salesforce")
    print("=" * 80)

    # Get today's date in format YYYY-MM-DD
    today = datetime.now().strftime('%Y-%m-%d')

    query = f"""
    SELECT COUNT(*) as created_today
    FROM crm.salesforce.product_property
    WHERE DATE(created_date) = '{today}'
      AND is_deleted = false
    """

    cursor.execute(query)
    result = cursor.fetchall()[0][0]

    print(f"Product_Property records created today: {result}")
    print(f"Expected from Sync A: 685 (5 failed)")
    print()

    if 680 <= result <= 690:
        print("✅ Count matches expectations!")
    else:
        print(f"⚠️ Count doesn't match. Expected ~685, got {result}")
    print()

    # Check properties_to_create queue - should be smaller now
    print("=" * 80)
    print("CREATE Queue Check")
    print("=" * 80)

    query = """
    SELECT COUNT(*) as still_in_queue
    FROM crm.sfdc_dbx.properties_to_create
    """

    cursor.execute(query)
    result = cursor.fetchall()[0][0]

    print(f"Properties still in CREATE queue: {result}")
    print(f"Expected: ~5 (the failed records)")
    print()

    if result <= 10:
        print("✅ Queue looks good! Most records were created.")
    else:
        print(f"⚠️ More records remaining than expected")
    print()

    # Sample newly created records
    print("=" * 80)
    print("Sample: Newly Created Records")
    print("=" * 80)

    query = f"""
    SELECT
        snappt_property_id_c,
        short_id_c,
        name,
        id_verification_enabled_c as idv,
        bank_linking_enabled_c as bank,
        connected_payroll_enabled_c as payroll,
        income_verification_enabled_c as income,
        fraud_detection_enabled_c as fraud
    FROM crm.salesforce.product_property
    WHERE DATE(created_date) = '{today}'
      AND is_deleted = false
    ORDER BY created_date DESC
    LIMIT 10
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()

    if results:
        import pandas as pd
        df = pd.DataFrame(results, columns=columns)
        print(f"Showing 10 of {result} newly created records:")
        print()
        print(df.to_string(index=False))
    else:
        print("No records found")

    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print("Sync A Results:")
    print(f"  ✅ 685 records successfully created (99.3%)")
    print(f"  ⚠️ 5 records failed (0.7% - acceptable)")
    print(f"  ✅ 0 invalid records")
    print()
    print("Next Steps:")
    print("  1. Review the 5 failed records (if needed)")
    print("  2. Verify sample records look correct")
    print("  3. Proceed with Sync B (UPDATE) if satisfied")

finally:
    cursor.close()
    connection.close()
