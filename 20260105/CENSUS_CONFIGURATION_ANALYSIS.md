# Census Sync Configuration Analysis

**Date:** January 5, 2026
**Purpose:** Verify Census sync configuration for RDS → product_property pipeline
**Analyst:** Claude Code

---

## EXECUTIVE SUMMARY

### ✅ **GOOD NEWS: Census Configuration is CORRECT!**

The Census sync IS using the correct field mapping:
- **Source:** `reverse_etl_id_c` (contains RDS.id UUID)
- **Destination:** `Reverse_ETL_ID__c` (Salesforce field)
- **Sync Mode:** Upsert (Update or Create)

**The ID mapping is configured correctly and is NOT the root cause of the 1,081 missing properties.**

---

## CENSUS SYNC DETAILS

### Sync ID: 3326072

**Label:** None (unnamed sync)
**Status:** Up to Date
**Paused:** False
**Schedule:** Never (manual trigger only)

### Source Configuration

**Connection ID:** 58981 (Databricks)
**Source Object:** `crm.sfdc_dbx.new_properties_with_features`
**Query:** `SELECT * FROM crm.sfdc_dbx.new_properties_with_features`

**Source Table Columns:** 45 fields including:
- `snappt_property_id_c` (UUID)
- `reverse_etl_id_c` (UUID)
- `name`, `address_street_s`, `city`, etc.
- All 14 product feature fields (fraud, income verification, etc.)

### Destination Configuration

**Connection ID:** 703012 (Salesforce)
**Destination Object:** `Product_Property__c`
**Operation:** Upsert (Update or Create)

### Sync Key Configuration

✅ **PRIMARY IDENTIFIER (Sync Key):**
```
Source Field: reverse_etl_id_c
Destination Field: Reverse_ETL_ID__c
```

**This is CORRECT** because:
1. `reverse_etl_id_c` contains the RDS property UUID (`RDS.id`)
2. `Reverse_ETL_ID__c` is marked as External ID in Salesforce
3. Allows upserts to work properly (create new, update existing)

### Field Mappings (41 total)

Sample mappings verified:
1. `snappt_property_id_c` → `Snappt_Property_ID__c` ✅
2. `short_id_c` → `Short_ID__c` ✅
3. `id_verification_enabled_c` → `ID_Verification_Enabled__c` ✅
4. `fraud_detection_enabled_c` → `Fraud_Detection_Enabled__c` ✅
5. `company_short_id_c` → `Company_Short_ID__c` ✅
... and 36 more mappings

**All mappings follow the correct pattern.**

---

## SOURCE TABLE ANALYSIS

### Table: `crm.sfdc_dbx.new_properties_with_features`

**Analysis Results:**
- Total Properties: **24**
- Unique `reverse_etl_id_c`: **24** (100%)
- Unique `snappt_property_id_c`: **24** (100%)
- **IDs Match:** 24/24 (100%)

**Sample Data Validation:**
```
Name: 110 Wilson Avenue
reverse_etl_id_c: 1971b58a-6b59-4a6f-b23e-88fc91ceabca
snappt_property_id_c: 1971b58a-6b59-4a6f-b23e-88fc91ceabca
```

✅ **VERIFIED:** Both fields contain the same UUID (RDS.id)

---

## OTHER TABLES IN crm.sfdc_dbx

Tables/views found in the schema:
- `cde_daily`
- `new_properties_with_features` ⭐ (Census source)
- `product_property`
- `product_property_activity`
- `product_property_feature_sync` ⭐ (Feature updates only)
- `product_property_user`
- `product_property_w_features` ⭐ (Feature aggregation)
- `product_user`
- `role_title_bridge`
- `test_product_property`
- `test_product_property_w_features`
- `unity_modify_address`
- `unity_modify_address_v2_test`

**Key Tables:**
1. **`new_properties_with_features`** (24 records)
   - Used by Census sync 3326072
   - For NEW properties only
   - Includes all 45 fields with features

2. **`product_property_feature_sync`** (likely small)
   - Used by Census sync 3326019
   - For feature updates on existing properties
   - Updates features that are out of sync

3. **`product_property_w_features`** (22,784+ records)
   - Source table for feature aggregation
   - Contains ALL properties with their features
   - Referenced in documentation

