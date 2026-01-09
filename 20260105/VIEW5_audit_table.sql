-- ============================================================================
-- TABLE: sync_audit_log
-- PURPOSE: Track all sync executions for debugging and monitoring
-- ============================================================================

CREATE TABLE IF NOT EXISTS crm.sfdc_dbx.sync_audit_log (
  audit_id STRING COMMENT 'Unique identifier for this audit record',
  sync_name STRING COMMENT 'Name of the sync (Sync A or Sync B)',
  sync_type STRING COMMENT 'CREATE or UPDATE',
  execution_timestamp TIMESTAMP COMMENT 'When the sync was executed',

  -- Counts
  records_processed INT COMMENT 'Total records sent to Census',
  records_succeeded INT COMMENT 'Successfully synced',
  records_failed INT COMMENT 'Failed to sync',
  error_rate DOUBLE COMMENT 'Percentage of records that failed',

  -- Metadata
  executed_by STRING COMMENT 'Who triggered the sync',
  notes STRING COMMENT 'Any notes about this sync execution',
  census_sync_id STRING COMMENT 'Census sync run ID for reference',

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When this record was created'
)
COMMENT 'Audit log for all Census sync executions';

-- Create initial record to verify table works
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
VALUES (
  'initial_setup',
  'System Setup',
  'SETUP',
  CURRENT_TIMESTAMP(),
  0,
  0,
  0,
  0.0,
  CURRENT_USER(),
  'Audit table created as part of Day 1 implementation'
);

-- Verify the table was created
SELECT * FROM crm.sfdc_dbx.sync_audit_log;
