# Databricks notebook source
# MAGIC %md
# MAGIC # RDS to Salesforce Sync - Dashboard Tiles
# MAGIC
# MAGIC **Purpose:** All queries for creating dashboard visualizations
# MAGIC
# MAGIC **Instructions:**
# MAGIC 1. Import this notebook into Databricks
# MAGIC 2. For each cell with SQL, copy the query
# MAGIC 3. Go to your dashboard: https://dbc-9ca0f5e0-2208.cloud.databricks.com/sql/dashboardsv3/01f0ed94192917438bfcd41de3134c5d
# MAGIC 4. Click "Add" → "Visualization"
# MAGIC 5. Paste the SQL query
# MAGIC 6. Configure visualization as noted in comments
# MAGIC 7. Add to dashboard
# MAGIC
# MAGIC **Dashboard Settings:**
# MAGIC - Auto-refresh: Every 1 hour
# MAGIC - Share with: data-engineering@snappt.com

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 1: System Status
# MAGIC
# MAGIC **Visualization Type:** Counter
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Counter Label: "System Health"
# MAGIC - Counter Value Column: `status`
# MAGIC - Color coding: Green for ✅/🟢, Yellow for 🟡, Red for 🔴
# MAGIC
# MAGIC **Purpose:** High-level system health indicator showing if coverage is good

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   'System Health' AS metric,
# MAGIC   CASE
# MAGIC     WHEN coverage_percentage >= 95 THEN '✅ Excellent'
# MAGIC     WHEN coverage_percentage >= 90 THEN '🟢 Good'
# MAGIC     WHEN coverage_percentage >= 85 THEN '🟡 OK'
# MAGIC     ELSE '🔴 Attention Needed'
# MAGIC   END AS status,
# MAGIC   coverage_percentage AS coverage_pct,
# MAGIC   rds_to_sf_gap AS gap
# MAGIC FROM crm.sfdc_dbx.daily_health_check;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 2: Coverage Percentage
# MAGIC
# MAGIC **Visualization Type:** Counter
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Counter Label: "Coverage %"
# MAGIC - Counter Value Column: `coverage_percentage`
# MAGIC - Format: Add "%" suffix
# MAGIC - Target threshold: 90% (show as reference line if possible)
# MAGIC
# MAGIC **Purpose:** Shows current sync coverage percentage (target >90%)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   ROUND(coverage_percentage, 2) AS coverage_percentage,
# MAGIC   total_sf_properties,
# MAGIC   total_rds_properties,
# MAGIC   rds_to_sf_gap
# MAGIC FROM crm.sfdc_dbx.daily_health_check;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 3: Queue Sizes
# MAGIC
# MAGIC **Visualization Type:** Bar Chart (Horizontal or Vertical)
# MAGIC
# MAGIC **Configuration:**
# MAGIC - X-axis: `queue_type`
# MAGIC - Y-axis: `queue_size`
# MAGIC - Color by: `status` (optional)
# MAGIC - Colors: Green (🟢 Normal), Yellow (🟡 Moderate), Red (🔴 High)
# MAGIC
# MAGIC **Purpose:** Shows current CREATE and UPDATE queue sizes with status indicators
# MAGIC
# MAGIC **Thresholds (Daily Sync):**
# MAGIC - CREATE: Normal <300, Moderate 300-500, High >500
# MAGIC - UPDATE: Normal <1000, Moderate 1000-2000, High >2000

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   'CREATE Queue' AS queue_type,
# MAGIC   COUNT(*) AS queue_size,
# MAGIC   CASE
# MAGIC     WHEN COUNT(*) > 500 THEN '🔴 High'
# MAGIC     WHEN COUNT(*) > 300 THEN '🟡 Moderate'
# MAGIC     ELSE '🟢 Normal'
# MAGIC   END AS status
# MAGIC FROM crm.sfdc_dbx.properties_to_create
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'UPDATE Queue' AS queue_type,
# MAGIC   COUNT(*) AS queue_size,
# MAGIC   CASE
# MAGIC     WHEN COUNT(*) > 2000 THEN '🔴 High'
# MAGIC     WHEN COUNT(*) > 1000 THEN '🟡 Moderate'
# MAGIC     ELSE '🟢 Normal'
# MAGIC   END AS status
# MAGIC FROM crm.sfdc_dbx.properties_to_update;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 4: Recent Activity
# MAGIC
# MAGIC **Visualization Type:** Table or Counter Grid
# MAGIC
# MAGIC **Configuration:**
# MAGIC - If Counter Grid: Show two counters side-by-side
# MAGIC - If Table: Show both rows with activity_type and record_count
# MAGIC
# MAGIC **Purpose:** Number of properties created/updated today
# MAGIC
# MAGIC **Note:** With daily syncs, you may see 0 most of the day, then spike after sync runs

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   'Created Today' AS activity_type,
# MAGIC   COUNT(*) AS record_count
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE DATE(created_date) = CURRENT_DATE()
# MAGIC   AND _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Updated Today' AS activity_type,
# MAGIC   COUNT(*) AS record_count
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE DATE(last_modified_date) = CURRENT_DATE()
# MAGIC   AND DATE(created_date) < CURRENT_DATE()
# MAGIC   AND _fivetran_deleted = false;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 7: Data Quality Metrics
# MAGIC
# MAGIC **Visualization Type:** Table or Counter Grid
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Show all metrics as table
# MAGIC - Highlight `quality_status` column with colors
# MAGIC - Alert if quality_status = '🔴 Poor'
# MAGIC
# MAGIC **Purpose:** Current data quality indicators
# MAGIC
# MAGIC **Target:** data_quality_pct >95%, null_company_names <50

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   COUNT(*) AS total_properties,
# MAGIC   SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) AS null_company_names,
# MAGIC   SUM(CASE WHEN id_verification_enabled_c IS NULL THEN 1 ELSE 0 END) AS null_idv,
# MAGIC   SUM(CASE WHEN bank_linking_enabled_c IS NULL THEN 1 ELSE 0 END) AS null_bank_linking,
# MAGIC   ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) AS data_quality_pct,
# MAGIC   CASE
# MAGIC     WHEN ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) >= 95 THEN '✅ Excellent'
# MAGIC     WHEN ROUND(100.0 * (COUNT(*) - SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END)) / COUNT(*), 2) >= 90 THEN '🟢 Good'
# MAGIC     ELSE '🔴 Poor'
# MAGIC   END AS quality_status
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 8: Feature Flag Adoption
# MAGIC
# MAGIC **Visualization Type:** Horizontal Bar Chart
# MAGIC
# MAGIC **Configuration:**
# MAGIC - X-axis: `enabled_count`
# MAGIC - Y-axis: `feature`
# MAGIC - Sort: By enabled_count descending
# MAGIC - Show both count and percentage
# MAGIC
# MAGIC **Purpose:** Number and percentage of properties with each feature enabled
# MAGIC
# MAGIC **Features tracked:**
# MAGIC - IDV / Identity Verification
# MAGIC - Bank Linking
# MAGIC - Connected Payroll
# MAGIC - Income Verification
# MAGIC - Fraud Detection

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   'IDV / Identity Verification' AS feature,
# MAGIC   SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Bank Linking' AS feature,
# MAGIC   SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Connected Payroll' AS feature,
# MAGIC   SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Income Verification' AS feature,
# MAGIC   SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Fraud Detection' AS feature,
# MAGIC   SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC ORDER BY enabled_count DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 11: Sync Health Monitor
# MAGIC
# MAGIC **Visualization Type:** Table with color-coded status
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Display as table
# MAGIC - Show all columns
# MAGIC - Color-code `status` column: Green (✅), Yellow (🟡), Red (🔴)
# MAGIC - Sort by `sync_name`
# MAGIC
# MAGIC **Purpose:** Real-time sync health from monitoring view
# MAGIC
# MAGIC **Columns:**
# MAGIC - sync_name: Which sync (CREATE or UPDATE)
# MAGIC - queue_size: Current backlog
# MAGIC - records_today: Activity today
# MAGIC - status: Health indicator
# MAGIC - queue_assessment: Interpretation
# MAGIC - hours_since_last_sync: Time since last sync
# MAGIC - last_sync_timestamp: Exact timestamp

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   sync_name,
# MAGIC   queue_size,
# MAGIC   records_today,
# MAGIC   status,
# MAGIC   queue_assessment,
# MAGIC   hours_since_last_sync,
# MAGIC   last_sync_timestamp
# MAGIC FROM crm.sfdc_dbx.sync_health_monitor
# MAGIC ORDER BY sync_name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 12: Top Properties by Feature Flags
# MAGIC
# MAGIC **Visualization Type:** Table
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Display as table
# MAGIC - Sort by `total_features_enabled` descending
# MAGIC - Show top 20 rows
# MAGIC - Color-code boolean columns (TRUE=green, FALSE=gray)
# MAGIC
# MAGIC **Purpose:** Properties with the most features enabled
# MAGIC
# MAGIC **Use case:** Identify power users or most engaged properties

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   snappt_property_id_c AS property_id,
# MAGIC   name AS property_name,
# MAGIC   company_name_c AS company_name,
# MAGIC   (CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END +
# MAGIC    CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END +
# MAGIC    CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END +
# MAGIC    CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END +
# MAGIC    CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS total_features_enabled,
# MAGIC   id_verification_enabled_c AS idv,
# MAGIC   bank_linking_enabled_c AS bank_linking,
# MAGIC   connected_payroll_enabled_c AS payroll,
# MAGIC   income_verification_enabled_c AS income,
# MAGIC   fraud_detection_enabled_c AS fraud
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC ORDER BY total_features_enabled DESC, property_name ASC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 13: Last Sync Timestamps
# MAGIC
# MAGIC **Visualization Type:** Counter Grid (2 counters side-by-side)
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Show two counters: "Last CREATE Sync" and "Last UPDATE Sync"
# MAGIC - Display both `last_sync_timestamp` and `hours_ago`
# MAGIC - Alert if `hours_ago` > 25 (daily sync missed)
# MAGIC - Format: Show full timestamp
# MAGIC
# MAGIC **Purpose:** When last CREATE and UPDATE syncs ran
# MAGIC
# MAGIC **Alert threshold:** >25 hours = missed daily sync

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   'Last CREATE Sync' AS sync_type,
# MAGIC   MAX(created_date) AS last_sync_timestamp,
# MAGIC   TIMESTAMPDIFF(HOUR, MAX(created_date), CURRENT_TIMESTAMP()) AS hours_ago
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC   'Last UPDATE Sync' AS sync_type,
# MAGIC   MAX(last_modified_date) AS last_sync_timestamp,
# MAGIC   TIMESTAMPDIFF(HOUR, MAX(last_modified_date), CURRENT_TIMESTAMP()) AS hours_ago
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC   AND DATE(created_date) < CURRENT_DATE();

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tile 14: Properties Missing Data
# MAGIC
# MAGIC **Visualization Type:** Counter with alert color
# MAGIC
# MAGIC **Configuration:**
# MAGIC - Primary counter: `properties_with_issues`
# MAGIC - Show breakdown: missing_company_name, missing_property_id, missing_name
# MAGIC - Color by `issue_severity`: Green (🟢 Low), Yellow (🟡 Moderate), Red (🔴 High)
# MAGIC - Alert if > 100 properties
# MAGIC
# MAGIC **Purpose:** Count of properties with missing/incomplete data
# MAGIC
# MAGIC **Quality check:** Should stay <50 under normal conditions

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   COUNT(*) AS properties_with_issues,
# MAGIC   SUM(CASE WHEN company_name_c IS NULL THEN 1 ELSE 0 END) AS missing_company_name,
# MAGIC   SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) AS missing_property_id,
# MAGIC   SUM(CASE WHEN name IS NULL OR name = '' THEN 1 ELSE 0 END) AS missing_name,
# MAGIC   CASE
# MAGIC     WHEN COUNT(*) > 100 THEN '🔴 High'
# MAGIC     WHEN COUNT(*) > 50 THEN '🟡 Moderate'
# MAGIC     ELSE '🟢 Low'
# MAGIC   END AS issue_severity
# MAGIC FROM crm.salesforce.product_property
# MAGIC WHERE _fivetran_deleted = false
# MAGIC   AND (company_name_c IS NULL
# MAGIC        OR snappt_property_id_c IS NULL
# MAGIC        OR name IS NULL
# MAGIC        OR name = '');

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tiles Requiring Audit Log Data (Add After Step 5)
# MAGIC
# MAGIC The following tiles require historical data from the audit log.
# MAGIC Add these AFTER Step 5 (Schedule audit log population) has been running for a few days.
# MAGIC
# MAGIC **Tiles to add later:**
# MAGIC - Tile 5: Coverage Trend (Line Chart - 30 days)
# MAGIC - Tile 6: Daily Sync Activity (Stacked Bar Chart - 30 days)
# MAGIC - Tile 9: Feature Flag Adoption Trend (Multi-line Chart - 30 days)
# MAGIC - Tile 10: Queue Backlog Trend (Stacked Area Chart - 30 days)
# MAGIC
# MAGIC These queries are available in `DASHBOARD_TILES_REFERENCE.md`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dashboard Summary
# MAGIC
# MAGIC **Tiles Added:** 10 core tiles (1, 2, 3, 4, 7, 8, 11, 12, 13, 14)
# MAGIC
# MAGIC **Tiles Pending:** 4 trend tiles (5, 6, 9, 10) - require audit log data
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. Copy each SQL query above into dashboard visualizations
# MAGIC 2. Configure visualization types as noted
# MAGIC 3. Arrange tiles in logical layout
# MAGIC 4. Set auto-refresh to 1 hour
# MAGIC 5. Share with team
# MAGIC 6. After Step 5 complete (audit log), add remaining 4 tiles
# MAGIC
# MAGIC **Dashboard URL:**
# MAGIC https://dbc-9ca0f5e0-2208.cloud.databricks.com/sql/dashboardsv3/01f0ed94192917438bfcd41de3134c5d
# MAGIC
# MAGIC **Created:** 2026-01-09
