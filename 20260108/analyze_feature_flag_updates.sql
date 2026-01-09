-- ============================================================================
-- UPDATE IMPACT ANALYSIS: What will change in 7,820 properties?
-- ============================================================================
-- Compares properties_to_update (NEW) with current Salesforce (OLD)
-- ============================================================================

-- STEP 1: Feature Flag Changes by Type
-- Shows how many properties will have each feature flag updated
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    property_name,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled,
    is_multi_property
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled,
    COALESCE(is_multi_property_c, false) as is_multi_property
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'ID Verification' as feature,
  COUNT(CASE WHEN n.idv_enabled != c.idv_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.idv_enabled = true AND c.idv_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.idv_enabled = false AND c.idv_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched,
  ROUND(COUNT(CASE WHEN n.idv_enabled != c.idv_enabled THEN 1 END) * 100.0 / COUNT(*), 1) as pct_change
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Bank Linking',
  COUNT(CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled THEN 1 END),
  COUNT(CASE WHEN n.bank_linking_enabled = true AND c.bank_linking_enabled = false THEN 1 END),
  COUNT(CASE WHEN n.bank_linking_enabled = false AND c.bank_linking_enabled = true THEN 1 END),
  COUNT(*),
  ROUND(COUNT(CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled THEN 1 END) * 100.0 / COUNT(*), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Connected Payroll',
  COUNT(CASE WHEN n.payroll_enabled != c.payroll_enabled THEN 1 END),
  COUNT(CASE WHEN n.payroll_enabled = true AND c.payroll_enabled = false THEN 1 END),
  COUNT(CASE WHEN n.payroll_enabled = false AND c.payroll_enabled = true THEN 1 END),
  COUNT(*),
  ROUND(COUNT(CASE WHEN n.payroll_enabled != c.payroll_enabled THEN 1 END) * 100.0 / COUNT(*), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Income Verification',
  COUNT(CASE WHEN n.income_insights_enabled != c.income_insights_enabled THEN 1 END),
  COUNT(CASE WHEN n.income_insights_enabled = true AND c.income_insights_enabled = false THEN 1 END),
  COUNT(CASE WHEN n.income_insights_enabled = false AND c.income_insights_enabled = true THEN 1 END),
  COUNT(*),
  ROUND(COUNT(CASE WHEN n.income_insights_enabled != c.income_insights_enabled THEN 1 END) * 100.0 / COUNT(*), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Fraud Detection',
  COUNT(CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled THEN 1 END),
  COUNT(CASE WHEN n.document_fraud_enabled = true AND c.document_fraud_enabled = false THEN 1 END),
  COUNT(CASE WHEN n.document_fraud_enabled = false AND c.document_fraud_enabled = true THEN 1 END),
  COUNT(*),
  ROUND(COUNT(CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled THEN 1 END) * 100.0 / COUNT(*), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Multi-Property Flag',
  COUNT(CASE WHEN n.is_multi_property != c.is_multi_property THEN 1 END),
  COUNT(CASE WHEN n.is_multi_property = true AND c.is_multi_property = false THEN 1 END),
  COUNT(CASE WHEN n.is_multi_property = false AND c.is_multi_property = true THEN 1 END),
  COUNT(*),
  ROUND(COUNT(CASE WHEN n.is_multi_property != c.is_multi_property THEN 1 END) * 100.0 / COUNT(*), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

ORDER BY will_change DESC;


-- ============================================================================
-- STEP 2: Overall Summary
-- ============================================================================

WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled,
    is_multi_property
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled,
    COALESCE(is_multi_property_c, false) as is_multi_property
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'Total properties that will be updated' as category,
  COUNT(*) as count,
  CAST(100.0 AS DECIMAL(5,1)) as percentage
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Properties with ANY change',
  COUNT(*),
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM new_data n INNER JOIN current_data c ON n.property_id = c.property_id), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled
   OR n.is_multi_property != c.is_multi_property

UNION ALL

SELECT
  'Properties with NO changes',
  COUNT(*),
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM new_data n INNER JOIN current_data c ON n.property_id = c.property_id), 1)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = c.idv_enabled
  AND n.bank_linking_enabled = c.bank_linking_enabled
  AND n.payroll_enabled = c.payroll_enabled
  AND n.income_insights_enabled = c.income_insights_enabled
  AND n.document_fraud_enabled = c.document_fraud_enabled
  AND n.is_multi_property = c.is_multi_property;


-- ============================================================================
-- STEP 3: Sample - Properties with Changes
-- ============================================================================

WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    property_name,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  n.property_name,
  CASE WHEN n.idv_enabled != c.idv_enabled
    THEN CONCAT(CAST(c.idv_enabled AS STRING), ' → ', CAST(n.idv_enabled AS STRING))
    ELSE '='
  END as idv,
  CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled
    THEN CONCAT(CAST(c.bank_linking_enabled AS STRING), ' → ', CAST(n.bank_linking_enabled AS STRING))
    ELSE '='
  END as bank,
  CASE WHEN n.payroll_enabled != c.payroll_enabled
    THEN CONCAT(CAST(c.payroll_enabled AS STRING), ' → ', CAST(n.payroll_enabled AS STRING))
    ELSE '='
  END as payroll,
  CASE WHEN n.income_insights_enabled != c.income_insights_enabled
    THEN CONCAT(CAST(c.income_insights_enabled AS STRING), ' → ', CAST(n.income_insights_enabled AS STRING))
    ELSE '='
  END as income,
  CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled
    THEN CONCAT(CAST(c.document_fraud_enabled AS STRING), ' → ', CAST(n.document_fraud_enabled AS STRING))
    ELSE '='
  END as fraud
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled
ORDER BY n.property_name
LIMIT 30;
