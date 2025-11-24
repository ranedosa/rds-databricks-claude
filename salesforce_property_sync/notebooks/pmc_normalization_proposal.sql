-- Databricks notebook source
-- MAGIC %md
-- MAGIC # PMC Data Normalization Proposal
-- MAGIC
-- MAGIC **Author:** Dane Rosa
-- MAGIC **Date:** 2025-11-05
-- MAGIC **Purpose:** Proposal to normalize PMC (Property Management Company) data into a proper entity
-- MAGIC
-- MAGIC ## Current State Problems
-- MAGIC
-- MAGIC 1. **Data Integrity Issues**
-- MAGIC    - PMC names stored as strings on each property → no referential integrity
-- MAGIC    - Risk of typos/inconsistencies ("Greystar" vs "GreyStar" vs "Greystar LLC")
-- MAGIC    - Can't easily correct PMC name changes globally
-- MAGIC
-- MAGIC 2. **Lost Information**
-- MAGIC    - Current query overwrites `company_name` with `pmc_name`
-- MAGIC    - Can't distinguish: "Property billed to Company X but managed by PMC Y"
-- MAGIC    - Difficult to analyze company vs PMC relationships
-- MAGIC
-- MAGIC 3. **Reporting Limitations**
-- MAGIC    - Can't aggregate at PMC level reliably
-- MAGIC    - Can't store PMC-level attributes (segment, contact info, etc.)
-- MAGIC    - Partner vs Direct logic is implicit in API key checks
-- MAGIC
-- MAGIC ## Proposed Solution
-- MAGIC
-- MAGIC Normalize PMCs as first-class entities with proper relationships

-- COMMAND ----------

-- DBTITLE 1,Step 1: Create PMC Master Table
-- MAGIC %md
-- MAGIC ### Create PMC Table
-- MAGIC This table will store all unique PMCs as distinct entities

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS product.fde.pmcs (
  id STRING COMMENT 'Unique identifier for PMC',
  name STRING COMMENT 'Official PMC name',
  normalized_name STRING COMMENT 'Lowercase trimmed name for matching',
  channel_type STRING COMMENT 'Direct or Partner',
  salesforce_account_id STRING COMMENT 'Link to Salesforce account if exists',
  created_at TIMESTAMP COMMENT 'When PMC was first identified in system',
  updated_at TIMESTAMP COMMENT 'Last update to PMC record',
  is_active BOOLEAN COMMENT 'Whether PMC is currently active',
  notes STRING COMMENT 'Additional context about the PMC'
)
COMMENT 'Master table of Property Management Companies'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- COMMAND ----------

-- DBTITLE 1,Step 2: Populate PMC Table from Existing Data
-- MAGIC %md
-- MAGIC ### Extract Unique PMCs
-- MAGIC Identify all unique PMCs from existing property data

-- COMMAND ----------

-- First, let's see what unique PMC names we have
CREATE OR REPLACE TEMP VIEW unique_pmcs_from_properties AS
SELECT DISTINCT
    uuid() as id,
    prop.pmc_name as name,
    trim(lower(prop.pmc_name)) as normalized_name,
    MIN(prop.inserted_at) as created_at,
    MAX(prop.updated_at) as updated_at,
    CASE
        WHEN COUNT(DISTINCT CASE WHEN prop.status = 'ACTIVE' THEN prop.id END) > 0
        THEN true
        ELSE false
    END as is_active,
    COUNT(DISTINCT prop.id) as property_count,
    COUNT(DISTINCT prop.company_id) as company_count
FROM rds.pg_rds_public.properties prop
WHERE prop.pmc_name IS NOT NULL
  AND trim(prop.pmc_name) != ''
GROUP BY prop.pmc_name
ORDER BY property_count DESC;

SELECT * FROM unique_pmcs_from_properties;

-- COMMAND ----------

-- DBTITLE 1,Step 3: Determine Channel Type for Each PMC
-- MAGIC %md
-- MAGIC ### Add Channel Type Logic
-- MAGIC Identify which PMCs are Partners vs Direct based on integration usage

-- COMMAND ----------

CREATE OR REPLACE TEMP VIEW pmcs_with_channel_type AS
SELECT
    up.id,
    up.name,
    up.normalized_name,
    up.created_at,
    up.updated_at,
    up.is_active,
    up.property_count,
    up.company_count,
    CASE
        WHEN partner_companies.company_id IS NOT NULL THEN 'Partner'
        ELSE 'Direct'
    END as channel_type,
    NULL as notes
