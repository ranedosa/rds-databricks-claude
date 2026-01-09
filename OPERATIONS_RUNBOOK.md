# Operations Runbook - RDS to Salesforce Property Sync

## Quick Reference

**System:** Automated property sync from RDS PostgreSQL → Databricks → Census → Salesforce
**Target:** Product_Property__c (staging object in Salesforce)
**Coverage:** 93%+ of properties (18,722 of 20,247)
**Accuracy:** 100% after company name bug fix (Jan 9, 2026)
**Update Frequency:** Every 15-30 minutes (near real-time)

### Key Resources

- **Census Sync A (CREATE):** https://app.getcensus.com/syncs/3394022
- **Census Sync B (UPDATE):** https://app.getcensus.com/syncs/3394041
- **Databricks Health Check:** `SELECT * FROM crm.sfdc_dbx.daily_health_check`
- **Quick Commands:** `20260105/QUICK_REFERENCE.md`
- **Full Project History:** `COMPREHENSIVE_PROJECT_CONTEXT.md`

### Contact Information

- **Primary Owner:** dane@snappt.com
- **Data Engineering Team:** data-engineering@snappt.com
- **Census Support:** support@getcensus.com
- **Escalation:** CTO / VP Engineering

---

## Daily Operations (5 Minutes)

Run this check every morning to ensure the system is healthy.

### Step 1: Health Check Query

```sql
SELECT * FROM crm.sfdc_dbx.daily_health_check;
```

**Expected Values:**
- `coverage_percentage`: >90% (ideally >95%)
- `coverage_status`: "🟢 Coverage GOOD (>95%)" or "🟡 Coverage OK (90-95%)"
- `rds_to_sf_gap`: <1,500 properties
- `null_company_names`: <100
- `queue_status`: "🟢 Queues Healthy"

### Step 2: Interpret Results

**If coverage_percentage <90%:**
1. Check if RDS added many new properties: Compare `total_rds_properties` with yesterday
2. Check if Census syncs are running: Visit https://app.getcensus.com/syncs
3. Review sync errors: Check Census UI for error details
4. Escalate if gap is increasing

**If null_company_names >100:**
1. Check if view bug was reintroduced: `SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update WHERE company_name IS NULL`
2. If many NULLs in queue view, check RDS data quality
3. Review `20260105/VIEW2_properties_to_update.sql` for correctness
4. Escalate if NULLs are widespread

**If CREATE queue >100 OR UPDATE queue >1000:**
1. Check Census sync frequency: Should run every 15-30 min
2. Check for Census errors: Review recent sync runs
3. May indicate sync paused or rate-limited
4. Monitor - queues should drain within 1-2 hours

### Step 3: Quick Validation

```sql
-- Check recent sync activity (should see updates today)
SELECT
  DATE(last_modified_date) as sync_date,
  COUNT(*) as properties_updated
FROM hive_metastore.salesforce.product_property
WHERE last_modified_date >= CURRENT_DATE() - INTERVAL 1 DAYS
GROUP BY DATE(last_modified_date)
ORDER BY sync_date DESC;
```

**Expected:** You should see records updated today (current date).

**If no updates today:**
1. Check time of day (syncs may not have run yet if early morning)
2. Check Census schedule: https://app.getcensus.com/syncs/3394022/settings
3. Check if RDS data changed (no changes = no updates)
4. Investigate if no updates after 2+ hours

---

## Weekly Review (15 Minutes)

Run this check every Monday morning to review the past week's performance.

### Step 1: Review Sync Audit Log

```sql
SELECT
  execution_timestamp,
  sync_name,
  records_processed,
  records_succeeded,
  records_failed,
  error_rate,
  notes
FROM crm.sfdc_dbx.sync_audit_log
WHERE execution_timestamp >= CURRENT_DATE() - INTERVAL 7 DAYS
ORDER BY execution_timestamp DESC;
```

**Look for:**
- Increasing error rates (>5%)
- Declining coverage trends
- Unusual patterns (e.g., many failures on specific days)

### Step 2: Check Coverage Trend

```sql
-- Track coverage over past 7 days (once daily snapshot populated)
SELECT
  DATE(execution_timestamp) as date,
  CAST(REGEXP_EXTRACT(notes, 'Coverage: ([0-9.]+)%', 1) AS DOUBLE) as coverage_pct
FROM crm.sfdc_dbx.sync_audit_log
WHERE execution_timestamp >= CURRENT_DATE() - INTERVAL 7 DAYS
  AND sync_type = 'MONITORING'
ORDER BY date DESC;
```

