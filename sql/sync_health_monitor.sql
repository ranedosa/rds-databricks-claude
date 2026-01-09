-- ============================================================================
-- Sync Health Monitor View
-- ============================================================================
-- Purpose: Real-time monitoring of Census sync health
-- Usage: Query this view to check if syncs are running properly
-- Alert: Set up Databricks SQL Alert when status contains '🔴'
--
-- Example usage:
--   SELECT * FROM crm.sfdc_dbx.sync_health_monitor;
--
-- Expected output when healthy:
--   sync_name      | queue_size | last_sync_today       | status
--   ---------------|------------|----------------------|-------------------
--   Census Sync A  | 45         | 2026-01-09 10:30:15  | ✅ Healthy
--   Census Sync B  | 120        | 2026-01-09 10:25:42  | ✅ Healthy
--
-- Alert conditions:
--   🔴 High backlog  - CREATE queue >100 OR UPDATE queue >1000
--   🔴 No syncs today - No records created/updated today
--   🟡 Moderate backlog - CREATE queue 50-100 OR UPDATE queue 500-1000
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_health_monitor AS

WITH queue_stats AS (
  -- Get current queue sizes
  SELECT
    'Census Sync A (CREATE)' AS sync_name,
    COUNT(*) AS queue_size,
    'create' AS queue_type
  FROM crm.sfdc_dbx.properties_to_create

  UNION ALL

  SELECT
    'Census Sync B (UPDATE)' AS sync_name,
    COUNT(*) AS queue_size,
    'update' AS queue_type
  FROM crm.sfdc_dbx.properties_to_update
),

sync_activity AS (
  -- Check recent sync activity in Salesforce
  SELECT
    'Census Sync A (CREATE)' AS sync_name,
    MAX(created_date) AS last_sync_timestamp,
    COUNT(*) AS records_today
  FROM hive_metastore.salesforce.product_property
  WHERE DATE(created_date) = CURRENT_DATE()
    AND _fivetran_deleted = false

  UNION ALL

  SELECT
    'Census Sync B (UPDATE)' AS sync_name,
    MAX(last_modified_date) AS last_sync_timestamp,
    COUNT(*) AS records_today
  FROM hive_metastore.salesforce.product_property
  WHERE DATE(last_modified_date) = CURRENT_DATE()
    AND DATE(created_date) < CURRENT_DATE()  -- Only updates, not creates
    AND _fivetran_deleted = false
)

SELECT
  q.sync_name,
  q.queue_size,
  s.last_sync_timestamp,
  s.records_today,

  -- Determine health status
  CASE
    -- Critical conditions (Red)
    WHEN q.queue_type = 'create' AND q.queue_size > 100 THEN '🔴 High CREATE backlog'
    WHEN q.queue_type = 'update' AND q.queue_size > 1000 THEN '🔴 High UPDATE backlog'
    WHEN s.last_sync_timestamp IS NULL AND HOUR(CURRENT_TIMESTAMP()) > 8 THEN '🔴 No syncs today (after 8am)'
    WHEN s.records_today = 0 AND HOUR(CURRENT_TIMESTAMP()) > 8 THEN '🔴 No records synced today'

    -- Warning conditions (Yellow)
    WHEN q.queue_type = 'create' AND q.queue_size BETWEEN 50 AND 100 THEN '🟡 Moderate CREATE backlog'
    WHEN q.queue_type = 'update' AND q.queue_size BETWEEN 500 AND 1000 THEN '🟡 Moderate UPDATE backlog'
    WHEN HOUR(CURRENT_TIMESTAMP()) - HOUR(s.last_sync_timestamp) > 2 THEN '🟡 No sync in 2+ hours'

    -- Healthy (Green)
    ELSE '✅ Healthy'
  END AS status,

  -- Additional context
  CASE
    WHEN q.queue_size = 0 THEN 'Queue empty - all synced'
    WHEN q.queue_size < 50 THEN 'Queue draining normally'
    WHEN q.queue_size BETWEEN 50 AND 100 THEN 'Moderate queue - monitor'
    WHEN q.queue_size BETWEEN 100 AND 500 THEN 'High queue - may need attention'
    ELSE 'Very high queue - investigate'
  END AS queue_assessment,

  CURRENT_TIMESTAMP() AS check_timestamp

FROM queue_stats q
LEFT JOIN sync_activity s ON q.sync_name = s.sync_name
ORDER BY q.sync_name;


-- ============================================================================
-- Example Databricks SQL Alert Configuration
-- ============================================================================
-- Alert Name: Census Sync Health Alert
-- Query: SELECT * FROM crm.sfdc_dbx.sync_health_monitor WHERE status LIKE '🔴%'
-- Schedule: Every 2 hours (or Every 1 hour)
-- Alert condition: Row count > 0
-- Recipients: dane@snappt.com, data-engineering@snappt.com
-- Message template:
--   Alert: Census sync health issue detected!
--
--   {{#results}}
--   Sync: {{sync_name}}
--   Status: {{status}}
--   Queue Size: {{queue_size}}
--   Last Sync: {{last_sync_timestamp}}
--   Assessment: {{queue_assessment}}
--   {{/results}}
--
--   Please check: https://app.getcensus.com/syncs
-- ============================================================================


-- ============================================================================
-- Usage Examples
-- ============================================================================

-- Check current health status
-- SELECT * FROM crm.sfdc_dbx.sync_health_monitor;

-- Check for any issues (use in alerts)
-- SELECT * FROM crm.sfdc_dbx.sync_health_monitor WHERE status NOT LIKE '✅%';

-- Get just the critical alerts
-- SELECT * FROM crm.sfdc_dbx.sync_health_monitor WHERE status LIKE '🔴%';

-- Monitor queue trends over time (requires periodic snapshots)
-- SELECT
--   check_timestamp,
--   sync_name,
--   queue_size,
--   status
-- FROM crm.sfdc_dbx.sync_health_monitor
-- ORDER BY check_timestamp DESC
-- LIMIT 100;