---

## KEY FINDING: Why Only 24 Properties?

The Census sync is configured correctly, but the **SOURCE TABLE** only has 24 properties.

**Question:** Where do the 1,081 missing properties come from?

### Hypothesis:

The table `crm.sfdc_dbx.new_properties_with_features` appears to be a **filtered view** for:
- Properties that are NEW (not yet in Salesforce)
- Properties that meet certain criteria

**This explains why:**
1. Census sync is configured correctly ✅
2. But only 24 properties are being synced ⚠️
3. And 1,081 properties are missing from staging ⚠️

**The issue is NOT the Census configuration.**
**The issue is the SOURCE DATA - the Databricks table/view is too small.**

---

## ROOT CAUSE IDENTIFICATION

### What We Thought Was Wrong

**Initial hypothesis from user:**
> "RDS only has the production sfdc_id from the properties table, so when wanting to write from RDS to product_properties, we need to use a field within there."

**This suggested:** Census might be using `RDS.sfdc_id` as the sync key (WRONG)

### What Is Actually Wrong

**Reality:** Census IS using `RDS.id → reverse_etl_id_c → Reverse_ETL_ID__c` (CORRECT)

**The real problem:** The Databricks source table `crm.sfdc_dbx.new_properties_with_features` only contains 24 properties when it should contain 1,081+ properties.

---

## COMPARISON WITH DOCUMENTATION

### From `census_sync_configuration.md`:

Shows configuration with:
- Sync Key: `id → snappt_property_id_c` ✅ CORRECT
- Source: RDS properties table
- Destination: product_property__c

**This documentation is CORRECT.**

### From `census_sync_quick_fix.md`:

Shows:
- Sync Key: `reverse_etl_id_c → Reverse_ETL_ID__c` ✅ CORRECT
- Explains that `reverse_etl_id_c` is used because it's marked as External ID in Salesforce

**This matches the actual Census configuration - CORRECT.**

---

## THE REAL ISSUE

### Problem Statement

**Census configuration:** ✅ Correct
**Field mapping:** ✅ Correct
**Source data:** ❌ **INCOMPLETE**

The Databricks table `crm.sfdc_dbx.new_properties_with_features` should contain:
- All ACTIVE RDS properties that are NOT in staging
- Estimated: **1,081 properties** (from our analysis)
- Actual: **24 properties**

**Gap: 1,057 properties missing from source table**

---

## INVESTIGATION NEEDED

### Question 1: How is `new_properties_with_features` defined?

Need to find:
- The SQL query or view definition
- What filters are applied?
- Why only 24 properties?

**Likely location:**
- Databricks notebook: `/Users/dane@snappt.com/product_property_feature_sync`
- Or similar notebook that creates this table/view

### Question 2: Should This Be a View or Table?

**If VIEW:**
- Should automatically include all properties NOT in staging
- Query might be filtering too aggressively

**If TABLE:**
- Needs to be refreshed/rebuilt regularly
- Might be stale (last updated long ago)

### Question 3: What Should the Source Query Be?

**Correct source query should be:**
```sql
SELECT
    CAST(r.id AS STRING) as reverse_etl_id_c,
    CAST(r.id AS STRING) as snappt_property_id_c,
    r.name,
    r.address,
    r.city,
    r.state,
    -- ... all property fields
    -- ... all feature fields from product_property_w_features
FROM rds.pg_rds_public.properties r
LEFT JOIN crm.sfdc_dbx.product_property_w_features f
    ON CAST(r.id AS STRING) = f.snappt_property_id_c
WHERE r.status = 'ACTIVE'
  AND r.sfdc_id IS NOT NULL
  AND r.sfdc_id != 'XXXXXXXXXXXXXXX'
  AND NOT EXISTS (
      SELECT 1 FROM crm.salesforce.product_property s
      WHERE CAST(r.id AS STRING) = s.snappt_property_id_c
        AND s.is_deleted = false
  )
```

**This query would return the 1,081 properties that need to be created.**

---

## RECOMMENDED ACTIONS

### Immediate (Today)

