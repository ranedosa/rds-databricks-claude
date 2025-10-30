# Databricks notebook source
# MAGIC %md
# MAGIC # Sales-Focused IDV Results Dashboard
# MAGIC
# MAGIC **Created:** 2025-10-30
# MAGIC **Purpose:** Customer-facing dashboard for sales demos showing ID verification results
# MAGIC **Owner:** Data Engineering Team
# MAGIC **Users:** Sales Team, Customer Success
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC This notebook contains all SQL queries for the Sales-Focused IDV Results Dashboard. Each query can be used to create a visualization in a Databricks Lakeview Dashboard.
# MAGIC
# MAGIC ### Dashboard Features:
# MAGIC - ✅ Company and property filtering
# MAGIC - ✅ Customizable date ranges
# MAGIC - ✅ Executive summary metrics
# MAGIC - ✅ Performance trends over time
# MAGIC - ✅ Failure reason analysis
# MAGIC - ✅ Geographic breakdown
# MAGIC - ✅ Individual submission details
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Parameters (Set These First)
# MAGIC
# MAGIC Create these as dashboard parameters when building in Lakeview:
# MAGIC - `start_date`: DATE (default: 30 days ago)
# MAGIC - `end_date`: DATE (default: today)
# MAGIC - `company_filter`: TEXT (optional, for filtering to specific company)
# MAGIC - `property_filter`: TEXT (optional, for filtering to specific property)

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 1: Executive Summary Metrics
# MAGIC **Widget Type:** Counter Cards
# MAGIC **Purpose:** High-level KPIs for dashboard header
# MAGIC **Visualizations:** 4 separate counter widgets

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Executive Summary: Total Scans, Pass Rate, Active Properties, Active Companies
# MAGIC SELECT
# MAGIC     COUNT(*) AS total_idv_scans,
# MAGIC     COUNT(DISTINCT property_id) AS active_properties,
# MAGIC     COUNT(DISTINCT company_id) AS active_companies,
# MAGIC     SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed_scans,
# MAGIC     SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS failed_scans,
# MAGIC     SUM(CASE WHEN status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review_scans,
# MAGIC     ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate_percentage,
# MAGIC     ROUND(SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS fail_rate_percentage
# MAGIC FROM rds.pg_rds_public.id_verifications
# MAGIC WHERE results_provided_at IS NOT NULL
# MAGIC     AND inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND inserted_at <= CURRENT_DATE
# MAGIC -- Add these filters in Lakeview dashboard:
# MAGIC -- AND (:company_filter IS NULL OR company_id = :company_filter)
# MAGIC -- AND (:property_filter IS NULL OR property_id = :property_filter)

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 2: Company Overview
# MAGIC **Widget Type:** Table
# MAGIC **Purpose:** Company-level performance aggregation
# MAGIC **Use Case:** Select specific company to drill down

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Company Overview with Performance Metrics
# MAGIC SELECT
# MAGIC     c.name AS company_name,
# MAGIC     c.short_id AS company_id,
# MAGIC     COUNT(DISTINCT p.id) AS num_properties,
# MAGIC     COUNT(DISTINCT iv.id) AS total_scans,
# MAGIC     SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
# MAGIC     SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
# MAGIC     SUM(CASE WHEN iv.status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review,
# MAGIC     ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 1) AS pass_rate,
# MAGIC     MIN(iv.inserted_at) AS first_scan_date,
# MAGIC     MAX(iv.inserted_at) AS most_recent_scan_date
# MAGIC FROM rds.pg_rds_public.companies c
# MAGIC JOIN rds.pg_rds_public.properties p ON c.id = p.company_id
# MAGIC JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC     AND p.identity_verification_enabled = TRUE
# MAGIC GROUP BY c.name, c.short_id
# MAGIC ORDER BY total_scans DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 3: Property-Level Performance
# MAGIC **Widget Type:** Table (Sortable)
# MAGIC **Purpose:** Detailed property breakdown
# MAGIC **Use Case:** Identify top/bottom performers

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Property Performance with Location and Provider Details
# MAGIC SELECT
# MAGIC     p.name AS property_name,
# MAGIC     c.name AS company_name,
# MAGIC     p.state AS property_state,
# MAGIC     p.city AS property_city,
# MAGIC     p.identity_verification_provider AS idv_provider,
# MAGIC     COUNT(iv.id) AS total_scans,
# MAGIC     SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
# MAGIC     SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
# MAGIC     SUM(CASE WHEN iv.status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review,
# MAGIC     ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 1) AS pass_rate,
# MAGIC     MIN(iv.inserted_at) AS first_scan_date,
# MAGIC     MAX(iv.inserted_at) AS most_recent_scan_date,
# MAGIC     DATEDIFF(CURRENT_DATE, MAX(iv.inserted_at)) AS days_since_last_scan
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC GROUP BY p.name, c.name, p.state, p.city, p.identity_verification_provider
# MAGIC ORDER BY total_scans DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 4: Daily Volume Trends
# MAGIC **Widget Type:** Stacked Bar Chart
# MAGIC **Purpose:** Show daily pass/fail trends
# MAGIC **Use Case:** Identify anomaly days or patterns

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Daily IDV Volume by Status (Stacked Bar Chart)
# MAGIC SELECT
# MAGIC     DATE(iv.inserted_at) AS scan_date,
# MAGIC     iv.status,
# MAGIC     COUNT(*) AS scan_count
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC GROUP BY DATE(iv.inserted_at), iv.status
# MAGIC ORDER BY scan_date ASC, iv.status

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 5: Status Distribution
# MAGIC **Widget Type:** Pie Chart
# MAGIC **Purpose:** Overall pass/fail/review breakdown
# MAGIC **Use Case:** Quick health check visualization

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Pass/Fail/Review Distribution (Pie Chart)
# MAGIC SELECT
# MAGIC     iv.status,
# MAGIC     COUNT(*) AS count,
# MAGIC     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC GROUP BY iv.status
# MAGIC ORDER BY count DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 6: Top Failure Reasons
# MAGIC **Widget Type:** Horizontal Bar Chart
# MAGIC **Purpose:** Identify most common failure causes
# MAGIC **Use Case:** Drive process improvements

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Top 10 Failure Reasons (Bar Chart)
# MAGIC SELECT
# MAGIC     iv.score_reason AS failure_reason,
# MAGIC     COUNT(*) AS failure_count,
# MAGIC     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage_of_failures
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.status = 'FAIL'
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC GROUP BY iv.score_reason
# MAGIC ORDER BY failure_count DESC
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 7: Recent Submissions Detail
# MAGIC **Widget Type:** Table (Detailed)
# MAGIC **Purpose:** Audit trail of recent activity
# MAGIC **Use Case:** Investigate specific submissions

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Recent 100 IDV Submissions with Full Details
# MAGIC SELECT
# MAGIC     iv.inserted_at AS scan_date,
# MAGIC     c.name AS company_name,
# MAGIC     p.name AS property_name,
# MAGIC     p.state AS property_state,
# MAGIC     iv.status,
# MAGIC     iv.score_reason,
# MAGIC     iv.provider AS idv_provider,
# MAGIC     CASE
# MAGIC         WHEN iv.provider = 'clear' THEN
# MAGIC             CASE
# MAGIC                 WHEN get_json_object(iv.provider_session_info, '$.flowType') = 'full' THEN 'Enhanced'
# MAGIC                 WHEN get_json_object(iv.provider_session_info, '$.flowType') = 'lite' THEN 'Basic'
# MAGIC                 ELSE 'N/A'
# MAGIC             END
# MAGIC         ELSE 'N/A'
# MAGIC     END AS verification_level,
# MAGIC     DATEDIFF(CURRENT_DATE, DATE(iv.inserted_at)) AS days_ago
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC ORDER BY iv.inserted_at DESC
# MAGIC LIMIT 100

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 8: Weekly Performance Summary
# MAGIC **Widget Type:** Line Chart
# MAGIC **Purpose:** Week-over-week pass rate trends
# MAGIC **Use Case:** Quarterly business reviews

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Weekly Performance Trends (Line Chart)
# MAGIC SELECT
# MAGIC     DATE_TRUNC('week', iv.inserted_at) AS week_start,
# MAGIC     COUNT(*) AS total_scans,
# MAGIC     SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
# MAGIC     SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
# MAGIC     ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 90 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC GROUP BY DATE_TRUNC('week', iv.inserted_at)
# MAGIC ORDER BY week_start ASC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 9: Provider Performance Comparison
# MAGIC **Widget Type:** Grouped Bar Chart
# MAGIC **Purpose:** Compare CLEAR vs Incode performance
# MAGIC **Use Case:** Justify provider selection

