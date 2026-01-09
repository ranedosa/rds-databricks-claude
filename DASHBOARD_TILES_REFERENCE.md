# Dashboard Tiles Reference
## RDS to Salesforce Sync Monitor

All queries for creating the monitoring dashboard in Databricks SQL.

**Dashboard Name:** RDS to Salesforce Sync Monitor
**Description:** Real-time monitoring for RDS property sync to Salesforce. Daily sync cadence (every 24 hours).

---

## Tile 1: System Status
**Visualization Type:** Counter
**Purpose:** High-level system health indicator

```sql
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
```

**Configuration:**
- Counter Label: "System Health"
- Counter Value Column: status

---

## Tile 2: Coverage Percentage
**Visualization Type:** Counter
**Purpose:** Current sync coverage percentage

```sql
SELECT
  ROUND(coverage_percentage, 2) AS coverage_percentage,
  total_sf_properties,
  total_rds_properties,
  rds_to_sf_gap
FROM crm.sfdc_dbx.daily_health_check;
```

**Configuration:**
- Counter Label: "Coverage %"
- Counter Value Column: coverage_percentage
- Add "%" suffix

---

## Tile 3: Queue Sizes
**Visualization Type:** Bar Chart (Horizontal or Vertical)
**Purpose:** Current CREATE and UPDATE queue sizes

```sql
SELECT
  'CREATE Queue' AS queue_type,
  COUNT(*) AS queue_size,
  CASE
    WHEN COUNT(*) > 500 THEN '🔴 High'
    WHEN COUNT(*) > 300 THEN '🟡 Moderate'
    ELSE '🟢 Normal'
  END AS status
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'UPDATE Queue' AS queue_type,
  COUNT(*) AS queue_size,
  CASE
    WHEN COUNT(*) > 2000 THEN '🔴 High'
    WHEN COUNT(*) > 1000 THEN '🟡 Moderate'
    ELSE '🟢 Normal'
  END AS status
FROM crm.sfdc_dbx.properties_to_update;
```

**Configuration:**
- X-axis: queue_type
- Y-axis: queue_size
- Color by: status (optional)

---

## Tile 4: Recent Activity
**Visualization Type:** Counter or Table
**Purpose:** Number of properties created/updated today

```sql
SELECT
  'Created Today' AS activity_type,
  COUNT(*) AS record_count
FROM crm.salesforce.product_property
WHERE DATE(created_date) = CURRENT_DATE()
  AND _fivetran_deleted = false

UNION ALL

SELECT
  'Updated Today' AS activity_type,
  COUNT(*) AS record_count
FROM crm.salesforce.product_property
WHERE DATE(last_modified_date) = CURRENT_DATE()
  AND DATE(created_date) < CURRENT_DATE()
  AND _fivetran_deleted = false;
```

**Configuration:**
- If Counter: Show both counts
- If Table: activity_type and record_count columns

---

## Tile 5: Coverage Trend (Line Chart)
**Visualization Type:** Line Chart
**Purpose:** Coverage percentage over past 30 days
**⚠️ REQUIRES:** Audit log data (available after Step 5)

```sql
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
```

**Configuration:**
- X-axis: snapshot_date
- Y-axis: coverage_percentage
- Line: coverage_percentage
- Add reference line at 90% (goal)

**Note:** This tile will show no data until audit log starts populating (Step 5).

---

## Tile 6: Daily Sync Activity (Stacked Bar Chart)
**Visualization Type:** Stacked Bar Chart
**Purpose:** Properties created vs updated per day (last 30 days)
**⚠️ REQUIRES:** Audit log data (available after Step 5)

```sql
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
```

**Configuration:**
- X-axis: sync_date
- Y-axis: count
- Series 1: properties_created (green)
- Series 2: properties_updated (blue)
- Stack bars

**Note:** This tile will show no data until audit log starts populating (Step 5).

---

## Tile 7: Data Quality Metrics
**Visualization Type:** Table or Counter Grid
**Purpose:** Current data quality indicators

```sql
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
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false;
```

**Configuration:**
- Show as table with all columns
- Or: Multiple counters (one per metric)

---

## Tile 8: Feature Flag Adoption
**Visualization Type:** Horizontal Bar Chart
**Purpose:** Number of properties with each feature enabled

```sql
SELECT
  'IDV / Identity Verification' AS feature,
  SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN id_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Bank Linking' AS feature,
  SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN bank_linking_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Connected Payroll' AS feature,
  SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN connected_payroll_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Income Verification' AS feature,
  SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN income_verification_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Fraud Detection' AS feature,
  SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) AS enabled_count,
  ROUND(100.0 * SUM(CASE WHEN fraud_detection_enabled_c THEN 1 ELSE 0 END) / COUNT(*), 1) AS enabled_pct
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

ORDER BY enabled_count DESC;
```

**Configuration:**
- X-axis: enabled_count
- Y-axis: feature
- Horizontal bars
- Sort by count descending

---

## Tile 9: Feature Flag Adoption Trend (Line Chart)
**Visualization Type:** Multi-line Chart
**Purpose:** Feature flag adoption over time (last 30 days)
**⚠️ REQUIRES:** Audit log data (available after Step 5)

```sql
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
```

**Configuration:**
- X-axis: trend_date
- Y-axis: count
- Multiple lines (one per feature)
- Legend showing feature names

**Note:** This tile will show no data until audit log starts populating (Step 5).

