# Production Readiness Checklist - RDS to Salesforce Sync

**Created:** January 9, 2026
**Current Status:** System operational, needs production hardening
**Target:** Fully production-ready with daily (or more frequent) sync cadence

---

## Current State Summary

### ✅ What's Working
- **Data Pipeline:** RDS → Databricks → Census → Salesforce (operational)
- **Coverage:** 93%+ (18,722 of 20,247 properties)
- **Accuracy:** 100% (validated sample after bug fix)
- **Error Rate:** <1% (exceeds <5% target)
- **Syncs Configured:** Sync A (CREATE) + Sync B (UPDATE)
- **Schedule:** Every 15-30 minutes (more frequent than daily requirement)

### ⚠️ What's Missing for Production
1. Monitoring & alerting not set up
2. Census automated schedules not verified as enabled
3. Operational runbooks incomplete
4. Stakeholder communication pending
5. Data quality monitoring not automated
6. Error handling procedures undefined
7. Backup/recovery plan not documented

---

## Phase 1: Critical Production Requirements (This Week)

### 1.1 Verify Census Automated Schedules ⏰
**Priority:** CRITICAL
**Time:** 15 minutes

**Action Steps:**
```bash
# Check Census sync schedules
https://app.getcensus.com/syncs/3394022  # Sync A (CREATE)
https://app.getcensus.com/syncs/3394041  # Sync B (UPDATE)
```

**Verify:**
- [ ] Sync A schedule: ENABLED (every 30 minutes or daily)
- [ ] Sync B schedule: ENABLED (every 15 minutes or daily)
- [ ] Both syncs show "Active" status
- [ ] Last run timestamp is recent (within schedule window)
- [ ] No error badges or warning icons

**If schedules are OFF:**
```
1. Click sync name → Settings → Schedule
2. Enable "Run this sync on a schedule"
3. Set frequency:
   - Minimum: Daily at 2:00 AM PT
   - Current: Every 15-30 minutes (if acceptable)
4. Save changes
5. Verify next scheduled run shows correct time
```

---

### 1.2 Set Up Census Sync Monitoring 📊
**Priority:** CRITICAL
**Time:** 30 minutes

**Option A: Census Native Alerts**
```
1. Go to Census: https://app.getcensus.com/settings/notifications
2. Configure alerts for:
   - Sync failures (error rate >5%)
   - Data quality issues
   - Schedule missed runs
3. Add email recipients:
   - dane@snappt.com
   - data-engineering@snappt.com
   - [other team members]
```

**Option B: Create Databricks Alert Dashboard**
```sql
-- Create monitoring view
CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_health_monitor AS
SELECT
  'Census Sync A' AS sync_name,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS queue_size,
  (SELECT MAX(created_date) FROM crm.salesforce.product_property
   WHERE DATE(created_date) = CURRENT_DATE()) AS last_sync_today,
  CASE
    WHEN queue_size > 100 THEN '🔴 High backlog'
    WHEN last_sync_today IS NULL THEN '🔴 No syncs today'
    ELSE '✅ Healthy'
  END AS status
UNION ALL
SELECT
  'Census Sync B' AS sync_name,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS queue_size,
  (SELECT MAX(last_modified_date) FROM crm.salesforce.product_property
   WHERE DATE(last_modified_date) = CURRENT_DATE()) AS last_sync_today,
  CASE
    WHEN queue_size > 1000 THEN '🔴 High backlog'
    WHEN last_sync_today IS NULL THEN '🔴 No syncs today'
    ELSE '✅ Healthy'
  END AS status;

-- Query to run daily
SELECT * FROM crm.sfdc_dbx.sync_health_monitor;
```

**Checklist:**
- [ ] Alerts configured in Census
- [ ] Alert recipients added
- [ ] Test alert by triggering sync failure
- [ ] Monitoring dashboard created
- [ ] Team knows where to check sync health

---

### 1.3 Create Operational Runbook 📖
**Priority:** HIGH
**Time:** 2 hours

**Document:** Create `OPERATIONS_RUNBOOK.md` with:

#### Daily Operations (5 minutes)
```sql
-- Run health check query
SELECT * FROM crm.sfdc_dbx.daily_health_check;

-- Expected results:
coverage_percentage: >90%
create_queue_count: <100
update_queue_count: <1000
coverage_status: "✅ Coverage Good"
```

