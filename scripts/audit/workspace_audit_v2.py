"""
Databricks Workspace Audit Script (v2 - Compatible with new CLI)
Analyzes workspace assets to identify usage patterns and unused resources
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess

# Configuration
DAYS_THRESHOLD_INACTIVE = 90  # Assets not modified in 90 days considered inactive
OUTPUT_DIR = "audit_results"
DATABRICKS_PROFILE = "pat"  # Use the 'pat' profile with token authentication

def run_databricks_cli(cmd):
    """Execute databricks CLI command and return JSON output"""
    # Add profile flag to the command
    cmd_with_profile = cmd.replace("databricks ", f"databricks --profile {DATABRICKS_PROFILE} ")

    try:
        result = subprocess.run(
            cmd_with_profile,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0 and result.stdout:
            # Try to parse as JSON
            try:
                return json.loads(result.stdout)
            except:
                return {"raw_output": result.stdout}
        else:
            print(f"Warning: Command returned non-zero status: {cmd}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception running command {cmd}: {e}")
        return None

def audit_jobs():
    """Audit Databricks jobs"""
    print("Auditing jobs...")
    jobs_data = run_databricks_cli("databricks jobs list --output json")

    if not jobs_data or not isinstance(jobs_data, dict):
        print("Warning: Could not fetch jobs data")
        return {"total": 0, "active": 0, "inactive": 0, "never_run": 0, "details": []}

    jobs = jobs_data.get('jobs', [])
    active = 0
    inactive = 0
    never_run = 0
    now = datetime.now()
    threshold = now - timedelta(days=DAYS_THRESHOLD_INACTIVE)

    job_details = []

    for job in jobs:
        job_id = job.get('job_id')
        job_name = job.get('settings', {}).get('name', 'Unknown')

        # Get job runs
        runs_list = run_databricks_cli(f"databricks jobs list-runs --job-id {job_id} --limit 1 --output json")

        last_run_time = None
        status = "Never Run"
        last_run_str = "Never"

        if runs_list and 'runs' in runs_list and len(runs_list['runs']) > 0:
            last_run_time = runs_list['runs'][0].get('start_time', 0) / 1000
            if last_run_time > 0:
                last_run_date = datetime.fromtimestamp(last_run_time)

                if last_run_date > threshold:
                    active += 1
                    status = "Active"
                else:
                    inactive += 1
                    status = "Inactive"

                last_run_str = last_run_date.strftime('%Y-%m-%d')
        else:
            never_run += 1

        job_details.append({
            "job_id": job_id,
            "name": job_name,
            "status": status,
            "last_run": last_run_str,
            "creator": job.get('creator_user_name', 'Unknown')
        })

    return {
        "total": len(jobs),
        "active": active,
        "inactive": inactive,
        "never_run": never_run,
        "details": job_details
    }

def audit_clusters():
    """Audit Databricks clusters"""
    print("Auditing clusters...")
    clusters_data = run_databricks_cli("databricks clusters list --output json")

    if not clusters_data or not isinstance(clusters_data, dict):
        print("Warning: Could not fetch clusters data")
        return {"total": 0, "running": 0, "terminated": 0, "details": []}

    clusters = clusters_data.get('clusters', [])
    running = 0
    terminated = 0
    cluster_details = []

    for cluster in clusters:
        cluster_id = cluster.get('cluster_id')
        cluster_name = cluster.get('cluster_name', 'Unknown')
        state = cluster.get('state', 'Unknown')

        last_activity = cluster.get('last_activity_time', 0) / 1000
        last_activity_date = datetime.fromtimestamp(last_activity) if last_activity > 0 else None

        if state == 'RUNNING':
            running += 1
        else:
            terminated += 1

        cluster_details.append({
            "cluster_id": cluster_id,
            "name": cluster_name,
            "state": state,
            "last_activity": last_activity_date.strftime('%Y-%m-%d %H:%M') if last_activity_date else "Unknown",
            "created_by": cluster.get('creator_user_name', 'Unknown'),
            "cluster_source": cluster.get('cluster_source', 'Unknown'),
            "node_type": cluster.get('node_type_id', 'Unknown'),
            "num_workers": cluster.get('num_workers', 0)
        })

    return {
        "total": len(clusters),
        "running": running,
        "terminated": terminated,
        "details": cluster_details
    }

def count_workspace_objects(path="/"):
    """Recursively count notebooks and directories"""
    notebooks = []

    data = run_databricks_cli(f"databricks workspace list '{path}' --output json")

    if not data or not isinstance(data, list):
        return notebooks

    for obj in data:
        obj_path = obj.get('path')
        obj_type = obj.get('object_type')

        if obj_type == 'NOTEBOOK':
            notebooks.append({
                "path": obj_path,
                "type": "NOTEBOOK"
            })
        elif obj_type == 'DIRECTORY':
            # Recurse into directory
            notebooks.extend(count_workspace_objects(obj_path))

    return notebooks

def audit_notebooks():
    """Audit workspace notebooks"""
    print("Auditing notebooks (this may take a while)...")

    notebooks = count_workspace_objects()

    print(f"Found {len(notebooks)} notebooks")

    return {
        "total": len(notebooks),
        "details": notebooks,
        "note": "Modification dates require individual notebook inspection (not included for performance)"
    }

def generate_report(audit_results):
    """Generate human-readable audit report"""
    report = []
    report.append("=" * 80)
    report.append("DATABRICKS WORKSPACE AUDIT REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")

    # Jobs summary
    jobs = audit_results.get('jobs', {})
    report.append("JOBS SUMMARY")
    report.append("-" * 80)
    report.append(f"Total Jobs: {jobs.get('total', 0)}")
    report.append(f"  Active (ran in last {DAYS_THRESHOLD_INACTIVE} days): {jobs.get('active', 0)}")
    report.append(f"  Inactive (not run in {DAYS_THRESHOLD_INACTIVE}+ days): {jobs.get('inactive', 0)}")
    report.append(f"  Never Run: {jobs.get('never_run', 0)}")

    if jobs.get('total', 0) > 0:
        waste_pct = ((jobs.get('inactive', 0) + jobs.get('never_run', 0)) / jobs.get('total', 1)) * 100
        report.append(f"\n  Waste Rate: {waste_pct:.1f}% of jobs are inactive or never run")

    report.append("")

    if jobs.get('inactive', 0) > 0 or jobs.get('never_run', 0) > 0:
        report.append("⚠️  RECOMMENDATION: Consider archiving or deleting inactive/never-run jobs")
        report.append("")

    # Clusters summary
    clusters = audit_results.get('clusters', {})
    report.append("CLUSTERS SUMMARY")
    report.append("-" * 80)
    report.append(f"Total Clusters: {clusters.get('total', 0)}")
    report.append(f"  Running: {clusters.get('running', 0)}")
    report.append(f"  Terminated: {clusters.get('terminated', 0)}")
    report.append("")

    if clusters.get('running', 0) > 5:
        report.append("⚠️  RECOMMENDATION: Multiple running clusters detected. Review for unused resources.")
        report.append("")

    # Notebooks summary
    notebooks = audit_results.get('notebooks', {})
    report.append("NOTEBOOKS SUMMARY")
    report.append("-" * 80)
    report.append(f"Total Notebooks: {notebooks.get('total', 0)}")
    report.append("")

    # Cost implications
    report.append("COST IMPLICATIONS & MIGRATION PLANNING")
    report.append("-" * 80)
    report.append("Current workspace resources:")
    report.append(f"  - {jobs.get('total', 0)} total jobs ({jobs.get('active', 0)} active)")
    report.append(f"  - {clusters.get('total', 0)} clusters ({clusters.get('running', 0)} running)")
    report.append(f"  - {notebooks.get('total', 0)} notebooks")
    report.append("")

    # Recommendations
    report.append("RECOMMENDATIONS FOR PROD ENVIRONMENT")
    report.append("-" * 80)

    if jobs.get('total', 0) > 0:
        active_job_pct = (jobs.get('active', 0) / jobs.get('total', 1)) * 100
        report.append(f"1. Migrate active assets: {jobs.get('active', 0)} jobs ({active_job_pct:.0f}% of total)")
    else:
        report.append("1. No jobs found to migrate")

    cleanup_count = jobs.get('inactive', 0) + jobs.get('never_run', 0)
    report.append(f"2. Clean up before migration: {cleanup_count} unused jobs can be deleted")
    report.append(f"3. Review notebooks: {notebooks.get('total', 0)} total notebooks to evaluate")
    report.append("4. Implement governance policies to prevent future sprawl")
    report.append("5. Set up proper CI/CD for controlled deployments")
    report.append("")

    # Cost estimation
    report.append("ESTIMATED COST IMPACT OF DUAL ENVIRONMENT")
    report.append("-" * 80)
    report.append("Factors to consider:")
    report.append(f"  - Compute: {jobs.get('active', 0)} active jobs will consume DBUs in prod")
    report.append(f"  - Storage: Data duplication costs (depends on data volume)")
    report.append(f"  - Management: Operating two workspaces (~20-40% overhead initially)")
    report.append("  - Savings: Reduced waste from better resource management")
    report.append("")
    report.append("Next steps:")
    report.append("  1. Review active job list to determine prod candidates")
    report.append("  2. Estimate data volume for storage cost calculation")
    report.append("  3. Calculate current monthly DBU consumption")
    report.append("  4. Compare with Unity Catalog single-workspace alternative")
    report.append("")

    return "\n".join(report)

def main():
    """Main audit execution"""
    print("Starting Databricks Workspace Audit...")
    print("=" * 80)
    print("")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Run audits
    audit_results = {
        "timestamp": datetime.now().isoformat(),
        "jobs": audit_jobs(),
        "clusters": audit_clusters(),
        "notebooks": audit_notebooks()
    }

    # Save detailed JSON results
    json_file = os.path.join(OUTPUT_DIR, f"audit_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(json_file, 'w') as f:
        json.dump(audit_results, f, indent=2)
    print(f"\nDetailed results saved to: {json_file}")

    # Generate and save report
    report = generate_report(audit_results)
    report_file = os.path.join(OUTPUT_DIR, f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Summary report saved to: {report_file}")
    print("")
    print("=" * 80)
    print(report)

if __name__ == "__main__":
    main()
