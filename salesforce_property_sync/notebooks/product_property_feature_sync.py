# Databricks notebook source
# MAGIC %md
# MAGIC # Product Property Feature Sync
# MAGIC
# MAGIC **Purpose:** Sync product feature enablement data to Salesforce product_property_c
# MAGIC
# MAGIC **Use Case:** Census reverse ETL to keep Salesforce feature flags accurate
# MAGIC
# MAGIC **Created:** 2025-11-21
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## What This Notebook Does
# MAGIC
# MAGIC This notebook creates **tables/views** that Census can read from to sync product feature data.
# MAGIC
# MAGIC **Output Tables:**
# MAGIC - `crm.sfdc_dbx.product_property_feature_backfill` - One-time backfill
# MAGIC - `crm.sfdc_dbx.product_property_feature_sync` - Ongoing sync (mismatches only)
# MAGIC - `crm.sfdc_dbx.product_property_feature_recent` - Recent updates (last 7 days)
# MAGIC
# MAGIC **Feature Fields:**
# MAGIC - Fraud Detection, Income Verification, ID Verification
# MAGIC - IDV Only Mode, Connected Payroll, Bank Linking
# MAGIC - Verification of Rent
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## How to Use
# MAGIC
# MAGIC 1. Run this notebook to create/refresh the tables
# MAGIC 2. Connect Census to one of the output tables
# MAGIC 3. Configure Census to UPDATE Salesforce product_property_c records
# MAGIC 4. Schedule Census sync (and optionally this notebook)
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Ensure Schema Exists

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Ensure the schema exists
# MAGIC CREATE SCHEMA IF NOT EXISTS crm.sfdc_dbx;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 1: One-Time Backfill (Today's Properties)
# MAGIC
# MAGIC Use this to fix properties synced today that have incorrect feature data.
# MAGIC
# MAGIC **Table:** `crm.sfdc_dbx.product_property_feature_backfill`
# MAGIC
# MAGIC **When to use:** Initial backfill for recently synced properties
# MAGIC
# MAGIC **Census setup:** Point to this table, run once, then switch to ongoing sync

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Drop and recreate for fresh data
# MAGIC DROP TABLE IF EXISTS crm.sfdc_dbx.product_property_feature_backfill;
# MAGIC
# MAGIC CREATE TABLE crm.sfdc_dbx.product_property_feature_backfill AS
# MAGIC SELECT
# MAGIC     -- Identifiers for Census upsert
# MAGIC     sf.snappt_property_id_c,
# MAGIC     sf.reverse_etl_id_c,
# MAGIC
# MAGIC     -- Property info (for reference/debugging)
# MAGIC     sf.name,
# MAGIC
# MAGIC     -- Fraud Detection
# MAGIC     COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
# MAGIC     feat.fraud_enabled_at as fraud_detection_start_date_c,
# MAGIC     feat.fraud_updated_at as fraud_detection_updated_date_c,
# MAGIC
# MAGIC     -- Income Verification
# MAGIC     COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
# MAGIC     feat.iv_enabled_at as income_verification_start_date_c,
# MAGIC     feat.iv_updated_at as income_verification_updated_date_c,
# MAGIC
# MAGIC     -- ID Verification
# MAGIC     COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
# MAGIC     feat.idv_enabled_at as id_verification_start_date_c,
# MAGIC     feat.idv_updated_at as id_verification_updated_date_c,
# MAGIC
# MAGIC     -- IDV Only Mode
# MAGIC     COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
# MAGIC     feat.idv_only_enabled_at as idv_only_start_date_c,
# MAGIC     feat.idv_only_updated_at as idv_only_updated_date_c,
# MAGIC
# MAGIC     -- Connected Payroll
# MAGIC     COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
# MAGIC     feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
# MAGIC     feat.payroll_linking_updated_at as connected_payroll_updated_date_c,
# MAGIC
# MAGIC     -- Bank Linking
# MAGIC     COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
# MAGIC     feat.bank_linking_enabled_at as bank_linking_start_date_c,
# MAGIC     feat.bank_linking_updated_at as bank_linking_updated_date_c,
# MAGIC
# MAGIC     -- Verification of Rent
# MAGIC     COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
# MAGIC     feat.vor_enabled_at as vor_start_date_c,
# MAGIC     feat.vor_updated_at as vor_updated_date_c
# MAGIC
# MAGIC FROM crm.salesforce.product_property_c sf
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC     ON sf.snappt_property_id_c = feat.property_id
# MAGIC WHERE DATE(sf.created_date) = CURRENT_DATE()
# MAGIC ORDER BY sf.name;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify the table
# MAGIC SELECT
# MAGIC     COUNT(*) as total_records,
# MAGIC     SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as fraud_enabled_count,
# MAGIC     SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as iv_enabled_count
# MAGIC FROM crm.sfdc_dbx.product_property_feature_backfill;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 2: Ongoing Sync (Mismatched Feature Data) ⭐ RECOMMENDED
# MAGIC
# MAGIC Use this as your regular Census source for keeping feature data in sync.
# MAGIC
# MAGIC **Table:** `crm.sfdc_dbx.product_property_feature_sync`
# MAGIC
# MAGIC **When to use:** Scheduled daily/hourly sync to catch any mismatches
# MAGIC
# MAGIC **Benefit:** Only includes properties that need updating (efficient, won't hit Flow limits)
# MAGIC
# MAGIC **This is a VIEW** - always shows current mismatches when queried

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create or replace view for ongoing sync
# MAGIC CREATE OR REPLACE VIEW crm.sfdc_dbx.product_property_feature_sync AS
# MAGIC SELECT
# MAGIC     sf.snappt_property_id_c,
# MAGIC     sf.reverse_etl_id_c,
# MAGIC     sf.name,
# MAGIC
# MAGIC     -- Fraud Detection
# MAGIC     COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
# MAGIC     feat.fraud_enabled_at as fraud_detection_start_date_c,
# MAGIC     feat.fraud_updated_at as fraud_detection_updated_date_c,
# MAGIC
# MAGIC     -- Income Verification
# MAGIC     COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
# MAGIC     feat.iv_enabled_at as income_verification_start_date_c,
# MAGIC     feat.iv_updated_at as income_verification_updated_date_c,
# MAGIC
# MAGIC     -- ID Verification
# MAGIC     COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
# MAGIC     feat.idv_enabled_at as id_verification_start_date_c,
# MAGIC     feat.idv_updated_at as id_verification_updated_date_c,
# MAGIC
# MAGIC     -- IDV Only Mode
# MAGIC     COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
# MAGIC     feat.idv_only_enabled_at as idv_only_start_date_c,
# MAGIC     feat.idv_only_updated_at as idv_only_updated_date_c,
# MAGIC
# MAGIC     -- Connected Payroll
# MAGIC     COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
# MAGIC     feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
# MAGIC     feat.payroll_linking_updated_at as connected_payroll_updated_date_c,
# MAGIC
# MAGIC     -- Bank Linking
# MAGIC     COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
# MAGIC     feat.bank_linking_enabled_at as bank_linking_start_date_c,
# MAGIC     feat.bank_linking_updated_at as bank_linking_updated_date_c,
# MAGIC
# MAGIC     -- Verification of Rent
# MAGIC     COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
# MAGIC     feat.vor_enabled_at as vor_start_date_c,
# MAGIC     feat.vor_updated_at as vor_updated_date_c
# MAGIC
# MAGIC FROM crm.salesforce.product_property_c sf
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC     ON sf.snappt_property_id_c = feat.property_id
# MAGIC WHERE
# MAGIC     -- Only include records where feature data differs
# MAGIC     (sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
# MAGIC      OR sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
# MAGIC      OR sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
# MAGIC      OR sf.idv_only_enabled_c != COALESCE(feat.idv_only_enabled, FALSE)
# MAGIC      OR sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
# MAGIC      OR sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
# MAGIC      OR sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE))
# MAGIC ORDER BY sf.name;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify the view
# MAGIC SELECT
# MAGIC     COUNT(*) as total_mismatches,
# MAGIC     SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as fraud_should_be_enabled,
# MAGIC     SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as iv_should_be_enabled
# MAGIC FROM crm.sfdc_dbx.product_property_feature_sync;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 3: Recent Updates (Last 7 Days)
# MAGIC
# MAGIC Use this to sync properties created or updated in the last week.
# MAGIC
# MAGIC **Table:** `crm.sfdc_dbx.product_property_feature_recent`
# MAGIC
# MAGIC **When to use:** Daily scheduled sync to catch new/updated properties
# MAGIC
# MAGIC **This is a VIEW** - always shows last 7 days when queried

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create or replace view for recent updates
# MAGIC CREATE OR REPLACE VIEW crm.sfdc_dbx.product_property_feature_recent AS
# MAGIC SELECT
# MAGIC     sf.snappt_property_id_c,
# MAGIC     sf.reverse_etl_id_c,
# MAGIC     sf.name,
# MAGIC
# MAGIC     -- Fraud Detection
# MAGIC     COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
# MAGIC     feat.fraud_enabled_at as fraud_detection_start_date_c,
# MAGIC     feat.fraud_updated_at as fraud_detection_updated_date_c,
# MAGIC
# MAGIC     -- Income Verification
# MAGIC     COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
# MAGIC     feat.iv_enabled_at as income_verification_start_date_c,
# MAGIC     feat.iv_updated_at as income_verification_updated_date_c,
# MAGIC
# MAGIC     -- ID Verification
# MAGIC     COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
# MAGIC     feat.idv_enabled_at as id_verification_start_date_c,
# MAGIC     feat.idv_updated_at as id_verification_updated_date_c,
# MAGIC
# MAGIC     -- IDV Only Mode
# MAGIC     COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
# MAGIC     feat.idv_only_enabled_at as idv_only_start_date_c,
# MAGIC     feat.idv_only_updated_at as idv_only_updated_date_c,
# MAGIC
# MAGIC     -- Connected Payroll
# MAGIC     COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
# MAGIC     feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
# MAGIC     feat.payroll_linking_updated_at as connected_payroll_updated_date_c,
# MAGIC
# MAGIC     -- Bank Linking
# MAGIC     COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
# MAGIC     feat.bank_linking_enabled_at as bank_linking_start_date_c,
# MAGIC     feat.bank_linking_updated_at as bank_linking_updated_date_c,
# MAGIC
# MAGIC     -- Verification of Rent
# MAGIC     COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
# MAGIC     feat.vor_enabled_at as vor_start_date_c,
# MAGIC     feat.vor_updated_at as vor_updated_date_c
# MAGIC
# MAGIC FROM crm.salesforce.product_property_c sf
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC     ON sf.snappt_property_id_c = feat.property_id
# MAGIC WHERE
# MAGIC     -- Include properties created or updated in last 7 days
# MAGIC     (DATE(sf.created_date) >= CURRENT_DATE() - INTERVAL 7 DAYS
# MAGIC      OR DATE(sf.last_modified_date) >= CURRENT_DATE() - INTERVAL 7 DAYS)
# MAGIC ORDER BY sf.name;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify the view
# MAGIC SELECT
# MAGIC     COUNT(*) as total_recent,
# MAGIC     SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as fraud_enabled_count,
# MAGIC     SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as iv_enabled_count
# MAGIC FROM crm.sfdc_dbx.product_property_feature_recent;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation: Check Current Mismatches
# MAGIC
# MAGIC Run this to see how many properties have mismatched feature data across ALL products

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check for mismatches across all products
# MAGIC SELECT
# MAGIC     COUNT(*) as total_properties,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as fraud_mismatches,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as iv_mismatches,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as idv_mismatches,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as payroll_mismatches,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as bank_mismatches,
# MAGIC
# MAGIC     SUM(CASE WHEN sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE)
# MAGIC         THEN 1 ELSE 0 END) as vor_mismatches
# MAGIC
# MAGIC FROM crm.salesforce.product_property_c sf
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC     ON sf.snappt_property_id_c = feat.property_id;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary: Tables Created
# MAGIC
# MAGIC This notebook created the following tables/views for Census:
# MAGIC
# MAGIC ### 1. `crm.sfdc_dbx.product_property_feature_backfill` (TABLE)
# MAGIC - **Purpose:** One-time backfill for today's properties
# MAGIC - **Type:** Table (static snapshot)
# MAGIC - **Usage:** Census one-time sync
# MAGIC - **Refresh:** Re-run notebook to refresh
# MAGIC
# MAGIC ### 2. `crm.sfdc_dbx.product_property_feature_sync` (VIEW) ⭐ RECOMMENDED
# MAGIC - **Purpose:** Ongoing sync for mismatched properties
# MAGIC - **Type:** View (always current)
# MAGIC - **Usage:** Census scheduled sync (hourly/daily)
# MAGIC - **Benefit:** Only syncs what needs updating
# MAGIC
# MAGIC ### 3. `crm.sfdc_dbx.product_property_feature_recent` (VIEW)
# MAGIC - **Purpose:** Recent updates (last 7 days)
# MAGIC - **Type:** View (always current)
# MAGIC - **Usage:** Census daily sync
# MAGIC - **Benefit:** Catches new/updated properties
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Census Setup
# MAGIC
# MAGIC **For each table/view:**
# MAGIC
# MAGIC 1. **Census Source:**
# MAGIC    - Connection: Databricks
# MAGIC    - Type: Table
# MAGIC    - Table: Choose one of the above
# MAGIC
# MAGIC 2. **Census Destination:**
# MAGIC    - Salesforce → `Product_Property__c`
# MAGIC
# MAGIC 3. **Sync Configuration:**
# MAGIC    - Sync Key: `Reverse_ETL_ID__c`
# MAGIC    - Sync Behavior: **UPDATE** (not insert)
# MAGIC    - Map all 23 feature fields
# MAGIC
# MAGIC 4. **Schedule:**
# MAGIC    - Backfill table: Run once manually
# MAGIC    - Sync view: Hourly or daily (recommended)
# MAGIC    - Recent view: Daily at 2am
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Notebook Scheduling
# MAGIC
# MAGIC **For static table (backfill):**
# MAGIC - Schedule this notebook to refresh the table daily at 1am
# MAGIC - Census reads the refreshed table at 2am
# MAGIC
# MAGIC **For views (sync/recent):**
# MAGIC - No notebook scheduling needed
# MAGIC - Views always show current data when queried
# MAGIC - Census can read directly on schedule
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Documentation
# MAGIC
# MAGIC See also:
# MAGIC - `/docs/census_databricks_notebook_setup.md` - Detailed setup guide
# MAGIC - `/docs/URGENT_feature_backfill_required.md` - Problem analysis
# MAGIC - `/docs/product_features_sync_plan.md` - Implementation plan
