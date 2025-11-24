"""
Analyze gaps between RDS properties and Salesforce product_property_c table
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

def describe_salesforce_table(table_name):
    """Get schema of a Salesforce table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    print(f"\n=== Schema for {table_name} ===")
    cursor.execute(f"DESCRIBE TABLE {table_name}")

    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[0]}: {col[1]}")

    cursor.close()
    conn.close()
    return columns

def count_salesforce_records(table_name):
    """Count records in a Salesforce table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result[0]

def sample_salesforce_records(table_name, limit=5):
    """Get sample records from Salesforce table"""
    conn = get_databricks_connection()
    cursor = conn.cursor()

    print(f"\n=== Sample records from {table_name} ===")
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")

    # Get column names
    columns = [desc[0] for desc in cursor.description]
    print(f"Columns: {', '.join(columns)}")

    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\nRecord {i}:")
        for col, val in zip(columns, row):
            if val is not None and str(val).strip():
                print(f"  {col}: {val}")

    cursor.close()
    conn.close()

def list_catalogs():
    """List available catalogs"""
    conn = get_databricks_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW CATALOGS")
    catalogs = cursor.fetchall()
    cursor.close()
    conn.close()
    return [c[0] for c in catalogs]

def list_schemas(catalog):
    """List schemas in a catalog"""
    conn = get_databricks_connection()
    cursor = conn.cursor()
    cursor.execute(f"SHOW SCHEMAS IN {catalog}")
    schemas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [s[0] for s in schemas]

def list_tables(catalog, schema):
    """List tables in a schema"""
    conn = get_databricks_connection()
    cursor = conn.cursor()
    cursor.execute(f"SHOW TABLES IN {catalog}.{schema}")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return tables

def search_salesforce_tables():
    """Search for Salesforce-related tables"""
    print("\n=== Searching for Salesforce tables ===")

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Search for tables with 'property' or 'salesforce' in the name
    queries = [
        "SHOW CATALOGS",
        "SHOW SCHEMAS IN hive_metastore",
    ]

    for query in queries:
        try:
            print(f"\nExecuting: {query}")
            cursor.execute(query)
            results = cursor.fetchall()
            for row in results:
                print(f"  {row}")
        except Exception as e:
            print(f"  Error: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("Analyzing Salesforce tables in Databricks...")

    # First, discover what's available
    print("\n" + "="*80)
    print("DISCOVERING AVAILABLE TABLES")
    print("="*80)

    try:
        search_salesforce_tables()

        # List catalogs
        print("\n=== Available catalogs ===")
        catalogs = list_catalogs()
        for cat in catalogs:
            print(f"  - {cat}")

        # Look for Salesforce schemas
        for catalog in catalogs:
            print(f"\n=== Schemas in {catalog} ===")
            try:
                schemas = list_schemas(catalog)
                for schema in schemas:
                    if 'salesforce' in schema.lower() or 'crm' in schema.lower():
                        print(f"  *** {schema} (Salesforce-related)")
                    else:
                        print(f"  - {schema}")

                    # If it looks like Salesforce, list tables
                    if 'salesforce' in schema.lower() or 'crm' in schema.lower():
                        print(f"\n    Tables in {catalog}.{schema}:")
                        tables = list_tables(catalog, schema)
                        for table in tables:
                            table_name = table[1]
                            if 'property' in table_name.lower():
                                print(f"      *** {table_name} (property-related)")
                            else:
                                print(f"      - {table_name}")
            except Exception as e:
                print(f"  Error listing schemas: {e}")

    except Exception as e:
        print(f"Error during discovery: {e}")
