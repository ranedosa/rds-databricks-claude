#!/usr/bin/env python3
"""
Validate our database documentation against DBeaver GraphML ERD exports
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import re

def parse_graphml(filepath):
    """Parse a GraphML file and extract tables and columns"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Define namespace
    ns = {
        'graphml': 'http://graphml.graphdrawing.org/xmlns',
        'y': 'http://www.yworks.com/xml/graphml'
    }

    tables = {}

    # Find all nodes (tables)
    for node in root.findall('.//graphml:node', ns):
        node_labels = node.findall('.//y:NodeLabel', ns)

        if len(node_labels) >= 2:
            # First label is table name
            table_name_elem = node_labels[0]
            if 'com.yworks.entityRelationship.label.name' in table_name_elem.get('configuration', ''):
                table_name = table_name_elem.text.strip()

                # Second label contains columns
                columns_elem = node_labels[1]
                if 'com.yworks.entityRelationship.label.attributes' in columns_elem.get('configuration', ''):
                    columns_text = columns_elem.text
                    if columns_text:
                        columns = []
                        for line in columns_text.strip().split('\n'):
                            line = line.strip()
                            if ':' in line:
                                col_name, col_type = line.split(':', 1)
                                columns.append({
                                    'name': col_name.strip(),
                                    'type': col_type.strip()
                                })
                        tables[table_name] = columns

    return tables

def main():
    graphml_dir = Path('/Users/danerosa/rds_databricks_claude-erd/postgres')

    results = {}

    # Parse all GraphML files
    for graphml_file in sorted(graphml_dir.glob('*.graphml')):
        print(f"\n{'='*80}")
        print(f"Parsing: {graphml_file.name}")
        print(f"{'='*80}")

        tables = parse_graphml(graphml_file)
        db_name = graphml_file.stem
        results[db_name] = tables

        print(f"\nFound {len(tables)} tables:")
        for table_name in sorted(tables.keys()):
            columns = tables[table_name]
            print(f"  - {table_name} ({len(columns)} columns)")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    total_tables = sum(len(tables) for tables in results.values())
    print(f"Total databases: {len(results)}")
    print(f"Total tables: {total_tables}\n")

    for db_name in sorted(results.keys()):
        tables = results[db_name]
        total_columns = sum(len(cols) for cols in tables.values())
        print(f"{db_name}: {len(tables)} tables, {total_columns} columns")

    # Print detailed table lists for comparison
    print(f"\n{'='*80}")
    print("DETAILED TABLE LISTS BY DATABASE")
    print(f"{'='*80}\n")

    for db_name in sorted(results.keys()):
        print(f"\n{db_name}:")
        print("-" * 80)
        for table_name in sorted(results[db_name].keys()):
            columns = results[db_name][table_name]
            print(f"  {table_name}:")
            for col in columns[:5]:  # Show first 5 columns
                print(f"    - {col['name']}: {col['type']}")
            if len(columns) > 5:
                print(f"    ... and {len(columns) - 5} more columns")

if __name__ == '__main__':
    main()
