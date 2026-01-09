#!/usr/bin/env python3
"""
Script to find the 100 largest tables using system.information_schema.table_storage
"""

import os
import requests
import pandas as pd
from datetime import datetime

# Databricks configuration
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
WAREHOUSE_ID = "9b7a58ad33c27fbc"

def log(message, level="INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}", flush=True)

def execute_query(query, description="Executing query"):
    """Execute a SQL query using Databricks REST API"""
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements/"
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": "50s"
    }

    log(f"{description}")

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        log(f"HTTP Error {response.status_code}: {response.text}", "ERROR")
        return None

    result = response.json()
    status = result.get('status', {})
    state = status.get('state')

    if state == 'SUCCEEDED':
        manifest = result.get('manifest', {})
        schema = manifest.get('schema', {})
        columns = [col['name'] for col in schema.get('columns', [])]

        chunks = result.get('result', {}).get('data_array', [])
        if chunks:
            df = pd.DataFrame(chunks, columns=columns)
            log(f"Retrieved {len(df)} rows", "SUCCESS")
            return df
        else:
            log("Query succeeded (no rows)", "SUCCESS")
            return pd.DataFrame()
    else:
        error_message = status.get('error', {}).get('message', 'Unknown error')
        log(f"Query failed ({state}): {error_message[:200]}", "ERROR")
        return None

def main():
    print("=" * 80)
    print("Finding 100 Largest Tables Using System Tables")
    print("=" * 80)

    # Try using system.information_schema.table_storage which has size info
    query = """
    SELECT
        table_catalog,
        table_schema,
        table_name,
        CONCAT(table_catalog, '.', table_schema, '.', table_name) as full_table_name,
        data_size_bytes,
        ROUND(data_size_bytes / (1024*1024*1024), 2) as size_gb,
        num_files
    FROM system.information_schema.table_storage
    WHERE table_catalog NOT IN ('__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples')
      AND table_name NOT LIKE '%_fivetran%'
    ORDER BY data_size_bytes DESC
    LIMIT 500
    """

    log("Querying system.information_schema.table_storage for table sizes")
    df = execute_query(query, "Getting table sizes from system tables")

    if df is None or len(df) == 0:
        log("Could not retrieve table sizes from system.information_schema.table_storage", "ERROR")
        log("Trying alternative approach...", "INFO")

        # Alternative: Get all Delta tables and their sizes
        alt_query = """
        SELECT
            t.table_catalog,
            t.table_schema,
            t.table_name,
            CONCAT(t.table_catalog, '.', t.table_schema, '.', t.table_name) as full_table_name
        FROM system.information_schema.tables t
        WHERE t.table_type = 'MANAGED'
          AND t.table_catalog NOT IN ('__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples')
          AND t.table_name NOT LIKE '%_fivetran%'
        LIMIT 100
        """

        df = execute_query(alt_query, "Getting list of managed tables")

        if df is None:
            log("Failed to retrieve tables", "ERROR")
            return

    # Process results
    if len(df) > 0:
        # Get top 100
        top_100 = df.head(100)

        print("\n" + "=" * 80)
        print("TOP 100 LARGEST TABLES")
        print("=" * 80)
        print(f"\nTotal tables found: {len(df)}")
        print(f"\nTop 100 tables by size:\n")
        print(top_100.to_string())

        # Save to CSV
        output_file = '/Users/danerosa/rds_databricks_claude/20251220/largest_tables_top100.csv'
        top_100.to_csv(output_file, index=False)
        log(f"Saved top 100 to: {output_file}", "SUCCESS")

        # Save full list if more than 100
        if len(df) > 100:
            full_output = '/Users/danerosa/rds_databricks_claude/20251220/all_table_sizes.csv'
            df.to_csv(full_output, index=False)
            log(f"Saved full list ({len(df)} tables) to: {full_output}", "SUCCESS")

        # Print summary statistics
        if 'size_gb' in df.columns:
            print("\n" + "=" * 80)
            print("SUMMARY STATISTICS")
            print("=" * 80)
            print(f"\nTotal size of top 100 tables: {top_100['size_gb'].sum():.2f} GB")
            print(f"Average table size (top 100): {top_100['size_gb'].mean():.2f} GB")
            print(f"Median table size (top 100): {top_100['size_gb'].median():.2f} GB")
            print(f"Largest table: {top_100.iloc[0]['full_table_name']} ({top_100.iloc[0]['size_gb']:.2f} GB)")

            # Show breakdown by catalog
            print("\n" + "=" * 80)
            print("BREAKDOWN BY CATALOG (Top 100)")
            print("=" * 80)
            catalog_summary = top_100.groupby('table_catalog').agg({
                'size_gb': ['count', 'sum', 'mean']
            }).round(2)
            print(catalog_summary)

        log("Analysis complete!", "SUCCESS")
    else:
        log("No tables found", "ERROR")

if __name__ == "__main__":
    main()
