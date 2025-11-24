# Databricks notebook source
# MAGIC %md
# MAGIC # New Properties with Features View
# MAGIC
# MAGIC **Purpose:** Create view for Census to sync NEW properties to Salesforce with complete feature data
# MAGIC
# MAGIC **Use Case:** Automated daily sync of new properties from Snappt → Salesforce
# MAGIC
# MAGIC **Created:** 2025-11-21
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## What This Creates
# MAGIC
# MAGIC **View:** `crm.sfdc_dbx.new_properties_with_features`
# MAGIC
# MAGIC **Contents:**
# MAGIC - Properties from `rds.pg_rds_public.properties`
# MAGIC - WITH feature data from `crm.sfdc_dbx.product_property_w_features`
# MAGIC - WHERE NOT already in Salesforce `product_property_c`
# MAGIC
# MAGIC **Census Usage:**
# MAGIC - Census reads this view daily
# MAGIC - INSERTs new records into Salesforce
# MAGIC - Properties get feature data from day 1
# MAGIC
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Ensure Schema Exists

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Ensure the schema exists for our views
# MAGIC CREATE SCHEMA IF NOT EXISTS crm.sfdc_dbx;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create New Properties with Features View
# MAGIC
# MAGIC This view shows properties that:
# MAGIC - Exist in RDS `properties` table
# MAGIC - Do NOT exist in Salesforce `product_property_c` yet
# MAGIC - Are ACTIVE status
# MAGIC - Include ALL feature data from `product_property_w_features`

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW crm.sfdc_dbx.new_properties_with_features AS
# MAGIC SELECT
# MAGIC     -- Property identifiers
# MAGIC     CAST(rds.id AS STRING) as snappt_property_id_c,
# MAGIC     CAST(rds.id AS STRING) as reverse_etl_id_c,
# MAGIC
# MAGIC     -- Basic property info
# MAGIC     rds.name,
# MAGIC     rds.entity_name as entity_name_c,
# MAGIC     rds.address as address_street_s,
# MAGIC     rds.city as address_city_s,
# MAGIC     rds.state as address_state_code_s,
# MAGIC     rds.zip as address_postal_code_s,
# MAGIC     rds.phone as phone_c,
# MAGIC     rds.email as email_c,
# MAGIC     rds.website as website_c,
# MAGIC     rds.logo as logo_c,
# MAGIC     rds.unit as unit_c,
# MAGIC     rds.status as status_c,
# MAGIC     CAST(rds.company_id AS STRING) as company_id_c,
# MAGIC     rds.company_short_id as company_short_id_c,
# MAGIC     rds.short_id as short_id_c,
# MAGIC     rds.bank_statement as bank_statement_c,
# MAGIC     rds.paystub as paystub_c,
# MAGIC     rds.unit_is_required as unit_is_required_c,
# MAGIC     rds.phone_is_required as phone_is_required_c,
# MAGIC     rds.identity_verification_enabled as identity_verification_enabled_c,
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
# MAGIC     feat.vor_updated_at as vor_updated_date_c,
# MAGIC
# MAGIC     -- Required for Salesforce
# MAGIC     FALSE as not_orphan_record_c,
# MAGIC     TRUE as trigger_rollups_c
# MAGIC
# MAGIC FROM rds.pg_rds_public.properties rds
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC     ON CAST(rds.id AS STRING) = feat.property_id
# MAGIC LEFT JOIN hive_metastore.salesforce.product_property_c sf
# MAGIC     ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
# MAGIC WHERE
# MAGIC     -- Only include properties NOT yet in Salesforce
# MAGIC     sf.snappt_property_id_c IS NULL
# MAGIC     AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
# MAGIC     AND rds.status = 'ACTIVE'
# MAGIC ORDER BY rds.updated_at DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Verify View Created Successfully

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check that view exists
# MAGIC DESCRIBE TABLE crm.sfdc_dbx.new_properties_with_features;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Count New Properties
# MAGIC
# MAGIC Check how many properties are ready to sync

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     COUNT(*) as total_new_properties,
# MAGIC     SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as with_fraud_detection,
# MAGIC     SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as with_income_verification,
# MAGIC     SUM(CASE WHEN id_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as with_id_verification,
# MAGIC     SUM(CASE WHEN connected_payroll_enabled_c = TRUE THEN 1 ELSE 0 END) as with_connected_payroll,
# MAGIC     SUM(CASE WHEN bank_linking_enabled_c = TRUE THEN 1 ELSE 0 END) as with_bank_linking,
# MAGIC     SUM(CASE WHEN verification_of_rent_enabled_c = TRUE THEN 1 ELSE 0 END) as with_vor
# MAGIC FROM crm.sfdc_dbx.new_properties_with_features;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Sample Records
# MAGIC
# MAGIC Preview a few properties that will be synced

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     snappt_property_id_c,
# MAGIC     name,
# MAGIC     address_city_s,
# MAGIC     address_state_code_s,
# MAGIC     fraud_detection_enabled_c,
# MAGIC     income_verification_enabled_c,
# MAGIC     id_verification_enabled_c
# MAGIC FROM crm.sfdc_dbx.new_properties_with_features
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Validate Data Quality
# MAGIC
# MAGIC Check for any data issues

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check for missing required fields
# MAGIC SELECT
# MAGIC     COUNT(*) as total_records,
# MAGIC     SUM(CASE WHEN name IS NULL OR name = '' THEN 1 ELSE 0 END) as missing_name,
# MAGIC     SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as missing_id,
# MAGIC     SUM(CASE WHEN address_city_s IS NULL THEN 1 ELSE 0 END) as missing_city,
# MAGIC     SUM(CASE WHEN address_state_code_s IS NULL THEN 1 ELSE 0 END) as missing_state
# MAGIC FROM crm.sfdc_dbx.new_properties_with_features;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC **View Created:** `crm.sfdc_dbx.new_properties_with_features`
# MAGIC
# MAGIC **What's in it:**
# MAGIC - All ACTIVE properties from RDS not yet in Salesforce
# MAGIC - Complete feature data from product_property_w_features
# MAGIC - All 45 fields needed for Salesforce sync
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. Review the record count and sample data above
# MAGIC 2. If everything looks good, proceed to Census configuration
# MAGIC 3. Create Census model pointing to this view
# MAGIC 4. Set up Census sync to INSERT new properties
# MAGIC
# MAGIC **Census Configuration:**
# MAGIC - Source: `crm.sfdc_dbx.new_properties_with_features`
# MAGIC - Destination: Salesforce `Product_Property__c`
# MAGIC - Sync Behavior: INSERT
# MAGIC - Sync Key: `Reverse_ETL_ID__c`
# MAGIC - Schedule: Daily at 2am
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Monitoring Query
# MAGIC
# MAGIC Run this periodically to check if sync is working:

# COMMAND ----------

# MAGIC %sql
# MAGIC -- This should decrease over time as Census syncs properties
# MAGIC SELECT
# MAGIC     COUNT(*) as properties_waiting_to_sync,
# MAGIC     MIN(name) as oldest_property_name
# MAGIC FROM crm.sfdc_dbx.new_properties_with_features;
# MAGIC
# MAGIC -- If this number stays high, check Census sync logs
