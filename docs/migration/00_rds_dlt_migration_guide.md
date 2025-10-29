# 00_RDS DLT Migration - Getting Started Guide

**Project**: Migrating 00_RDS workflow from notebook-based tasks to DLT pipeline
**Timeline**: 8-12 weeks
**Owner**: dane@snappt.com
**Created**: 2025-10-22

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 0: Preparation (Week 1)](#phase-0-preparation-week-1)
4. [Phase 1: Unity FDE DLT Pipeline (Weeks 2-5)](#phase-1-unity-fde-dlt-pipeline-weeks-2-5)
5. [Phase 2: Downstream Tables (Weeks 6-11)](#phase-2-downstream-tables-weeks-6-11)
6. [Phase 3: Cutover & Optimization (Week 12)](#phase-3-cutover--optimization-week-12)
7. [Project Structure](#project-structure)
8. [Testing Strategy](#testing-strategy)
9. [Rollback Plan](#rollback-plan)

---

## Overview

### Current State
- **Workflow**: 00_RDS (Job ID: 314473856953682)
- **Schedule**: Every 6 hours (4x daily)
- **Architecture**: 12 notebook-based tasks with complex dependencies
- **Main output**: `product.fde.dim_fde` and downstream analytical tables

### Target State
- **Workflow**: 00_RDS v2 (New Job)
- **Schedule**: Same (every 6 hours)
- **Architecture**: 7 tasks (1 DLT pipeline + 6 notebooks)
- **DLT Pipeline**: Manages 6 data tables in medallion architecture

### Tasks to Convert to DLT
1. ✅ `unity_fde` → Bronze/Silver/Gold layers (READY - code exists!)
2. `income_verification` → Gold layer
3. `iv_fde_ax` → Gold layer
4. `iv_master_results` → Gold layer
5. `unity_av_fde` → Gold layer
6. `roi_fraud_reduction` → Gold layer

---

## Prerequisites

### Tools & Access
- [ ] Databricks Workspace access (with CREATE PIPELINE permission)
- [ ] GitHub access to `https://github.com/snapptinc/dbx`
- [ ] Databricks CLI configured (`~/.databrickscfg` setup)
- [ ] Python 3.10+ with virtual environment
- [ ] Access to RDS source tables (`rds.pg_rds_public.*`)
- [ ] Write access to `team_sandbox.data_engineering.*` (for testing)
- [ ] Write access to `product.fde.*` (for production)

### Knowledge Requirements
- [ ] Understanding of Delta Live Tables concepts
- [ ] Familiarity with PySpark/SparkSQL
- [ ] Knowledge of existing 00_RDS workflow
- [ ] Understanding of FDE data model

### Repository Setup
```bash
# Clone the repository
git clone https://github.com/snapptinc/dbx.git
cd dbx

# Create feature branch
git checkout -b feature/00-rds-dlt-migration

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install databricks-cli pyspark
```

---

## Phase 0: Preparation (Week 1)

### Step 1: Understand Current Notebooks

**Action Items:**
1. Export and review all task notebooks from 00_RDS workflow
2. Document what each notebook does
3. Identify table outputs and dependencies
4. Map data lineage

**Commands:**
```bash
# Export all notebooks to understand them
databricks workspace export /Repos/dbx_git/dbx/snappt/unity_fde --profile m2m > notebooks/unity_fde.py
databricks workspace export /Repos/dbx_git/dbx/snappt/dash_fde_iv_submissions --profile m2m > notebooks/income_verification.sql
databricks workspace export /Repos/dbx_git/dbx/snappt/iv_fde_ax --profile m2m > notebooks/iv_fde_ax.sql
databricks workspace export /Repos/dbx_git/dbx/snappt/iv_master_results --profile m2m > notebooks/iv_master_results.sql
databricks workspace export /Repos/dbx_git/dbx/snappt/unity_av_fde --profile m2m > notebooks/unity_av_fde.sql
databricks workspace export /Repos/dbx_git/dbx/snappt/roi_fraud_reduction_submission_level --profile m2m > notebooks/roi_fraud_reduction.sql
```

**Deliverable:**
- [ ] Documentation of each notebook's purpose
- [ ] List of output tables and their schemas
- [ ] Data lineage diagram

### Step 2: Set Up Development Environment

**Action Items:**
1. Create development DLT pipeline in Databricks
2. Set up sandbox catalog for testing
3. Configure CI/CD (if not already set up)

**Databricks Workspace Setup:**
```bash
# Create workspace directory for DLT pipeline
databricks workspace mkdirs /Repos/dbx_git/dbx/snappt/dlt_pipelines --profile m2m

# Upload initial DLT pipeline code (we already have unity_fde!)
databricks workspace import /Repos/dbx_git/dbx/snappt/dlt_pipelines/fde_pipeline.py \
  --file dlt_fde_pipeline.py --language PYTHON --profile m2m
```

**Deliverable:**
- [ ] Development pipeline created in Databricks
- [ ] Sandbox catalog/schema configured (`team_sandbox.data_engineering`)
- [ ] Git branch created and pushed

### Step 3: Review Existing DLT Code

**Action Items:**
1. Review `dlt_fde_pipeline.py` (already created!)
2. Test the existing unity_fde DLT code
3. Validate it produces the same output

**Commands:**
```bash
# Review existing DLT code
cat dlt_fde_pipeline.py

# The file already contains:
# - Bronze layer: bronze_fde_raw (11-table JOIN)
# - Silver layer: silver_fde_cleaned (exclusions applied)
# - Gold layer: dim_fde (final dimension table)
```

**Deliverable:**
- [ ] Unity FDE DLT code reviewed and validated
- [ ] Test run completed in sandbox
- [ ] Output compared with production table

### Step 4: Create Project Plan

**Action Items:**
1. Review this migration guide with the team
2. Get stakeholder approval
3. Schedule weekly check-ins
4. Assign resources (1-2 engineers)

**Deliverable:**
- [ ] Team alignment on approach
- [ ] Timeline approved
- [ ] Resources allocated
- [ ] Weekly check-in meetings scheduled

---

## Phase 1: Unity FDE DLT Pipeline (Weeks 2-5)

### Week 2: Deploy Development Pipeline

**Goal**: Get unity_fde DLT pipeline running in sandbox

**Step 1: Create DLT Pipeline in Databricks UI**

1. Navigate to **Workflows** → **Delta Live Tables** → **Create Pipeline**
2. Configure pipeline:
   - **Name**: `00_RDS_FDE_Pipeline_DEV`
   - **Product Edition**: Advanced
   - **Pipeline Mode**: Triggered (not continuous)
   - **Source Code**: `/Repos/dbx_git/dbx/snappt/dlt_pipelines/fde_pipeline.py`
   - **Target**: `team_sandbox.data_engineering`
   - **Storage Location**: `dbfs:/pipelines/00_rds_fde_dev`
   - **Cluster Mode**: Fixed Size
   - **Workers**: 8 (match current 00_RDS)
   - **Photon**: Enabled
   - **Node Type**: r6id.xlarge

3. Add configuration:
   ```json
   {
     "catalog": "team_sandbox",
     "schema": "data_engineering",
     "table_prefix": "dlt_test_"
   }
   ```

**Step 2: First Test Run**

```bash
# Trigger pipeline via CLI
databricks pipelines start-update --profile m2m \
  --pipeline-id <PIPELINE_ID_FROM_UI>

# Monitor progress
databricks pipelines get-update --profile m2m \
  --pipeline-id <PIPELINE_ID_FROM_UI> \
  --update-id <UPDATE_ID>
```

**Step 3: Validate Output**

```sql
-- In Databricks SQL Editor
-- Compare row counts
SELECT 'production' as source, COUNT(*) as row_count
FROM product.fde.dim_fde
UNION ALL
SELECT 'dlt_dev' as source, COUNT(*) as row_count
FROM team_sandbox.data_engineering.dlt_test_dim_fde;

-- Compare distinct keys
SELECT 'production' as source,
  COUNT(DISTINCT property_id) as properties,
  COUNT(DISTINCT submission_id) as submissions,
  COUNT(DISTINCT document_id) as documents
FROM product.fde.dim_fde
UNION ALL
SELECT 'dlt_dev' as source,
  COUNT(DISTINCT property_id) as properties,
  COUNT(DISTINCT submission_id) as submissions,
  COUNT(DISTINCT document_id) as documents
FROM team_sandbox.data_engineering.dlt_test_dim_fde;
```

**Deliverable:**
- [ ] DLT pipeline created in Databricks
- [ ] First successful run completed
- [ ] Output tables created in sandbox
- [ ] Basic validation passed

### Week 3: Parallel Testing

**Goal**: Run DLT pipeline alongside existing notebook

**Step 1: Schedule DLT Pipeline**

1. In Databricks UI, go to your DLT pipeline
2. Click **Settings** → **Schedule**
3. Add schedule:
   - **Cron**: `0 0 6,12,18 * * ?` (offset from production by 1 hour)
   - **Timezone**: America/New_York

**Step 2: Set Up Monitoring**

```python
# Create monitoring notebook: monitoring/compare_outputs.py
# Databricks notebook source
"""
Compare DLT output with production table
Run after each DLT pipeline execution
"""

import pandas as pd
from pyspark.sql import functions as F

# Compare schemas
prod_schema = spark.table("product.fde.dim_fde").schema
dev_schema = spark.table("team_sandbox.data_engineering.dlt_test_dim_fde").schema

print("Schema Differences:")
prod_cols = set([f.name for f in prod_schema.fields])
dev_cols = set([f.name for f in dev_schema.fields])
print(f"Missing in DEV: {prod_cols - dev_cols}")
print(f"Extra in DEV: {dev_cols - prod_cols}")

# Compare data
prod_df = spark.table("product.fde.dim_fde")
dev_df = spark.table("team_sandbox.data_engineering.dlt_test_dim_fde")

# Row counts
prod_count = prod_df.count()
dev_count = dev_df.count()
print(f"\nRow Count - Prod: {prod_count:,}, Dev: {dev_count:,}, Diff: {abs(prod_count - dev_count):,}")

# Sample comparison
comparison = prod_df.join(
    dev_df,
    on=['property_id', 'submission_id', 'document_id'],
    how='full_outer'
).where(
    "property_id IS NULL OR submission_id IS NULL OR document_id IS NULL"
)

missing_count = comparison.count()
print(f"Missing/Extra records: {missing_count:,}")

if missing_count > 0:
    print("\nSample differences:")
    comparison.show(20, truncate=False)
```

**Step 3: Daily Validation**

Run the monitoring notebook daily for 1 week and log results.

**Deliverable:**
- [ ] DLT pipeline scheduled (offset from production)
- [ ] Monitoring notebook created and scheduled
- [ ] 1 week of parallel runs completed
- [ ] Validation reports generated

### Week 4: Performance Optimization

**Goal**: Optimize DLT pipeline performance and costs

**Step 1: Analyze Performance Metrics**

1. Go to DLT pipeline → **Details** tab
2. Review:
   - **Execution time** (should be similar to notebook)
   - **Data processed** (GB)
   - **DBU consumption**
   - **Error rates**

**Step 2: Optimize if Needed**

```python
# Add optimizations to dlt_fde_pipeline.py

# Option 1: Enable auto-scaling
# In pipeline settings, change cluster mode to "Auto Scaling"
# Workers: 2 to 8

# Option 2: Add Z-ordering
@dlt.table(
    name=f"{TABLE_PREFIX}dim_fde",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.zOrderCols": "property_id,submission_datetime,company_id",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true"
    }
)

# Option 3: Add partition columns if data is large
# (Only if table is > 1TB)
@dlt.table(
    name=f"{TABLE_PREFIX}dim_fde",
    partition_cols=["submission_date"]  # Only if needed
)
```

**Deliverable:**
- [ ] Performance analysis completed
- [ ] Optimization applied (if needed)
- [ ] Cost comparison documented
- [ ] Performance meets or exceeds notebook

### Week 5: Production Preparation

**Goal**: Prepare for production deployment

**Step 1: Create Production DLT Pipeline**

```bash
# Update pipeline code for production
# Change configuration in dlt_fde_pipeline.py:
CATALOG = "product"
SCHEMA = "fde"
TABLE_PREFIX = "dlt_v2_"  # Use different prefix to not conflict
```

Create production pipeline in UI:
- **Name**: `00_RDS_FDE_Pipeline_PROD`
- **Target**: `product.fde`
- **Storage**: `dbfs:/pipelines/00_rds_fde_prod`
- **Schedule**: OFF (will trigger from workflow)

**Step 2: Create New 00_RDS Workflow**

Create new workflow: `00_RDS_v2`

```json
{
  "name": "00_RDS_v2",
  "max_concurrent_runs": 1,
  "schedule": {
    "quartz_cron_expression": "55 0 5/6 * * ?",
    "timezone_id": "America/New_York",
    "pause_status": "PAUSED"
  },
  "tasks": [
    {
      "task_key": "blockSelfJoins",
      "notebook_task": {
        "notebook_path": "snappt/python/blockSelfJoins",
        "source": "GIT"
      }
    },
    {
      "task_key": "fde_dlt_pipeline",
      "depends_on": [{"task_key": "blockSelfJoins"}],
      "pipeline_task": {
        "pipeline_id": "<PROD_PIPELINE_ID>",
        "full_refresh": false
      }
    },
    {
      "task_key": "24_hour_iv_submission_email",
      "depends_on": [{"task_key": "fde_dlt_pipeline"}],
      "notebook_task": {
        "notebook_path": "snappt/24hr_iv_table_email",
        "source": "GIT"
      }
    },
    {
      "task_key": "last_submission_report",
      "depends_on": [{"task_key": "fde_dlt_pipeline"}],
      "notebook_task": {
        "notebook_path": "snappt/fde_last_submission_report",
        "source": "GIT"
      }
    },
    {
      "task_key": "clean_tables",
      "depends_on": [{"task_key": "last_submission_report"}],
      "notebook_task": {
        "notebook_path": "snappt/unity_clean_tables",
        "source": "GIT"
      }
    },
    {
      "task_key": "properties_deactivation",
      "depends_on": [{"task_key": "fde_dlt_pipeline"}],
      "notebook_task": {
        "notebook_path": "snappt/properties_deactivation",
        "source": "GIT"
      }
    },
    {
      "task_key": "ov_dashboard",
      "depends_on": [{"task_key": "fde_dlt_pipeline"}],
      "notebook_task": {
        "notebook_path": "snappt/ov_dashboard",
        "source": "GIT"
      }
    }
  ]
}
```

**Step 3: Update Downstream Notebooks**

Update notebooks to read from new table:
```sql
-- OLD: FROM product.fde.dim_fde
-- NEW: FROM product.fde.dlt_v2_dim_fde

-- Or use a view for easier cutover:
CREATE OR REPLACE VIEW product.fde.dim_fde_v2 AS
SELECT * FROM product.fde.dlt_v2_dim_fde;
```

**Deliverable:**
- [ ] Production DLT pipeline created (not scheduled)
- [ ] New 00_RDS_v2 workflow created (paused)
- [ ] Downstream notebooks updated to use new table
- [ ] Ready for parallel production run

---

## Phase 2: Downstream Tables (Weeks 6-11)

**Note**: After unity_fde is stable in production, add other tasks to DLT pipeline

### Week 6-7: Add income_verification + iv_fde_ax

**Goal**: Convert next 2 tasks to DLT

**Step 1: Analyze Notebooks**

```bash
# Review what these notebooks do
databricks workspace export /Repos/dbx_git/dbx/snappt/dash_fde_iv_submissions --profile m2m > notebooks/income_verification.sql
databricks workspace export /Repos/dbx_git/dbx/snappt/iv_fde_ax --profile m2m > notebooks/iv_fde_ax.sql
```

**Step 2: Convert to DLT**

Add to `dlt_fde_pipeline.py`:

```python
# Add after dim_fde definition

@dlt.table(
    name=f"{TABLE_PREFIX}income_verification",
    comment="Income verification submissions with calculation details"
)
@dlt.expect_all({
    "valid_submission_id": "submission_id IS NOT NULL",
    "valid_status": "iv_status IN ('success', 'error', 'pending')"
})
def income_verification():
    """
    Creates the income verification table.
    Converts from: dash_fde_iv_submissions notebook
    """
    # Read from existing dim_fde
    dim_fde = dlt.read(f"{TABLE_PREFIX}dim_fde")

    # Add IV-specific logic here
    # (Convert SQL from notebook to PySpark)

    return transformed_df


@dlt.table(
    name=f"{TABLE_PREFIX}iv_fde_ax",
    comment="IV FDE analytics table"
)
def iv_fde_ax():
    """
    Creates IV FDE analytics table.
    Converts from: iv_fde_ax notebook
    """
    # Read from income_verification
    iv_df = dlt.read(f"{TABLE_PREFIX}income_verification")

    # Add analytics logic here

    return analytics_df
```

**Deliverable:**
- [ ] 2 new tables added to DLT pipeline
- [ ] Tested in sandbox
- [ ] Validated against production
- [ ] Deployed to production

### Week 8-9: Add iv_master_results + unity_av_fde

**Goal**: Convert next 2 tasks to DLT

Follow same process as weeks 6-7.

**Deliverable:**
- [ ] 2 more tables added to DLT pipeline
- [ ] Total of 5 tables now in DLT (dim_fde + 4 downstream)

### Week 10-11: Add roi_fraud_reduction

**Goal**: Convert final task to DLT

Follow same process.

**Deliverable:**
- [ ] All 6 tables now in DLT pipeline
- [ ] Full workflow running in parallel with original
- [ ] All validation tests passing

---

## Phase 3: Cutover & Optimization (Week 12)

### Step 1: Final Validation

**Action Items:**
1. Run both workflows in parallel for 1 week
2. Compare all outputs
3. Verify all downstream consumers work
4. Get stakeholder sign-off

**Validation Checklist:**
- [ ] All 6 tables produce identical output
- [ ] Performance is equal or better
- [ ] Costs are equal or lower
- [ ] All downstream dashboards/reports work
- [ ] Data quality metrics all green

### Step 2: Cutover Plan

**Action Items:**
1. Schedule cutover during low-traffic period
2. Communicate to stakeholders
3. Execute cutover

**Cutover Steps:**
```sql
-- Step 1: Rename tables (during cutover window)
ALTER TABLE product.fde.dim_fde RENAME TO product.fde.dim_fde_old;
ALTER TABLE product.fde.dlt_v2_dim_fde RENAME TO product.fde.dim_fde;

-- Repeat for all 6 tables

-- Step 2: Update workflow schedule
-- Pause 00_RDS (old)
-- Unpause 00_RDS_v2 (new)

-- Step 3: Monitor first few runs
```

**Rollback Plan:**
```sql
-- If issues arise, reverse the rename
ALTER TABLE product.fde.dim_fde RENAME TO product.fde.dim_fde_new;
ALTER TABLE product.fde.dim_fde_old RENAME TO product.fde.dim_fde;

-- Re-enable old workflow
-- Pause new workflow
```

### Step 3: Decommission Old Workflow

**Wait 1 week** after cutover, then:

1. Archive old 00_RDS workflow
2. Delete old tables (keep backups for 30 days)
3. Update documentation
4. Celebrate! 🎉

**Deliverable:**
- [ ] Cutover completed successfully
- [ ] Old workflow archived
- [ ] Documentation updated
- [ ] Team trained on new DLT pipeline

---

## Project Structure

```
dbx/
├── snappt/
│   ├── dlt_pipelines/
│   │   ├── fde_pipeline.py              # Main DLT pipeline
│   │   ├── fde_pipeline_config.json     # Pipeline configuration
│   │   └── README.md                    # Pipeline documentation
│   ├── monitoring/
│   │   ├── compare_outputs.py           # Validation notebook
│   │   └── dlt_metrics_dashboard.sql    # Monitoring dashboard
│   └── (existing notebooks remain unchanged)
└── docs/
    ├── 00_rds_dlt_migration_guide.md    # This guide
    ├── workflow_dlt_analysis.md          # Initial analysis
    └── dim_fde_dlt_analysis.md           # Technical details
```

---

## Testing Strategy

### Unit Testing

```python
# tests/test_dlt_pipeline.py
import pytest
from pyspark.sql import SparkSession
from dlt_fde_pipeline import get_fde_exclusion_filter

def test_exclusion_filter():
    """Test that exclusion filter works correctly"""
    spark = SparkSession.builder.getOrCreate()

    # Create test data
    test_data = [
        ("prop1", "Test Property", "Company A", "comp1"),  # Should exclude
        ("prop2", "Real Property", "Company B", "comp2"),  # Should include
    ]

    df = spark.createDataFrame(
        test_data,
        ["properties_id", "properties_name", "companies_name", "companies_short_id"]
    )

    # Apply filter
    filtered_df = df.filter(get_fde_exclusion_filter())

    # Verify
    assert filtered_df.count() == 1
    assert filtered_df.first()["properties_id"] == "prop2"
```

### Integration Testing

```python
# tests/test_integration.py
def test_full_pipeline():
    """Test that pipeline produces expected output"""

    # Trigger pipeline
    pipeline_id = "<TEST_PIPELINE_ID>"
    update_id = trigger_pipeline(pipeline_id)

    # Wait for completion
    wait_for_completion(pipeline_id, update_id)

    # Validate output
    df = spark.table("team_sandbox.data_engineering.dlt_test_dim_fde")

    assert df.count() > 0
    assert "property_id" in df.columns
    assert df.filter("property_id IS NULL").count() == 0
```

### Comparison Testing

```sql
-- Compare production vs DLT output
-- Run daily during parallel phase

-- 1. Row count comparison
SELECT 'production' as source, COUNT(*) as cnt FROM product.fde.dim_fde
UNION ALL
SELECT 'dlt' as source, COUNT(*) as cnt FROM team_sandbox.data_engineering.dlt_test_dim_fde;

-- 2. Missing records in DLT
SELECT 'missing_in_dlt' as issue, COUNT(*) as cnt
FROM product.fde.dim_fde p
LEFT ANTI JOIN team_sandbox.data_engineering.dlt_test_dim_fde d
  ON p.property_id = d.property_id
  AND p.submission_id = d.submission_id
  AND p.document_id = d.document_id;

-- 3. Extra records in DLT
SELECT 'extra_in_dlt' as issue, COUNT(*) as cnt
FROM team_sandbox.data_engineering.dlt_test_dim_fde d
LEFT ANTI JOIN product.fde.dim_fde p
  ON p.property_id = d.property_id
  AND p.submission_id = d.submission_id
  AND p.document_id = d.document_id;

-- 4. Value differences
SELECT
  p.property_id,
  p.submission_id,
  'submission_status' as column_name,
  p.submission_status as prod_value,
  d.submission_status as dlt_value
FROM product.fde.dim_fde p
JOIN team_sandbox.data_engineering.dlt_test_dim_fde d
  ON p.property_id = d.property_id
  AND p.submission_id = d.submission_id
  AND p.document_id = d.document_id
WHERE p.submission_status != d.submission_status
LIMIT 100;
```

---

## Rollback Plan

### If Issues During Development
- Simply pause the dev pipeline
- No impact on production

### If Issues During Parallel Production Run
- Pause new 00_RDS_v2 workflow
- Old 00_RDS continues running
- Investigate and fix issues
- Resume parallel run

### If Issues After Cutover
```sql
-- Emergency rollback (5 minute procedure)

-- 1. Pause new workflow
-- Via Databricks UI: Workflows → 00_RDS_v2 → Pause

-- 2. Restore old table names
ALTER TABLE product.fde.dim_fde RENAME TO product.fde.dim_fde_dlt_new;
ALTER TABLE product.fde.dim_fde_old RENAME TO product.fde.dim_fde;

-- (Repeat for all 6 tables)

-- 3. Resume old workflow
-- Via Databricks UI: Workflows → 00_RDS → Unpause

-- 4. Verify next run succeeds
-- Monitor workflow execution

-- 5. Investigate issues in new pipeline
-- Fix and test in sandbox before re-attempting cutover
```

---

## Success Metrics

### Technical Metrics
- [ ] Pipeline runs successfully 4x daily for 2 weeks
- [ ] Output matches production exactly (row-for-row)
- [ ] Execution time ≤ current notebook execution time
- [ ] DBU cost ≤ current workflow cost
- [ ] Data quality expectations all passing
- [ ] Zero production incidents

### Business Metrics
- [ ] All downstream dashboards working
- [ ] All scheduled reports delivering
- [ ] All data consumers satisfied
- [ ] Stakeholder approval obtained

### Quality Metrics
- [ ] 100% schema compatibility
- [ ] 100% data accuracy
- [ ] ≥ 99.9% pipeline reliability
- [ ] Data quality metrics implemented and tracking

---

## Common Issues & Solutions

### Issue: DLT pipeline is slower than notebook
**Solution:**
- Enable Photon if not already enabled
- Increase worker count
- Check for data skew (use `.repartition()`)
- Optimize JOIN strategies

### Issue: Output row count differs
**Solution:**
- Check for timing differences (data captured at different times)
- Verify exclusion logic is identical
- Check for duplicate handling differences
- Review DISTINCT/GROUP BY logic

### Issue: Schema differences
**Solution:**
- Ensure column names match exactly (case-sensitive)
- Check data types (INT vs BIGINT, etc.)
- Verify column order if needed
- Add explicit casts if needed

### Issue: Pipeline fails with timeout
**Solution:**
- Increase timeout settings
- Break into smaller incremental updates
- Optimize complex JOINs
- Check for shuffle operations

---

## Resources

### Documentation
- [Delta Live Tables Documentation](https://docs.databricks.com/delta-live-tables/index.html)
- [DLT Best Practices](https://docs.databricks.com/delta-live-tables/best-practices.html)
- [DLT Expectations](https://docs.databricks.com/delta-live-tables/expectations.html)

### Internal Resources
- **Existing DLT Example**: fa_stream workflow (Job ID: 781003259638778)
- **Analysis Doc**: `workflow_dlt_analysis.md`
- **Technical Doc**: `dim_fde_dlt_analysis.md`
- **Pipeline Code**: `dlt_fde_pipeline.py`

### Team Contacts
- **Project Owner**: dane@snappt.com
- **Data Engineering Team**: (add contacts)
- **Stakeholders**: (add contacts)

---

## Next Steps

### Immediate Actions (This Week)
1. [ ] Review this guide with the team
2. [ ] Set up development environment
3. [ ] Export and analyze all 6 notebooks
4. [ ] Create feature branch in Git
5. [ ] Schedule kickoff meeting

### Week 1 Actions
1. [ ] Complete Phase 0 (Preparation)
2. [ ] Test existing unity_fde DLT code in sandbox
3. [ ] Create development DLT pipeline
4. [ ] Set up monitoring notebooks

### Week 2 Actions
1. [ ] Start Phase 1 (Unity FDE DLT)
2. [ ] Deploy to sandbox
3. [ ] Begin parallel testing
4. [ ] Daily validation checks

---

## Questions & Answers

### Q: Why not convert everything at once?
**A**: Phased approach reduces risk. Unity FDE is the foundation - once stable, downstream tables are easier to convert.

### Q: What if the DLT pipeline is more expensive?
**A**: We can optimize with auto-scaling, lower worker counts, or spot instances. Monitoring during parallel run will show true costs.

### Q: How do we handle the 6-hour schedule?
**A**: DLT pipelines can be triggered from workflows just like notebooks. The new 00_RDS_v2 workflow will trigger the pipeline on the same schedule.

### Q: What about the notebooks that stay as-is?
**A**: Reporting notebooks (24hr_iv_submission_email, last_submission_report, etc.) remain as notebooks but now read from DLT tables.

### Q: Can we roll back if there's an issue?
**A**: Yes! During parallel run, old workflow continues. After cutover, we keep old tables for 30 days for emergency rollback.

---

## Appendix: CLI Commands Cheatsheet

```bash
# List all pipelines
databricks pipelines list --profile m2m

# Get pipeline details
databricks pipelines get <pipeline-id> --profile m2m

# Trigger pipeline
databricks pipelines start-update <pipeline-id> --profile m2m

# Get update status
databricks pipelines get-update <pipeline-id> <update-id> --profile m2m

# List all workflows
databricks jobs list --profile m2m

# Get workflow details
databricks jobs get <job-id> --profile m2m

# Trigger workflow
databricks jobs run-now <job-id> --profile m2m

# Export notebook
databricks workspace export <notebook-path> --profile m2m --format SOURCE

# Import notebook
databricks workspace import <notebook-path> --profile m2m --file <local-file>
```

---

**Last Updated**: 2025-10-22
**Version**: 1.0
**Status**: Ready to Start

