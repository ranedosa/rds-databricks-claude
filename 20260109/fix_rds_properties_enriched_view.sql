-- ============================================================================
-- FIX: rds_properties_enriched view - Correct company_name field
-- Date: January 9, 2026
-- Issue: View uses properties.name instead of companies.name for company_name
-- Impact: All synced properties have wrong company names in Salesforce
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS
WITH properties_base AS (
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
      p.inserted_at as created_at,
      p.updated_at,
      c.name AS company_name,  -- ✅ FIXED: Now uses companies.name instead of properties.name
      CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
      CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.companies c  -- ✅ ADDED: JOIN to companies table
      ON p.company_id = c.id
      AND c._fivetran_deleted = false  -- ✅ ADDED: Filter out deleted companies
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
  ),
  features_deduplicated AS (
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
      ROW_NUMBER() OVER (
        PARTITION BY property_id
        ORDER BY
          GREATEST(
            COALESCE(idv_updated_at, '1900-01-01'),
            COALESCE(bank_linking_updated_at, '1900-01-01'),
            COALESCE(payroll_linking_updated_at, '1900-01-01'),
            COALESCE(iv_updated_at, '1900-01-01'),
            COALESCE(fraud_updated_at, '1900-01-01')
          ) DESC
      ) AS rn
    FROM crm.sfdc_dbx.product_property_w_features
  )
  SELECT
    pb.rds_property_id,
    pb.sfdc_id,
    pb.short_id,
    pb.company_id,
    pb.property_name,
    pb.property_status,
    pb.address,
    pb.city,
    pb.state,
    pb.postal_code,
    pb.created_at,
    pb.updated_at,
    pb.company_name,
    COALESCE(feat.idv_enabled, FALSE) AS idv_enabled,
    COALESCE(feat.bank_linking_enabled, FALSE) AS bank_linking_enabled,
    COALESCE(feat.payroll_linking_enabled, FALSE) AS payroll_enabled,
    COALESCE(feat.iv_enabled, FALSE) AS income_insights_enabled,
    COALESCE(feat.fraud_enabled, FALSE) AS document_fraud_enabled,
    feat.idv_enabled_at,
    feat.bank_linking_enabled_at,
    feat.payroll_linking_enabled_at,
    feat.iv_enabled_at AS income_insights_enabled_at,
    feat.fraud_enabled_at AS document_fraud_enabled_at,
    pb.is_active,
    pb.has_valid_sfdc_id
  FROM properties_base pb
  LEFT JOIN features_deduplicated feat
    ON CAST(pb.rds_property_id AS STRING) = feat.property_id
    AND feat.rn = 1;

-- ============================================================================
-- CHANGES MADE:
-- 1. Line 13: Changed "p.name AS company_name" to "c.name AS company_name"
-- 2. Lines 18-20: Added LEFT JOIN to companies table
-- 3. Line 20: Added filter for non-deleted companies
-- ============================================================================
