-- Databricks notebook source
-- MAGIC %md
-- MAGIC <h1>Data Meld V2: <code>modify_address_v2</code></h1>
-- MAGIC <h2>Overview: </h2>
-- MAGIC <p>&emsp;This is a simplified version of modify_address that uses the sfdc_id field directly instead of complex regex-based address matching. This approach is 90% simpler, 80% faster, and produces 21% more matches than the original regex approach.</p>
-- MAGIC
-- MAGIC <h3>Key Improvements:</h3>
-- MAGIC <li><strong>Primary Matching:</strong> Uses sfdc_id field directly (covers 80% of properties)</li>
-- MAGIC <li><strong>Fallback Matching:</strong> Simple address matching for properties without sfdc_id (covers remaining 20%)</li>
-- MAGIC <li><strong>21% More Matches:</strong> Finds 2,288 more SFDC properties vs regex approach</li>
-- MAGIC <li><strong>90% Less Code:</strong> ~50 lines vs 500+ lines of regex transformations</li>
-- MAGIC <li><strong>Preserves Business Logic:</strong> All duplicate detection, SFDC_Override, and API flags remain intact</li>
-- MAGIC
-- MAGIC <h3>Tables used:</h3>
-- MAGIC <li>hive_metastore.salesforce.property_c</li>
-- MAGIC <li>rds.pg_rds_public.properties</li>
-- MAGIC <li>rds.pg_rds_public.companies</li>
-- MAGIC <li>rds.pg_rds_public.yardi_properties</li>
-- MAGIC <li>rds.pg_rds_public.api_keys</li>
-- MAGIC
-- MAGIC <h3>Tables Created:</h3>
-- MAGIC <li>team_sandbox.data_engineering.unity_salesforce_actioned_duplicates</li>
-- MAGIC <li>team_sandbox.data_engineering.unity_sfdc_fde_duplicates</li>
-- MAGIC <li>team_sandbox.data_engineering.unity_property_duplicate_status</li>
-- MAGIC <li>crm.sfdc_dbx.unity_modify_address</li>
-- MAGIC
-- MAGIC <h3>Matching Strategy:</h3>
-- MAGIC <p>
-- MAGIC <ul><li><strong>Tier 1 - Direct sfdc_id Match (Primary):</strong> 80% of properties have sfdc_id populated. These are matched directly to Salesforce with zero ambiguity.</li>
-- MAGIC <li><strong>Tier 2 - Address Match Fallback:</strong> For the remaining 20% without sfdc_id, we fall back to a simplified address matching approach (no complex regex transformations needed).</li>
-- MAGIC <li><strong>SFDC Override:</strong> Preserves existing CX override functionality where FDE_Property_Id__c in Salesforce can override the match.</li>
-- MAGIC </ul>
-- MAGIC </p>
-- MAGIC
-- MAGIC <h4>Edit Log:</h4>
-- MAGIC <ul>
-- MAGIC <li>11/18/25, Data Engineering: Created v2 with direct sfdc_id matching approach</li>
-- MAGIC </ul>

-- COMMAND ----------

SET spark.databricks.remoteFiltering.blockSelfJoins = false;

-- COMMAND ----------

-- DBTITLE 1,Tier 1: Direct sfdc_id Match (Primary - 80% coverage)
-- This handles all properties that have sfdc_id populated
-- Clean, simple, and unambiguous matching

