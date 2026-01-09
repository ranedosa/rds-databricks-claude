#!/usr/bin/env python3
"""
Script to find the 100 largest tables in Databricks workspace
"""

import os
import requests
import pandas as pd
from datetime import datetime

# Databricks configuration
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
WAREHOUSE_ID = "9b7a58ad33c27fbc"

# Catalogs to exclude
EXCLUDE_CATALOGS = ['__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples']

def log(message, level="INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}", flush=True)

def execute_query(query, description="Executing query", silent=False):
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

    if not silent:
        log(f"{description}")

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        log(f"Error {response.status_code}: {response.text}", "ERROR")
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
            if not silent:
                log(f"Retrieved {len(df)} rows", "SUCCESS")
            return df
        else:
            if not silent:
                log("Query succeeded (no rows)", "SUCCESS")
            return pd.DataFrame()
    else:
        error_message = status.get('error', {}).get('message', 'Unknown error')
        if not silent:
            log(f"Query failed ({state}): {error_message}", "ERROR")
        return None

def main():
    print("=" * 80)
    print("Finding 100 Largest Tables in Databricks Workspace")
    print("=" * 80)
    print(f"\nExcluding catalogs: {', '.join(EXCLUDE_CATALOGS)}")
    print("Excluding tables with '_fivetran' in name")

    # Use a more efficient query approach - get table history from system tables
    query_tables = """
    SELECT
        table_catalog,
        table_schema,
        table_name,
        table_type,
        CONCAT(table_catalog, '.', table_schema, '.', table_name) as full_table_name
    FROM system.information_schema.tables
    WHERE table_type IN ('MANAGED', 'EXTERNAL')
      AND table_catalog NOT IN ('__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples')
      AND table_name NOT LIKE '%_fivetran%'
    ORDER BY table_catalog, table_schema, table_name
    """

    print("\n" + "=" * 80)
    print("STEP 1: Getting all tables (excluding filtered catalogs/tables)")
    print("=" * 80)

    tables_df = execute_query(query_tables, "Querying system.information_schema.tables")

    if tables_df is None or len(tables_df) == 0:
        print("\n✗ Could not retrieve tables from information_schema")
        return

    print(f"\nFound {len(tables_df)} tables (after filters)")
    print("\nSample tables:")
    print(tables_df.head(20))

    # Now get sizes for tables - focusing on key catalogs
    print("\n" + "=" * 80)
    print("STEP 2: Getting table sizes")
    print("=" * 80)

    all_table_stats = []

    # Process tables in batches
    log(f"Starting to analyze {len(tables_df)} tables for sizes...")
    start_time = datetime.now()
    error_count = 0
    success_count = 0
    first_error_shown = False

    for idx, row in tables_df.iterrows():
        catalog = row['table_catalog']
        schema = row['table_schema']
        table_name = row['table_name']
        full_table_name = row['full_table_name']

        if idx % 10 == 0 and idx > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (len(tables_df) - idx) / rate if rate > 0 else 0
            log(f"Progress: {idx}/{len(tables_df)} tables ({idx/len(tables_df)*100:.1f}%) | "
                f"Successes: {success_count} | Errors: {error_count} | "
                f"Rate: {rate:.1f} tables/sec | ETA: {remaining/60:.1f} min", "PROGRESS")

        try:
            query_detail = f"DESCRIBE DETAIL `{full_table_name}`"
            # Show error for first table only
            detail_df = execute_query(query_detail, f"Analyzing {full_table_name}",
                                     silent=(error_count > 0 or success_count > 0))

            if detail_df is not None and len(detail_df) > 0:
                size_bytes = detail_df.iloc[0].get('sizeInBytes', 0)
                num_files = detail_df.iloc[0].get('numFiles', 0)

                all_table_stats.append({
                    'catalog': catalog,
                    'schema': schema,
                    'table_name': table_name,
                    'full_table_name': full_table_name,
                    'size_bytes': size_bytes,
                    'size_gb': round(size_bytes / (1024**3), 2) if size_bytes else 0,
                    'num_files': num_files
                })
                success_count += 1

                if size_bytes > 1024**3:  # Log if > 1GB
                    log(f"Found large table: {full_table_name} = {size_bytes / (1024**3):.2f} GB", "FOUND")
            else:
                error_count += 1
                # Only log first 5 errors in detail
                if error_count <= 5:
                    log(f"Failed to get size for: {full_table_name}", "ERROR")

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                log(f"Error analyzing {full_table_name}: {str(e)}", "ERROR")

        # Limit to first 500 tables to avoid timeout
        if idx >= 499:
            log(f"Stopping at 500 tables to avoid timeout", "WARNING")
            break

    log(f"Completed analysis: {success_count} successes, {error_count} errors", "SUCCESS")

    # Convert to DataFrame and sort by size
    if all_table_stats:
        log("Sorting and generating report...", "INFO")
        stats_df = pd.DataFrame(all_table_stats)
        stats_df = stats_df.sort_values('size_bytes', ascending=False)

        # Get top 100
        top_100 = stats_df.head(100)

        print("\n" + "=" * 80)
        print("TOP 100 LARGEST TABLES")
        print("=" * 80)
        log(f"Total tables analyzed: {len(stats_df)}", "SUMMARY")
        print(f"\nTop 100 tables by size:\n")
        print(top_100.to_string())

        # Save to CSV
        output_file = '/Users/danerosa/rds_databricks_claude/20251220/largest_tables_top100.csv'
        top_100.to_csv(output_file, index=False)
        log(f"Saved top 100 to: {output_file}", "SUCCESS")

        # Save full list
        full_output = '/Users/danerosa/rds_databricks_claude/20251220/all_table_sizes.csv'
        stats_df.to_csv(full_output, index=False)
        log(f"Saved full list to: {full_output}", "SUCCESS")

        # Print summary statistics
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
        catalog_summary = top_100.groupby('catalog').agg({
            'size_gb': ['count', 'sum', 'mean']
        }).round(2)
        print(catalog_summary)

        log("Analysis complete!", "SUCCESS")

    else:
        log("No table statistics collected", "ERROR")

if __name__ == "__main__":
    main()
