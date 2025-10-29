#!/usr/bin/env python3
"""Get table history operation parameters for the last 20 days and save to JSON."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import json
from datetime import datetime, timedelta

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Table to query
table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print(f"TABLE HISTORY: {table_name}")
print("=" * 80)

try:
    # Get SQL warehouses to execute the query
    warehouses = list(w.warehouses.list())

    if not warehouses:
        print("No SQL warehouses found. Please create a SQL warehouse first.")
        exit(1)

    # Use the first available warehouse
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name} (ID: {warehouse.id})")
    print(f"State: {warehouse.state.value if warehouse.state else 'UNKNOWN'}")

    # Calculate the date 20 days ago
    twenty_days_ago = datetime.utcnow() - timedelta(days=20)
    print(f"\nFiltering operations from: {twenty_days_ago.isoformat()}Z")

    # Execute DESCRIBE HISTORY query
    print(f"\nExecuting: DESCRIBE HISTORY {table_name}")
    print("Waiting for results...")

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=f"DESCRIBE HISTORY {table_name}",
        wait_timeout="50s"
    )

    if result.status and result.status.state:
        print(f"Query Status: {result.status.state.value}")

    # Process results
    if result.result and result.result.data_array:
        # Get column names from manifest
        columns = []
        if result.manifest and result.manifest.schema and result.manifest.schema.columns:
            columns = [col.name for col in result.manifest.schema.columns]

        print(f"\nTotal history records: {len(result.result.data_array)}")

        # Build list of operations from last 20 days
        operations = []

        for row in result.result.data_array:
            # Create dictionary for this row
            record = {}
            for col_name, value in zip(columns, row):
                record[col_name] = value

            # Parse timestamp
            if 'timestamp' in record and record['timestamp']:
                try:
                    # Parse ISO format timestamp
                    timestamp_str = record['timestamp']
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1]
                    record_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                    # Check if within last 20 days
                    if record_time >= twenty_days_ago:
                        # Parse JSON fields
                        operation_data = {
                            'version': record.get('version'),
                            'timestamp': record.get('timestamp'),
                            'userId': record.get('userId'),
                            'userName': record.get('userName'),
                            'operation': record.get('operation'),
                            'operationParameters': None,
                            'operationMetrics': None,
                            'job': record.get('job'),
                            'notebook': record.get('notebook'),
                            'clusterId': record.get('clusterId'),
                            'readVersion': record.get('readVersion'),
                            'isolationLevel': record.get('isolationLevel'),
                            'isBlindAppend': record.get('isBlindAppend'),
                            'userMetadata': record.get('userMetadata'),
                            'engineInfo': record.get('engineInfo')
                        }

                        # Parse operationParameters JSON
                        if record.get('operationParameters'):
                            try:
                                operation_data['operationParameters'] = json.loads(record['operationParameters'])
                            except:
                                operation_data['operationParameters'] = record['operationParameters']

                        # Parse operationMetrics JSON
                        if record.get('operationMetrics'):
                            try:
                                operation_data['operationMetrics'] = json.loads(record['operationMetrics'])
                            except:
                                operation_data['operationMetrics'] = record['operationMetrics']

                        operations.append(operation_data)
                except Exception as e:
                    print(f"Error parsing timestamp: {e}")
                    continue

        print(f"Operations in last 20 days: {len(operations)}")

        # Save to JSON file
        output_file = "enterprise_property_history_20days.json"
        with open(output_file, 'w') as f:
            json.dump(operations, f, indent=2)

        print(f"\n✓ Saved to {output_file}")

        # Print summary statistics
        if operations:
            print("\nSummary:")
            print("-" * 80)

            # Count operations by type
            op_types = {}
            for op in operations:
                op_type = op.get('operation', 'UNKNOWN')
                op_types[op_type] = op_types.get(op_type, 0) + 1

            print("\nOperations by type:")
            for op_type, count in sorted(op_types.items()):
                print(f"  {op_type}: {count}")

            # Date range
            if len(operations) > 0:
                print(f"\nDate range:")
                print(f"  Earliest: {operations[-1]['timestamp']}")
                print(f"  Latest: {operations[0]['timestamp']}")

    else:
        print("\nNo history records found or empty result.")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
