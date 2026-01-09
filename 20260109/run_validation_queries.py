#!/usr/bin/env python3
"""
Run all Day 3 validation queries in Databricks and display results
"""

from databricks import sql
from databricks.sdk.core import Config
import os
import pandas as pd
from datetime import datetime

# Databricks connection setup
config = Config()

# Define all validation queries
QUERIES = {
    "1_overall_impact": """
        SELECT 'CREATES' AS Operation, COUNT(*) AS RecordCount
        FROM crm.salesforce.product_property
        WHERE DATE(created_date) = CURRENT_DATE()
          AND _fivetran_deleted = false

        UNION ALL

        SELECT 'UPDATES' AS Operation, COUNT(*) AS RecordCount
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = CURRENT_DATE()
          AND DATE(created_date) != CURRENT_DATE()
          AND _fivetran_deleted = false

        UNION ALL

        SELECT 'TOTAL_MODIFIED' AS Operation, COUNT(*) AS RecordCount
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = CURRENT_DATE()
          AND _fivetran_deleted = false
    """,

    "2_feature_distribution": """
        SELECT
            'ID_Verification' AS Feature,
            SUM(CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
            SUM(CASE WHEN id_verification_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
            COUNT(*) AS Total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false

        UNION ALL

        SELECT
            'Bank_Linking' AS Feature,
            SUM(CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
            SUM(CASE WHEN bank_linking_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
            COUNT(*) AS Total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false

        UNION ALL

        SELECT
            'Connected_Payroll' AS Feature,
            SUM(CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
            SUM(CASE WHEN connected_payroll_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
            COUNT(*) AS Total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false

        UNION ALL

        SELECT
            'Income_Verification' AS Feature,
            SUM(CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
            SUM(CASE WHEN income_verification_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
            COUNT(*) AS Total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false

        UNION ALL

        SELECT
            'Fraud_Detection' AS Feature,
            SUM(CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
            SUM(CASE WHEN fraud_detection_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
            COUNT(*) AS Total
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false
    """,

    "3_total_records": """
        SELECT COUNT(*) AS Total_Product_Property_Records
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false
    """,

    "4_recent_changes": """
        SELECT COUNT(*) AS Records_Modified_Last_Hour
        FROM crm.salesforce.product_property
        WHERE last_modified_date >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
          AND _fivetran_deleted = false
    """,

    "5_sample_creates": """
        SELECT
            id,
            name,
            snappt_property_id_c,
            short_id_c,
            company_name_c,
            id_verification_enabled_c,
            bank_linking_enabled_c,
            connected_payroll_enabled_c,
            income_verification_enabled_c,
            fraud_detection_enabled_c,
            created_date,
            last_modified_date
        FROM crm.salesforce.product_property
        WHERE DATE(created_date) = CURRENT_DATE()
          AND _fivetran_deleted = false
        ORDER BY created_date DESC
        LIMIT 10
    """,

    "6_sample_updates": """
        SELECT
            id,
            name,
            snappt_property_id_c,
            short_id_c,
            company_name_c,
            id_verification_enabled_c,
            bank_linking_enabled_c,
            connected_payroll_enabled_c,
            income_verification_enabled_c,
            fraud_detection_enabled_c,
            created_date,
            last_modified_date
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = CURRENT_DATE()
          AND DATE(created_date) != CURRENT_DATE()
          AND _fivetran_deleted = false
        ORDER BY last_modified_date DESC
        LIMIT 10
    """,

    "7_data_quality": """
        SELECT
            id,
            name,
            snappt_property_id_c,
            short_id_c,
            company_name_c,
            last_modified_date
        FROM crm.salesforce.product_property
        WHERE DATE(last_modified_date) = CURRENT_DATE()
          AND _fivetran_deleted = false
          AND (
            snappt_property_id_c IS NULL
            OR name IS NULL
            OR company_name_c IS NULL
          )
        LIMIT 50
    """,

    "8_multi_feature_properties": """
        SELECT
            id,
            name,
            snappt_property_id_c,
            id_verification_enabled_c,
            bank_linking_enabled_c,
            connected_payroll_enabled_c,
            income_verification_enabled_c,
            fraud_detection_enabled_c,
            (CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END +
             CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END +
             CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END +
             CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END +
             CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS total_feature_count,
            last_modified_date
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false
          AND DATE(last_modified_date) = CURRENT_DATE()
        ORDER BY total_feature_count DESC
        LIMIT 10
    """
}

def run_query(cursor, query_name, query):
    """Run a single query and return results as DataFrame"""
    print(f"\n{'='*80}")
    print(f"Running Query: {query_name}")
    print(f"{'='*80}")

    try:
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        return df
    except Exception as e:
        print(f"❌ Error running {query_name}: {str(e)}")
        return None

def main():
    print(f"\n{'='*80}")
    print(f"Day 3 Validation Queries - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # Connect to Databricks
    print("Connecting to Databricks...")
    with sql.connect(
        server_hostname=config.host,
        http_path="/sql/1.0/warehouses/98c28e1f58224f36",
        credentials_provider=config.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            results = {}

            # Run priority queries first
            priority_queries = ["1_overall_impact", "2_feature_distribution", "3_total_records"]

            print("\n🔴 PRIORITY QUERIES (MUST RUN):")
            for query_name in priority_queries:
                if query_name in QUERIES:
                    df = run_query(cursor, query_name, QUERIES[query_name])
                    if df is not None:
                        results[query_name] = df
                        print(f"\n{df.to_string(index=False)}")
                        print(f"\n✅ {query_name} completed")

            # Run remaining queries
            print("\n\n🟡 ADDITIONAL VALIDATION QUERIES:")
            remaining = [q for q in QUERIES.keys() if q not in priority_queries]
            for query_name in remaining:
                df = run_query(cursor, query_name, QUERIES[query_name])
                if df is not None:
                    results[query_name] = df
                    print(f"\n{df.to_string(index=False)}")
                    print(f"\n✅ {query_name} completed")

            # Summary
            print(f"\n\n{'='*80}")
            print("VALIDATION SUMMARY")
            print(f"{'='*80}")

            if "1_overall_impact" in results:
                print("\n📊 Overall Impact:")
                for _, row in results["1_overall_impact"].iterrows():
                    print(f"  {row['Operation']}: {row['RecordCount']:,}")

            if "3_total_records" in results:
                total = results["3_total_records"].iloc[0]['Total_Product_Property_Records']
                print(f"\n📈 Total Records: {total:,}")
                print(f"  Expected: 18,450-18,560")
                if 18450 <= total <= 18560:
                    print(f"  ✅ Within expected range")
                else:
                    print(f"  ⚠️  Outside expected range")

            if "7_data_quality" in results:
                issues = len(results["7_data_quality"])
                print(f"\n🔍 Data Quality Issues: {issues}")
                if issues == 0:
                    print(f"  ✅ No data quality issues found")
                else:
                    print(f"  ⚠️  {issues} records with missing key fields")

            # Save results to CSV
            output_dir = "validation_results"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            print(f"\n\n💾 Saving results to CSV files...")
            for query_name, df in results.items():
                filename = f"{output_dir}/{query_name}_{timestamp}.csv"
                df.to_csv(filename, index=False)
                print(f"  Saved: {filename}")

            print(f"\n✅ All validation queries completed!")
            print(f"   Results saved to ./{output_dir}/")

if __name__ == "__main__":
    main()
