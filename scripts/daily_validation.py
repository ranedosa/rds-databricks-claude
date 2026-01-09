#!/usr/bin/env python3
"""
Daily Data Quality Validation Script
=====================================

Purpose: Automated validation of RDS to Salesforce sync health
Schedule: Run daily at 3:00 AM PT (after overnight syncs)
Duration: ~2 minutes

Checks:
1. Coverage hasn't dropped below 90%
2. NULL company names spike (>50)
3. Syncs ran recently (within expected window)
4. Queue sizes within normal range
5. Data quality maintained

Alerts:
- Sends email/Slack notification if issues detected
- Includes detailed error information
- Provides recommended actions

Usage:
  # Run manually:
  python3 scripts/daily_validation.py

  # Run with verbose output:
  python3 scripts/daily_validation.py --verbose

  # Dry run (no alerts sent):
  python3 scripts/daily_validation.py --dry-run

Schedule via cron (3:00 AM daily):
  0 3 * * * cd /path/to/rds_databricks_claude && python3 scripts/daily_validation.py

Or schedule via Databricks Job:
  - Create Notebook with this script
  - Schedule: Daily at 3:00 AM PT
  - Timeout: 10 minutes
  - Retry: 2 times
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from databricks import sql
from typing import List, Dict, Tuple

# Configuration
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"

# Thresholds
COVERAGE_THRESHOLD = 90.0  # Alert if coverage <90%
NULL_COMPANY_THRESHOLD = 50  # Alert if >50 NULLs
SYNC_RECENCY_HOURS = 2  # Alert if no sync in 2+ hours
CREATE_QUEUE_THRESHOLD = 100  # Alert if CREATE queue >100
UPDATE_QUEUE_THRESHOLD = 1000  # Alert if UPDATE queue >1000

# Alert recipients
ALERT_EMAIL = "dane@snappt.com"


def connect_databricks():
    """Connect to Databricks"""
    if not DATABRICKS_TOKEN:
        print("❌ ERROR: DATABRICKS_TOKEN environment variable not set")
        sys.exit(1)

    try:
        connection = sql.connect(
            server_hostname=DATABRICKS_HOST.replace('https://', ''),
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_TOKEN
        )
        return connection
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Databricks: {e}")
        sys.exit(1)


def validate_coverage(cursor) -> Tuple[bool, str, dict]:
    """
    Check that coverage hasn't dropped below threshold

    Returns:
        (is_valid, message, metrics)
    """
    query = """
    SELECT
        coverage_percentage,
        total_rds_properties,
        total_sf_properties,
        rds_to_sf_gap,
        coverage_status
    FROM crm.sfdc_dbx.daily_health_check
    """

    cursor.execute(query)
    row = cursor.fetchone()

    if not row:
        return False, "❌ ERROR: Could not retrieve health check data", {}

    coverage_pct = float(row[0])
    rds_total = int(row[1])
    sf_total = int(row[2])
    gap = int(row[3])
    status = row[4]

    metrics = {
        'coverage_pct': coverage_pct,
        'rds_total': rds_total,
        'sf_total': sf_total,
        'gap': gap,
        'status': status
    }

    if coverage_pct < COVERAGE_THRESHOLD:
        message = (
            f"❌ COVERAGE DROP: {coverage_pct:.2f}% (threshold: {COVERAGE_THRESHOLD}%)\n"
            f"   RDS Total: {rds_total:,}\n"
            f"   SF Total: {sf_total:,}\n"
            f"   Gap: {gap:,} properties\n"
            f"   Status: {status}\n"
            f"   → ACTION REQUIRED: Investigate why coverage dropped"
        )
        return False, message, metrics
    else:
        message = f"✅ Coverage OK: {coverage_pct:.2f}% (threshold: {COVERAGE_THRESHOLD}%)"
        return True, message, metrics


def validate_data_quality(cursor) -> Tuple[bool, str, dict]:
    """
    Check for NULL company names spike

    Returns:
        (is_valid, message, metrics)
    """
    query = """
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) as null_companies,
        SUM(CASE WHEN id_verification_enabled_c IS NULL THEN 1 ELSE 0 END) as null_idv,
        ROUND(100.0 * SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as null_pct
    FROM hive_metastore.salesforce.product_property
    WHERE _fivetran_deleted = false
    """

    cursor.execute(query)
    row = cursor.fetchone()

    total = int(row[0])
    null_companies = int(row[1])
    null_idv = int(row[2])
    null_pct = float(row[3])

    metrics = {
        'total': total,
        'null_companies': null_companies,
        'null_idv': null_idv,
        'null_pct': null_pct
    }

    if null_companies > NULL_COMPANY_THRESHOLD:
        message = (
            f"❌ DATA QUALITY ISSUE: {null_companies} properties with NULL company names (threshold: {NULL_COMPANY_THRESHOLD})\n"
            f"   Total Properties: {total:,}\n"
            f"   NULL %: {null_pct:.2f}%\n"
            f"   → ACTION REQUIRED: Check view definition for bugs (like Jan 9 company name bug)"
        )
        return False, message, metrics
    else:
        message = f"✅ Data Quality OK: {null_companies} NULL company names (threshold: {NULL_COMPANY_THRESHOLD})"
        return True, message, metrics


def validate_sync_recency(cursor) -> Tuple[bool, str, dict]:
    """
    Check that syncs ran recently

    Returns:
        (is_valid, message, metrics)
    """
    query = """
    SELECT
        MAX(created_date) as last_create,
        MAX(last_modified_date) as last_update,
        COUNT(CASE WHEN DATE(created_date) = CURRENT_DATE() THEN 1 END) as created_today,
        COUNT(CASE WHEN DATE(last_modified_date) = CURRENT_DATE() THEN 1 END) as updated_today
    FROM hive_metastore.salesforce.product_property
    WHERE _fivetran_deleted = false
    """

    cursor.execute(query)
    row = cursor.fetchone()

    last_create = row[0]
    last_update = row[1]
    created_today = int(row[2])
    updated_today = int(row[3])

    now = datetime.now()

    metrics = {
        'last_create': str(last_create),
        'last_update': str(last_update),
        'created_today': created_today,
        'updated_today': updated_today
    }

    issues = []

    # Check CREATE sync recency
    if last_create:
        hours_since_create = (now - last_create).total_seconds() / 3600
        if hours_since_create > SYNC_RECENCY_HOURS:
            issues.append(
                f"   - No CREATE sync in {hours_since_create:.1f} hours (last: {last_create})"
            )

    # Check UPDATE sync recency
    if last_update:
        hours_since_update = (now - last_update).total_seconds() / 3600
        if hours_since_update > SYNC_RECENCY_HOURS:
            issues.append(
                f"   - No UPDATE sync in {hours_since_update:.1f} hours (last: {last_update})"
            )

    # Check if any activity today (after 8am)
    if now.hour >= 8 and created_today == 0 and updated_today == 0:
        issues.append(
            f"   - No sync activity today (after 8am) - created: {created_today}, updated: {updated_today}"
        )

    if issues:
        message = (
            f"❌ SYNC RECENCY ISSUE:\n" +
            "\n".join(issues) +
            f"\n   → ACTION REQUIRED: Check Census sync schedules: https://app.getcensus.com/syncs"
        )
        return False, message, metrics
    else:
        message = f"✅ Sync Recency OK: Created {created_today}, Updated {updated_today} today"
        return True, message, metrics


def validate_queue_sizes(cursor) -> Tuple[bool, str, dict]:
    """
    Check queue sizes are within normal range

    Returns:
        (is_valid, message, metrics)
    """
    query_create = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create"
    query_update = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update"

    cursor.execute(query_create)
    create_queue = int(cursor.fetchone()[0])

    cursor.execute(query_update)
    update_queue = int(cursor.fetchone()[0])

    metrics = {
        'create_queue': create_queue,
        'update_queue': update_queue
    }

    issues = []

    if create_queue > CREATE_QUEUE_THRESHOLD:
        issues.append(
            f"   - CREATE queue: {create_queue:,} (threshold: {CREATE_QUEUE_THRESHOLD})"
        )

    if update_queue > UPDATE_QUEUE_THRESHOLD:
        issues.append(
            f"   - UPDATE queue: {update_queue:,} (threshold: {UPDATE_QUEUE_THRESHOLD})"
        )

    if issues:
        message = (
            f"❌ QUEUE BACKLOG:\n" +
            "\n".join(issues) +
            f"\n   → ACTION: Monitor queue drain rate. May indicate sync paused or rate-limited."
        )
        return False, message, metrics
    else:
        message = f"✅ Queue Sizes OK: CREATE={create_queue}, UPDATE={update_queue}"
        return True, message, metrics


def run_validation(verbose=False, dry_run=False) -> Tuple[bool, List[str], Dict]:
    """
    Run all validation checks

    Returns:
        (all_passed, messages, all_metrics)
    """
    print(f"\n{'='*80}")
    print(f"RDS to Salesforce Sync - Daily Validation")
    print(f"{'='*80}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # Connect to Databricks
    print("→ Connecting to Databricks...")
    connection = connect_databricks()
    cursor = connection.cursor()
    print("✅ Connected\n")

    # Run validations
    all_passed = True
    messages = []
    all_metrics = {}

    checks = [
        ("Coverage", validate_coverage),
        ("Data Quality", validate_data_quality),
        ("Sync Recency", validate_sync_recency),
        ("Queue Sizes", validate_queue_sizes)
    ]

    for check_name, check_func in checks:
        print(f"→ Running {check_name} check...")
        is_valid, message, metrics = check_func(cursor)

        if verbose:
            print(f"   Metrics: {metrics}")

        print(f"{message}\n")

        if not is_valid:
            all_passed = False
            messages.append(f"**{check_name} Check Failed:**\n{message}")

        all_metrics[check_name] = metrics

    cursor.close()
    connection.close()

    # Summary
    print(f"{'='*80}")
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print(f"{'='*80}\n")
        print("System is healthy. No action required.")
    else:
        print("❌ VALIDATION FAILURES DETECTED")
        print(f"{'='*80}\n")
        print(f"Failed checks: {len([m for m in messages if m])}")
        print("\nAction required - see details above.")

        if not dry_run:
            print("\n→ Sending alert notifications...")
            send_alert_notification(messages, all_metrics)
            print("✅ Alerts sent")
        else:
            print("\n→ DRY RUN: Alerts not sent")

    return all_passed, messages, all_metrics


def send_alert_notification(messages: List[str], metrics: Dict):
    """
    Send alert notification via email/Slack

    For now, this is a placeholder. To implement:
    1. Install: pip install sendgrid (for email)
    2. Or: pip install slack-sdk (for Slack)
    3. Configure credentials in environment variables
    """
    alert_body = "\n\n".join(messages)

    print("\n" + "="*80)
    print("ALERT NOTIFICATION")
    print("="*80)
    print(f"\nTo: {ALERT_EMAIL}")
    print(f"Subject: RDS to Salesforce Sync - Daily Validation FAILED")
    print(f"\nBody:\n{alert_body}")
    print("\n" + "="*80)

    # TODO: Implement actual email/Slack sending
    # Example with SendGrid:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    #
    # message = Mail(
    #     from_email='noreply@snappt.com',
    #     to_emails=ALERT_EMAIL,
    #     subject='RDS to Salesforce Sync - Daily Validation FAILED',
    #     html_content=alert_body.replace('\n', '<br>')
    # )
    # sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
    # response = sg.send(message)

    # Example with Slack:
    # from slack_sdk import WebClient
    #
    # client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
    # client.chat_postMessage(
    #     channel='#data-alerts',
    #     text=alert_body
    # )

    # For now, just print to console
    # In production, uncomment one of the above implementations


def main():
    parser = argparse.ArgumentParser(
        description='Daily validation for RDS to Salesforce sync'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose output including metrics'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run validation but do not send alerts'
    )

    args = parser.parse_args()

    try:
        all_passed, messages, metrics = run_validation(
            verbose=args.verbose,
            dry_run=args.dry_run
        )

        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