# COMMAND ----------

# MAGIC %sql
# MAGIC -- CLEAR vs Incode Performance Comparison
# MAGIC SELECT
# MAGIC     CASE
# MAGIC         WHEN iv.provider = 'clear' THEN 'CLEAR'
# MAGIC         WHEN iv.provider = 'incode' THEN 'Incode'
# MAGIC         ELSE 'Other'
# MAGIC     END AS idv_provider,
# MAGIC     COUNT(*) AS total_scans,
# MAGIC     SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
# MAGIC     SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
# MAGIC     ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate
# MAGIC FROM rds.pg_rds_public.id_verifications iv
# MAGIC JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC     AND iv.provider IN ('clear', 'incode')
# MAGIC GROUP BY CASE
# MAGIC         WHEN iv.provider = 'clear' THEN 'CLEAR'
# MAGIC         WHEN iv.provider = 'incode' THEN 'Incode'
# MAGIC         ELSE 'Other'
# MAGIC     END
# MAGIC ORDER BY total_scans DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 10: Geographic Performance
# MAGIC **Widget Type:** Table (Color-Coded)
# MAGIC **Purpose:** Performance breakdown by state
# MAGIC **Use Case:** Regional analysis

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Performance by State (Geographic Distribution)
# MAGIC SELECT
# MAGIC     p.state AS property_state,
# MAGIC     COUNT(DISTINCT p.id) AS num_properties,
# MAGIC     COUNT(iv.id) AS total_scans,
# MAGIC     SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
# MAGIC     SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
# MAGIC     ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 2) AS pass_rate
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE iv.results_provided_at IS NOT NULL
# MAGIC     AND iv.inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC     AND iv.inserted_at <= CURRENT_DATE
# MAGIC     AND p.state IS NOT NULL
# MAGIC GROUP BY p.state
# MAGIC ORDER BY total_scans DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 11: Company Filter List
# MAGIC **Widget Type:** Dropdown Filter
# MAGIC **Purpose:** Populate company filter
# MAGIC **Use Case:** Enable company-specific filtering

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Company List for Filter Dropdown
# MAGIC SELECT DISTINCT
# MAGIC     c.id AS company_id,
# MAGIC     c.name AS company_name
# MAGIC FROM rds.pg_rds_public.companies c
# MAGIC JOIN rds.pg_rds_public.properties p ON c.id = p.company_id
# MAGIC WHERE p.identity_verification_enabled = TRUE
# MAGIC ORDER BY c.name ASC