**Action if issues:**
- Coverage <90%: Check if Census syncs are running
- CREATE queue >100: Investigate why properties not syncing
- UPDATE queue >1000: Check for data quality issues

#### Weekly Review (15 minutes)
```sql
-- Review sync audit log
SELECT
  sync_name,
  execution_timestamp,
  records_processed,
  records_succeeded,
  error_rate
FROM crm.sfdc_dbx.sync_audit_log
WHERE execution_timestamp >= CURRENT_DATE() - INTERVAL 7 DAYS
ORDER BY execution_timestamp DESC;
```

**Action items:**
- Review error patterns
- Check for anomalies
- Update stakeholders on sync health

#### When Sync Fails (Troubleshooting)
```
1. Check Census sync logs:
   - https://app.getcensus.com/syncs/3394022 (Sync A)
   - https://app.getcensus.com/syncs/3394041 (Sync B)

2. Common errors:
   - "Invalid field": Check if Salesforce schema changed
   - "Duplicate records": Check for duplicate SFDC IDs
   - "Rate limit": Wait and retry, or contact Census support
   - "Connection timeout": Check Databricks warehouse status

3. Manual retry:
   - Click "Run Sync" button in Census UI
   - Monitor execution
   - Validate results in Salesforce

4. If persistent failures (>3 retries):
   - Check source views in Databricks
   - Verify Databricks warehouse is running
   - Check Salesforce API limits
   - Contact Census support if needed
```

**Checklist:**
- [ ] Daily operations documented
- [ ] Weekly review procedure documented
- [ ] Troubleshooting guide created
- [ ] Escalation contacts added
- [ ] Runbook reviewed by team

---

### 1.4 Implement Data Quality Checks 🔍
**Priority:** HIGH
**Time:** 1 hour

**Create automated validation script:**

```python
#!/usr/bin/env python3
"""
Daily data quality validation
Run after Census syncs complete (e.g., 3:00 AM PT)
"""
import os
from databricks import sql
from datetime import datetime, timedelta

def validate_daily_sync():
    """Run daily validation checks"""

    connection = sql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST").replace("https://", ""),
        http_path="/sql/1.0/warehouses/95a8f5979c3f8740",
        access_token=os.getenv("DATABRICKS_TOKEN")
    )
    cursor = connection.cursor()

    # Check 1: Coverage hasn't dropped
    cursor.execute("""
        SELECT coverage_percentage
        FROM crm.sfdc_dbx.daily_health_check
    """)
    coverage = cursor.fetchone()[0]

    if coverage < 90:
        print(f"🔴 ALERT: Coverage dropped to {coverage}%")
        send_alert("Coverage drop", f"Coverage: {coverage}%")
    else:
        print(f"✅ Coverage: {coverage}%")

    # Check 2: No spike in NULL company names
    cursor.execute("""
        SELECT COUNT(*) as null_companies
        FROM crm.salesforce.product_property
        WHERE company_name_c IS NULL
          AND _fivetran_deleted = false
          AND DATE(last_modified_date) = CURRENT_DATE()
    """)
    null_companies = cursor.fetchone()[0]

    if null_companies > 50:
        print(f"🔴 ALERT: {null_companies} properties with NULL company names today")
        send_alert("Data quality issue", f"NULL companies: {null_companies}")
    else:
        print(f"✅ NULL company names: {null_companies}")

    # Check 3: Syncs ran recently
    cursor.execute("""
        SELECT
            MAX(created_date) as last_create,
            MAX(last_modified_date) as last_update
        FROM crm.salesforce.product_property
        WHERE _fivetran_deleted = false
    """)
    last_create, last_update = cursor.fetchone()

    hours_since_create = (datetime.now() - last_create).total_seconds() / 3600
    hours_since_update = (datetime.now() - last_update).total_seconds() / 3600

    if hours_since_create > 24:
        print(f"🔴 ALERT: No creates in {hours_since_create:.1f} hours")
        send_alert("Sync stalled", f"No creates in {hours_since_create:.1f}h")

    if hours_since_update > 2:
        print(f"⚠️ WARNING: No updates in {hours_since_update:.1f} hours")
    else:
        print(f"✅ Last update: {hours_since_update:.1f} hours ago")

    cursor.close()
    connection.close()

def send_alert(subject, message):
    """Send alert to team (implement with your alerting system)"""
    # Option 1: Email via sendgrid/mailgun
    # Option 2: Slack webhook
    # Option 3: PagerDuty
    print(f"ALERT: {subject} - {message}")

if __name__ == "__main__":
    validate_daily_sync()
```

