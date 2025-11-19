-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Validation: V2 Test vs V1 Production
-- MAGIC
-- MAGIC This notebook compares the V2 test results against V1 production results to validate the new approach.
-- MAGIC
-- MAGIC ## Tables Being Compared:
-- MAGIC
-- MAGIC | Table Type | V1 Production | V2 Test |
-- MAGIC |------------|---------------|---------|
-- MAGIC | **Main Output** | `crm.sfdc_dbx.unity_modify_address` | `crm.sfdc_dbx.unity_modify_address_v2_test` |
-- MAGIC | **Duplicates** | `team_sandbox.data_engineering.unity_sfdc_fde_duplicates` | `team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test` |
-- MAGIC | **Dupe Status** | `team_sandbox.data_engineering.unity_property_duplicate_status` | `team_sandbox.data_engineering.unity_property_duplicate_status_v2_test` |
-- MAGIC
-- MAGIC ## What to Look For:
-- MAGIC
-- MAGIC ✅ **Expected:** V2 should have 21% more SFDC properties matched
-- MAGIC ✅ **Expected:** V2 should have cleaner, more accurate matches
-- MAGIC ⚠️ **Check:** Review any matches lost in V2 (should be ~403)
-- MAGIC ⚠️ **Check:** Duplicate detection should remain stable

-- COMMAND ----------

-- DBTITLE 1,1. Overall Match Count Comparison
SELECT
    'V1 Production (Regex)' AS version,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records
FROM
    crm.sfdc_dbx.unity_modify_address

UNION ALL

SELECT
    'V2 Test (sfdc_id)' AS version,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test

UNION ALL

SELECT
    'Difference (V2 - V1)' AS version,
    COUNT(DISTINCT v2.sfdc_id) - COUNT(DISTINCT v1.sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT v2.fde_id) - COUNT(DISTINCT v1.fde_id) AS fde_properties,
    COUNT(v2.*) - COUNT(v1.*) AS total_records
FROM
    crm.sfdc_dbx.unity_modify_address v1
FULL OUTER JOIN
    crm.sfdc_dbx.unity_modify_address_v2_test v2
    ON 1=1

-- COMMAND ----------

-- DBTITLE 1,2. Match Method Breakdown (V2 Only)
SELECT
    match_method,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct_of_total
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test
GROUP BY
    match_method
ORDER BY
    total_records DESC

-- COMMAND ----------

-- DBTITLE 1,3. NEW Matches: Properties in V2 but NOT in V1
-- These are the 4,311+ new matches found by V2
CREATE OR REPLACE TEMPORARY VIEW NewMatchesInV2 AS
SELECT
    v2.sfdc_id,
    v2.fde_id,
    v2.match_method,
    sp.name AS sfdc_name,
    p.name AS fde_name,
    p.address AS fde_address,
    p.city AS fde_city,
    p.state AS fde_state,
    p.zip AS fde_zip,
    sp.property_address_street_s AS sfdc_address,
    sp.property_address_city_s AS sfdc_city,
    sp.property_address_state_code_s AS sfdc_state,
    sp.property_address_postal_code_s AS sfdc_zip
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test v2
LEFT JOIN
    crm.sfdc_dbx.unity_modify_address v1
    ON v2.sfdc_id = v1.sfdc_id AND v2.fde_id = v1.fde_id
INNER JOIN
    hive_metastore.salesforce.property_c sp ON v2.sfdc_id = sp.id
INNER JOIN
    rds.pg_rds_public.properties p ON v2.fde_id = p.id
WHERE
    v1.sfdc_id IS NULL;

-- Summary of new matches
SELECT
    'New Matches in V2' AS category,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records
FROM
    NewMatchesInV2;

-- COMMAND ----------

-- DBTITLE 1,4. Sample of NEW Matches (First 20)
-- Review these to ensure they look correct
SELECT
    sfdc_id,
    fde_id,
    match_method,
    sfdc_name,
    fde_name,
    sfdc_address,
    fde_address,
    CONCAT(sfdc_city, ', ', sfdc_state, ' ', sfdc_zip) AS sfdc_location,
    CONCAT(fde_city, ', ', fde_state, ' ', fde_zip) AS fde_location
FROM
    NewMatchesInV2
ORDER BY
    match_method, sfdc_name
