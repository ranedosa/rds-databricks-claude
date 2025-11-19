# modify_address V2 Testing Plan

**Objective:** Safely test the new sfdc_id-based matching approach without impacting production tables.

**Approach:** Run test notebook that writes to separate `_v2_test` tables, then validate results.

---

## 📋 Testing Checklist

### Phase 1: Setup (5 minutes)

- [ ] Upload `modify_address_v2_test.sql` to Databricks workspace
- [ ] Upload `modify_address_v2_validation.sql` to Databricks workspace
- [ ] Verify both notebooks are accessible

**File Locations:**
- Test notebook: https://dbc-9ca0f5e0-2208.cloud.databricks.com/editor/notebooks/2584135676346077
- Validation notebook: [Upload `modify_address_v2_validation.sql`]

---

### Phase 2: Run Test Notebook (10-15 minutes)

#### Step 1: Execute Test Run

1. Open the **test notebook** in Databricks
2. Attach to a cluster (recommend: `fivetran` warehouse or similar)
3. Click **"Run All"**
4. Monitor execution

**Expected Runtime:** 10-15 minutes (vs 20+ min for current approach)

**Expected Output:**
- ✅ All cells should complete successfully
- ✅ 4 test tables created with `_v2_test` suffix
- ✅ Final cell shows quick summary statistics

#### Step 2: Verify Test Tables Created

Check that these tables exist:

```sql
-- Run this to verify tables were created
SHOW TABLES IN team_sandbox.data_engineering LIKE '*_v2_test';
SHOW TABLES IN crm.sfdc_dbx LIKE '*_v2_test';
```

**Expected Tables:**
- `team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test`
- `team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test`
- `team_sandbox.data_engineering.unity_property_duplicate_status_v2_test`
- `crm.sfdc_dbx.unity_modify_address_v2_test` ⭐ Main output

#### Step 3: Quick Sanity Check

Run this query in the test notebook:

```sql
-- Quick sanity check
SELECT
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records,
    SUM(CASE WHEN match_method = 'DIRECT_SFDC_ID' THEN 1 ELSE 0 END) AS direct_matches,
    SUM(CASE WHEN match_method = 'ADDRESS_MATCH_FALLBACK' THEN 1 ELSE 0 END) AS fallback_matches
FROM crm.sfdc_dbx.unity_modify_address_v2_test;
```

