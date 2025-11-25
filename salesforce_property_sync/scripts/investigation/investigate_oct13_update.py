#!/usr/bin/env python3
"""Deep dive into the October 13 operations that affected 2,432 rows."""

import json
from datetime import datetime

# Load the history data
with open('enterprise_property_history_20days.json', 'r') as f:
    operations = json.load(f)

print("=" * 80)
print("DEEP DIVE: OCTOBER 13, 2025 DATA LOSS EVENT")
print("=" * 80)

# Find operations on Oct 13
oct13_ops = [op for op in operations if '2025-10-13' in op.get('timestamp', '')]

print(f"\nFound {len(oct13_ops)} operations on October 13, 2025\n")

# Focus on the big updates
big_updates = [op for op in oct13_ops
               if op.get('operationMetrics', {}).get('numTargetRowsUpdated')
               and int(op.get('operationMetrics', {}).get('numTargetRowsUpdated', 0)) > 100]

big_updates.sort(key=lambda x: int(x.get('operationMetrics', {}).get('numTargetRowsUpdated', 0)), reverse=True)

print("=" * 80)
print("LARGE UPDATE OPERATIONS ON OCTOBER 13")
print("=" * 80)

for op in big_updates[:5]:
    metrics = op.get('operationMetrics', {})
    params = op.get('operationParameters', {})

    print(f"\nVersion: {op['version']}")
    print(f"Timestamp: {op['timestamp']}")
    print(f"Operation: {op['operation']}")
    print(f"User: {op['userName']}")

    print("\n📊 Metrics:")
    print(f"   Rows Updated: {int(metrics.get('numTargetRowsUpdated', 0) or 0):,}")
    print(f"   Rows Copied: {int(metrics.get('numTargetRowsCopied', 0) or 0):,}")
    print(f"   Rows Inserted: {int(metrics.get('numTargetRowsInserted', 0) or 0):,}")
    print(f"   Source Rows: {int(metrics.get('numSourceRows', 0) or 0):,}")
    print(f"   Files Added: {int(metrics.get('numTargetFilesAdded', 0) or 0)}")
    print(f"   Files Removed: {int(metrics.get('numTargetFilesRemoved', 0) or 0)}")

    print("\n🔍 Operation Parameters:")
    for key, value in params.items():
        print(f"   {key}: {value}")

    print("\n" + "-" * 80)

# Now look at what happened before and after
print("\n" + "=" * 80)
print("CONTEXT: Operations Around October 13")
print("=" * 80)

# Get operations from Oct 12 to Oct 14
context_ops = [op for op in operations
               if '2025-10-12' in op.get('timestamp', '') or
                  '2025-10-13' in op.get('timestamp', '') or
                  '2025-10-14' in op.get('timestamp', '')]

# Look for any UPDATE operations (not MERGE)
update_ops = [op for op in context_ops if op.get('operation') == 'UPDATE']

if update_ops:
    print(f"\n⚠️  Found {len(update_ops)} UPDATE operations (not MERGE):")
    for op in update_ops:
        print(f"\n   Version: {op['version']}")
        print(f"   Timestamp: {op['timestamp']}")
        metrics = op.get('operationMetrics', {})
        params = op.get('operationParameters', {})
        print(f"   Rows Updated: {int(metrics.get('numUpdatedRows', 0) or 0):,}")
        print(f"   Rows Copied: {int(metrics.get('numCopiedRows', 0) or 0):,}")
        if params.get('predicate'):
            print(f"   Predicate: {params['predicate']}")

# Get operations around version 22756-22757
target_versions = ['22756', '22757', '22755', '22758']
target_ops = [op for op in operations if op.get('version') in target_versions]
target_ops.sort(key=lambda x: int(x['version']))

print("\n" + "=" * 80)
print("DETAILED VIEW: Versions 22755-22758")
print("=" * 80)

for op in target_ops:
    print(f"\n{'=' * 80}")
    print(f"VERSION {op['version']} - {op['timestamp']}")
    print(f"{'=' * 80}")
    print(f"Operation: {op['operation']}")
    print(f"User: {op['userName']}")

    metrics = op.get('operationMetrics', {})
    print(f"\nMetrics:")
    for key, value in metrics.items():
        if 'Row' in key or 'row' in key:
            print(f"   {key}: {value}")

    params = op.get('operationParameters', {})
    print(f"\nParameters:")
    print(json.dumps(params, indent=3))

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print("""
Based on the data:

1. The table has a ROW FILTER that automatically hides rows where _fivetran_deleted = true
   Row Filter: `rds`.`pg_rds_enterprise_public`.`filter_deleted_rows` ON (_fivetran_deleted)

2. On October 13, 2025, there were MERGE operations that updated ~2,432 rows

3. These MERGE operations included predicates checking _fivetran_deleted status

4. The most likely scenario:
   - Fivetran detected deletions in the source PostgreSQL database
   - It set _fivetran_deleted = true on 2,432 rows
   - The row filter automatically hid these rows from queries
   - You're now seeing ~2,432 fewer rows than before

RECOMMENDATION:
   To see the "deleted" data, query the table without the filter:

   SELECT * FROM rds.pg_rds_enterprise_public.enterprise_property
   WHERE _fivetran_deleted = true

   This will show you which records were marked as deleted and when.
""")

print("=" * 80)