**Expected:** Coverage should be stable (90-95%) or improving.

### Step 3: Review Census Sync Performance

Visit each sync in Census UI:
- https://app.getcensus.com/syncs/3394022 (CREATE)
- https://app.getcensus.com/syncs/3394041 (UPDATE)

**Check:**
- Success rate: Should be >95%
- Average run time: CREATE <5 min, UPDATE <10 min
- Recent errors: Review and categorize

### Step 4: Identify Error Patterns

Common error categories:
1. **Salesforce API Errors:** Rate limits, field validation, duplicate detection
2. **Data Quality Errors:** NULL required fields, invalid formats, missing lookups
3. **Census Configuration Errors:** Field mapping issues, sync conditions
4. **Temporary Failures:** Network issues, timeouts (usually retry successfully)

**Action Items:**
- Document new error patterns in this runbook
- Fix data quality issues in source views
- Adjust Census sync configuration if needed

---

## Troubleshooting Guide

### Issue: Census Sync Failing with "Field Validation" Errors

**Symptoms:**
- Census shows errors like "Required field missing: Company_Name__c"
- Sync run has >5% error rate
- Properties with NULL company names failing to sync

**Root Cause:**
- View definition bug (like the one fixed on Jan 9, 2026)
- RDS source data has NULLs for required field
- Field mapping mismatch between Databricks and Salesforce

**Resolution:**
1. Check view definition: `20260105/VIEW2_properties_to_update.sql` and `VIEW1_properties_to_create.sql`
2. Query for NULL company names:
   ```sql
   SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update WHERE company_name IS NULL;
   SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create WHERE company_name IS NULL;
   ```
3. If many NULLs found, review view logic for company name derivation
4. Fix view definition and redeploy
5. Validate fix: `python3 20260109/validate_company_fix.py`
6. Census will retry failed records automatically

**Reference:** See `20260108/FINAL_SESSION_SUMMARY.md` for company name bug case study

---

### Issue: Coverage Dropping Below 90%

**Symptoms:**
- `daily_health_check` shows `coverage_percentage < 90%`
- `rds_to_sf_gap` is increasing
- More properties in RDS than syncing to Salesforce

**Possible Causes:**
1. **RDS added many new properties:** Check `total_rds_properties` trend
2. **Census syncs stopped/paused:** Check Census UI
3. **CREATE queue backed up:** Check `create_queue_count`
4. **View filters too restrictive:** Check view WHERE clauses

**Resolution:**

**If RDS grew significantly:**
- Normal - Census will catch up within 24 hours
- Monitor queue drain rate
- No action needed if queues are processing

**If Census syncs stopped:**
1. Check sync schedule: https://app.getcensus.com/syncs/3394022/settings
2. Verify "Active" and "Scheduled" enabled
3. Check Databricks connection: https://app.getcensus.com/connections/58981
4. Check Salesforce connection: https://app.getcensus.com/destinations/703012
5. Manually trigger sync to test
6. Contact Census support if connection issues

**If queues backed up:**
1. Check for Salesforce API rate limits (Census will show this)
2. Check for Census sync errors (>5% error rate)
3. Consider increasing batch size (test with caution)
4. May need to wait for queues to drain naturally

**If view filters too restrictive:**
1. Review view logic: `20260105/VIEW1_properties_to_create.sql`
2. Check join conditions and WHERE clauses
3. Validate against RDS: Compare counts
4. Adjust if inadvertently filtering valid properties

---

### Issue: Duplicate Properties in Salesforce

**Symptoms:**
- Same property appears multiple times in Product_Property__c
- Census CREATE sync creating duplicates
- External ID matching not working

**Root Cause:**
- External ID field not properly configured in Salesforce
- Salesforce_Property_ID__c field not marked as External ID
- Census sync using wrong matching strategy

**Resolution:**
1. Check Salesforce Object Manager for Product_Property__c
2. Verify `Snappt_Property_ID__c` is marked as External ID
3. Check Census sync settings:
   - Operation: "Update or Create"
   - Match on: "Snappt_Property_ID__c"
4. If duplicates exist:
   ```sql
   -- Find duplicates
   SELECT
     snappt_property_id_c,
     COUNT(*) as duplicate_count
   FROM hive_metastore.salesforce.product_property
   WHERE _fivetran_deleted = false
   GROUP BY snappt_property_id_c
   HAVING COUNT(*) > 1;
   ```
