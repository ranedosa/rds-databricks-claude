#!/usr/bin/env python3
"""
List all catalogs and table counts
"""

import os
import requests
import pandas as pd

DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
WAREHOUSE_ID = "9b7a58ad33c27fbc"

def execute_query(query):
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
    if result.get('status', {}).get('state') == 'SUCCEEDED':
        manifest = result.get('manifest', {})
        schema = manifest.get('schema', {})
        columns = [col['name'] for col in schema.get('columns', [])]
        chunks = result.get('result', {}).get('data_array', [])
        if chunks:
            return pd.DataFrame(chunks, columns=columns)
    return None

# Get all catalogs and count tables in each
query = """
SELECT
    table_catalog,
    COUNT(*) as table_count,
    SUM(CASE WHEN table_type IN ('MANAGED', 'EXTERNAL') THEN 1 ELSE 0 END) as managed_external_count,
    SUM(CASE WHEN table_name LIKE '%_fivetran%' THEN 1 ELSE 0 END) as fivetran_count
FROM system.information_schema.tables
GROUP BY table_catalog
ORDER BY table_count DESC
"""

print("All Catalogs in Workspace:\n")
df = execute_query(query)
if df is not None:
    print(df.to_string(index=False))
    print(f"\n\nTotal catalogs: {len(df)}")

    # Highlight what we analyzed vs missed
    analyzed = ['rds', 'crm', 'product', 'team_sandbox']
    excluded_by_user = ['__databricks_internal', 'tmp_enterprise_catalog', 'star', 'samples']

    print("\n" + "="*80)
    print("ANALYSIS:")
    print("="*80)
    print("\nCatalogs I analyzed:")
    for cat in analyzed:
        if cat in df['table_catalog'].values:
            count = df[df['table_catalog'] == cat]['table_count'].values[0]
            print(f"  ✓ {cat}: {count} tables")

    print("\nCatalogs you asked to exclude:")
    for cat in excluded_by_user:
        if cat in df['table_catalog'].values:
            count = df[df['table_catalog'] == cat]['table_count'].values[0]
            print(f"  ✗ {cat}: {count} tables (excluded)")

    print("\nCatalogs I MISSED (but should have included):")
    for _, row in df.iterrows():
        cat = row['table_catalog']
        if cat not in analyzed and cat not in excluded_by_user:
            count = row['table_count']
            managed = row['managed_external_count']
            print(f"  ⚠️  {cat}: {count} tables ({managed} managed/external)")