FROM unique_pmcs_from_properties up
LEFT JOIN (
    -- Get companies that have partner-level API integrations
    SELECT DISTINCT prop.company_id, prop.pmc_name
    FROM rds.pg_rds_public.properties prop
    WHERE prop.company_id IN (
        SELECT company_id
        FROM rds.pg_rds_public.api_keys ak
        WHERE role_id = 12
          AND is_active = true
          AND description NOT LIKE '%Extract%'
          AND description NOT LIKE '%Demo%'
          AND description NOT LIKE '%Viv%'
          AND description NOT LIKE '%QA%'
          AND description NOT LIKE '%Advenir%'
    )
) partner_companies
  ON up.name = partner_companies.pmc_name;

SELECT * FROM pmcs_with_channel_type
ORDER BY property_count DESC;

-- COMMAND ----------

-- DBTITLE 1,Step 4: Insert PMCs into Master Table
-- MAGIC %md
-- MAGIC ### Populate PMC Master Table
-- MAGIC **IMPORTANT:** Review the data above before running this insert!

-- COMMAND ----------

-- Uncomment to execute after review
/*
INSERT INTO product.fde.pmcs
SELECT
    id,
    name,
    normalized_name,
    channel_type,
    NULL as salesforce_account_id,  -- Can be populated later via join
    created_at,
    updated_at,
    is_active,
    CASE
        WHEN property_count = 1 THEN 'Single property PMC'
        WHEN company_count > 1 THEN 'PMC managing properties across multiple companies'
        ELSE NULL
    END as notes
FROM pmcs_with_channel_type;
*/

-- COMMAND ----------

-- DBTITLE 1,Step 5: Add PMC Foreign Key to Properties (Schema Change)
-- MAGIC %md
-- MAGIC ### Add pmc_id Column to Properties
-- MAGIC
-- MAGIC **Note:** This requires a schema change to the properties table in RDS.
-- MAGIC This is a proposal only - actual implementation would need to be coordinated with the data engineering team.
-- MAGIC
-- MAGIC ```sql
-- MAGIC -- In RDS PostgreSQL:
-- MAGIC ALTER TABLE properties ADD COLUMN pmc_id VARCHAR(36);
-- MAGIC CREATE INDEX idx_properties_pmc_id ON properties(pmc_id);
-- MAGIC
-- MAGIC -- Backfill pmc_id based on pmc_name matching
-- MAGIC UPDATE properties p
-- MAGIC SET pmc_id = (
-- MAGIC     SELECT id FROM pmcs
-- MAGIC     WHERE normalized_name = trim(lower(p.pmc_name))
-- MAGIC     LIMIT 1
-- MAGIC )
-- MAGIC WHERE p.pmc_name IS NOT NULL;
-- MAGIC ```

-- COMMAND ----------

-- DBTITLE 1,Step 6: Create Enhanced Property Master Table
-- MAGIC %md
-- MAGIC ### Updated Property Master Table
-- MAGIC This version properly separates company and PMC entities

-- COMMAND ----------

