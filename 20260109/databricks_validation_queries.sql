-- ============================================================================
-- DATABRICKS VALIDATION QUERIES - Day 3 Sync Validation
-- Run these in Databricks SQL Editor or Notebook
-- ============================================================================

-- QUERY 1: Overall Impact Summary
-- Shows total creates and updates from today
-- ============================================================================
SELECT 'CREATES' AS Operation, COUNT(*) AS RecordCount
FROM crm.salesforce.product_property
WHERE DATE(created_date) = CURRENT_DATE()
  AND _fivetran_deleted = false

UNION ALL

SELECT 'UPDATES' AS Operation, COUNT(*) AS RecordCount
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND DATE(created_date) != CURRENT_DATE()
  AND _fivetran_deleted = false

UNION ALL

SELECT 'TOTAL_MODIFIED' AS Operation, COUNT(*) AS RecordCount
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND _fivetran_deleted = false;


-- ============================================================================
-- QUERY 2: Feature Flag Distribution (After Sync)
-- Shows how many properties have each feature enabled
-- ============================================================================
SELECT
    'ID_Verification' AS Feature,
    SUM(CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN id_verification_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT(*) AS Total
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
    'Bank_Linking' AS Feature,
    SUM(CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN bank_linking_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT(*) AS Total
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
    'Connected_Payroll' AS Feature,
    SUM(CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN connected_payroll_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT(*) AS Total
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
    'Income_Verification' AS Feature,
    SUM(CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN income_verification_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT(*) AS Total
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
    'Fraud_Detection' AS Feature,
    SUM(CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN fraud_detection_enabled_c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT(*) AS Total
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false;


-- ============================================================================
-- QUERY 3: Sample of Created Records (Sync A Impact)
-- Shows 50 newly created properties
-- ============================================================================
SELECT
    id,
    name,
    snappt_property_id_c,
    short_id_c,
    company_name_c,
    address_street_s,
    address_city_s,
    address_state_code_s,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    income_verification_enabled_c,
    fraud_detection_enabled_c,
    -- Calculate total features inline since field doesn't exist
    (CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS total_feature_count,
    created_date,
    last_modified_date
FROM crm.salesforce.product_property
WHERE DATE(created_date) = CURRENT_DATE()
  AND _fivetran_deleted = false
ORDER BY created_date DESC
LIMIT 50;


-- ============================================================================
-- QUERY 4: Sample of Updated Records (Sync B Impact)
-- Shows 100 properties that were updated today (not created today)
-- ============================================================================
SELECT
    id,
    name,
    snappt_property_id_c,
    short_id_c,
    company_name_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    income_verification_enabled_c,
    fraud_detection_enabled_c,
    (CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS total_feature_count,
    created_date,
    last_modified_date
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND DATE(created_date) != CURRENT_DATE()
  AND _fivetran_deleted = false
ORDER BY last_modified_date DESC
LIMIT 100;


-- ============================================================================
-- QUERY 5: Records with Multiple Features Enabled
-- Properties with 3+ features enabled (high-value properties)
-- ============================================================================
WITH feature_counts AS (
  SELECT
    id,
    name,
    snappt_property_id_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    income_verification_enabled_c,
    fraud_detection_enabled_c,
    (CASE WHEN id_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN bank_linking_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN connected_payroll_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN income_verification_enabled_c = true THEN 1 ELSE 0 END +
     CASE WHEN fraud_detection_enabled_c = true THEN 1 ELSE 0 END) AS total_feature_count,
    last_modified_date
  FROM crm.salesforce.product_property
  WHERE _fivetran_deleted = false
    AND DATE(last_modified_date) = CURRENT_DATE()
)
SELECT
    id,
    name,
    snappt_property_id_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    income_verification_enabled_c,
    fraud_detection_enabled_c,
    total_feature_count,
    last_modified_date
FROM feature_counts
WHERE total_feature_count >= 3
ORDER BY total_feature_count DESC
LIMIT 100;


-- ============================================================================
-- QUERY 6: Multi-Property Records
-- Properties linked to multiple SFDC Property IDs
-- NOTE: is_multi_property_c and active_property_count_c fields don't exist
-- This query shows records with sf_property_id_c populated instead
-- ============================================================================
SELECT
    id,
    name,
    snappt_property_id_c,
    sf_property_id_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    last_modified_date
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false
  AND sf_property_id_c IS NOT NULL
  AND DATE(last_modified_date) = CURRENT_DATE()
ORDER BY last_modified_date DESC
LIMIT 100;


-- ============================================================================
-- QUERY 7: Records Modified in Last Hour (Most Recent Changes)
-- Precise timing of sync impact
-- ============================================================================
SELECT
    COUNT(*) AS Records_Modified_Last_Hour
FROM crm.salesforce.product_property
WHERE last_modified_date >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
  AND _fivetran_deleted = false;


-- ============================================================================
-- QUERY 8: Total Product_Property Records (Before vs After)
-- Current state of entire object
-- ============================================================================
SELECT
    COUNT(*) AS Total_Product_Property_Records
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false;


-- ============================================================================
-- QUERY 9: Records with Timestamps (Feature Enabled Dates)
-- Check that enabled dates are populated correctly
-- ============================================================================
SELECT
    id,
    name,
    snappt_property_id_c,
    id_verification_enabled_c,
    id_verification_start_date_c,
    bank_linking_enabled_c,
    bank_linking_start_date_c,
    connected_payroll_enabled_c,
    connected_payroll_start_date_c,
    income_verification_enabled_c,
    income_verification_start_date_c,
    fraud_detection_enabled_c,
    fraud_detection_start_date_c,
    last_modified_date
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND _fivetran_deleted = false
  AND (
    id_verification_enabled_c = true
    OR bank_linking_enabled_c = true
    OR connected_payroll_enabled_c = true
    OR income_verification_enabled_c = true
    OR fraud_detection_enabled_c = true
  )
ORDER BY last_modified_date DESC
LIMIT 100;


-- ============================================================================
-- QUERY 10: Data Quality Check - Records Missing Key Fields
-- Find any records with data quality issues
-- ============================================================================
SELECT
    id,
    name,
    snappt_property_id_c,
    short_id_c,
    company_name_c,
    address_street_s,
    address_city_s,
    address_state_code_s,
    last_modified_date
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND _fivetran_deleted = false
  AND (
    snappt_property_id_c IS NULL
    OR name IS NULL
    OR company_name_c IS NULL
  )
LIMIT 50;


-- ============================================================================
-- INTERPRETATION GUIDE
-- ============================================================================

-- QUERY 1 Expected Results:
--   CREATES: ~574-690 (Sync A impact)
--   UPDATES: ~7,500-7,820 (Sync B impact)
--   TOTAL_MODIFIED: ~8,100-8,500 (combined)

-- QUERY 2 Expected Results:
--   Should show realistic distribution of features
--   Compare with RDS source data for accuracy

-- QUERY 3 & 4 Expected Results:
--   Sample data should look correct
--   Feature flags should have true/false values
--   Timestamps should be populated where features enabled

-- QUERY 5 Expected Results:
--   Properties with multiple features = high-value customers
--   Check these are correct

-- QUERY 6 Expected Results:
--   NOTE: Multi-property tracking fields don't exist in Databricks table
--   This shows records with sf_property_id_c populated instead

-- QUERY 7 Expected Results:
--   Should match TOTAL_MODIFIED from Query 1
--   Confirms all changes happened in last hour

-- QUERY 8 Expected Results:
--   Total should be ~18,450-18,560
--   (Previous 17,875 + 574-685 new creates)

-- QUERY 9 Expected Results:
--   Enabled features should have start dates populated
--   Check dates are reasonable (not null, not far future)

-- QUERY 10 Expected Results:
--   Should return 0 rows (no missing key fields)
--   If rows returned = data quality issues to investigate

-- ============================================================================
-- HOW TO USE THESE QUERIES IN DATABRICKS
-- ============================================================================

-- Option 1: Databricks SQL Editor (Recommended)
--   1. Go to your Databricks workspace
--   2. Click "SQL Editor" in the sidebar
--   3. Copy/paste each query ONE AT A TIME
--   4. Click "Run" to execute
--   5. Click "Download" to save results as CSV

-- Option 2: Databricks Notebook
--   1. Create a new SQL notebook
--   2. Put each query in a separate cell with %%sql magic command
--   3. Run each cell
--   4. Results display inline

-- Option 3: Python Script
--   Use the Databricks SQL connector to run these programmatically

-- Priority order:
--   1. Query 1 (Overall Impact) - MUST RUN
--   2. Query 2 (Feature Distribution) - MUST RUN
--   3. Query 8 (Total Records) - MUST RUN
--   4-10. Optional but recommended

-- ============================================================================
-- NOTES ON DIFFERENCES FROM SALESFORCE
-- ============================================================================

-- Fields that don't exist in Databricks (may be Salesforce-calculated):
--   - Active_Property_Count__c → Not in crm.salesforce.product_property
--   - Is_Multi_Property__c → Not in crm.salesforce.product_property
--   - Total_Feature_Count__c → Calculated inline in queries

-- Address field differences:
--   - Address__c → address_street_s
--   - City__c → address_city_s
--   - State__c → address_state_code_s

-- Deletion tracking:
--   - IsDeleted → _fivetran_deleted (Fivetran's deletion flag)

-- Date functions:
--   - TODAY → CURRENT_DATE()
--   - LAST_N_HOURS:1 → CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
