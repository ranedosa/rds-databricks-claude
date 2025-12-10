#!/usr/bin/env python3
"""
Query Databricks to identify top tables for each schema in the rds catalog.
"""

from databricks import sql
import configparser
import os
from collections import defaultdict
import sys

# Read Databricks config
config = configparser.ConfigParser()
config.read('/Users/danerosa/rds_databricks_claude/config/.databrickscfg')

host = config['DEFAULT']['host'].replace('https://', '')
token = config['DEFAULT']['token']

# Try multiple common warehouse paths
warehouse_paths = [
    '/sql/1.0/warehouses/48c6583a712e2b94',
    '/sql/1.0/endpoints/48c6583a712e2b94',
]

print("Attempting to connect to Databricks...")
connection = None

for path in warehouse_paths:
    try:
        print(f"Trying warehouse path: {path}")
        connection = sql.connect(
            server_hostname=host,
            http_path=path,
            access_token=token,
            _socket_timeout=30
        )
        print(f"✅ Connected successfully using path: {path}")
        break
    except Exception as e:
        print(f"❌ Failed with path {path}: {str(e)}")
        continue

if not connection:
    print("\n❌ Could not connect with any warehouse path.")
    print("Please provide the correct http_path for your SQL warehouse.")
    print("\nYou can find it in Databricks:")
    print("  1. Go to SQL Warehouses")
    print("  2. Select your warehouse")
    print("  3. Copy the 'HTTP Path' from Connection Details")
    sys.exit(1)

cursor = connection.cursor()

print("=" * 100)
print("QUERYING RDS CATALOG - TOP TABLES BY SCHEMA")
print("=" * 100)

try:
    # First, get all schemas in the rds catalog
    print("\n🔍 Finding schemas in rds catalog...")
    cursor.execute("SHOW SCHEMAS IN rds")
    schemas = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(schemas)} schemas: {', '.join(schemas)}\n")

    schema_tables = defaultdict(list)

    # For each schema, get table information
    for schema in schemas:
        if schema in ['information_schema']:  # Skip system schemas
            continue

        print(f"\n{'='*100}")
        print(f"📊 SCHEMA: rds.{schema}")
        print(f"{'='*100}")

        try:
            # Get detailed table information
            query = f"""
            SELECT
                table_name,
                table_type,
                CAST(NULL AS BIGINT) as row_count,
                CAST(NULL AS BIGINT) as size_bytes
            FROM system.information_schema.tables
            WHERE table_catalog = 'rds'
            AND table_schema = '{schema}'
            ORDER BY table_name
            """

            cursor.execute(query)
            tables = cursor.fetchall()

            if not tables:
                print(f"  No tables found in {schema}")
                continue

            print(f"\n  Found {len(tables)} tables in {schema}:")
            print(f"  {'-'*96}")
            print(f"  {'Table Name':<50} {'Type':<20}")
            print(f"  {'-'*96}")

            # Try to get row counts for each table
            table_info = []
            for table in tables:
                table_name = table[0]
                table_type = table[1]

                # Try to get row count
                try:
                    count_query = f"SELECT COUNT(*) FROM rds.{schema}.{table_name}"
                    cursor.execute(count_query)
                    row_count = cursor.fetchone()[0]
                except Exception as e:
                    row_count = None

                table_info.append({
                    'name': table_name,
                    'type': table_type,
                    'row_count': row_count
                })

            # Sort by row count (tables with counts first, then by count descending)
            table_info.sort(key=lambda x: (x['row_count'] is None, -(x['row_count'] or 0)))

            # Print top tables
            for idx, info in enumerate(table_info[:10], 1):  # Top 10 per schema
                row_count_str = f"{info['row_count']:,}" if info['row_count'] is not None else "N/A"
                print(f"  {idx:2}. {info['name']:<45} {info['type']:<20} Rows: {row_count_str}")

            if len(table_info) > 10:
                print(f"  ... and {len(table_info) - 10} more tables")

            schema_tables[schema] = table_info

        except Exception as e:
            print(f"  ⚠️  Error querying schema {schema}: {str(e)}")
            continue

    # Summary
    print(f"\n\n{'='*100}")
    print("📈 SUMMARY - TOP 5 LARGEST TABLES BY SCHEMA")
    print(f"{'='*100}")

    for schema in sorted(schema_tables.keys()):
        tables = schema_tables[schema]
        tables_with_counts = [t for t in tables if t['row_count'] is not None]

        if tables_with_counts:
            print(f"\n{schema}:")
            for idx, table in enumerate(tables_with_counts[:5], 1):
                print(f"  {idx}. {table['name']:<50} {table['row_count']:>15,} rows")
        else:
            print(f"\n{schema}: (No row count data available)")

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    cursor.close()
    connection.close()
    print("\n✅ Connection closed")
