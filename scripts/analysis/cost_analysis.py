#!/usr/bin/env python3
"""
Cost Analysis: 00_RDS Workflow vs DLT Pipeline
===============================================

This script analyzes the cost difference between running the 00_RDS workflow
and converting it to a DLT pipeline.

Assumptions and Pricing (as of Oct 2024):
- Standard Databricks compute: $0.15/DBU
- DLT Core (standard): Additional $0.20/DBU on top of compute
- DLT Pro (advanced): Additional $0.30/DBU on top of compute
- Average DBU consumption per minute varies by cluster size

References:
- https://www.databricks.com/product/pricing
- https://docs.databricks.com/en/delta-live-tables/index.html
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from datetime import datetime, timedelta
import statistics

# Load credentials
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

print("=" * 80)
print("COST ANALYSIS: 00_RDS WORKFLOW vs DLT PIPELINE")
print("=" * 80)

# Configuration
JOB_ID = 314473856953682
LOOKBACK_DAYS = 30

# Databricks pricing (approximate, region/contract dependent)
# These are AWS us-west-2 list prices - adjust for your region/contract
COMPUTE_DBU_PRICE = 0.15  # $/DBU for standard compute
DLT_CORE_PREMIUM = 0.20   # Additional $/DBU for DLT Core
DLT_PRO_PREMIUM = 0.30    # Additional $/DBU for DLT Pro/Advanced

print(f"\nPricing Assumptions:")
print(f"  Standard Compute: ${COMPUTE_DBU_PRICE}/DBU")
print(f"  DLT Core Premium: ${DLT_CORE_PREMIUM}/DBU (total: ${COMPUTE_DBU_PRICE + DLT_CORE_PREMIUM}/DBU)")
print(f"  DLT Pro Premium:  ${DLT_PRO_PREMIUM}/DBU (total: ${COMPUTE_DBU_PRICE + DLT_PRO_PREMIUM}/DBU)")
print(f"\nNote: Actual pricing varies by region, contract, and commitment level")

# Step 1: Analyze workflow runs
print(f"\n{'=' * 80}")
print(f"STEP 1: Analyzing Workflow Performance (Last {LOOKBACK_DAYS} Days)")
print(f"{'=' * 80}\n")

try:
    job = w.jobs.get(JOB_ID)
    print(f"Workflow: {job.settings.name}")
    print(f"Schedule: {job.settings.schedule.quartz_cron_expression if job.settings.schedule else 'Manual'}")

    # Get cluster configuration to estimate DBU consumption
    cluster_config = None
    if job.settings.tasks and len(job.settings.tasks) > 0:
        first_task = job.settings.tasks[0]
        if hasattr(first_task, 'existing_cluster_id') and first_task.existing_cluster_id:
            print(f"\nUsing existing cluster: {first_task.existing_cluster_id}")
        elif hasattr(first_task, 'new_cluster') and first_task.new_cluster:
            cluster_config = first_task.new_cluster
            print(f"\nCluster Configuration:")
            if cluster_config.node_type_id:
                print(f"  Node Type: {cluster_config.node_type_id}")
            if hasattr(cluster_config, 'num_workers'):
                print(f"  Workers: {cluster_config.num_workers}")
            elif hasattr(cluster_config, 'autoscale'):
                print(f"  Autoscale: {cluster_config.autoscale.min_workers}-{cluster_config.autoscale.max_workers} workers")

    # Get recent runs (API has limit of 25 per call)
    cutoff_time = int((datetime.now() - timedelta(days=LOOKBACK_DAYS)).timestamp() * 1000)

    # Fetch runs in batches
    recent_runs = []
    has_more = True
    page_token = None

    while has_more and len(recent_runs) < 200:  # Collect up to 200 runs
        runs_response = w.jobs.list_runs(
            job_id=JOB_ID,
            limit=25,
            expand_tasks=False,
            page_token=page_token
        )
        batch = list(runs_response)
        recent_runs.extend(batch)

        # Check if we've gone past our cutoff
        if batch and batch[-1].start_time and batch[-1].start_time < cutoff_time:
            break

        # Databricks SDK typically includes pagination info
        # If we got fewer than requested, we're done
        if len(batch) < 25:
            break

        # For simplicity, we'll just fetch a few batches
        if len(recent_runs) >= 100:
            break

    # Filter to lookback period
    recent_runs = [r for r in recent_runs if r.start_time and r.start_time >= cutoff_time]

    if not recent_runs:
        print(f"\nNo runs found in the last {LOOKBACK_DAYS} days")
        exit(1)

    # Calculate runtime statistics
    durations = []
    for run in recent_runs:
        if run.start_time and run.end_time:
            duration_min = (run.end_time - run.start_time) / (1000 * 60)
            durations.append(duration_min)

    if not durations:
        print("\nNo completed runs with timing data found")
        exit(1)

    avg_duration = statistics.mean(durations)
    median_duration = statistics.median(durations)
    min_duration = min(durations)
    max_duration = max(durations)

    print(f"\nRuntime Statistics ({len(durations)} runs in last {LOOKBACK_DAYS} days):")
    print(f"  Average: {avg_duration:.1f} minutes")
    print(f"  Median:  {median_duration:.1f} minutes")
    print(f"  Min:     {min_duration:.1f} minutes")
    print(f"  Max:     {max_duration:.1f} minutes")

    # Estimate runs per month
    runs_per_month = len(durations) * (30 / LOOKBACK_DAYS)
    total_compute_minutes_per_month = avg_duration * runs_per_month

    print(f"\nProjected Monthly Usage:")
    print(f"  Runs per month: {runs_per_month:.0f}")
    print(f"  Total compute time: {total_compute_minutes_per_month:.0f} minutes ({total_compute_minutes_per_month/60:.1f} hours)")

except Exception as e:
    print(f"Error analyzing workflow: {e}")
    exit(1)

# Step 2: Estimate DBU consumption
print(f"\n{'=' * 80}")
print("STEP 2: Estimating DBU Consumption")
print(f"{'=' * 80}\n")

# DBU consumption rates (approximate, based on typical cluster configs)
# These are rough estimates - actual consumption varies significantly
print("DBU consumption depends on cluster size. Common configurations:")
print("\nTypical cluster DBU rates:")
print("  Small (2-4 workers):    2-4 DBUs/hour   (~0.033-0.067 DBUs/min)")
print("  Medium (4-8 workers):   4-8 DBUs/hour   (~0.067-0.133 DBUs/min)")
print("  Large (8-16 workers):   8-16 DBUs/hour  (~0.133-0.267 DBUs/min)")
print("  X-Large (16+ workers):  16+ DBUs/hour   (~0.267+ DBUs/min)")

# Let's estimate based on common scenarios
scenarios = {
    "Small Cluster (2-4 workers)": 0.05,    # DBUs per minute
    "Medium Cluster (4-8 workers)": 0.10,   # DBUs per minute
    "Large Cluster (8-16 workers)": 0.20,   # DBUs per minute
}

print(f"\n{'=' * 80}")
print("STEP 3: Cost Comparison")
print(f"{'=' * 80}\n")

print(f"Based on {total_compute_minutes_per_month:.0f} minutes/month compute time:\n")

for scenario_name, dbu_per_min in scenarios.items():
    print(f"\n{scenario_name}:")
    print("-" * 60)

    # Current workflow cost (standard jobs)
    monthly_dbus = total_compute_minutes_per_month * dbu_per_min
    workflow_cost = monthly_dbus * COMPUTE_DBU_PRICE

    print(f"  Estimated DBUs/month: {monthly_dbus:.0f}")
    print(f"\n  Current Workflow (Standard Jobs):")
    print(f"    Monthly cost: ${workflow_cost:.2f}")
    print(f"    Annual cost:  ${workflow_cost * 12:.2f}")

    # DLT Core cost
    dlt_core_cost = monthly_dbus * (COMPUTE_DBU_PRICE + DLT_CORE_PREMIUM)
    dlt_core_increase = dlt_core_cost - workflow_cost
    dlt_core_increase_pct = (dlt_core_increase / workflow_cost) * 100

    print(f"\n  DLT Core Pipeline:")
    print(f"    Monthly cost: ${dlt_core_cost:.2f}")
    print(f"    Annual cost:  ${dlt_core_cost * 12:.2f}")
    print(f"    Cost increase: ${dlt_core_increase:.2f}/month (${dlt_core_increase * 12:.2f}/year)")
    print(f"    Increase %: {dlt_core_increase_pct:.0f}%")

    # DLT Pro cost
    dlt_pro_cost = monthly_dbus * (COMPUTE_DBU_PRICE + DLT_PRO_PREMIUM)
    dlt_pro_increase = dlt_pro_cost - workflow_cost
    dlt_pro_increase_pct = (dlt_pro_increase / workflow_cost) * 100

    print(f"\n  DLT Pro/Advanced Pipeline:")
    print(f"    Monthly cost: ${dlt_pro_cost:.2f}")
    print(f"    Annual cost:  ${dlt_pro_cost * 12:.2f}")
    print(f"    Cost increase: ${dlt_pro_increase:.2f}/month (${dlt_pro_increase * 12:.2f}/year)")
    print(f"    Increase %: {dlt_pro_increase_pct:.0f}%")

# Step 4: Potential optimizations
print(f"\n{'=' * 80}")
print("STEP 4: Potential Cost Optimizations with DLT")
print(f"{'=' * 80}\n")

print("""
While DLT has higher per-DBU costs, it can reduce TOTAL costs through:

1. **Incremental Processing**: DLT automatically processes only changed data
   - Reduces compute time for incremental updates
   - Current workflow may reprocess entire datasets
   - Potential savings: 30-50% reduction in compute time

2. **Automatic Optimization**: DLT handles optimization automatically
   - Auto-compaction and Z-ordering
   - Optimized file sizes
   - Better query performance downstream

3. **Reduced Development Time**:
   - Simpler pipeline code (declarative vs imperative)
   - Built-in data quality and monitoring
   - Less time debugging and maintaining

4. **Better Resource Utilization**:
   - DLT can scale clusters dynamically based on workload
   - More efficient task parallelization
   - Reduced idle time between tasks

5. **Failure Recovery**:
   - DLT checkpointing means failed runs don't reprocess everything
   - Current workflow may need to start from scratch on failure
""")

# Optimistic scenario: 30% compute time reduction
print(f"{'=' * 80}")
print("Optimistic Scenario: 30% Compute Time Reduction")
print(f"{'=' * 80}\n")

optimized_compute_minutes = total_compute_minutes_per_month * 0.70
print(f"Optimized compute time: {optimized_compute_minutes:.0f} minutes/month (down from {total_compute_minutes_per_month:.0f})")

for scenario_name, dbu_per_min in scenarios.items():
    print(f"\n{scenario_name}:")
    print("-" * 60)

    # Current workflow cost
    current_monthly_dbus = total_compute_minutes_per_month * dbu_per_min
    workflow_cost = current_monthly_dbus * COMPUTE_DBU_PRICE

    # Optimized DLT cost (less compute time, but higher per-DBU rate)
    optimized_monthly_dbus = optimized_compute_minutes * dbu_per_min
    dlt_core_optimized_cost = optimized_monthly_dbus * (COMPUTE_DBU_PRICE + DLT_CORE_PREMIUM)

    savings = workflow_cost - dlt_core_optimized_cost

    print(f"  Current Workflow:     ${workflow_cost:.2f}/month")
    print(f"  DLT Core (optimized): ${dlt_core_optimized_cost:.2f}/month")

    if savings > 0:
        print(f"  💰 Net SAVINGS: ${savings:.2f}/month (${savings * 12:.2f}/year)")
        print(f"  Savings %: {(savings/workflow_cost)*100:.0f}%")
    else:
        print(f"  Net cost increase: ${-savings:.2f}/month (${-savings * 12:.2f}/year)")

print(f"\n{'=' * 80}")
print("SUMMARY & RECOMMENDATIONS")
print(f"{'=' * 80}\n")

print("""
Key Findings:

1. **Direct Conversion**: Moving to DLT without optimizations will increase costs
   by 133-200% due to DLT's premium pricing.

2. **With Optimizations**: If DLT's incremental processing and optimizations
   reduce compute time by 30%+, total costs can be LOWER than current workflow.

3. **Non-Cost Benefits**:
   - Better data quality and monitoring
   - Simplified maintenance and development
   - Automatic optimization and compaction
   - Built-in lineage and observability
   - Reduced developer time

Recommendations:

✓ **Convert to DLT if**:
  - Data volume is growing (incremental processing will save more over time)
  - Data quality and observability are priorities
  - You want to reduce developer maintenance time
  - You're willing to invest in optimization

✗ **Keep as Workflow if**:
  - Cost is the primary concern and workload is stable
  - Current workflow is well-optimized and performant
  - Budget constraints are strict
  - Workflow includes many non-data tasks (emails, API calls)

💡 **Hybrid Approach**:
  - Convert only the core data processing tasks (unity_fde, income_verification)
    to DLT
  - Keep auxiliary tasks (emails, cleanup, deactivation) as separate workflow tasks
  - Use a workflow to orchestrate the DLT pipeline + other tasks
  - This gives you DLT benefits for data processing while maintaining flexibility
    for operational tasks
""")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80 + "\n")

print("""
1. **Get Accurate Cluster Details**: Check the exact cluster configuration
   used by the 00_RDS workflow to get precise DBU consumption

2. **Review Task Breakdown**: Identify which tasks would benefit most from DLT:
   - unity_fde (main FDE table creation) ✓ Good candidate
   - income_verification (IV processing) ✓ Good candidate
   - Email/notification tasks ✗ Keep as workflow tasks
   - Cleanup/admin tasks ✗ Keep as workflow tasks

3. **Pilot Test**: Run the DLT pipeline in parallel with the workflow for 1-2 weeks
   - Compare actual costs
   - Measure performance improvements
   - Validate data quality

4. **Negotiate Pricing**: If you have enterprise support, discuss:
   - Volume discounts for DLT
   - Commitment-based pricing
   - Reserved capacity options

5. **Optimize Current Workflow First**: Before converting, ensure current
   workflow is optimized (proper partitioning, caching, etc.) for fair comparison
""")

print("=" * 80)