LIMIT 20

-- COMMAND ----------

-- DBTITLE 1,5. LOST Matches: Properties in V1 but NOT in V2
-- These are the ~403 matches that V2 doesn't find (likely false positives from regex)
CREATE OR REPLACE TEMPORARY VIEW LostMatchesInV2 AS
SELECT
    v1.sfdc_id,
    v1.fde_id,
    sp.name AS sfdc_name,
    p.name AS fde_name,
    p.address AS fde_address,
    p.city AS fde_city,
    p.state AS fde_state,
    p.zip AS fde_zip,
    sp.property_address_street_s AS sfdc_address,
    sp.property_address_city_s AS sfdc_city,
    sp.property_address_state_code_s AS sfdc_state,
    sp.property_address_postal_code_s AS sfdc_zip,
    -- Check if FDE property has sfdc_id populated
    p.sfdc_id AS fde_has_sfdc_id,
    CASE
        WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id <> v1.sfdc_id
        THEN 'MISMATCH: FDE.sfdc_id points to different SFDC property'
        WHEN p.sfdc_id IS NULL
        THEN 'FDE property has no sfdc_id'
        ELSE 'Match'
    END AS sfdc_id_status
FROM
    crm.sfdc_dbx.unity_modify_address v1
LEFT JOIN
    crm.sfdc_dbx.unity_modify_address_v2_test v2
    ON v1.sfdc_id = v2.sfdc_id AND v1.fde_id = v2.fde_id
INNER JOIN
    hive_metastore.salesforce.property_c sp ON v1.sfdc_id = sp.id
INNER JOIN
    rds.pg_rds_public.properties p ON v1.fde_id = p.id
WHERE
    v2.sfdc_id IS NULL;

-- Summary of lost matches
SELECT
    'Lost Matches in V2' AS category,
    COUNT(DISTINCT sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT fde_id) AS fde_properties,
    COUNT(*) AS total_records
FROM
    LostMatchesInV2;

-- COMMAND ----------

-- DBTITLE 1,6. Analysis of LOST Matches by sfdc_id Status
-- This helps us understand WHY V2 didn't match these
SELECT
    sfdc_id_status,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct_of_lost
FROM
    LostMatchesInV2
GROUP BY
    sfdc_id_status
ORDER BY
    count DESC

-- COMMAND ----------

-- DBTITLE 1,7. Sample of LOST Matches (First 20)
-- Review these carefully - are they legitimate matches or false positives?
SELECT
    sfdc_id,
    fde_id,
    sfdc_id_status,
    sfdc_name,
    fde_name,
    sfdc_address,
    fde_address,
    CONCAT(sfdc_city, ', ', sfdc_state, ' ', sfdc_zip) AS sfdc_location,
    CONCAT(fde_city, ', ', fde_state, ' ', fde_zip) AS fde_location,
    fde_has_sfdc_id
FROM
    LostMatchesInV2
ORDER BY
    sfdc_id_status, sfdc_name
LIMIT 20

-- COMMAND ----------

-- DBTITLE 1,8. Address Quality Comparison for LOST Matches
-- Check if addresses actually match (to identify false positives in V1)
SELECT
    COUNT(*) AS total_lost_matches,
    SUM(CASE WHEN UPPER(TRIM(sfdc_address)) = UPPER(TRIM(fde_address)) THEN 1 ELSE 0 END) AS exact_address_match,
    SUM(CASE WHEN UPPER(TRIM(sfdc_city)) = UPPER(TRIM(fde_city)) THEN 1 ELSE 0 END) AS exact_city_match,
    SUM(CASE WHEN UPPER(TRIM(sfdc_state)) = UPPER(TRIM(fde_state)) THEN 1 ELSE 0 END) AS exact_state_match,
    SUM(CASE WHEN SUBSTR(TRIM(sfdc_zip), 1, 5) = SUBSTR(TRIM(fde_zip), 1, 5) THEN 1 ELSE 0 END) AS exact_zip_match,
    SUM(CASE
        WHEN UPPER(TRIM(sfdc_address)) = UPPER(TRIM(fde_address))
        AND UPPER(TRIM(sfdc_city)) = UPPER(TRIM(fde_city))
        AND UPPER(TRIM(sfdc_state)) = UPPER(TRIM(fde_state))
        AND SUBSTR(TRIM(sfdc_zip), 1, 5) = SUBSTR(TRIM(fde_zip), 1, 5)
        THEN 1 ELSE 0 END) AS full_address_match
