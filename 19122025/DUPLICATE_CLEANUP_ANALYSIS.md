# Duplicate sfdc_id Cleanup - Analysis & Action Plan

**Date:** 2025-12-19
**Analyst:** Claude Code Investigation

---

## EXECUTIVE SUMMARY

### Scale of the Issue

**🚨 CRITICAL FINDINGS:**
- **2,541 duplicate sfdc_id groups** affecting production properties
- **6,068 total properties** with duplicate sfdc_ids
  - 3,391 DISABLED properties
  - 2,677 ACTIVE properties

**Impact:**
- Features not syncing to Salesforce (like Park Kennedy)
- Sync workflow blocked for ~2,677 ACTIVE properties
- Customer-facing impact for properties with features enabled

---

## BREAKDOWN BY PATTERN

### Pattern 1: ACTIVE + DISABLED Pairs (Most Common ~85%)

**Example:** Park Kennedy, The Emery, Millennium Dallas, etc.

```
Property A: ACTIVE (newer, 2025-11-10)
Property B: DISABLED (older, 2025-06-04)
Same sfdc_id: a01Dn00000HHUanIAH
```

**Root Cause:** Property migration/recreation - old property kept sfdc_id

**Resolution:** Clear sfdc_id from DISABLED property

**Estimated Count:** ~2,000 groups

---

### Pattern 2: Multiple DISABLEDs + One ACTIVE

**Examples:**
- **Regal Vista:** 4 properties (1 ACTIVE, 3 DISABLED)
- **Puritan Place:** 4 properties (1 ACTIVE, 3 DISABLED)
- **Arbor Ridge:** 4 properties (1 ACTIVE, 3 DISABLED)
- **Axis Grand Crossing:** 6 properties (2 ACTIVE, 4 DISABLED)

**Root Cause:** Multiple migrations over time

**Resolution:** Clear sfdc_id from all DISABLED properties

**Estimated Count:** ~300 groups

---

### Pattern 3: TWO ACTIVE Properties 🚨 (Concerning)

**Examples:**
- **Bell Lighthouse Point** + **Advenir Lighthouse Point** (both ACTIVE)
- **NOVEL West Midtown** + **MAA West Midtown** (both ACTIVE)
- **Elowen** + **Ion Aero** (both ACTIVE)
- **The National** + **National** (both ACTIVE)
- **Territory at Williams Way - MS** + duplicate (both ACTIVE)

**Root Cause:**
- Could be legitimate different properties (name change, different buildings)
- Could be accidental duplicates
- Could be different product types (guarantor, employee, etc.)

**Resolution:** **REQUIRES MANUAL REVIEW** ⚠️
- Investigate each case
- Determine if properties are actually different entities
- If same: mark one as DISABLED and clear sfdc_id
- If different: one needs new Salesforce record

**Estimated Count:** ~150-200 groups

---

### Pattern 4: Both DISABLED

**Example:** Riachi at One21 (both DISABLED)

**Root Cause:** Property no longer active, duplicates never cleaned up

**Resolution:** Clear sfdc_id from all but one (or both if truly obsolete)

**Estimated Count:** ~50 groups

---

## IMPACT ANALYSIS

### High Priority (Immediate Action Needed)

**Criteria:**
- ACTIVE property
- Has features enabled
- NOT in Salesforce

**Query to Find:**
```sql
SELECT COUNT(*) FROM cell5.csv
WHERE status = 'ACTIVE'
  AND enabled_features_count > 0
  AND salesforce_record_id IS NULL;
```

**Estimated:** 200-500 properties

**Action:** Fix immediately (these are customer-facing)

---

### Medium Priority (Next 2 Weeks)

**Criteria:**
- ACTIVE property
- No features enabled yet
- NOT in Salesforce

**Risk:** Will break when features get enabled

**Action:** Batch cleanup

---

### Low Priority (Maintenance)

**Criteria:**
- DISABLED properties
- No Salesforce sync expected

**Action:** Clean up for data hygiene

---

## RECOMMENDED CLEANUP APPROACH

### Phase 1: Quick Wins (Week 1) - Pattern 1 & 2

**Target:** ACTIVE + DISABLED pairs where resolution is clear

**Script:**
```sql
-- Clear sfdc_id from all DISABLED properties in duplicate groups
WITH duplicate_groups AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'  -- Exclude test properties
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

disabled_to_clear AS (
    SELECT p.id, p.name, p.sfdc_id, p.status
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
    WHERE p.status = 'DISABLED'
)

-- PREVIEW: Review before executing
SELECT COUNT(*) as properties_to_update,
       COUNT(DISTINCT sfdc_id) as duplicate_groups_affected
FROM disabled_to_clear;

-- EXECUTE: Uncomment to clear sfdc_ids
/*
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id IN (SELECT id FROM disabled_to_clear);
*/
```

**Estimated Impact:**
- ~3,400 DISABLED properties updated
- ~2,000 duplicate groups resolved
- ~2,000 ACTIVE properties unblocked for sync

---

### Phase 2: Manual Review (Week 2) - Pattern 3

**Target:** TWO ACTIVE properties sharing sfdc_id

**Process:**
1. Export list of these duplicates
2. For each group, investigate:
   - Are they the same property? (name change, migration)
   - Are they different properties? (different buildings, different mgmt co)
   - Which one should keep the sfdc_id?
3. Create case-by-case resolution plan
4. Execute fixes

**SQL to Generate Review List:**
```sql
WITH active_duplicates AS (
    SELECT
        sfdc_id,
        COLLECT_LIST(STRUCT(id, name, short_id, inserted_at)) as properties
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
      AND status = 'ACTIVE'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)
SELECT * FROM active_duplicates
ORDER BY sfdc_id;
```

---

