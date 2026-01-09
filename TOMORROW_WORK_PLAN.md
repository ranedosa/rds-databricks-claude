# Work Plan for Tomorrow - RDS to Salesforce Sync Production Readiness

**Date Created:** January 9, 2026
**Session Summary:** Production readiness implementation and view bug fixes

---

## 🎯 Current State Summary

### ✅ What We Completed Today

**1. Fixed Critical View Bugs**
- **Issue Found:** Views were using wrong catalog (`hive_metastore` instead of `crm.salesforce`)
- **Issue Found:** Views were joining on wrong field (`sf_property_id_c` instead of `snappt_property_id_c`)
- **Result:** Queues showed 8,396+ properties when only 1,182 actually needed syncing
- **Fixed Views:**
  - `crm.sfdc_dbx.properties_to_create` - Now correctly identifies 332 properties missing from Salesforce
  - `crm.sfdc_dbx.properties_to_update` - Now correctly identifies 851 properties with actual differences
  - Added difference detection logic to UPDATE view (compares all fields)

**2. Validated All Data**
- ✅ All 332 CREATE queue properties match RDS source
- ✅ All 851 UPDATE queue properties match RDS source
- ✅ Zero NULL or empty company names found
- ✅ Full validation passed: 1,182 properties ready to sync

**3. Updated Monitoring for Daily Sync Cadence**
- Changed thresholds from 15-30 min syncs to daily syncs:
  - CREATE: 🔴 High >500 (was 100), 🟡 Moderate 300-500 (was 50-100)
  - UPDATE: 🔴 High >2000 (was 1000), 🟡 Moderate 1000-2000 (was 500-1000)
  - Sync recency: 🔴 >25 hours (was 2 hours), 🟡 20-25 hours (new)
- Added `hours_since_last_sync` column to monitoring view

**4. Enabled Census Syncs on Daily Schedule**
- **Status:** Both syncs enabled in Census, set to run every 24 hours
- **Important:** Syncs are PAUSED until you manually resume them
- **Schedule:** Daily cadence (you set the time in Census)
- **Next sync:** Check Census UI for "Next run" timestamp

**5. Set Up Automated Alerting**
- ✅ Databricks SQL Alert created
- ✅ Checks for 🔴 critical issues every 4 hours
- ✅ Email notifications to dane@snappt.com
- ✅ Alert triggers when: sync overdue, high backlog, or critical status

**6. Created Dashboard Resources**
- ✅ Databricks notebook with all tile queries: `Dashboard_Tiles_Notebook.py`
- ✅ Reference documentation: `DASHBOARD_TILES_REFERENCE.md`
- ✅ 10 tiles ready to add (4 more need audit log data)
- ⏳ Dashboard tiles not yet added to Databricks dashboard

---

## ⚠️ Critical Context: Why We Were Cautious

**The Company Name Bug Incident**
- Earlier in the project, a view bug caused 9,715 properties to have incorrect company names synced to Salesforce
- This is why we thoroughly validated all data before enabling syncs
- All validation passed - data is confirmed correct this time

**Current Safety Measures:**
- ✅ All 1,182 properties validated against RDS source
- ✅ Daily sync cadence (not real-time) gives time to catch issues
- ✅ Automated monitoring and alerts configured
- ✅ Views use correct catalog and join fields

---

## 🔄 Current System Status

### Census Syncs
**Status:** Configured but PAUSED

**Sync A (CREATE) - ID: 3394022**
- Queue: 332 properties
- Purpose: Create new properties in Salesforce that don't exist yet
- Schedule: Daily (every 24 hours)
- URL: https://app.getcensus.com/syncs/3394022

**Sync B (UPDATE) - ID: 3394041**
- Queue: 851 properties
- Purpose: Update existing properties with changes from RDS
- Schedule: Daily (every 24 hours)
- URL: https://app.getcensus.com/syncs/3394041

**To Resume Syncs:**
1. Go to Census URLs above
2. Click "Resume" or toggle "Active" to ON
3. Verify "Next run" timestamp appears
4. Syncs will run automatically at scheduled time

### Monitoring
**Last Sync:** January 9, 2026 at 4:34 PM (before fixes)
**Queue Status:** 🟡 Moderate (CREATE 332, UPDATE 851)
**Hours Since Last Sync:** ~3 hours as of 7:30 PM
**Alert Status:** ✅ Working, checks every 4 hours

