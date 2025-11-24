"""
Verify that properties with sfdc_id in RDS actually exist in property_c table
"""
from databricks import sql
import os
import csv

# Databricks connection settings
DATABRICKS_SERVER_HOSTNAME = "dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

def get_databricks_connection():
    """Create a Databricks SQL connection"""
    return sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

def verify_sfdc_id_in_property_c():
    """Verify properties with sfdc_id exist in property_c"""
    print("\n" + "="*80)
    print("VERIFYING SFDC_ID MATCHES IN PROPERTY_C")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Query to check if properties with sfdc_id exist in property_c
    query = """
    WITH missing_from_product_property AS (
        SELECT
            rds_props.id as property_id,
            rds_props.name as property_name,
            rds_props.sfdc_id,
            rds_props.status
        FROM rds.pg_rds_public.properties rds_props
        LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
            ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
        WHERE sf_product.snappt_property_id_c IS NULL
            AND rds_props.sfdc_id IS NOT NULL
            AND rds_props.sfdc_id != ''
    )
    SELECT
        missing.property_id,
        missing.property_name,
        missing.sfdc_id,
        missing.status,
        CASE
            WHEN property_c.id IS NOT NULL THEN 'YES'
            ELSE 'NO'
        END as exists_in_property_c,
        property_c.name as property_c_name,
        property_c.snappt_property_id_c as property_c_snappt_id
    FROM missing_from_product_property missing
    LEFT JOIN hive_metastore.salesforce.property_c property_c
        ON missing.sfdc_id = property_c.id
    ORDER BY exists_in_property_c DESC, missing.property_name
    """

    print("\nExecuting verification query...")
    cursor.execute(query)
    results = cursor.fetchall()

    # Get column names
    columns = [desc[0] for desc in cursor.description]

    # Count matches
    exists_count = sum(1 for row in results if row[4] == 'YES')
    not_exists_count = sum(1 for row in results if row[4] == 'NO')

    print(f"\nVerification Results:")
    print(f"  Properties with sfdc_id missing from product_property_c: {len(results):,}")
    print(f"  ✓ Exists in property_c: {exists_count:,}")
    print(f"  ✗ Does NOT exist in property_c: {not_exists_count:,}")

    # Show properties that exist in property_c
    print("\n" + "="*80)
    print("PROPERTIES THAT EXIST IN PROPERTY_C (First 20)")
    print("="*80)

    exists_results = [row for row in results if row[4] == 'YES']
    for i, row in enumerate(exists_results[:20], 1):
        print(f"\n{i}. RDS Property: {row[1]} ({row[0]})")
        print(f"   RDS Status: {row[3]}")
        print(f"   SFDC ID: {row[2]}")
        print(f"   property_c Name: {row[5]}")
        print(f"   property_c snappt_property_id_c: {row[6]}")

    # Show properties that DON'T exist in property_c
    print("\n" + "="*80)
    print("PROPERTIES THAT DO NOT EXIST IN PROPERTY_C (First 20)")
    print("="*80)

    not_exists_results = [row for row in results if row[4] == 'NO']
    for i, row in enumerate(not_exists_results[:20], 1):
        print(f"\n{i}. RDS Property: {row[1]} ({row[0]})")
        print(f"   RDS Status: {row[3]}")
        print(f"   SFDC ID: {row[2]}")
        print(f"   ✗ NOT FOUND in property_c")

    # Save results to CSV
    csv_path = "/Users/danerosa/rds_databricks_claude/output/sfdc_id_verification.csv"
    print(f"\n\nSaving full results to: {csv_path}")

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in results:
            writer.writerow(row)

    print(f"✓ Saved {len(results):,} records to CSV")

    cursor.close()
    conn.close()

    return exists_results, not_exists_results