FROM
    LostMatchesInV2

-- COMMAND ----------

-- DBTITLE 1,9. Duplicate Status Comparison
-- Compare duplicate detection between V1 and V2
SELECT
    'V1 Production' AS version,
    FinalDupeStatus,
    COUNT(*) AS count
FROM
    team_sandbox.data_engineering.unity_sfdc_fde_duplicates
GROUP BY
    FinalDupeStatus

UNION ALL

SELECT
    'V2 Test' AS version,
    FinalDupeStatus,
    COUNT(*) AS count
FROM
    team_sandbox.data_engineering.unity_sfdc_fde_duplicates_v2_test
GROUP BY
    FinalDupeStatus

ORDER BY
    version, count DESC

-- COMMAND ----------

-- DBTITLE 1,10. API/Partner Property Flags Comparison
SELECT
    'V1 Production' AS version,
    IsPartnerProperty,
    COUNT(*) AS count,
    COUNT(DISTINCT sfdc_id) AS distinct_sfdc,
    COUNT(DISTINCT fde_id) AS distinct_fde
FROM
    crm.sfdc_dbx.unity_modify_address
GROUP BY
    IsPartnerProperty

UNION ALL

SELECT
    'V2 Test' AS version,
    IsPartnerProperty,
    COUNT(*) AS count,
    COUNT(DISTINCT sfdc_id) AS distinct_sfdc,
    COUNT(DISTINCT fde_id) AS distinct_fde
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test
GROUP BY
    IsPartnerProperty

ORDER BY
    version, IsPartnerProperty

-- COMMAND ----------

-- DBTITLE 1,11. PropertyCreatedBy Distribution Comparison
SELECT
    'V1 Production' AS version,
    PropertyCreatedBy,
    COUNT(*) AS count
FROM
    crm.sfdc_dbx.unity_modify_address
GROUP BY
    PropertyCreatedBy

UNION ALL

SELECT
    'V2 Test' AS version,
    PropertyCreatedBy,
    COUNT(*) AS count
FROM
    crm.sfdc_dbx.unity_modify_address_v2_test
GROUP BY
    PropertyCreatedBy

ORDER BY
    version, count DESC

-- COMMAND ----------

-- DBTITLE 1,12. Overlap Analysis: Exact Matches Between V1 and V2
SELECT
    'Exact Matches (Both V1 and V2)' AS category,
    COUNT(DISTINCT v1.sfdc_id) AS sfdc_properties,
    COUNT(DISTINCT v1.fde_id) AS fde_properties,
    ROUND(COUNT(DISTINCT v1.sfdc_id) * 100.0 / (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address), 2) AS pct_of_v1,
    ROUND(COUNT(DISTINCT v1.sfdc_id) * 100.0 / (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address_v2_test), 2) AS pct_of_v2
FROM
    crm.sfdc_dbx.unity_modify_address v1
INNER JOIN
    crm.sfdc_dbx.unity_modify_address_v2_test v2
    ON v1.sfdc_id = v2.sfdc_id AND v1.fde_id = v2.fde_id

-- COMMAND ----------

-- DBTITLE 1,13. SFDC Override Handling Comparison
-- Verify that SFDC Override records are handled correctly in both versions
SELECT
    'V1 - Has SFDC Override' AS category,
    COUNT(*) AS count,
    COUNT(DISTINCT sfdc_id) AS distinct_sfdc,
    COUNT(DISTINCT fde_id) AS distinct_fde
FROM
    team_sandbox.data_engineering.unity_salesforce_actioned_duplicates
WHERE
    SFDC_Override IS NOT NULL

UNION ALL

SELECT
    'V2 - Has SFDC Override' AS category,
    COUNT(*) AS count,
    COUNT(DISTINCT sfdc_id) AS distinct_sfdc,
    COUNT(DISTINCT fde_id) AS distinct_fde
FROM
    team_sandbox.data_engineering.unity_salesforce_actioned_duplicates_v2_test
WHERE
    SFDC_Override IS NOT NULL

-- COMMAND ----------

