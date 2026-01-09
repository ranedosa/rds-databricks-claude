-- =============================================================================
-- PILOT VALIDATION QUERIES - RDS to Salesforce Sync
-- =============================================================================
-- Project: Automated Property Synchronization
-- Date: January 7, 2026
-- Pilot: 100 properties (50 CREATE + 50 UPDATE)
-- Expected Results: 36 creates + 64 updates = 100 records
-- =============================================================================

-- -----------------------------------------------------------------------------
-- QUERY 1: View All Records Updated Today
-- Expected: ~100 records (pilot test)
-- Run in: Developer Console > Query Editor
-- -----------------------------------------------------------------------------
SELECT
  Id,
  Snappt_Property_ID__c,
  Name,
  Company_Name__c,
  Company_ID__c,
  Short_ID__c,
  Address__Street__s,
  Address__City__s,
  Address__StateCode__s,
  Address__PostalCode__s,
  ID_Verification_Enabled__c,
  Bank_Linking_Enabled__c,
  Connected_Payroll_Enabled__c,
  Income_Verification_Enabled__c,
  Fraud_Detection_Enabled__c,
  ID_Verification_Start_Date__c,
  Bank_Linking_Start_Date__c,
  Connected_Payroll_Start_Date__c,
  Income_Verification_Start_Date__c,
  Fraud_Detection_Start_Date__c,
  LastModifiedDate,
  CreatedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
ORDER BY LastModifiedDate DESC
LIMIT 200;

-- -----------------------------------------------------------------------------
-- QUERY 2: Count Records by Creation Date
-- Expected: ~36 created today, ~64 updated today
-- -----------------------------------------------------------------------------
SELECT
  COUNT(Id) AS Total_Count,
  COUNT(CASE WHEN CreatedDate = TODAY THEN 1 END) AS Created_Today,
  COUNT(CASE WHEN CreatedDate < TODAY AND LastModifiedDate = TODAY THEN 1 END) AS Updated_Today
FROM Product_Property__c
WHERE LastModifiedDate = TODAY;

-- -----------------------------------------------------------------------------
-- QUERY 3: Field Completeness Check
-- Expected: All 19 fields should be populated (non-null) for synced records
-- Note: Timestamp fields may be NULL if feature was never enabled
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  Name,
  CASE WHEN Snappt_Property_ID__c IS NULL THEN 'MISSING' ELSE 'OK' END AS RDS_Property_ID,
  CASE WHEN Name IS NULL THEN 'MISSING' ELSE 'OK' END AS Property_Name,
  CASE WHEN Company_Name__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Company_Name,
  CASE WHEN Company_ID__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Company_ID,
  CASE WHEN Short_ID__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Short_ID,
  CASE WHEN Address__Street__s IS NULL THEN 'MISSING' ELSE 'OK' END AS Address,
  CASE WHEN Address__City__s IS NULL THEN 'MISSING' ELSE 'OK' END AS City,
  CASE WHEN Address__StateCode__s IS NULL THEN 'MISSING' ELSE 'OK' END AS State,
  CASE WHEN Address__PostalCode__s IS NULL THEN 'MISSING' ELSE 'OK' END AS Postal_Code,
  CASE WHEN ID_Verification_Enabled__c IS NULL THEN 'MISSING' ELSE 'OK' END AS IDV_Enabled,
  CASE WHEN Bank_Linking_Enabled__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Bank_Linking_Enabled,
  CASE WHEN Connected_Payroll_Enabled__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Payroll_Enabled,
  CASE WHEN Income_Verification_Enabled__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Income_Insights_Enabled,
  CASE WHEN Fraud_Detection_Enabled__c IS NULL THEN 'MISSING' ELSE 'OK' END AS Doc_Fraud_Enabled
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
ORDER BY Snappt_Property_ID__c;

