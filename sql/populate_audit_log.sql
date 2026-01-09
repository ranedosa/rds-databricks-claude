-- ============================================================================
-- Populate Sync Audit Log - Daily Snapshot
-- ============================================================================
-- Purpose: Capture daily metrics for historical tracking and trend analysis
-- Schedule: Run daily at 11:59 PM (via Databricks Job or cron)
-- Target: crm.sfdc_dbx.sync_audit_log
--
-- This query inserts a daily snapshot of system health metrics including:
-- - Total properties in Salesforce
-- - Data quality metrics (NULL counts)
-- - Coverage percentage
-- - Queue sizes
-- - Sync activity
--
-- Usage:
--   1. Copy this entire query
--   2. Create Databricks SQL Job:
--      - Schedule: Daily at 11:59 PM PT (Cron: 59 23 * * *)
--      - Timeout: 5 minutes
--      - Retry: 3 times
--   3. Or run manually: Execute this query in Databricks SQL Editor
--
-- Monitoring:
--   - Query history: SELECT * FROM crm.sfdc_dbx.sync_audit_log WHERE sync_type = 'MONITORING' ORDER BY execution_timestamp DESC;
--   - Coverage trends: See queries at bottom of this file
-- ============================================================================

INSERT INTO crm.sfdc_dbx.sync_audit_log (
  audit_id,
  sync_name,
  sync_type,
  execution_timestamp,
  records_processed,
  records_succeeded,
  records_failed,
  error_rate,
  executed_by,
  notes
)
WITH daily_metrics AS (
  -- Calculate all metrics in one pass
  SELECT
    COUNT(*) AS total_sf_properties,
    SUM(CASE WHEN company_name_c IS NOT NULL THEN 1 ELSE 0 END) AS properties_with_company,
    SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) AS properties_without_company,
    SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) AS idv_enabled_count,
    SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) AS bank_linking_enabled_count,
    SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) AS payroll_enabled_count,
    SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) AS income_enabled_count,
    SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS fraud_enabled_count,
    MAX(created_date) AS last_create_timestamp,
    MAX(last_modified_date) AS last_update_timestamp,
    COUNT(CASE WHEN DATE(created_date) = CURRENT_DATE() THEN 1 END) AS created_today,
    COUNT(CASE WHEN DATE(last_modified_date) = CURRENT_DATE() THEN 1 END) AS updated_today
  FROM hive_metastore.salesforce.product_property
  WHERE _fivetran_deleted = false
),

queue_metrics AS (
  -- Get current queue sizes
  SELECT
    COUNT(*) AS create_queue_size
  FROM crm.sfdc_dbx.properties_to_create
),

update_queue_metrics AS (
  SELECT
    COUNT(*) AS update_queue_size
  FROM crm.sfdc_dbx.properties_to_update
),

health_metrics AS (
  -- Get coverage from health check view
  SELECT
    coverage_percentage,
    total_rds_properties,
    total_sf_properties,
    rds_to_sf_gap,
    coverage_status
  FROM crm.sfdc_dbx.daily_health_check
)

SELECT
  -- Unique audit ID based on date
  CONCAT('daily_snapshot_', DATE_FORMAT(CURRENT_TIMESTAMP(), 'yyyyMMdd')) AS audit_id,

  -- Sync metadata
  'Daily System Snapshot' AS sync_name,
  'MONITORING' AS sync_type,
  CURRENT_TIMESTAMP() AS execution_timestamp,

  -- Metrics
  dm.total_sf_properties AS records_processed,
  dm.properties_with_company AS records_succeeded,
  dm.properties_without_company AS records_failed,
  ROUND(100.0 * dm.properties_without_company / NULLIF(dm.total_sf_properties, 0), 2) AS error_rate,

  -- Execution metadata
  'automated_daily_snapshot' AS executed_by,

  -- Detailed notes (JSON-like format for easy parsing)
  CONCAT(
    'Coverage: ', CAST(hm.coverage_percentage AS STRING), '% | ',
    'Status: ', hm.coverage_status, ' | ',
    'RDS Total: ', CAST(hm.total_rds_properties AS STRING), ' | ',
    'SF Total: ', CAST(hm.total_sf_properties AS STRING), ' | ',
    'Gap: ', CAST(hm.rds_to_sf_gap AS STRING), ' | ',
    'CREATE Queue: ', CAST(qm.create_queue_size AS STRING), ' | ',
    'UPDATE Queue: ', CAST(uqm.update_queue_size AS STRING), ' | ',
    'Created Today: ', CAST(dm.created_today AS STRING), ' | ',
    'Updated Today: ', CAST(dm.updated_today AS STRING), ' | ',
    'IDV Enabled: ', CAST(dm.idv_enabled_count AS STRING), ' | ',
    'Bank Linking: ', CAST(dm.bank_linking_enabled_count AS STRING), ' | ',
    'Payroll: ', CAST(dm.payroll_enabled_count AS STRING), ' | ',
    'Income: ', CAST(dm.income_enabled_count AS STRING), ' | ',
    'Fraud Detection: ', CAST(dm.fraud_enabled_count AS STRING), ' | ',
    'Last Create: ', CAST(dm.last_create_timestamp AS STRING), ' | ',
    'Last Update: ', CAST(dm.last_update_timestamp AS STRING)
  ) AS notes

FROM daily_metrics dm
CROSS JOIN queue_metrics qm
CROSS JOIN update_queue_metrics uqm
CROSS JOIN health_metrics hm;


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check if today's snapshot was recorded
-- SELECT * FROM crm.sfdc_dbx.sync_audit_log
-- WHERE audit_id = CONCAT('daily_snapshot_', DATE_FORMAT(CURRENT_DATE(), 'yyyyMMdd'));