-- DBTITLE 1,14. Final Summary Report
-- MAGIC %md
-- MAGIC ## 📊 Summary Report
-- MAGIC
-- MAGIC ### Key Metrics to Review:
-- MAGIC
-- MAGIC 1. **Match Count** (Cell 1): V2 should show ~21% more SFDC properties
-- MAGIC 2. **Match Method** (Cell 2): Should show 80% direct sfdc_id, 20% fallback
-- MAGIC 3. **New Matches** (Cell 3): Should show ~4,311 new matches
-- MAGIC 4. **Lost Matches** (Cell 5): Should show ~403 lost matches
-- MAGIC 5. **Lost Match Analysis** (Cell 6): Check why matches were lost
-- MAGIC 6. **Duplicate Status** (Cell 9): Should remain stable
-- MAGIC 7. **API Flags** (Cell 10): Should remain consistent
-- MAGIC
-- MAGIC ### Decision Criteria:
-- MAGIC
-- MAGIC ✅ **Proceed with V2 if:**
-- MAGIC - V2 has 15-25% more SFDC properties matched
-- MAGIC - Lost matches (Cell 7) are primarily false positives (mismatched addresses)
-- MAGIC - Duplicate detection remains stable (Cell 9)
-- MAGIC - API/Partner flags remain consistent (Cell 10)
-- MAGIC
-- MAGIC ⚠️ **Investigate further if:**
-- MAGIC - Lost matches include legitimate, accurate matches
-- MAGIC - Duplicate detection shows significant changes
-- MAGIC - API flags are inconsistent
-- MAGIC
-- MAGIC ❌ **Do NOT proceed if:**
-- MAGIC - V2 has fewer total matches than V1
-- MAGIC - Critical business logic is broken (duplicates, API flags, etc.)

-- COMMAND ----------

-- DBTITLE 1,15. Export Results for Stakeholder Review
-- Create a summary table that can be easily shared
CREATE OR REPLACE TABLE team_sandbox.data_engineering.modify_address_v2_validation_summary AS
SELECT
    'Match Counts' AS metric_category,
    'V1 SFDC Properties' AS metric_name,
    CAST(COUNT(DISTINCT sfdc_id) AS STRING) AS metric_value
FROM crm.sfdc_dbx.unity_modify_address

UNION ALL

SELECT
    'Match Counts' AS metric_category,
    'V2 SFDC Properties' AS metric_name,
    CAST(COUNT(DISTINCT sfdc_id) AS STRING) AS metric_value
FROM crm.sfdc_dbx.unity_modify_address_v2_test

UNION ALL

SELECT
    'Match Counts' AS metric_category,
    'Improvement' AS metric_name,
    CONCAT('+', CAST(
        (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address_v2_test) -
        (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address)
    AS STRING), ' (+',
    CAST(ROUND(
        ((SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address_v2_test) -
         (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address)) * 100.0 /
        (SELECT COUNT(DISTINCT sfdc_id) FROM crm.sfdc_dbx.unity_modify_address)
    , 2) AS STRING), '%)')

UNION ALL

SELECT
    'New/Lost Matches' AS metric_category,
    'New Matches in V2' AS metric_name,
    CAST(COUNT(*) AS STRING) AS metric_value
FROM (
    SELECT v2.sfdc_id, v2.fde_id
    FROM crm.sfdc_dbx.unity_modify_address_v2_test v2
    LEFT JOIN crm.sfdc_dbx.unity_modify_address v1 ON v2.sfdc_id = v1.sfdc_id AND v2.fde_id = v1.fde_id
    WHERE v1.sfdc_id IS NULL
)

UNION ALL

SELECT
    'New/Lost Matches' AS metric_category,
    'Lost Matches in V2' AS metric_name,
    CAST(COUNT(*) AS STRING) AS metric_value
FROM (
    SELECT v1.sfdc_id, v1.fde_id
    FROM crm.sfdc_dbx.unity_modify_address v1
    LEFT JOIN crm.sfdc_dbx.unity_modify_address_v2_test v2 ON v1.sfdc_id = v2.sfdc_id AND v1.fde_id = v2.fde_id
    WHERE v2.sfdc_id IS NULL
)

ORDER BY metric_category, metric_name;

-- Display the summary
SELECT * FROM team_sandbox.data_engineering.modify_address_v2_validation_summary;