CREATE OR REPLACE TABLE product.fde.unity_property_details_master_v2 AS (

WITH bank_linking AS (
    SELECT
        prop.id AS property_id,
        pf.updated_at AS date_bal_enabled
    FROM rds.pg_rds_public.properties prop
    RIGHT JOIN rds.pg_rds_public.property_features pf ON prop.id = pf.property_id
    WHERE pf.feature_code = 'bank_linking' AND pf.state = 'enabled'
),

-- Clean up the metro data
metro_data AS (
    SELECT
        property_id, property_name, company_id, company_name,
        property_county, property_msa, CSA_Title,
        CBSA_Title as property_metro_area,
        property_city, property_state,
        concat(property_city, ", ", property_state) as city_state
    FROM team_sandbox.data_engineering.unity_roi_fraud_reduction
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
),

idv_data AS (
    SELECT
        property_id,
        MIN(idv.inserted_at) as first_IDV_scan_attempt
    FROM rds.pg_rds_public.id_verifications idv
    GROUP BY 1
),

-- Clean up and dedupe salesforce account data
salesforce_account_data AS (
    SELECT
        a.id as salesforce_account_id,
        a.name as salesforce_account_name,
        a.segment_c as salesforce_account_segment,
        a.csmowner_c as csm_owner_salesforce_user_ID,
        u3.name as csm_owner_name,
        u3.email as csm_owner_email,
        a.owner_id as ae_owner_salesforce_user_ID,
        u.name as sales_owner_name,
        a.strategic_account_manager_c as strategic_account_manager_salesforce_user_ID,
        u2.name as strategic_account_manager_name,
        RANK() OVER (
            PARTITION BY trim(lower(a.name))
            ORDER BY a.last_modified_date DESC
        ) AS account_rank
    FROM hive_metastore.salesforce.account a
    LEFT JOIN hive_metastore.salesforce.user u ON u.id = a.owner_id
    LEFT JOIN hive_metastore.salesforce.user u2 ON u2.id = a.strategic_account_manager_c
    LEFT JOIN hive_metastore.salesforce.user u3 ON u3.id = a.csmowner_c
    WHERE a.is_deleted = false
    QUALIFY account_rank = 1
),

-- Identify partner companies via API keys
partner_companies AS (
    SELECT DISTINCT company_id
    FROM rds.pg_rds_public.api_keys ak
    WHERE role_id = 12
      AND is_active = true
      AND description NOT LIKE '%Extract%'
      AND description NOT LIKE '%Demo%'
      AND description NOT LIKE '%Viv%'
      AND description NOT LIKE '%QA%'
      AND description NOT LIKE '%Advenir%'
),

-- Gather all the product data
product_details AS (
    SELECT
        prop.id as property_id,
        prop.short_id as property_short_id,
        prop.name as property_name,
        CAST(date_trunc('month', prop.inserted_at) AS DATE) as onboarded_month,
        prop.inserted_at as onboarded_date,
        prop.address as property_address,
        prop.city as property_city,
        prop.state as property_state,
        prop.unit as num_units,
        prop.status as property_status,
        CASE WHEN prop.status = "DISABLED" THEN prop.updated_at ELSE null END as deactivated_date,

        -- CHANGED: Keep company and PMC separate
        comp.name as company_name,
        prop.company_id,
        prop.company_short_id,
        prop.pmc_name as pmc_name_legacy,  -- Keep legacy field for transition
        pmc.id as pmc_id,
        pmc.name as pmc_name,
        pmc.channel_type as pmc_channel_type,

        -- Display name: show who manages the property
        COALESCE(pmc.name, comp.name) as property_manager_display_name,

        -- Company-level channel type (for backwards compatibility)
        CASE
            WHEN pc.company_id IS NOT NULL THEN 'Partner'
            ELSE 'Direct'
        END as company_channel_type,

        -- Integration details
        CASE
            WHEN ep.id IS NOT NULL OR pc.company_id IS NOT NULL
            THEN 'yes'
            ELSE 'no'
        END as uses_integration,

        CASE
            WHEN ep.id IS NOT NULL THEN ep.integration_activation_date
            WHEN pc.company_id IS NOT NULL THEN prop.inserted_at
            ELSE NULL
        END AS integration_enabled_at,

        eic.type as outbound_integration_PMS,
        CASE
            WHEN pc.company_id IS NOT NULL THEN comp.name
            ELSE null
        END as inbound_integration_PMS,

        COALESCE(
            get_json_object(CAST(ep.integration_details AS STRING), '$.yardiPropertyId'),
            get_json_object(CAST(ep.integration_details AS STRING), '$.SiteID')
        ) AS integration_external_id,

        -- Feature enablement
        pf.iv_enabled,
        pf.iv_updated_at as iv_enabled_at,
        pf.payroll_linking_enabled,
        pf.payroll_linking_updated_at as payroll_linking_enabled_at,
        prop.identity_verification_enabled,
        bl.date_bal_enabled as bal_enabled_at,
        CASE WHEN bl.date_bal_enabled IS NOT NULL THEN true ELSE false END AS bal_enabled,

        -- Salesforce and geo data
        prop.sfdc_id,
        m.property_county,
        m.property_metro_area,
        m.csa_title as property_csa_title,
        m.property_msa,
        m.city_state as property_city_state,
        prop.zip as property_zip,
        prop.updated_at as property_last_updated_at,

        -- IDV data
        idv.first_idv_scan_attempt,
        CASE
            WHEN idv.first_IDV_scan_attempt IS NOT NULL THEN idv.first_IDV_scan_attempt
            WHEN prop.identity_verification_enabled = "true"
                 AND idv.first_IDV_scan_attempt IS NULL
                 AND prop.status = "ACTIVE" THEN prop.updated_at
            WHEN prop.identity_verification_enabled = "true"
                 AND idv.first_IDV_scan_attempt IS NULL
                 AND prop.status = "DISABLED" THEN prop.inserted_at
            ELSE null
        END as identity_verification_enabled_at_estimated

    FROM rds.pg_rds_public.properties prop

    -- Join to companies (billing/contract entity)
    JOIN rds.pg_rds_public.companies comp ON comp.id = prop.company_id

    -- Join to PMCs (management entity) - NEW!
    LEFT JOIN product.fde.pmcs pmc
        ON trim(lower(prop.pmc_name)) = pmc.normalized_name

    -- Existing joins
    LEFT JOIN rds.pg_rds_enterprise_public.enterprise_property ep
        ON ep.snappt_property_id = prop.id
        AND ep.integration_activation_date IS NOT NULL
    LEFT JOIN rds.pg_rds_enterprise_public.enterprise_integration_configuration eic
        ON eic.id = ep.enterprise_integration_id
        AND eic.deleted_at IS NULL
        AND eic.name NOT LIKE 'Snappt Integration'
    LEFT JOIN product.fde.unity_agg_property_features pf ON pf.property_id = prop.id
    LEFT JOIN bank_linking bl ON bl.property_id = prop.id
    LEFT JOIN metro_data m ON m.property_id = prop.id
    LEFT JOIN idv_data idv ON idv.property_id = prop.id
    LEFT JOIN partner_companies pc ON pc.company_id = prop.company_id

    GROUP BY ALL
)

-- Bring salesforce and product data together
SELECT
    pd.*,

    -- Company-level salesforce data
    comp_sf.csm_owner_salesforce_user_id as company_csm_owner_salesforce_user_ID,
    CASE
        WHEN comp_sf.csm_owner_name IS NULL AND pd.company_channel_type = "Partner"
            THEN concat("Partner: ", pd.inbound_integration_PMS)
        WHEN comp_sf.csm_owner_name IS NULL THEN "None Assigned"
        ELSE comp_sf.csm_owner_name
    END as company_csm_owner,
    CASE
        WHEN comp_sf.salesforce_account_segment IS NULL
             AND comp_sf.salesforce_account_id IS NOT NULL THEN "Unassigned"
        WHEN comp_sf.salesforce_account_segment IS NULL
             AND comp_sf.salesforce_account_id IS NULL THEN "Unable to match to SF Account"
        ELSE comp_sf.salesforce_account_segment
    END as company_segment,
    comp_sf.csm_owner_email as company_csm_owner_email,
    comp_sf.sales_owner_name as company_sales_owner_name,
    comp_sf.strategic_account_manager_name as company_strategic_account_manager_name,
    comp_sf.salesforce_account_id as company_salesforce_account_id,
    comp_sf.salesforce_account_name as company_salesforce_account_name,

    -- PMC-level salesforce data (NEW!)
    pmc_sf.salesforce_account_id as pmc_salesforce_account_id,
    pmc_sf.salesforce_account_name as pmc_salesforce_account_name,
    pmc_sf.salesforce_account_segment as pmc_segment,
    pmc_sf.csm_owner_name as pmc_csm_owner,
    pmc_sf.sales_owner_name as pmc_sales_owner_name

FROM product_details pd

-- Join to company's salesforce account
LEFT JOIN salesforce_account_data comp_sf
    ON trim(lower(pd.company_name)) = trim(lower(comp_sf.salesforce_account_name))

-- Join to PMC's salesforce account (NEW!)
LEFT JOIN salesforce_account_data pmc_sf
    ON trim(lower(pd.pmc_name)) = trim(lower(pmc_sf.salesforce_account_name))

GROUP BY ALL
);

