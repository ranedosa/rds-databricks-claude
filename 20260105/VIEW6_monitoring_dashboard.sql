-- ============================================================================
-- VIEW: daily_health_check
-- PURPOSE: Single query to check sync health every day
-- USAGE: Run this every morning to verify everything is working
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.daily_health_check AS

WITH queue_stats AS (
  SELECT
    COUNT(*) AS create_queue_count,
    SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS create_queue_with_features,
    SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS create_queue_multi_property
  FROM crm.sfdc_dbx.properties_to_create
),

update_stats AS (
  SELECT
    COUNT(*) AS update_queue_count,
    SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS update_queue_with_features,
    SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS update_queue_multi_property
  FROM crm.sfdc_dbx.properties_to_update
),

rds_stats AS (
  SELECT
    COUNT(*) AS total_rds_properties,
    SUM(is_active) AS active_rds_properties,
    SUM(has_valid_sfdc_id) AS rds_with_sfdc_id
  FROM crm.sfdc_dbx.rds_properties_enriched
),

sf_stats AS (
  SELECT
    COUNT(*) AS total_sf_properties
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
),

aggregation_stats AS (
  SELECT
    COUNT(*) AS total_aggregated_sfdc_ids,
    SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_count,
    MAX(active_property_count) AS max_properties_per_sfdc_id
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
),

recent_audit AS (
  SELECT
    MAX(execution_timestamp) AS last_sync_time,
    SUM(CASE WHEN DATE(execution_timestamp) = CURRENT_DATE() THEN records_succeeded ELSE 0 END) AS records_synced_today
  FROM crm.sfdc_dbx.sync_audit_log
  WHERE sync_type IN ('CREATE', 'UPDATE')
)

SELECT
  -- Timestamp
  CURRENT_TIMESTAMP() AS report_timestamp,
  CURRENT_DATE() AS report_date,

  -- RDS Stats
  rds.total_rds_properties,
  rds.active_rds_properties,
  rds.rds_with_sfdc_id,

  -- Salesforce Stats
  sf.total_sf_properties,

  -- Coverage (what % of RDS properties are in SF?)
  ROUND(sf.total_sf_properties * 100.0 / NULLIF(rds.rds_with_sfdc_id, 0), 2) AS coverage_percentage,

  -- Aggregation Stats
  agg.total_aggregated_sfdc_ids,
  agg.multi_property_count,
  agg.max_properties_per_sfdc_id,

  -- Queue Stats (work remaining)
  q_create.create_queue_count,
  q_create.create_queue_with_features,
  q_create.create_queue_multi_property,
  q_update.update_queue_count,
  q_update.update_queue_with_features,
  q_update.update_queue_multi_property,

  -- Recent Sync Activity
  audit.last_sync_time,
  audit.records_synced_today,

  -- Health Indicators
  CASE
    WHEN q_create.create_queue_count > 200 THEN '⚠️ High CREATE backlog'
    WHEN q_create.create_queue_count > 50 THEN '⚡ Moderate CREATE queue'
    WHEN q_create.create_queue_count > 0 THEN '✅ Small CREATE queue'
    ELSE '✅ No creates needed'
  END AS create_queue_status,

  CASE
    WHEN ROUND(sf.total_sf_properties * 100.0 / NULLIF(rds.rds_with_sfdc_id, 0), 2) < 90 THEN '🔴 Coverage LOW (<90%)'
    WHEN ROUND(sf.total_sf_properties * 100.0 / NULLIF(rds.rds_with_sfdc_id, 0), 2) < 95 THEN '🟡 Coverage OK (90-95%)'
    ELSE '🟢 Coverage GOOD (>95%)'
  END AS coverage_status

FROM queue_stats q_create
CROSS JOIN update_stats q_update
CROSS JOIN rds_stats rds
CROSS JOIN sf_stats sf
CROSS JOIN aggregation_stats agg
CROSS JOIN recent_audit audit;

-- Add documentation
COMMENT ON VIEW crm.sfdc_dbx.daily_health_check IS
'Daily health check dashboard - run this every morning to verify sync health.
Shows queue sizes, coverage %, multi-property stats, and recent sync activity.';
