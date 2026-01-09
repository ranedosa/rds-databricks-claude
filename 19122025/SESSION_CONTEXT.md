# Session Context - December 19, 2025
## Salesforce Feature Sync Investigation & Duplicate sfdc_id Cleanup

**Session Duration:** ~6 hours
**Status:** Investigation Complete, Ready for Cleanup Execution
**Next Session:** Review Phase 1 script and execute cleanup

---

## WHAT WE INVESTIGATED

### Initial Problem Statement
**From Ella:** "Park Kennedy (sfdc_id: a01Dn00000HHUanIAH) has features turned on in RDS but they are not syncing to Salesforce"

### Investigation Scope
1. Analyzed Databricks job 1061000314609635 (daily Salesforce sync workflow)
2. Investigated Park Kennedy specifically
3. Discovered systemic issue affecting 2,541+ properties
4. Created comprehensive cleanup plan

---

## KEY FINDINGS

### Park Kennedy Root Cause (Specific)

**Problem:** THREE "Park Kennedy" properties in RDS, TWO share same sfdc_id:

| Property ID | Name | Status | SFDC ID | IDV | Features |
|------------|------|--------|---------|-----|----------|
| `5eec38f2-85c9...` | Park Kennedy | **DISABLED** | a01Dn00000HHUanIAH | false | None |
| `94246cbb-5eec...` | Park Kennedy | **ACTIVE** | a01Dn00000HHUanIAH | true | 4 enabled |
| `c686cc05-e207...` | Park Kennedy - Guarantor | DISABLED | NULL | false | None |

**Why Features Don't Sync:**
1. ACTIVE property has sfdc_id populated → Filtered from "new properties" workflow
2. Salesforce has DISABLED property → Feature sync join fails
3. ACTIVE property with 4 features (IV, Bank, Payroll, IDV) has nowhere to sync

**Features Enabled on ACTIVE Property (not syncing):**
- ✅ Income Verification (2025-11-10)
- ✅ Bank Linking (2025-11-10)
- ✅ Payroll Linking (2025-11-10)
- ✅ Identity Verification (2025-11-10)

---

### Systemic Issue (Massive Scale)

**Scope:**
- **2,541 duplicate sfdc_id groups** found
- **6,068 properties affected**
  - 3,391 DISABLED
  - 2,677 ACTIVE
- **~2,500 ACTIVE properties blocked** from syncing features

**Patterns Discovered:**

1. **ACTIVE + DISABLED pairs (85%)** - Most common
   - Example: New property created, old kept sfdc_id
   - Resolution: Clear sfdc_id from DISABLED

2. **Multiple DISABLED + 1 ACTIVE (10%)** - Migration history
   - Example: Regal Vista (4 properties: 1 ACTIVE, 3 DISABLED)
   - Resolution: Clear sfdc_id from all DISABLED

3. **TWO ACTIVE properties (5%)** - Requires manual review
   - Example: "Bell Lighthouse Point" + "Advenir Lighthouse Point"
   - Could be: name change, mgmt change, or truly different properties
   - Resolution: Case-by-case investigation needed

4. **All DISABLED (rare)** - Legacy cleanup
   - Resolution: Clear sfdc_id from all but newest

---

## THE SYNC WORKFLOW (How it Works)

### Job: 1061000314609635 - "00_sfdc_dbx_v2"
**Schedule:** Daily at 6:09 AM ET

**Task Flow:**
1. **new_properties_with_features** → Syncs NEW properties with features
   - Filters: `WHERE sfdc_id IS NULL AND status = 'ACTIVE'`
   - **Problem:** Properties with sfdc_id are filtered out

2. **check_fivetran_run** → Ensures fresh Salesforce data
   - Validates Fivetran ran within 50 minutes

3. **product_property_feature_sync** → Updates features on EXISTING properties
   - Join: `pp.sf_property_id_c = p.sfdc_id`
   - **Problem:** Join fails when sf_property_id_c is NULL

4. **product_property_activity** → Syncs usage metrics
5. **product_property_user** → Syncs user relationships
6. **product_user** → Syncs user data
7. **trigger_census** → Triggers Census API syncs

**Why Duplicates Break the Workflow:**
- ACTIVE property has sfdc_id → Can't use "new properties" path
- Wrong property in Salesforce → "feature sync" join fails
- Result: Features have nowhere to sync to

---

## FILES CREATED (All in /19122025/)

