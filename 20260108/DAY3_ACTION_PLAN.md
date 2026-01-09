# Day 3 Follow-Up Action Plan
**Created:** January 9, 2026
**Status:** Validation Complete - Investigation Phase
**Priority:** Address anomalies before stakeholder notification

---

## Overview

Day 3 production rollout completed successfully with both syncs executing at >99% success rates. However, validation revealed three anomalies requiring investigation before final sign-off:

1. 🔴 **524 records with missing key fields** (2.8% data quality issue)
2. 🟡 **Sync B count higher than expected** (9,141 vs ~7,820)
3. 🟡 **Total records above expected range** (18,722 vs 18,450-18,560)

This action plan prioritizes investigation of these issues while maintaining momentum on operational improvements.

---

## 🔴 CRITICAL PRIORITY (Next 24 Hours)

These items must be completed before notifying stakeholders of Day 3 success.

### 1. Investigate 524 Records with Missing Key Fields
**Priority:** CRITICAL
**Impact:** 2.8% of synced records may have incomplete data
**Owner:** Data Quality team

**Action Steps:**
```sql
-- Query to identify which fields are missing
SELECT
    CASE
        WHEN snappt_property_id_c IS NULL THEN 'missing_snappt_id'
        WHEN name IS NULL THEN 'missing_name'
        WHEN company_name_c IS NULL THEN 'missing_company'
        ELSE 'multiple_missing'
    END as issue_type,
    COUNT(*) as count
FROM crm.salesforce.product_property
WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
  AND _fivetran_deleted = false
  AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
GROUP BY issue_type
```

**Questions to Answer:**
- Which specific fields are most commonly null?
- Are these from Sync A (creates) or Sync B (updates)?
- Does the source RDS data also have these nulls?
- Are these legitimate edge cases or sync errors?

**Expected Outcome:**
- Root cause identified
- Remediation plan created (fix in RDS, re-sync, or document as expected)

---

### 2. Analyze Sync B Count Discrepancy (9,141 vs 7,820)
**Priority:** HIGH
**Impact:** 17% more records updated than planned
**Owner:** Data Engineering team

**Action Steps:**
```sql
-- Check properties_to_update view count as of Jan 9
SELECT COUNT(*) as view_count
FROM crm.sfdc_dbx.properties_to_update;

-- Compare with actual Sync B count
-- Expected: Should match or explain the 9,141 updates
```

**Questions to Answer:**
- What was the exact count in properties_to_update view on Jan 9?
- Did the view data change between dry run (Jan 8) and production (Jan 9)?
- Did automated Census syncs run in addition to manual execution?
- Were there additional filters/conditions in Census we didn't account for?

**Expected Outcome:**
- Source of additional ~1,400 records identified
- Confirm whether this is expected behavior or configuration issue

---

### 3. Check Census Sync Logs for Jan 8-9
**Priority:** HIGH
**Impact:** Understand actual execution vs expected
**Owner:** Operations team

**Action Steps:**
- Log into Census UI: https://app.getcensus.com
- Review sync history for:
  - Sync A (3394022): https://app.getcensus.com/syncs/3394022
  - Sync B (3394041): https://app.getcensus.com/syncs/3394041
- Check for:
  - Multiple executions on same day
  - Automated schedule runs vs manual runs
  - Record counts per execution
  - Error details for failed records

**Questions to Answer:**
- How many times did each sync run on Jan 8-9?
- Were there automated syncs in addition to manual execution?
- What were the exact record counts per run?
- What caused the 5 failed creates and 6 invalid updates?

**Expected Outcome:**
- Complete timeline of sync executions
- Explanation for count differences
- Details on failed records

---

## 🟡 HIGH PRIORITY (This Week)

These items validate the success of Day 3 and address known gaps.

### 4. Re-run Mismatch Analysis (RDS vs Salesforce)
**Priority:** HIGH
**Impact:** Confirms Day 3 achieved its goal (fix 772 mismatches)
**Owner:** Data Engineering team

**Action Steps:**
- Re-run the comparison query from before Day 3
- Compare RDS property_features vs Salesforce product_property
- Count current mismatches
- Calculate: Original (1,072) - Fixed = Remaining

**Expected Results:**
- Original mismatches: 1,072
- Expected fixes from Day 3: 772
- Expected remaining: ~300 (orphaned properties)
- Actual remaining: TBD

**Success Criteria:**
- ≤300 mismatches remaining
- 72%+ of original mismatches resolved

---

### 5. Query properties_to_update View (Jan 9 State)
**Priority:** HIGH
**Impact:** Reconciles Sync B count discrepancy

**Query:**
```sql
-- Current view count
SELECT COUNT(*) as current_count
FROM crm.sfdc_dbx.properties_to_update;

-- Sample records to verify data quality
SELECT * FROM crm.sfdc_dbx.properties_to_update LIMIT 10;
```

