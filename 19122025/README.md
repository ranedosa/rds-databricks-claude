# Salesforce Feature Sync Investigation - December 19, 2025

**Investigation into why Park Kennedy features aren't syncing, revealing systemic duplicate sfdc_id issue affecting 2,500+ properties**

---

## ⚠️ CRITICAL UPDATE - December 23, 2025

**🔄 WORKFLOW REDESIGN IN PROGRESS**

A new finding has fundamentally changed this work:
- **We can now support many-to-1 relationships** (multiple properties → same sfdc_id)
- The duplicate cleanup approach needs to be **reconsidered**
- Solution shifts from "cleanup duplicates" to **"aggregate features before sync"**

**📋 Next Step:** Read `WORKFLOW_REDESIGN_QUESTIONS.md` - 9 questions need answers before proceeding

**Status:** ⏸️ PAUSED pending clarification on aggregation rules

---

## 🚀 START HERE

**New to this investigation?** Read files in this order:

1. **QUICK_REFERENCE.md** ⭐ (5 min read) - How to resume work
2. **DUPLICATE_CLEANUP_SUMMARY.md** ⭐ (10 min read) - Executive summary
3. **SESSION_CONTEXT.md** (30 min read) - Complete context for resuming

**Ready to execute?**
4. **Phase1_Cleanup_Script.sql** - Review and run this script

---

## 📊 Investigation Summary

### The Problem
Park Kennedy property has features enabled in RDS (Income Verification, Bank Linking, Payroll Linking, Identity Verification) but they're not appearing in Salesforce.

### What We Found
- Park Kennedy has **duplicate sfdc_id** (2 properties share same ID)
- This pattern exists across **2,541 duplicate groups** affecting **6,068 properties**
- ~**2,500 ACTIVE properties** are blocked from syncing features
- **79% of cases** have clear automated resolution
- **15% require manual review** for edge cases

### The Solution
**3-Phase Cleanup Plan:**
- ✅ Phase 1: Automated cleanup of DISABLED properties (2 hours, LOW risk)
- ⏳ Phase 2: Manual review of ACTIVE+ACTIVE cases (10-15 hours, MEDIUM risk)
- ⏳ Phase 3: Prevention (constraints, monitoring, 4 hours, LOW risk)

### Current Status
- 📝 Investigation: **COMPLETE**
- ✅ Root cause: **IDENTIFIED**
- ✅ Scripts: **READY TO EXECUTE**
- ⏸️ Execution: **WAITING FOR APPROVAL**

---

## 📁 File Directory

### Start Here (Read First)
```
⭐ WORKFLOW_REDESIGN_QUESTIONS.md - NEW: Questions to answer before proceeding (Dec 23)
QUICK_REFERENCE.md          - Quick start guide for resuming work
DUPLICATE_CLEANUP_SUMMARY.md - Executive summary of findings (based on old 1:1 model)
SESSION_CONTEXT.md          - Complete session context with all details
README.md                   - This file
```

### Investigation & Analysis
```
PARK_KENNEDY_DIAGNOSTIC.md           - Initial diagnostic with 6 root causes
PARK_KENNEDY_ROOT_CAUSE.md           - Detailed Park Kennedy root cause
DUPLICATE_CLEANUP_ANALYSIS.md        - Complete technical analysis (10K words)
DUPLICATE_SFDC_ID_RESOLUTION_STRATEGY.md - Resolution strategy guide
```

### Databricks Notebooks (Importable)
```
Park_Kennedy_Investigation_Report.ipynb - Full Park Kennedy investigation
Park_Kennedy_Investigation_Report.py    - Python version
Find_Duplicate_SFDC_IDs.ipynb          - 5 queries to find all duplicates
```

### Cleanup Scripts (Ready to Run)
```
Phase1_Cleanup_Script.sql      ⭐ - READY TO EXECUTE (clears DISABLED props)
Phase2_Manual_Review_List.sql  - Queries for manual review cases
```

### Detection Queries
```
find_duplicate_sfdc_ids.sql         - Main duplicate detection query
find_duplicate_sfdc_ids_summary.sql - Summary view of duplicates
```

### Investigation Scripts (Used During Analysis)
```
investigate_park_kennedy.py         - Park Kennedy investigation notebook
investigate_api.py                  - Investigation using REST API
investigate_live.py                 - Investigation using SQL connector
run_park_kennedy_investigation.py   - Full investigation runner
park_kennedy_investigation.sql      - SQL queries for Park Kennedy
query1_rds_properties.sql          - Query RDS properties
query2_feature_events.sql          - Query feature events
```

