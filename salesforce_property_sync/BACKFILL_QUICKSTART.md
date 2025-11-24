# Feature Data Backfill - Quick Start Guide

**Status:** 1,226 of 1,296 synced properties need product feature data corrected

---

## What Happened

Your sync succeeded in creating 1,296 property records in Salesforce. However, product feature fields (Fraud Detection, Income Verification, etc.) were synced as **False** when they should be **True** for 94.6% of properties.

---

## The Fix (Choose One)

### ⚡ Fast Track (30-60 min) - Requires Salesforce Admin

1. Disable "Product Property | After | Rollup Flow" in Salesforce
2. Upload: `/output/sync_payloads/feature_backfill_20251121.csv`
3. Census sync: UPDATE mode, key = `Reverse_ETL_ID__c`
4. Re-enable Flow
5. Done!

### 🛡️ Safe Track (2-3 hours) - No Admin Needed

1. Upload batches from: `/output/sync_payloads/feature_backfill_batches/`
2. Census sync: UPDATE mode, key = `Reverse_ETL_ID__c`
3. Run 26 batches (50 records each)
4. Wait 2-3 min between batches
5. Done!

---

## Census Configuration

**Sync Type:** UPDATE existing records (not INSERT)
**Sync Key:** `Reverse_ETL_ID__c`
**Destination:** Salesforce `Product_Property__c`

**Map these fields:**
- fraud_detection_enabled_c → fraud_detection_enabled_c
- fraud_detection_start_date_c → fraud_detection_start_date_c
- income_verification_enabled_c → income_verification_enabled_c
- income_verification_start_date_c → income_verification_start_date_c
- id_verification_enabled_c → id_verification_enabled_c
- (plus 9 more feature fields - see CSV header)

---

## After Backfill - Validate

```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_feature_data.py
```

Should return: `✅ RESULT: 0 properties with mismatched feature data`

---

## Prevent Future Issues

Update your Census source query to include:
```sql
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
```

Full example in: `/scripts/generate_sync_with_features.py`

---

## Files Ready to Use

✅ `/output/sync_payloads/feature_backfill_20251121.csv` - Full dataset
✅ `/output/sync_payloads/feature_backfill_batches/` - 26 batch files (50 each)
✅ `/docs/URGENT_feature_backfill_required.md` - Detailed documentation

---

**Need help?** See `/docs/URGENT_feature_backfill_required.md` for detailed instructions
