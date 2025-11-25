# Phase 1 Assets Created ✅

**Date:** 2025-11-21
**Status:** Ready to implement
**Time to implement:** 30 minutes

---

## What Was Created

### 1. Databricks Notebook

**Location in Databricks:** `/Users/dane@snappt.com/new_properties_with_features_view`
**Local backup:** `/notebooks/new_properties_with_features_view.py`
**Status:** ✅ Uploaded and ready to run

**What it does:**
- Creates schema `crm.sfdc_dbx` if needed
- Creates view `crm.sfdc_dbx.new_properties_with_features`
- Validates the view with 6 built-in checks:
  1. Describes table schema (45 columns)
  2. Counts new properties
  3. Shows feature enablement breakdown
  4. Displays sample records
  5. Checks data quality (missing fields)
  6. Includes monitoring query

**The View Query:**
```sql
SELECT
    -- 21 property fields
    -- 23 feature fields
    -- 2 Salesforce control fields
FROM rds.pg_rds_public.properties
LEFT JOIN crm.sfdc_dbx.product_property_w_features  -- Feature data
LEFT JOIN hive_metastore.salesforce.product_property_c  -- Check if exists
WHERE NOT in Salesforce  -- Only new properties
  AND status = 'ACTIVE'
```

---

### 2. Validation Script

**Location:** `/scripts/validate_new_properties_view.py`
**Status:** ✅ Ready to run

**What it does:**
- Verifies view exists (45 columns expected)
- Counts records (should be reasonable)
- Analyzes feature enablement statistics
- Checks data quality (no missing required fields)
- Shows 5 sample records
- Verifies no overlap with existing Salesforce properties
- Provides clear next steps

**Run with:**
```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_new_properties_view.py
```

**Expected output:**
```
✅ View exists with 45 columns
✅ Found X properties ready to sync
✅ Feature enablement breakdown
✅ No data quality issues found
✅ No overlap with existing Salesforce properties

🎯 NEXT STEPS:
   1. Proceed to Census configuration
   2. Create Census model from this view
   3. Set up INSERT sync to Salesforce
```

---

### 3. Implementation Guide

**Location:** `/docs/PHASE_1_QUICKSTART.md`
**Status:** ✅ Complete

**Contents:**
- Step-by-step implementation (4 steps, 30 min)
- Troubleshooting guide
- View query explanation
- Success criteria checklist
- Monitoring queries
- Quick command reference

**Covers:**
- How to run the notebook
- How to validate the view
- How to review the data
- Common issues and fixes
- What to do next (Phase 2)

---

## How to Implement (30 minutes)

### Step 1: Run Databricks Notebook (10 min)

1. Go to Databricks: https://dbc-9ca0f5e0-2208.cloud.databricks.com
2. Navigate to: `/Users/dane@snappt.com/new_properties_with_features_view`
3. Click: **"Run All"**
4. Wait: ~1-2 minutes for completion
5. Review output:
   - Cell 4: Count of new properties
   - Cell 5: Sample data preview
   - Cell 6: Data quality check

### Step 2: Validate the View (5 min)

```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_new_properties_view.py
```

Look for:
- ✅ All checks passing
- Record count is reasonable
- Feature data present
- No data quality issues

### Step 3: Review Results (10 min)

Check the numbers:
- How many new properties?
- How many have features enabled?
- Do sample records look correct?

### Step 4: Document (5 min)

Record:
- Date view created
- Number of properties found
- Any issues noted
- Ready for Phase 2

---

## What This Enables

### Before
❌ New properties synced without feature data
❌ Manual backfills needed
❌ Feature data added separately

### After
✅ New properties include feature data from day 1
✅ Automated - no manual work needed
✅ Self-filtering view (shrinks as properties sync)
✅ Ready for Census scheduled sync

---

## The View in Detail

### Fields Included (45 total)

**Property Fields (21):**
1. snappt_property_id_c
2. reverse_etl_id_c
3. name
4. entity_name_c
5. address_street_s
6. address_city_s
7. address_state_code_s
8. address_postal_code_s
9. phone_c
10. email_c
11. website_c
12. logo_c
13. unit_c
14. status_c
15. company_id_c
16. company_short_id_c
17. short_id_c
18. bank_statement_c
19. paystub_c
20. unit_is_required_c
21. phone_is_required_c
22. identity_verification_enabled_c
23. not_orphan_record_c
24. trigger_rollups_c

