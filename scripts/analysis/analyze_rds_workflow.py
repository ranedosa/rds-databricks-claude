#!/usr/bin/env python3
"""Analyze the 00_RDS workflow to determine if DLT conversion makes sense."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# Load credentials
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

print("=" * 80)
print("ANALYZING 00_RDS WORKFLOW FOR DLT CONVERSION")
print("=" * 80)

# Get the 00_RDS job details
job_id = 314473856953682

try:
    job = w.jobs.get(job_id)

    print(f"\nWorkflow Name: {job.settings.name}")
    print(f"Job ID: {job.job_id}")
    print(f"Creator: {job.creator_user_name}")

    if job.settings.schedule:
        print(f"\nSchedule: {job.settings.schedule.quartz_cron_expression}")
        print(f"Timezone: {job.settings.schedule.timezone_id}")

    print(f"\n{'=' * 80}")
    print(f"TASKS ({len(job.settings.tasks)} total)")
    print(f"{'=' * 80}\n")

    for idx, task in enumerate(job.settings.tasks, 1):
        print(f"{idx}. Task: {task.task_key}")

        if task.notebook_task:
            notebook_path = task.notebook_task.notebook_path
            print(f"   Type: Notebook")
            print(f"   Path: {notebook_path}")

            # Try to read the notebook to understand what it does
            try:
                # Get notebook content
                notebook = w.workspace.export(notebook_path, format="SOURCE")
                content = notebook.content.decode('utf-8') if notebook.content else ""

                # Analyze patterns
                patterns = {
                    "reads_from": [],
                    "writes_to": [],
                    "uses_spark_sql": "CREATE TABLE" in content or "INSERT INTO" in content or "MERGE INTO" in content,
                    "uses_delta": "delta" in content.lower() or "DeltaTable" in content,
                    "has_transformations": "transform" in content.lower() or "join" in content.lower() or "groupBy" in content or "filter" in content.lower(),
                    "has_data_quality": "@dlt.expect" in content or "expectation" in content.lower(),
                    "is_streaming": "readStream" in content or "writeStream" in content or "trigger" in content.lower(),
                    "has_dependencies": len([t for t in job.settings.tasks if task.task_key in str(t.depends_on)]) > 0,
                    "lines_of_code": len([l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')])
                }

                # Look for table reads/writes
                import re
                table_reads = re.findall(r'spark\.(?:read|table)\(["\']([^"\']+)["\']', content)
                table_writes = re.findall(r'\.(?:saveAsTable|insertInto|write\..*?\.save)\(["\']([^"\']+)["\']', content)

                if table_reads:
                    patterns["reads_from"] = list(set(table_reads))[:5]
                if table_writes:
                    patterns["writes_to"] = list(set(table_writes))[:5]

                # Print analysis
                print(f"   Analysis:")
                print(f"     - Lines of code: {patterns['lines_of_code']}")
                print(f"     - Uses Spark SQL: {patterns['uses_spark_sql']}")
                print(f"     - Uses Delta: {patterns['uses_delta']}")
                print(f"     - Has transformations: {patterns['has_transformations']}")
                print(f"     - Is streaming: {patterns['is_streaming']}")
                print(f"     - Has data quality checks: {patterns['has_data_quality']}")

                if patterns["reads_from"]:
                    print(f"     - Reads from: {', '.join(patterns['reads_from'][:3])}")
                if patterns["writes_to"]:
                    print(f"     - Writes to: {', '.join(patterns['writes_to'][:3])}")

            except Exception as e:
                print(f"   (Could not analyze notebook: {e})")

        # Check task dependencies
        if task.depends_on:
            deps = [d.task_key for d in task.depends_on]
            print(f"   Depends on: {', '.join(deps)}")

        print()

    # Analyze task dependencies to understand the DAG
    print(f"{'=' * 80}")
    print("DEPENDENCY ANALYSIS")
    print(f"{'=' * 80}\n")

    # Check if tasks run in parallel or sequence
    tasks_with_deps = [t for t in job.settings.tasks if t.depends_on]
    tasks_without_deps = [t for t in job.settings.tasks if not t.depends_on]

    print(f"Tasks that can run in parallel (no dependencies): {len(tasks_without_deps)}")
    for t in tasks_without_deps:
        print(f"  - {t.task_key}")

    print(f"\nTasks with dependencies: {len(tasks_with_deps)}")
    for t in tasks_with_deps:
        deps = [d.task_key for d in t.depends_on]
        print(f"  - {t.task_key} (depends on: {', '.join(deps)})")

    print(f"\n{'=' * 80}")
    print("DLT CONVERSION ASSESSMENT")
    print(f"{'=' * 80}\n")

    print("✓ Good candidates for DLT:")
    print("  - Tasks with clear data lineage (reads -> transforms -> writes)")
    print("  - Tasks that process streaming data")
    print("  - Tasks that need data quality expectations")
    print("  - Tasks that build on each other (dependencies)")
    print("  - Tasks that write to Delta tables")

    print("\n✗ Poor candidates for DLT:")
    print("  - Tasks that send emails/notifications")
    print("  - Tasks that call external APIs")
    print("  - Tasks that perform administrative operations")
    print("  - Tasks with complex orchestration logic")
    print("  - Tasks that don't produce tables/views")

    # Get recent runs to understand runtime
    print(f"\n{'=' * 80}")
    print("RECENT RUN PERFORMANCE")
    print(f"{'=' * 80}\n")

    recent_runs = list(w.jobs.list_runs(job_id=job_id, limit=5, expand_tasks=False))

    if recent_runs:
        print(f"Last 5 runs:\n")
        for run in recent_runs:
            if run.start_time and run.end_time:
                duration_min = (run.end_time - run.start_time) / (1000 * 60)
                state = run.state.result_state if run.state and run.state.result_state else "UNKNOWN"
                from datetime import datetime
                start = datetime.fromtimestamp(run.start_time / 1000)
                print(f"  Run {run.run_id}: {state} - {duration_min:.1f} minutes - {start.strftime('%Y-%m-%d %H:%M')}")

except Exception as e:
    print(f"Error analyzing workflow: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'=' * 80}")
print("RECOMMENDATION")
print(f"{'=' * 80}\n")

print("""
Based on the analysis above, consider converting to DLT if:

1. **Data Lineage is Clear**: Most tasks read from source tables, transform data,
   and write to destination tables in a clear pipeline flow.

2. **Delta Lake is Primary**: Tasks primarily work with Delta tables and would
   benefit from automatic schema evolution and versioning.

3. **Data Quality Matters**: You need built-in data quality expectations and
   monitoring (DLT provides @dlt.expect decorators).

4. **Incremental Processing**: Tasks process incremental data and would benefit
   from DLT's automatic incremental processing.

5. **Streaming Workloads**: Tasks process streaming data (DLT handles streaming
   and batch in the same pipeline).

6. **Dependency Management**: Tasks have complex dependencies that form a DAG
   (DLT handles this automatically based on table references).

7. **Observability**: You need better lineage tracking and data quality metrics
   (DLT provides built-in observability).

Keep as workflow if:

1. **Mixed Operations**: Tasks include non-data operations (emails, API calls,
   file transfers, administrative tasks).

2. **Complex Orchestration**: Tasks have conditional logic or dynamic branching
   that doesn't fit DLT's declarative model.

3. **External Dependencies**: Tasks depend on external systems or services that
   need to be checked before running.

4. **Flexibility Needed**: You need fine-grained control over error handling,
   retries, and execution order.

5. **Cost Concerns**: DLT has additional compute costs compared to standard jobs.
""")

print("=" * 80)