---

## Tile 10: Queue Backlog Trend (Area Chart)
**Visualization Type:** Stacked Area Chart
**Purpose:** CREATE and UPDATE queue sizes over time
**⚠️ REQUIRES:** Audit log data (available after Step 5)

```sql
SELECT
  DATE(execution_timestamp) AS trend_date,
  CAST(REGEXP_EXTRACT(notes, 'CREATE Queue: ([0-9]+)', 1) AS INT) AS create_queue_size,
  CAST(REGEXP_EXTRACT(notes, 'UPDATE Queue: ([0-9]+)', 1) AS INT) AS update_queue_size
FROM crm.sfdc_dbx.sync_audit_log
WHERE sync_type = 'MONITORING'
  AND execution_timestamp >= CURRENT_DATE() - INTERVAL 30 DAYS
ORDER BY trend_date ASC;
```

**Configuration:**
- X-axis: trend_date
- Y-axis: queue size
- Area 1: create_queue_size
- Area 2: update_queue_size
- Stack areas
- Add reference lines: CREATE=500, UPDATE=2000

**Note:** This tile will show no data until audit log starts populating (Step 5).

---

## Tile 11: Sync Health Monitor
**Visualization Type:** Table with color-coded status
**Purpose:** Real-time sync health from monitoring view

```sql
SELECT
  sync_name,
  queue_size,
  records_today,
  status,
  queue_assessment,
  hours_since_last_sync,
  last_sync_timestamp
FROM crm.sfdc_dbx.sync_health_monitor
ORDER BY sync_name;
```

**Configuration:**
- Display as table
- All columns visible
- Color-code status column (green=✅, yellow=🟡, red=🔴)

---

## Tile 12: Top Properties by Feature Flags
**Visualization Type:** Table
**Purpose:** Properties with the most features enabled (top 20)

```sql
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
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false
ORDER BY total_features_enabled DESC, property_name ASC
LIMIT 20;
```

**Configuration:**
- Display as table
- Sort by total_features_enabled descending
- Show top 20

---

## Tile 13: Last Sync Timestamps
**Visualization Type:** Counter Grid (2 counters)
**Purpose:** When last CREATE and UPDATE syncs ran

```sql
SELECT
  'Last CREATE Sync' AS sync_type,
  MAX(created_date) AS last_sync_timestamp,
  TIMESTAMPDIFF(HOUR, MAX(created_date), CURRENT_TIMESTAMP()) AS hours_ago
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false

UNION ALL

SELECT
  'Last UPDATE Sync' AS sync_type,
  MAX(last_modified_date) AS last_sync_timestamp,
  TIMESTAMPDIFF(HOUR, MAX(last_modified_date), CURRENT_TIMESTAMP()) AS hours_ago
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false
  AND DATE(created_date) < CURRENT_DATE();
```

**Configuration:**
- Two counters side by side
- Show last_sync_timestamp and hours_ago
- Alert if hours_ago > 25 (daily sync missed)

---

## Tile 14: Properties Missing Data
**Visualization Type:** Counter with alert color
**Purpose:** Count of properties with missing/incomplete data

```sql
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
FROM crm.salesforce.product_property
WHERE _fivetran_deleted = false
  AND (company_name_c IS NULL
       OR snappt_property_id_c IS NULL
       OR name IS NULL
       OR name = '');
```

**Configuration:**
- Counter showing properties_with_issues
- Show issue_severity with color coding
- Alert if > 100 properties

---

## Dashboard Configuration

### Auto-Refresh
- Enable auto-refresh: Every 1 hour
- Or: Every 4 hours (to match alert schedule)

### Sharing
- Owner: dane@snappt.com (Can Edit)
- Team: data-engineering@snappt.com (Can View)

### Layout Recommendations
```
┌─────────────────────────────────────────────────────────────┐
│  [Tile 1: Status]  [Tile 2: Coverage]  [Tile 3: Queues]    │
│  [Tile 4: Activity]                                          │
├─────────────────────────────────────────────────────────────┤
│  [Tile 7: Data Quality]      [Tile 8: Feature Adoption]    │
├─────────────────────────────────────────────────────────────┤
│  [Tile 11: Sync Health Monitor - Wide Table]                │
├─────────────────────────────────────────────────────────────┤
│  [Tile 13: Last Sync Times]  [Tile 14: Missing Data]       │
└─────────────────────────────────────────────────────────────┘
```

**Tiles 5, 6, 9, 10:** Add after audit log is populated (Step 5)

---

## Notes

- **Tiles available now:** 1, 2, 3, 4, 7, 8, 11, 12, 13, 14 (10 tiles)
- **Tiles needing audit log data:** 5, 6, 9, 10 (4 tiles) - Add after Step 5
- **Recommended minimum:** Tiles 1, 2, 3, 4, 7, 11, 13, 14 (8 core tiles)
- **All queries tested:** Yes, against current schema
- **Performance:** All queries run in <5 seconds

---

## Adding Tiles to Dashboard

For each tile:
1. Click "Add" → "Visualization"
2. Copy/paste the SQL query
3. Click "Run" to test
4. Configure visualization type and settings
5. Name the tile
6. Click "Add to Dashboard"
7. Arrange tiles in layout
8. Save dashboard

---

**Created:** 2026-01-09
**Last Updated:** 2026-01-09
**Databricks Dashboard:** RDS to Salesforce Sync Monitor