# COMMAND ----------

# MAGIC %md
# MAGIC ## QUERY 12: Property Filter List
# MAGIC **Widget Type:** Dropdown Filter (Cascading)
# MAGIC **Purpose:** Populate property filter based on company selection
# MAGIC **Use Case:** Enable property-specific filtering

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Property List for Filter Dropdown (Cascading from Company)
# MAGIC SELECT DISTINCT
# MAGIC     p.id AS property_id,
# MAGIC     p.name AS property_name,
# MAGIC     c.name AS company_name
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE p.identity_verification_enabled = TRUE
# MAGIC ORDER BY c.name ASC, p.name ASC

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## How to Build the Lakeview Dashboard
# MAGIC
# MAGIC ### Step 1: Create New Lakeview Dashboard
# MAGIC 1. Go to Databricks Workspace
# MAGIC 2. Click **Workspace** → **Create** → **Dashboard**
# MAGIC 3. Name it: **"Sales - IDV Results Dashboard"**
# MAGIC
# MAGIC ### Step 2: Add Parameters
# MAGIC Click **Add Parameter** for each:
# MAGIC - `start_date`: Type = DATE, Default = 30 days ago
# MAGIC - `end_date`: Type = DATE, Default = today
# MAGIC - `company_filter`: Type = TEXT, Optional = true
# MAGIC - `property_filter`: Type = TEXT, Optional = true
# MAGIC
# MAGIC ### Step 3: Create Datasets
# MAGIC For each query above (1-12):
# MAGIC 1. Click **Add** → **Dataset**
# MAGIC 2. Copy the SQL query from this notebook
# MAGIC 3. Replace hardcoded dates with parameter references:
# MAGIC    - Change `CURRENT_DATE - INTERVAL 30 DAYS` to `:start_date`
# MAGIC    - Change `CURRENT_DATE` to `:end_date`
# MAGIC 4. Add filter conditions:
# MAGIC    ```sql
# MAGIC    AND (:company_filter IS NULL OR c.id = :company_filter)
# MAGIC    AND (:property_filter IS NULL OR p.id = :property_filter)
# MAGIC    ```
# MAGIC 5. Name the dataset (e.g., "Executive Summary", "Daily Trends")
# MAGIC
# MAGIC ### Step 4: Create Visualizations
# MAGIC Follow the widget type specifications from the Build Guide:
# MAGIC - **Counter widgets** for metrics (Query 1)
# MAGIC - **Stacked bar chart** for daily trends (Query 4)
# MAGIC - **Pie chart** for status distribution (Query 5)
# MAGIC - **Bar chart** for failure reasons (Query 6)
# MAGIC - **Tables** for company/property details (Queries 2, 3, 7)
# MAGIC - **Line chart** for weekly trends (Query 8)
# MAGIC
# MAGIC ### Step 5: Configure Filters
# MAGIC 1. Add filter widgets using Queries 11 and 12
# MAGIC 2. Set up cascading: Property filter depends on Company filter
# MAGIC 3. Link all visualizations to these filters
# MAGIC
# MAGIC ### Step 6: Arrange Layout
# MAGIC - Place filters at the top
# MAGIC - Executive summary counters in a row
# MAGIC - Trend charts in the middle
# MAGIC - Detailed tables at the bottom
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Testing the Dashboard
# MAGIC
# MAGIC 1. **Test without filters:** Should show all data
# MAGIC 2. **Test company filter:** Select one company, verify all data filters
# MAGIC 3. **Test property filter:** Select one property, verify drill-down
# MAGIC 4. **Test date range:** Change dates, verify data updates
# MAGIC 5. **Test edge cases:** Empty results, single property, etc.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Documentation
# MAGIC
# MAGIC Full documentation is available in:
# MAGIC - **Build Guide:** `/Users/danerosa/rds_databricks_claude/docs/dashboards/sales_idv_results_dashboard_guide.md`
# MAGIC - **Widget Explanation:** `/Users/danerosa/rds_databricks_claude/docs/dashboards/sales_idv_results_dashboard_widget_explanation.md`
# MAGIC
# MAGIC For questions or support, contact the Data Engineering Team.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation Queries
# MAGIC
# MAGIC Run these to verify data availability before building dashboard:

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check: Do we have recent IDV data?
# MAGIC SELECT
# MAGIC     COUNT(*) AS recent_scans,
# MAGIC     COUNT(DISTINCT company_id) AS companies,
# MAGIC     COUNT(DISTINCT property_id) AS properties,
# MAGIC     MIN(inserted_at) AS oldest_scan,
# MAGIC     MAX(inserted_at) AS newest_scan
# MAGIC FROM rds.pg_rds_public.id_verifications
# MAGIC WHERE results_provided_at IS NOT NULL
# MAGIC     AND inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check: Status distribution (should have PASS, FAIL, maybe NEEDS REVIEW)
# MAGIC SELECT
# MAGIC     status,
# MAGIC     COUNT(*) AS count
# MAGIC FROM rds.pg_rds_public.id_verifications
# MAGIC WHERE results_provided_at IS NOT NULL
# MAGIC     AND inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC GROUP BY status

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check: Provider distribution (should have clear, incode, maybe others)
# MAGIC SELECT
# MAGIC     provider,
# MAGIC     COUNT(*) AS count
# MAGIC FROM rds.pg_rds_public.id_verifications
# MAGIC WHERE results_provided_at IS NOT NULL
# MAGIC     AND inserted_at >= CURRENT_DATE - INTERVAL 30 DAYS
# MAGIC GROUP BY provider
