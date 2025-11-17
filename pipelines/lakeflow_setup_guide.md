# Lakeflow Connect Setup Guide
## AWS RDS PostgreSQL to Databricks Migration

**Target:** `pg_rds_public` schema (20 core tables)
**Source:** AWS RDS PostgreSQL
**Destination:** Databricks Unity Catalog (`rds` catalog)

---

## Phase 1: AWS RDS PostgreSQL Configuration

### Step 1.1: Enable Logical Replication

Logical replication is required for CDC (Change Data Capture) in Lakeflow Connect.

**Option A: Using AWS Console**
1. Navigate to RDS → Parameter Groups
2. Find or create a custom parameter group for your PostgreSQL version
3. Edit the parameter group:
   - Set `rds.logical_replication` = `1`
4. Apply the parameter group to your RDS instance
5. **Reboot the RDS instance** (required for this parameter change)

**Option B: Using AWS CLI**
```bash
# Create a new parameter group (if needed)
aws rds create-db-parameter-group \
    --db-parameter-group-name lakeflow-postgres-params \
    --db-parameter-group-family postgres15 \
    --description "PostgreSQL parameters with logical replication enabled"

# Modify the parameter
aws rds modify-db-parameter-group \
    --db-parameter-group-name lakeflow-postgres-params \
    --parameters "ParameterName=rds.logical_replication,ParameterValue=1,ApplyMethod=pending-reboot"

# Apply to your RDS instance
aws rds modify-db-instance \
    --db-instance-identifier <your-rds-instance-id> \
    --db-parameter-group-name lakeflow-postgres-params \
    --apply-immediately

# Reboot the instance
aws rds reboot-db-instance \
    --db-instance-identifier <your-rds-instance-id>
```

**Verification:**
After reboot, connect to PostgreSQL and verify:
```sql
SHOW wal_level;
-- Should return: logical
```

### Step 1.2: Create Replication User and Grant Permissions

Connect to your RDS PostgreSQL instance and run the following SQL:

```sql
-- Create a dedicated user for Lakeflow Connect
CREATE ROLE lakeflow_user WITH LOGIN PASSWORD '<secure-password>';

-- Grant replication privileges
GRANT rds_replication TO lakeflow_user;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO lakeflow_user;

-- Grant SELECT on all existing tables in public schema
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lakeflow_user;

-- Grant SELECT on future tables (optional but recommended)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO lakeflow_user;

-- Create a replication slot (will be done by Lakeflow Connect, but you can verify permissions)
-- This tests that the user has proper replication permissions
SELECT pg_create_logical_replication_slot('test_slot', 'pgoutput');
SELECT pg_drop_replication_slot('test_slot');
```

### Step 1.3: Configure Network Access

Ensure Databricks can reach your RDS instance:

**Option A: Public Access (Testing Only)**
- RDS Security Group: Allow inbound from Databricks IP ranges
- Find Databricks IPs: https://docs.databricks.com/resources/ip-addresses.html

**Option B: Private Connectivity (Production - Recommended)**
- Use AWS PrivateLink
- Configure VPC peering between Databricks VPC and RDS VPC
- Update RDS security group to allow Databricks VPC CIDR

### Step 1.4: Gather Connection Details

You'll need:
- **Hostname:** `<your-rds-instance>.region.rds.amazonaws.com`
- **Port:** `5432` (default)
- **Database Name:** `<your-database-name>`
- **Username:** `lakeflow_user`
- **Password:** `<secure-password>`
- **Schema:** `public`

---

## Phase 2: Databricks Lakeflow Connect Setup

### Step 2.1: Create Secret Scope (Store Credentials Securely)

**Option A: Using Databricks CLI**
```bash
# Create secret scope
databricks secrets create-scope --scope lakeflow-rds --profile pat

# Add database password
databricks secrets put --scope lakeflow-rds --key postgres-password --profile pat
# This will open an editor - paste your password and save

# Add username (optional, can be in connection string)
databricks secrets put --scope lakeflow-rds --key postgres-username --profile pat
```

**Option B: Using Databricks UI**
1. Navigate to: Workspace → Settings → Secrets
2. Create new scope: `lakeflow-rds`
3. Add secret: `postgres-password`

