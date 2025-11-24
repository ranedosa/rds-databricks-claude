#!/usr/bin/env python3
"""Check access to Databricks workflows (jobs) and DLT pipelines."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

print("=" * 80)
print("DATABRICKS WORKFLOWS (JOBS)")
print("=" * 80)

try:
    # List all jobs/workflows
    jobs = list(w.jobs.list(expand_tasks=True))

    if jobs:
        print(f"\nFound {len(jobs)} workflow(s):\n")

        for job in jobs:
            print(f"{'=' * 80}")
            print(f"Workflow Name: {job.settings.name if job.settings else 'Unnamed'}")
            print(f"Job ID: {job.job_id}")

            if job.creator_user_name:
                print(f"Creator: {job.creator_user_name}")

            if job.settings:
                # Show tasks
                if job.settings.tasks:
                    print(f"\nTasks ({len(job.settings.tasks)}):")
                    for task in job.settings.tasks:
                        print(f"  • {task.task_key}")
                        if task.notebook_task:
                            print(f"    Type: Notebook - {task.notebook_task.notebook_path}")
                        elif task.spark_python_task:
                            print(f"    Type: Python - {task.spark_python_task.python_file}")
                        elif task.spark_jar_task:
                            print(f"    Type: JAR")
                        elif task.pipeline_task:
                            print(f"    Type: DLT Pipeline - {task.pipeline_task.pipeline_id}")
                        elif task.sql_task:
                            print(f"    Type: SQL")

                # Show schedule
                if job.settings.schedule:
                    print(f"\nSchedule: {job.settings.schedule.quartz_cron_expression}")
                    print(f"  Timezone: {job.settings.schedule.timezone_id}")
                    print(f"  Paused: {job.settings.schedule.pause_status}")

                # Show triggers
                if job.settings.trigger:
                    if job.settings.trigger.periodic:
                        print(f"\nTrigger: Periodic (every {job.settings.trigger.periodic.interval} {job.settings.trigger.periodic.unit})")
                    elif job.settings.trigger.file_arrival:
                        print(f"\nTrigger: File Arrival")

            print()
    else:
        print("No workflows found")

except Exception as e:
    print(f"Error accessing workflows: {e}")

print("\n" + "=" * 80)
print("DELTA LIVE TABLES (DLT) PIPELINES")
print("=" * 80)

try:
    # List all DLT pipelines
    pipelines = list(w.pipelines.list_pipelines())

    if pipelines:
        print(f"\nFound {len(pipelines)} DLT pipeline(s):\n")

        for pipeline in pipelines:
            print(f"{'=' * 80}")
            print(f"Pipeline Name: {pipeline.name}")
            print(f"Pipeline ID: {pipeline.pipeline_id}")

            if pipeline.creator_user_name:
                print(f"Creator: {pipeline.creator_user_name}")

            if pipeline.state:
                print(f"State: {pipeline.state}")

            if pipeline.spec:
                # Show configuration
                if pipeline.spec.configuration:
                    print(f"\nConfiguration:")
                    for key, value in list(pipeline.spec.configuration.items())[:5]:
                        print(f"  {key}: {value}")

                # Show storage location
                if pipeline.spec.storage:
                    print(f"\nStorage: {pipeline.spec.storage}")

                # Show target schema
                if pipeline.spec.target:
                    print(f"Target Schema: {pipeline.spec.target}")

                # Show libraries/notebooks
                if pipeline.spec.libraries:
                    print(f"\nLibraries ({len(pipeline.spec.libraries)}):")
                    for lib in pipeline.spec.libraries[:5]:
                        if lib.notebook:
                            print(f"  • Notebook: {lib.notebook.path}")
                        elif lib.file:
                            print(f"  • File: {lib.file.path}")

                # Show clusters
                if pipeline.spec.clusters:
                    print(f"\nClusters ({len(pipeline.spec.clusters)}):")
                    for cluster in pipeline.spec.clusters:
                        if cluster.label:
                            print(f"  • {cluster.label}")

            print()
    else:
        print("No DLT pipelines found")

except Exception as e:
    print(f"Error accessing DLT pipelines: {e}")

print("\n" + "=" * 80)
print("RECENT JOB RUNS")
print("=" * 80)

try:
    # Get recent job runs
    runs = list(w.jobs.list_runs(limit=10, expand_tasks=False))

    if runs:
        print(f"\nFound {len(runs)} recent run(s):\n")

        for run in runs:
            print(f"Run ID: {run.run_id}")
            if run.run_name:
                print(f"  Name: {run.run_name}")
            if run.state:
                print(f"  State: {run.state.life_cycle_state}")
                if run.state.result_state:
                    print(f"  Result: {run.state.result_state}")
            if run.start_time:
                from datetime import datetime
                start = datetime.fromtimestamp(run.start_time / 1000)
                print(f"  Started: {start}")
            print()
    else:
        print("No recent runs found")

except Exception as e:
    print(f"Error accessing job runs: {e}")

print("=" * 80)
print("ACCESS CHECK COMPLETE")
print("=" * 80)
