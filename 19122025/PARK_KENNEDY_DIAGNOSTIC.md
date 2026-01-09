# Park Kennedy Feature Sync Issue - Diagnostic Guide

**Property:** Park Kennedy
**SFDC ID:** a01Dn00000HHUanIAH
**Issue:** Features are enabled in RDS but not syncing to Salesforce
**Observation:** 2 records found in `crm.salesforce.product_property` for Park Kennedy

---

## Root Cause Analysis

Based on the sync workflow (Job 1061000314609635), I've identified **6 potential root causes**:

### 1. **DUPLICATE SALESFORCE RECORDS** ⭐ Most Likely

**Problem:** You mentioned finding 2 records for Park Kennedy in Salesforce. The feature sync logic may be:
- Matching to the wrong record
- Getting confused by duplicates
- Only updating one record

**How to Check:**
```sql
-- Check for duplicate records
SELECT
    id,
    name,
    snappt_property_id_c,
    sf_property_id_c,
    is_deleted,
    created_date,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
ORDER BY created_date DESC;
```

**What to look for:**
- Are both records active (is_deleted = false)?
- Do they have the same `snappt_property_id_c`?
- Do they have different `sf_property_id_c` values?
- Which record has the SFDC ID a01Dn00000HHUanIAH?

**Fix if confirmed:**
- Delete the duplicate record in Salesforce
- Or update the census_pfe logic to handle duplicates

---

### 2. **ID MAPPING MISMATCH**

**Problem:** The join between RDS and Salesforce uses multiple ID fields:
- `product_property_w_features` joins on `pp.sf_property_id_c = p.sfdc_id` (line in census_pfe)
- Feature sync uses `snappt_property_id_c` for matching
- If these IDs don't align correctly, features won't sync

**How to Check:**
```sql
-- Check ID mapping
SELECT
    p.id as rds_property_id,
    p.name,
    p.sfdc_id as rds_sfdc_id,
    sf.id as salesforce_record_id,
    sf.snappt_property_id_c,
    sf.sf_property_id_c,
    CASE
        WHEN CAST(p.id AS STRING) = sf.snappt_property_id_c THEN '✓ ID Match'
        ELSE '✗ ID MISMATCH'
    END as snappt_id_status,
    CASE
        WHEN p.sfdc_id = sf.sf_property_id_c THEN '✓ SFDC Match'
        ELSE '✗ SFDC MISMATCH'
    END as sfdc_id_status
FROM rds.pg_rds_public.properties p
FULL OUTER JOIN crm.salesforce.product_property sf
    ON p.name = sf.name
WHERE p.name LIKE '%Park Kennedy%' OR sf.name LIKE '%Park Kennedy%';
```

**What to look for:**
- Does `rds_property_id` match `snappt_property_id_c`?
- Does `rds_sfdc_id` match `sf_property_id_c`?
- Are there NULL values in any ID fields?

**Fix if confirmed:**
- Update the Salesforce record with correct IDs
- Or fix the RDS properties table sfdc_id field

---

### 3. **MISSING FROM product_property_w_features TABLE**

**Problem:** The intermediate table `crm.sfdc_dbx.product_property_w_features` might not include Park Kennedy, meaning features never make it to the sync process.

**How to Check:**
```sql
-- Check if Park Kennedy exists in the aggregated features table
SELECT
    property_id,
    sfdc_id,
    product_property_id,
    fraud_enabled,
    iv_enabled,
    idv_enabled,
    idv_only_enabled,
    payroll_linking_enabled,
    bank_linking_enabled,
    vor_enabled
FROM crm.sfdc_dbx.product_property_w_features
WHERE property_id IN (
    SELECT id FROM rds.pg_rds_public.properties WHERE name LIKE '%Park Kennedy%'
);
```

**What to look for:**
- Does Park Kennedy appear in this table at all?
- If yes, are the feature flags correct (matching RDS)?
- Is `product_property_id` NULL?

**Fix if confirmed:**
- Re-run the census_pfe notebook to rebuild the table:
  - Path: `/Workspace/Shared/census_pfe`
- Check if the Fivetran sync has the latest data

---

### 4. **NOT IN THE SYNC TABLE**

**Problem:** The table `crm.sfdc_dbx.product_property_feature_sync` only includes properties where features DIFFER between RDS and Salesforce. If Park Kennedy isn't in this table, Census won't update it.

**How to Check:**
```sql
-- Check if Park Kennedy appears in the sync table
SELECT
    snappt_property_id_c,
    reverse_etl_id_c,
    name,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    verification_of_rent_enabled_c
FROM crm.sfdc_dbx.product_property_feature_sync
WHERE name LIKE '%Park Kennedy%';
```

