#!/usr/bin/env python3
"""
Validate Day 3 Sync Results in Databricks
"""
import os
from databricks import sql
from datetime import datetime

# Connect to Databricks
host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")

connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/95a8f5979c3f8740",  # fivetran warehouse
    access_token=os.getenv("DATABRICKS_TOKEN")
)

cursor = connection.cursor()

try:
    print("=" * 80)
    print("DAY 3 VALIDATION - BOTH SYNCS")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # QUERY 1: Overall Impact Summary
    print("=" * 80)
    print("QUERY 1: Overall Impact Summary")
    print("=" * 80)

    # Day 3 syncs ran on January 8, 2026
    today = '2026-01-08'  # datetime.now().strftime('%Y-%m-%d')

    queries = {
        "CREATES": f"""
            SELECT COUNT(*) as count
            FROM crm.salesforce.product_property
            WHERE DATE(created_date) = '{today}'
              AND _fivetran_deleted = false
        """,
        "UPDATES": f"""
            SELECT COUNT(*) as count
            FROM crm.salesforce.product_property
            WHERE DATE(last_modified_date) = '{today}'
              AND DATE(created_date) != '{today}'
              AND _fivetran_deleted = false
        """,
        "TOTAL_MODIFIED": f"""
            SELECT COUNT(*) as count
            FROM crm.salesforce.product_property
            WHERE DATE(last_modified_date) = '{today}'
              AND _fivetran_deleted = false
        """
    }

    results = {}
    for operation, query in queries.items():
        cursor.execute(query)
        count = cursor.fetchall()[0][0]
        results[operation] = count
        print(f"  {operation}: {count:,}")

    print()
    print("Expected Results:")
    print(f"  CREATES: ~574-690 (Sync A)")
    print(f"  UPDATES: ~7,500-7,820 (Sync B)")
    print(f"  TOTAL_MODIFIED: ~8,100-8,500")
    print()

    # Validation
    if 574 <= results["CREATES"] <= 690:
        print("✅ CREATES count within expected range")
    else:
        print(f"⚠️  CREATES count outside expected range: {results['CREATES']}")

    if 7500 <= results["UPDATES"] <= 7820:
        print("✅ UPDATES count within expected range")
    else:
        print(f"⚠️  UPDATES count outside expected range: {results['UPDATES']}")

    print()

    # QUERY 2: Feature Flag Distribution
    print("=" * 80)
    print("QUERY 2: Feature Flag Distribution")
    print("=" * 80)

    features = {
        "ID_Verification": "id_verification_enabled_c",
        "Bank_Linking": "bank_linking_enabled_c",
        "Connected_Payroll": "connected_payroll_enabled_c",
        "Income_Verification": "income_verification_enabled_c",
        "Fraud_Detection": "fraud_detection_enabled_c"
    }

    for feature_name, column_name in features.items():
        query = f"""
            SELECT
                SUM(CASE WHEN {column_name} = true THEN 1 ELSE 0 END) as enabled,
                SUM(CASE WHEN {column_name} = false THEN 1 ELSE 0 END) as disabled,
                COUNT(*) as total
            FROM crm.salesforce.product_property
            WHERE _fivetran_deleted = false
        """
        cursor.execute(query)
        enabled, disabled, total = cursor.fetchall()[0]
        print(f"  {feature_name}:")
        print(f"    Enabled: {enabled:,} ({100*enabled/total:.1f}%)")
        print(f"    Disabled: {disabled:,} ({100*disabled/total:.1f}%)")

    print()

    # QUERY 3: Total Product_Property Records
    print("=" * 80)
    print("QUERY 3: Total Product_Property Records")
    print("=" * 80)

    query = """
        SELECT COUNT(*) as total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false
    """
    cursor.execute(query)
    total = cursor.fetchall()[0][0]
    print(f"  Total Records: {total:,}")
    print(f"  Expected: 18,450-18,560")

    if 18450 <= total <= 18560:
        print(f"  ✅ Total within expected range")
    else:
        print(f"  ⚠️  Total outside expected range")

    print()

    # QUERY 4: Records Modified in Last Hour
    print("=" * 80)
    print("QUERY 4: Records Modified in Last Hour")
    print("=" * 80)

    query = """
        SELECT COUNT(*) as recent
        FROM crm.salesforce.product_property
        WHERE last_modified_date >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
          AND _fivetran_deleted = false
    """
    cursor.execute(query)
    recent = cursor.fetchall()[0][0]
    print(f"  Records modified in last hour: {recent:,}")

    if recent > 0:
        print(f"  ✅ Recent sync activity detected")
    else:
        print(f"  ⚠️  No recent activity (may be more than 1 hour since sync)")

    print()

    # QUERY 5: Sample of Created Records
    print("=" * 80)
    print("QUERY 5: Sample of Created Records (First 10)")
    print("=" * 80)

    query = f"""
        SELECT
            name,
            snappt_property_id_c,
            company_name_c,
            id_verification_enabled_c as idv,
            bank_linking_enabled_c as bank,
            connected_payroll_enabled_c as payroll,
            income_verification_enabled_c as income,
            fraud_detection_enabled_c as fraud
        FROM crm.salesforce.product_property
        WHERE DATE(created_date) = '{today}'
          AND _fivetran_deleted = false
        ORDER BY created_date DESC
        LIMIT 10
    """
    cursor.execute(query)
    results = cursor.fetchall()

    if results:
        print(f"\n  {'Name':<40} {'Features Enabled'}")
        print(f"  {'-'*40} {'-'*30}")
        for row in results:
            name, prop_id, company, idv, bank, payroll, income, fraud = row
            features = []
            if idv: features.append("IDV")
            if bank: features.append("Bank")
            if payroll: features.append("Payroll")
            if income: features.append("Income")
            if fraud: features.append("Fraud")
            features_str = ", ".join(features) if features else "None"
            display_name = (name[:37] + "...") if len(name) > 40 else name
            print(f"  {display_name:<40} {features_str}")
    else:
        print("  No records created today")

    print()

    # QUERY 6: Sample of Updated Records
    print("=" * 80)
    print("QUERY 6: Sample of Updated Records (First 10)")
    print("=" * 80)

    query = f"""
        SELECT
            name,
            snappt_property_id_c,
            company_name_c,
            id_verification_enabled_c as idv,
            bank_linking_enabled_c as bank,
            connected_payroll_enabled_c as payroll,
            income_verification_enabled_c as income,
            fraud_detection_enabled_c as fraud
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = '{today}'
          AND DATE(created_date) != '{today}'
          AND _fivetran_deleted = false
        ORDER BY last_modified_date DESC
        LIMIT 10
    """
    cursor.execute(query)
    results = cursor.fetchall()

    if results:
        print(f"\n  {'Name':<40} {'Features Enabled'}")
        print(f"  {'-'*40} {'-'*30}")
        for row in results:
            name, prop_id, company, idv, bank, payroll, income, fraud = row
            features = []
            if idv: features.append("IDV")
            if bank: features.append("Bank")
            if payroll: features.append("Payroll")
            if income: features.append("Income")
            if fraud: features.append("Fraud")
            features_str = ", ".join(features) if features else "None"
            display_name = (name[:37] + "...") if len(name) > 40 else name
            print(f"  {display_name:<40} {features_str}")
    else:
        print("  No records updated today")

    print()

    # QUERY 7: Data Quality Check
    print("=" * 80)
    print("QUERY 7: Data Quality Check")
    print("=" * 80)

    query = f"""
        SELECT COUNT(*) as issues
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = '{today}'
          AND _fivetran_deleted = false
          AND (
            snappt_property_id_c IS NULL
            OR name IS NULL
            OR company_name_c IS NULL
          )
    """
    cursor.execute(query)
    issues = cursor.fetchall()[0][0]

    print(f"  Records with missing key fields: {issues}")
    if issues == 0:
        print(f"  ✅ No data quality issues found")
    else:
        print(f"  ⚠️  {issues} records with data quality issues")

    print()

    # FINAL SUMMARY
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print()
    print("Day 3 Sync Validation Results:")
    print()
    creates_count = results.get('CREATES', 0) if isinstance(results, dict) else 0
    updates_count = results.get('UPDATES', 0) if isinstance(results, dict) else 0
    total_modified = results.get('TOTAL_MODIFIED', 0) if isinstance(results, dict) else 0

    print(f"  Creates (Sync A):  {creates_count:>8,}  {'✅' if 574 <= creates_count <= 690 else '⚠️'}")
    print(f"  Updates (Sync B):  {updates_count:>8,}  {'✅' if 7500 <= updates_count <= 7820 else '⚠️'}")
    print(f"  Total Modified:    {total_modified:>8,}")
    print()
    print(f"  Total Records:     {total:>8,}  {'✅' if 18450 <= total <= 18560 else '⚠️'}")
    print(f"  Data Quality:      {issues:>8} issues  {'✅' if issues == 0 else '⚠️'}")
    print()

    overall_status = "✅ SUCCESS" if (
        574 <= creates_count <= 690 and
        7500 <= updates_count <= 7820 and
        18450 <= total <= 18560 and
        issues == 0
    ) else "⚠️ NEEDS REVIEW"

    print(f"Overall Status: {overall_status}")
    print()

finally:
    cursor.close()
    connection.close()