**Feature Fields (23):**
25. fraud_detection_enabled_c
26. fraud_detection_start_date_c
27. fraud_detection_updated_date_c
28. income_verification_enabled_c
29. income_verification_start_date_c
30. income_verification_updated_date_c
31. id_verification_enabled_c
32. id_verification_start_date_c
33. id_verification_updated_date_c
34. idv_only_enabled_c
35. idv_only_start_date_c
36. idv_only_updated_date_c
37. connected_payroll_enabled_c
38. connected_payroll_start_date_c
39. connected_payroll_updated_date_c
40. bank_linking_enabled_c
41. bank_linking_start_date_c
42. bank_linking_updated_date_c
43. verification_of_rent_enabled_c
44. vor_start_date_c
45. vor_updated_date_c

---

## Success Criteria

Before moving to Phase 2, verify:

- [ ] Notebook runs without errors
- [ ] View `crm.sfdc_dbx.new_properties_with_features` exists
- [ ] Validation script completes successfully
- [ ] Record count is reasonable (not thousands)
- [ ] Sample data looks correct
- [ ] Feature data is present
- [ ] No data quality issues flagged
- [ ] No overlap with existing Salesforce properties

**All checks passed?** ✅ Proceed to Phase 2!

---

## What's Next

### Phase 2: Configure Census (1 hour)

1. **Create Census Model**
   - Source: `crm.sfdc_dbx.new_properties_with_features`
   - Type: Table/View
   - Connection: Databricks

2. **Create Census Sync**
   - Destination: Salesforce `Product_Property__c`
   - Sync Key: `Reverse_ETL_ID__c`
   - Behavior: INSERT (create new records)
   - Map: All 45 fields

3. **Test**
   - Run manually with first 10 records
   - Verify in Salesforce
   - Check feature fields populated

4. **Schedule**
   - Daily at 2am
   - Or hourly if faster sync needed

**See:** `/docs/FUTURE_ARCHITECTURE_automated_property_sync.md` Section "Phase 2"

---

## Monitoring After Implementation

**Daily check:**
```sql
-- Should be low (0-50)
SELECT COUNT(*) FROM crm.sfdc_dbx.new_properties_with_features;
```

**Weekly check:**
```bash
python scripts/validate_new_properties_view.py
```

**Alert if:**
- Count keeps growing (Census not running?)
- Count > 500 (backlog building?)
- Validation fails (data quality issues?)

---

## Files Reference

| File | Path | Purpose |
|------|------|---------|
| **Databricks Notebook** | `/Users/dane@snappt.com/new_properties_with_features_view` | Creates the view |
| **Notebook Backup** | `/notebooks/new_properties_with_features_view.py` | Local copy |
| **Validation Script** | `/scripts/validate_new_properties_view.py` | Tests the view |
| **Quick Start Guide** | `/docs/PHASE_1_QUICKSTART.md` | Implementation steps |
| **This Summary** | `/PHASE_1_ASSETS_CREATED.md` | Overview |

---

## Architecture Context

This is **Part 1 of 2** in the complete automation:

**Part 1 (This Phase):** New Properties Sync
- Creates new properties WITH features
- Runs daily
- Ensures no missing data going forward

**Part 2 (Already exists):** Feature Updates Sync
- Updates existing properties when features change
- Runs hourly
- Keeps data accurate
- Already configured: https://app.getcensus.com/workspaces/33026/syncs/3326019/overview

**Together they create:** A fully automated, self-healing property & feature sync system

---

## Quick Start

**Ready to implement? Here's what to do:**

```bash
# 1. Open Databricks
https://dbc-9ca0f5e0-2208.cloud.databricks.com

# 2. Navigate to notebook
/Users/dane@snappt.com/new_properties_with_features_view

# 3. Click "Run All"

# 4. When complete, validate:
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_new_properties_view.py

# 5. If validation passes, proceed to Phase 2 (Census setup)
```

---

**Phase 1 Assets: Complete and Ready! ✅**

Next: Implement Phase 1 (30 min) → Then Phase 2 (1 hour) → Fully automated system!