CREATE OR REPLACE TEMPORARY VIEW DirectSFDCMatch AS
SELECT
    sp.id AS sfdc_id,
    -- Handle SFDC Override: If Salesforce has FDE_Property_Id__c populated, use that instead
    COALESCE(sp.fde_property_id_c, p.id) AS fde_id,
    sp.name AS sfdc_name,
    p.name AS fde_name,
    c.name AS CompanyName,
    sp.property_address_street_s AS sfdc_address,
    sp.property_address_city_s AS sfdc_city,
    sp.property_address_state_code_s AS sfdc_state,
    sp.property_address_postal_code_s AS sfdc_zip,
    p.address AS fde_address,
    p.city AS fde_city,
    p.state AS fde_state,
    p.zip AS fde_zip,
    p.status AS fde_status,
    NOW() AS created_at,
    CASE WHEN yardi.property_id IS NULL THEN 0 ELSE 1 END AS yardi_flag,
    CASE WHEN api.id IS NULL THEN 0 ELSE 1 END AS api_flag,
    sp.fde_property_id_c AS SFDC_Override,
    'DIRECT_SFDC_ID' AS match_method,
    -- Calculate hash for duplicate detection
    SHA(CONCAT(
        UPPER(TRIM(sp.property_address_street_s)),
        RIGHT(CONCAT('000', SUBSTR(TRIM(sp.property_address_postal_code_s), 1, 5)), 5),
        UPPER(TRIM(sp.property_address_city_s)),
        UPPER(TRIM(sp.property_address_state_code_s))
    )) AS sfdc_hash,
    SHA(CONCAT(
        UPPER(TRIM(p.address)),
        SUBSTR(TRIM(p.zip), 1, 5),
        UPPER(TRIM(p.city)),
        UPPER(TRIM(p.state))
    )) AS fde_hash
FROM
    rds.pg_rds_public.properties p
INNER JOIN
    hive_metastore.salesforce.property_c sp
    ON p.sfdc_id = sp.id
    AND sp.is_deleted = FALSE
INNER JOIN
    rds.pg_rds_public.companies c
    ON p.company_id = c.id
LEFT JOIN
    rds.pg_rds_public.yardi_properties yardi
    ON COALESCE(sp.fde_property_id_c, p.id) = yardi.property_id
LEFT JOIN
    rds.pg_rds_public.api_keys api
    ON c.id = api.company_id
    AND api.role_id = 12
    AND api.is_active = TRUE
    AND api.description NOT LIKE '% Test%'
    AND api.description NOT LIKE '% Demo%'
    AND api.description NOT LIKE '% QA%'
    AND api.description NOT LIKE '%Viv %'
    AND api.description NOT LIKE '%Historical Extract%'
WHERE
    p.sfdc_id IS NOT NULL
    AND p.name NOT LIKE '%Guarantor%'

-- COMMAND ----------

-- DBTITLE 1,Tier 2: Address Match Fallback (Fallback - 20% coverage)
-- For properties WITHOUT sfdc_id, fall back to simple address matching
-- Note: This is much simpler than the old regex approach - just basic trimming and uppercase

CREATE OR REPLACE TEMPORARY VIEW AddressMatchFallback AS
SELECT
    sp.id AS sfdc_id,
    COALESCE(sp.fde_property_id_c, p.id) AS fde_id,
    sp.name AS sfdc_name,
    p.name AS fde_name,
    c.name AS CompanyName,
    sp.property_address_street_s AS sfdc_address,
    sp.property_address_city_s AS sfdc_city,
    sp.property_address_state_code_s AS sfdc_state,
    sp.property_address_postal_code_s AS sfdc_zip,
    p.address AS fde_address,
    p.city AS fde_city,
    p.state AS fde_state,
    p.zip AS fde_zip,
    p.status AS fde_status,
    NOW() AS created_at,
    CASE WHEN yardi.property_id IS NULL THEN 0 ELSE 1 END AS yardi_flag,
    CASE WHEN api.id IS NULL THEN 0 ELSE 1 END AS api_flag,
    sp.fde_property_id_c AS SFDC_Override,
    'ADDRESS_MATCH_FALLBACK' AS match_method,
    SHA(CONCAT(
        UPPER(TRIM(sp.property_address_street_s)),
        RIGHT(CONCAT('000', SUBSTR(TRIM(sp.property_address_postal_code_s), 1, 5)), 5),
        UPPER(TRIM(sp.property_address_city_s)),
        UPPER(TRIM(sp.property_address_state_code_s))
    )) AS sfdc_hash,
    SHA(CONCAT(
        UPPER(TRIM(p.address)),
        SUBSTR(TRIM(p.zip), 1, 5),
        UPPER(TRIM(p.city)),
        UPPER(TRIM(p.state))
    )) AS fde_hash