**Schedule this script:**
```bash
# Add to cron (runs daily at 3:00 AM PT)
0 3 * * * cd /path/to/scripts && python3 daily_validation.py >> /var/log/census_validation.log 2>&1
```

**Checklist:**
- [ ] Validation script created
- [ ] Script scheduled (cron/Airflow/other)
- [ ] Alert mechanism configured
- [ ] Test script runs successfully
- [ ] Team added to alert distribution

---

### 1.5 Update Stakeholder Communication 📢
**Priority:** HIGH
**Time:** 30 minutes

**Action: Send production launch notification**

Use `STAKEHOLDER_NOTIFICATION.md` as template, but update with:
```markdown
Subject: RDS to Salesforce Sync - Now Production Ready ✅

Team,

The RDS to Salesforce property sync is now fully operational in production!

**What This Means:**
✅ Salesforce Product_Property records now automatically sync with RDS
✅ Feature flags update every 15-30 minutes (or daily minimum)
✅ 93%+ of RDS properties visible in Salesforce
✅ 100% data accuracy (company names, feature flags, timestamps)

**How It Works:**
- RDS data flows to Databricks (5-15 min)
- Census syncs Databricks → Salesforce (15-30 min)
- Total sync time: 20-45 minutes from RDS update to SF

**What Changed:**
- 574 new properties added
- 9,141 properties updated with current feature flags
- Company names corrected (8,577 properties)

**No Action Required:**
- Syncs run automatically
- Monitoring is in place
- Data quality checks active

**Questions?**
Contact: dane@snappt.com or data-engineering@snappt.com

Dashboard: [link to monitoring dashboard]
Runbook: [link to operations runbook]
```

**Distribution list:**
- [ ] Sales Operations
- [ ] Customer Success team
- [ ] Salesforce Admin team
- [ ] Data Engineering team
- [ ] Product team
- [ ] Leadership/stakeholders

---

## Phase 2: Enhanced Operations (Next 2 Weeks)

### 2.1 Set Up Monitoring Dashboard 📈
**Priority:** MEDIUM
**Time:** 3 hours

**Create Databricks SQL Dashboard:**

```sql
-- Tile 1: Sync Health
SELECT
  'System Status' as metric,
  CASE
    WHEN coverage_percentage >= 95 THEN '✅ Excellent'
    WHEN coverage_percentage >= 90 THEN '⚠️ Good'
    ELSE '🔴 Needs Attention'
  END as status
FROM crm.sfdc_dbx.daily_health_check;

-- Tile 2: Coverage Trend (Last 7 Days)
-- (Requires historical tracking - add to audit log)

-- Tile 3: Sync Queue Sizes
SELECT
  'CREATE Queue' as queue,
  COUNT(*) as size
FROM crm.sfdc_dbx.properties_to_create
UNION ALL
SELECT
  'UPDATE Queue' as queue,
  COUNT(*) as size
FROM crm.sfdc_dbx.properties_to_update;

-- Tile 4: Recent Sync Activity
SELECT
  DATE(last_modified_date) as date,
  COUNT(*) as properties_updated
FROM crm.salesforce.product_property
WHERE last_modified_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY DATE(last_modified_date)
ORDER BY date DESC;

-- Tile 5: Data Quality Metrics
SELECT
  COUNT(*) as total_properties,
  SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) as null_companies,
  SUM(CASE WHEN sf_property_id_c IS NULL THEN 1 ELSE 0 END) as null_sfdc_ids,
  ROUND(100.0 * (1 - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) / COUNT(*)), 2) as quality_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false;
```

**Dashboard Features:**
- Refresh: Every 1 hour
- Alerts: Enabled for quality_pct <95%
- Access: Shared with data-engineering@snappt.com
- URL: Bookmark and share with team

**Checklist:**
- [ ] Dashboard created in Databricks SQL
- [ ] All tiles configured
- [ ] Auto-refresh enabled
- [ ] Alerts configured
- [ ] Team has access link

---

### 2.2 Historical Tracking & Reporting 📊
**Priority:** MEDIUM
**Time:** 2 hours

**Enhance audit log to track daily metrics:**

