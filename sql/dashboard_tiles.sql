-- ============================================================================
-- Databricks SQL Dashboard Tiles
-- RDS to Salesforce Sync Monitoring Dashboard
-- ============================================================================
-- Purpose: Queries for visual monitoring dashboard in Databricks SQL
-- Usage: Create a new dashboard and add each query as a separate tile
--
-- Dashboard Setup:
-- 1. Go to: Databricks SQL → Dashboards → Create Dashboard
-- 2. Name: "RDS to Salesforce Sync Monitor"
-- 3. Add each query below as a visualization tile
-- 4. Configure auto-refresh: Every 1 hour
-- 5. Share with: data-engineering@snappt.com
--
-- Recommended Dashboard Layout:
-- ┌─────────────────────────────────────────────────────────────┐
-- │  [System Status]  [Coverage %]  [Queue Sizes]  [Activity]   │
-- ├─────────────────────────────────────────────────────────────┤
-- │  [Coverage Trend Chart - 30 days]                           │
-- ├─────────────────────────────────────────────────────────────┤
-- │  [Daily Sync Activity Chart]   [Data Quality Metrics]       │
-- ├─────────────────────────────────────────────────────────────┤
-- │  [Feature Flag Adoption]       [Queue Trend Chart]          │
-- └─────────────────────────────────────────────────────────────┘
-- ============================================================================


-- ============================================================================
-- TILE 1: System Status (Counter Visualization)
-- ============================================================================
-- Description: High-level system health indicator
-- Visualization: Counter with color coding
-- Color rules:
--   - Green: "Excellent" or "Good"
--   - Yellow: "OK"
--   - Red: "Attention Needed"
-- ============================================================================

SELECT
  'System Health' AS metric,
  CASE
    WHEN coverage_percentage >= 95 THEN '✅ Excellent'
    WHEN coverage_percentage >= 90 THEN '🟢 Good'
    WHEN coverage_percentage >= 85 THEN '🟡 OK'
    ELSE '🔴 Attention Needed'
  END AS status,
  coverage_percentage AS coverage_pct,
  rds_to_sf_gap AS gap
FROM crm.sfdc_dbx.daily_health_check;


-- ============================================================================
-- TILE 2: Coverage Percentage (Counter Visualization)
-- ============================================================================
-- Description: Current sync coverage percentage
-- Visualization: Counter with % suffix
-- Target: >90% (ideally >95%)
-- ============================================================================

SELECT
  ROUND(coverage_percentage, 2) AS coverage_percentage,
  total_sf_properties,
  total_rds_properties,
  rds_to_sf_gap
FROM crm.sfdc_dbx.daily_health_check;


-- ============================================================================
-- TILE 3: Queue Sizes (Bar Chart)
-- ============================================================================
-- Description: Current CREATE and UPDATE queue sizes
-- Visualization: Horizontal or Vertical Bar Chart
-- Alert if: CREATE >100 OR UPDATE >1000
-- ============================================================================

SELECT
  'CREATE Queue' AS queue_type,
  COUNT(*) AS queue_size,
  CASE
    WHEN COUNT(*) > 100 THEN '🔴 High'
    WHEN COUNT(*) > 50 THEN '🟡 Moderate'
    ELSE '🟢 Normal'
  END AS status
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'UPDATE Queue' AS queue_type,
  COUNT(*) AS queue_size,
  CASE
    WHEN COUNT(*) > 1000 THEN '🔴 High'
    WHEN COUNT(*) > 500 THEN '🟡 Moderate'
    ELSE '🟢 Normal'
  END AS status
FROM crm.sfdc_dbx.properties_to_update;


-- ============================================================================
-- TILE 4: Recent Sync Activity (Counter)
-- ============================================================================
-- Description: Number of properties created/updated today
-- Visualization: Counter
-- Expected: Should see activity if syncs are running
-- ============================================================================

SELECT
  'Created Today' AS activity_type,
  COUNT(*) AS record_count
FROM hive_metastore.salesforce.product_property
WHERE DATE(created_date) = CURRENT_DATE()
  AND _fivetran_deleted = false

UNION ALL

SELECT
  'Updated Today' AS activity_type,
  COUNT(*) AS record_count
FROM hive_metastore.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND DATE(created_date) < CURRENT_DATE()
  AND _fivetran_deleted = false;


-- ============================================================================
-- TILE 5: Coverage Trend (Line Chart)
-- ============================================================================
-- Description: Coverage percentage over past 30 days
-- Visualization: Line Chart
-- X-axis: Date
-- Y-axis: Coverage %
-- Goal line: 90% (add as reference line)
-- ============================================================================

