-- Check ALL properties with Park Kennedy's sfdc_id (including non-active)
SELECT
  rds_property_id,
  property_name,
  property_status,
  sfdc_id,
  idv_enabled,
  bank_linking_enabled,
  is_active,
  has_valid_sfdc_id
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE sfdc_id = 'a01Dn00000HHUanIAH'
ORDER BY property_status, updated_at DESC;

-- This will show if there are DISABLED/DELETED properties with same sfdc_id
