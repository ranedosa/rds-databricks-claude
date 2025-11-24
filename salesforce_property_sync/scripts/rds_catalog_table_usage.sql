-- Top 50 Most Used Tables in RDS Catalog
-- Run this in Databricks SQL Editor
-- Analyzes last 90 days of query history

WITH parsed_queries AS (
  SELECT
    statement_text,
    executed_by,
    start_time,
    statement_type,
    execution_status
  FROM system.query.history
  WHERE start_time >= CURRENT_DATE() - INTERVAL 90 DAYS
    AND execution_status = 'FINISHED'
    AND statement_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE_TABLE_AS_SELECT')
    -- Filter for queries that reference the rds catalog
    AND LOWER(statement_text) LIKE '%rds.%'
),

-- Extract table references using string functions
table_references AS (
  SELECT
    executed_by,
    start_time,
    statement_type,
    -- Extract all potential table references with rds catalog
    EXPLODE(
      SPLIT(
        REGEXP_REPLACE(
          LOWER(statement_text),
          '(from|join|into|update|table)\\s+`?rds\\.([a-z0-9_]+)\\.([a-z0-9_]+)`?',
          '|||rds.$2.$3|||'
        ),
        '\\|\\|\\|'
      )
    ) as extracted_text
  FROM parsed_queries
),

clean_tables AS (
  SELECT
    TRIM(extracted_text) as table_name,
    executed_by,
    start_time,
    statement_type
  FROM table_references
  WHERE extracted_text LIKE 'rds.%'
    AND LENGTH(TRIM(extracted_text)) > 4
),

table_stats AS (
  SELECT
    table_name,
    COUNT(*) as total_queries,
    COUNT(DISTINCT executed_by) as unique_users,
    MIN(start_time) as first_access,
    MAX(start_time) as last_access,
    SUM(CASE WHEN statement_type = 'SELECT' THEN 1 ELSE 0 END) as read_queries,
    SUM(CASE WHEN statement_type IN ('INSERT', 'UPDATE', 'DELETE', 'MERGE') THEN 1 ELSE 0 END) as write_queries
  FROM clean_tables
  GROUP BY table_name
)

SELECT
  table_name,
  total_queries,
  unique_users,
  read_queries,
  write_queries,
  ROUND(total_queries / 90.0, 2) as avg_queries_per_day,
  DATEDIFF(CURRENT_DATE(), last_access) as days_since_last_access,
  first_access,
  last_access,
  ROUND(read_queries * 100.0 / NULLIF(total_queries, 0), 1) as read_percentage
FROM table_stats
WHERE total_queries >= 3  -- Filter out very rarely used tables
ORDER BY total_queries DESC
LIMIT 50;