### Data Quality
**Total Properties in Salesforce:** 18,722
**Coverage:** 93%+
**NULL Company Names:** <50 (excellent)
**Data Quality:** 95%+ (excellent)

---

## 📋 Tomorrow's Work - Remaining Tasks

### Priority 1: Monitor First Sync (CRITICAL - Do This First)

**When:** After Census runs the first daily sync (check "Next run" time in Census)

**Steps:**
1. **Check sync completed successfully:**
   ```sql
   SELECT * FROM crm.sfdc_dbx.sync_health_monitor;
   ```
   - Expected: Queues should be near 0
   - Expected: Status should be ✅ Healthy

2. **Verify data quality maintained:**
   ```sql
   SELECT COUNT(*)
   FROM crm.salesforce.product_property
   WHERE _fivetran_deleted = FALSE
     AND company_name_c IS NULL;
   ```
   - Expected: Still <50 NULL company names

3. **Spot-check created properties:**
   - Pick 5 properties from CREATE queue (use list from validation)
   - Search in Salesforce by property name or ID
   - Verify company name is correct
   - Verify feature flags match RDS

4. **Check Census sync history:**
   - Go to each sync in Census UI
   - Check "Run History" tab
   - Verify "Success" status
   - Check error rate <5%

**If any issues found:** Immediately pause syncs and investigate using `OPERATIONS_RUNBOOK.md`

---

### Priority 2: Complete Dashboard Setup (30-60 min)

**Current:** Dashboard exists but only has a few tiles

**Goal:** Add 10 core visualization tiles

**Resources:**
- Databricks notebook: `/Users/danerosa/rds_databricks_claude/Dashboard_Tiles_Notebook.py`
- Reference doc: `DASHBOARD_TILES_REFERENCE.md`
- Your dashboard: https://dbc-9ca0f5e0-2208.cloud.databricks.com/sql/dashboardsv3/01f0ed94192917438bfcd41de3134c5d

**10 Tiles to Add (in order of importance):**
1. ✅ System Status (Counter) - Health indicator
2. ✅ Coverage % (Counter) - Current coverage
3. ✅ Queue Sizes (Bar Chart) - CREATE/UPDATE backlogs
4. ✅ Recent Activity (Counter) - Today's syncs
7. ✅ Data Quality Metrics (Table) - NULL counts, quality %
8. ✅ Feature Adoption (Bar Chart) - Which features enabled
11. ✅ Sync Health Monitor (Table) - Real-time health
13. ✅ Last Sync Times (Counter) - When syncs last ran
14. ✅ Missing Data (Counter) - Properties with issues
12. Top Properties (Table) - Most features enabled

**How to Add:**
1. Import `Dashboard_Tiles_Notebook.py` into Databricks
2. For each tile, copy SQL from notebook cell
3. In dashboard, click "Add" → "Visualization"
4. Paste SQL, configure viz type (noted in notebook)
5. Add to dashboard

**Alternative (Faster):** Add just 4 essential tiles:
- System Status, Coverage %, Queue Sizes, Sync Health Monitor

---

### Priority 3: Set Up Audit Log Population (20 min)

**Purpose:** Capture daily snapshots for historical tracking and trend analysis

**Steps:**

1. **Deploy the SQL view (already created):**
   - Open Databricks SQL Editor
   - Copy contents of `sql/populate_audit_log.sql`
   - Run to test (should insert 1 row)

2. **Schedule as Databricks Job:**
   - Go to: Databricks → SQL → Jobs
   - Create new job: "Daily Audit Log Population"
   - Query: Use `populate_audit_log.sql`
   - Schedule: Daily at 11:59 PM PT (Cron: `59 23 * * *`)
   - Timeout: 5 minutes
   - Retry: 3 times

3. **Verify first snapshot:**
   ```sql
   SELECT * FROM crm.sfdc_dbx.sync_audit_log
   WHERE audit_id = CONCAT('daily_snapshot_', DATE_FORMAT(CURRENT_DATE(), 'yyyyMMdd'));
   ```

**After this runs for a few days:** Add 4 trend tiles to dashboard (coverage trend, sync activity, feature trends, queue trends)

---

