#!/usr/bin/env python3
"""
Get actual storage sizes in GB for ALL tables in workspace
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
    print("Getting Storage Sizes for ALL Tables in Workspace")
    print("=" * 80)

    # Load ALL tables from previous analysis
    all_tables_file = '/Users/danerosa/rds_databricks_claude/20251220/all_table_row_counts_complete.csv'
    all_tables_df = pd.read_csv(all_tables_file)

    log(f"Loaded {len(all_tables_df)} tables from previous analysis")

    # Get sizes for each table
    all_sizes = []
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    total_size_gb = 0

    for idx, row in all_tables_df.iterrows():
        catalog = row['catalog']
        schema = row['schema']
        table_name = row['table_name']
        full_table_name = row['full_table_name']
        row_count = row['row_count']

        if idx % 25 == 0 and idx > 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = idx / elapsed if elapsed > 0 else 0
            remaining = (len(all_tables_df) - idx) / rate if rate > 0 else 0
            log(f"Progress: {idx}/{len(all_tables_df)} ({idx/len(all_tables_df)*100:.0f}%) | "
                f"Success: {success_count} | Errors: {error_count} | "
                f"Total so far: {total_size_gb:.2f} GB | "
                f"Rate: {rate:.1f}/sec | ETA: {remaining/60:.1f} min", "PROGRESS")

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
                total_size_gb += size_gb
                success_count += 1

                if size_gb > 5:
                    log(f"Large: {full_table_name} = {size_gb:.2f} GB", "FOUND")
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

    log(f"Analysis complete: {success_count} sizes retrieved, {error_count} errors", "SUCCESS")

    # Create DataFrame
    sizes_df = pd.DataFrame(all_sizes)

    # Separate valid and invalid sizes
    valid_sizes_df = sizes_df[sizes_df['size_gb'].notna()].copy()
    valid_sizes_df = valid_sizes_df.sort_values('size_gb', ascending=False)

    print("\n" + "=" * 80)
    print("WORKSPACE STORAGE SUMMARY")
    print("=" * 80)
    print(f"\nTables analyzed: {len(sizes_df)}")
    print(f"Tables with size data: {len(valid_sizes_df)}")
    print(f"Tables without size data: {error_count}")

    # Save complete results
    output_file = '/Users/danerosa/rds_databricks_claude/20251220/all_tables_with_sizes_gb.csv'
    sizes_df.to_csv(output_file, index=False)
    log(f"Saved complete results to: {output_file}", "SUCCESS")

    # Summary statistics
    if len(valid_sizes_df) > 0:
        print("\n" + "=" * 80)
        print("🎯 TOTAL WORKSPACE STORAGE")
        print("=" * 80)

        total_size_gb = valid_sizes_df['size_gb'].sum()
        total_rows = valid_sizes_df['row_count'].sum()
        avg_size_gb = valid_sizes_df['size_gb'].mean()
        median_size_gb = valid_sizes_df['size_gb'].median()

        print(f"\n✅ TOTAL STORAGE: {total_size_gb:.2f} GB")
        print(f"   Total rows: {total_rows:,}")
        print(f"   Tables with data: {len(valid_sizes_df)}")
        print(f"   Average size per table: {avg_size_gb:.2f} GB")
        print(f"   Median size per table: {median_size_gb:.2f} GB")

        # Top 20 largest
        print(f"\n🔥 Top 20 Largest Tables:")
        for idx, row in valid_sizes_df.head(20).iterrows():
            print(f"   {idx+1}. {row['full_table_name']}")
            print(f"      {row['size_gb']:.2f} GB | {row['row_count']:,} rows")

        # By catalog
        print("\n" + "=" * 80)
        print("STORAGE BY CATALOG")
        print("=" * 80)
        catalog_summary = valid_sizes_df.groupby('catalog').agg({
            'size_gb': ['count', 'sum', 'mean'],
            'row_count': 'sum'
        }).round(2)
        catalog_summary.columns = ['table_count', 'total_gb', 'avg_gb', 'total_rows']
        catalog_summary = catalog_summary.sort_values('total_gb', ascending=False)
        print(catalog_summary)

        # Percentage breakdown
        print("\n" + "=" * 80)
        print("PERCENTAGE OF TOTAL STORAGE")
        print("=" * 80)
        for catalog, group in valid_sizes_df.groupby('catalog'):
            cat_size = group['size_gb'].sum()
            pct = (cat_size / total_size_gb) * 100
            print(f"{catalog:30s}: {cat_size:>10.2f} GB ({pct:>5.1f}%)")

        # Save top 100 by size
        top_100_by_size = valid_sizes_df.head(100)
        top_100_file = '/Users/danerosa/rds_databricks_claude/20251220/top_100_by_storage_gb.csv'
        top_100_by_size.to_csv(top_100_file, index=False)
        log(f"Saved top 100 by storage to: {top_100_file}", "SUCCESS")

        # Estimate for missing data
        if error_count > 0:
            print(f"\n⚠️  NOTE:")
            print(f"   {error_count} tables missing size data (likely system tables or views)")
            estimated = (total_size_gb / success_count) * len(sizes_df)
            print(f"   Estimated total if same avg: {estimated:.2f} GB")

    else:
        log("No size data collected", "ERROR")

if __name__ == "__main__":
    main()