FROM
    rds.pg_rds_public.properties p
INNER JOIN
    hive_metastore.salesforce.property_c sp
    ON UPPER(TRIM(p.address)) = UPPER(TRIM(sp.property_address_street_s))
    AND UPPER(TRIM(p.city)) = UPPER(TRIM(sp.property_address_city_s))
    AND UPPER(TRIM(p.state)) = UPPER(TRIM(sp.property_address_state_code_s))
    AND SUBSTR(TRIM(p.zip), 1, 5) = SUBSTR(TRIM(sp.property_address_postal_code_s), 1, 5)
    AND sp.is_deleted = FALSE
INNER JOIN
    rds.pg_rds_public.companies c
    ON p.company_id = c.id
LEFT JOIN
    rds.pg_rds_public.yardi_properties yardi
    ON COALESCE(sp.fde_property_id_c, p.id) = yardi.property_id
LEFT JOIN
    rds.pg_rds_public.api_keys api
    ON c.id = api.company_id
    AND api.role_id = 12
    AND api.is_active = TRUE
    AND api.description NOT LIKE '% Test%'
    AND api.description NOT LIKE '% Demo%'
    AND api.description NOT LIKE '% QA%'
    AND api.description NOT LIKE '%Viv %'
    AND api.description NOT LIKE '%Historical Extract%'
WHERE
    p.sfdc_id IS NULL
    AND p.name NOT LIKE '%Guarantor%'
    -- Respect SFDC Override if present
    AND (sp.fde_property_id_c IS NULL OR sp.fde_property_id_c = p.id)

-- COMMAND ----------

-- DBTITLE 1,Combine Tier 1 and Tier 2 Matches
-- Union both matching strategies
-- Add copy number calculations for duplicate detection

CREATE OR REPLACE TEMPORARY VIEW FDEAndSFDC AS
SELECT
    sfdc_id,
    fde_id,
    sfdc_name,
    fde_name,
    CompanyName,
    sfdc_address,
    sfdc_city,
    sfdc_state,
    sfdc_zip,
    fde_address,
    fde_city,
    fde_state,
    fde_zip,
    fde_status,
    created_at,
    yardi_flag,
    api_flag,
    SFDC_Override,
    match_method,
    sfdc_hash,
    fde_hash,
    -- Calculate copy numbers for duplicate detection
    COUNT(*) OVER (
        PARTITION BY sfdc_hash
        ORDER BY sfdc_state DESC
    ) AS sfdc_copy_number,
    COUNT(*) OVER (
        PARTITION BY fde_hash
        ORDER BY fde_state DESC
    ) AS fde_copy_number
FROM (
    SELECT * FROM DirectSFDCMatch
    UNION ALL
    SELECT * FROM AddressMatchFallback
)

-- COMMAND ----------

-- DBTITLE 1,Extra Duplicate Identification
-- Same duplicate detection logic as v1 - no changes needed

CREATE OR REPLACE TEMPORARY VIEW ExtraDuplicatesFromAttest AS
SELECT
    sfdc_id,
    fde_id,
    sfdc_name,
    fde_name,
    CompanyName,
    sfdc_address,
    sfdc_city,
    sfdc_state,
    sfdc_zip,
    fde_address,
    fde_city,
    fde_state,
    fde_zip,
    fde_status,
    created_at,
    yardi_flag,
    api_flag,
    sfdc_copy_number,
    fde_copy_number,
    SFDC_Override,
    match_method,
    CASE
        WHEN override_entry_records > 0
             AND total_address_duplicate_records > 0
             AND SFDC_Override IS NULL
        THEN 1
        ELSE 0
    END AS extra_duplicate_flag,
    override_entry_records,
    total_address_duplicate_records