-- COMMAND ----------

-- DBTITLE 1,Validation: Check Results
SELECT *
FROM product.fde.unity_property_details_master_v2
WHERE pmc_name IS NOT NULL
LIMIT 100;

-- COMMAND ----------

-- DBTITLE 1,Validation: Compare Company vs PMC
-- MAGIC %md
-- MAGIC ### Show cases where Company ≠ PMC
-- MAGIC These are properties where the billing company differs from the managing PMC

-- COMMAND ----------

SELECT
    property_name,
    company_name,
    pmc_name,
    property_manager_display_name,
    company_channel_type,
    pmc_channel_type,
    company_segment,
    pmc_segment,
    property_city,
    property_state
FROM product.fde.unity_property_details_master_v2
WHERE pmc_name IS NOT NULL
  AND trim(lower(company_name)) != trim(lower(pmc_name))
ORDER BY pmc_name, company_name
LIMIT 100;

-- COMMAND ----------

-- DBTITLE 1,Validation: PMC-Level Aggregation
-- MAGIC %md
-- MAGIC ### Example: Property Count by PMC
-- MAGIC This type of analysis is now clean and accurate

-- COMMAND ----------

SELECT
    pmc_name,
    pmc_channel_type,
    pmc_segment,
    COUNT(DISTINCT property_id) as property_count,
    COUNT(DISTINCT company_id) as company_count,
    COUNT(DISTINCT CASE WHEN property_status = 'ACTIVE' THEN property_id END) as active_properties,
    COUNT(DISTINCT CASE WHEN bal_enabled = true THEN property_id END) as properties_with_bal,
    SUM(num_units) as total_units
