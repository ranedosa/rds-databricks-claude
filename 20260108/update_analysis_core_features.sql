-- What Feature Flags Will Change? (5 Core Features Only)

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

SELECT 'SUMMARY' as analysis_type, NULL as feature, NULL as detail, NULL as count

UNION ALL

SELECT 'Total', NULL, 'Properties in UPDATE queue', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT 'Changes', NULL, 'Properties with ANY change', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled

UNION ALL

SELECT 'Changes', NULL, 'Properties with NO changes', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = c.idv_enabled
  AND n.bank_linking_enabled = c.bank_linking_enabled
  AND n.payroll_enabled = c.payroll_enabled
  AND n.income_insights_enabled = c.income_insights_enabled
  AND n.document_fraud_enabled = c.document_fraud_enabled

UNION ALL

SELECT 'BY FEATURE', NULL, NULL, NULL

UNION ALL

SELECT 'ID Verification', 'Total changing', NULL, COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled

UNION ALL

SELECT 'ID Verification', 'Turning ON', 'false → true', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = true AND c.idv_enabled = false

UNION ALL

SELECT 'ID Verification', 'Turning OFF', 'true → false ⚠️', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = false AND c.idv_enabled = true

UNION ALL

SELECT 'Bank Linking', 'Total changing', NULL, COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.bank_linking_enabled != c.bank_linking_enabled

UNION ALL

SELECT 'Bank Linking', 'Turning ON', 'false → true', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.bank_linking_enabled = true AND c.bank_linking_enabled = false

UNION ALL

SELECT 'Bank Linking', 'Turning OFF', 'true → false ⚠️', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.bank_linking_enabled = false AND c.bank_linking_enabled = true

UNION ALL

SELECT 'Connected Payroll', 'Total changing', NULL, COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.payroll_enabled != c.payroll_enabled

UNION ALL

SELECT 'Connected Payroll', 'Turning ON', 'false → true', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.payroll_enabled = true AND c.payroll_enabled = false

UNION ALL

SELECT 'Connected Payroll', 'Turning OFF', 'true → false ⚠️', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.payroll_enabled = false AND c.payroll_enabled = true

UNION ALL

SELECT 'Income Verification', 'Total changing', NULL, COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.income_insights_enabled != c.income_insights_enabled

UNION ALL

SELECT 'Income Verification', 'Turning ON', 'false → true', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.income_insights_enabled = true AND c.income_insights_enabled = false

UNION ALL

SELECT 'Income Verification', 'Turning OFF', 'true → false ⚠️', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.income_insights_enabled = false AND c.income_insights_enabled = true

UNION ALL

SELECT 'Fraud Detection', 'Total changing', NULL, COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.document_fraud_enabled != c.document_fraud_enabled

UNION ALL

SELECT 'Fraud Detection', 'Turning ON', 'false → true', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.document_fraud_enabled = true AND c.document_fraud_enabled = false

UNION ALL

SELECT 'Fraud Detection', 'Turning OFF', 'true → false ⚠️', COUNT(*)
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.document_fraud_enabled = false AND c.document_fraud_enabled = true;
