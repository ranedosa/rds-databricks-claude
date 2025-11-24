# 🚨 URGENT: Feature Data Backfill Required

**Date:** 2025-11-21
**Priority:** HIGH - Action Required Today
**Impact:** 1,226 properties have incorrect product enablement data in Salesforce

---

## Executive Summary

The 1,296 properties synced today to `product_property_c` have **incorrect feature data**:

- ❌ **Currently in Salesforce:** All feature fields = False
- ✅ **Should be:** 1,226 properties have products enabled
- 📊 **Accuracy:** 94.6% of synced properties need correction

**Business Impact:**
- Salesforce shows properties as having NO products enabled
- Reality: Most have Fraud Detection and Income Verification active
- Revenue reporting, CSM workflows, and product analytics are incorrect

---

## What Went Wrong

The original sync payload generated from `/scripts/prepare_missing_properties_for_sync.py` only pulled from `rds.pg_rds_public.properties` which **doesn't have product feature data**.

**Missing JOIN:**
```sql
-- What we did:
FROM rds.pg_rds_public.properties

-- What we should have done:
FROM rds.pg_rds_public.properties rds
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
```

---

## The Numbers

### Properties Needing Correction

| Product | Currently in SF | Should Be | Missing |
|---------|----------------|-----------|---------|
| **Fraud Detection** | 0 | 1,226 | 1,226 ❌ |
| **Income Verification** | 0 | 1,176 | 1,176 ❌ |
| **ID Verification** | 0 | 7 | 7 ❌ |
| **Connected Payroll** | 0 | 5 | 5 ❌ |
| **Bank Linking** | 0 | 4 | 4 ❌ |

### Breakdown
- Total properties synced: **1,296**
- Properties with products enabled: **1,226 (94.6%)**
- Properties correctly synced as False: **70 (5.4%)**

---

## Solution: Feature Data Backfill

### Files Created

**1. Full Backfill CSV:**
```
/output/sync_payloads/feature_backfill_20251121.csv
```
- Contains all 1,296 properties with correct feature data
- Includes all 14 feature fields and timestamps
- Ready for Census UPDATE operation

**2. Batched Files (26 batches × 50 records):**
```
/output/sync_payloads/feature_backfill_batches/
  feature_backfill_batch_001_records_1-50.csv
  feature_backfill_batch_002_records_51-100.csv
  ...
  feature_backfill_batch_026_records_1251-1296.csv
```
- Pre-batched to avoid Salesforce Flow governor limits
- Same issue we hit earlier (Flow "Product Property | After | Rollup Flow")

---

## Implementation Steps

### Option 1: Full Backfill (Fastest)

**Use if:** Your Salesforce admin can temporarily disable the rollup Flow

**Steps:**
1. Ask Salesforce admin to temporarily disable "Product Property | After | Rollup Flow"
2. Upload `/output/sync_payloads/feature_backfill_20251121.csv` to Census
3. Configure as **UPDATE** operation:
   - Sync Key: `Reverse_ETL_ID__c`
   - Sync Behavior: Update existing records
   - Map all feature fields
4. Run sync (should complete in minutes)
5. Re-enable the Flow
6. Manually trigger rollup calculations if needed

**Time:** 30-60 minutes

---

### Option 2: Batched Backfill (Safer)

**Use if:** You can't disable the Flow

**Steps:**
1. Upload batch files from `/output/sync_payloads/feature_backfill_batches/`
2. Configure Census sync as **UPDATE** operation:
   - Sync Key: `Reverse_ETL_ID__c`
   - Sync Behavior: Update existing records
   - Map all feature fields
3. Run batches sequentially:
   - Batch 1: Records 1-50
   - Batch 2: Records 51-100
   - ... (26 batches total)
   - Wait 2-3 minutes between batches
4. Monitor via Census UI or API

**Time:** 2-3 hours (can be automated)

---

### Option 3: Single Large Batch (Test First)

**Use if:** Flow limits may have changed or been optimized

**Steps:**
1. Test with batch 1 (50 records) first
2. If successful, try batch size of 100 records
3. If that works, upload full CSV and run
4. Fall back to Option 2 if fails

---

## Field Mapping for Census