```sql
-- Insert daily snapshot into audit log
INSERT INTO crm.sfdc_dbx.sync_audit_log (
  audit_id,
  sync_name,
  sync_type,
  execution_timestamp,
  records_processed,
  records_succeeded,
  records_failed,
  error_rate,
  executed_by,
  notes
)
SELECT
  CONCAT('daily_snapshot_', DATE_FORMAT(CURRENT_TIMESTAMP(), 'yyyyMMdd')),
  'Daily Snapshot',
  'MONITORING',
  CURRENT_TIMESTAMP(),
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE _fivetran_deleted = false),
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE _fivetran_deleted = false AND company_name_c IS NOT NULL),
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE _fivetran_deleted = false AND company_name_c IS NULL),
  (SELECT ROUND(100.0 * COUNT(CASE WHEN company_name_c IS NULL THEN 1 END) / COUNT(*), 2)
   FROM crm.salesforce.product_property WHERE _fivetran_deleted = false),
  'automated_monitoring',
  CONCAT('Coverage: ',
    (SELECT CAST(coverage_percentage AS STRING) FROM crm.sfdc_dbx.daily_health_check),
    '%');
```

**Schedule:** Run daily at 11:59 PM PT

**Benefits:**
- Track coverage trends over time
- Identify degradation early
- Report monthly metrics to leadership
- Historical baseline for troubleshooting

**Checklist:**
- [ ] Daily snapshot query created
- [ ] Scheduled in Databricks Jobs
- [ ] Test insertion successful
- [ ] Create monthly report template

---

### 2.3 Error Handling & Recovery Procedures 🔧
**Priority:** MEDIUM
**Time:** 2 hours

**Document recovery procedures:**

#### Scenario 1: Census Sync Fails
```
1. Check Census sync page for error details
2. Common fixes:
   - Rate limit: Wait 1 hour, retry
   - Invalid field: Check Salesforce schema changes
   - Timeout: Reduce batch size in Census settings
3. Manual retry: Click "Run Sync" in Census UI
4. If 3 retries fail: Contact Census support
```

#### Scenario 2: Data Quality Drop (Coverage <90%)
```
1. Run health check query to identify issue
2. Check if properties_to_create/update views have data
3. Verify Databricks views haven't been modified
4. Check if RDS source data changed
5. Re-run sync manually if views are correct
```

#### Scenario 3: Duplicate Records Created
```
1. Identify duplicates:
   SELECT sf_property_id_c, COUNT(*)
   FROM crm.salesforce.product_property
   WHERE _fivetran_deleted = false
   GROUP BY sf_property_id_c
   HAVING COUNT(*) > 1

2. Root cause:
   - External ID not marked in Salesforce?
   - Census sync key misconfigured?

3. Fix:
   - Mark Snappt_Property_ID__c as External ID
   - Reconfigure Census sync key
   - Delete duplicate records in Salesforce
```

#### Scenario 4: View Definition Bug (Like Company Name Issue)
```
1. Identify affected view and bug
2. Create fix SQL
3. Test fix with sample query
4. Apply fix to production view
5. Re-run affected Census syncs
6. Validate fix in Salesforce
7. Document incident in audit log
```

**Checklist:**
- [ ] Recovery procedures documented
- [ ] Team trained on procedures
- [ ] Contact list for escalations
- [ ] Rollback procedures defined

---

### 2.4 Performance Optimization 🚀
**Priority:** LOW
**Time:** 3 hours

**Evaluate and optimize sync performance:**

**Current Performance:**
- Sync A: ~30 minutes for 740 records
- Sync B: ~1.5 minutes for 7,837 records

**Optimization Targets:**
- Sync A: <15 minutes
- Sync B: <5 minutes

**Optimization Steps:**
1. **Increase Census batch size:**
   - Settings → Advanced → Batch size
   - Increase from 1000 to 5000 (test first)

2. **Optimize Databricks views:**
   - Add indexes to frequently queried columns
   - Consider materializing views as tables
   - Cache frequently accessed data

3. **Partition large queries:**
   - properties_to_update could be partitioned by date
   - Only sync properties modified in last 7 days

4. **Enable Census Smart Sync:**
   - Only syncs changed records
   - Reduces API calls to Salesforce
   - Settings → Enable "Only sync changed fields"

**Checklist:**
- [ ] Baseline performance metrics captured
- [ ] Optimizations tested in non-production
- [ ] Performance improvements measured
- [ ] Document configuration changes

---

## Phase 3: Long-term Maintenance (Ongoing)