-- -----------------------------------------------------------------------------
-- QUERY 4: Feature Flag Summary
-- Expected: Distribution of TRUE/FALSE for each feature flag
-- -----------------------------------------------------------------------------
SELECT
  COUNT(Id) AS Total_Records,
  SUM(CASE WHEN ID_Verification_Enabled__c = TRUE THEN 1 ELSE 0 END) AS IDV_Enabled_Count,
  SUM(CASE WHEN Bank_Linking_Enabled__c = TRUE THEN 1 ELSE 0 END) AS Bank_Linking_Enabled_Count,
  SUM(CASE WHEN Connected_Payroll_Enabled__c = TRUE THEN 1 ELSE 0 END) AS Payroll_Enabled_Count,
  SUM(CASE WHEN Income_Verification_Enabled__c = TRUE THEN 1 ELSE 0 END) AS Income_Insights_Enabled_Count,
  SUM(CASE WHEN Fraud_Detection_Enabled__c = TRUE THEN 1 ELSE 0 END) AS Doc_Fraud_Enabled_Count
FROM Product_Property__c
WHERE LastModifiedDate = TODAY;

-- -----------------------------------------------------------------------------
-- QUERY 5: Timestamp Completeness Check
-- Expected: Some timestamps may be NULL (features never enabled)
-- -----------------------------------------------------------------------------
SELECT
  COUNT(Id) AS Total_Records,
  COUNT(ID_Verification_Start_Date__c) AS IDV_Timestamp_Count,
  COUNT(Bank_Linking_Start_Date__c) AS Bank_Linking_Timestamp_Count,
  COUNT(Connected_Payroll_Start_Date__c) AS Payroll_Timestamp_Count,
  COUNT(Income_Verification_Start_Date__c) AS Income_Insights_Timestamp_Count,
  COUNT(Fraud_Detection_Start_Date__c) AS Doc_Fraud_Timestamp_Count
FROM Product_Property__c
WHERE LastModifiedDate = TODAY;

-- -----------------------------------------------------------------------------
-- QUERY 6: Sample Records for Spot-Checking
-- Expected: First 10 records with all field details
-- Use to compare with Databricks source data
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  Name,
  Company_Name__c,
  Company_ID__c,
  Short_ID__c,
  Address__Street__s,
  Address__City__s,
  Address__StateCode__s,
  Address__PostalCode__s,
  ID_Verification_Enabled__c,
  Bank_Linking_Enabled__c,
  Connected_Payroll_Enabled__c,
  Income_Verification_Enabled__c,
  Fraud_Detection_Enabled__c,
  ID_Verification_Start_Date__c,
  Bank_Linking_Start_Date__c,
  Connected_Payroll_Start_Date__c,
  Income_Verification_Start_Date__c,
  Fraud_Detection_Start_Date__c,
  CreatedDate,
  LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
ORDER BY Snappt_Property_ID__c
LIMIT 10;

-- -----------------------------------------------------------------------------
-- QUERY 7: Records with Missing Critical Fields
-- Expected: 0 records (all critical fields should be populated)
-- Critical fields: Snappt_Property_ID__c, Name, Company_ID__c
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  Name,
  Company_ID__c,
  LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND (Snappt_Property_ID__c IS NULL OR Name IS NULL OR Company_ID__c IS NULL);

-- -----------------------------------------------------------------------------
-- QUERY 8: Records Created Today (CREATE Sync Results)
-- Expected: ~36 records from Sync A (CREATE)
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  Name,
  Company_Name__c,
  Address__Street__s,
  Address__City__s,
  Address__StateCode__s,
  CreatedDate
FROM Product_Property__c
WHERE CreatedDate = TODAY
ORDER BY CreatedDate DESC;

-- -----------------------------------------------------------------------------
-- QUERY 9: Records Updated Today (UPDATE Sync Results)
-- Expected: ~64 records (14 from Sync A + 50 from Sync B)
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  Name,
  Company_Name__c,
  Address__Street__s,
  Address__City__s,
  Address__StateCode__s,
  CreatedDate,
  LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate = TODAY
  AND CreatedDate < TODAY
ORDER BY LastModifiedDate DESC;

-- -----------------------------------------------------------------------------
-- QUERY 10: Time-Based Validation (Records Synced in Last Hour)
-- Expected: All 100 records if run shortly after pilot
-- Pilot execution time: ~2 minutes (around 8:43-8:48 PM EST)
-- -----------------------------------------------------------------------------
SELECT
  COUNT(Id) AS Total_Count