def analyze_snappt_property_id_mismatch():
    """Check if property_c has snappt_property_id_c set correctly"""
    print("\n" + "="*80)
    print("ANALYZING SNAPPT_PROPERTY_ID_C FIELD IN PROPERTY_C")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Check if snappt_property_id_c is populated for matched records
    query = """
    WITH missing_from_product_property AS (
        SELECT
            rds_props.id as property_id,
            rds_props.name as property_name,
            rds_props.sfdc_id
        FROM rds.pg_rds_public.properties rds_props
        LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
            ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
        WHERE sf_product.snappt_property_id_c IS NULL
            AND rds_props.sfdc_id IS NOT NULL
            AND rds_props.sfdc_id != ''
    )
    SELECT
        CASE
            WHEN property_c.snappt_property_id_c IS NULL OR property_c.snappt_property_id_c = '' THEN 'snappt_property_id_c is NULL/empty'
            WHEN CAST(missing.property_id AS STRING) = property_c.snappt_property_id_c THEN 'snappt_property_id_c matches RDS id'
            ELSE 'snappt_property_id_c MISMATCH'
        END as match_status,
        COUNT(*) as count
    FROM missing_from_product_property missing
    INNER JOIN hive_metastore.salesforce.property_c property_c
        ON missing.sfdc_id = property_c.id
    GROUP BY CASE
            WHEN property_c.snappt_property_id_c IS NULL OR property_c.snappt_property_id_c = '' THEN 'snappt_property_id_c is NULL/empty'
            WHEN CAST(missing.property_id AS STRING) = property_c.snappt_property_id_c THEN 'snappt_property_id_c matches RDS id'
            ELSE 'snappt_property_id_c MISMATCH'
        END
    ORDER BY count DESC
    """

    print("\nChecking snappt_property_id_c field consistency...")
    cursor.execute(query)
    results = cursor.fetchall()

    print("\nSnappt Property ID Field Analysis:")
    for row in results:
        print(f"  {row[0]}: {row[1]:,} properties")

    cursor.close()
    conn.close()

def get_summary_stats():
    """Get comprehensive summary statistics"""
    print("\n" + "="*80)
    print("COMPREHENSIVE SUMMARY STATISTICS")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Summary query
    query = """
    SELECT
        COUNT(DISTINCT rds_props.id) as total_rds_properties,
        COUNT(DISTINCT sf_product.snappt_property_id_c) as in_product_property_c,
        COUNT(DISTINCT CASE
            WHEN sf_product.snappt_property_id_c IS NULL THEN rds_props.id
        END) as not_in_product_property_c,
        COUNT(DISTINCT CASE
            WHEN sf_product.snappt_property_id_c IS NULL
                AND rds_props.sfdc_id IS NOT NULL
                AND rds_props.sfdc_id != ''
            THEN rds_props.id
        END) as has_sfdc_id_missing_from_product_property,
        COUNT(DISTINCT CASE
            WHEN sf_product.snappt_property_id_c IS NULL
                AND (rds_props.sfdc_id IS NULL OR rds_props.sfdc_id = '')
            THEN rds_props.id
        END) as no_sfdc_id_missing_from_product_property
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    """

    cursor.execute(query)
    result = cursor.fetchone()

    print(f"\nOverall Summary:")
    print(f"  Total RDS properties: {result[0]:,}")
    print(f"  In product_property_c (staging): {result[1]:,}")
    print(f"  NOT in product_property_c: {result[2]:,}")
    print(f"    └─ Has sfdc_id: {result[3]:,}")
    print(f"    └─ No sfdc_id: {result[4]:,}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROPERTY_C TABLE VERIFICATION")
    print("Checking if properties with sfdc_id exist in final property_c table")
    print("="*80)

    try:
        # Get summary first
        get_summary_stats()

        # Verify sfdc_id matches
        exists_results, not_exists_results = verify_sfdc_id_in_property_c()

        # Analyze snappt_property_id_c field
        analyze_snappt_property_id_mismatch()

        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        print(f"\nResults saved to: /Users/danerosa/rds_databricks_claude/output/sfdc_id_verification.csv")

    except Exception as e:
        print(f"\nError during verification: {e}")
        import traceback
        traceback.print_exc()
