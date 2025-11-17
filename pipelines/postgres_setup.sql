-- ============================================================================
-- PostgreSQL Configuration for Lakeflow Connect
-- AWS RDS PostgreSQL Setup Script
-- ============================================================================
--
-- Purpose: Configure PostgreSQL for logical replication and create user
--          with appropriate permissions for Lakeflow Connect CDC
--
-- Prerequisites:
-- 1. Parameter group has rds.logical_replication = 1
-- 2. RDS instance has been rebooted after parameter change
-- 3. You are connected as a superuser (e.g., postgres or master user)
--
-- ============================================================================

-- Step 1: Verify Logical Replication is Enabled
-- ============================================================================
SHOW wal_level;
-- Expected output: logical
-- If not 'logical', check parameter group and reboot RDS instance

-- Step 2: Create Dedicated Lakeflow User
-- ============================================================================
-- Replace <secure-password> with a strong password
-- Store this password in Databricks secret scope

CREATE ROLE lakeflow_user WITH LOGIN PASSWORD '<secure-password>';

-- Add comment for documentation
COMMENT ON ROLE lakeflow_user IS 'Databricks Lakeflow Connect replication user';

-- Step 3: Grant Replication Privileges
-- ============================================================================
-- This allows the user to create replication slots and stream WAL
GRANT rds_replication TO lakeflow_user;

-- Step 4: Grant Schema-Level Permissions
-- ============================================================================
-- Grant access to the public schema
GRANT USAGE ON SCHEMA public TO lakeflow_user;

-- Grant connect privilege on the database
-- Replace <database_name> with your actual database name
GRANT CONNECT ON DATABASE <database_name> TO lakeflow_user;

-- Step 5: Grant Table-Level SELECT Permissions
-- ============================================================================
-- Grant SELECT on all existing tables in public schema
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lakeflow_user;

-- Grant SELECT on all future tables (recommended)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO lakeflow_user;

-- Step 6: Grant Sequence Permissions (if tables have sequences)
-- ============================================================================
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO lakeflow_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON SEQUENCES TO lakeflow_user;

-- Step 7: Verify User Permissions
-- ============================================================================
-- Check role attributes
SELECT
    rolname,
    rolsuper,
    rolinherit,
    rolcreaterole,
    rolcreatedb,
    rolcanlogin,
    rolreplication
FROM pg_roles
WHERE rolname = 'lakeflow_user';

-- Check granted privileges
SELECT
    grantee,
    table_schema,
    privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'lakeflow_user'
    AND table_schema = 'public'
LIMIT 10;

-- Step 8: Test Replication Slot Creation (Validation)
-- ============================================================================
-- Test that the user can create replication slots
-- NOTE: Lakeflow Connect will create its own slot, this is just for testing

-- Switch to lakeflow_user (using psql)
-- \c <database_name> lakeflow_user

-- Create a test replication slot
SELECT pg_create_logical_replication_slot('lakeflow_test_slot', 'pgoutput');

-- Verify the slot was created
SELECT
    slot_name,
    plugin,
    slot_type,
    active,
    confirmed_flush_lsn
FROM pg_replication_slots
WHERE slot_name = 'lakeflow_test_slot';

-- Clean up test slot
SELECT pg_drop_replication_slot('lakeflow_test_slot');

-- Step 9: List Tables That Will Be Synced
-- ============================================================================
-- Top 20 tables in public schema (based on usage analysis)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_live_tup as estimated_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'entries',
        'folders',
        'applicants',
        'income_verification_reviews',
        'proof',
        'properties',
        'companies',
        'applicant_submission_document_sources',
        'income_verification_submissions',
        'applicant_submissions',
        'id_verifications',
        'users',
        'property_features',
        'income_verification_results',
        'rent_verifications',
        'api_keys',
        'unauthenticated_session',
        'rent_verification_events',
        'fraud_submissions',
        'fraud_reviews'
    )
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Step 10: Check Primary Keys (Required for CDC)
-- ============================================================================
-- Lakeflow Connect requires primary keys for CDC
-- Verify all target tables have primary keys
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_schema = 'public'
    AND tc.table_name IN (
        'entries', 'folders', 'applicants', 'income_verification_reviews',
        'proof', 'properties', 'companies', 'applicant_submission_document_sources',
        'income_verification_submissions', 'applicant_submissions',
        'id_verifications', 'users', 'property_features',
        'income_verification_results', 'rent_verifications',
        'api_keys', 'unauthenticated_session', 'rent_verification_events',
        'fraud_submissions', 'fraud_reviews'
    )
ORDER BY tc.table_name;

-- Step 11: Check for Tables Without Primary Keys
-- ============================================================================
-- These tables will need primary keys added before CDC can work
SELECT t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints tc
    ON t.table_name = tc.table_name
    AND t.table_schema = tc.table_schema
    AND tc.constraint_type = 'PRIMARY KEY'
WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
    AND t.table_name IN (
        'entries', 'folders', 'applicants', 'income_verification_reviews',
        'proof', 'properties', 'companies', 'applicant_submission_document_sources',
        'income_verification_submissions', 'applicant_submissions',
        'id_verifications', 'users', 'property_features',
        'income_verification_results', 'rent_verifications',
        'api_keys', 'unauthenticated_session', 'rent_verification_events',
        'fraud_submissions', 'fraud_reviews'
    )
    AND tc.constraint_name IS NULL;

-- Step 12: Monitor Replication Slots (Post-Setup)
-- ============================================================================
-- After Lakeflow Connect starts, monitor replication slots
-- Run this periodically to check for slot health

SELECT
    slot_name,
    plugin,
    slot_type,
    database,
    active,
    active_pid,
    restart_lsn,
    confirmed_flush_lsn,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) as replication_lag
FROM pg_replication_slots
ORDER BY slot_name;

-- Step 13: Monitor WAL Generation (Capacity Planning)
-- ============================================================================
-- Check WAL generation rate to understand replication volume
SELECT
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')) as total_wal_generated,
    pg_current_wal_lsn() as current_wal_lsn;

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
--
-- Next Steps:
-- 1. Store password in Databricks secret scope: lakeflow-rds/postgres-password
-- 2. Create connection in Databricks Catalog -> External Data -> Connections
-- 3. Test connection
-- 4. Create Delta Live Tables pipeline
-- 5. Start initial sync
--
-- Connection Details for Databricks:
-- - Host: <your-rds-endpoint>.rds.amazonaws.com
-- - Port: 5432
-- - Database: <your-database-name>
-- - Schema: public
-- - Username: lakeflow_user
-- - Password: {{secrets/lakeflow-rds/postgres-password}}
--
-- ============================================================================