### Investigation & Analysis
1. **PARK_KENNEDY_DIAGNOSTIC.md** - Initial diagnostic with 6 root causes
2. **PARK_KENNEDY_ROOT_CAUSE.md** - Detailed Park Kennedy analysis
3. **Park_Kennedy_Investigation_Report.ipynb** - Full investigation notebook (Databricks-ready)
4. **Park_Kennedy_Investigation_Report.py** - Python version of investigation

### Duplicate Detection
5. **Find_Duplicate_SFDC_IDs.ipynb** - Databricks notebook with 5 queries
6. **find_duplicate_sfdc_ids.sql** - Quick detection query
7. **find_duplicate_sfdc_ids_summary.sql** - Summary query

### Analysis & Strategy
8. **DUPLICATE_CLEANUP_ANALYSIS.md** ⭐ - Complete technical analysis (10K words)
9. **DUPLICATE_SFDC_ID_RESOLUTION_STRATEGY.md** - Resolution strategy guide
10. **DUPLICATE_CLEANUP_SUMMARY.md** ⭐ - Executive summary (START HERE)

### Cleanup Scripts (Ready to Execute)
11. **Phase1_Cleanup_Script.sql** ⭐ - READY TO RUN
    - Clears sfdc_id from ~3,400 DISABLED properties
    - Includes preview, backup, execution, verification, rollback steps
    - **Safe to run** - only touches DISABLED properties

12. **Phase2_Manual_Review_List.sql** - Queries for edge cases
    - Identifies 150-200 properties needing manual review
    - Includes priority ranking, categorization
    - Export format for spreadsheet review

### Investigation Scripts (Used During Analysis)
13. **investigate_park_kennedy.py** - Databricks notebook (imported)
14. **investigate_api.py** - Python script using Databricks REST API
15. **investigate_live.py** - Python script using SQL connector
16. **run_park_kennedy_investigation.py** - Full investigation runner

