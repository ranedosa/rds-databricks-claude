-- ============================================================================
-- VIEW: properties_to_create
-- PURPOSE: Queue of properties that need to be CREATED in Salesforce
-- LOGIC: Properties in RDS but NOT in Salesforce product_property table
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_create AS

SELECT
  -- Identifiers (Census will use these)
  agg.rds_property_id,
  agg.sfdc_id,
  agg.short_id,
  agg.company_id,

  -- Property Metadata
  agg.property_name,
  agg.address,
  agg.city,
  agg.state,
  agg.postal_code,
  agg.company_name,

  -- Feature Flags
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

  -- Aggregation Metrics (for monitoring)
  agg.active_property_count,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
LEFT JOIN crm.salesforce.product_property sf
  ON agg.sfdc_id = sf.sf_property_id_c
  AND sf.is_deleted = FALSE

WHERE sf.id IS NULL  -- NOT in Salesforce = needs to be CREATED
  AND agg.sfdc_id IS NOT NULL  -- Must have valid SFDC ID to create

ORDER BY agg.created_at DESC;  -- Newest first

-- Add documentation
COMMENT ON VIEW crm.sfdc_dbx.properties_to_create IS
'Properties that exist in RDS but NOT in Salesforce product_property.
Census Sync A (CREATE) will use this view to create ~1,081 missing properties.';
