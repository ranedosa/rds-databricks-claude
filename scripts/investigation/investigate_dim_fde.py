#!/usr/bin/env python3
"""Investigate product.fde.dim_fde table for DLT conversion assessment."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import re

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

print("=" * 80)
print("INVESTIGATING product.fde.dim_fde TABLE")
print("=" * 80)

table_name = "product.fde.dim_fde"

# Step 1: Get table metadata
print(f"\n{'=' * 80}")
print("TABLE METADATA")
print(f"{'=' * 80}\n")

try:
    # Using SQL to get table info
    from databricks.sdk.service.sql import StatementState

    # Get table details
    query = f"DESCRIBE EXTENDED {table_name}"
    print(f"Querying: {query}\n")

    statement = w.statement_execution.execute_statement(
        warehouse_id="3f6dd2f58e0d5c95",  # We'll need to find a warehouse
        statement=query,
        wait_timeout="30s"
    )

    if statement.status and statement.status.state == StatementState.SUCCEEDED:
        print("Table exists! Getting details...\n")
except Exception as e:
    print(f"Note: Could not query table directly: {e}")
    print("Will search for table references in notebooks...\n")

# Step 2: Search for notebooks that reference this table
print(f"{'=' * 80}")
print("SEARCHING FOR NOTEBOOKS THAT REFERENCE dim_fde")
print(f"{'=' * 80}\n")

search_patterns = [
    "product.fde.dim_fde",
    "dim_fde",
    "fde.dim_fde"
]

# Search in common directories
search_paths = [
    "/Workspace/snappt",
    "/Workspace/Users/dane@snappt.com",
    "/Repos/dbx_git/dbx/snappt",
    "/Workspace/data_team"
]

notebooks_found = {}

for search_path in search_paths:
    try:
        print(f"Searching in: {search_path}")
        items = list(w.workspace.list(search_path, recursive=True))

        notebooks = [item for item in items if item.object_type and
                    str(item.object_type).endswith('NOTEBOOK')]

        for notebook in notebooks:
            try:
                # Export and search notebook content
                exported = w.workspace.export(notebook.path, format="SOURCE")
                if exported.content:
                    content = exported.content.decode('utf-8')

                    # Check if any search pattern is in the content
                    for pattern in search_patterns:
                        if pattern in content:
                            if notebook.path not in notebooks_found:
                                notebooks_found[notebook.path] = {
                                    'creates': False,
                                    'updates': False,
                                    'reads': False,
                                    'patterns': []
                                }

                            notebooks_found[notebook.path]['patterns'].append(pattern)

                            # Determine operation type
                            if re.search(rf'CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+.*{pattern}',
                                       content, re.IGNORECASE):
                                notebooks_found[notebook.path]['creates'] = True

                            if re.search(rf'INSERT\s+(?:INTO|OVERWRITE)\s+.*{pattern}',
                                       content, re.IGNORECASE):
                                notebooks_found[notebook.path]['updates'] = True

                            if re.search(rf'MERGE\s+INTO\s+.*{pattern}',
                                       content, re.IGNORECASE):
                                notebooks_found[notebook.path]['updates'] = True

                            if re.search(rf'(?:FROM|JOIN)\s+.*{pattern}',
                                       content, re.IGNORECASE):
                                notebooks_found[notebook.path]['reads'] = True

                            if re.search(rf'spark\.(?:read|table)\(["\'].*{pattern}',
                                       content):
                                notebooks_found[notebook.path]['reads'] = True

                            break

            except Exception as e:
                continue

    except Exception as e:
        print(f"  Could not search {search_path}: {e}")

if notebooks_found:
    print(f"\nFound {len(notebooks_found)} notebook(s) referencing dim_fde:\n")

    for notebook_path, info in notebooks_found.items():
        print(f"{'=' * 80}")
        print(f"Notebook: {notebook_path}")
        print(f"{'=' * 80}")
        print(f"  Operations:")
        print(f"    Creates table: {info['creates']}")
        print(f"    Updates table: {info['updates']}")
        print(f"    Reads table: {info['reads']}")
        print(f"  Patterns found: {', '.join(set(info['patterns']))}")
        print()
else:
    print("No notebooks found referencing dim_fde")

# Step 3: Check which workflows use these notebooks
print(f"{'=' * 80}")
print("WORKFLOWS USING THESE NOTEBOOKS")
print(f"{'=' * 80}\n")

if notebooks_found:
    jobs = list(w.jobs.list(expand_tasks=True))

    workflow_matches = []

    for job in jobs:
        if job.settings and job.settings.tasks:
            for task in job.settings.tasks:
                if task.notebook_task:
                    # Normalize paths for comparison
                    task_path = task.notebook_task.notebook_path

                    for notebook_path in notebooks_found.keys():
                        # Check if paths match (considering /Workspace prefix variations)
                        if (task_path in notebook_path or
                            notebook_path in task_path or
                            task_path.split('/')[-1] == notebook_path.split('/')[-1]):

                            workflow_matches.append({
                                'workflow_name': job.settings.name,
                                'workflow_id': job.job_id,
                                'task_name': task.task_key,
                                'notebook': task_path,
                                'schedule': job.settings.schedule.quartz_cron_expression if job.settings.schedule else None,
                                'trigger': 'Periodic' if job.settings.trigger and job.settings.trigger.periodic else None
                            })

    if workflow_matches:
        print(f"Found {len(workflow_matches)} workflow task(s) using these notebooks:\n")
        for match in workflow_matches:
            print(f"Workflow: {match['workflow_name']} (ID: {match['workflow_id']})")
            print(f"  Task: {match['task_name']}")
            print(f"  Notebook: {match['notebook']}")
            if match['schedule']:
                print(f"  Schedule: {match['schedule']}")
            if match['trigger']:
                print(f"  Trigger: {match['trigger']}")
            print()
    else:
        print("No workflows found using these notebooks")

# Step 4: Analyze one of the key notebooks in detail
print(f"{'=' * 80}")
print("DETAILED NOTEBOOK ANALYSIS")
print(f"{'=' * 80}\n")

# Find the notebook that CREATES the table
creator_notebooks = [path for path, info in notebooks_found.items()
                     if info['creates'] or info['updates']]

if creator_notebooks:
    print(f"Analyzing: {creator_notebooks[0]}\n")

    try:
        exported = w.workspace.export(creator_notebooks[0], format="SOURCE")
        content = exported.content.decode('utf-8') if exported.content else ""

        # Analyze the notebook structure
        analysis = {
            'total_lines': len(content.split('\n')),
            'code_lines': len([l for l in content.split('\n')
                             if l.strip() and not l.strip().startswith('#')]),
            'uses_delta': 'delta' in content.lower() or 'DeltaTable' in content,
            'uses_spark_sql': bool(re.search(r'spark\.sql\(', content)),
            'has_joins': bool(re.search(r'\bJOIN\b', content, re.IGNORECASE)),
            'has_aggregations': bool(re.search(r'\b(GROUP BY|SUM|COUNT|AVG|MAX|MIN)\b',
                                             content, re.IGNORECASE)),
            'is_streaming': 'readStream' in content or 'writeStream' in content,
            'has_merge': bool(re.search(r'\bMERGE\s+INTO\b', content, re.IGNORECASE)),
            'source_tables': [],
            'transformations': []
        }

        # Find source tables
        table_refs = re.findall(r'(?:FROM|JOIN)\s+([a-z_]+\.[a-z_]+\.[a-z_]+)',
                               content, re.IGNORECASE)
        analysis['source_tables'] = list(set(table_refs))[:10]

        # Find common transformation patterns
        if 'CASE WHEN' in content.upper():
            analysis['transformations'].append('Conditional logic (CASE WHEN)')
        if re.search(r'\bWINDOW\b', content, re.IGNORECASE):
            analysis['transformations'].append('Window functions')
        if re.search(r'\bPIVOT\b', content, re.IGNORECASE):
            analysis['transformations'].append('Pivot operations')
        if re.search(r'\bUNPIVOT\b', content, re.IGNORECASE):
            analysis['transformations'].append('Unpivot operations')

        print("Analysis Results:")
        print(f"  Total lines: {analysis['total_lines']}")
        print(f"  Code lines: {analysis['code_lines']}")
        print(f"  Uses Delta Lake: {analysis['uses_delta']}")
        print(f"  Uses Spark SQL: {analysis['uses_spark_sql']}")
        print(f"  Has JOINs: {analysis['has_joins']}")
        print(f"  Has aggregations: {analysis['has_aggregations']}")
        print(f"  Is streaming: {analysis['is_streaming']}")
        print(f"  Uses MERGE: {analysis['has_merge']}")

        if analysis['source_tables']:
            print(f"\n  Source tables ({len(analysis['source_tables'])}):")
            for table in analysis['source_tables'][:5]:
                print(f"    - {table}")
            if len(analysis['source_tables']) > 5:
                print(f"    ... and {len(analysis['source_tables']) - 5} more")

        if analysis['transformations']:
            print(f"\n  Transformations:")
            for transform in analysis['transformations']:
                print(f"    - {transform}")

        # Show a snippet of the code
        print(f"\n  Code snippet (first 30 lines):")
        print("  " + "-" * 76)
        lines = content.split('\n')[:30]
        for i, line in enumerate(lines, 1):
            print(f"  {i:3d} | {line[:70]}")
        print("  " + "-" * 76)

    except Exception as e:
        print(f"Could not analyze notebook: {e}")

# Step 5: DLT Conversion Assessment
print(f"\n{'=' * 80}")
print("DLT CONVERSION ASSESSMENT")
print(f"{'=' * 80}\n")

print("✅ GOOD indicators for DLT conversion:")
checks = {
    'Delta Lake usage': any(info.get('uses_delta', False) for info in [analysis] if 'analysis' in locals()),
    'Clear data lineage': len(notebooks_found) > 0 and any(info['creates'] or info['updates'] for info in notebooks_found.values()),
    'Regular schedule': len(workflow_matches) > 0,
    'Table dependencies': len(analysis.get('source_tables', [])) > 0 if 'analysis' in locals() else False,
    'Data transformations': analysis.get('has_joins', False) or analysis.get('has_aggregations', False) if 'analysis' in locals() else False
}

for check, result in checks.items():
    symbol = "✓" if result else "✗"
    print(f"  {symbol} {check}: {result}")

print(f"\n{'=' * 80}")
print("RECOMMENDATION")
print(f"{'=' * 80}\n")

if sum(checks.values()) >= 3:
    print("✅ STRONG CANDIDATE for DLT conversion!")
    print("\nReasons:")
    print("  - Table has clear ownership and update patterns")
    print("  - Regular scheduled updates via workflows")
    print("  - Uses Delta Lake for storage")
    print("  - Has defined data lineage and dependencies")
    print("\nNext steps:")
    print("  1. Review the source notebook in detail")
    print("  2. Identify all upstream dependencies")
    print("  3. Create DLT pipeline with @dlt.table decorators")
    print("  4. Add data quality expectations")
    print("  5. Test in development environment")
else:
    print("⚠️  MAY NOT BE IDEAL for DLT conversion")
    print("\nConsider keeping as regular notebook if:")
    print("  - Complex orchestration logic required")
    print("  - External API calls or file operations")
    print("  - Administrative tasks mixed with data processing")

print("\n" + "=" * 80)