### Data Exports (Query Results)
17. **notebook_output_sfdc_dupes/** - All duplicate analysis results
    - sfdc_id_duplicate_count.csv (2,542 rows) - Summary of all duplicates
    - cell2.csv (6,069 rows) - Detailed property list
    - cell3.csv - Status breakdown (3,391 DISABLED, 2,677 ACTIVE)
    - cell4.csv (6,104 rows) - Salesforce sync status
    - cell5.csv (6,069 rows) - Feature enablement analysis

---

## DATABRICKS ASSETS CREATED

### Notebooks (Already Imported)
1. **Path:** `/Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs`
   - 5 diagnostic queries
   - Status breakdowns
   - Salesforce sync checks
   - Feature enablement analysis

2. **Path:** `/Users/dane@snappt.com/investigate_park_kennedy`
   - 7-step investigation
   - All Park Kennedy queries
   - Validation queries

### Key Tables/Views in Databricks
- `crm.sfdc_dbx.product_property_w_features` - Aggregated feature data
- `crm.sfdc_dbx.product_property_feature_sync` - Properties needing updates
- `crm.sfdc_dbx.new_properties_with_features` - New properties to sync
- `crm.salesforce.product_property` - Salesforce data (via Fivetran)
- `rds.pg_rds_public.properties` - Source RDS data
- `rds.pg_rds_public.property_feature_events` - Feature event log

---

## CURRENT STATE

### What We Know
✅ Root cause identified (duplicate sfdc_ids blocking sync)
✅ Scope quantified (2,541 groups, 6,068 properties)
✅ Patterns categorized (85% clear resolution, 15% needs review)
✅ Impact assessed (~2,500 ACTIVE properties blocked)
✅ Solution designed (3-phase cleanup plan)
✅ Scripts written and ready to execute
✅ Verification queries prepared
✅ Rollback procedure documented

### What We Don't Know Yet
❓ Exact count of P1 cases (ACTIVE with features, not in SF) - estimated 200-500
❓ Business context for TWO ACTIVE cases - requires stakeholder input
❓ Whether staging environment available for testing
❓ Approval timeline for Phase 1 execution

### Decisions Made
✅ Use 3-phase approach (automated → manual → prevention)
✅ Start with DISABLED properties only (low risk)
✅ Require manual review for ACTIVE+ACTIVE cases
✅ Clear sfdc_id rather than delete properties
✅ Create backups before execution

### Decisions Pending
❓ Approval to execute Phase 1 cleanup
❓ Who will do Phase 2 manual review
❓ When to add database constraint
❓ Whether to communicate to customers

---

## THE 3-PHASE CLEANUP PLAN

### Phase 1: Automated Cleanup (Week 1) ⭐ READY
**Target:** Clear sfdc_id from DISABLED properties in duplicate groups

**Impact:**
- Fixes ~2,000 duplicate groups (79%)
- Unblocks ~2,500 ACTIVE properties
- Takes 2 hours to execute

**Risk:** LOW (only touches DISABLED)

**Steps:**
1. Review Phase1_Cleanup_Script.sql
2. Run STEP 1-3 (preview queries)
3. Create backup (in script)
4. Uncomment STEP 4 to execute
5. Run STEP 5 (verification)
6. Monitor sync job to confirm properties start syncing

**Expected Outcome:**
- Park Kennedy features start syncing ✅
- ~2,500 other properties unblocked ✅
- Duplicate groups drop from 2,541 → ~500 ✅

---

### Phase 2: Manual Review (Week 2)
**Target:** 150-200 cases with TWO ACTIVE properties sharing sfdc_id

**Examples Needing Review:**
- Bell Lighthouse Point + Advenir Lighthouse Point
- NOVEL West Midtown + MAA West Midtown
- Territory at Williams Way (multiple variants)
- National + The National + The National Residences (3 ACTIVE!)

**Process:**
1. Run Phase2_Manual_Review_List.sql Query 4 (priority ranking)
2. Export Query 5 to spreadsheet
3. For each case, research:
   - Same property or different?
   - Which has more features/activity?
   - Which should be in Salesforce?
4. Document decision in spreadsheet
5. Generate cleanup SQL for each
6. Execute in batches

**Effort:** 10-15 hours over several days

**Decision Framework:**
- Name change? → Clear sfdc_id from old
- Management change? → May need separate SF records
- Guarantor variant? → Need separate SF records
- Test property? → Mark DISABLED, clear sfdc_id
- Migration error? → Mark old DISABLED, clear sfdc_id

---

### Phase 3: Prevention (Week 3-4)
**Target:** Stop duplicates from happening again

**Actions:**
1. **Add database constraint:**
   ```sql
   CREATE UNIQUE INDEX unique_sfdc_id
   ON properties(sfdc_id)
   WHERE sfdc_id IS NOT NULL;
   ```

2. **Add daily monitoring:**
   ```sql
   -- Alert if duplicates created in last 24 hours
   SELECT * FROM properties
   WHERE inserted_at >= CURRENT_DATE - 1
   GROUP BY sfdc_id HAVING COUNT(*) > 1;
   ```

3. **Add application validation:**
   ```python
   def set_sfdc_id(property_id, sfdc_id):
       if exists(property with sfdc_id, id != property_id):
           raise ValueError("Duplicate sfdc_id")
   ```

4. **Document process:**
   - Update runbooks
   - Train team on proper migration process
   - Add alerts to monitoring dashboard

---

## KEY QUERIES FOR CONTINUATION

### Check Current Duplicate Count
```sql
SELECT COUNT(DISTINCT sfdc_id) as duplicate_groups
FROM (
    SELECT sfdc_id FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
    GROUP BY sfdc_id HAVING COUNT(*) > 1
);
-- Current: 2,541 groups
```

### Find High Priority Cases (P1)
```sql
-- ACTIVE properties with features, NOT in Salesforce
SELECT p.id, p.name, COUNT(pfe.feature_code) as features
FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.property_feature_events pfe
    ON p.id = pfe.property_id AND pfe.event_type = 'enabled'
LEFT JOIN crm.salesforce.product_property sf
    ON CAST(p.id AS STRING) = sf.snappt_property_id_c
WHERE p.status = 'ACTIVE'
  AND sf.id IS NULL
  AND EXISTS (
      SELECT 1 FROM rds.pg_rds_public.properties p2
      WHERE p2.sfdc_id = p.sfdc_id AND p2.id != p.id
  )
GROUP BY p.id, p.name
HAVING COUNT(pfe.feature_code) > 0;
```

### Verify Park Kennedy After Fix
```sql
SELECT id, name, status, sfdc_id, identity_verification_enabled
FROM rds.pg_rds_public.properties
WHERE name LIKE '%Park Kennedy%'
ORDER BY status, inserted_at DESC;
```

---

## METRICS TO TRACK

### Before Cleanup (Current State)
- Duplicate sfdc_id groups: **2,541**
- Properties affected: **6,068** (3,391 DISABLED + 2,677 ACTIVE)
- Estimated ACTIVE blocked: **~2,500**
- Sync success rate: **~60%** (estimated)

### After Phase 1 (Expected)
- Duplicate groups: **~500** (↓81%)
- Properties affected: **~1,000** (↓83%)
- ACTIVE blocked: **~150** (↓94%)
- Sync success rate: **~95%**

### After Phase 2 (Expected)
- Duplicate groups: **~50** (↓98%)
- Properties affected: **~100** (↓98%)
- ACTIVE blocked: **0** (↓100%)
- Sync success rate: **~100%**

### Success Criteria
- [ ] Phase 1 executed without errors
- [ ] Park Kennedy syncing features correctly
- [ ] No customer complaints about sync
- [ ] Duplicate count < 500 after Phase 1
- [ ] All P1 cases resolved
- [ ] Monitoring in place
- [ ] No new duplicates created

---

## TECHNICAL DETAILS

### Why Duplicates Break Sync

**New Property Path:**
```sql
-- In new_properties_with_features
WHERE sf.snappt_property_id_c IS NULL
  AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')  -- ← FILTERS OUT PROPERTIES WITH SFDC_ID
  AND rds.status = 'ACTIVE'
```
**Result:** ACTIVE property with sfdc_id is skipped

**Feature Sync Path:**
```sql
-- In census_pfe
left join hive_metastore.salesforce.product_property_c pp
    on pp.sf_property_id_c = p.sfdc_id  -- ← JOIN FAILS IF WRONG PROPERTY IN SF
```
**Result:** If Salesforce has DISABLED property, join returns NULL

**Conclusion:** Features have no path to sync when duplicate sfdc_ids exist

---

### Database Schema (Relevant Fields)

**rds.pg_rds_public.properties:**
- `id` (UUID) - Primary key
- `name` (text) - Property name
- `short_id` (text) - Short identifier
- `status` (text) - ACTIVE, DISABLED, DELETED
- `sfdc_id` (text) - Salesforce Property ID (a01...)
- `identity_verification_enabled` (boolean)
- `inserted_at` (timestamp)
- `updated_at` (timestamp)

**rds.pg_rds_public.property_feature_events:**
- `property_id` (UUID)
- `feature_code` (text) - income_verification, bank_linking, etc.
- `event_type` (text) - enabled, disabled
- `inserted_at` (timestamp)
- `_fivetran_deleted` (boolean)

**crm.salesforce.product_property:**
- `id` (text) - Salesforce record ID (a13...)
- `snappt_property_id_c` (text) - Maps to properties.id
- `sf_property_id_c` (text) - Maps to properties.sfdc_id
- `fraud_detection_enabled_c` (boolean)
- `income_verification_enabled_c` (boolean)
- `bank_linking_enabled_c` (boolean)
- ...25+ feature fields

---

## IMPORTANT CONTEXT FOR NEXT SESSION

### What to Review First
1. **DUPLICATE_CLEANUP_SUMMARY.md** - Quick overview
2. **Phase1_Cleanup_Script.sql** - The actual script to run
3. **notebook_output_sfdc_dupes/sfdc_id_duplicate_count.csv** - See the data

### Questions You'll Need to Answer
1. **Do you want to execute Phase 1?** (Recommendation: YES, low risk)
2. **Can we test on staging first?** (Recommendation: If available, yes)
3. **Who will do Phase 2 manual review?** (Needs domain expertise)
4. **When can we add the database constraint?** (After cleanup complete)

### Before Running Phase 1
- [ ] Get approval from team/stakeholder
- [ ] Verify backup process works
- [ ] Test on staging (if available)
- [ ] Schedule a maintenance window (optional but recommended)
- [ ] Have rollback plan ready (in script)

### How to Resume Work

**Option 1: Review & Execute**
```bash
cd /Users/danerosa/rds_databricks_claude/19122025
# Read the summary
open DUPLICATE_CLEANUP_SUMMARY.md
# Review the script
open Phase1_Cleanup_Script.sql
# Execute in Databricks SQL editor
```

**Option 2: Continue Investigation**
```bash
# Open Databricks notebook
# Navigate to: /Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs
# Run cells to see current state
```

**Option 3: Check a Specific Property**
```sql
-- In Databricks
SELECT * FROM rds.pg_rds_public.properties
WHERE name LIKE '%<property name>%';
```

---

## COMMANDS & TOOLS USED

### Databricks CLI
```bash
# Export notebook
databricks workspace export <path> --format SOURCE

# List notebooks
databricks workspace list <path>

# Import notebook
databricks workspace import <path> --file <file> --format JUPYTER
```

### Python Investigation Scripts
```bash
# With venv
cd /Users/danerosa/rds_databricks_claude
source venv/bin/activate
python investigate_api.py  # Uses REST API
python investigate_live.py  # Uses SQL connector
```

### Database Connections (Available)
- MCP PostgreSQL connections to various databases
- Databricks SQL warehouse: 9b7a58ad33c27fbc
- Databricks host: dbc-9ca0f5e0-2208.cloud.databricks.com

---

## LESSONS LEARNED

### What Worked Well
✅ Starting with specific case (Park Kennedy) revealed systemic issue
✅ Creating Jupyter notebooks makes investigation reproducible
✅ Using REST API for queries when SQL connector had issues
✅ Exporting results to CSV for analysis
✅ Breaking solution into phases (automated → manual → prevention)

### What to Watch For
⚠️ XXXXXXXXXXXXXXX sfdc_id = test properties (filtered in queries)
⚠️ Some properties have same name but different entities
⚠️ Guarantor/Employee variants are legitimate separate properties
⚠️ Database constraints need careful timing (after cleanup)
⚠️ Salesforce has 2 different ID fields (snappt_property_id_c vs sf_property_id_c)

### Key Insights
💡 Property migrations often leave old properties with sfdc_id
💡 ~85% of duplicates have clear resolution (DISABLED + ACTIVE)
💡 Sync workflow assumes 1:1 mapping between RDS and Salesforce
💡 Clearing sfdc_id is safer than deleting properties
💡 Manual review needed for edge cases (~15% of duplicates)

---

## STAKEHOLDERS & COMMUNICATION

### Key People
- **Ella** - Flagged Park Kennedy issue initially
- **Dane** - Investigated and created cleanup plan (you)
- **Team** - Need approval for cleanup execution

### What to Communicate

**To Team:**
- "Found systemic issue: 2,500 properties can't sync features"
- "Have safe, automated solution ready to fix 79% of cases"
- "Need approval to execute Phase 1 cleanup"
- "Estimated 2 hours execution + monitoring"

**To Customers:** (After Phase 1 complete)
- Most won't notice anything
- Some may see properties appear in Salesforce for first time
- May see duplicate Salesforce records (can be merged manually)
- Recommend: Monitor first week, communicate if issues arise

---

## SUCCESS STORY (When Complete)

### Before
❌ Park Kennedy features not syncing
❌ 2,541 duplicate groups blocking sync
❌ ~2,500 ACTIVE properties can't sync features
❌ Customers see incorrect feature data in Salesforce

### After
✅ Park Kennedy syncing all 4 features correctly
✅ <100 duplicate groups remaining (98% reduction)
✅ All ACTIVE properties syncing features
✅ Database constraint prevents future duplicates
✅ Monitoring alerts on new duplicates
✅ ~2,500 properties unblocked and syncing

---

## REFERENCES & LINKS

### Databricks
- **Job:** 1061000314609635 (00_sfdc_dbx_v2)
- **Feature Aggregation:** `/Workspace/Shared/census_pfe`
- **Feature Sync:** `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
- **New Properties:** `/Repos/dbx_git/dbx/snappt/new_properties_with_features`

### Census
- Census sync: https://app.getcensus.com/workspaces/33026/syncs/3326072/overview

### Documentation
- All files in: `/Users/danerosa/rds_databricks_claude/19122025/`
- Investigation outputs: `notebook_output_sfdc_dupes/`

---

## FINAL STATUS

**Investigation:** ✅ COMPLETE
**Root Cause:** ✅ IDENTIFIED
**Solution:** ✅ DESIGNED
**Scripts:** ✅ READY
**Approval:** ⏳ PENDING
**Execution:** ⏸️ WAITING

**Next Action:** Review Phase1_Cleanup_Script.sql and get approval to execute

**Estimated Time to Resolution:**
- Phase 1: 2 hours
- Phase 2: 10-15 hours (over 1-2 weeks)
- Phase 3: 4 hours
- **Total: ~20-25 hours** to complete resolution

---

## NOTES FOR CLAUDE (Next Session)

When resuming:
1. Ask user for current state/approval status
2. Refer to this context file for full background
3. Key files to reference:
   - DUPLICATE_CLEANUP_SUMMARY.md (executive summary)
   - Phase1_Cleanup_Script.sql (execution script)
   - notebook_output_sfdc_dupes/ (data exports)
4. If executing Phase 1, walk through script step-by-step
5. If investigating specific property, use queries from this file
6. Remember: Park Kennedy is just example of systemic issue

**Session Summary:**
Investigated Park Kennedy feature sync issue → Discovered 2,541 duplicate sfdc_id groups blocking ~2,500 ACTIVE properties → Created 3-phase cleanup plan → Ready to execute Phase 1 (clears 3,400 DISABLED properties, resolves 79% of duplicates).

---

**End of Session Context**
**Date:** December 19, 2025
**Status:** Ready for Phase 1 Execution
**All files preserved in:** `/Users/danerosa/rds_databricks_claude/19122025/`
