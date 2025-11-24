# Databricks Tables/Views for Census

**Notebook:** `/Users/dane@snappt.com/product_property_feature_sync`

**Status:** ✅ Updated and uploaded to Databricks

---

## What the Notebook Creates

When you run this notebook, it will create **3 tables/views** that Census can read from:

### 1. `crm.sfdc_dbx.product_property_feature_backfill` (TABLE)

**Type:** Table (static snapshot)

**Purpose:** One-time backfill for today's 1,296 properties

**Query:**
```sql
SELECT sf.*, feat.*
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
WHERE DATE(sf.created_date) = CURRENT_DATE()
```

**Use Case:**
- Fix today's synced properties with incorrect feature data
- Run Census sync once manually
- Then switch to one of the views below

**Refresh:** Re-run notebook to refresh the table

---

### 2. `crm.sfdc_dbx.product_property_feature_sync` (VIEW) ⭐ **RECOMMENDED**

**Type:** View (always current)

**Purpose:** Ongoing sync for properties with mismatched feature data

**Query:**
```sql
SELECT sf.*, feat.*
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
WHERE sf.fraud_detection_enabled_c != feat.fraud_enabled
   OR sf.income_verification_enabled_c != feat.iv_enabled
   OR ... (checks all 7 products)
```

**Use Case:**
- Scheduled Census sync (hourly or daily)
- Only syncs properties that need updating
- Efficient - won't hit Flow governor limits
- Self-healing - automatically catches any future mismatches

**Refresh:** Automatic (it's a view)

---

### 3. `crm.sfdc_dbx.product_property_feature_recent` (VIEW)

**Type:** View (always current)

**Purpose:** Properties created or updated in last 7 days

**Query:**
```sql
SELECT sf.*, feat.*
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
WHERE DATE(sf.created_date) >= CURRENT_DATE() - INTERVAL 7 DAYS
   OR DATE(sf.last_modified_date) >= CURRENT_DATE() - INTERVAL 7 DAYS
```

**Use Case:**
- Daily scheduled sync to catch new/updated properties
- Good for general maintenance
- Ensures recent changes are always in sync

**Refresh:** Automatic (it's a view)

---

## How to Run the Notebook

### Option 1: Run Manually in Databricks

1. Go to Databricks Workspace
2. Navigate to `/Users/dane@snappt.com/product_property_feature_sync`
3. Click "Run All" button
4. Wait for all cells to complete
5. Tables/views will be created

### Option 2: Schedule the Notebook (Optional)

**For the backfill table only:**
- Schedule notebook to run daily at 1am
- Keeps the table fresh
- Census can sync at 2am

**For the views:**
- No scheduling needed
- Views are always current when queried
- Census reads directly on its own schedule

---

## Census Configuration

Once tables/views are created, connect Census to them:

### Step 1: Create Census Source

1. Go to Census → Models → New Model
2. **Model Name:** `Product Property Feature Sync`
3. **Connection:** Your Databricks connection
4. **Source Type:** Table/View
5. **Table:** Choose one:
   - `crm.sfdc_dbx.product_property_feature_backfill` (one-time)
   - `crm.sfdc_dbx.product_property_feature_sync` (recommended)
   - `crm.sfdc_dbx.product_property_feature_recent` (daily)

### Step 2: Create Census Sync

1. **Source:** The model you created above
2. **Destination:** Salesforce → `Product_Property__c`
3. **Sync Key:** `Reverse_ETL_ID__c`
4. **Sync Behavior:** UPDATE (not insert or upsert)
5. **Field Mappings:** Map all 23 feature fields

### Step 3: Schedule

**For backfill table:**
- Run manually once
- Or schedule notebook + Census sync

**For sync view (recommended):**
- Schedule Census sync: Hourly or daily
- No notebook scheduling needed

**For recent view:**
- Schedule Census sync: Daily at 2am
- No notebook scheduling needed

---

## Field List (23 fields)

All tables/views include these fields:

**Identifiers:**
- `snappt_property_id_c`
- `reverse_etl_id_c`
- `name` (property name)

**Fraud Detection:**
- `fraud_detection_enabled_c`
- `fraud_detection_start_date_c`
- `fraud_detection_updated_date_c`

**Income Verification:**
- `income_verification_enabled_c`
- `income_verification_start_date_c`
- `income_verification_updated_date_c`

**ID Verification:**
- `id_verification_enabled_c`
- `id_verification_start_date_c`
- `id_verification_updated_date_c`

**IDV Only:**
- `idv_only_enabled_c`
- `idv_only_start_date_c`
- `idv_only_updated_date_c`

**Connected Payroll:**
- `connected_payroll_enabled_c`
- `connected_payroll_start_date_c`
- `connected_payroll_updated_date_c`

**Bank Linking:**
- `bank_linking_enabled_c`
- `bank_linking_start_date_c`
- `bank_linking_updated_date_c`

**Verification of Rent:**
- `verification_of_rent_enabled_c`
- `vor_start_date_c`
- `vor_updated_date_c`

---

## Recommended Setup Path

### For Immediate Backfill (Today)

1. **Run notebook** in Databricks (creates all 3 tables/views)
2. **Census source:** `crm.sfdc_dbx.product_property_feature_backfill` table
3. **Run sync manually** once to fix today's 1,296 properties
4. **Validate:** Run validation cell in notebook

### For Long-Term Maintenance (This Week)

1. **Census source:** Switch to `crm.sfdc_dbx.product_property_feature_sync` view
2. **Schedule:** Hourly or daily
3. **Benefit:** Automatically catches and fixes future mismatches
4. **Set and forget:** No manual intervention needed

### For Future Prevention

Update your main property sync to include feature data from the start:
- See `/scripts/generate_sync_with_features.py` for query
- Future new properties will have correct feature data immediately

---

## Advantages of Table/View Approach

**vs Manual CSV:**
- ✅ Automated - no manual CSV generation
- ✅ Scheduled - runs on cron
- ✅ Always current - views show real-time data
- ✅ Self-healing - catches mismatches automatically
- ✅ Repeatable - same process every time

**vs Direct Notebook Queries:**
- ✅ Census can connect to tables/views natively
- ✅ Better performance (tables are materialized)
- ✅ Can query tables directly for debugging
- ✅ Standard Census workflow

---

## Verification

After running the notebook, you can query the tables/views directly:

```sql
-- Check backfill table
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_backfill;

-- Check ongoing sync view (should show mismatches)
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_sync;

-- Check recent view
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_recent;
```

Or use the validation cells built into the notebook.

---

## Summary

✅ **Notebook:** `/Users/dane@snappt.com/product_property_feature_sync`
✅ **Creates:** 3 tables/views for Census
✅ **Recommended:** Use `crm.sfdc_dbx.product_property_feature_sync` view
✅ **Schedule:** Census sync hourly/daily (no notebook scheduling needed)

**Next Steps:**
1. Run notebook in Databricks
2. Connect Census to `crm.sfdc_dbx.product_property_feature_sync` view
3. Configure Census sync as UPDATE operation
4. Schedule and let it run automatically!