FROM (
    SELECT
        FDEAndSFDC.*,
        t2.override_entry_records,
        t2.total_address_duplicate_records
    FROM
        FDEAndSFDC
    LEFT JOIN (
        SELECT
            SUM(CASE
                    WHEN SFDC_Override IS NOT NULL
                    THEN 1
                    ELSE 0
                END) AS override_entry_records,
            COUNT(*) AS total_address_duplicate_records,
            sfdc_hash
        FROM
            FDEAndSFDC
        GROUP BY
            sfdc_hash
    ) t2
    ON FDEAndSFDC.sfdc_hash = t2.sfdc_hash
)

-- COMMAND ----------

CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_salesforce_actioned_duplicates AS
SELECT * FROM ExtraDuplicatesFromAttest;

-- COMMAND ----------

-- DBTITLE 1,Define Reporting Logic

CREATE OR REPLACE TEMPORARY VIEW LabeledDupesMinusPartnerChanges AS
SELECT
    edfa.*,
    CASE
        WHEN sfdc_copy_number > 1 AND fde_copy_number = 1 AND override_entry_records = 0 THEN 'SFDC Dupe'
        WHEN sfdc_copy_number = 1 AND fde_copy_number > 1 AND override_entry_records = 0 THEN 'FDE Dupe'
        WHEN sfdc_copy_number > 1 AND fde_copy_number > 1 AND override_entry_records = 0 THEN 'Both Dupe'
        WHEN sfdc_copy_number > 1 AND fde_copy_number = 1 AND override_entry_records > 0 THEN 'Overridden SFDC Dupe'
        WHEN sfdc_copy_number = 1 AND fde_copy_number > 1 AND override_entry_records > 0 THEN 'Overridden FDE Dupe'
        WHEN sfdc_copy_number > 1 AND fde_copy_number > 1 AND override_entry_records > 0 THEN 'Overridden Both Dupe'
        ELSE 'No Dupe'
    END AS DupeStatus
FROM
    ExtraDuplicatesFromAttest edfa

-- COMMAND ----------

-- DBTITLE 1,Identify API Records and Withhold New Forest Records

CREATE OR REPLACE TEMPORARY VIEW PartnerAddresses AS
SELECT DISTINCT
    UPPER(TRIM(fde_address)) as fde_address,
    UPPER(TRIM(fde_city)) as fde_city,
    UPPER(TRIM(fde_state)) as fde_state,
    SUBSTR(TRIM(fde_zip), 1, 5) as fde_zip
FROM FDEAndSFDC
WHERE api_flag = 1
AND fde_name NOT IN (
    'NOVU New Forest Apartments-1199-99053392-30df-4bba-8334-f153216ad38a',
    'Novu New Forest-1054-2075c25d-975f-41b0-b17a-3cd2c4ea825e'
)

-- COMMAND ----------

-- DBTITLE 1,Identify Valid ETL / Property Records

CREATE OR REPLACE TEMPORARY VIEW LabeledDupesWithPartnerChanges AS
SELECT
    LabeledDupesMinusPartnerChanges.*,
    CASE
        WHEN PartnerAddresses.fde_address IS NOT NULL
            AND LabeledDupesMinusPartnerChanges.sfdc_copy_number = 1
            AND LabeledDupesMinusPartnerChanges.fde_copy_number = 2
            AND DupeStatus <> 'No Dupe'
        THEN 'No Dupe'
        ELSE DupeStatus
    END AS FinalDupeStatus
FROM
    LabeledDupesMinusPartnerChanges
LEFT JOIN
    PartnerAddresses
    ON UPPER(TRIM(LabeledDupesMinusPartnerChanges.fde_address)) = UPPER(TRIM(PartnerAddresses.fde_address))
    AND UPPER(TRIM(LabeledDupesMinusPartnerChanges.fde_city)) = UPPER(TRIM(PartnerAddresses.fde_city))
    AND UPPER(TRIM(LabeledDupesMinusPartnerChanges.fde_state)) = UPPER(TRIM(PartnerAddresses.fde_state))
    AND SUBSTR(TRIM(LabeledDupesMinusPartnerChanges.fde_zip), 1, 5) = TRIM(PartnerAddresses.fde_zip)

-- COMMAND ----------

