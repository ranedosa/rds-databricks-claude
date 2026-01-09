#!/usr/bin/env python3
"""
Script to find the 100 largest tables by querying each table's history
"""

import os
import requests
import pandas as pd
from datetime import datetime
import time

# Databricks configuration
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
WAREHOUSE_ID = "9b7a58ad33c27fbc"

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
        if not silent:
            log(f"HTTP Error {response.status_code}", "ERROR")
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
            return pd.DataFrame()
    else:
        return None

def get_table_size(full_table_name):
    """Get table size using SELECT COUNT and approximate bytes"""
    # Try getting row count and estimating size
    query = f"SELECT COUNT(*) as row_count FROM {full_table_name}"
    df = execute_query(query, f"Getting row count for {full_table_name}", silent=True)

    if df is not None and len(df) > 0:
        return df.iloc[0]['row_count']
    return 0

def main():
    print("=" * 80)
    print("Finding 100 Largest Tables By Row Count")
    print("=" * 80)

    # Get all managed/external Delta tables
    query = """
    SELECT
        t.table_catalog,
        t.table_schema,
        t.table_name,
        CONCAT(t.table_catalog, '.', t.table_schema, '.', t.table_name) as full_table_name,
        t.table_type
    FROM system.information_schema.tables t
    WHERE t.table_type IN ('MANAGED', 'EXTERNAL')
      AND t.table_catalog NOT IN ('__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples', 'system')
      AND t.table_name NOT LIKE '%_fivetran%'
      AND t.table_catalog IN ('rds', 'crm', 'product', 'team_sandbox')
    ORDER BY t.table_catalog, t.table_schema, t.table_name
    LIMIT 200
    """

    log("Getting list of tables to analyze")
    tables_df = execute_query(query, "Querying tables list")

    if tables_df is None or len(tables_df) == 0:
        log("No tables found", "ERROR")
        return

    log(f"Found {len(tables_df)} tables to analyze")

    # Get sizes for each table
    all_stats = []
    start_time = datetime.now()
    success_count = 0
    error_count = 0

    for idx, row in tables_df.iterrows():
        catalog = row['table_catalog']
        schema = row['table_schema']
        table_name = row['table_name']
        full_table_name = row['full_table_name']

        if idx % 10 == 0 and idx > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (len(tables_df) - idx) / rate if rate > 0 else 0
            log(f"Progress: {idx}/{len(tables_df)} ({idx/len(tables_df)*100:.0f}%) | "
                f"Success: {success_count} | Errors: {error_count} | "
                f"Rate: {rate:.1f}/sec | ETA: {remaining/60:.1f} min", "PROGRESS")

        try:
            row_count = get_table_size(full_table_name)

            if row_count is not None:
                all_stats.append({
                    'catalog': catalog,
                    'schema': schema,
                    'table_name': table_name,
                    'full_table_name': full_table_name,
                    'row_count': row_count
                })
                success_count += 1

                if row_count > 1000000:
                    log(f"Large table: {full_table_name} = {row_count:,} rows", "FOUND")
            else:
                error_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 3:
                log(f"Error with {full_table_name}: {str(e)}", "ERROR")

    log(f"Analysis complete: {success_count} tables analyzed, {error_count} errors", "SUCCESS")

    if all_stats:
        # Sort by row count
        stats_df = pd.DataFrame(all_stats)
        stats_df = stats_df.sort_values('row_count', ascending=False)

        # Get top 100
        top_100 = stats_df.head(100)

        print("\n" + "=" * 80)
        print("TOP 100 LARGEST TABLES BY ROW COUNT")
        print("=" * 80)
        print(f"\nTotal tables analyzed: {len(stats_df)}")
        print(f"\nTop 100 tables:\n")
        print(top_100.to_string())

        # Save results
        output_file = '/Users/danerosa/rds_databricks_claude/20251220/largest_tables_by_rows_top100.csv'
        top_100.to_csv(output_file, index=False)
        log(f"Saved to: {output_file}", "SUCCESS")

        # Full results
        full_output = '/Users/danerosa/rds_databricks_claude/20251220/all_table_row_counts.csv'
        stats_df.to_csv(full_output, index=False)
        log(f"Saved all results to: {full_output}", "SUCCESS")

        # Summary stats
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total rows (top 100): {top_100['row_count'].sum():,}")
        print(f"Average rows (top 100): {top_100['row_count'].mean():,.0f}")
        print(f"Median rows (top 100): {top_100['row_count'].median():,.0f}")
        print(f"Largest: {top_100.iloc[0]['full_table_name']} ({top_100.iloc[0]['row_count']:,} rows)")

        # By catalog
        print("\n" + "=" * 80)
        print("BY CATALOG (Top 100)")
        print("=" * 80)
        catalog_summary = top_100.groupby('catalog').agg({
            'row_count': ['count', 'sum', 'mean']
        })
        print(catalog_summary)

    else:
        log("No data collected", "ERROR")

if __name__ == "__main__":
    main()
