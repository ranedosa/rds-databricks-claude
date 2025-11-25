"""
Find properties in RDS that don't exist in Salesforce product_property_c table
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

def verify_matching_key():
    """Verify the matching key between tables"""
    print("\n" + "="*80)
    print("VERIFYING MATCHING KEY")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Check if snappt_property_id_c in product_property_c matches properties.id in RDS
    query = """
    SELECT
        COUNT(DISTINCT rds_props.id) as total_rds_properties,
        COUNT(DISTINCT sf_product.snappt_property_id_c) as total_sf_product_properties,
        COUNT(DISTINCT CASE
            WHEN sf_product.snappt_property_id_c IS NOT NULL THEN rds_props.id
        END) as matched_properties,
        COUNT(DISTINCT CASE
            WHEN sf_product.snappt_property_id_c IS NULL THEN rds_props.id
        END) as unmatched_properties
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    """

    print("\nExecuting key verification query...")
    cursor.execute(query)
    result = cursor.fetchone()

    print(f"\nKey Verification Results:")
    print(f"  Total RDS properties: {result[0]:,}")
    print(f"  Total SF product_property_c records: {result[1]:,}")
    print(f"  Matched properties: {result[2]:,}")
    print(f"  Unmatched properties (gaps): {result[3]:,}")

    cursor.close()
    conn.close()

def find_property_gaps():
    """Find properties in RDS that don't exist in product_property_c"""
    print("\n" + "="*80)
    print("FINDING PROPERTY GAPS")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Query to find properties NOT in product_property_c
    query = """
    SELECT
        rds_props.id as property_id,
        rds_props.name as property_name,
        rds_props.status,
        rds_props.company_id,
        rds_props.address,
        rds_props.city,
        rds_props.state,
        rds_props.zip,
        rds_props.sfdc_id,
        rds_props.short_id,
        rds_props.inserted_at,
        rds_props.updated_at
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    WHERE sf_product.snappt_property_id_c IS NULL
        AND rds_props.status != 'DELETED'  -- Exclude deleted properties
    ORDER BY rds_props.updated_at DESC
    """

    print("\nExecuting gap analysis query...")
    cursor.execute(query)
    results = cursor.fetchall()

    print(f"\nFound {len(results):,} properties in RDS NOT in product_property_c\n")

    # Get column names
    columns = [desc[0] for desc in cursor.description]

    # Display first 20 results
    print("="*80)
    print("SAMPLE OF MISSING PROPERTIES (First 20)")
    print("="*80)

    for i, row in enumerate(results[:20], 1):
        print(f"\n{i}. Property: {row[1]} ({row[0]})")
        print(f"   Status: {row[2]}")
        print(f"   Address: {row[4]}, {row[5]}, {row[6]} {row[7]}")
        print(f"   SFDC ID: {row[8]}")
        print(f"   Short ID: {row[9]}")
        print(f"   Created: {row[10]}")
        print(f"   Updated: {row[11]}")

    # Save full results to CSV
    csv_path = "/Users/danerosa/rds_databricks_claude/output/missing_properties.csv"
    print(f"\n\nSaving full results to: {csv_path}")

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in results:
            writer.writerow(row)

    print(f"✓ Saved {len(results):,} missing properties to CSV")

    cursor.close()
    conn.close()

    return results

def analyze_gap_patterns():
    """Analyze patterns in the gaps"""
    print("\n" + "="*80)
    print("ANALYZING GAP PATTERNS")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Analyze by status
    print("\n--- Gap Analysis by Status ---")
    query = """
    SELECT
        rds_props.status,
        COUNT(*) as count
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    WHERE sf_product.snappt_property_id_c IS NULL
    GROUP BY rds_props.status
    ORDER BY count DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    for row in results:
        print(f"  {row[0] or 'NULL'}: {row[1]:,} properties")

    # Analyze by creation date range
    print("\n--- Gap Analysis by Creation Date ---")
    query = """
    SELECT
        YEAR(rds_props.inserted_at) as year,
        MONTH(rds_props.inserted_at) as month,
        COUNT(*) as count
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    WHERE sf_product.snappt_property_id_c IS NULL
        AND rds_props.inserted_at IS NOT NULL
    GROUP BY YEAR(rds_props.inserted_at), MONTH(rds_props.inserted_at)
    ORDER BY year DESC, month DESC
    LIMIT 12
    """

    cursor.execute(query)
    results = cursor.fetchall()

    for row in results:
        print(f"  {row[0]}-{row[1]:02d}: {row[2]:,} properties")

    # Check if they have sfdc_id populated
    print("\n--- Properties with vs without SFDC ID ---")
    query = """
    SELECT
        CASE
            WHEN rds_props.sfdc_id IS NOT NULL AND rds_props.sfdc_id != '' THEN 'Has SFDC ID'
            ELSE 'No SFDC ID'
        END as sfdc_status,
        COUNT(*) as count
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    WHERE sf_product.snappt_property_id_c IS NULL
    GROUP BY CASE
            WHEN rds_props.sfdc_id IS NOT NULL AND rds_props.sfdc_id != '' THEN 'Has SFDC ID'
            ELSE 'No SFDC ID'
        END
    """

    cursor.execute(query)
    results = cursor.fetchall()

    for row in results:
        print(f"  {row[0]}: {row[1]:,} properties")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROPERTY GAP ANALYSIS")
    print("RDS Properties NOT in Salesforce product_property_c")
    print("="*80)

    try:
        # Step 1: Verify matching key
        verify_matching_key()

        # Step 2: Find properties in RDS not in product_property_c
        results = find_property_gaps()

        # Step 3: Analyze patterns
        analyze_gap_patterns()

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"\nResults saved to: /Users/danerosa/rds_databricks_claude/output/missing_properties.csv")

    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