### Step 2.2: Create Connection in Databricks

**Using Databricks UI:**
1. Navigate to **Catalog** → **External Data** → **Connections**
2. Click **Create Connection**
3. Select **PostgreSQL** connector type
4. Fill in connection details:
   ```
   Name: rds_postgres_public
   Host: <your-rds-endpoint>.rds.amazonaws.com
   Port: 5432
   Database: <your-database-name>
   Schema: public
   Username: lakeflow_user
   Password: {{secrets/lakeflow-rds/postgres-password}}
   ```
5. Click **Test Connection**
6. If successful, click **Create**

**Using REST API (Alternative):**
```bash
# Create connection via API
curl -X POST https://<workspace-url>/api/2.0/unity-catalog/connections \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rds_postgres_public",
    "connection_type": "POSTGRESQL",
    "options": {
      "host": "<your-rds-endpoint>.rds.amazonaws.com",
      "port": "5432",
      "database": "<your-database-name>",
      "schema": "public",
      "user": "lakeflow_user",
      "password": "{{secrets/lakeflow-rds/postgres-password}}"
    }
  }'
```

### Step 2.3: Verify Connection and Browse Tables

Once the connection is created:
1. Navigate to **Catalog** → **External Data** → **Connections**
2. Click on `rds_postgres_public`
3. Browse the `public` schema
4. Verify you can see all 20 target tables

---

## Phase 3: Delta Live Tables Pipeline Setup

### Step 3.1: Create DLT Pipeline Notebook

The pipeline notebook will define how data flows from PostgreSQL to Delta Lake.

See: `/Users/danerosa/rds_databricks_claude/pipelines/lakeflow_dlt_pipeline.py`

### Step 3.2: Create DLT Pipeline

**Using Databricks UI:**
1. Navigate to **Workflows** → **Delta Live Tables**
2. Click **Create Pipeline**
3. Configure:
   ```
   Pipeline Name: RDS Public Schema - Lakeflow Connect
   Product Edition: Advanced (required for Lakeflow Connect)
   Pipeline Mode: Continuous (for real-time CDC)
   Notebook Libraries: /Users/dane@snappt.com/lakeflow_dlt_pipeline
   Storage Location: dbfs:/pipelines/rds_public_lakeflow
   Target Catalog: rds
   Target Schema: pg_rds_public
   Compute: Serverless (required for Lakeflow Connect)
   ```
4. Click **Create**

### Step 3.3: Configure Pipeline Settings

**Important Pipeline Configurations:**

```json
{
  "configuration": {
    "connection_name": "rds_postgres_public",
    "source_schema": "public",
    "sync_mode": "FULL_THEN_INCREMENTAL"
  },
  "continuous": true,
  "photon": true,
  "serverless": true
}
```

---

## Phase 4: Initial Sync and Testing

### Step 4.1: Start Pipeline (Full Load)

1. Navigate to your DLT pipeline
2. Click **Start**
3. The pipeline will:
   - Perform initial full sync of all 20 tables
   - Create Delta tables in `rds.pg_rds_public`
   - Set up logical replication for CDC

**Expected Duration:** 15-60 minutes (depends on table sizes)

### Step 4.2: Monitor Progress

**In Pipeline UI:**
- View table-by-table sync progress
- Check for any errors or warnings
- Monitor row counts

**SQL Verification:**
```sql
-- Check that tables were created
SHOW TABLES IN rds.pg_rds_public;

-- Compare row counts (example for entries table)
SELECT COUNT(*) FROM rds.pg_rds_public.entries;
-- Compare this with source PostgreSQL

-- Check data freshness
SELECT MAX(_change_timestamp) FROM rds.pg_rds_public.entries;
```

### Step 4.3: Validate Data Quality

Run validation queries for critical tables:

```sql
-- Check for NULL primary keys (should be 0)
SELECT COUNT(*) FROM rds.pg_rds_public.applicants WHERE id IS NULL;

-- Verify referential integrity
SELECT COUNT(*)
FROM rds.pg_rds_public.applicants a
LEFT JOIN rds.pg_rds_public.companies c ON a.company_id = c.id
WHERE a.company_id IS NOT NULL AND c.id IS NULL;

-- Check recent data (should show today's date)
SELECT MAX(created_at) FROM rds.pg_rds_public.entries;
```

