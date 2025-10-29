#!/usr/bin/env python3
"""Analyze table history to find the most impactful operations."""

import json
from datetime import datetime
from collections import defaultdict

# Load the history data
with open('enterprise_property_history_20days.json', 'r') as f:
    operations = json.load(f)

print("=" * 80)
print("ANALYZING TABLE OPERATIONS FOR DATA IMPACT")
print("=" * 80)

# Track different types of impacts
deleted_rows = []
updated_rows = []
large_byte_changes = []
vacuum_operations = []
optimize_operations = []

for op in operations:
    version = op.get('version')
    timestamp = op.get('timestamp')
    operation = op.get('operation')
    metrics = op.get('operationMetrics', {})
    params = op.get('operationParameters', {})

    if not metrics:
        continue

    # Track deletions
    num_deleted = int(metrics.get('numTargetRowsDeleted', 0)) if metrics.get('numTargetRowsDeleted') else 0
    if num_deleted > 0:
        deleted_rows.append({
            'version': version,
            'timestamp': timestamp,
            'operation': operation,
            'rows_deleted': num_deleted,
            'parameters': params,
            'metrics': metrics
        })

    # Track updates (especially large ones)
    num_updated = int(metrics.get('numTargetRowsUpdated', 0)) if metrics.get('numTargetRowsUpdated') else 0
    num_copied = int(metrics.get('numTargetRowsCopied', 0)) if metrics.get('numTargetRowsCopied') else 0
    if num_updated > 0:
        updated_rows.append({
            'version': version,
            'timestamp': timestamp,
            'operation': operation,
            'rows_updated': num_updated,
            'rows_copied': num_copied,
            'parameters': params,
            'metrics': metrics
        })

    # Track large byte removals
    bytes_removed = int(metrics.get('numTargetBytesRemoved', 0)) if metrics.get('numTargetBytesRemoved') else 0
    bytes_added = int(metrics.get('numTargetBytesAdded', 0)) if metrics.get('numTargetBytesAdded') else 0
    net_bytes = bytes_added - bytes_removed

    if bytes_removed > 1000000:  # > 1MB removed
        large_byte_changes.append({
            'version': version,
            'timestamp': timestamp,
            'operation': operation,
            'bytes_removed': bytes_removed,
            'bytes_added': bytes_added,
            'net_change': net_bytes,
            'parameters': params,
            'metrics': metrics
        })

    # Track VACUUM operations (these permanently delete data)
    if operation == 'VACUUM END':
        vacuum_operations.append({
            'version': version,
            'timestamp': timestamp,
            'operation': operation,
            'parameters': params,
            'metrics': metrics
        })

    # Track OPTIMIZE operations
    if operation == 'OPTIMIZE':
        optimize_operations.append({
            'version': version,
            'timestamp': timestamp,
            'operation': operation,
            'metrics': metrics
        })

# Print findings
print("\n" + "=" * 80)
print("1. ROW DELETIONS")
print("=" * 80)
if deleted_rows:
    deleted_rows.sort(key=lambda x: x['rows_deleted'], reverse=True)
    print(f"\nFound {len(deleted_rows)} operations with row deletions")
    print("\nTop 10 operations by rows deleted:")
    for i, op in enumerate(deleted_rows[:10], 1):
        print(f"\n{i}. Version {op['version']} - {op['timestamp']}")
        print(f"   Operation: {op['operation']}")
        print(f"   Rows Deleted: {op['rows_deleted']:,}")
        if op['parameters']:
            print(f"   Parameters: {json.dumps(op['parameters'], indent=6)}")
else:
    print("\nNo row deletions found")

print("\n" + "=" * 80)
print("2. LARGE UPDATE OPERATIONS")
print("=" * 80)
updated_rows.sort(key=lambda x: x['rows_updated'], reverse=True)
print(f"\nTop 10 operations by rows updated:")
for i, op in enumerate(updated_rows[:10], 1):
    print(f"\n{i}. Version {op['version']} - {op['timestamp']}")
    print(f"   Operation: {op['operation']}")
    print(f"   Rows Updated: {op['rows_updated']:,}")
    print(f"   Rows Copied: {op['rows_copied']:,}")
    if '_fivetran' in str(op['parameters']):
        print(f"   ⚠️  Contains _fivetran_deleted predicate (soft delete)")
    # Show predicate for UPDATE operations
    if op['operation'] == 'UPDATE' and op['parameters'].get('predicate'):
        print(f"   Predicate: {op['parameters']['predicate']}")

print("\n" + "=" * 80)
print("3. LARGE DATA REMOVALS (by bytes)")
print("=" * 80)
if large_byte_changes:
    large_byte_changes.sort(key=lambda x: x['bytes_removed'], reverse=True)
    print(f"\nTop 10 operations by bytes removed:")
    for i, op in enumerate(large_byte_changes[:10], 1):
        print(f"\n{i}. Version {op['version']} - {op['timestamp']}")
        print(f"   Operation: {op['operation']}")
        print(f"   Bytes Removed: {op['bytes_removed']:,} ({op['bytes_removed']/1024/1024:.2f} MB)")
        print(f"   Bytes Added: {op['bytes_added']:,} ({op['bytes_added']/1024/1024:.2f} MB)")
        print(f"   Net Change: {op['net_change']:,} ({op['net_change']/1024/1024:.2f} MB)")
        if op['operation'] == 'UPDATE' and op['parameters'].get('predicate'):
            print(f"   Predicate: {op['parameters']['predicate']}")

print("\n" + "=" * 80)
print("4. VACUUM OPERATIONS (Permanent Deletions)")
print("=" * 80)
if vacuum_operations:
    print(f"\nFound {len(vacuum_operations)} VACUUM operations")
    for op in vacuum_operations:
        print(f"\n   Version {op['version']} - {op['timestamp']}")
else:
    print("\nNo VACUUM operations found")

print("\n" + "=" * 80)
print("5. KEY FINDINGS")
print("=" * 80)

# Look for the most significant impact
print("\n🔍 Most Impactful Operations:")

# Check for operations that updated many rows with _fivetran_deleted
fivetran_deletes = [op for op in updated_rows if '_fivetran_deleted' in str(op['parameters']) or '_fivetran_synced' in str(op['parameters'])]
if fivetran_deletes:
    fivetran_deletes.sort(key=lambda x: x['rows_updated'], reverse=True)
    top = fivetran_deletes[0]
    print(f"\n⚠️  LARGEST POTENTIAL DATA HIDING OPERATION:")
    print(f"   Version: {top['version']}")
    print(f"   Timestamp: {top['timestamp']}")
    print(f"   Operation: {top['operation']}")
    print(f"   Rows Updated: {top['rows_updated']:,}")
    print(f"   Rows Copied: {top['rows_copied']:,}")
    if top['parameters'].get('predicate'):
        print(f"\n   Predicate: {top['parameters']['predicate']}")
    print("\n   ⚠️  This operation likely set _fivetran_deleted=true on rows,")
    print("      which would make them invisible due to the row filter.")

# Total impact summary
total_deleted = sum(op['rows_deleted'] for op in deleted_rows)
total_updated = sum(op['rows_updated'] for op in updated_rows)

print(f"\n📊 SUMMARY:")
print(f"   Total Rows Deleted: {total_deleted:,}")
print(f"   Total Rows Updated: {total_updated:,}")
print(f"   Operations with Deletions: {len(deleted_rows)}")
print(f"   VACUUM Operations: {len(vacuum_operations)}")

print("\n" + "=" * 80)
