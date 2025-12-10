#!/usr/bin/env python3
"""
Query Databricks Unity Catalog via REST API to identify top tables for each schema in the rds catalog.
"""

import requests
import configparser
from collections import defaultdict
import json

# Read Databricks config
config = configparser.ConfigParser()
config.read('/Users/danerosa/rds_databricks_claude/config/.databrickscfg')

host = config['DEFAULT']['host']
token = config['DEFAULT']['token']

# Setup headers
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print("=" * 100)
print("QUERYING RDS CATALOG VIA REST API - TOP TABLES BY SCHEMA")
print("=" * 100)

try:
    # List all schemas in the rds catalog
    print("\n🔍 Finding schemas in rds catalog...")
    schemas_url = f"{host}/api/2.1/unity-catalog/schemas"
    params = {'catalog_name': 'rds', 'max_results': 100}

    response = requests.get(schemas_url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"❌ Error fetching schemas: {response.status_code}")
        print(f"Response: {response.text}")
        exit(1)

    schemas_data = response.json()
    schemas = [s['name'] for s in schemas_data.get('schemas', [])]

    print(f"Found {len(schemas)} schemas: {', '.join(schemas)}\n")

    schema_tables = defaultdict(list)

    # For each schema, get tables
    for schema in schemas:
        if schema in ['information_schema']:  # Skip system schemas
            continue

        print(f"\n{'='*100}")
        print(f"📊 SCHEMA: rds.{schema}")
        print(f"{'='*100}")

        try:
            # Get tables in this schema
            tables_url = f"{host}/api/2.1/unity-catalog/tables"
            params = {'catalog_name': 'rds', 'schema_name': schema, 'max_results': 100}

            response = requests.get(tables_url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"  ⚠️  Error fetching tables: {response.status_code}")
                continue

            tables_data = response.json()
            tables = tables_data.get('tables', [])

            if not tables:
                print(f"  No tables found in {schema}")
                continue

            print(f"\n  Found {len(tables)} tables in {schema}:")
            print(f"  {'-'*96}")
            print(f"  {'#':<4} {'Table Name':<50} {'Type':<20} {'Size (MB)'}")
            print(f"  {'-'*96}")

            # Collect table info
            table_info = []
            for table in tables:
                table_name = table['name']
                table_type = table.get('table_type', 'UNKNOWN')

                # Try to get size info from storage_location or properties
                size_mb = None
                if 'storage_location' in table:
                    # Size might be in table properties
                    props = table.get('properties', {})
                    if 'delta.size' in props:
                        size_mb = int(props['delta.size']) / (1024 * 1024)

                table_info.append({
                    'name': table_name,
                    'type': table_type,
                    'size_mb': size_mb,
                    'full_name': table.get('full_name', f'rds.{schema}.{table_name}')
                })

            # Sort by size (tables with size first, then by size descending)
            table_info.sort(key=lambda x: (x['size_mb'] is None, -(x['size_mb'] or 0)))

            # Print all tables
            for idx, info in enumerate(table_info, 1):
                size_str = f"{info['size_mb']:.2f}" if info['size_mb'] is not None else "N/A"
                print(f"  {idx:<4} {info['name']:<50} {info['type']:<20} {size_str}")

            schema_tables[schema] = table_info

        except Exception as e:
            print(f"  ⚠️  Error querying schema {schema}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # Summary by schema
    print(f"\n\n{'='*100}")
    print("📈 SUMMARY - TABLES BY SCHEMA")
    print(f"{'='*100}\n")

    for schema in sorted(schema_tables.keys()):
        tables = schema_tables[schema]
        print(f"\n{schema}: {len(tables)} tables")

        # Show top 10 tables
        for idx, table in enumerate(tables[:10], 1):
            size_str = f" ({table['size_mb']:.2f} MB)" if table['size_mb'] is not None else ""
            print(f"  {idx:2}. {table['name']:<50} {table['type']:<15}{size_str}")

        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more tables")

    # Grand summary
    print(f"\n\n{'='*100}")
    print("📊 OVERALL SUMMARY")
    print(f"{'='*100}\n")

    total_tables = sum(len(tables) for tables in schema_tables.values())
    print(f"Total Schemas: {len(schema_tables)}")
    print(f"Total Tables: {total_tables}")

    print("\nTables per schema:")
    for schema in sorted(schema_tables.keys()):
        print(f"  {schema:<30} {len(schema_tables[schema]):>5} tables")

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n✅ Query complete")