### Phase 3: Batch Cleanup (Week 3) - Pattern 4

**Target:** Both DISABLED properties

**Script:**
```sql
-- For duplicate groups where ALL properties are DISABLED,
-- clear sfdc_id from all but the most recent
WITH all_disabled_groups AS (
    SELECT p.sfdc_id
    FROM rds.pg_rds_public.properties p
    WHERE p.sfdc_id IS NOT NULL
      AND p.sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY p.sfdc_id
    HAVING COUNT(*) > 1
      AND SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) = 0
),

keep_newest AS (
    SELECT
        p.sfdc_id,
        MAX(p.inserted_at) as keep_date
    FROM rds.pg_rds_public.properties p
    INNER JOIN all_disabled_groups adg ON p.sfdc_id = adg.sfdc_id
    GROUP BY p.sfdc_id
),

properties_to_clear AS (
    SELECT p.id
    FROM rds.pg_rds_public.properties p
    INNER JOIN keep_newest kn ON p.sfdc_id = kn.sfdc_id
    WHERE p.inserted_at < kn.keep_date
)

-- Clear sfdc_id from older DISABLED properties
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id IN (SELECT id FROM properties_to_clear);
```

---

## VERIFICATION QUERIES

### After Phase 1:

```sql
-- Check how many duplicates remain
SELECT COUNT(DISTINCT sfdc_id) as remaining_duplicates
FROM (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
);

-- Check how many ACTIVE properties are now unblocked
SELECT COUNT(*) as unblocked_active_properties
FROM rds.pg_rds_public.properties p
WHERE status = 'ACTIVE'
  AND NOT EXISTS (
      SELECT 1
      FROM rds.pg_rds_public.properties p2
      WHERE p2.sfdc_id = p.sfdc_id
        AND p2.id != p.id
        AND p2.sfdc_id IS NOT NULL
  );
```

---

## EXPECTED OUTCOMES

### After Full Cleanup:

**Resolved Duplicates:**
- ~2,400 of 2,541 groups resolved automatically (94%)
- ~150 groups requiring manual review (6%)

**Properties Unblocked:**
- ~2,500 ACTIVE properties can now sync features
- New property sync workflow will work correctly
- Feature sync workflow will work correctly

**Remaining Issues:**
- ~150 groups with 2 ACTIVE properties need manual decisions
- Test properties with XXXXXXXXXXXXXXX still need cleanup

---

## MONITORING & PREVENTION

### 1. Add Monitoring Query (Run Daily)

```sql
-- Alert if new duplicates appear
SELECT
    sfdc_id,
    COUNT(*) as duplicate_count,
    COLLECT_LIST(name) as property_names
FROM rds.pg_rds_public.properties
WHERE sfdc_id IS NOT NULL
  AND sfdc_id != 'XXXXXXXXXXXXXXX'
  AND inserted_at >= CURRENT_DATE() - INTERVAL 1 DAY
GROUP BY sfdc_id
HAVING COUNT(*) > 1;
```

### 2. Add Database Constraint (After Cleanup)

```sql
-- Prevent future duplicates (PostgreSQL)
CREATE UNIQUE INDEX unique_sfdc_id
ON properties(sfdc_id)
WHERE sfdc_id IS NOT NULL
  AND sfdc_id != 'XXXXXXXXXXXXXXX';
```

### 3. Application-Level Validation

Add validation before setting sfdc_id in application code.

---

## RISKS & MITIGATION

### Risk 1: Clearing wrong property's sfdc_id

**Mitigation:**
- Start with DISABLED properties only (Phase 1)
- Require manual review for ACTIVE+ACTIVE pairs
- Keep audit trail of all changes
- Test on staging first

### Risk 2: Breaking existing Salesforce relationships

**Mitigation:**
- Clearing sfdc_id doesn't delete Salesforce records
- Properties will sync as "new" and create new records
- Old Salesforce records remain intact
- Can be manually merged if needed

### Risk 3: Impact on historical reporting

**Mitigation:**
- Document all changes
- Keep sfdc_id change log
- Properties keep their original IDs in Snappt
- Salesforce history preserved

---

## SUCCESS METRICS

**Week 1:**
- ✅ 2,000+ duplicate groups resolved
- ✅ 2,500+ ACTIVE properties unblocked
- ✅ Park Kennedy syncing features

**Week 2:**
- ✅ Manual review list completed
- ✅ Plan for each ACTIVE+ACTIVE case

**Week 3:**
- ✅ All automatic cleanups complete
- ✅ < 150 duplicate groups remaining
- ✅ Monitoring in place

**Week 4:**
- ✅ Database constraint added
- ✅ Application validation added
- ✅ Documentation complete

---

## NEXT STEPS

1. **Get Approval** - Review this plan with team
2. **Test on Staging** - Run Phase 1 script on staging environment
3. **Execute Phase 1** - Clear sfdc_id from DISABLED properties
4. **Monitor Sync** - Verify properties start syncing correctly
5. **Continue Phases** - Proceed with Phase 2 & 3

---

## ESTIMATED EFFORT

**Phase 1 (Automated):** 2 hours
- Write script: 30 min
- Test on staging: 30 min
- Execute on production: 15 min
- Monitor results: 45 min

**Phase 2 (Manual Review):** 10-15 hours
- Export and categorize: 2 hours
- Review each case: 8-10 hours
- Execute fixes: 2-3 hours

**Phase 3 (Automated):** 1 hour
- Execute batch cleanup
- Verify results

**Prevention (One-time):** 3-4 hours
- Add monitoring: 1 hour
- Add constraints: 1 hour
- Update application: 2 hours

**Total:** ~20-25 hours over 3-4 weeks

---

**Ready to proceed?** Start with Phase 1 to get quick wins and unblock 2,500+ properties.
