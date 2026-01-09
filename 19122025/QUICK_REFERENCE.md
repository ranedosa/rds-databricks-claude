# Quick Reference Guide

**When you need to pick this work back up, read this file first.**

---

## ⚠️ CRITICAL UPDATE - December 23, 2025

**THIS APPROACH HAS CHANGED!**

New finding: **Many-to-1 relationships are now supported** (multiple properties can share same sfdc_id)

👉 **Read instead:** `START_HERE_DEC23.md` or `WORKFLOW_REDESIGN_QUESTIONS.md`

The content below is from the original Dec 19 investigation based on 1:1 assumption.

---

## TL;DR - What We Did (Original Dec 19 Work)

1. **Problem:** Park Kennedy features not syncing to Salesforce
2. **Investigation:** Discovered 2,541 duplicate sfdc_id groups
3. **Impact:** ~2,500 ACTIVE properties blocked from syncing
4. **Solution:** 3-phase cleanup plan ready to execute
5. **Status:** ~~Waiting for approval to run Phase 1~~ → **PAUSED - Approach changed Dec 23**

---

## How to Resume - Choose Your Path

### Path A: "I want to execute the cleanup"
```
1. Read: DUPLICATE_CLEANUP_SUMMARY.md
2. Review: Phase1_Cleanup_Script.sql
3. Get approval from team
4. Test on staging (if available)
5. Execute Phase 1 script in Databricks
6. Monitor sync job results
```

### Path B: "I want to review the analysis first"
```
1. Read: SESSION_CONTEXT.md (full context)
2. Review: notebook_output_sfdc_dupes/sfdc_id_duplicate_count.csv
3. Open: /Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs
4. Decide on next steps
```

### Path C: "I want to investigate a specific property"
```sql
-- Run in Databricks:
SELECT * FROM rds.pg_rds_public.properties
WHERE name LIKE '%<property name>%';

-- Check for duplicates:
SELECT sfdc_id, COUNT(*), COLLECT_LIST(name)
FROM rds.pg_rds_public.properties
WHERE sfdc_id IN (
    SELECT sfdc_id FROM properties WHERE name LIKE '%<property name>%'
)
GROUP BY sfdc_id;
```

---

## Key Files - What They Do

| File | Purpose | When to Use |
|------|---------|-------------|
| **SESSION_CONTEXT.md** ⭐ | Complete context, read this file | Resuming work, need full background |
| **DUPLICATE_CLEANUP_SUMMARY.md** | Executive summary | Need quick overview |
| **DUPLICATE_CLEANUP_ANALYSIS.md** | Technical deep dive | Need detailed analysis |
| **Phase1_Cleanup_Script.sql** ⭐ | Ready-to-run cleanup | Ready to execute |
| **Phase2_Manual_Review_List.sql** | Edge case queries | After Phase 1 complete |
| **Park_Kennedy_Investigation_Report.ipynb** | Case study | Understanding the issue |
| **Find_Duplicate_SFDC_IDs.ipynb** | Detection queries | Finding duplicates |

---

## The Problem (One Sentence)

When properties are migrated/recreated, old DISABLED properties keep their sfdc_id, blocking new ACTIVE properties from syncing features to Salesforce.

---

## The Solution (Three Phases)

**Phase 1: Automated (79%)** - Clear sfdc_id from ~3,400 DISABLED properties
- Risk: LOW, Script: Ready, Time: 2 hours

**Phase 2: Manual (15%)** - Review ~150 cases with 2 ACTIVE properties
- Risk: MEDIUM, Needs: Domain expertise, Time: 10-15 hours

**Phase 3: Prevention (Future)** - Add constraints and monitoring
- Risk: LOW, Needs: Database access, Time: 4 hours

---

## Current Numbers

- Duplicate groups: **2,541**
- DISABLED with duplicates: **3,391**
- ACTIVE blocked: **~2,500**
- Properties affected: **6,068 total**

---

## After Phase 1 (Expected)

