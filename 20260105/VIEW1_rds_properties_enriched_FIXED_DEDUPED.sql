-- ============================================================================
-- VIEW: rds_properties_enriched (FIXED - Deduplicated)
-- PURPOSE: Enrich RDS properties with feature flags (ONE row per property)
-- FIX: Deduplicate when product_property_w_features has multiple records
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS

WITH properties_base AS (
  -- Get all properties (no join yet)
  SELECT
    p.id AS rds_property_id,
    p.sfdc_id,
    p.short_id,
    p.company_id,
    p.name AS property_name,
    p.status AS property_status,
    p.address AS address,
    p.city AS city,
    p.state AS state,
    p.zip AS postal_code,
    p.created_at,
    p.updated_at,
    p.company_name,
    CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
    CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id
  FROM rds.pg_rds_public.properties p
  WHERE p.company_id IS NOT NULL
    AND p.status != 'DELETED'
),

features_deduplicated AS (
  -- Deduplicate product_property_w_features (pick most recent per property_id)
  SELECT
    property_id,
    idv_enabled,
    bank_linking_enabled,
    payroll_linking_enabled,
    iv_enabled,
    fraud_enabled,
    idv_enabled_at,
    bank_linking_enabled_at,
    payroll_linking_enabled_at,
    iv_enabled_at,
    fraud_enabled_at,
    ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY updated_at DESC NULLS LAST) AS rn
  FROM crm.sfdc_dbx.product_property_w_features
)

SELECT
  -- Property Identifiers
  pb.rds_property_id,
  pb.sfdc_id,
  pb.short_id,
  pb.company_id,

  -- Property Attributes
  pb.property_name,
  pb.property_status,
  pb.address,
  pb.city,
  pb.state,
  pb.postal_code,

  -- Timestamps
  pb.created_at,
  pb.updated_at,

  -- Company Info
  pb.company_name,

  -- Feature Flags from product_property_w_features (deduplicated)
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
  pb.is_active,
  pb.has_valid_sfdc_id

FROM properties_base pb
LEFT JOIN features_deduplicated feat
  ON CAST(pb.rds_property_id AS STRING) = feat.property_id
  AND feat.rn = 1;  -- Only the most recent feature record

COMMENT ON VIEW crm.sfdc_dbx.rds_properties_enriched IS
'Enriched RDS properties with feature flags from product_property_w_features.
FIXED: Deduplicates to ensure ONE row per property_id.
Excludes DELETED properties and those without company_id.';
