-- Quick Table Usage Analysis
-- Run this in Databricks SQL Editor for immediate results
-- Analyzes last 90 days of query history

WITH query_tables AS (
  SELECT
    statement_text,
    executed_by,
    start_time,
    statement_type,
    -- Extract table names using regex
    REGEXP_EXTRACT_ALL(
      UPPER(statement_text),
      'FROM\\s+[`"]?(\\w+\\.?\\w*\\.?\\w+)[`"]?|JOIN\\s+[`"]?(\\w+\\.?\\w*\\.?\\w+)[`"]?|INTO\\s+[`"]?(\\w+\\.?\\w*\\.?\\w+)[`"]?'
    ) as table_matches
  FROM system.query.history
  WHERE start_time >= CURRENT_DATE() - INTERVAL 90 DAYS
    AND execution_status = 'FINISHED'
    AND statement_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE_TABLE_AS_SELECT')
),

exploded_tables AS (
  SELECT
    LOWER(TRIM(table_ref)) as table_name,
    executed_by,
    start_time,
    statement_type
  FROM query_tables
  LATERAL VIEW EXPLODE(table_matches) t AS table_ref
  WHERE table_ref IS NOT NULL
    AND TRIM(table_ref) != ''
    AND TRIM(table_ref) NOT IN ('SELECT', 'WHERE', 'GROUP', 'ORDER', 'HAVING')
),

table_metrics AS (
  SELECT
    table_name,
    COUNT(*) as total_queries,
    COUNT(DISTINCT executed_by) as unique_users,
    MIN(start_time) as first_access,
    MAX(start_time) as last_access,
    COUNT(CASE WHEN statement_type = 'SELECT' THEN 1 END) as read_queries,
    COUNT(CASE WHEN statement_type IN ('INSERT', 'UPDATE', 'DELETE', 'MERGE') THEN 1 END) as write_queries,
    ROUND(COUNT(*) / 90.0, 2) as avg_queries_per_day,
    DATEDIFF(CURRENT_DATE(), MAX(start_time)) as days_since_last_access
  FROM exploded_tables
  GROUP BY table_name
)

SELECT
  table_name,
  total_queries,
  unique_users,
  read_queries,
  write_queries,
  avg_queries_per_day,
  days_since_last_access,
  first_access,
  last_access,
  CASE
    WHEN table_name LIKE '%fivetran%' OR
         table_name LIKE '%source%' OR
         table_name LIKE '%raw%' OR
         table_name LIKE '%stg_%' OR
         table_name LIKE '%src_%' THEN 'Likely Fivetran/Source'
    ELSE 'Other'
  END as table_category
FROM table_metrics
WHERE total_queries > 5  -- Filter out very rarely used tables
ORDER BY total_queries DESC
LIMIT 50;
