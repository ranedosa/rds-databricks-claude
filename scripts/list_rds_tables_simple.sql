-- Simple query to list all tables in RDS catalog
-- This is faster than analyzing query history
-- Run in Databricks SQL Editor

SELECT
    table_schema as schema_name,
    table_name,
    CONCAT('rds.', table_schema, '.', table_name) as full_table_name,
    table_type,
    created as created_at
FROM system.information_schema.tables
WHERE table_catalog = 'rds'
    AND table_type IN ('MANAGED', 'EXTERNAL')
ORDER BY table_schema, table_name;