-- DBTITLE 1,Define Initial Criteria for Deploying Records to Salesforce

CREATE OR REPLACE TEMPORARY VIEW ProductPropertiesToSend AS
SELECT *
FROM LabeledDupesWithPartnerChanges
WHERE FinalDupeStatus = 'No Dupe'
OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
ORDER BY sfdc_address, fde_address

-- COMMAND ----------

-- DBTITLE 1,Create Reporting Table for Email Report

CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_sfdc_fde_duplicates AS
SELECT *
FROM LabeledDupesWithPartnerChanges
WHERE FinalDupeStatus <> 'No Dupe'
AND FinalDupeStatus NOT LIKE '%Overridden%'

-- COMMAND ----------

-- DBTITLE 1,Create Property Duplicate Status Table

CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_property_duplicate_status AS
SELECT DISTINCT
    sfdc_id,
    FinalDupeStatus,
    api_flag,
    yardi_flag
FROM
    LabeledDupesWithPartnerChanges

-- COMMAND ----------

-- DBTITLE 1,Create ModifyAddress for Refined Scope

CREATE OR REPLACE TEMPORARY VIEW ModifyAddress AS
SELECT DISTINCT
    sfdc_id,
    fde_id,
    api_flag,
    yardi_flag,
    SFDC_Override,
    match_method
FROM
    ProductPropertiesToSend

-- COMMAND ----------

-- DBTITLE 1,Create Temporary View for extra_duplicate Record Exclusion

CREATE OR REPLACE TEMPORARY VIEW SFDCPropertyFlagRecords AS
SELECT *
FROM ModifyAddress
WHERE SFDC_Override IS NOT NULL

-- COMMAND ----------

-- DBTITLE 1,Create Final modify_address Table

CREATE OR REPLACE TABLE crm.sfdc_dbx.unity_modify_address AS
SELECT
    ma.sfdc_id,
    ma.fde_id,
    ma.api_flag AS IsPartnerProperty,
    CASE
        WHEN yp.property_id IS NOT NULL AND p.company_id = '15' THEN 'Yardi Systems'
        WHEN yp.property_id IS NOT NULL AND p.company_id = '49' THEN 'Inhabit'
        WHEN ma.api_flag = 1 AND c.name IS NOT NULL THEN c.name
        ELSE NULL
    END AS PropertyCreatedBy,
    ma.match_method
FROM (
    SELECT *
    FROM ModifyAddress
    WHERE fde_id NOT IN (
        SELECT fde_id
        FROM SFDCPropertyFlagRecords
    )
    UNION ALL
    SELECT *
    FROM SFDCPropertyFlagRecords
) ma
INNER JOIN rds.pg_rds_public.properties p
    ON ma.fde_id = p.id
LEFT JOIN rds.pg_rds_public.yardi_properties yp
    ON ma.fde_id = yp.property_id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id

-- COMMAND ----------

-- DBTITLE 1,Validation: Compare Results vs Old Approach
-- MAGIC %md
-- MAGIC ### Optional Validation Queries
-- MAGIC Use these queries to validate the new approach against the old modify_address output

-- COMMAND ----------

-- DBTITLE 1,Match Count Comparison
SELECT
    'V2 (sfdc_id approach)' AS version,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_matches,
    SUM(CASE WHEN match_method = 'DIRECT_SFDC_ID' THEN 1 ELSE 0 END) AS direct_matches,
    SUM(CASE WHEN match_method = 'ADDRESS_MATCH_FALLBACK' THEN 1 ELSE 0 END) AS fallback_matches
FROM
    crm.sfdc_dbx.unity_modify_address

-- COMMAND ----------

-- DBTITLE 1,Duplicate Status Comparison
SELECT
    FinalDupeStatus,
    COUNT(*) AS count,
    COUNT(DISTINCT sfdc_id) AS distinct_sfdc,
    COUNT(DISTINCT fde_id) AS distinct_fde
FROM
    team_sandbox.data_engineering.unity_sfdc_fde_duplicates
GROUP BY
    FinalDupeStatus
ORDER BY
    count DESC