**Expected Outcome:**
- If view shows ~9,141: Explains Sync B count (source was accurate)
- If view shows ~7,820: Suggests view data changed or multiple syncs ran

---

### 6. Verify Total Record Count Reconciliation
**Priority:** MEDIUM
**Impact:** Understand why total is 18,722 vs expected 18,450-18,560

**Calculation:**
```
Before Day 3:  17,875 records
Sync A creates: +574
Expected total: 18,449

Actual total:   18,722
Difference:     +273
```

**Questions:**
- Are there 273 duplicate records?
- Did Fivetran sync bring in additional records?
- Were records created outside of our syncs?

---

### 7. Investigate 5 Failed CREATE Records
**Priority:** MEDIUM
**Impact:** Understand 0.7% error rate from Sync A

**From Census logs, identify:**
- Which 5 property IDs failed
- Error messages from Salesforce
- Root cause (validation rule, missing field, duplicate, etc.)
- Whether these need manual remediation

---

### 8. Investigate 6 Invalid UPDATE Records
**Priority:** MEDIUM
**Impact:** Understand 0.1% error rate from Sync B dry run

**Similar to #7:**
- Identify the 6 property IDs
- Error messages
- Root cause
- Remediation plan

---

## 🟢 MEDIUM PRIORITY (Next 2 Weeks)

These items improve operational maturity and prevent future issues.

### 9. Analyze 300 Orphaned Properties
**Priority:** MEDIUM
**Impact:** Properties in RDS but not syncing to Salesforce

**Investigation:**
- Which properties are in RDS but not in properties_to_create/update views?
- Why aren't they included? (filters, deleted records, data quality issues)
- Should they be synced or are they legitimately excluded?

---

### 10. Verify Census Automated Schedules
**Priority:** MEDIUM
**Impact:** Ensures ongoing syncs happen automatically

**Check:**
- Sync A schedule: Every 15 minutes? Daily? Manual only?
- Sync B schedule: Every 30 minutes? Daily? Manual only?
- Are schedules enabled or paused?

**Recommended:**
- Sync A (CREATE): Daily or manual (creates are one-time)
- Sync B (UPDATE): Every 30-60 minutes (keeps data fresh)

---

### 11. Create Monitoring Dashboard
**Priority:** MEDIUM
**Impact:** Proactive visibility into sync health

**Metrics to Track:**
- Daily sync success rate
- Record counts (creates, updates, failures)
- Data quality metrics (nulls, mismatches)
- Sync duration trends
- Error rate trends

**Tools:** Databricks SQL Dashboard, Looker, or Census built-in monitoring

---

### 12. Set Up Automated Alerts
**Priority:** MEDIUM
**Impact:** Immediate notification of sync issues

**Alerts to Configure:**
- Sync failure (>5% error rate)
- Sync didn't run (missed schedule)
- Data quality degradation (>100 nulls)
- Unusual record counts (>20% variance)

**Channels:** Email, Slack, PagerDuty

---

### 13. Write Operational Runbook
**Priority:** MEDIUM
**Impact:** Team can handle issues without escalation

**Sections:**
1. Architecture overview
2. Normal operation expectations
3. Common issues and solutions
4. How to run manual syncs
5. How to investigate failures
6. Rollback procedures
7. Contact information

---

### 14. Rename Census Datasets
**Priority:** LOW
**Impact:** Clarity (datasets labeled "pilot" but contain prod data)

**Changes:**
- "pilot_create" → "prod_create" or "properties_to_create"
- "pilot_update" → "prod_update" or "properties_to_update"

---

### 15. Document Actual Execution Timeline
**Priority:** LOW
**Impact:** Historical accuracy

**Update SESSION_SUMMARY.md with:**
- Sync A: January 8, 2026, ~18:00 UTC
- Sync B: January 9, 2026, time TBD
- Why 1-day gap? (manual execution, scheduling)

---

## 📢 STAKEHOLDER COMMUNICATION

### 16. Prepare Final Stakeholder Notification
**Priority:** HIGH (after critical items complete)
**Impact:** Inform teams of new capabilities

**Draft Message:**

```
Subject: Property Feature Flag Sync - Production Rollout Complete ✅

Team,

The RDS → Salesforce property sync has been successfully deployed to production:

✅ Results:
- 574 new properties added to Salesforce (Jan 8)
- 9,141 existing properties updated with current feature flags (Jan 9)
- 99%+ success rate on both operations
- Census automated syncs now running [schedule TBD]

🔍 Open Items:
- Investigating 524 records with data quality issues (2.8%)
- Validating higher-than-expected update count
- Follow-up report in 48 hours with resolution

📊 Feature Flag Coverage:
- Income Verification: 62.6% of properties
- Fraud Detection: 98.3% of properties
- Connected Payroll: 37.9% of properties
- ID Verification: 30.4% of properties
- Bank Linking: 17.3% of properties

🎯 Impact:
- Sales team can now see all properties with features
- CS team has accurate customer feature data
- Billing reflects reality
- No more manual interventions needed

❓ Questions?
Contact [your name/team]

More details: [link to validation report]
```