### 3.1 Monthly Review 📅
**Schedule:** First Monday of each month
**Time:** 1 hour

**Review Topics:**
1. **Sync Performance:**
   - Average sync duration
   - Error rate trends
   - Data quality metrics

2. **Coverage Analysis:**
   - Current coverage percentage
   - Properties not syncing (orphaned)
   - New properties added

3. **Incident Review:**
   - Sync failures
   - Data quality issues
   - Resolution time

4. **System Improvements:**
   - New features to sync
   - Process optimizations
   - Tool updates (Census, Databricks)

**Deliverable:** Monthly sync health report

---

### 3.2 Quarterly Configuration Review 🔍
**Schedule:** Quarterly
**Time:** 2 hours

**Review Areas:**
1. **Field Mappings:**
   - Are all required fields still mapping?
   - New fields to add?
   - Deprecated fields to remove?

2. **View Definitions:**
   - Still accurate and performant?
   - Business logic changes needed?
   - Deduplication still working?

3. **Sync Schedule:**
   - Is 15-30 minute frequency still needed?
   - Should we move to daily only?
   - Peak hours vs off-hours optimization?

4. **Access & Permissions:**
   - Who needs access to Census?
   - Databricks permissions current?
   - Salesforce API user still active?

**Deliverable:** Quarterly configuration audit

---

### 3.3 Team Training & Knowledge Transfer 👥
**Priority:** MEDIUM
**Time:** 4 hours (one-time)

**Training Sessions:**

**Session 1: System Overview (1 hour)**
- How the sync pipeline works
- Data flow diagram
- Key components (Databricks views, Census syncs)

**Session 2: Daily Operations (1 hour)**
- How to run health checks
- Reading monitoring dashboard
- Common troubleshooting scenarios

**Session 3: Hands-on Troubleshooting (2 hours)**
- Simulate sync failure
- Practice recovery procedures
- Review actual incidents

**Materials:**
- [ ] Training slides created
- [ ] Hands-on lab environment
- [ ] Runbook reviewed
- [ ] Q&A session held

---

## Phase 4: Advanced Features (Future)

### 4.1 Expand Sync Scope 🔄
**Future enhancements:**
- Add more fields to sync (custom properties)
- Sync additional objects (contacts, accounts)
- Bidirectional sync (Salesforce → RDS)

### 4.2 Machine Learning for Anomaly Detection 🤖
**Potential features:**
- Auto-detect unusual sync patterns
- Predict when coverage will drop
- Smart alerting (reduce false positives)

### 4.3 Self-Healing Automation 🔧
**Potential features:**
- Auto-retry failed syncs
- Auto-fix common errors
- Auto-scale Databricks warehouse

---

## Summary Checklist

### Week 1 (Critical - Must Complete)
- [ ] Verify Census automated schedules enabled
- [ ] Set up monitoring and alerts
- [ ] Create operational runbook
- [ ] Implement daily data quality checks
- [ ] Send stakeholder notification

### Week 2 (Important)
- [ ] Create monitoring dashboard
- [ ] Set up historical tracking
- [ ] Document error handling procedures
- [ ] Performance optimization

### Month 1 (Ongoing)
- [ ] Team training completed
- [ ] First monthly review held
- [ ] All documentation reviewed and approved

### Quarter 1 (Long-term)
- [ ] Quarterly configuration review
- [ ] Evaluate advanced features
- [ ] Process improvements identified

---

## Success Metrics

**System is production-ready when:**
- ✅ Automated syncs run reliably (>95% success rate)
- ✅ Monitoring alerts team of issues within 15 minutes
- ✅ Mean time to recovery (MTTR) <2 hours
- ✅ Data quality maintained >95%
- ✅ Coverage stable at >90%
- ✅ Team trained and confident in operations

**Daily cadence confirmed when:**
- ✅ Syncs run at least once every 24 hours
- ✅ Data lag from RDS to Salesforce <2 hours
- ✅ No manual intervention required for 7+ consecutive days

---

## Contact & Escalation

**Primary Contact:** dane@snappt.com
**Team:** data-engineering@snappt.com
**Escalation:** [manager/director]

**External Support:**
- Census: support@getcensus.com
- Databricks: [support contact]
- Salesforce: [admin contact]

---

**Last Updated:** January 9, 2026
**Owner:** Data Engineering Team
**Status:** ✅ Checklist created, awaiting execution
