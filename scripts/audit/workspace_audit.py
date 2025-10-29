"""
Databricks Workspace Audit Script
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
            return json.loads(result.stdout)
        else:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception running command {cmd}: {e}")
        return None

def audit_jobs():
    """Audit Databricks jobs"""
    print("Auditing jobs...")
    jobs_data = run_databricks_cli("databricks jobs list --output json")

    if not jobs_data or 'jobs' not in jobs_data:
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
        runs_data = run_databricks_cli(f"databricks jobs get --job-id {job_id} --output json")

        if runs_data:
            created_time = runs_data.get('created_time', 0) / 1000  # Convert from milliseconds

            # Check last run
            runs_list = run_databricks_cli(f"databricks jobs list-runs --job-id {job_id} --limit 1 --output json")

            last_run_time = None
            if runs_list and 'runs' in runs_list and len(runs_list['runs']) > 0:
                last_run_time = runs_list['runs'][0].get('start_time', 0) / 1000
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
                status = "Never Run"
                last_run_str = "Never"

            job_details.append({
                "job_id": job_id,
                "name": job_name,
                "status": status,
                "last_run": last_run_str,
                "created_by": runs_data.get('creator_user_name', 'Unknown')
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

    if not clusters_data or 'clusters' not in clusters_data:
        return {"total": 0, "running": 0, "terminated": 0, "details": []}

    clusters = clusters_data.get('clusters', [])
    running = 0
    terminated = 0
    cluster_details = []

    for cluster in clusters:
        cluster_id = cluster.get('cluster_id')
        cluster_name = cluster.get('cluster_name', 'Unknown')
        state = cluster.get('state', 'Unknown')

        # Get detailed cluster info
        detail = run_databricks_cli(f"databricks clusters get --cluster-id {cluster_id} --output json")

        if detail:
            last_activity = detail.get('last_activity_time', 0) / 1000
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
                "created_by": detail.get('creator_user_name', 'Unknown'),
                "cluster_source": detail.get('cluster_source', 'Unknown'),
                "node_type": detail.get('node_type_id', 'Unknown'),
                "num_workers": detail.get('num_workers', 0)
            })

    return {
        "total": len(clusters),
        "running": running,
        "terminated": terminated,
        "details": cluster_details
    }

def audit_notebooks():
    """Audit workspace notebooks"""
    print("Auditing notebooks...")
    # List workspace recursively (newer CLI doesn't use -l flag)
    workspace_data = run_databricks_cli("databricks workspace list / --output json")

    if not workspace_data:
        return {"total": 0, "details": []}

    def recurse_workspace(path="/"):
        """Recursively list all notebooks"""
        notebooks = []
        data = run_databricks_cli(f"databricks workspace list '{path}' --output json")

        if data and 'objects' in data:
            for obj in data['objects']:
                if obj.get('object_type') == 'NOTEBOOK':
                    modified_time = obj.get('modified_at', 0) / 1000
                    modified_date = datetime.fromtimestamp(modified_time) if modified_time > 0 else None

                    notebooks.append({
                        "path": obj.get('path'),
                        "language": obj.get('language', 'Unknown'),
                        "modified_at": modified_date.strftime('%Y-%m-%d') if modified_date else "Unknown",
                        "modified_by": obj.get('modified_by', 'Unknown')
                    })
                elif obj.get('object_type') == 'DIRECTORY':
                    # Recurse into directories
                    notebooks.extend(recurse_workspace(obj.get('path')))

        return notebooks

    all_notebooks = recurse_workspace()

    # Count inactive notebooks
    now = datetime.now()
    threshold = now - timedelta(days=DAYS_THRESHOLD_INACTIVE)
    inactive = sum(1 for nb in all_notebooks
                   if nb['modified_at'] != "Unknown" and
                   datetime.strptime(nb['modified_at'], '%Y-%m-%d') < threshold)

    return {
        "total": len(all_notebooks),
        "inactive": inactive,
        "details": all_notebooks
    }

def audit_tables():
    """Audit tables/databases"""
    print("Auditing tables...")
    # Note: This requires SQL execution, which is more complex
    # For now, we'll provide a placeholder structure
    return {
        "note": "Table audit requires SQL execution. Use Unity Catalog system tables or run SQL queries to analyze table usage.",
        "recommended_queries": [
            "SELECT * FROM system.information_schema.tables",
            "SELECT * FROM system.access.table_lineage",
            "SELECT * FROM system.access.audit"
        ]
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
    report.append(f"  Inactive (not modified in {DAYS_THRESHOLD_INACTIVE}+ days): {notebooks.get('inactive', 0)}")
    report.append("")

    if notebooks.get('inactive', 0) > 0:
        inactive_pct = (notebooks.get('inactive', 0) / notebooks.get('total', 1)) * 100
        report.append(f"⚠️  RECOMMENDATION: {inactive_pct:.1f}% of notebooks are inactive. Consider archiving.")
        report.append("")

    # Cost implications
    report.append("COST IMPLICATIONS")
    report.append("-" * 80)
    report.append("Active compute resources that could be optimized:")
    report.append(f"  - {clusters.get('running', 0)} running clusters")
    report.append(f"  - {jobs.get('active', 0)} active jobs (review schedules/frequency)")
    report.append("")

    # Recommendations
    report.append("RECOMMENDATIONS FOR PROD ENVIRONMENT")
    report.append("-" * 80)
    active_job_pct = (jobs.get('active', 0) / jobs.get('total', 1)) * 100 if jobs.get('total', 0) > 0 else 0
    report.append(f"1. Migrate only active assets: ~{active_job_pct:.0f}% of jobs ({jobs.get('active', 0)}/{jobs.get('total', 0)})")
    report.append(f"2. Clean up before migration: {jobs.get('inactive', 0) + jobs.get('never_run', 0)} unused jobs")
    report.append(f"3. Archive inactive notebooks: {notebooks.get('inactive', 0)} candidates")
    report.append("4. Implement governance policies to prevent future sprawl")
    report.append("5. Set up proper CI/CD for controlled deployments")
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
        "notebooks": audit_notebooks(),
        "tables": audit_tables()
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