### Data Exports
```
notebook_output_sfdc_dupes/
  ├── sfdc_id_duplicate_count.csv   - 2,542 duplicate groups summary
  ├── cell2.csv                     - 6,069 detailed property records
  ├── cell3.csv                     - Status breakdown (3,391 DISABLED, 2,677 ACTIVE)
  ├── cell4.csv                     - 6,104 Salesforce sync status records
  └── cell5.csv                     - 6,069 feature enablement records
```

---

## 🎯 Key Findings

### Scale
- **2,541** duplicate sfdc_id groups
- **6,068** properties affected
- **3,391** DISABLED properties with duplicates
- **2,677** ACTIVE properties with duplicates
- **~2,500** ACTIVE properties blocked from syncing

### Patterns
1. **ACTIVE + DISABLED pairs (85%)** - Old property kept sfdc_id after migration
2. **Multiple DISABLED + 1 ACTIVE (10%)** - Multiple migrations over time
3. **TWO ACTIVE properties (5%)** - Name changes, mgmt changes, or different properties
4. **All DISABLED (rare)** - Legacy cleanup needed

### Impact
- Features not visible in Salesforce for customers
- Sales/CS teams see incorrect feature data
- Sync workflow blocked for ~2,500 properties
- Reporting inaccurate

---

## 🔧 How to Execute Phase 1

### Prerequisites
- [ ] Read DUPLICATE_CLEANUP_SUMMARY.md
- [ ] Review Phase1_Cleanup_Script.sql
- [ ] Get team approval
- [ ] Have Databricks access ready

### Steps
1. Open Phase1_Cleanup_Script.sql
2. Run STEP 1-3 (preview queries) to verify expectations
3. Review the counts and sample data
4. Uncomment STEP 4 to execute cleanup
5. Run STEP 5 (verification queries)
6. Monitor sync job 1061000314609635

### Expected Results
- ~3,400 DISABLED properties cleared
- Duplicate groups: 2,541 → ~500 (↓81%)
- ACTIVE blocked: ~2,500 → ~150 (↓94%)
- Park Kennedy starts syncing features ✅

### Safety Features
- ✅ Creates backup before execution
- ✅ Only touches DISABLED properties
- ✅ Rollback procedure included
- ✅ Verification queries provided
- ✅ Preview steps before execution

---

## 📈 Metrics

### Before Cleanup (Current)
| Metric | Value |
|--------|-------|
| Duplicate groups | 2,541 |
| Properties affected | 6,068 |
| DISABLED with duplicates | 3,391 |
| ACTIVE blocked | ~2,500 |
| Sync success rate | ~60% |

### After Phase 1 (Expected)
| Metric | Value | Change |
|--------|-------|--------|
| Duplicate groups | ~500 | ↓81% |
| Properties affected | ~1,000 | ↓83% |
| DISABLED with duplicates | ~50 | ↓98% |
| ACTIVE blocked | ~150 | ↓94% |
| Sync success rate | ~95% | ↑35% |

### After Phase 2 (Expected)
| Metric | Value | Change |
|--------|-------|--------|
| Duplicate groups | ~50 | ↓98% |
| Properties affected | ~100 | ↓98% |
| ACTIVE blocked | 0 | ↓100% |
| Sync success rate | ~100% | ↑40% |

---

## 🔗 Databricks Assets

### Notebooks (Already Imported)
- `/Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs`
- `/Users/dane@snappt.com/investigate_park_kennedy`

### Key Resources
- **Sync Job:** 1061000314609635 (00_sfdc_dbx_v2)
- **Warehouse:** 9b7a58ad33c27fbc
- **Host:** dbc-9ca0f5e0-2208.cloud.databricks.com
- **Census Sync:** https://app.getcensus.com/workspaces/33026/syncs/3326072/overview

### Important Tables
- `rds.pg_rds_public.properties` - Source data
- `rds.pg_rds_public.property_feature_events` - Feature events
- `crm.sfdc_dbx.product_property_w_features` - Feature aggregation
- `crm.sfdc_dbx.product_property_feature_sync` - Sync queue
- `crm.salesforce.product_property` - Salesforce data (via Fivetran)

---

## 🚦 Phase Status

### Phase 1: Automated Cleanup ⏸️ READY
- [x] Analysis complete
- [x] Script written
- [x] Verification queries ready
- [x] Rollback procedure documented
- [ ] Team approval received
- [ ] Staging tested
- [ ] Production executed
- [ ] Results verified

### Phase 2: Manual Review ⏳ PENDING
- [x] Query scripts written
- [x] Decision framework created
- [ ] Cases exported to spreadsheet
- [ ] Manual review started
- [ ] Resolutions documented
- [ ] Cleanup executed

### Phase 3: Prevention ⏳ PENDING
- [ ] Database constraint added
- [ ] Daily monitoring implemented
- [ ] Application validation added
- [ ] Documentation updated
- [ ] Team trained

---