### Priority 4: Schedule Daily Validation Script (25 min)

**Purpose:** Automated daily checks for data quality issues

**Steps:**

1. **Test the script locally:**
   ```bash
   cd /Users/danerosa/rds_databricks_claude
   python3 scripts/daily_validation.py --dry-run --verbose
   ```
   - Should show 4 checks: Coverage, Data Quality, Sync Recency, Queue Sizes
   - All should pass ✅

2. **Choose scheduling method:**

   **Option A: Databricks Notebook (Recommended)**
   - Create new notebook in Databricks
   - Copy contents of `scripts/daily_validation.py`
   - Add cell at top: `%pip install databricks-sql-connector`
   - Schedule as Databricks Job: Daily at 3:00 AM PT
   - Configure alerts on failure

   **Option B: Cron Job (if you have server access)**
   ```bash
   # Add to crontab
   0 3 * * * cd /Users/danerosa/rds_databricks_claude && python3 scripts/daily_validation.py
   ```

3. **Configure alerts:**
   - Script exits with code 1 if validation fails
   - Databricks Job can email on failure
   - Or script can send email/Slack (placeholder code exists)

---

### Priority 5: Send Stakeholder Notification (30 min)

**When:** After first sync proves successful

**Purpose:** Inform teams that the system is production-ready

**Steps:**

1. **Review and customize:**
   - Check if `STAKEHOLDER_NOTIFICATION.md` exists (might need to create)
   - Add dashboard URL
   - Add final metrics from first sync

2. **Draft email:**

   **To:**
   - Sales Operations
   - Customer Success
   - Salesforce Admin team
   - Data Engineering team
   - Leadership

   **Subject:** RDS to Salesforce Property Sync - Production Ready ✅

   **Key Points to Include:**
   - System now running on daily automated schedule
   - 93%+ coverage (18,722 properties)
   - Automated monitoring and alerts configured
   - Dashboard URL for self-service monitoring
   - Operations runbook available: `OPERATIONS_RUNBOOK.md`
   - Contact: dane@snappt.com

3. **Send and monitor for questions**

---

## 📁 Key Files Reference

### Documentation
- **`OPERATIONS_RUNBOOK.md`** - Complete operations guide (daily checks, troubleshooting, emergencies)
- **`COMPREHENSIVE_PROJECT_CONTEXT.md`** - Full project history (5-day journey)
- **`PRODUCTION_READINESS_CHECKLIST.md`** - Original checklist
- **`PRODUCTION_IMPLEMENTATION_SUMMARY.md`** - What we built today
- **`TOMORROW_WORK_PLAN.md`** - This file

### SQL Files
- **`sql/sync_health_monitor.sql`** - Real-time monitoring view (deployed)
- **`sql/populate_audit_log.sql`** - Daily snapshot insertion (ready to schedule)
- **`sql/dashboard_tiles.sql`** - All 14 dashboard queries (reference)

### Scripts
- **`scripts/daily_validation.py`** - Automated validation (ready to schedule)
- **`scripts/README.md`** - Script documentation

### Dashboard Resources
- **`Dashboard_Tiles_Notebook.py`** - Databricks notebook with all tile queries
- **`DASHBOARD_TILES_REFERENCE.md`** - Detailed reference with all queries

### View Definitions (Fixed Today)
- **`20260105/VIEW3_properties_to_create_CORRECTED.sql`** - CREATE queue view
- **`20260105/VIEW4_properties_to_update_CORRECTED.sql`** - UPDATE queue view

### Config
- **`config/.databrickscfg`** - Databricks credentials
- **`config/.env`** - Environment variables

---

## 🚨 Important Reminders

### Before Enabling Syncs
- ✅ Data validated (DONE - all 1,182 properties checked)
- ✅ Views fixed (DONE - correct catalog and joins)
- ✅ Monitoring configured (DONE - alerts every 4 hours)
- ⏳ First sync needs to complete successfully
- ⏳ Spot-check results after first sync

### After First Sync
- Verify queues drained to near 0
- Check data quality maintained (NULL company names <50)
- Spot-check 5-10 created properties in Salesforce
- Review Census sync history for errors
- Send stakeholder notification