FROM product.fde.unity_property_details_master_v2
WHERE pmc_name IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY property_count DESC;

-- COMMAND ----------

-- DBTITLE 1,Migration Path: Side-by-Side Comparison
-- MAGIC %md
-- MAGIC ### Compare Old vs New Tables
-- MAGIC Verify that critical fields match during transition

-- COMMAND ----------

SELECT
    'old_table' as source,
    COUNT(*) as row_count,
    COUNT(DISTINCT property_id) as unique_properties,
    COUNT(DISTINCT company_id) as unique_companies
FROM product.fde.unity_property_details_master

UNION ALL

SELECT
    'new_table' as source,
    COUNT(*) as row_count,
    COUNT(DISTINCT property_id) as unique_properties,
    COUNT(DISTINCT company_id) as unique_companies
FROM product.fde.unity_property_details_master_v2;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary of Changes
-- MAGIC
-- MAGIC ### What Changed
-- MAGIC
-- MAGIC 1. **New PMC Master Table** (`product.fde.pmcs`)
-- MAGIC    - PMCs are now first-class entities with unique IDs
-- MAGIC    - Prevents name inconsistencies
-- MAGIC    - Enables PMC-level attributes and reporting
-- MAGIC
-- MAGIC 2. **Separated Company and PMC** in Property Master Table
-- MAGIC    - `company_name`: Who we bill/contract with
-- MAGIC    - `pmc_name`: Who manages the property
-- MAGIC    - `property_manager_display_name`: Convenience field for reporting
-- MAGIC    - Both can have independent Salesforce account relationships
-- MAGIC
-- MAGIC 3. **Clearer Channel Type Logic**
-- MAGIC    - `company_channel_type`: Partner vs Direct for the company
-- MAGIC    - `pmc_channel_type`: Partner vs Direct for the PMC
-- MAGIC
-- MAGIC ### Benefits
-- MAGIC
-- MAGIC ✅ **Data Integrity**: PMC names are consistent across all properties
-- MAGIC ✅ **Clear Semantics**: No more ambiguous "company_name" that's sometimes PMC
-- MAGIC ✅ **Better Reporting**: Can aggregate at company OR PMC level accurately
-- MAGIC ✅ **Flexibility**: Can track relationships where billing company ≠ managing PMC
-- MAGIC ✅ **Salesforce Integration**: Can link both companies AND PMCs to SF accounts
-- MAGIC
-- MAGIC ### Migration Path
-- MAGIC
-- MAGIC 1. Create PMC table and populate from existing data ✅
-- MAGIC 2. Create v2 of property master table ✅
-- MAGIC 3. Run both tables in parallel for validation period
-- MAGIC 4. Update downstream dependencies to use v2
-- MAGIC 5. (Optional) Add `pmc_id` column to RDS properties table
-- MAGIC 6. Deprecate v1 table
-- MAGIC
-- MAGIC ### Questions for Discussion
-- MAGIC
-- MAGIC 1. Should we add `pmc_id` to the source RDS properties table?
-- MAGIC 2. What's the validation period before switching to v2?
-- MAGIC 3. Which downstream dashboards/queries need to be updated?
-- MAGIC 4. Do we want to track PMC contact information in the PMC table?