---

## Phase 5: Enable CDC and Ongoing Sync

### Step 5.1: Verify CDC is Active

After full load completes:

```sql
-- Check for CDC metadata columns
DESCRIBE TABLE rds.pg_rds_public.entries;
-- Should see: _change_type, _commit_version, _change_timestamp
```

### Step 5.2: Test Real-Time Updates

**In PostgreSQL (source):**
```sql
-- Insert a test record
INSERT INTO public.entries (id, name, created_at)
VALUES (999999, 'test_entry', NOW());
```

**In Databricks (verify within 1-2 minutes):**
```sql
SELECT * FROM rds.pg_rds_public.entries
WHERE id = 999999;
```

### Step 5.3: Monitor Lag

```sql
-- Check sync lag
SELECT
  table_name,
  MAX(_change_timestamp) as last_change,
  CURRENT_TIMESTAMP() as now,
  TIMESTAMPDIFF(MINUTE, MAX(_change_timestamp), CURRENT_TIMESTAMP()) as lag_minutes
FROM rds.pg_rds_public.entries
GROUP BY table_name;
```

---

## Phase 6: Cutover from Fivetran

### Step 6.1: Run Parallel Testing (1-2 weeks)

- Keep Fivetran running
- Run Lakeflow Connect in parallel
- Compare data quality, freshness, and reliability

### Step 6.2: Update Downstream Dependencies

Update queries/dashboards to use new table paths:
```sql
-- Old Fivetran path (example)
SELECT * FROM fivetran_schema.entries;

-- New Lakeflow path
SELECT * FROM rds.pg_rds_public.entries;
```

### Step 6.3: Pause Fivetran Connectors

Once confident:
1. Pause Fivetran syncs for the 20 tables
2. Monitor Lakeflow Connect for 48 hours
3. If stable, disable Fivetran connectors

---

## Troubleshooting

### Issue: Connection Test Fails
- Verify RDS security group allows Databricks IPs
- Check username/password in secret scope
- Verify RDS endpoint is correct
- Ensure database name is correct

### Issue: Logical Replication Slot Errors
```sql
-- Check existing replication slots
SELECT * FROM pg_replication_slots;

-- Drop stuck slots (if needed)
SELECT pg_drop_replication_slot('slot_name');
```

### Issue: Pipeline Stalls During Full Load
- Check cluster size (increase if needed)
- Verify source database isn't under heavy load
- Check for long-running transactions blocking replication

### Issue: CDC Lag Increasing
- Check source database transaction volume
- Increase pipeline compute resources
- Verify network connectivity is stable

---

## Monitoring and Maintenance

### Daily Checks
```sql
-- Check sync lag
SELECT
  table_name,
  MAX(_change_timestamp) as last_sync,
  DATEDIFF(minute, MAX(_change_timestamp), CURRENT_TIMESTAMP()) as lag_minutes
FROM (
  SELECT 'entries' as table_name, _change_timestamp FROM rds.pg_rds_public.entries
  UNION ALL
  SELECT 'applicants' as table_name, _change_timestamp FROM rds.pg_rds_public.applicants
  -- Add more tables as needed
)
GROUP BY table_name
HAVING lag_minutes > 5;
```

### Weekly Maintenance
- Review pipeline execution logs
- Check for failed syncs
- Verify row counts match source
- Monitor storage costs

---

## Next Steps

1. ✅ Complete Phase 1: PostgreSQL Configuration
2. ✅ Complete Phase 2: Create Databricks Connection
3. ✅ Complete Phase 3: Set up DLT Pipeline
4. ✅ Complete Phase 4: Run Initial Sync
5. ✅ Complete Phase 5: Validate CDC
6. ✅ Complete Phase 6: Migrate from Fivetran

---

**Questions or Issues?** Document them in `/Users/danerosa/rds_databricks_claude/pipelines/setup_notes.md`