---

### 17. Notify Stakeholders
**Priority:** HIGH (after critical items + draft approval)

**Distribution List:**
- Sales Ops team (new properties available)
- CS team (accurate feature data)
- Salesforce Admin (ready for downstream sync)
- Data Engineering team (pipeline live)
- Leadership (project completion)

---

## Timeline Summary

```
┌─────────────────────────────────────────────────────────────┐
│ DAY 1-2 (Next 24-48 Hours) - CRITICAL                      │
├─────────────────────────────────────────────────────────────┤
│ ✓ Investigate 524 missing fields                            │
│ ✓ Analyze Sync B count (9,141 vs 7,820)                    │
│ ✓ Check Census logs                                         │
│ ✓ Re-run mismatch analysis                                  │
│ ✓ Query properties_to_update view                           │
│ → DECISION POINT: Approve stakeholder notification          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEEK 1 (Days 3-7) - HIGH PRIORITY                          │
├─────────────────────────────────────────────────────────────┤
│ ✓ Investigate failed records (5+6)                          │
│ ✓ Verify Census schedules                                   │
│ ✓ Reconcile total count                                     │
│ ✓ Send stakeholder notification                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEEKS 2-3 - OPERATIONAL MATURITY                           │
├─────────────────────────────────────────────────────────────┤
│ ✓ Create monitoring dashboard                               │
│ ✓ Set up automated alerts                                   │
│ ✓ Write operational runbook                                 │
│ ✓ Analyze orphaned properties                               │
│ ✓ Rename Census datasets                                    │
│ ✓ Document timeline                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

**Critical items (1-3) complete when:**
- [ ] Root cause of 524 missing fields identified with remediation plan
- [ ] Sync B count discrepancy (9,141 vs 7,820) explained
- [ ] Census logs reviewed and execution timeline documented

**High priority items (4-8) complete when:**
- [ ] Mismatch analysis shows ≥72% of issues resolved (≤300 remaining)
- [ ] Total record count reconciled and explained
- [ ] Failed/invalid records investigated with remediation plan

**Stakeholder notification ready when:**
- [ ] All critical items complete
- [ ] Final metrics validated
- [ ] Draft message approved by leadership
- [ ] Known issues documented with resolution timeline

**Operational maturity achieved when:**
- [ ] Monitoring dashboard live
- [ ] Automated alerts configured
- [ ] Operational runbook published
- [ ] Team trained on new system

---

## Decision Points

### Decision 1: Proceed with Stakeholder Notification?
**Timing:** After completing critical items 1-3
**Decision Maker:** Project Lead / Data Engineering Manager

**Criteria:**
- Critical data quality issues understood with plan
- Count discrepancies explained satisfactorily
- No major concerns requiring rollback

**Options:**
1. ✅ **Proceed** - Issues are minor/expected, notify stakeholders
2. ⏸️ **Pause** - Need more investigation before communication
3. ⚠️ **Rollback** - Critical issues found requiring sync reversal

---

### Decision 2: Automated Schedule Configuration?
**Timing:** After verifying current schedule (item 10)
**Decision Maker:** Operations team

**Options:**
1. **Keep current** - If already optimal
2. **Enable/adjust** - Set to every 30-60 minutes
3. **Manual only** - If data changes infrequently

**Recommendation:** Every 30-60 minutes for Sync B (updates)

---

## Resources

### Documentation
- Day 3 Validation Results: `20260108/DAY3_VALIDATION_RESULTS.md`
- Session Summary: `20260108/SESSION_SUMMARY.md`
- Validation Queries: `databricks_validation_queries.sql`

### Scripts
- Main Validation: `validate_day3_syncs.py`
- Timing Analysis: `check_sync_b_timing.py`
- Combined Analysis: `validate_both_days.py`

### Census URLs
- Sync A (CREATE): https://app.getcensus.com/syncs/3394022
- Sync B (UPDATE): https://app.getcensus.com/syncs/3394041

### Databricks
- Warehouse: fivetran (95a8f5979c3f8740)
- Schema: crm.salesforce, crm.sfdc_dbx, rds.pg_rds_public

---

## Notes

- This plan assumes Day 3 execution was fundamentally successful
- Priority may shift based on findings from critical investigations
- Timeline is aggressive but achievable with focused effort
- Some items can be parallelized (e.g., monitoring + runbook)
- Stakeholder notification should wait for critical items completion

---

**Created by:** Claude Sonnet 4.5
**Date:** January 9, 2026
**Version:** 1.0
**Status:** Active - Awaiting execution
