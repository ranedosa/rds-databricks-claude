-- Find Park Kennedy's rank in CREATE queue
WITH ranked AS (
  SELECT
    rds_property_id,
    sfdc_id,
    property_name,
    total_feature_count,
    ROW_NUMBER() OVER (ORDER BY total_feature_count DESC, created_at DESC) AS rank
  FROM crm.sfdc_dbx.properties_to_create
  WHERE property_name IS NOT NULL AND city IS NOT NULL
)
SELECT
  rank,
  rds_property_id,
  sfdc_id,
  property_name,
  total_feature_count
FROM ranked
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- If rank > 50, Park Kennedy wasn't in top 50
-- You can manually add it to pilot_create_properties.csv if desired
