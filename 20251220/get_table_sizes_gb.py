#!/usr/bin/env python3
"""
Get actual storage sizes in GB for the top 100 tables
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

def execute_query(query, silent=False):
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

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
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
            return pd.DataFrame(chunks, columns=columns)
    return None

def get_table_size_gb(full_table_name):
    """Get table size in GB using DESCRIBE DETAIL"""
    query = f"DESCRIBE DETAIL {full_table_name}"
    df = execute_query(query, silent=True)

    if df is not None and len(df) > 0:
        size_bytes = df.iloc[0].get('sizeInBytes', 0)
        num_files = df.iloc[0].get('numFiles', 0)

        if size_bytes is not None:
            try:
                size_gb = float(size_bytes) / (1024**3)
                return size_gb, num_files
            except:
                return None, None
    return None, None

def main():
    print("=" * 80)
    print("Getting Storage Sizes for Top 100 Tables")
    print("=" * 80)

    # Load the top 100 tables from previous analysis
    top_100_file = '/Users/danerosa/rds_databricks_claude/20251220/largest_tables_complete_top100.csv'
    top_100_df = pd.read_csv(top_100_file)

    log(f"Loaded {len(top_100_df)} tables from previous analysis")

    # Get sizes for each table
    all_sizes = []
    start_time = datetime.now()
    success_count = 0
    error_count = 0

    for idx, row in top_100_df.iterrows():
        catalog = row['catalog']
        schema = row['schema']
        table_name = row['table_name']
        full_table_name = row['full_table_name']
        row_count = row['row_count']

        if idx % 10 == 0 and idx > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (len(top_100_df) - idx) / rate if rate > 0 else 0
            log(f"Progress: {idx}/{len(top_100_df)} ({idx/len(top_100_df)*100:.0f}%) | "
                f"Success: {success_count} | Errors: {error_count} | "
                f"ETA: {remaining/60:.1f} min", "PROGRESS")

        try:
            size_gb, num_files = get_table_size_gb(full_table_name)

            if size_gb is not None:
                all_sizes.append({
                    'catalog': catalog,
                    'schema': schema,
                    'table_name': table_name,
                    'full_table_name': full_table_name,
                    'row_count': row_count,
                    'size_gb': round(size_gb, 2),
                    'num_files': num_files
                })
                success_count += 1

                if size_gb > 10:
                    log(f"Large: {full_table_name} = {size_gb:.2f} GB ({row_count:,} rows)", "FOUND")
            else:
                all_sizes.append({
                    'catalog': catalog,
                    'schema': schema,
                    'table_name': table_name,
                    'full_table_name': full_table_name,
                    'row_count': row_count,
                    'size_gb': None,
                    'num_files': None
                })
                error_count += 1
                if error_count <= 5:
                    log(f"Could not get size for: {full_table_name}", "ERROR")

        except Exception as e:
            all_sizes.append({
                'catalog': catalog,
                'schema': schema,
                'table_name': table_name,
                'full_table_name': full_table_name,
                'row_count': row_count,
                'size_gb': None,
                'num_files': None
            })
            error_count += 1
            if error_count <= 3:
                log(f"Error with {full_table_name}: {str(e)}", "ERROR")

    log(f"Analysis complete: {success_count} sizes retrieved, {error_count} errors", "SUCCESS")

    # Create DataFrame and sort by size
    sizes_df = pd.DataFrame(all_sizes)

    # Remove rows with no size data and sort
    valid_sizes_df = sizes_df[sizes_df['size_gb'].notna()].copy()
    valid_sizes_df = valid_sizes_df.sort_values('size_gb', ascending=False)

    print("\n" + "=" * 80)
    print("TOP 100 TABLES BY STORAGE SIZE (GB)")
    print("=" * 80)
    print(f"\nTables with size data: {len(valid_sizes_df)}/100")
    print(f"\nTop tables by storage size:\n")
    print(valid_sizes_df.head(50).to_string())

    # Save results
    output_file = '/Users/danerosa/rds_databricks_claude/20251220/top_100_with_sizes_gb.csv'
    sizes_df.to_csv(output_file, index=False)
    log(f"Saved to: {output_file}", "SUCCESS")

    # Summary statistics
    if len(valid_sizes_df) > 0:
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        total_size_gb = valid_sizes_df['size_gb'].sum()
        avg_size_gb = valid_sizes_df['size_gb'].mean()
        median_size_gb = valid_sizes_df['size_gb'].median()
        total_rows = valid_sizes_df['row_count'].sum()

        print(f"\n✅ Total storage (tables with size data): {total_size_gb:.2f} GB")
        print(f"   Total rows: {total_rows:,}")
        print(f"   Average size: {avg_size_gb:.2f} GB")
        print(f"   Median size: {median_size_gb:.2f} GB")

        # Top 5 largest
        print(f"\n🔥 Top 5 Largest by Storage:")
        for idx, row in valid_sizes_df.head(5).iterrows():
            print(f"   {idx+1}. {row['full_table_name']}")
            print(f"      Size: {row['size_gb']:.2f} GB | Rows: {row['row_count']:,}")

        # By catalog
        print("\n" + "=" * 80)
        print("STORAGE BY CATALOG")
        print("=" * 80)
        catalog_summary = valid_sizes_df.groupby('catalog').agg({
            'size_gb': ['count', 'sum', 'mean']
        }).round(2)
        print(catalog_summary)

        # Estimate for missing data
        if error_count > 0:
            print(f"\n⚠️  Note: {error_count} tables missing size data")
            print(f"   Estimated total if same avg: {(total_size_gb/success_count*100):.2f} GB")

    else:
        log("No size data collected", "ERROR")

if __name__ == "__main__":
    main()