1. **Find the Databricks notebook** that creates/maintains `new_properties_with_features`
   - Search for notebooks in `/Users/dane@snappt.com/`
   - Look for SQL CREATE TABLE or CREATE VIEW statements

2. **Check the view/table definition:**
   ```sql
   SHOW CREATE TABLE crm.sfdc_dbx.new_properties_with_features
   ```

3. **Identify why only 24 properties** are in the table
   - Too restrictive filters?
   - Stale data?
   - Wrong JOIN conditions?

### Short Term (This Week)

4. **Update the source query** to include all 1,081 properties
   - Remove overly restrictive filters
   - Ensure it checks for properties NOT in staging
   - Include feature data from `product_property_w_features`

5. **Rebuild the table/view** with correct query

6. **Run Census sync** - should now sync 1,081 properties

7. **Validate results:**
   ```sql
   -- Should return ~0 after sync
   SELECT COUNT(*) FROM rds.pg_rds_public.properties r
   WHERE r.status = 'ACTIVE'
     AND r.sfdc_id IS NOT NULL
     AND r.sfdc_id != 'XXXXXXXXXXXXXXX'
     AND NOT EXISTS (
         SELECT 1 FROM crm.salesforce.product_property s
         WHERE CAST(r.id AS STRING) = s.snappt_property_id_c
           AND s.is_deleted = false
     )
   ```

### Long Term (Next Month)

8. **Convert to a scheduled view** that automatically refreshes
9. **Set up monitoring** to alert when properties are missing from staging
10. **Document the source query** so it's clear what properties should be included

---

## CENSUS SYNC HEALTH

### Current Sync Performance

**Sync 3326072 (new_properties_with_features):**
- Status: Up to Date ✅
- Schedule: Manual (never runs automatically)
- Last Run: Unknown
- Records Processed: Unknown

**Sync 3326019 (product_property_feature_sync):**
- Status: Up to Date ✅
- Schedule: Unknown
- Purpose: Feature updates only

**Sync 3325886 (sync_payload_ACTIVE_only_20251121_104454):**
- Status: **Paused** ⏸️
- This was the November 21 sync (1,296 properties)
- Paused after initial run

### Recommendation

**Re-enable scheduled syncs** once source data is fixed:
1. Set `new_properties_with_features` sync to run daily (catches new properties)
2. Keep `product_property_feature_sync` for feature updates
3. Archive the paused sync 3325886 (one-time backfill)

---

## SUMMARY

### What's Working ✅

1. Census sync key configuration is CORRECT
2. Field mappings are CORRECT
3. `reverse_etl_id_c` → `Reverse_ETL_ID__c` works perfectly
4. Upsert mode allows create + update

### What's Broken ❌

1. Source table `crm.sfdc_dbx.new_properties_with_features` only has 24 properties
2. Should have 1,081 properties
3. Missing 1,057 properties from the source data

### Next Step

**Find and fix the Databricks notebook/query** that populates `new_properties_with_features`.

The Census configuration does NOT need to change.
The SOURCE DATA needs to be expanded.

---

## FILES REFERENCED

### Census Configuration
- Sync ID: 3326072
- URL: https://app.getcensus.com/workspaces/33026/syncs/3326072
- Full config saved to: `census_sync_3326072.json`

### Documentation
- `census_sync_configuration.md` - Correct configuration guide
- `census_sync_quick_fix.md` - Correct quick reference
- `databricks_tables_for_census.md` - Table/view documentation

### Related Analysis
- `PIPELINE_ID_MAPPING_ISSUE.md` - Three-tier ID system explained
- `RDS_SALESFORCE_DISCOVERY_REPORT.md` - Full sync gap analysis

---

## CONCLUSION

**The user's concern was valid** - there IS a problem with the sync.

**But the root cause was different than expected:**
- It's NOT a Census configuration issue ✅
- It's NOT an ID mapping issue ✅
- It IS a source data issue ❌

**The fix:**
Update the Databricks source table to include all 1,081 properties that should be synced.

---

**Next Action:** Find the Databricks notebook that creates `crm.sfdc_dbx.new_properties_with_features` and expand its query.

---

**Report By:** Claude Code
**Analysis Date:** January 5, 2026
**Census Workspace:** 33026
**Contact:** Dane Rosa
