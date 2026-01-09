-- Query 1: Overall Impact
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