FROM Product_Property__c
WHERE LastModifiedDate >= :HOUR_AGO;
-- Note: Replace :HOUR_AGO with LAST_N_HOURS:1 in actual query

-- -----------------------------------------------------------------------------
-- QUERY 11: Duplicate Check (Same Snappt_Property_ID__c)
-- Expected: 0 duplicates (External ID enforces uniqueness)
-- -----------------------------------------------------------------------------
SELECT
  Snappt_Property_ID__c,
  COUNT(Id) AS Record_Count
FROM Product_Property__c
WHERE Snappt_Property_ID__c IS NOT NULL
GROUP BY Snappt_Property_ID__c
HAVING COUNT(Id) > 1;

-- -----------------------------------------------------------------------------
-- QUERY 12: Address Completeness
-- Expected: Most records should have complete addresses
-- Some properties may have NULL postal codes or states
-- -----------------------------------------------------------------------------
SELECT
  COUNT(Id) AS Total_Records,
  COUNT(Address__Street__s) AS Has_Street,
  COUNT(Address__City__s) AS Has_City,
  COUNT(Address__StateCode__s) AS Has_State,
  COUNT(Address__PostalCode__s) AS Has_Postal_Code
FROM Product_Property__c
WHERE LastModifiedDate = TODAY;

-- =============================================================================
-- VALIDATION CHECKLIST
-- =============================================================================
-- [ ] QUERY 1: View all 100 records updated today
-- [ ] QUERY 2: Confirm ~36 creates + ~64 updates = 100 total
-- [ ] QUERY 3: Verify no critical fields are missing
-- [ ] QUERY 4: Review feature flag distribution (should match source)
-- [ ] QUERY 5: Check timestamp completeness (NULL is OK if feature disabled)
-- [ ] QUERY 6: Spot-check 10 records against Databricks source
-- [ ] QUERY 7: Confirm 0 records with missing critical fields
-- [ ] QUERY 11: Confirm 0 duplicate Snappt_Property_ID__c values
-- [ ] QUERY 12: Verify address fields are mostly populated
-- =============================================================================

-- =============================================================================
-- COMPARISON WITH DATABRICKS SOURCE
-- =============================================================================
-- To validate sync accuracy, compare these SOQL results with Databricks data:
--
-- Databricks Query:
-- SELECT * FROM crm.sfdc_dbx.properties_to_create LIMIT 50
-- SELECT * FROM crm.sfdc_dbx.properties_to_update LIMIT 50
--
-- Compare:
-- 1. Snappt_Property_ID__c matches rds_property_id
-- 2. Feature flags (TRUE/FALSE) match source
-- 3. Timestamps match *_enabled_at fields (NULL is OK)
-- 4. Addresses match source (street, city, state, postal_code)
-- 5. Company names and IDs match
-- =============================================================================

-- =============================================================================
-- SUCCESS CRITERIA
-- =============================================================================
-- ✅ All 100 records present in QUERY 1
-- ✅ Record counts match expected (QUERY 2)
-- ✅ No missing critical fields (QUERY 7 returns 0 rows)
-- ✅ No duplicate Snappt_Property_ID__c values (QUERY 11 returns 0 rows)
-- ✅ Feature flags match Databricks source (spot-check QUERY 6)
-- ✅ Addresses are populated and accurate (QUERY 12 + spot-check)
-- ✅ Execution time was <5 minutes (actual: ~2 minutes)
-- =============================================================================

-- =============================================================================
-- NEXT STEPS AFTER VALIDATION
-- =============================================================================
-- IF ALL VALIDATION PASSES:
-- 1. Make GO decision for Day 3 full rollout
-- 2. Remove LIMIT 50 from Census models
-- 3. Run Sync A (CREATE) for 735 properties
-- 4. Run Sync B (UPDATE) for 7,881 properties
-- 5. Schedule recurring daily syncs
--
-- IF ISSUES FOUND:
-- 1. Document specific failures in PILOT_RESULTS.md
-- 2. Debug mapping or sync configuration
-- 3. Retry pilot test
-- 4. Revalidate before proceeding to Day 3
-- =============================================================================
