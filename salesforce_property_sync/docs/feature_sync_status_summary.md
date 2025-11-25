# Product Feature Sync - Status Summary

**Date:** 2025-11-21
**Status:** Feature fields exist but need proper data source

---

## Executive Summary

✅ **Good News:**
- Product feature fields **already exist** in Salesforce `product_property_c`
- Your recent sync **is writing** to these fields
- Fields are structured correctly and match Salesforce schema

⚠️ **Current Issue:**
- Feature data is **not sourced from the correct table**
- Your sync pulled data from `rds.pg_rds_public.properties` (doesn't have feature flags)
- Should also pull from `crm.sfdc_dbx.product_property_w_features` (has actual feature enablement data)

**Impact:**
- All 1,296 synced properties show `False` for all products
- This is technically accurate for these new properties (they don't have products enabled yet)
- But future syncs need to include feature data from the `_w_features` table

---

## Field Mapping

### These fields EXIST and ARE synced

| Purpose | Salesforce Field | Currently Synced? | Has Real Data? |
|---------|------------------|-------------------|----------------|
| **Fraud Detection** | | | |
| Enabled flag | `fraud_detection_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `fraud_detection_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| **Income Verification** | | | |
| Enabled flag | `income_verification_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `income_verification_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| Update date | `income_verification_updated_date_c` | ✅ Yes | ❌ No (all NULL) |
| **Identity Verification** | | | |
| Enabled flag | `id_verification_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `id_verification_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| **IDV Only Mode** | | | |
| Enabled flag | `idv_only_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `idv_only_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| **Connected Payroll** | | | |
| Enabled flag | `connected_payroll_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `connected_payroll_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| Update date | `connected_payroll_updated_date_c` | ✅ Yes | ❌ No (all NULL) |
| **Bank Linking** | | | |
| Enabled flag | `bank_linking_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `bank_linking_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| Update date | `bank_linking_updated_date_c` | ✅ Yes | ❌ No (all NULL) |
| **Verification of Rent** | | | |
| Enabled flag | `verification_of_rent_enabled_c` | ✅ Yes | ❌ No (all False) |
| Start date | `vor_start_date_c` | ✅ Yes | ❌ No (all NULL) |
| Update date | `vor_updated_date_c` | ✅ Yes | ❌ No (all NULL) |

---

## Data Source Comparison

### Current Source: `rds.pg_rds_public.properties`

**Has:**
- ✅ Property name, address, company
- ✅ Status, short_id, etc.
- ❌ **No product feature flags**

**Result:**
- Properties sync successfully
- But all feature fields = False/NULL

### Should Also Use: `crm.sfdc_dbx.product_property_w_features`

**Has:**
- ✅ All product enablement flags (fraud_enabled, iv_enabled, etc.)
- ✅ Enablement timestamps
- ✅ Update timestamps
- ✅ 22,784 properties with feature data

**Would Enable:**
- Accurate product enablement flags
- Real activation dates
- Product mix visibility

---

## What Happened in Your Recent Sync

### Properties Synced: 1,296

**Feature Data Status:**
- All `fraud_detection_enabled_c`: **False**
- All `income_verification_enabled_c`: **False**
- All `id_verification_enabled_c`: **False**
- All other feature fields: **False** or **NULL**

**Why?**
The CSV generation script only pulled data from `rds.pg_rds_public.properties`, which doesn't have feature enablement data. The script needed to also LEFT JOIN with `crm.sfdc_dbx.product_property_w_features` to get the actual feature flags.

**Is this wrong?**
Not necessarily! These 1,296 properties were from your "missing" list - properties that were never synced before. It's possible they truly don't have any products enabled yet (all False is accurate).

**The real concern:**
When you sync properties that **DO** have products enabled, the feature data won't be included unless you update the source query.

---

## Solution: Update Census Source Query

### Current Query (Simplified):
```sql
SELECT
    id,
    name,
    address,
    ...
FROM rds.pg_rds_public.properties
WHERE ...
```

### Updated Query (WITH feature data):
```sql
SELECT
    -- Property fields
    rds.id,
    rds.name,
    rds.address,
    ...

    -- Product feature fields
    COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
    feat.fraud_enabled_at as fraud_detection_start_date_c,
    COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
    feat.iv_enabled_at as income_verification_start_date_c,
    COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
    feat.idv_enabled_at as id_verification_start_date_c,
    ...

FROM rds.pg_rds_public.properties rds
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
WHERE ...
```

**Key change:** `LEFT JOIN crm.sfdc_dbx.product_property_w_features`

This will:
- ✅ Include actual product enablement flags
- ✅ Include activation timestamps
- ✅ Show which properties have which products

---

## Next Steps

### Option 1: Update Census Sync (Recommended for Future) ⭐

**For future property syncs:**
1. Update your Census model/source query to include the JOIN with `product_property_w_features`
2. Map all the feature fields
3. Future syncs will have correct feature data

**Pros:**
- One-time update
- All future syncs will be correct
- Clean, maintainable solution

**Cons:**
- Doesn't fix the 1,296 already synced

**Time:** 15-30 minutes

---

### Option 2: Backfill Feature Data for Existing Properties

**For the 1,296 properties already synced:**

**Option A: Re-sync with corrected data**
1. Generate new CSV with feature data included (already done: `sync_with_features.csv`)
2. Re-upload to Census
3. Run as UPDATE operation (not INSERT)
4. Feature data will be populated

**Option B: Separate feature update sync**
1. Create a Census sync specifically for updating feature fields
2. Source: `product_property_w_features`
3. Destination: `product_property_c`
4. Sync behavior: UPDATE only
5. Match on: `snappt_property_id_c`

**Pros:**
- Fixes existing data
- Can run as needed for backfills

**Cons:**
- Extra work
- Need to maintain two syncs (if using Option B)

**Time:** 30-60 minutes

---

### Option 3: Do Nothing (Also Valid) ✅

**Why this might be okay:**
- The 1,296 properties you synced were from the "missing" list
- They likely **don't have products enabled** (all False is correct)
- When properties WITH products get synced, just ensure the source query includes feature data

**Recommendation:**
- Update the Census source query (Option 1) for future syncs
- Don't worry about backfilling the 1,296 unless they actually have products enabled

---

## Validation Queries

### Check if properties should have features enabled

```sql
-- Databricks: See which of your synced properties actually have products
SELECT
    rds.name,
    rds.id,
    feat.fraud_enabled,
    feat.iv_enabled,
    feat.idv_enabled,
    sf.fraud_detection_enabled_c as sf_fraud,
    sf.income_verification_enabled_c as sf_iv
FROM rds.pg_rds_public.properties rds
INNER JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
WHERE DATE(sf.created_date) = CURRENT_DATE()
    AND (feat.fraud_enabled = TRUE OR feat.iv_enabled = TRUE OR feat.idv_enabled = TRUE)
```

If this returns **0 rows**, then all False is correct - no action needed.

If this returns rows, those properties should have been synced with TRUE flags.

---

## Summary Table

| Component | Status | Action Needed |
|-----------|--------|---------------|
| **Salesforce Fields** | ✅ Exist | None |
| **Census Sync** | ✅ Working | None |
| **Field Mapping** | ✅ Correct | None |
| **Data Source** | ⚠️ Incomplete | Update query to include product_property_w_features |
| **Feature Data** | ❌ All False/NULL | Update source OR backfill OR do nothing if accurate |

---

## Recommended Action Plan

**Immediate (Today):**
1. ✅ DONE - Synced 1,296 missing properties
2. ✅ DONE - Verified fields exist in Salesforce
3. ✅ DONE - Generated new CSV with feature data

**Short-term (This Week):**
1. **Update Census source query** to include product_property_w_features JOIN
2. **Test** with a few properties that have products enabled
3. **Validate** feature flags are correct

**Optional (If Needed):**
1. **Backfill** the 1,296 properties IF they should have products enabled
2. Run validation query above to check

**Long-term:**
1. **Monitor** feature data accuracy
2. **Report** on product adoption using Salesforce
3. **Build workflows** based on product enablement

---

## Files Created

**Documentation:**
- `/docs/product_features_sync_plan.md` - Comprehensive plan
- `/docs/feature_sync_status_summary.md` - This document

**Scripts:**
- `/scripts/analyze_product_property_features.py` - Analysis tool
- `/scripts/generate_sync_with_features.py` - CSV generator with features

**Data Files:**
- `/output/sync_payloads/sync_with_features.csv` - Sample CSV with feature data

---

## Questions?

1. **Should we backfill the 1,296 properties?**
   - Run the validation query above to check if they have products enabled

2. **How do I update the Census query?**
   - See the example query in "Solution" section above
   - Or reference `/docs/product_features_sync_plan.md`

3. **Which properties actually have products enabled?**
   - 22,784 total properties in `product_property_w_features`
   - Check with validation queries in the doc

4. **Is this urgent?**
   - Not urgent if the 1,296 properties don't have products
   - Urgent if future syncs need accurate feature data
   - Recommend updating Census query this week for future syncs

---

**Bottom Line:**
- Your sync **technically worked** - fields were populated
- Data source just needs to be expanded to include `product_property_w_features`
- Update the Census query for future syncs to get accurate product data
