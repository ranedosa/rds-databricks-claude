-- ============================================================================
-- VIEW: properties_to_update (FIXED - Handles SF Duplicates)
-- PURPOSE: Queue of properties that need to be UPDATED in Salesforce
-- FIX: Deduplicate when multiple SF records share same sf_property_id_c
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS

WITH sf_deduplicated AS (
  -- If multiple SF records have same sf_property_id_c, pick the most recent
  SELECT
    sf_property_id_c,
    snappt_property_id_c,
    id AS sf_id,
    ROW_NUMBER() OVER (PARTITION BY sf_property_id_c ORDER BY last_modified_date DESC) AS rn
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
    AND sf_property_id_c IS NOT NULL
)

SELECT
  -- Identifiers (Census will use these)
  sf.snappt_property_id_c,  -- Census sync key for UPDATE mode
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

  -- Aggregation Metrics
  agg.active_property_count,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
INNER JOIN sf_deduplicated sf
  ON agg.sfdc_id = sf.sf_property_id_c
  AND sf.rn = 1  -- Only the most recent SF record

WHERE agg.sfdc_id IS NOT NULL

ORDER BY agg.rds_last_updated_at DESC;

COMMENT ON VIEW crm.sfdc_dbx.properties_to_update IS
'Properties that exist in BOTH RDS and Salesforce product_property.
FIXED: Deduplicates when multiple SF records share same sf_property_id_c (picks most recent).
Census Sync B (UPDATE) will use this view to update existing properties.';
