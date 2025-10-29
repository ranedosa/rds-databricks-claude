"""
Quick Databricks Workspace Audit - Jobs and Clusters Only
"""

import json
import os
from datetime import datetime, timedelta
import subprocess

DAYS_THRESHOLD_INACTIVE = 90
OUTPUT_DIR = "audit_results"
DATABRICKS_PROFILE = "pat"

def run_cli(cmd):
    """Execute databricks CLI command"""
    cmd_with_profile = cmd.replace("databricks ", f"databricks --profile {DATABRICKS_PROFILE} ")
    try:
        result = subprocess.run(cmd_with_profile, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except:
                return None
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def audit_jobs():
    """Audit jobs"""
    print("Auditing jobs...")
    jobs_data = run_cli("databricks jobs list --output json")

    if not jobs_data:
        return {"total": 0, "active": 0, "inactive": 0, "never_run": 0, "details": []}

    # Handle both old format (dict with 'jobs' key) and new format (direct list)
    if isinstance(jobs_data, list):
        jobs = jobs_data
    else:
        jobs = jobs_data.get('jobs', [])
    active, inactive, never_run = 0, 0, 0
    threshold = datetime.now() - timedelta(days=DAYS_THRESHOLD_INACTIVE)
    job_details = []

    for job in jobs:
        job_id = job.get('job_id')
        job_name = job.get('settings', {}).get('name', 'Unknown')

        runs_list = run_cli(f"databricks jobs list-runs --job-id {job_id} --limit 1 --output json")

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
    """Audit clusters"""
    print("Auditing clusters...")
    clusters_data = run_cli("databricks clusters list --output json")

    if not clusters_data:
        return {"total": 0, "running": 0, "terminated": 0, "details": []}

    # Handle both old format (dict with 'clusters' key) and new format (direct list)
    if isinstance(clusters_data, list):
        clusters = clusters_data
    else:
        clusters = clusters_data.get('clusters', [])
    running, terminated = 0, 0
    cluster_details = []

    for cluster in clusters:
        state = cluster.get('state', 'Unknown')
        if state == 'RUNNING':
            running += 1
        else:
            terminated += 1

        last_activity = cluster.get('last_activity_time', 0) / 1000
        last_activity_date = datetime.fromtimestamp(last_activity) if last_activity > 0 else None

        cluster_details.append({
            "cluster_id": cluster.get('cluster_id'),
            "name": cluster.get('cluster_name', 'Unknown'),
            "state": state,
            "last_activity": last_activity_date.strftime('%Y-%m-%d %H:%M') if last_activity_date else "Unknown",
            "created_by": cluster.get('creator_user_name', 'Unknown'),
            "node_type": cluster.get('node_type_id', 'Unknown'),
            "num_workers": cluster.get('num_workers', 0)
        })

    return {
        "total": len(clusters),
        "running": running,
        "terminated": terminated,
        "details": cluster_details
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("QUICK DATABRICKS WORKSPACE AUDIT")
    print("=" * 80)
    print("")

    results = {
        "timestamp": datetime.now().isoformat(),
        "jobs": audit_jobs(),
        "clusters": audit_clusters()
    }

    # Save JSON
    json_file = os.path.join(OUTPUT_DIR, f"quick_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print report
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    jobs = results['jobs']
    print(f"\nJOBS: {jobs['total']} total")
    print(f"  ✓ Active: {jobs['active']} ({jobs['active']/max(jobs['total'],1)*100:.1f}%)")
    print(f"  ⚠ Inactive: {jobs['inactive']} ({jobs['inactive']/max(jobs['total'],1)*100:.1f}%)")
    print(f"  ✗ Never Run: {jobs['never_run']} ({jobs['never_run']/max(jobs['total'],1)*100:.1f}%)")

    waste = jobs['inactive'] + jobs['never_run']
    if waste > 0:
        print(f"\n  💡 {waste} jobs ({waste/max(jobs['total'],1)*100:.1f}%) can be cleaned up!")

    clusters = results['clusters']
    print(f"\nCLUSTERS: {clusters['total']} total")
    print(f"  ▶ Running: {clusters['running']}")
    print(f"  ■ Terminated: {clusters['terminated']}")

    if clusters['running'] > 3:
        print(f"\n  💡 {clusters['running']} running clusters - review for cost optimization")

    print("\n" + "=" * 80)
    print(f"Full results saved to: {json_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
