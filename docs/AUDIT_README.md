# Databricks Workspace Audit Tool

This tool helps you audit your Databricks workspace to identify unused assets and understand what should be migrated to a production environment.

## Prerequisites

1. Databricks CLI installed and configured
2. Python 3.7+

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Databricks CLI (if not already done):
```bash
databricks configure --token
```

You'll need:
- Databricks workspace URL (e.g., https://your-workspace.cloud.databricks.com)
- Personal access token (generate in User Settings > Access Tokens)

## Running the Audit

```bash
python workspace_audit.py
```

## What It Analyzes

### 1. Jobs
- Total number of jobs
- Active jobs (ran in last 90 days)
- Inactive jobs (not run in 90+ days)
- Never-run jobs
- Details: job name, creator, last run date

### 2. Clusters
- Total clusters
- Running vs terminated
- Last activity time
- Configuration details (node types, workers)
- Creator information

### 3. Notebooks
- Total notebooks across workspace
- Inactive notebooks (not modified in 90+ days)
- Last modified date and user
- Language type

### 4. Tables (Manual Step)
- Provides SQL queries to run for table usage analysis
- Requires Unity Catalog or direct SQL execution

## Output

The script generates two files in `audit_results/`:

1. **audit_report_[timestamp].txt** - Human-readable summary with recommendations
2. **audit_detailed_[timestamp].json** - Complete data for further analysis

## Customization

Edit these variables in `workspace_audit.py`:

- `DAYS_THRESHOLD_INACTIVE` - Days to consider asset inactive (default: 90)
- `OUTPUT_DIR` - Where to save results (default: "audit_results")

## Next Steps After Audit

Based on the audit results:

1. **Identify production assets** - Review active jobs and notebooks
2. **Clean up workspace** - Archive/delete unused resources
3. **Plan migration** - Determine what to move to prod environment
4. **Calculate costs** - Estimate compute needs for prod workspace
5. **Implement governance** - Set up policies to prevent future sprawl

## Advanced: Table Usage Analysis

To analyze table usage, connect to your workspace and run:

```sql
-- Tables by size and last access
SELECT
  table_catalog,
  table_schema,
  table_name,
  table_type,
  created_time,
  last_altered
FROM system.information_schema.tables
ORDER BY last_altered DESC;

-- Query audit logs (Unity Catalog)
SELECT
  event_time,
  user_identity.email as user,
  request_params.full_name_arg as table_name,
  action_name
FROM system.access.audit
WHERE action_name LIKE '%table%'
  AND event_date >= current_date() - INTERVAL 90 DAYS
ORDER BY event_time DESC;
```

## Troubleshooting

**Issue**: "databricks: command not found"
- Install: `pip install databricks-cli`

**Issue**: Authentication errors
- Run: `databricks configure --token`
- Verify token has proper permissions

**Issue**: Timeout errors
- Large workspaces may need increased timeout
- Edit `timeout=300` in `run_databricks_cli()` function

## Support

For issues or questions, refer to Databricks CLI documentation:
https://docs.databricks.com/dev-tools/cli/index.html