WITH coverage_history AS (
  SELECT
    DATE(execution_timestamp) AS snapshot_date,
    CAST(REGEXP_EXTRACT(notes, 'Coverage: ([0-9.]+)%', 1) AS DOUBLE) AS coverage_pct,
    CAST(REGEXP_EXTRACT(notes, 'SF Total: ([0-9]+)', 1) AS INT) AS sf_total,
    CAST(REGEXP_EXTRACT(notes, 'RDS Total: ([0-9]+)', 1) AS INT) AS rds_total
  FROM crm.sfdc_dbx.sync_audit_log
  WHERE sync_type = 'MONITORING'
    AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
)
SELECT
  snapshot_date,
  coverage_pct AS coverage_percentage,
  sf_total,
  rds_total
FROM coverage_history
ORDER BY snapshot_date ASC;


-- ============================================================================
-- TILE 6: Daily Sync Activity (Stacked Bar Chart)
-- ============================================================================
-- Description: Properties created vs updated per day (last 30 days)
-- Visualization: Stacked Bar Chart
-- X-axis: Date
-- Y-axis: Count
-- Series: Created (green), Updated (blue)
-- ============================================================================

SELECT
  DATE(execution_timestamp) AS sync_date,
  CAST(REGEXP_EXTRACT(notes, 'Created Today: ([0-9]+)', 1) AS INT) AS properties_created,
  CAST(REGEXP_EXTRACT(notes, 'Updated Today: ([0-9]+)', 1) AS INT) AS properties_updated,
  CAST(REGEXP_EXTRACT(notes, 'Created Today: ([0-9]+)', 1) AS INT) +
    CAST(REGEXP_EXTRACT(notes, 'Updated Today: ([0-9]+)', 1) AS INT) AS total_synced
FROM crm.sfdc_dbx.sync_audit_log
WHERE sync_type = 'MONITORING'
  AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY sync_date ASC;


-- ============================================================================
-- TILE 7: Data Quality Metrics (Table)
-- ============================================================================
-- Description: Current data quality indicators
-- Visualization: Table or Counter Grid
-- Metrics: Total properties, NULL counts, quality %
-- ============================================================================

SELECT
  COUNT(*) AS total_properties,
  SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) AS null_company_names,
  SUM(CASE WHEN id_verification_enabled_c IS NULL THEN 1 ELSE 0 END) AS null_idv,
  SUM(CASE WHEN bank_linking_enabled_c IS NULL THEN 1 ELSE 0 END) AS null_bank_linking,
  ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) AS data_quality_pct,
  CASE
    WHEN ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) >= 95 THEN '✅ Excellent'
    WHEN ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) >= 90 THEN '🟢 Good'
    ELSE '🔴 Poor'
  END AS quality_status
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false;


-- ============================================================================
-- TILE 8: Feature Flag Adoption (Bar Chart)
-- ============================================================================
-- Description: Number of properties with each feature enabled
-- Visualization: Horizontal Bar Chart
-- Sorted by: Count descending
-- ============================================================================

SELECT
  'IDV / Identity Verification' AS feature,
  SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Bank Linking' AS feature,
  SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Connected Payroll' AS feature,
  SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Income Verification' AS feature,
  SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Fraud Detection' AS feature,
  SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

ORDER BY enabled_count DESC;


-- ============================================================================
-- TILE 9: Feature Flag Adoption Trend (Line Chart)
-- ============================================================================
-- Description: Feature flag adoption over time (last 30 days)
-- Visualization: Multi-line Chart
-- X-axis: Date
-- Y-axis: Count
-- Series: One line per feature
-- ============================================================================

SELECT
  DATE(execution_timestamp) AS trend_date,
  CAST(REGEXP_EXTRACT(notes, 'IDV Enabled: ([0-9]+)', 1) AS INT) AS idv_count,
  CAST(REGEXP_EXTRACT(notes, 'Bank Linking: ([0-9]+)', 1) AS INT) AS bank_linking_count,
  CAST(REGEXP_EXTRACT(notes, 'Payroll: ([0-9]+)', 1) AS INT) AS payroll_count,
  CAST(REGEXP_EXTRACT(notes, 'Income: ([0-9]+)', 1) AS INT) AS income_count,
  CAST(REGEXP_EXTRACT(notes, 'Fraud Detection: ([0-9]+)', 1) AS INT) AS fraud_count
FROM crm.sfdc_dbx.sync_audit_log
WHERE sync_type = 'MONITORING'
  AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY trend_date ASC;


-- ============================================================================
-- TILE 10: Queue Backlog Trend (Area Chart)
-- ============================================================================
-- Description: CREATE and UPDATE queue sizes over time
-- Visualization: Area Chart (stacked)
-- X-axis: Date
-- Y-axis: Queue Size
-- Series: CREATE Queue, UPDATE Queue
-- Alert line: CREATE=100, UPDATE=1000
-- ============================================================================