5. Clean up duplicates in Salesforce (keep most recent, delete others)
6. Fix Census sync configuration
7. Verify no new duplicates created

---

### Issue: Census Sync Running Slowly

**Symptoms:**
- Sync runs taking >30 minutes
- Queue not draining quickly
- Large backlog building up

**Possible Causes:**
1. Large batch size causing timeouts
2. Salesforce API rate limits
3. Complex field mappings
4. Network latency

**Resolution:**
1. Check Census sync settings:
   - Batch size (currently 1000 for CREATE, 1000 for UPDATE)
   - Consider reducing to 500 if timeouts occurring
2. Review recent sync runs for patterns:
   - Consistent slow = configuration issue
   - Intermittent slow = rate limits or network
3. Check Salesforce API usage:
   - Setup → System Overview → API Usage
   - If near limit, syncs will slow down
4. Consider scheduling syncs during off-peak hours if rate limits hit
5. Contact Census support for performance optimization advice

---

### Issue: Data Quality Issues (Wrong Values in Salesforce)

**Symptoms:**
- Company names incorrect or NULL
- Feature flags not matching RDS
- Timestamps wrong or missing

**Root Cause:**
- View definition bug
- RDS source data incorrect
- Census field mapping wrong

**Resolution:**
1. Validate data in source:
   ```sql
   -- Check RDS source data
   SELECT
     rds_property_id,
     property_name,
     company_name,
     idv_enabled,
     idv_enabled_at
   FROM crm.sfdc_dbx.rds_properties_enriched
   WHERE rds_property_id = '<property_id>';
   ```

2. Check view transformation:
   ```sql
   -- Check CREATE/UPDATE queue
   SELECT *
   FROM crm.sfdc_dbx.properties_to_update
   WHERE rds_property_id = '<property_id>';
   ```

3. Check Salesforce result:
   ```sql
   -- Check final Salesforce data
   SELECT *
   FROM hive_metastore.salesforce.product_property
   WHERE snappt_property_id_c = '<property_id>';
   ```

4. Compare across all three layers to identify where transformation went wrong
5. Fix view definition if bug found
6. Trigger Census sync to update corrected data
7. Validate with comparison script: `python3 20260105/compare_sf_with_rds.py`

---

## Emergency Procedures

### EMERGENCY: All Syncs Stopped

**Detection:**
- No updates in Salesforce for >2 hours
- Census UI shows "Paused" or errors
- Databricks connection failing

**Immediate Actions:**
1. **Check Census Status Page:** https://status.getcensus.com
   - If Census is down, wait for resolution

2. **Check Databricks Connection:**
   - Login to Census: https://app.getcensus.com
   - Go to Connections → Databricks
   - Test connection
   - If failed, check Databricks token expiration

3. **Check Salesforce Connection:**
   - Go to Destinations → Salesforce
   - Test connection
   - If failed, check Salesforce credentials/permissions

4. **Check Sync Schedules:**
   - Verify syncs not accidentally paused
   - Re-enable if paused

5. **Manually Trigger Sync:**
   ```bash
   # Use Census API to trigger manually
   curl -X POST \
     https://app.getcensus.com/api/v1/syncs/3394022/trigger \
     -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz"
   ```

6. **Escalate:**
   - If cannot resolve in 30 minutes, contact Census support
   - Email: support@getcensus.com
   - Include: Sync IDs, error messages, recent changes

---

### EMERGENCY: Data Quality Drop >10%

**Detection:**
- `daily_health_check` shows sudden increase in NULL values
- Coverage dropped significantly (>10 percentage points)
- Many properties with wrong data

**Immediate Actions:**
1. **PAUSE Census Syncs Immediately:**
   - Go to Census UI
   - Pause both CREATE and UPDATE syncs
   - This prevents spreading bad data

2. **Identify Root Cause:**
   ```sql
   -- Check for view definition changes
   DESCRIBE HISTORY crm.sfdc_dbx.properties_to_update;

   -- Check for NULL spikes
   SELECT
     COUNT(*) as total,
     SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as null_companies,
     SUM(CASE WHEN idv_enabled IS NULL THEN 1 ELSE 0 END) as null_idv,
     SUM(CASE WHEN bank_linking_enabled IS NULL THEN 1 ELSE 0 END) as null_bank
   FROM crm.sfdc_dbx.properties_to_update;
   ```

3. **Check Recent Changes:**
   - Review git commits: `git log --since="24 hours ago" --oneline`
   - Check if views were redeployed
   - Check if RDS schema changed

