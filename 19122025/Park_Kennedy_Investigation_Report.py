# Databricks notebook source
# MAGIC %md
# MAGIC # Park Kennedy Feature Sync Issue - Investigation Report
# MAGIC
# MAGIC **Issue:** Features enabled for Park Kennedy are not syncing to Salesforce
# MAGIC **SFDC ID:** a01Dn00000HHUanIAH
# MAGIC **Investigated:** 2025-12-19
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Executive Summary
# MAGIC
# MAGIC **ROOT CAUSE IDENTIFIED:** Multiple properties in RDS share the same Salesforce ID, causing the sync workflow to link to the wrong property.
# MAGIC
# MAGIC - ❌ **DISABLED property** is in Salesforce (no features)
# MAGIC - ✅ **ACTIVE property** has features enabled but is NOT in Salesforce
# MAGIC - 🔗 Both properties have the same `sfdc_id` causing mapping conflicts
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check RDS Properties Table
# MAGIC
# MAGIC Let's find all "Park Kennedy" properties in the source RDS database.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     id as property_id,
# MAGIC     name,
# MAGIC     short_id,
# MAGIC     status,
# MAGIC     sfdc_id,
# MAGIC     identity_verification_enabled,
# MAGIC     inserted_at,
# MAGIC     updated_at
# MAGIC FROM rds.pg_rds_public.properties
# MAGIC WHERE name LIKE '%Park Kennedy%'
# MAGIC ORDER BY status DESC, id;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #1: THREE Park Kennedy Properties Found
# MAGIC
# MAGIC | Property ID | Name | Status | SFDC ID | IDV Enabled |
# MAGIC |------------|------|--------|---------|-------------|
# MAGIC | `5eec38f2-85c9-41f2-bac3-e0e350ec1083` | Park Kennedy | **DISABLED** | a01Dn00000HHUanIAH | false |
# MAGIC | `94246cbb-5eec-4fff-b688-553dcb0e3e29` | Park Kennedy | **ACTIVE** | a01Dn00000HHUanIAH | true |
# MAGIC | `c686cc05-e207-4e65-b3fe-ce9f17edf922` | Park Kennedy - Guarantor | DISABLED | NULL | false |
# MAGIC
# MAGIC **⚠️ PROBLEM:** Two properties share the SAME `sfdc_id` (a01Dn00000HHUanIAH)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Check Feature Events (What Features Are Enabled?)
# MAGIC
# MAGIC Let's see what features are enabled for each property by checking the latest feature events.

# COMMAND ----------

