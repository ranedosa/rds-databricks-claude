# Park Kennedy Feature Sync - ROOT CAUSE IDENTIFIED

**Issue:** Features enabled for Park Kennedy are not syncing to Salesforce
**SFDC ID:** a01Dn00000HHUanIAH

---

## Investigation Results

### CRITICAL FINDINGS:

#### 1. MULTIPLE PROPERTIES WITH SAME SFDC_ID ⚠️

There are **3 properties** named "Park Kennedy" in RDS:

| Property ID | Name | Status | SFDC ID | IDV Enabled |
|------------|------|--------|---------|-------------|
| `5eec38f2-85c9-41f2-bac3-e0e350ec1083` | Park Kennedy | **DISABLED** | a01Dn00000HHUanIAH | false |
| `94246cbb-5eec-4fff-b688-553dcb0e3e29` | Park Kennedy | **ACTIVE** | a01Dn00000HHUanIAH | true |
| `c686cc05-e207-4e65-b3fe-ce9f17edf922` | Park Kennedy - Guarantor | DISABLED | NULL | false |

**Problem:** TWO properties share the SAME `sfdc_id` (a01Dn00000HHUanIAH)

#### 2. ACTIVE PROPERTY HAS FEATURES ENABLED ✓

The **ACTIVE** property (`94246cbb-5eec-4fff-b688-553dcb0e3e29`) has these features enabled:
- ✓ Income Verification (enabled 2025-11-10)
- ✓ Bank Linking (enabled 2025-11-10)
- ✓ Payroll Linking (enabled 2025-11-10)
- ✓ Identity Verification (enabled 2025-11-10)

#### 3. WRONG PROPERTY IN SALESFORCE ✗

Salesforce has records for:
- The **DISABLED** property (`5eec38f2...`) - Record ID: a13UL00000hM1SKYA0
- The Guarantor property (`c686cc05...`) - Record ID: a13UL00000hM1sdYAC

**The ACTIVE property with all the features is NOT in Salesforce!**

#### 4. JOIN FAILURE IN product_property_w_features ✗

The aggregation table shows `product_property_id = NULL` for all Park Kennedy properties.

This means the join failed in the census_pfe notebook:
```sql
left join hive_metastore.salesforce.product_property_c pp
    on pp.sf_property_id_c = p.sfdc_id
```

**Why it failed:** The Salesforce records have `sf_property_id_c = NULL`

#### 5. NOT IN SYNC TABLE ✗

Park Kennedy is **NOT** in `product_property_feature_sync`, which means:
- The sync job won't update it
- Census won't trigger any updates

---

## ROOT CAUSE

**The fundamental issue is:**

1. **Duplicate RDS Properties:** Two "Park Kennedy" properties exist with the same SFDC ID
   - One DISABLED (5eec38f2...)
   - One ACTIVE (94246cbb...)

2. **Wrong Property Synced:** Salesforce has the DISABLED property, not the ACTIVE one

3. **Missing ID Mapping:** The Salesforce field `sf_property_id_c` is NULL, causing join failures

4. **New Property Not Detected:** The ACTIVE property isn't recognized as "new" because:
   - It has an `sfdc_id` populated (a01Dn00000HHUanIAH)
   - The new properties workflow filters out properties with `sfdc_id`
   - This filters out the ACTIVE property from the new properties sync

---

## Why Features Aren't Syncing

The workflow is:
1. **New Properties Task** → Filters out properties where `sfdc_id IS NOT NULL`
   - ACTIVE property has `sfdc_id = a01Dn00000HHUanIAH`
   - So it's excluded from "new properties"

2. **Feature Sync Task** → Joins using `sf_property_id_c = sfdc_id`
   - Salesforce record has `sf_property_id_c = NULL`
   - Join fails, `product_property_id = NULL`

3. **Sync Table** → Only includes properties where features differ AND join succeeded
   - Since join failed, Park Kennedy not included

**Result:** Features have nowhere to sync to

---

## Solution Options

### Option 1: Fix the ACTIVE Property (Recommended)

Make the ACTIVE property recognizable as new:

```sql
-- Clear the sfdc_id from the ACTIVE property so it's treated as "new"
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id = '94246cbb-5eec-4fff-b688-553dcb0e3e29';
```

Then re-run the job, which will:
- Detect it as a new property
- Sync it to Salesforce with all features
- Create proper ID mappings

### Option 2: Fix the Salesforce Record

Update the existing Salesforce record to point to the ACTIVE property:

```sql
-- Update Salesforce to use the ACTIVE property ID
UPDATE crm.salesforce.product_property
SET snappt_property_id_c = '94246cbb-5eec-4fff-b688-553dcb0e3e29',
    sf_property_id_c = 'a01Dn00000HHUanIAH'
WHERE id = 'a13UL00000hM1SKYA0';
```

Then manually trigger feature sync.

### Option 3: Deactivate DISABLED Property

Remove the DISABLED property to eliminate confusion:

```sql
-- Mark DISABLED property as deleted
UPDATE rds.pg_rds_public.properties
SET status = 'DELETED'
WHERE id = '5eec38f2-85c9-41f2-bac3-e0e350ec1083';
```

---

## Immediate Action Required

**Recommended Steps:**

1. **Clarify with team:** Why are there two Park Kennedy properties?
   - Is one a test/old property?
   - Should we keep both?

2. **Choose a solution:**
   - If ACTIVE property should replace DISABLED: Use Option 1
   - If we need to preserve the Salesforce record: Use Option 2
   - If DISABLED property is obsolete: Use Option 3

3. **After fixing, manually trigger sync:**
   ```python
   # In Databricks
   dbutils.notebook.run('/Workspace/Shared/census_pfe', 0)
   dbutils.notebook.run('/Repos/dbx_git/dbx/snappt/product_property_feature_sync', 0)

   # Trigger Census
   import sys
   sys.path.append('/Workspace/Repos/dbx_git/dbx/snappt/python')
   from census_api_triggers import product_property_features
   product_property_features()
   ```

4. **Verify:** Check that features appear in Salesforce after sync

---

## Key Takeaways

- The sync workflow assumes each property has a unique `sfdc_id`
- Having duplicate `sfdc_id` values breaks the workflow
- Properties with `sfdc_id` populated are excluded from "new property" sync
- The feature sync relies on `sf_property_id_c` being populated in Salesforce
- This is a data integrity issue that needs manual intervention

---

## Related Files

- Investigation notebook: `/Users/dane@snappt.com/investigate_park_kennedy`
- Investigation script: `investigate_api.py`
- Feature aggregation: `/Workspace/Shared/census_pfe`
- Feature sync: `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
- Sync job: Job ID 1061000314609635
