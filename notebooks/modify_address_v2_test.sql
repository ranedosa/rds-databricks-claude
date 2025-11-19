-- Databricks notebook source
-- MAGIC %md
-- MAGIC <h1>TEST VERSION: modify_address_v2</h1>
-- MAGIC <h2>⚠️ THIS IS A TEST NOTEBOOK - SAFE TO RUN ⚠️</h2>
-- MAGIC <p>This notebook writes to separate test tables and will NOT overwrite production tables.</p>
-- MAGIC
-- MAGIC <h3>Test Tables Created:</h3>
-- MAGIC <li>team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test</li>
-- MAGIC <li>team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test</li>
-- MAGIC <li>team_sandbox.data_engineering.unity_property_duplicate_status_v2_test</li>
-- MAGIC <li>crm.sfdc_dbx.unity_modify_address_v2_test</li>
-- MAGIC
-- MAGIC <h3>Safe to Run Because:</h3>
-- MAGIC <li>✅ Writes to _v2_test tables only</li>
-- MAGIC <li>✅ Does NOT overwrite production tables</li>
-- MAGIC <li>✅ Can be compared side-by-side with production</li>
-- MAGIC <li>✅ Can be deleted after testing</li>

-- COMMAND ----------

SET spark.databricks.remoteFiltering.blockSelfJoins = false;

-- COMMAND ----------

-- DBTITLE 1,Tier 1: Direct sfdc_id Match (Primary - 80% coverage)
CREATE OR REPLACE TEMPORARY VIEW DirectSFDCMatch AS
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
    'DIRECT_SFDC_ID' AS match_method,
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
    AND (sp.fde_property_id_c IS NULL OR sp.fde_property_id_c = p.id)

-- COMMAND ----------

-- DBTITLE 1,Combine Tier 1 and Tier 2 Matches
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

-- DBTITLE 1,TEST TABLE: salesforce_actioned_duplicates
CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test AS
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

-- DBTITLE 1,Identify API Records
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

-- DBTITLE 1,Identify Valid ETL Records
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

-- DBTITLE 1,Define Criteria for Salesforce Deploy
CREATE OR REPLACE TEMPORARY VIEW ProductPropertiesToSend AS
SELECT *
FROM LabeledDupesWithPartnerChanges
WHERE FinalDupeStatus = 'No Dupe'
OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
ORDER BY sfdc_address, fde_address

-- COMMAND ----------

-- DBTITLE 1,TEST TABLE: sfdc_fde_duplicates
CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test AS
SELECT *
FROM LabeledDupesWithPartnerChanges
WHERE FinalDupeStatus <> 'No Dupe'
AND FinalDupeStatus NOT LIKE '%Overridden%'

-- COMMAND ----------

-- DBTITLE 1,TEST TABLE: property_duplicate_status
CREATE OR REPLACE TABLE team_sandbox.data_engineering.unity_property_duplicate_status_v2_test AS
SELECT DISTINCT
    sfdc_id,
    FinalDupeStatus,
    api_flag,
    yardi_flag
FROM
    LabeledDupesWithPartnerChanges

-- COMMAND ----------

-- DBTITLE 1,Create ModifyAddress Staging
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

-- DBTITLE 1,SFDC Override Records
CREATE OR REPLACE TEMPORARY VIEW SFDCPropertyFlagRecords AS
SELECT *
FROM ModifyAddress
WHERE SFDC_Override IS NOT NULL

-- COMMAND ----------

-- DBTITLE 1,TEST TABLE: modify_address (MAIN OUTPUT)
CREATE OR REPLACE TABLE crm.sfdc_dbx.unity_modify_address_v2_test AS
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

-- DBTITLE 1,✅ TEST COMPLETE - Tables Created
-- MAGIC %md
-- MAGIC ## ✅ Test Run Complete!
-- MAGIC
-- MAGIC ### Test Tables Created:
-- MAGIC 1. `team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test`
-- MAGIC 2. `team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test`
-- MAGIC 3. `team_sandbox.data_engineering.unity_property_duplicate_status_v2_test`
-- MAGIC 4. `crm.sfdc_dbx.unity_modify_address_v2_test` ⭐ **Main output table**
-- MAGIC
-- MAGIC ### Next Step:
-- MAGIC Run the validation notebook to compare with production tables.

-- COMMAND ----------

-- DBTITLE 1,Quick Test Summary
SELECT
    'V2 TEST (sfdc_id approach)' AS version,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records,
    SUM(CASE WHEN match_method = 'DIRECT_SFDC_ID' THEN 1 ELSE 0 END) AS direct_sfdc_id_matches,
    SUM(CASE WHEN match_method = 'ADDRESS_MATCH_FALLBACK' THEN 1 ELSE 0 END) AS address_fallback_matches,
    ROUND(SUM(CASE WHEN match_method = 'DIRECT_SFDC_ID' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_direct_matches
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test
