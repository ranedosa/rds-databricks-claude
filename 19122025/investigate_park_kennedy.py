# Databricks notebook source
# Investigation: Park Kennedy Feature Sync Issue
# SFDC ID: a01Dn00000HHUanIAH

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 1: Find Park Kennedy in RDS properties table
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
# MAGIC ORDER BY id;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 2: Check all feature events for Park Kennedy
# MAGIC SELECT
# MAGIC     pfe.property_id,
# MAGIC     p.name,
# MAGIC     pfe.feature_code,
# MAGIC     pfe.event_type,
# MAGIC     pfe.inserted_at,
# MAGIC     pfe._fivetran_deleted,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY pfe.property_id, pfe.feature_code ORDER BY pfe.inserted_at DESC) as event_rank
# MAGIC FROM rds.pg_rds_public.property_feature_events pfe
# MAGIC JOIN rds.pg_rds_public.properties p ON p.id = pfe.property_id
# MAGIC WHERE p.name LIKE '%Park Kennedy%'
# MAGIC ORDER BY pfe.property_id, pfe.feature_code, pfe.inserted_at DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 3: Check Park Kennedy in product_property_w_features (the aggregated feature table)
# MAGIC SELECT
# MAGIC     property_id,
# MAGIC     sfdc_id,
# MAGIC     product_property_id,
# MAGIC     fraud_enabled,
# MAGIC     fraud_enabled_at,
# MAGIC     iv_enabled,
# MAGIC     iv_enabled_at,
# MAGIC     idv_enabled,
# MAGIC     idv_enabled_at,
# MAGIC     idv_only_enabled,
# MAGIC     idv_only_enabled_at,
# MAGIC     payroll_linking_enabled,
# MAGIC     payroll_linking_enabled_at,
# MAGIC     bank_linking_enabled,
# MAGIC     bank_linking_enabled_at,
# MAGIC     vor_enabled,
# MAGIC     vor_enabled_at
# MAGIC FROM crm.sfdc_dbx.product_property_w_features pwf
# MAGIC WHERE property_id IN (
# MAGIC     SELECT id FROM rds.pg_rds_public.properties WHERE name LIKE '%Park Kennedy%'
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 4: Check Park Kennedy in Salesforce product_property table
# MAGIC SELECT
# MAGIC     id as salesforce_id,
# MAGIC     name,
# MAGIC     snappt_property_id_c,
# MAGIC     sf_property_id_c,
# MAGIC     reverse_etl_id_c,
# MAGIC     fraud_detection_enabled_c,
# MAGIC     fraud_detection_start_date_c,
# MAGIC     income_verification_enabled_c,
# MAGIC     income_verification_start_date_c,
# MAGIC     id_verification_enabled_c,
# MAGIC     id_verification_start_date_c,
# MAGIC     idv_only_enabled_c,
# MAGIC     idv_only_start_date_c,
# MAGIC     connected_payroll_enabled_c,
# MAGIC     connected_payroll_start_date_c,
# MAGIC     bank_linking_enabled_c,
# MAGIC     bank_linking_start_date_c,
# MAGIC     verification_of_rent_enabled_c,
# MAGIC     vor_start_date_c,
# MAGIC     is_deleted,
# MAGIC     created_date,
# MAGIC     last_modified_date
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE name LIKE '%Park Kennedy%'
# MAGIC ORDER BY created_date DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 5: Check if Park Kennedy is in the sync table (indicating it needs updating)
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

# MAGIC %sql
# MAGIC -- Step 6: Check for mapping issues - compare RDS property_id with Salesforce snappt_property_id_c
# MAGIC SELECT
# MAGIC     p.id as rds_property_id,
# MAGIC     p.name as rds_name,
# MAGIC     p.sfdc_id as rds_sfdc_id,
# MAGIC     sf.id as sf_record_id,
# MAGIC     sf.snappt_property_id_c,
# MAGIC     sf.sf_property_id_c,
# MAGIC     CASE
# MAGIC         WHEN CAST(p.id AS STRING) = sf.snappt_property_id_c THEN 'MATCH'
# MAGIC         ELSE 'MISMATCH'
# MAGIC     END as id_mapping_status
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC FULL OUTER JOIN crm.salesforce.product_property sf ON sf.name LIKE CONCAT('%', p.name, '%')
# MAGIC WHERE p.name LIKE '%Park Kennedy%' OR sf.name LIKE '%Park Kennedy%'
# MAGIC ORDER BY p.id;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Step 7: Check if there are duplicate Salesforce records
# MAGIC SELECT
# MAGIC     snappt_property_id_c,
# MAGIC     COUNT(*) as record_count,
# MAGIC     COLLECT_LIST(id) as salesforce_ids,
# MAGIC     COLLECT_LIST(is_deleted) as deleted_status
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE name LIKE '%Park Kennedy%'
# MAGIC GROUP BY snappt_property_id_c;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC This notebook investigates why Park Kennedy (SFDC ID: a01Dn00000HHUanIAH) features are not syncing.
# MAGIC
# MAGIC Check the results above to identify:
# MAGIC 1. What features are enabled in RDS
# MAGIC 2. Whether features made it to product_property_w_features
# MAGIC 3. What features are in Salesforce currently
# MAGIC 4. Whether Park Kennedy appears in the sync table
# MAGIC 5. Any ID mapping mismatches
# MAGIC 6. Duplicate Salesforce records
