-- ============================================================================
-- VIEW: rds_properties_enriched (CORRECTED)
-- PURPOSE: Enrich RDS properties with feature flags
-- CORRECTED: Uses actual column names from schema
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS

SELECT
  -- Property Identifiers
  p.id AS rds_property_id,
  p.sfdc_id,
  p.short_id,
  p.company_id,

  -- Property Attributes
  p.name AS property_name,
  p.status AS property_status,
  p.address AS address,        -- CORRECTED: was address_street
  p.city AS city,              -- CORRECTED: was address_city
  p.state AS state,            -- CORRECTED: was address_state
  p.zip AS postal_code,        -- CORRECTED: was address_postal_code
  -- Note: No country column in properties table

  -- Timestamps
  p.created_at,
  p.updated_at,

  -- Company Info
  p.company_name,

  -- Feature Flags from product_property_w_features (wide format)
  COALESCE(feat.idv_enabled, FALSE) AS idv_enabled,
  COALESCE(feat.bank_linking_enabled, FALSE) AS bank_linking_enabled,
  COALESCE(feat.payroll_linking_enabled, FALSE) AS payroll_enabled,
  COALESCE(feat.iv_enabled, FALSE) AS income_insights_enabled,
  COALESCE(feat.fraud_enabled, FALSE) AS document_fraud_enabled,

  -- Feature Enabled Timestamps
  feat.idv_enabled_at,
  feat.bank_linking_enabled_at,
  feat.payroll_linking_enabled_at,
  feat.iv_enabled_at AS income_insights_enabled_at,
  feat.fraud_enabled_at AS document_fraud_enabled_at,

  -- Calculated Fields
  CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
  CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id

FROM rds.pg_rds_public.properties p
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
  ON CAST(p.id AS STRING) = feat.property_id

WHERE p.company_id IS NOT NULL
  AND p.status != 'DELETED';

-- Add documentation comment
COMMENT ON VIEW crm.sfdc_dbx.rds_properties_enriched IS
'Enriched RDS properties with feature flags from product_property_w_features.
Excludes DELETED properties and those without company_id.';
