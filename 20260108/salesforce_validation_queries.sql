-- ============================================================================
-- SALESFORCE VALIDATION QUERIES - Sync A (CREATE)
-- Run these in Salesforce Workbench: https://workbench.developerforce.com
-- ============================================================================

-- QUERY 1: Count records created TODAY
-- Should return: ~685 (from Sync A)
-- ============================================================================
SELECT COUNT()
FROM Product_Property__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false


-- QUERY 2: Count records created in last hour
-- More precise - should show exactly what Sync A created
-- ============================================================================
SELECT COUNT()
FROM Product_Property__c
WHERE CreatedDate = LAST_N_HOURS:1
  AND IsDeleted = false


-- QUERY 3: Sample of newly created records
-- See what was actually created
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    Short_ID__c,
    ID_Verification_Enabled__c,
    Bank_Linking_Enabled__c,
    Connected_Payroll_Enabled__c,
    Income_Verification_Enabled__c,
    Fraud_Detection_Enabled__c,
    CreatedDate
FROM Product_Property__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false
ORDER BY CreatedDate DESC
LIMIT 10


-- QUERY 4: Total Product_Property records before and after
-- Get baseline to compare
-- ============================================================================
SELECT COUNT()
FROM Product_Property__c
WHERE IsDeleted = false


-- QUERY 5: Check for any errors or validation failures
-- See if Salesforce blocked any records
-- ============================================================================
SELECT
    Id,
    Name,
    Snappt_Property_ID__c,
    LastModifiedDate
FROM Product_Property__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false
ORDER BY CreatedDate DESC


-- ============================================================================
-- INTERPRETATION GUIDE
-- ============================================================================

-- QUERY 1 Result:
--   Expected: ~685 records
--   If 680-690: ✅ EXCELLENT - Sync A worked perfectly
--   If 0-50: ⚠️ PROBLEM - Records didn't make it to Salesforce
--   If >700: ⚠️ UNEXPECTED - More records than expected

-- QUERY 2 Result:
--   Expected: Same as Query 1 (~685)
--   More precise time window

-- QUERY 3 Result:
--   Check that:
--   - Property names look correct
--   - Feature flags have values (true/false)
--   - Snappt_Property_ID__c is populated
--   - CreatedDate is within last hour

-- QUERY 4 Result:
--   Expected: ~18,560 total (17,875 before + 685 new)
--   Compare with baseline from before Sync A

-- ============================================================================
-- NEXT STEPS BASED ON RESULTS
-- ============================================================================

-- If Query 1 shows ~685 records:
--   ✅ SUCCESS - Proceed with Sync B (UPDATE)
--
-- If Query 1 shows 0 records:
--   ⚠️ PROBLEM - Check:
--   1. Are you looking at the right Salesforce org?
--   2. Did Census connect to the right org?
--   3. Check Census logs for actual errors
--
-- If Query 3 shows data looks wrong:
--   ⚠️ QUALITY ISSUE - Investigate data mapping
--   Review Census field mappings
