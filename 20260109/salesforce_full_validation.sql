-- ============================================================================
-- SALESFORCE FULL VALIDATION - Both Syncs Complete
-- Run these in Salesforce Workbench and download results
-- ============================================================================

-- QUERY 1: Overall Impact Summary
-- Shows total creates and updates from today
-- ============================================================================
-- Creates (new records)
SELECT 'CREATES' AS Operation, COUNT() AS RecordCount
FROM Product_Property__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false

-- Updates (modified existing)
UNION ALL
SELECT 'UPDATES' AS Operation, COUNT() AS RecordCount
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND CreatedDate != TODAY
  AND IsDeleted = false

-- Total touched
UNION ALL
SELECT 'TOTAL_MODIFIED' AS Operation, COUNT() AS RecordCount
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND IsDeleted = false


-- ============================================================================
-- QUERY 2: Feature Flag Distribution (After Sync)
-- Shows how many properties have each feature enabled
-- ============================================================================
SELECT
    'ID_Verification' AS Feature,
    SUM(CASE WHEN ID_Verification_Enabled__c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN ID_Verification_Enabled__c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT() AS Total
FROM Product_Property__c
WHERE IsDeleted = false

UNION ALL

SELECT
    'Bank_Linking' AS Feature,
    SUM(CASE WHEN Bank_Linking_Enabled__c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN Bank_Linking_Enabled__c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT() AS Total
FROM Product_Property__c
WHERE IsDeleted = false

UNION ALL

SELECT
    'Connected_Payroll' AS Feature,
    SUM(CASE WHEN Connected_Payroll_Enabled__c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN Connected_Payroll_Enabled__c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT() AS Total
FROM Product_Property__c
WHERE IsDeleted = false

UNION ALL

SELECT
    'Income_Verification' AS Feature,
    SUM(CASE WHEN Income_Verification_Enabled__c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN Income_Verification_Enabled__c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT() AS Total
FROM Product_Property__c
WHERE IsDeleted = false

UNION ALL

SELECT
    'Fraud_Detection' AS Feature,
    SUM(CASE WHEN Fraud_Detection_Enabled__c = true THEN 1 ELSE 0 END) AS Enabled_Count,
    SUM(CASE WHEN Fraud_Detection_Enabled__c = false THEN 1 ELSE 0 END) AS Disabled_Count,
    COUNT() AS Total
FROM Product_Property__c
WHERE IsDeleted = false


-- ============================================================================
-- QUERY 3: Sample of Created Records (Sync A Impact)
-- Shows 50 newly created properties
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    Short_ID__c,
    Company_Name__c,
    Address__c,
    City__c,
    State__c,
    ID_Verification_Enabled__c,
    Bank_Linking_Enabled__c,
    Connected_Payroll_Enabled__c,
    Income_Verification_Enabled__c,
    Fraud_Detection_Enabled__c,
    Active_Property_Count__c,
    Is_Multi_Property__c,
    CreatedDate,
    LastModifiedDate
FROM Product_Property__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false
ORDER BY CreatedDate DESC
LIMIT 50


-- ============================================================================
-- QUERY 4: Sample of Updated Records (Sync B Impact)
-- Shows 100 properties that were updated today (not created today)
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    Short_ID__c,
    Company_Name__c,
    ID_Verification_Enabled__c,
    Bank_Linking_Enabled__c,
    Connected_Payroll_Enabled__c,
    Income_Verification_Enabled__c,
    Fraud_Detection_Enabled__c,
    Active_Property_Count__c,
    Is_Multi_Property__c,
    CreatedDate,
    LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND CreatedDate != TODAY
  AND IsDeleted = false
ORDER BY LastModifiedDate DESC
LIMIT 100


-- ============================================================================
-- QUERY 5: Records with Multiple Features Enabled
-- Properties with 3+ features enabled (high-value properties)
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    ID_Verification_Enabled__c,
    Bank_Linking_Enabled__c,
    Connected_Payroll_Enabled__c,
    Income_Verification_Enabled__c,
    Fraud_Detection_Enabled__c,
    Total_Feature_Count__c,
    LastModifiedDate
FROM Product_Property__c
WHERE IsDeleted = false
  AND (
    (ID_Verification_Enabled__c = true AND Bank_Linking_Enabled__c = true AND Connected_Payroll_Enabled__c = true)
    OR Total_Feature_Count__c >= 3
  )
  AND LastModifiedDate = TODAY
ORDER BY Total_Feature_Count__c DESC
LIMIT 100


-- ============================================================================
-- QUERY 6: Multi-Property Records
-- Properties linked to multiple SFDC Property IDs
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    SF_Property_ID__c,
    Is_Multi_Property__c,
    Active_Property_Count__c,
    ID_Verification_Enabled__c,
    Bank_Linking_Enabled__c,
    Connected_Payroll_Enabled__c,
    LastModifiedDate
FROM Product_Property__c
WHERE IsDeleted = false
  AND Is_Multi_Property__c = true
  AND LastModifiedDate = TODAY
ORDER BY Active_Property_Count__c DESC
LIMIT 100


-- ============================================================================
-- QUERY 7: Records Modified in Last Hour (Most Recent Changes)
-- Precise timing of sync impact
-- ============================================================================
SELECT
    COUNT() AS Records_Modified_Last_Hour
FROM Product_Property__c
WHERE LastModifiedDate >= LAST_N_HOURS:1
  AND IsDeleted = false


-- ============================================================================
-- QUERY 8: Total Product_Property Records (Before vs After)
-- Current state of entire object
-- ============================================================================
SELECT
    COUNT() AS Total_Product_Property_Records
FROM Product_Property__c
WHERE IsDeleted = false


-- ============================================================================
-- QUERY 9: Records with Timestamps (Feature Enabled Dates)
-- Check that enabled dates are populated correctly
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    ID_Verification_Enabled__c,
    ID_Verification_Start_Date__c,
    Bank_Linking_Enabled__c,
    Bank_Linking_Start_Date__c,
    Connected_Payroll_Enabled__c,
    Connected_Payroll_Start_Date__c,
    Income_Verification_Enabled__c,
    Income_Verification_Start_Date__c,
    Fraud_Detection_Enabled__c,
    Fraud_Detection_Start_Date__c,
    LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND IsDeleted = false
  AND (
    ID_Verification_Enabled__c = true
    OR Bank_Linking_Enabled__c = true
    OR Connected_Payroll_Enabled__c = true
    OR Income_Verification_Enabled__c = true
    OR Fraud_Detection_Enabled__c = true
  )
ORDER BY LastModifiedDate DESC
LIMIT 100


-- ============================================================================
-- QUERY 10: Data Quality Check - Records Missing Key Fields
-- Find any records with data quality issues
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    Short_ID__c,
    Company_Name__c,
    Address__c,
    City__c,
    State__c,
    LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND IsDeleted = false
  AND (
    Snappt_Property_ID__c = null
    OR Name = null
    OR Company_Name__c = null
  )
LIMIT 50


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
--   Multi-property records should have:
--     - Is_Multi_Property__c = true
--     - Active_Property_Count__c > 1
--     - Features enabled

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
-- HOW TO USE THESE QUERIES
-- ============================================================================

-- 1. Go to Salesforce Workbench: https://workbench.developerforce.com
-- 2. Login with your credentials
-- 3. Navigate to: Queries → SOQL Query
-- 4. Copy/paste each query ONE AT A TIME
-- 5. Click "Query" to execute
-- 6. Click "Download" to save results as CSV
-- 7. Upload CSVs here or share key numbers

-- Priority order:
--   1. Query 1 (Overall Impact) - MUST RUN
--   2. Query 2 (Feature Distribution) - MUST RUN
--   3. Query 8 (Total Records) - MUST RUN
--   4-10. Optional but recommended
