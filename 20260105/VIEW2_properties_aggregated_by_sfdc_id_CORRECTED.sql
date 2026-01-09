-- ============================================================================
-- VIEW: properties_aggregated_by_sfdc_id (CORRECTED)
-- PURPOSE: Aggregate multiple RDS properties → single SFDC ID
-- BUSINESS RULES:
--   1. Only ACTIVE properties contribute
--   2. Feature flags: ANY active property has feature → TRUE (UNION logic)
--   3. Timestamps: Earliest enabled date across all properties
--   4. Property metadata: From most recently updated property
--   5. Full audit trail: Count of properties aggregated
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id AS

WITH active_properties AS (
  -- Filter to only ACTIVE properties with valid SFDC IDs
  SELECT *
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
    AND has_valid_sfdc_id = 1
),

aggregated AS (
  SELECT
    sfdc_id,

    -- Aggregation: Count of properties sharing this SFDC ID
    COUNT(*) AS active_property_count,
    COUNT(DISTINCT rds_property_id) AS unique_property_count,

    -- Feature Flags: UNION logic (MAX = TRUE if ANY property has it)
    MAX(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS idv_enabled,
    MAX(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) AS bank_linking_enabled,
    MAX(CASE WHEN payroll_enabled THEN 1 ELSE 0 END) AS payroll_enabled,
    MAX(CASE WHEN income_insights_enabled THEN 1 ELSE 0 END) AS income_insights_enabled,
    MAX(CASE WHEN document_fraud_enabled THEN 1 ELSE 0 END) AS document_fraud_enabled,

    -- Feature Timestamps: EARLIEST enabled date across all properties
    MIN(idv_enabled_at) AS idv_enabled_at,
    MIN(bank_linking_enabled_at) AS bank_linking_enabled_at,
    MIN(payroll_enabled_at) AS payroll_enabled_at,
    MIN(income_insights_enabled_at) AS income_insights_enabled_at,
    MIN(document_fraud_enabled_at) AS document_fraud_enabled_at,

    -- Calculated: Total feature count for this SFDC ID
    (
      MAX(CASE WHEN idv_enabled THEN 1 ELSE 0 END) +
      MAX(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) +
      MAX(CASE WHEN payroll_enabled THEN 1 ELSE 0 END) +
      MAX(CASE WHEN income_insights_enabled THEN 1 ELSE 0 END) +
      MAX(CASE WHEN document_fraud_enabled THEN 1 ELSE 0 END)
    ) AS total_feature_count,

    -- Is this a multi-property case? (Critical for business case validation)
    CASE WHEN COUNT(*) > 1 THEN TRUE ELSE FALSE END AS is_multi_property,

    -- Does this SFDC ID have ANY features enabled?
    CASE WHEN MAX(
      CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled OR document_fraud_enabled
      THEN 1 ELSE 0 END
    ) = 1 THEN TRUE ELSE FALSE END AS has_any_features_enabled,

    -- Audit: Most recently updated property (for metadata)
    MAX(updated_at) AS rds_last_updated_at,

    -- Audit: All RDS property IDs rolled into this SFDC ID (for debugging)
    COLLECT_LIST(rds_property_id) AS rds_property_ids_list

  FROM active_properties
  GROUP BY sfdc_id
),

metadata AS (
  -- Get property metadata from the most recently updated property for each SFDC ID
  -- This ensures we use the "latest" name, address, etc.
  SELECT
    ap.sfdc_id,
    ap.rds_property_id,
    ap.short_id,
    ap.company_id,
    ap.property_name,
    ap.address,
    ap.city,
    ap.state,
    ap.postal_code,
    ap.created_at,
    ap.company_name,
    ROW_NUMBER() OVER (PARTITION BY ap.sfdc_id ORDER BY ap.updated_at DESC) AS rn
  FROM active_properties ap
)

-- Final join: Aggregated data + metadata from most recent property
SELECT
  -- Identifiers
  agg.sfdc_id,
  meta.rds_property_id,  -- ID of the "representative" property (most recent)
  meta.short_id,
  meta.company_id,

  -- Property Metadata (from most recent property)
  meta.property_name,
  meta.address,
  meta.city,
  meta.state,
  meta.postal_code,
  meta.company_name,

  -- Feature Flags (aggregated via UNION logic)
  agg.idv_enabled,
  agg.bank_linking_enabled,
  agg.payroll_enabled,
  agg.income_insights_enabled,
  agg.document_fraud_enabled,

  -- Feature Timestamps (earliest across all properties)
  agg.idv_enabled_at,
  agg.bank_linking_enabled_at,
  agg.payroll_enabled_at,
  agg.income_insights_enabled_at,
  agg.document_fraud_enabled_at,

  -- Timestamps
  meta.created_at,
  agg.rds_last_updated_at,

  -- Aggregation Metrics (NEW - critical for monitoring)
  agg.active_property_count,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled,

  -- Audit Trail
  agg.rds_property_ids_list

FROM aggregated agg
INNER JOIN metadata meta
  ON agg.sfdc_id = meta.sfdc_id
  AND meta.rn = 1;  -- Only the most recent property for metadata

-- Add documentation
COMMENT ON VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id IS
'Aggregates multiple RDS properties by sfdc_id using UNION logic for features.
Critical view that solves the many-to-1 relationship problem (e.g., Park Kennedy case).';
