-- Check if Park Kennedy is in the properties_to_update view
SELECT
  'Park Kennedy Check' AS check_name,
  COUNT(*) AS found_count,
  MAX(sfdc_id) AS sfdc_id,
  MAX(property_name) AS property_name,
  MAX(total_feature_count) AS total_feature_count,
  MAX(is_multi_property) AS is_multi_property
FROM crm.sfdc_dbx.properties_to_update
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- If found_count = 0, Park Kennedy might not be in Salesforce yet
-- If found_count = 1, it should be in UPDATE queue

-- Check if Park Kennedy is in CREATE queue instead
SELECT
  'Park Kennedy in CREATE?' AS check_name,
  COUNT(*) AS found_count,
  MAX(sfdc_id) AS sfdc_id,
  MAX(property_name) AS property_name
FROM crm.sfdc_dbx.properties_to_create
WHERE sfdc_id = 'a01Dn00000HHUanIAH';