SELECT
  DATE(execution_timestamp) AS trend_date,
  CAST(REGEXP_EXTRACT(notes, 'CREATE Queue: ([0-9]+)', 1) AS INT) AS create_queue_size,
  CAST(REGEXP_EXTRACT(notes, 'UPDATE Queue: ([0-9]+)', 1) AS INT) AS update_queue_size
FROM crm.sfdc_dbx.sync_audit_log
WHERE sync_type = 'MONITORING'
  AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY trend_date ASC;


-- ============================================================================
-- TILE 11: Sync Health Monitor (Table with Status)
-- ============================================================================
-- Description: Real-time sync health from monitoring view
-- Visualization: Table with color-coded status column
-- Refresh: Every 1 hour
-- ============================================================================

SELECT
  sync_name,
  queue_size,
  records_today,
  status,
  queue_assessment,
  last_sync_timestamp
FROM crm.sfdc_dbx.sync_health_monitor
ORDER BY sync_name;


-- ============================================================================
-- TILE 12: Top Properties by Feature Flags (Table)
-- ============================================================================
-- Description: Properties with the most features enabled
-- Visualization: Table
-- Limit: Top 20
-- ============================================================================

SELECT
  snappt_property_id_c AS property_id,
  name AS property_name,
  company_name_c AS company_name,
  (CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END +
   CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END +
   CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END +
   CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END +
   CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS total_features_enabled,
  id_verification_enabled_c AS idv,
  bank_linking_enabled_c AS bank_linking,
  connected_payroll_enabled_c AS payroll,
  income_verification_enabled_c AS income,
  fraud_detection_enabled_c AS fraud
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false
ORDER BY total_features_enabled DESC, property_name ASC
LIMIT 20;


-- ============================================================================
-- TILE 13: Last Sync Timestamps (Counter Grid)
-- ============================================================================
-- Description: When last CREATE and UPDATE syncs ran
-- Visualization: Counter Grid (2 columns)
-- Alert if: >2 hours ago
-- ============================================================================

SELECT
  'Last CREATE Sync' AS sync_type,
  MAX(created_date) AS last_sync_timestamp,
  TIMESTAMPDIFF(HOUR, MAX(created_date), CURRENT_TIMESTAMP()) AS hours_ago
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Last UPDATE Sync' AS sync_type,
  MAX(last_modified_date) AS last_sync_timestamp,
  TIMESTAMPDIFF(HOUR, MAX(last_modified_date), CURRENT_TIMESTAMP()) AS hours_ago
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false
  AND DATE(created_date) < CURRENT_DATE();


-- ============================================================================
-- TILE 14: Properties Missing Data (Counter)
-- ============================================================================
-- Description: Count of properties with missing/incomplete data
-- Visualization: Counter with alert color
-- Alert if: >100 properties
-- ============================================================================

SELECT
  COUNT(*) AS properties_with_issues,
  SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) AS missing_company_name,
  SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) AS missing_property_id,
  SUM(CASE WHEN name IS NULL OR name = '' THEN 1 ELSE 0 END) AS missing_name,
  CASE
    WHEN COUNT(*) > 100 THEN '🔴 High'
    WHEN COUNT(*) > 50 THEN '🟡 Moderate'
    ELSE '🟢 Low'
  END AS issue_severity
FROM hive_metastore.salesforce.product_property
WHERE _fivetran_deleted = false
  AND (company_name_c IS NULL
       OR snappt_property_id_c IS NULL
       OR name IS NULL
       OR name = '');


-- ============================================================================
-- Dashboard Configuration Instructions
-- ============================================================================
--
-- 1. Create New Dashboard:
--    - Go to Databricks SQL → Dashboards
--    - Click "Create Dashboard"
--    - Name: "RDS to Salesforce Sync Monitor"
--    - Description: "Real-time monitoring for RDS property sync to Salesforce"
--
-- 2. Add Tiles:
--    - For each query above, click "Add" → "Visualization"
--    - Copy/paste the query
--    - Choose appropriate visualization type (noted in each section)
--    - Set refresh schedule: Auto-refresh every 1 hour
--    - Arrange tiles in logical layout (see top of file)
--
-- 3. Configure Alerts (optional):
--    - Tile 1 (System Status): Alert if status contains "🔴"
--    - Tile 3 (Queue Sizes): Alert if status = "🔴 High"
--    - Tile 7 (Data Quality): Alert if quality_status = "🔴 Poor"
--    - Tile 11 (Sync Health): Alert if any status contains "🔴"
--
-- 4. Share Dashboard:
--    - Click "Share" button
--    - Add: dane@snappt.com, data-engineering@snappt.com
--    - Permission: "Can Edit" for dane, "Can View" for team
--
-- 5. Set as Default (optional):
--    - If you want this dashboard to be your default view
--    - User Settings → Default Dashboard
--
-- ============================================================================