**What to look for:**
- If Park Kennedy is NOT in this table, it means the job thinks features are already in sync
- Check the WHERE clause logic in the `product_property_feature_sync` notebook

**Fix if confirmed:**
- The sync table is recreated by task 3 of the job
- Check if the comparison logic is working correctly
- May need to manually trigger an update

---

### 5. **FEATURE DATA NOT IN RDS**

**Problem:** Features might not be properly recorded in the source tables:
- `rds.pg_rds_public.property_feature_events` (for most features)
- `rds.pg_rds_public.properties.identity_verification_enabled` (for IDV)

**How to Check:**
```sql
-- Check feature events in RDS
SELECT
    pfe.property_id,
    p.name,
    pfe.feature_code,
    pfe.event_type,
    pfe.inserted_at,
    pfe._fivetran_deleted,
    ROW_NUMBER() OVER (
        PARTITION BY pfe.property_id, pfe.feature_code
        ORDER BY pfe.inserted_at DESC
    ) as event_rank
FROM rds.pg_rds_public.property_feature_events pfe
JOIN rds.pg_rds_public.properties p ON p.id = pfe.property_id
WHERE p.name LIKE '%Park Kennedy%'
    AND pfe._fivetran_deleted = false
ORDER BY pfe.feature_code, pfe.inserted_at DESC;
```

**What to look for:**
- Are the expected features present (income_verification, bank_linking, etc.)?
- Is the latest event (event_rank = 1) an "enabled" event?
- Are there any '_fivetran_deleted = true' records?

**Fix if confirmed:**
- Features need to be enabled in the product application
- Check if Fivetran is syncing property_feature_events properly

---

### 6. **CENSUS SYNC NOT RUNNING OR FAILING**

**Problem:** Even if data is correct in Databricks, Census might not be syncing it to Salesforce.

**How to Check:**
- Check Census sync status: https://app.getcensus.com/workspaces/33026/syncs/
- Look for the product property feature sync (triggered by task 3)
- Check sync logs for errors

**What to look for:**
- Is the sync enabled and scheduled?
- When did it last run successfully?
- Are there any error messages?
- Is it reading from the correct source table?

**Fix if confirmed:**
- Manually trigger the Census sync
- Check Census sync configuration
- Verify Salesforce API limits haven't been hit

---

## Step-by-Step Diagnostic Process

Run these queries in order:

1. **Check Salesforce records** (Problem 1)
2. **Check ID mapping** (Problem 2)
3. **Check product_property_w_features** (Problem 3)
4. **Check feature events in RDS** (Problem 5)
5. **Check sync table** (Problem 4)
6. **Check Census logs** (Problem 6)

---

## Quick Fix Script

Once you've identified the root cause, here's how to force a sync:

```python
# Run this in Databricks
import sys
sys.path.append('/Workspace/Repos/dbx_git/dbx/snappt/python')

# Rebuild the product_property_w_features table
dbutils.notebook.run('/Workspace/Shared/census_pfe', 0)

# Rebuild the sync table
dbutils.notebook.run('/Repos/dbx_git/dbx/snappt/product_property_feature_sync', 0)

# Trigger Census sync
from census_api_triggers import product_property_features
product_property_features()
```

---

## Key Files and Notebooks

- **Feature aggregation:** `/Workspace/Shared/census_pfe`
- **Feature sync:** `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
- **Job configuration:** Job ID 1061000314609635
- **Census sync trigger:** `/Repos/dbx_git/dbx/snappt/python/census_api_triggers.py`

---

## My Hypothesis

Based on the fact that you found **2 records** for Park Kennedy in Salesforce, I believe **Problem #1 (Duplicate Records)** is the most likely root cause.

The join logic in `census_pfe` may be matching to the wrong record or getting confused by duplicates:

```sql
left join hive_metastore.salesforce.product_property_c pp
    on pp.sf_property_id_c = p.sfdc_id
```

If there are 2 records with the same or similar mapping, this could cause:
- Features to sync to the wrong record
- The JOIN to return multiple rows (causing data duplication issues)
- The sync logic to skip the update entirely

**Recommended Action:**
1. Run the duplicate check query first
2. Identify which of the 2 records is the "correct" one (probably the one with SFDC ID a01Dn00000HHUanIAH)
3. Delete or deactivate the duplicate
4. Re-run the sync job

---

## Need More Help?

If none of these diagnostics reveal the issue, we may need to:
1. Check the Census sync configuration directly
2. Review Salesforce Flow logs (there's a trigger_rollups_c flag that fires flows)
3. Check if there's a Salesforce validation rule blocking the update
4. Review the Fivetran sync status to ensure fresh data