4. **Rollback if Needed:**
   - If view definition bug, redeploy last known good version
   - If RDS data issue, contact backend team

5. **Validate Fix:**
   - Run validation scripts: `python3 20260109/validate_company_fix.py`
   - Ensure fix resolves issue

6. **Resume Syncs:**
   - After validation passes, resume Census syncs
   - Monitor closely for next 2 hours

7. **Cleanup Bad Data:**
   - If bad data already synced to Salesforce, may need manual cleanup
   - Use comparison scripts to identify affected properties
   - Coordinate with Salesforce admin team

---

### EMERGENCY: View Definition Bug Introduced

**Detection:**
- Sudden increase in sync errors
- Data quality validation failing
- NULL values appearing where they shouldn't

**Example:** Company Name Bug (Jan 9, 2026) - See `20260108/FINAL_SESSION_SUMMARY.md`

**Recovery Procedure:**
1. **Identify the Bug:**
   - Review recent view changes: `git diff HEAD~5 HEAD 20260105/VIEW*.sql`
   - Common issues: Wrong join conditions, missing COALESCE, incorrect WHERE clauses

2. **Fix the View:**
   - Edit view SQL file (e.g., `20260105/VIEW2_properties_to_update.sql`)
   - Correct the logic
   - Test query in Databricks SQL editor first

3. **Redeploy Fixed View:**
   ```sql
   -- In Databricks SQL editor
   -- Copy/paste corrected CREATE OR REPLACE VIEW statement
   -- Execute
   ```

4. **Validate Fix:**
   ```bash
   # Run validation script
   python3 20260109/validate_company_fix.py

   # Should show:
   # - 0 NULLs in company_name (or very few)
   # - All properties passing validation
   ```

5. **Trigger Census Sync:**
   - Census will automatically pick up corrected data
   - Or manually trigger: https://app.getcensus.com/syncs/3394041/trigger

6. **Monitor Recovery:**
   ```sql
   -- Check that Salesforce data is being corrected
   SELECT
     COUNT(*) as total,
     SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) as nulls,
     MAX(last_modified_date) as last_update
   FROM hive_metastore.salesforce.product_property
   WHERE _fivetran_deleted = false;
   ```

7. **Document:**
   - Add bug and fix to this runbook
   - Update `ERROR_RECOVERY_GUIDE.md`
   - Share learnings with team

---

## Census Schedule Verification

**CRITICAL:** Ensure Census syncs are scheduled to run automatically.

### Verification Steps

1. **Log into Census:** https://app.getcensus.com

2. **Check Sync A (CREATE) - 3394022:**
   - Navigate to: https://app.getcensus.com/syncs/3394022/settings
   - Verify:
     - ✅ "Active" toggle is ON (green)
     - ✅ "Run this sync on a schedule" is enabled
     - ✅ Frequency: Every 30 minutes (or as configured)
     - ✅ "Next run" shows a future timestamp
   - If any of the above are disabled/missing, enable them

3. **Check Sync B (UPDATE) - 3394041:**
   - Navigate to: https://app.getcensus.com/syncs/3394041/settings
   - Verify:
     - ✅ "Active" toggle is ON (green)
     - ✅ "Run this sync on a schedule" is enabled
     - ✅ Frequency: Every 15 minutes (or as configured)
     - ✅ "Next run" shows a future timestamp
   - If any of the above are disabled/missing, enable them

4. **Verify Automatic Execution:**
   - Wait for next scheduled run time
   - Check sync history: Should see new runs appearing automatically
   - No manual "Trigger Sync" clicks should be needed

5. **Set Up Census Alerts:**
   - Go to: https://app.getcensus.com/settings/notifications
   - Configure alert rules:
     - ✅ Sync failures (error rate >5%)
     - ✅ Scheduled run misses
     - ✅ Data quality issues
   - Add alert recipients: dane@snappt.com (and data-engineering@snappt.com if available)
   - Test alerts by simulating a failure (optional)

### Monitoring Census Syncs

**Check Sync Status:**
```bash
# Use monitor script
python3 20260108/monitor_sync.py

# Or manually via Census API
curl -X GET \
  "https://app.getcensus.com/api/v1/syncs/3394022/sync_runs?limit=5" \
  -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz"
```

**Expected Output:**
- Recent sync runs show "completed" status
- Error rate <5%
- Records processed matches queue size

---

## Validation Scripts

Use these scripts to validate system health:

### Daily Validation (Automated)
```bash
# Run daily at 3:00 AM (after syncs)
python3 scripts/daily_validation.py
```