-- View recent snapshots (last 7 days)
-- SELECT
--   execution_timestamp,
--   records_processed AS total_properties,
--   records_succeeded AS with_company_name,
--   records_failed AS without_company_name,
--   error_rate AS null_pct,
--   notes
-- FROM crm.sfdc_dbx.sync_audit_log
-- WHERE sync_type = 'MONITORING'
-- ORDER BY execution_timestamp DESC
-- LIMIT 7;


-- ============================================================================
-- Trend Analysis Queries
-- ============================================================================

-- Coverage trend over past 30 days
-- WITH coverage_history AS (
--   SELECT
--     DATE(execution_timestamp) AS snapshot_date,
--     CAST(REGEXP_EXTRACT(notes, 'Coverage: ([0-9.]+)%', 1) AS DOUBLE) AS coverage_pct,
--     CAST(REGEXP_EXTRACT(notes, 'SF Total: ([0-9]+)', 1) AS INT) AS sf_total,
--     CAST(REGEXP_EXTRACT(notes, 'Gap: ([0-9]+)', 1) AS INT) AS gap
--   FROM crm.sfdc_dbx.sync_audit_log
--   WHERE sync_type = 'MONITORING'
--     AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
-- )
-- SELECT
--   snapshot_date,
--   coverage_pct,
--   sf_total,
--   gap,
--   LAG(coverage_pct) OVER (ORDER BY snapshot_date) AS prev_day_coverage,
--   coverage_pct - LAG(coverage_pct) OVER (ORDER BY snapshot_date) AS coverage_change
-- FROM coverage_history
-- ORDER BY snapshot_date DESC;


-- Daily sync activity trend (creations + updates per day)
-- SELECT
--   DATE(execution_timestamp) AS snapshot_date,
--   CAST(REGEXP_EXTRACT(notes, 'Created Today: ([0-9]+)', 1) AS INT) AS created,
--   CAST(REGEXP_EXTRACT(notes, 'Updated Today: ([0-9]+)', 1) AS INT) AS updated,
--   CAST(REGEXP_EXTRACT(notes, 'Created Today: ([0-9]+)', 1) AS INT) +
--     CAST(REGEXP_EXTRACT(notes, 'Updated Today: ([0-9]+)', 1) AS INT) AS total_synced
-- FROM crm.sfdc_dbx.sync_audit_log
-- WHERE sync_type = 'MONITORING'
--   AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
-- ORDER BY snapshot_date DESC;


-- Feature flag adoption trend
-- SELECT
--   DATE(execution_timestamp) AS snapshot_date,
--   CAST(REGEXP_EXTRACT(notes, 'IDV Enabled: ([0-9]+)', 1) AS INT) AS idv_count,
--   CAST(REGEXP_EXTRACT(notes, 'Bank Linking: ([0-9]+)', 1) AS INT) AS bank_linking_count,
--   CAST(REGEXP_EXTRACT(notes, 'Payroll: ([0-9]+)', 1) AS INT) AS payroll_count,
--   CAST(REGEXP_EXTRACT(notes, 'Income: ([0-9]+)', 1) AS INT) AS income_count,
--   CAST(REGEXP_EXTRACT(notes, 'Fraud Detection: ([0-9]+)', 1) AS INT) AS fraud_count
-- FROM crm.sfdc_dbx.sync_audit_log
-- WHERE sync_type = 'MONITORING'
--   AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
-- ORDER BY snapshot_date DESC;


-- Queue size trend (helps identify backlog patterns)
-- SELECT
--   DATE(execution_timestamp) AS snapshot_date,
--   CAST(REGEXP_EXTRACT(notes, 'CREATE Queue: ([0-9]+)', 1) AS INT) AS create_queue,
--   CAST(REGEXP_EXTRACT(notes, 'UPDATE Queue: ([0-9]+)', 1) AS INT) AS update_queue,
--   CAST(REGEXP_EXTRACT(notes, 'SF Total: ([0-9]+)', 1) AS INT) AS total_properties
-- FROM crm.sfdc_dbx.sync_audit_log
-- WHERE sync_type = 'MONITORING'
--   AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
-- ORDER BY snapshot_date DESC;


-- ============================================================================
-- Scheduling Instructions
-- ============================================================================
--
-- Option A: Databricks SQL Job (Recommended)
-- ------------------------------------------
-- 1. Go to Databricks SQL: https://dbc-9ca0f5e0-2208.cloud.databricks.com/sql
-- 2. Navigate to: SQL → Jobs → Create Job
-- 3. Configure:
--    - Name: "Daily Sync Audit Log Population"
--    - Query: Copy this entire file
--    - Schedule: Cron expression: 59 23 * * *
--    - Timezone: America/Los_Angeles (PT)
--    - SQL Warehouse: /sql/1.0/warehouses/95a8f5979c3f8740
--    - Timeout: 5 minutes
--    - Max retries: 3
-- 4. Test: Run job manually first
-- 5. Enable schedule
--
-- Option B: Add to daily_validation.py
-- -------------------------------------
-- Import this query into scripts/daily_validation.py
-- Run as part of daily validation routine at 11:59 PM
--
-- Option C: Manual Execution
-- --------------------------
-- Run this query manually in Databricks SQL Editor at end of each day
-- Good for initial testing, not sustainable long-term
--
-- ============================================================================