## 📞 Next Steps

### Immediate (This Week)
1. Get approval from team for Phase 1
2. Review Phase1_Cleanup_Script.sql thoroughly
3. Test on staging if available
4. Execute Phase 1 cleanup
5. Verify Park Kennedy syncs correctly
6. Monitor sync job for 24-48 hours

### Short Term (Next 2 Weeks)
1. Export Phase 2 manual review cases
2. Categorize and prioritize cases
3. Research each ACTIVE+ACTIVE duplicate
4. Document resolution decisions
5. Execute Phase 2 cleanup in batches

### Long Term (Next Month)
1. Add database unique constraint
2. Implement daily monitoring
3. Add application validation
4. Update documentation and runbooks
5. Train team on proper migration process

---

## ❓ FAQ

**Q: Is it safe to run Phase 1?**
A: Yes. It only touches DISABLED properties, includes backup creation, and has rollback procedure.

**Q: What if something goes wrong?**
A: Rollback procedure in Phase1_Cleanup_Script.sql restores original state. Properties aren't deleted, just sfdc_id cleared.

**Q: Will this affect customers?**
A: Most won't notice. Some may see properties appear in Salesforce for first time (positive). May create duplicate SF records (can merge manually).

**Q: How long will this take?**
A: Phase 1: 2 hours execution + 1 week monitoring. Phase 2: 10-15 hours over 2 weeks. Phase 3: 4 hours.

**Q: Why did this happen?**
A: When properties are migrated/recreated, old properties kept their sfdc_id instead of having it cleared.

**Q: How do we prevent this?**
A: Phase 3 adds database constraint, daily monitoring, and application validation.

---

## 🎓 Lessons Learned

### What Worked Well
- Starting with specific case (Park Kennedy) revealed systemic issue
- Creating reproducible Jupyter notebooks
- Exporting results to CSV for offline analysis
- Breaking solution into phases (auto → manual → prevention)
- Documenting everything comprehensively

### What to Watch For
- XXXXXXXXXXXXXXX = test properties (filter in queries)
- Properties with same name might be different entities
- Guarantor/Employee variants are legitimate duplicates
- Some name changes are management company changes (separate entities)
- Both `snappt_property_id_c` and `sf_property_id_c` exist in Salesforce

### Key Insights
- Property migrations often leave artifacts (old sfdc_ids)
- 1:1 mapping assumption in sync workflow breaks with duplicates
- Clearing sfdc_id is safer than deleting properties
- Most cases (85%) have clear automated resolution
- Edge cases (15%) need domain expertise for resolution

---

## 📚 Additional Resources

### Related Documentation
- Sync workflow: Job 1061000314609635 notebooks
- Feature aggregation: `/Workspace/Shared/census_pfe`
- Feature sync: `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
- New properties: `/Repos/dbx_git/dbx/snappt/new_properties_with_features`

### External Links
- Census workspace: https://app.getcensus.com/workspaces/33026
- Databricks workspace: https://dbc-9ca0f5e0-2208.cloud.databricks.com

---

## 🏁 Success Criteria

### Phase 1 Complete When:
- [ ] Script executed without errors
- [ ] ~3,400 DISABLED properties cleared
- [ ] Duplicate count drops to ~500
- [ ] Park Kennedy syncing correctly
- [ ] No customer complaints
- [ ] Sync job running without errors

### Phase 2 Complete When:
- [ ] All ACTIVE+ACTIVE cases reviewed
- [ ] Top 50 priority cases resolved
- [ ] Resolution plan documented
- [ ] Duplicate count < 100

### Phase 3 Complete When:
- [ ] Database constraint active
- [ ] Daily monitoring running
- [ ] Application validation deployed
- [ ] No new duplicates detected for 1 week
- [ ] Documentation updated
- [ ] Team trained

### Overall Success:
- [ ] Duplicate groups reduced 98% (2,541 → ~50)
- [ ] All ACTIVE properties unblocked
- [ ] Sync success rate ~100%
- [ ] Prevention measures in place
- [ ] No recurrence of issue

---

## 📝 Change Log

**December 19, 2025:**
- Initial investigation of Park Kennedy issue
- Discovery of systemic duplicate problem
- Analysis of 2,541 duplicate groups
- Creation of 3-phase cleanup plan
- Documentation of all findings
- Scripts ready for execution

---

## 👥 Credits

**Investigation:** Dane Rosa
**Tool:** Claude Code
**Date:** December 19, 2025
**Time Invested:** ~6 hours
**Files Created:** 22 files (analysis, scripts, notebooks, documentation)

---

**For questions or to resume work, start with QUICK_REFERENCE.md**

**Ready to execute? Review Phase1_Cleanup_Script.sql**

---

*Last Updated: December 19, 2025*
