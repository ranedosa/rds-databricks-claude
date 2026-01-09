-- ============================================================================
-- VIEW: properties_to_update
-- PURPOSE: Queue of properties that need to be UPDATED in Salesforce
-- LOGIC: Properties that EXIST in both RDS and Salesforce
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS

SELECT
  -- Identifiers (Census will use these)
  sf.snappt_property_id_c,  -- Census sync key for UPDATE mode
  agg.rds_property_id,
  agg.sfdc_id,
  agg.short_id,
  agg.company_id,

  -- Property Metadata (may have changed in RDS)
  agg.property_name,
  agg.address,
  agg.city,
  agg.state,
  agg.postal_code,
  agg.company_name,

  -- Feature Flags (aggregated from RDS)
  agg.idv_enabled,
  agg.bank_linking_enabled,
  agg.payroll_enabled,
  agg.income_insights_enabled,
  agg.document_fraud_enabled,

  -- Feature Timestamps
  agg.idv_enabled_at,
  agg.bank_linking_enabled_at,
  agg.payroll_enabled_at,
  agg.income_insights_enabled_at,
  agg.document_fraud_enabled_at,

  -- Timestamps
  agg.created_at,
  agg.rds_last_updated_at,

  -- Aggregation Metrics (NEW - these are what fix the multi-property issue!)
  agg.active_property_count,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
INNER JOIN crm.salesforce.product_property sf
  ON agg.sfdc_id = sf.sf_property_id_c
  AND sf.is_deleted = FALSE

WHERE agg.sfdc_id IS NOT NULL  -- Must have valid SFDC ID

ORDER BY agg.rds_last_updated_at DESC;  -- Most recently changed first

-- Add documentation
COMMENT ON VIEW crm.sfdc_dbx.properties_to_update IS
'Properties that exist in BOTH RDS and Salesforce product_property.
Census Sync B (UPDATE) will use this view to update ~7,980 existing properties.
Includes aggregation fields (active_property_count, is_multi_property) that solve the multi-property problem.';