**Expected Results:**
- `sfdc_properties`: ~13,335 (21% more than V1's ~11,047)
- `fde_properties`: ~13,335
- `direct_matches`: ~80% of total
- `fallback_matches`: ~20% of total

**✅ If numbers look correct, proceed to Phase 3**
**❌ If numbers are significantly off, investigate before proceeding**

---

### Phase 3: Run Validation Notebook (15-20 minutes)

#### Step 1: Execute Validation

1. Open the **validation notebook** in Databricks
2. Attach to same cluster
3. Click **"Run All"**
4. Review each cell's output carefully

#### Step 2: Review Key Validation Results

**Cell 1: Overall Match Count Comparison**

| Expected Metric | Target Value |
|----------------|--------------|
| V1 SFDC properties | ~11,047 |
| V2 SFDC properties | ~13,335 |
| Improvement | **+21% (+2,288)** |

**Decision Point:** ✅ Proceed if V2 shows 15-25% improvement

---

**Cell 2: Match Method Breakdown**

| Match Method | Expected % |
|--------------|------------|
| DIRECT_SFDC_ID | 75-85% |
| ADDRESS_MATCH_FALLBACK | 15-25% |

**Decision Point:** ✅ Proceed if direct sfdc_id matches are 75-85%

---

**Cell 3 & 4: NEW Matches Analysis**

- **Expected:** ~4,311 new matches found by V2
- **Action:** Review sample (Cell 4) to verify they look correct
- **Check:** Do addresses actually match? Are these legitimate properties?

**Decision Point:** ✅ Proceed if new matches look legitimate

---

**Cell 5, 6 & 7: LOST Matches Analysis**

- **Expected:** ~403 matches lost in V2
- **Action:** Review sample (Cell 7) and sfdc_id status (Cell 6)
- **Key Question:** Are these false positives from V1 regex, or legitimate matches?

**Decision Point:**
- ✅ Proceed if lost matches are primarily:
  - Properties with mismatched sfdc_id
  - Properties with no sfdc_id and non-matching addresses
  - Clear false positives from fuzzy regex matching
- ⚠️ Investigate if lost matches include:
  - Many properties with exact address matches
  - High-value customers or critical properties
  - SFDC Override records

---

**Cell 8: Address Quality for Lost Matches**

Check this metric:

| Metric | Ideal Value | Concern Threshold |
|--------|-------------|-------------------|
| `full_address_match` | < 10% | > 50% |

**Interpretation:**
- If most lost matches DON'T have full address matches → They're likely false positives ✅
- If most lost matches DO have full address matches → They're legitimate, need investigation ⚠️

**Decision Point:** ✅ Proceed if < 20% of lost matches have full address match

---

**Cell 9: Duplicate Status Comparison**

- **Expected:** Duplicate counts should be similar between V1 and V2
- **Minor differences OK:** V2 may show slightly different counts due to different match logic

**Decision Point:** ✅ Proceed if duplicate distribution is similar

---

**Cell 10: API/Partner Property Flags**

- **Expected:** IsPartnerProperty counts should be very similar
- **Action:** Verify that API properties are correctly flagged

**Decision Point:** ✅ Proceed if API flag counts are within 5% of V1

---

**Cell 11: PropertyCreatedBy Distribution**

- **Expected:** Similar distribution of Yardi, Inhabit, etc.
- **Action:** Verify that partner attributions remain consistent

**Decision Point:** ✅ Proceed if distribution is similar

---

**Cell 12: Overlap Analysis**

- **Expected:** 96-97% of V1 matches should also be in V2
- **This confirms:** V2 is finding almost all V1 matches PLUS many more

**Decision Point:** ✅ Proceed if overlap is > 95%

---

### Phase 4: Stakeholder Review (1-2 days)

#### Step 1: Generate Summary Report

Run Cell 15 in validation notebook to create summary table:

```sql
SELECT * FROM team_sandbox.data_engineering.modify_address_v2_validation_summary;
```

**Export this table** and share with stakeholders.

#### Step 2: Review Specific Cases

**Sample of New Matches (for stakeholder approval):**

```sql
-- Export top 50 new matches for review
SELECT
    sfdc_name,
    fde_name,
    sfdc_address,
    fde_address,
    CONCAT(sfdc_city, ', ', sfdc_state, ' ', sfdc_zip) AS sfdc_location,
    CONCAT(fde_city, ', ', fde_state, ' ', fde_zip) AS fde_location,
    match_method
FROM (
    SELECT
        v2.sfdc_id,
        v2.fde_id,
        v2.match_method,
        sp.name AS sfdc_name,
        p.name AS fde_name,
        sp.property_address_street_s AS sfdc_address,
        p.address AS fde_address,
        sp.property_address_city_s AS sfdc_city,
        sp.property_address_state_code_s AS sfdc_state,
        sp.property_address_postal_code_s AS sfdc_zip,
        p.city AS fde_city,
        p.state AS fde_state,
        p.zip AS fde_zip
    FROM crm.sfdc_dbx.unity_modify_address_v2_test v2
    LEFT JOIN crm.sfdc_dbx.unity_modify_address v1 ON v2.sfdc_id = v1.sfdc_id AND v2.fde_id = v1.fde_id
    INNER JOIN hive_metastore.salesforce.property_c sp ON v2.sfdc_id = sp.id
    INNER JOIN rds.pg_rds_public.properties p ON v2.fde_id = p.id
    WHERE v1.sfdc_id IS NULL
)
LIMIT 50;
```

**Sample of Lost Matches (for stakeholder review):**

```sql
-- Export top 50 lost matches for review
SELECT
    sfdc_name,
    fde_name,
    sfdc_address,
    fde_address,
    CONCAT(sfdc_city, ', ', sfdc_state, ' ', sfdc_zip) AS sfdc_location,
    CONCAT(fde_city, ', ', fde_state, ' ', fde_zip) AS fde_location,
    sfdc_id_status,
    CASE
        WHEN UPPER(TRIM(sfdc_address)) = UPPER(TRIM(fde_address)) THEN 'EXACT MATCH'
        ELSE 'NOT EXACT'
    END AS address_match_quality
FROM (
    SELECT
        v1.sfdc_id,
        v1.fde_id,
        sp.name AS sfdc_name,
        p.name AS fde_name,
        sp.property_address_street_s AS sfdc_address,
        p.address AS fde_address,
        sp.property_address_city_s AS sfdc_city,
        sp.property_address_state_code_s AS sfdc_state,
        sp.property_address_postal_code_s AS sfdc_zip,
        p.city AS fde_city,
        p.state AS fde_state,
        p.zip AS fde_zip,
        CASE
            WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id <> v1.sfdc_id
            THEN 'MISMATCH: FDE.sfdc_id points elsewhere'
            WHEN p.sfdc_id IS NULL
            THEN 'FDE has no sfdc_id'
            ELSE 'Match'
        END AS sfdc_id_status
    FROM crm.sfdc_dbx.unity_modify_address v1
    LEFT JOIN crm.sfdc_dbx.unity_modify_address_v2_test v2 ON v1.sfdc_id = v2.sfdc_id AND v1.fde_id = v2.fde_id
    INNER JOIN hive_metastore.salesforce.property_c sp ON v1.sfdc_id = sp.id
    INNER JOIN rds.pg_rds_public.properties p ON v1.fde_id = p.id
    WHERE v2.sfdc_id IS NULL
)
LIMIT 50;
```

#### Step 3: Stakeholder Meeting

**Agenda:**
1. Present summary metrics (21% improvement)
2. Show samples of new matches
3. Discuss lost matches and root cause
4. Get approval to proceed OR identify concerns

**Key Questions to Answer:**
- Are the new matches legitimate and valuable?
- Are the lost matches acceptable (false positives)?
- Are there any critical properties in the lost matches?
- Is 21% improvement worth the potential risk?

---

### Phase 5: Decision & Next Steps

#### ✅ Decision: PROCEED

If stakeholders approve:

1. **Schedule Production Cutover**
   - Choose low-traffic time (Sunday 2-3am PST recommended)
   - Follow implementation guide Week 3 plan

2. **Update Workflow**
   - Change notebook path from `modify_address` to `modify_address_v2_test`
   - Remove `_test` suffix from table names in notebook
   - Test in production during scheduled window

3. **Monitor First Run**
   - Watch for errors
   - Verify downstream tasks complete
   - Check Census sync for issues

#### ⚠️ Decision: INVESTIGATE FURTHER

If concerns are raised:

1. **Investigate Specific Cases**
   - Deep dive into lost matches flagged by stakeholders
   - Determine if they're legitimate or false positives
   - Consider if Tier 2 fallback can be improved

2. **Adjust Approach if Needed**
   - Consider hybrid approach (keep some regex for edge cases)
   - Improve Tier 2 fallback matching logic
   - Re-test with adjustments

#### ❌ Decision: DO NOT PROCEED

If critical issues found:

1. **Document Issues**
   - What went wrong?
   - Which matches are problematic?
   - Why is V2 not working as expected?

2. **Clean Up Test Tables**
   ```sql
   DROP TABLE IF EXISTS team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test;
   DROP TABLE IF EXISTS team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test;
   DROP TABLE IF EXISTS team_sandbox.data_engineering.unity_property_duplicate_status_v2_test;
   DROP TABLE IF EXISTS crm.sfdc_dbx.unity_modify_address_v2_test;
   DROP TABLE IF EXISTS team_sandbox.data_engineering.modify_address_v2_validation_summary;
   ```

3. **Revisit Approach**
   - Consider alternative strategies
   - Improve sfdc_id data quality first
   - Re-evaluate later when sfdc_id coverage improves

---

## 🎯 Success Criteria Summary

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **SFDC Properties Matched** | +21% (+2,288) | +15% minimum |
| **Direct sfdc_id Matches** | 75-85% | 70% minimum |
| **New Matches Quality** | Legitimate properties | No clear false positives |
| **Lost Matches** | < 5% of V1 | < 10% of V1 |
| **Lost Matches with Exact Address** | < 20% | < 50% |
| **Duplicate Detection Stable** | Similar distribution | Within 20% |
| **API Flags Consistent** | Within 5% | Within 10% |
| **Overlap with V1** | 95-97% | > 90% |

**Overall Decision:**
- ✅ **Proceed** if 6+ metrics meet target thresholds
- ⚠️ **Investigate** if 3-5 metrics meet target thresholds
- ❌ **Do Not Proceed** if < 3 metrics meet target thresholds

---

## 📊 Expected Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Setup** | 5 min | Upload notebooks |
| **Test Run** | 10-15 min | Execute test notebook |
| **Validation** | 15-20 min | Execute validation notebook |
| **Analysis** | 1-2 hours | Review results, document findings |
| **Stakeholder Review** | 1-2 days | Present findings, get approval |
| **Decision** | 1 day | Go/No-go decision |
| **Production Cutover** | 1 week | If approved, follow Week 3 plan |

**Total Testing Phase:** ~3-4 days

---

## 🚨 Common Issues & Troubleshooting

### Issue: Test notebook fails with permissions error

**Solution:** Run on a cluster with access to all required schemas:
- `rds.pg_rds_public`
- `hive_metastore.salesforce`
- `crm.sfdc_dbx`
- `team_sandbox.data_engineering`

### Issue: V2 shows fewer matches than expected

**Possible Causes:**
1. sfdc_id data quality worse than anticipated
2. Address fallback logic too strict
3. Recent changes to source data

**Action:** Review Cell 2 (match method breakdown) and Cell 6 (lost match analysis)

### Issue: Lost matches include critical properties

**Action:**
1. Identify why they're not matching (no sfdc_id? sfdc_id mismatch?)
2. Consider manual remediation (populate correct sfdc_id in Product)
3. May need hybrid approach for specific edge cases

### Issue: Duplicate detection shows major changes

**Possible Cause:** Different match logic affects duplicate identification

**Action:** Review Cell 9 carefully and determine if changes are acceptable

---

## 📁 Files Reference

| File | Purpose | Location |
|------|---------|----------|
| **Test Notebook** | Run test without affecting production | `notebooks/modify_address_v2_test.sql` |
| **Validation Notebook** | Compare V1 vs V2 results | `notebooks/modify_address_v2_validation.sql` |
| **Implementation Guide** | Full 4-week rollout plan | `docs/sfdc_workflow_simplification_guide.md` |
| **Quick Summary** | One-page overview | `docs/sfdc_workflow_simplification_summary.md` |
| **This Document** | Testing plan and checklist | `docs/modify_address_v2_testing_plan.md` |

---

## ✅ Final Checklist Before Production

Before proceeding to production cutover, ensure:

- [ ] Test notebook executed successfully
- [ ] Validation notebook reviewed completely
- [ ] All metrics meet success criteria
- [ ] Stakeholders reviewed and approved
- [ ] Sample of new matches validated
- [ ] Sample of lost matches reviewed and acceptable
- [ ] No critical properties in lost matches
- [ ] Duplicate detection remains stable
- [ ] API/Partner flags remain consistent
- [ ] Rollback plan documented and understood
- [ ] Production cutover window scheduled
- [ ] Monitoring plan in place for first production run

**Once all boxes checked:** Proceed to Week 3 of implementation guide (Production Cutover)

---

**Questions?** Refer to main implementation guide or reach out to Data Engineering team.
