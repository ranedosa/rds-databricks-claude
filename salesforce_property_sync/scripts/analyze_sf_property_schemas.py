"""
Analyze schemas of Salesforce property tables to understand the data structure
"""
from databricks import sql
import os

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

def describe_table(table_name):
    """Get detailed schema of a table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print(f"Schema for {table_name}")
    print('='*80)

    cursor.execute(f"DESCRIBE TABLE {table_name}")
    columns = cursor.fetchall()

    print(f"\n{'Column Name':<40} {'Type':<30} {'Nullable'}")
    print('-'*80)
    for col in columns:
        col_name = col[0]
        col_type = col[1]
        print(f"{col_name:<40} {col_type:<30}")

    cursor.close()
    conn.close()
    return columns

def count_records(table_name):
    """Count records in a table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result[0]

def sample_records(table_name, limit=3):
    """Get sample records from a table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print(f"Sample records from {table_name}")
    print('='*80)

    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")

    # Get column names
    columns = [desc[0] for desc in cursor.description]

    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\nRecord {i}:")
        for col, val in zip(columns, row):
            if val is not None and str(val).strip():
                # Truncate long values
                val_str = str(val)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                print(f"  {col}: {val_str}")

    cursor.close()
    conn.close()

def get_distinct_count(table_name, column_name):
    """Get distinct count of a column"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT COUNT(DISTINCT {column_name}) as distinct_count FROM {table_name}")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0]
    except Exception as e:
        cursor.close()
        conn.close()
        return f"Error: {e}"

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SALESFORCE PROPERTY TABLES ANALYSIS")
    print("="*80)

    # Analyze product_property_c (staging table)
    print("\n\n" + "#"*80)
    print("# TABLE 1: hive_metastore.salesforce.product_property_c (STAGING)")
    print("#"*80)

    try:
        describe_table("hive_metastore.salesforce.product_property_c")
        count = count_records("hive_metastore.salesforce.product_property_c")
        print(f"\nTotal records: {count:,}")
        sample_records("hive_metastore.salesforce.product_property_c", limit=3)
    except Exception as e:
        print(f"Error analyzing product_property_c: {e}")

    # Analyze property_c (final production table)
    print("\n\n" + "#"*80)
    print("# TABLE 2: hive_metastore.salesforce.property_c (PRODUCTION)")
    print("#"*80)

    try:
        describe_table("hive_metastore.salesforce.property_c")
        count = count_records("hive_metastore.salesforce.property_c")
        print(f"\nTotal records: {count:,}")
        sample_records("hive_metastore.salesforce.property_c", limit=3)
    except Exception as e:
        print(f"Error analyzing property_c: {e}")

    # Check if RDS data is available in Databricks
    print("\n\n" + "#"*80)
    print("# TABLE 3: rds.pg_rds_public.properties (RDS SOURCE IN DATABRICKS)")
    print("#"*80)

    try:
        # Check if table exists
        conn = get_databricks_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES IN rds.pg_rds_public")
        tables = cursor.fetchall()
        cursor.close()
        conn.close()

        print("\nTables in rds.pg_rds_public:")
        properties_exists = False
        for table in tables:
            table_name = table[1]
            print(f"  - {table_name}")
            if table_name == 'properties':
                properties_exists = True

        if properties_exists:
            print("\n✓ Properties table found in Databricks!")
            describe_table("rds.pg_rds_public.properties")
            count = count_records("rds.pg_rds_public.properties")
            print(f"\nTotal records: {count:,}")
            sample_records("rds.pg_rds_public.properties", limit=3)

            # Get distinct count of sfdc_id
            print("\n\nKey metrics:")
            distinct_sfdc_id = get_distinct_count("rds.pg_rds_public.properties", "sfdc_id")
            print(f"  Distinct sfdc_id values: {distinct_sfdc_id:,}" if isinstance(distinct_sfdc_id, int) else f"  Distinct sfdc_id values: {distinct_sfdc_id}")

            null_sfdc_id_conn = get_databricks_connection()
            null_sfdc_id_cursor = null_sfdc_id_conn.cursor()
            null_sfdc_id_cursor.execute("SELECT COUNT(*) FROM rds.pg_rds_public.properties WHERE sfdc_id IS NULL OR sfdc_id = ''")
            null_count = null_sfdc_id_cursor.fetchone()[0]
            null_sfdc_id_cursor.close()
            null_sfdc_id_conn.close()
            print(f"  Properties with NULL or empty sfdc_id: {null_count:,}")
        else:
            print("\n✗ Properties table NOT found in rds.pg_rds_public")
            print("  You may need to set up Lakeflow Connect to sync RDS data to Databricks")

    except Exception as e:
        print(f"Error checking RDS data: {e}")

    print("\n\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