# MAGIC %sql
# MAGIC WITH ranked_events AS (
# MAGIC     SELECT
# MAGIC         pfe.property_id,
# MAGIC         p.name,
# MAGIC         p.status,
# MAGIC         pfe.feature_code,
# MAGIC         pfe.event_type,
# MAGIC         pfe.inserted_at,
# MAGIC         pfe._fivetran_deleted,
# MAGIC         ROW_NUMBER() OVER (PARTITION BY pfe.property_id, pfe.feature_code ORDER BY pfe.inserted_at DESC) as event_rank
# MAGIC     FROM rds.pg_rds_public.property_feature_events pfe
# MAGIC     JOIN rds.pg_rds_public.properties p ON p.id = pfe.property_id
# MAGIC     WHERE p.name LIKE '%Park Kennedy%'
# MAGIC )
# MAGIC SELECT
# MAGIC     property_id,
# MAGIC     name,
# MAGIC     status,
# MAGIC     feature_code,
# MAGIC     event_type,
# MAGIC     inserted_at,
# MAGIC     _fivetran_deleted
# MAGIC FROM ranked_events
# MAGIC WHERE event_rank = 1
# MAGIC ORDER BY property_id, feature_code;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #2: ACTIVE Property Has Features Enabled
# MAGIC
# MAGIC **Property:** `94246cbb-5eec-4fff-b688-553dcb0e3e29` (ACTIVE)
# MAGIC
# MAGIC **Enabled Features (as of 2025-11-10):**
# MAGIC - ✅ Income Verification (`income_verification`)
# MAGIC - ✅ Bank Linking (`bank_linking`)
# MAGIC - ✅ Payroll Linking (`payroll_linking`)
# MAGIC - ✅ Identity Verification (`identity_verification`)
# MAGIC
# MAGIC **Disabled Features:**
# MAGIC - ❌ IDV Only Mode (`identity_verification_only_web_portal`)
# MAGIC - ❌ Verification of Rent (`rental_history`)
# MAGIC - ❌ Asset Verification (`asset_verification`)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC **DISABLED Property:** `5eec38f2-85c9-41f2-bac3-e0e350ec1083`
# MAGIC - Has no recent feature events (property is disabled)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Check Feature Aggregation Table
# MAGIC
# MAGIC This table (`product_property_w_features`) is where features are aggregated before syncing to Salesforce.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     property_id,
# MAGIC     sfdc_id,
# MAGIC     product_property_id,
# MAGIC     fraud_enabled,
# MAGIC     iv_enabled,
# MAGIC     idv_enabled,
# MAGIC     idv_only_enabled,
# MAGIC     payroll_linking_enabled,
# MAGIC     bank_linking_enabled,
# MAGIC     vor_enabled
# MAGIC FROM crm.sfdc_dbx.product_property_w_features
# MAGIC WHERE property_id IN (
# MAGIC     SELECT CAST(id AS STRING) FROM rds.pg_rds_public.properties WHERE name LIKE '%Park Kennedy%'
# MAGIC )
# MAGIC ORDER BY property_id;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #3: Features Are Aggregated BUT product_property_id is NULL
# MAGIC
# MAGIC The aggregation correctly identifies features:
# MAGIC
# MAGIC | Property ID | Status | Fraud | IV | IDV | Bank | Payroll | product_property_id |
# MAGIC |------------|--------|-------|----|----|------|---------|-------------------|
# MAGIC | `5eec38f2...` (DISABLED) | a01Dn00000HHUanIAH | ✓ | ❌ | ❌ | ❌ | ❌ | **NULL** |
# MAGIC | `94246cbb...` (ACTIVE) | a01Dn00000HHUanIAH | ✓ | ✅ | ✅ | ✅ | ✅ | **NULL** |
# MAGIC | `c686cc05...` (Guarantor) | NULL | ✓ | ❌ | ❌ | ❌ | ❌ | **NULL** |
# MAGIC
# MAGIC **⚠️ PROBLEM:** `product_property_id = NULL` means the join to Salesforce failed!
# MAGIC
# MAGIC The join uses:
# MAGIC ```sql
# MAGIC left join hive_metastore.salesforce.product_property_c pp
# MAGIC     on pp.sf_property_id_c = p.sfdc_id
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Check Salesforce Records
# MAGIC
# MAGIC Let's see what's actually in Salesforce for Park Kennedy.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     id as salesforce_id,
# MAGIC     name,
# MAGIC     snappt_property_id_c,
# MAGIC     sf_property_id_c,
# MAGIC     reverse_etl_id_c,
# MAGIC     fraud_detection_enabled_c,
# MAGIC     income_verification_enabled_c,
# MAGIC     id_verification_enabled_c,
# MAGIC     idv_only_enabled_c,
# MAGIC     connected_payroll_enabled_c,
# MAGIC     bank_linking_enabled_c,
# MAGIC     verification_of_rent_enabled_c,
# MAGIC     is_deleted,
# MAGIC     created_date,
# MAGIC     last_modified_date
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE name LIKE '%Park Kennedy%'
# MAGIC ORDER BY created_date DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #4: Wrong Property in Salesforce!
# MAGIC
# MAGIC **Salesforce has 2 records:**
# MAGIC
# MAGIC 1. **Park Kennedy** (SF ID: a13UL00000hM1SKYA0)
# MAGIC    - Maps to: `5eec38f2-85c9-41f2-bac3-e0e350ec1083` (DISABLED property)
# MAGIC    - `sf_property_id_c`: **NULL** ⚠️
# MAGIC    - Features: All FALSE ❌
# MAGIC
# MAGIC 2. **Park Kennedy - Guarantor** (SF ID: a13UL00000hM1sdYAC)
# MAGIC    - Maps to: `c686cc05-e207-4e65-b3fe-ce9f17edf922`
# MAGIC    - Features: All FALSE ❌
# MAGIC
# MAGIC **❌ THE ACTIVE PROPERTY WITH FEATURES IS NOT IN SALESFORCE!**
# MAGIC
# MAGIC **Why `sf_property_id_c` is NULL:**
# MAGIC - This field should contain the Salesforce property ID (a01Dn00000HHUanIAH)
# MAGIC - It's used for joining in the feature aggregation
# MAGIC - Being NULL causes the join to fail

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Check Feature Sync Table
# MAGIC
# MAGIC This table contains properties that need feature updates (where features differ between RDS and Salesforce).

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     snappt_property_id_c,
# MAGIC     reverse_etl_id_c,
# MAGIC     name,
# MAGIC     fraud_detection_enabled_c,
# MAGIC     income_verification_enabled_c,
# MAGIC     id_verification_enabled_c,
# MAGIC     bank_linking_enabled_c,
# MAGIC     connected_payroll_enabled_c,
# MAGIC     verification_of_rent_enabled_c,
# MAGIC     idv_only_enabled_c
# MAGIC FROM crm.sfdc_dbx.product_property_feature_sync
# MAGIC WHERE name LIKE '%Park Kennedy%';

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #5: NOT in Sync Table
# MAGIC
# MAGIC **Result:** No records found
# MAGIC
# MAGIC **What this means:**
# MAGIC - Park Kennedy is NOT in the sync queue
# MAGIC - The sync job won't update it
# MAGIC - Census won't be triggered for it
# MAGIC
# MAGIC **Why:**
# MAGIC - The sync table filters to properties where features differ AND the join succeeded
# MAGIC - Since the join to Salesforce failed (product_property_id = NULL), it's excluded

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Verify ID Mapping Issue
# MAGIC
# MAGIC Let's confirm the ID mapping problem.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     p.id as rds_property_id,
# MAGIC     p.name as rds_name,
# MAGIC     p.status,
# MAGIC     p.sfdc_id as rds_sfdc_id,
# MAGIC     sf.id as sf_record_id,
# MAGIC     sf.snappt_property_id_c,
# MAGIC     sf.sf_property_id_c,
# MAGIC     CASE
# MAGIC         WHEN CAST(p.id AS STRING) = sf.snappt_property_id_c THEN '✓ MATCH'
# MAGIC         ELSE '✗ MISMATCH'
# MAGIC     END as snappt_id_mapping,
# MAGIC     CASE
# MAGIC         WHEN p.sfdc_id = sf.sf_property_id_c THEN '✓ MATCH'
# MAGIC         WHEN sf.sf_property_id_c IS NULL THEN '⚠ NULL IN SF'
# MAGIC         ELSE '✗ MISMATCH'
# MAGIC     END as sfdc_id_mapping
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC FULL OUTER JOIN crm.salesforce.product_property sf
# MAGIC     ON sf.name LIKE CONCAT('%', p.name, '%')
# MAGIC WHERE p.name LIKE '%Park Kennedy%' OR sf.name LIKE '%Park Kennedy%'
# MAGIC ORDER BY p.status DESC, p.id;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #6: ID Mapping Failure
# MAGIC
# MAGIC **The Problem:**
# MAGIC
# MAGIC | RDS Property | Status | RDS sfdc_id | SF Record | SF sf_property_id_c | Mapping Status |
# MAGIC |-------------|--------|-------------|-----------|---------------------|----------------|
# MAGIC | `94246cbb...` | ACTIVE | a01Dn00000HHUanIAH | No SF record | N/A | ❌ NOT IN SF |
# MAGIC | `5eec38f2...` | DISABLED | a01Dn00000HHUanIAH | a13UL00000hM1SKYA0 | **NULL** | ⚠️ NULL IN SF |
# MAGIC | `c686cc05...` | DISABLED | NULL | a13UL00000hM1sdYAC | **NULL** | ⚠️ NULL IN SF |
# MAGIC
# MAGIC **Issues:**
# MAGIC 1. ACTIVE property not in Salesforce at all
# MAGIC 2. `sf_property_id_c` is NULL in Salesforce records
# MAGIC 3. Two RDS properties share the same sfdc_id

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Check for Duplicate sfdc_id
# MAGIC
# MAGIC Let's confirm there are duplicate sfdc_id values.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     sfdc_id,
# MAGIC     COUNT(*) as property_count,
# MAGIC     COLLECT_LIST(STRUCT(id, name, status)) as properties
# MAGIC FROM rds.pg_rds_public.properties
# MAGIC WHERE name LIKE '%Park Kennedy%'
# MAGIC     AND sfdc_id IS NOT NULL
# MAGIC GROUP BY sfdc_id
# MAGIC HAVING COUNT(*) > 1;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔍 Finding #7: Confirmed Duplicate sfdc_id
# MAGIC
# MAGIC **SFDC ID `a01Dn00000HHUanIAH` is used by 2 properties:**
# MAGIC - DISABLED property: `5eec38f2-85c9-41f2-bac3-e0e350ec1083`
# MAGIC - ACTIVE property: `94246cbb-5eec-4fff-b688-553dcb0e3e29`
# MAGIC
# MAGIC This violates the expected one-to-one relationship.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## ROOT CAUSE ANALYSIS
# MAGIC
# MAGIC ### Why Features Aren't Syncing
# MAGIC
# MAGIC The sync workflow has 3 paths for getting features to Salesforce:
# MAGIC
# MAGIC #### Path 1: New Properties
# MAGIC ```
# MAGIC new_properties_with_features → Census INSERT → Salesforce
# MAGIC ```
# MAGIC
# MAGIC **Filters:**
# MAGIC ```sql
# MAGIC WHERE sf.snappt_property_id_c IS NULL
# MAGIC   AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
# MAGIC   AND rds.status = 'ACTIVE'
# MAGIC ```
# MAGIC
# MAGIC **Result for ACTIVE Park Kennedy:**
# MAGIC - ❌ Has `sfdc_id = a01Dn00000HHUanIAH` (not NULL)
# MAGIC - **FILTERED OUT** - Not treated as "new"
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC #### Path 2: Feature Sync (Existing Properties)
# MAGIC ```
# MAGIC product_property_w_features → product_property_feature_sync → Census UPDATE → Salesforce
# MAGIC ```
# MAGIC
# MAGIC **Join Logic:**
# MAGIC ```sql
# MAGIC left join hive_metastore.salesforce.product_property_c pp
# MAGIC     on pp.sf_property_id_c = p.sfdc_id
# MAGIC ```
# MAGIC
# MAGIC **Result for ACTIVE Park Kennedy:**
# MAGIC - Salesforce record has `sf_property_id_c = NULL`
# MAGIC - ❌ Join fails, `product_property_id = NULL`
# MAGIC - Not included in sync table
# MAGIC - **NO UPDATE HAPPENS**
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC #### Path 3: Manual Update
# MAGIC ```
# MAGIC Direct Salesforce update (outside workflow)
# MAGIC ```
# MAGIC
# MAGIC **Result:**
# MAGIC - Not attempted
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Summary
# MAGIC
# MAGIC 1. **ACTIVE property has features** ✅
# MAGIC 2. **ACTIVE property blocked from "new property" sync** (has sfdc_id) ❌
# MAGIC 3. **ACTIVE property can't use "feature sync"** (not in Salesforce) ❌
# MAGIC 4. **DISABLED property is in Salesforce** (wrong one) ❌
# MAGIC 5. **Result: Features have nowhere to sync to** ❌
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## SOLUTION OPTIONS
# MAGIC
# MAGIC ### Option 1: Clear sfdc_id from ACTIVE Property (Recommended)
# MAGIC
# MAGIC Treat the ACTIVE property as "new" so it syncs with features.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE rds.pg_rds_public.properties
# MAGIC SET sfdc_id = NULL
# MAGIC WHERE id = '94246cbb-5eec-4fff-b688-553dcb0e3e29';
# MAGIC ```
# MAGIC
# MAGIC **Then:**
# MAGIC - Re-run Job 1061000314609635
# MAGIC - The ACTIVE property will be detected as "new"
# MAGIC - Census will INSERT it to Salesforce with all features
# MAGIC - Proper ID mappings will be created
# MAGIC
# MAGIC **Pros:**
# MAGIC - Clean solution using existing workflow
# MAGIC - Automatic feature sync
# MAGIC - Creates proper mappings
# MAGIC
# MAGIC **Cons:**
# MAGIC - Creates a new Salesforce record
# MAGIC - May need to update references to old SFDC ID
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Option 2: Update Salesforce Record to Point to ACTIVE Property
# MAGIC
# MAGIC Redirect the existing Salesforce record to the ACTIVE property.
# MAGIC
# MAGIC **In Salesforce:**
# MAGIC 1. Update record `a13UL00000hM1SKYA0`:
# MAGIC    - `Snappt_Property_ID__c` = `94246cbb-5eec-4fff-b688-553dcb0e3e29`
# MAGIC    - `SF_Property_ID__c` = `a01Dn00000HHUanIAH`
# MAGIC
# MAGIC **Then:**
# MAGIC - Re-run census_pfe notebook to rebuild product_property_w_features
# MAGIC - Re-run product_property_feature_sync
# MAGIC - Trigger Census sync
# MAGIC
# MAGIC **Pros:**
# MAGIC - Preserves existing Salesforce record
# MAGIC - No new record created
# MAGIC
# MAGIC **Cons:**
# MAGIC - Manual Salesforce update required
# MAGIC - Requires multiple manual steps
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Option 3: Clean Up DISABLED Property
# MAGIC
# MAGIC Remove the DISABLED property to eliminate confusion.
# MAGIC
# MAGIC ```sql
# MAGIC -- Option A: Delete
# MAGIC UPDATE rds.pg_rds_public.properties
# MAGIC SET status = 'DELETED',
# MAGIC     sfdc_id = NULL
# MAGIC WHERE id = '5eec38f2-85c9-41f2-bac3-e0e350ec1083';
# MAGIC
# MAGIC -- Option B: Clear sfdc_id only
# MAGIC UPDATE rds.pg_rds_public.properties
# MAGIC SET sfdc_id = NULL
# MAGIC WHERE id = '5eec38f2-85c9-41f2-bac3-e0e350ec1083';
# MAGIC ```
# MAGIC
# MAGIC **Then:** Use Option 1 or 2 above
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## RECOMMENDED ACTION PLAN
# MAGIC
# MAGIC ### Phase 1: Clarify with Team
# MAGIC
# MAGIC **Questions to answer:**
# MAGIC 1. Why are there two Park Kennedy properties?
# MAGIC 2. Is the DISABLED property obsolete?
# MAGIC 3. Should we keep the existing Salesforce record or create a new one?
# MAGIC 4. Are there any dependencies on the DISABLED property?
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Phase 2: Implement Fix (Option 1)
# MAGIC
# MAGIC If team confirms ACTIVE property should be synced:
# MAGIC
# MAGIC ```sql
# MAGIC -- Step 1: Clear sfdc_id from ACTIVE property
# MAGIC UPDATE rds.pg_rds_public.properties
# MAGIC SET sfdc_id = NULL
# MAGIC WHERE id = '94246cbb-5eec-4fff-b688-553dcb0e3e29';
# MAGIC
# MAGIC -- Step 2: Optionally clean up DISABLED property
# MAGIC UPDATE rds.pg_rds_public.properties
# MAGIC SET status = 'DELETED',
# MAGIC     sfdc_id = NULL
# MAGIC WHERE id = '5eec38f2-85c9-41f2-bac3-e0e350ec1083';
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Phase 3: Trigger Sync
# MAGIC
# MAGIC Wait for Fivetran to sync the changes (or trigger manually), then:
# MAGIC
# MAGIC ```python
# MAGIC # Run the daily sync job
# MAGIC # Job ID: 1061000314609635
# MAGIC # Or run manually:
# MAGIC
# MAGIC # Step 1: Rebuild feature aggregation
# MAGIC dbutils.notebook.run('/Workspace/Shared/census_pfe', 0)
# MAGIC
# MAGIC # Step 2: Create new property record
# MAGIC dbutils.notebook.run('/Repos/dbx_git/dbx/snappt/new_properties_with_features', 0)
# MAGIC
# MAGIC # Step 3: Trigger Census
# MAGIC import sys
# MAGIC sys.path.append('/Workspace/Repos/dbx_git/dbx/snappt/python')
# MAGIC from census_api_triggers import product_property_v2
# MAGIC product_property_v2()
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Phase 4: Verify
# MAGIC
# MAGIC ```sql
# MAGIC -- Check that ACTIVE property is now in Salesforce
# MAGIC SELECT
# MAGIC     id,
# MAGIC     name,
# MAGIC     snappt_property_id_c,
# MAGIC     fraud_detection_enabled_c,
# MAGIC     income_verification_enabled_c,
# MAGIC     bank_linking_enabled_c,
# MAGIC     connected_payroll_enabled_c
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE snappt_property_id_c = '94246cbb-5eec-4fff-b688-553dcb0e3e29';
# MAGIC ```
# MAGIC
# MAGIC **Expected:**
# MAGIC - New Salesforce record exists
# MAGIC - All features are enabled (TRUE)
# MAGIC - Feature dates are populated
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## CONCLUSION
# MAGIC
# MAGIC **Root Cause:** Data integrity issue with duplicate `sfdc_id` values causing the sync workflow to link to the wrong property.
# MAGIC
# MAGIC **Impact:**
# MAGIC - ACTIVE property with features can't sync (blocked by both new property and feature sync paths)
# MAGIC - DISABLED property without features is in Salesforce
# MAGIC - Customer/team sees features enabled in product but not in Salesforce
# MAGIC
# MAGIC **Resolution:** Clear `sfdc_id` from ACTIVE property, let workflow sync it as new
# MAGIC
# MAGIC **Prevention:**
# MAGIC - Add validation to prevent duplicate `sfdc_id` values
# MAGIC - Consider using `snappt_property_id` as the primary linking field instead of `sfdc_id`
# MAGIC - Add monitoring to detect properties with features that aren't syncing
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## RELATED FILES
# MAGIC
# MAGIC - **Diagnostic Guide:** `PARK_KENNEDY_DIAGNOSTIC.md`
# MAGIC - **Root Cause Doc:** `PARK_KENNEDY_ROOT_CAUSE.md`
# MAGIC - **Sync Job:** Databricks Job 1061000314609635
# MAGIC - **Feature Aggregation:** `/Workspace/Shared/census_pfe`
# MAGIC - **Feature Sync:** `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
# MAGIC - **New Properties:** `/Repos/dbx_git/dbx/snappt/new_properties_with_features`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC **Investigation completed:** 2025-12-19
# MAGIC **Next action:** Team decision on which solution to implement
