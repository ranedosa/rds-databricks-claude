#!/usr/bin/env python3
"""
Analyze All Databricks Workflows for DLT Conversion
===================================================

This script analyzes all workflows in your Databricks workspace to:
1. Identify the most costly workflows
2. Determine which are good candidates for DLT conversion
3. Provide cost-benefit analysis
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

# Load credentials
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Configuration
LOOKBACK_DAYS = 30
COMPUTE_DBU_PRICE = 0.15
DLT_CORE_PREMIUM = 0.20

print("=" * 100)
print("ANALYZING ALL WORKFLOWS FOR DLT CONVERSION OPPORTUNITIES")
print("=" * 100)
print(f"\nAnalyzing workflows from the last {LOOKBACK_DAYS} days...")

# Step 1: Get all jobs/workflows
print(f"\n{'=' * 100}")
print("STEP 1: Fetching All Workflows")
print(f"{'=' * 100}\n")

try:
    all_jobs = list(w.jobs.list(expand_tasks=False))
    print(f"Found {len(all_jobs)} total workflow(s)")
except Exception as e:
    print(f"Error fetching workflows: {e}")
    exit(1)

# Step 2: Analyze each workflow
print(f"\n{'=' * 100}")
print("STEP 2: Analyzing Workflow Performance and Costs")
print(f"{'=' * 100}\n")

workflow_data = []
cutoff_time = int((datetime.now() - timedelta(days=LOOKBACK_DAYS)).timestamp() * 1000)

for job in all_jobs:
    try:
        job_name = job.settings.name if job.settings else "Unnamed"
        job_id = job.job_id

        print(f"Analyzing: {job_name} (ID: {job_id})...")

        # Get job details
        job_details = w.jobs.get(job_id)

        # Get schedule info
        schedule = None
        if job_details.settings and job_details.settings.schedule:
            schedule = job_details.settings.schedule.quartz_cron_expression

        # Get task count
        task_count = len(job_details.settings.tasks) if job_details.settings and job_details.settings.tasks else 0

        # Fetch recent runs
        recent_runs = []
        try:
            for i in range(4):  # Fetch up to 4 batches (100 runs)
                batch = list(w.jobs.list_runs(job_id=job_id, limit=25, expand_tasks=False))
                recent_runs.extend(batch)
                if len(batch) < 25:
                    break
        except Exception as e:
            print(f"  Warning: Could not fetch all runs: {e}")

        # Filter to lookback period
        recent_runs = [r for r in recent_runs if r.start_time and r.start_time >= cutoff_time]

        if not recent_runs:
            print(f"  No runs in last {LOOKBACK_DAYS} days - skipping")
            continue

        # Calculate runtime statistics
        durations = []
        successful_runs = 0
        failed_runs = 0

        for run in recent_runs:
            if run.state and run.state.result_state:
                if run.state.result_state.value == "SUCCESS":
                    successful_runs += 1
                else:
                    failed_runs += 1

            if run.start_time and run.end_time:
                duration_min = (run.end_time - run.start_time) / (1000 * 60)
                durations.append(duration_min)

        if not durations:
            print(f"  No completed runs with timing data - skipping")
            continue

        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)

        # Project monthly usage
        runs_per_month = len(durations) * (30 / LOOKBACK_DAYS)
        total_compute_minutes_per_month = avg_duration * runs_per_month

        # Estimate cost (using medium cluster assumption)
        dbu_per_min = 0.10  # Medium cluster
        monthly_dbus = total_compute_minutes_per_month * dbu_per_min
        monthly_cost = monthly_dbus * COMPUTE_DBU_PRICE

        # Analyze tasks for DLT suitability
        dlt_score = 0
        dlt_reasons = []

        if task_count > 0:
            # More tasks = more complex DAG = better for DLT
            if task_count >= 5:
                dlt_score += 2
                dlt_reasons.append(f"Multiple tasks ({task_count}) with dependencies")
            elif task_count >= 3:
                dlt_score += 1
                dlt_reasons.append(f"Several tasks ({task_count}) forming a pipeline")

        # Check task types
        if job_details.settings and job_details.settings.tasks:
            notebook_tasks = 0
            sql_tasks = 0
            pipeline_tasks = 0
            other_tasks = 0

            for task in job_details.settings.tasks:
                if task.notebook_task:
                    notebook_tasks += 1
                elif task.sql_task:
                    sql_tasks += 1
                elif task.pipeline_task:
                    pipeline_tasks += 1
                else:
                    other_tasks += 1

            # Notebook and SQL tasks are good candidates
            if notebook_tasks > 0 or sql_tasks > 0:
                dlt_score += 1
                dlt_reasons.append("Contains data processing tasks")

            # Already has DLT tasks?
            if pipeline_tasks > 0:
                dlt_score = 0
                dlt_reasons = ["Already uses DLT"]

        # Scheduled jobs benefit more from DLT
        if schedule:
            dlt_score += 1
            dlt_reasons.append("Scheduled regularly")

        # High frequency = more benefit from DLT optimization
        if runs_per_month > 100:
            dlt_score += 2
            dlt_reasons.append(f"High frequency ({runs_per_month:.0f} runs/month)")
        elif runs_per_month > 50:
            dlt_score += 1
            dlt_reasons.append(f"Moderate frequency ({runs_per_month:.0f} runs/month)")

        # Long running jobs = more cost = more to optimize
        if avg_duration > 30:
            dlt_score += 1
            dlt_reasons.append(f"Long runtime ({avg_duration:.1f} min avg)")

        # High cost = worth optimizing
        if monthly_cost > 100:
            dlt_score += 2
            dlt_reasons.append(f"High monthly cost (~${monthly_cost:.0f})")
        elif monthly_cost > 50:
            dlt_score += 1
            dlt_reasons.append(f"Moderate monthly cost (~${monthly_cost:.0f})")

        workflow_data.append({
            'name': job_name,
            'job_id': job_id,
            'task_count': task_count,
            'runs_last_30d': len(durations),
            'avg_duration_min': avg_duration,
            'median_duration_min': median_duration,
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'runs_per_month': runs_per_month,
            'compute_hours_per_month': total_compute_minutes_per_month / 60,
            'estimated_monthly_cost': monthly_cost,
            'dlt_score': dlt_score,
            'dlt_reasons': dlt_reasons,
            'schedule': schedule
        })

        print(f"  ✓ {len(durations)} runs analyzed - Avg: {avg_duration:.1f}min - Est. cost: ${monthly_cost:.2f}/month")

    except Exception as e:
        print(f"  Error analyzing workflow: {e}")
        continue

# Step 3: Sort and display results
print(f"\n{'=' * 100}")
print("STEP 3: WORKFLOW COST RANKING")
print(f"{'=' * 100}\n")

if not workflow_data:
    print("No workflows with sufficient data found")
    exit(1)

# Sort by cost
workflow_data.sort(key=lambda x: x['estimated_monthly_cost'], reverse=True)

print(f"{'Rank':<5} {'Workflow Name':<40} {'Cost/Month':<15} {'Hours/Month':<15} {'Runs/Month':<12}")
print("-" * 100)

for i, wf in enumerate(workflow_data[:20], 1):
    print(f"{i:<5} {wf['name'][:38]:<40} ${wf['estimated_monthly_cost']:>8.2f}      "
          f"{wf['compute_hours_per_month']:>8.1f} hrs    {wf['runs_per_month']:>8.0f}")

total_cost = sum(wf['estimated_monthly_cost'] for wf in workflow_data)
print("-" * 100)
print(f"{'TOTAL':<45} ${total_cost:>8.2f}")

# Step 4: DLT Conversion Recommendations
print(f"\n{'=' * 100}")
print("STEP 4: DLT CONVERSION RECOMMENDATIONS")
print(f"{'=' * 100}\n")

print("Scoring criteria:")
print("  - Multiple tasks with dependencies: +1-2 points")
print("  - Scheduled regularly: +1 point")
print("  - High frequency (>100 runs/month): +2 points")
print("  - Long runtime (>30 min): +1 point")
print("  - High cost (>$100/month): +2 points")
print("  - Contains data processing tasks: +1 point")
print()

# Sort by DLT score
dlt_candidates = [wf for wf in workflow_data if wf['dlt_score'] > 0]
dlt_candidates.sort(key=lambda x: (x['dlt_score'], x['estimated_monthly_cost']), reverse=True)

print(f"{'Score':<7} {'Workflow Name':<35} {'Cost/Mo':<12} {'Runs/Mo':<10} {'Reasons'}")
print("-" * 100)

for wf in dlt_candidates[:15]:
    reasons_str = "; ".join(wf['dlt_reasons'][:2])
    if len(wf['dlt_reasons']) > 2:
        reasons_str += f" +{len(wf['dlt_reasons'])-2} more"

    print(f"{wf['dlt_score']:<7} {wf['name'][:33]:<35} ${wf['estimated_monthly_cost']:>6.2f}     "
          f"{wf['runs_per_month']:>6.0f}     {reasons_str[:40]}")

# Step 5: Detailed analysis of top candidates
print(f"\n{'=' * 100}")
print("STEP 5: TOP 5 DLT CONVERSION CANDIDATES - DETAILED ANALYSIS")
print(f"{'=' * 100}\n")

for i, wf in enumerate(dlt_candidates[:5], 1):
    print(f"\n{i}. {wf['name']}")
    print("-" * 80)
    print(f"   Job ID: {wf['job_id']}")
    print(f"   Schedule: {wf['schedule'] if wf['schedule'] else 'Manual/Trigger-based'}")
    print(f"   Tasks: {wf['task_count']}")
    print(f"   Average Runtime: {wf['avg_duration_min']:.1f} minutes")
    print(f"   Runs per month: {wf['runs_per_month']:.0f}")
    print(f"   Compute hours/month: {wf['compute_hours_per_month']:.1f}")
    print(f"   Success rate: {wf['successful_runs']}/{wf['successful_runs']+wf['failed_runs']} ({100*wf['successful_runs']/(wf['successful_runs']+wf['failed_runs']):.0f}%)")

    print(f"\n   Current Cost (estimated): ${wf['estimated_monthly_cost']:.2f}/month")

    # Estimate DLT costs
    dlt_core_cost = wf['estimated_monthly_cost'] * (COMPUTE_DBU_PRICE + DLT_CORE_PREMIUM) / COMPUTE_DBU_PRICE
    dlt_optimized_cost = dlt_core_cost * 0.70  # Assume 30% reduction

    print(f"   DLT Core Cost (no optimization): ${dlt_core_cost:.2f}/month (+${dlt_core_cost - wf['estimated_monthly_cost']:.2f})")
    print(f"   DLT Core Cost (30% optimized): ${dlt_optimized_cost:.2f}/month ({'+' if dlt_optimized_cost > wf['estimated_monthly_cost'] else ''}{dlt_optimized_cost - wf['estimated_monthly_cost']:+.2f})")

    print(f"\n   DLT Score: {wf['dlt_score']}/10")
    print(f"   Reasons for DLT:")
    for reason in wf['dlt_reasons']:
        print(f"     ✓ {reason}")

    print(f"\n   Recommendation: ", end="")
    if wf['dlt_score'] >= 6:
        print("⭐ STRONG CANDIDATE - High priority for DLT conversion")
    elif wf['dlt_score'] >= 4:
        print("✓ GOOD CANDIDATE - Consider for DLT conversion")
    else:
        print("~ MODERATE CANDIDATE - Evaluate task types before converting")

# Summary
print(f"\n{'=' * 100}")
print("SUMMARY")
print(f"{'=' * 100}\n")

high_priority = len([wf for wf in dlt_candidates if wf['dlt_score'] >= 6])
good_candidates = len([wf for wf in dlt_candidates if 4 <= wf['dlt_score'] < 6])
moderate = len([wf for wf in dlt_candidates if wf['dlt_score'] < 4])

print(f"Total workflows analyzed: {len(workflow_data)}")
print(f"Total estimated monthly cost: ${total_cost:.2f}")
print(f"\nDLT Conversion Candidates:")
print(f"  ⭐ High priority (score ≥6): {high_priority} workflows")
print(f"  ✓ Good candidates (score 4-5): {good_candidates} workflows")
print(f"  ~ Moderate (score <4): {moderate} workflows")

if high_priority > 0:
    top_candidates = [wf for wf in dlt_candidates if wf['dlt_score'] >= 6]
    potential_cost = sum(wf['estimated_monthly_cost'] for wf in top_candidates)
    print(f"\nTop {high_priority} candidates represent ${potential_cost:.2f}/month in compute costs")
    print(f"Converting these to DLT with 30% optimization could result in:")
    print(f"  Current cost: ${potential_cost:.2f}/month")
    print(f"  DLT cost (optimized): ${potential_cost * 0.70 * (COMPUTE_DBU_PRICE + DLT_CORE_PREMIUM) / COMPUTE_DBU_PRICE:.2f}/month")

print(f"\n{'=' * 100}")
print("NEXT STEPS")
print(f"{'=' * 100}\n")

print("""
1. Review the top 5 candidates in detail
2. For each candidate, examine the actual tasks:
   - Use: python analyze_rds_workflow.py (modify for each job_id)
   - Identify data processing vs operational tasks

3. Start with the highest-scoring, highest-cost workflow
   - Create a pilot DLT pipeline for one workflow
   - Run in parallel for 1-2 weeks
   - Compare costs, performance, and data quality

4. Consider a hybrid approach:
   - Convert core data processing tasks to DLT
   - Keep operational tasks (emails, cleanup) in workflows
   - Use workflows to orchestrate DLT pipelines + other tasks

5. Document lessons learned and create a conversion playbook
""")

print("=" * 100)