Map these source columns to Salesforce fields:

| CSV Column | Salesforce Field |
|-----------|------------------|
| `snappt_property_id_c` | `snappt_property_id_c` |
| `reverse_etl_id_c` | `reverse_etl_id_c` (Sync Key) |
| `fraud_detection_enabled_c` | `fraud_detection_enabled_c` |
| `fraud_detection_start_date_c` | `fraud_detection_start_date_c` |
| `fraud_detection_updated_date_c` | `fraud_detection_updated_date_c` |
| `income_verification_enabled_c` | `income_verification_enabled_c` |
| `income_verification_start_date_c` | `income_verification_start_date_c` |
| `income_verification_updated_date_c` | `income_verification_updated_date_c` |
| `id_verification_enabled_c` | `id_verification_enabled_c` |
| `id_verification_start_date_c` | `id_verification_start_date_c` |
| `id_verification_updated_date_c` | `id_verification_updated_date_c` |
| `idv_only_enabled_c` | `idv_only_enabled_c` |
| `idv_only_start_date_c` | `idv_only_start_date_c` |
| `idv_only_updated_date_c` | `idv_only_updated_date_c` |
| `connected_payroll_enabled_c` | `connected_payroll_enabled_c` |
| `connected_payroll_start_date_c` | `connected_payroll_start_date_c` |
| `connected_payroll_updated_date_c` | `connected_payroll_updated_date_c` |
| `bank_linking_enabled_c` | `bank_linking_enabled_c` |
| `bank_linking_start_date_c` | `bank_linking_start_date_c` |
| `bank_linking_updated_date_c` | `bank_linking_updated_date_c` |
| `verification_of_rent_enabled_c` | `verification_of_rent_enabled_c` |
| `vor_start_date_c` | `vor_start_date_c` |
| `vor_updated_date_c` | `vor_updated_date_c` |

---

## Validation After Backfill

Run this script to verify the backfill worked:

```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_feature_data.py
```

**Expected result after backfill:**
```
✅ RESULT: 0 properties with mismatched feature data
```

---

## Preventing This in the Future

### Immediate Action (This Week)

**Update Census Source Query** to include product feature data for ALL future syncs.

**Location to update:** Your Census model configuration

**Current query structure:**
```sql
FROM rds.pg_rds_public.properties
WHERE ...
```

**Updated query structure:**
```sql
FROM rds.pg_rds_public.properties rds
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
WHERE ...
```

**Reference:** See `/scripts/generate_sync_with_features.py:88-97` for full query example

### Long-term Solution

**Option A:** Consolidate into one comprehensive sync
- Single Census model with all fields
- Includes basic property data + feature flags
- Easier to maintain

**Option B:** Separate feature sync
- Keep property sync as-is
- Add second sync just for feature data updates
- More modular but two syncs to maintain

See `/docs/product_features_sync_plan.md` for detailed implementation plans

---

## Timeline

**Today (2025-11-21):**
- ✅ Identified issue: 1,226 properties with incorrect data
- ✅ Generated backfill CSV with correct data
- ✅ Created 26 batch files to avoid Flow limits
- 🔲 **TO DO:** Run backfill sync (2-3 hours)

**This Week:**
- 🔲 Update Census source query for future syncs
- 🔲 Test updated query with small batch
- 🔲 Document new sync process

---

## Questions & Support

**Generated by:** `/scripts/validate_feature_data.py`
**Backfill CSV:** `/scripts/generate_feature_backfill.py`
**Batch files:** `/scripts/create_feature_backfill_batches.py`

**Related Documentation:**
- `/docs/feature_sync_status_summary.md` - Full feature analysis
- `/docs/product_features_sync_plan.md` - Long-term solution plan
- `/docs/sync_error_solution.md` - Flow governor limit workaround

---

## Critical Path Forward

1. **Immediate (Today):** Run feature backfill using batched approach
2. **Short-term (This Week):** Update Census query to include feature data
3. **Ongoing:** Monitor feature data accuracy in Salesforce

**Bottom Line:**
The sync technically worked - records were created successfully. But the data source was incomplete. The backfill CSV has been generated and is ready to upload to Census to fix the 1,226 properties with incorrect feature data.