### Daily Operations (5 min)
```sql
-- Run this every morning
SELECT * FROM crm.sfdc_dbx.daily_health_check;
```
- Coverage should stay >90%
- NULL company names should stay <50
- Queues should be small (<300 CREATE, <1000 UPDATE)

### If Issues Occur
1. **Pause syncs immediately** in Census
2. Check `OPERATIONS_RUNBOOK.md` for troubleshooting
3. Run validation queries to identify issue
4. Don't resume until issue is resolved

---

## 📊 Success Metrics

**System is fully production-ready when:**
- ✅ First daily sync completes successfully (0 Tomorrow)
- ✅ Data quality maintained >95% (Tomorrow)
- ✅ Coverage stable at 93%+ (Tomorrow)
- ✅ Monitoring dashboard complete (Tomorrow)
- ✅ Audit log populating daily (Tomorrow)
- ✅ Daily validation running automatically (Tomorrow)
- ✅ Stakeholders notified (Tomorrow)
- ✅ 7 consecutive days with no issues (Next week)

---

## 🔍 Quick Reference Commands

### Check System Health
```sql
SELECT * FROM crm.sfdc_dbx.sync_health_monitor;
```

### Check Daily Health
```sql
SELECT * FROM crm.sfdc_dbx.daily_health_check;
```

### Check Queue Counts
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;  -- CREATE queue
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;  -- UPDATE queue
```

### Check Data Quality
```sql
SELECT COUNT(*)
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = FALSE AND company_name_c IS NULL;
```

### Run Daily Validation
```bash
cd /Users/danerosa/rds_databricks_claude
python3 scripts/daily_validation.py --verbose
```

---

## 📞 Support Resources

**Operations Guide:** `OPERATIONS_RUNBOOK.md`
- Daily operations (5 min routine)
- Troubleshooting scenarios
- Emergency procedures

**Quick Commands:** `20260105/QUICK_REFERENCE.md`
- Census URLs and IDs
- Common queries

**Census Support:** support@getcensus.com
**Primary Contact:** dane@snappt.com

---

## ✅ Tomorrow's Checklist

**Morning (First Thing):**
- [ ] Check if Census syncs ran overnight
- [ ] Verify syncs completed successfully
- [ ] Run health check query
- [ ] Spot-check 5 created properties in Salesforce
- [ ] Verify data quality maintained

**If First Sync Successful:**
- [ ] Add dashboard tiles (30-60 min)
- [ ] Schedule audit log population (20 min)
- [ ] Schedule daily validation script (25 min)
- [ ] Send stakeholder notification (30 min)

**If First Sync Had Issues:**
- [ ] Pause syncs immediately
- [ ] Review Census errors
- [ ] Check OPERATIONS_RUNBOOK.md troubleshooting
- [ ] Run validation queries
- [ ] Fix issues before resuming

**End of Day:**
- [ ] Verify all automation is scheduled
- [ ] Check monitoring dashboard working
- [ ] Review audit log has first snapshot
- [ ] Confirm alerts are configured

---

## 🎯 The Big Picture

**What We're Building:**
A production-grade, automated property sync system from RDS to Salesforce with:
- ✅ Data validated and accurate
- ✅ Daily automated syncs
- ✅ Real-time monitoring and alerts
- ⏳ Visual dashboard (tomorrow)
- ⏳ Historical tracking (tomorrow)
- ⏳ Automated daily validation (tomorrow)
- ⏳ Stakeholder communication (tomorrow)

**Timeline:**
- **Today (Jan 9):** Fixed bugs, validated data, enabled syncs, configured alerts
- **Tomorrow (Jan 10):** Monitor first sync, complete dashboard, finish automation
- **Next Week:** 7-day validation period, then fully production-ready

**Estimated Time Tomorrow:** 2-3 hours (assuming first sync is successful)

---

**Last Updated:** January 9, 2026, 7:45 PM
**Status:** Ready for tomorrow's work
**Next Session:** Monitor first sync, complete dashboard and automation

---

## Quick Start for Tomorrow

1. **Check Census:** https://app.getcensus.com/syncs
2. **Run:** `SELECT * FROM crm.sfdc_dbx.sync_health_monitor;`
3. **If healthy:** Continue with dashboard and automation setup
4. **If issues:** Pause syncs, troubleshoot using OPERATIONS_RUNBOOK.md

**Good luck! 🚀**