- Duplicate groups: **~500** (↓81%)
- ACTIVE blocked: **~150** (↓94%)
- Properties fixed: **~2,500** ✅

---

## Park Kennedy Specifics

**Property IDs:**
- DISABLED: `5eec38f2-85c9-41f2-bac3-e0e350ec1083` (clear sfdc_id from this one)
- ACTIVE: `94246cbb-5eec-4fff-b688-553dcb0e3e29` (has features, needs to sync)

**Features Enabled (not syncing):**
- Income Verification
- Bank Linking
- Payroll Linking
- Identity Verification

**Fix:** Clear sfdc_id from DISABLED property, ACTIVE will sync as "new"

---

## Quick Commands

### Check current duplicate count
```sql
SELECT COUNT(DISTINCT sfdc_id) FROM (
    SELECT sfdc_id FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
    GROUP BY sfdc_id HAVING COUNT(*) > 1
);
```

### Find properties with features not syncing
```sql
-- See Phase2_Manual_Review_List.sql Query 4
```

### Verify Park Kennedy
```sql
SELECT id, name, status, sfdc_id
FROM rds.pg_rds_public.properties
WHERE name LIKE '%Park Kennedy%';
```

---

## Databricks Locations

- **Investigation notebook:** `/Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs`
- **Park Kennedy notebook:** `/Users/dane@snappt.com/investigate_park_kennedy`
- **Sync job:** Job 1061000314609635
- **Warehouse ID:** 9b7a58ad33c27fbc

---

## Next Steps (In Order)

1. [ ] Get team approval for Phase 1
2. [ ] Review Phase1_Cleanup_Script.sql thoroughly
3. [ ] Test on staging environment (if available)
4. [ ] Execute Phase 1 cleanup
5. [ ] Verify Park Kennedy syncs correctly
6. [ ] Monitor other properties
7. [ ] Start Phase 2 manual review
8. [ ] Add prevention measures (Phase 3)

---

## Questions to Answer Before Executing

- [ ] Has team approved Phase 1?
- [ ] Is staging environment available for testing?
- [ ] Who will do Phase 2 manual review?
- [ ] When can we add database constraint?
- [ ] Should we communicate to customers?

---

## Warning Signs (Check for These)

⚠️ If Phase 1 script shows different counts than expected
⚠️ If Park Kennedy still not syncing after fix
⚠️ If new duplicates appear after cleanup
⚠️ If customers report missing properties
⚠️ If sync job fails after cleanup

---

## Success Indicators (Look for These)

✅ Duplicate count drops from 2,541 → ~500
✅ Park Kennedy appears in sync table
✅ Park Kennedy features visible in Salesforce
✅ No errors in sync job logs
✅ New properties start syncing features

---

## Who to Ask

**For approval:** Team lead / Manager
**For Salesforce questions:** Sales Ops / Salesforce admin
**For RDS questions:** Database team
**For sync workflow:** Data engineering team
**For customer impact:** Customer Success team

---

## Estimated Timeline

- **Phase 1 execution:** 2 hours
- **Monitoring:** 1 week
- **Phase 2 review:** 2 weeks
- **Phase 3 prevention:** 1 week
- **Total:** ~1 month to full resolution

---

## If Something Goes Wrong

**Rollback Phase 1:**
```sql
-- See Phase1_Cleanup_Script.sql "ROLLBACK PROCEDURE"
-- Restores sfdc_ids from backup table
```

**Get help:**
1. Check SESSION_CONTEXT.md for full details
2. Review relevant queries in Phase1 or Phase2 scripts
3. Check Databricks notebooks for investigation steps
4. Review data exports in notebook_output_sfdc_dupes/

---

**Remember:** This is a data hygiene fix, not a critical system change. It's safe to execute Phase 1, but good to be thorough.

---

**Quick Start:** Read DUPLICATE_CLEANUP_SUMMARY.md → Review Phase1_Cleanup_Script.sql → Get approval → Execute

**Last Updated:** December 19, 2025