**Checks:**
- Coverage hasn't dropped below 90%
- NULL company names <50
- Syncs ran recently (within expected window)
- Alerts if issues found

### Manual Validation

**After View Changes:**
```bash
python3 20260109/validate_company_fix.py
```

**Full Sync Validation:**
```bash
python3 20260109/validate_day3_syncs.py
```

**Compare Salesforce with RDS:**
```bash
python3 20260105/compare_sf_with_rds.py
```

---

## Key Databricks Views

### Production Views (Schema: crm.sfdc_dbx)

1. **`rds_properties_enriched`** - Base view, 20,274 properties from RDS
   - Location: `20260105/VIEW0_rds_properties_enriched.sql`
   - Purpose: Single source of truth for RDS property data

2. **`properties_aggregated_by_sfdc_id`** - 8,629 unique Salesforce IDs
   - Location: `20260105/VIEW3_properties_aggregated_by_sfdc_id.sql`
   - Purpose: Handle 1:many RDS:SFDC mapping

3. **`properties_to_create`** - CREATE queue (new properties)
   - Location: `20260105/VIEW1_properties_to_create.sql`
   - Purpose: Properties not yet in Salesforce (Census Sync A)

4. **`properties_to_update`** - UPDATE queue (existing properties)
   - Location: `20260105/VIEW2_properties_to_update.sql`
   - Purpose: Properties to update in Salesforce (Census Sync B)

5. **`daily_health_check`** - System health monitoring
   - Location: `20260105/VIEW6_monitoring_dashboard.sql`
   - Purpose: Single query for daily operations

6. **`sync_audit_log`** - Historical tracking (audit table)
   - Location: `20260105/VIEW5_sync_audit_log.sql`
   - Purpose: Track sync execution history

### Query Examples

```sql
-- Daily health check
SELECT * FROM crm.sfdc_dbx.daily_health_check;

-- Check CREATE queue
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;

-- Check UPDATE queue
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;

-- Recent sync activity
SELECT
  DATE(last_modified_date) as date,
  COUNT(*) as updates
FROM hive_metastore.salesforce.product_property
WHERE last_modified_date >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY DATE(last_modified_date)
ORDER BY date DESC;

-- Properties with data quality issues
SELECT
  snappt_property_id_c,
  name,
  company_name_c,
  last_modified_date
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false
  AND company_name_c IS NULL
LIMIT 100;
```

---

## Reference Documentation

- **Quick Reference:** `20260105/QUICK_REFERENCE.md` - Census IDs, API commands
- **Project History:** `COMPREHENSIVE_PROJECT_CONTEXT.md` - Full 5-day journey
- **Production Checklist:** `PRODUCTION_READINESS_CHECKLIST.md` - Implementation tasks
- **Final Summary:** `20260108/FINAL_SESSION_SUMMARY.md` - Day 3 results
- **View Definitions:** `20260105/VIEW*.sql` - All 6 production views
- **Validation Scripts:** `20260109/*.py` - Data quality validation

---

## System Architecture Diagram

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐       ┌──────────────────┐
│   RDS       │       │  Databricks  │       │   Census    │       │   Salesforce     │
│ PostgreSQL  │──────>│ Unity Catalog│──────>│  Reverse    │──────>│ Product_Property │
│             │       │              │       │    ETL      │       │    __c (staging) │
└─────────────┘       └──────────────┘       └─────────────┘       └──────────────────┘
     │                      │                       │                       │
     │                      │                       │                       │
   20,274               6 Views:               2 Syncs:                18,722
 properties          - rds_properties       - CREATE (A)            properties
                     - properties_agg       - UPDATE (B)            (93% coverage)
                     - to_create
                     - to_update            Every 15-30 min
                     - daily_health
                     - audit_log
```

---

## Change Log

| Date | Change | Author | Impact |
|------|--------|--------|--------|
| 2026-01-09 | Fixed company name bug in VIEW2 | Dane Rosa | Corrected 9,715 properties |
| 2026-01-09 | Created operations runbook | Dane Rosa + Claude | Team can now operate system |
| 2026-01-05 | Initial views deployed | Dane Rosa + Claude | Pipeline operational |

---

## Next Steps

After completing daily operations successfully for 7 consecutive days:
1. Move to Phase 2: Create monitoring dashboard
2. Set up historical tracking with audit log population
3. Implement automated daily validation script
4. Send stakeholder notification
5. Schedule team training session

---

**Last Updated:** 2026-01-09
**Version:** 1.0
**Owner:** dane@snappt.com
