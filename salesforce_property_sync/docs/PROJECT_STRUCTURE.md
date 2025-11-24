# Project Structure Documentation

This document provides a detailed overview of the project's organization and file structure.

## Directory Overview

```
rds_databricks_claude/
├── config/          # Configuration and credentials (GITIGNORED)
├── data/            # Data files and exports (GITIGNORED)
├── docs/            # All project documentation
├── results/         # Script outputs and logs (GITIGNORED)
└── scripts/         # Python scripts organized by purpose
```

## Detailed Structure

### Root Level Files

| File | Purpose | Committable |
|------|---------|-------------|
| `README.md` | Main project documentation | ✓ Yes |
| `.gitignore` | Git ignore rules for security | ✓ Yes |
| `.env.example` | Template for environment variables | ✓ Yes |
| `requirements.txt` | Python dependencies | ✓ Yes |
| `setup.sh` | Quick start setup script | ✓ Yes |

### config/ - Configuration Files

**Purpose**: Store all configuration and credential files
**Git Status**: ENTIRE DIRECTORY GITIGNORED

| File | Purpose | Committable |
|------|---------|-------------|
| `.env` | Environment variables with Databricks credentials | ✗ NO |
| `.databrickscfg` | Databricks CLI configuration | ✗ NO |
| `.databrickscfg.example` | Template for Databricks config | ✓ Yes |
| `README.md` | Configuration setup instructions | ✓ Yes |

**Security Notes:**
- This directory is fully gitignored
- Never commit actual credentials
- Use template files to share configuration structure

### data/ - Data Files

**Purpose**: Store sample data and exports
**Git Status**: Partially gitignored (large files excluded)

#### data/samples/
Sample data files used for testing and development.

| File Type | Example | Committable |
|-----------|---------|-------------|
| Small text files | `databricks_sample_pks.txt` | ✓ Yes |
| Sample JSON | Small samples < 1MB | ✓ Yes |

#### data/exports/
Large data exports from scripts.

| File Type | Example | Committable |
|-----------|---------|-------------|
| JSON exports | `enterprise_property_history_20days.json` | ✗ NO (3.4MB) |
| CSV exports | `*.csv` | ✗ NO |
| Parquet files | `*.parquet` | ✗ NO |

**Note**: Large data files are gitignored automatically.

### docs/ - Documentation

**Purpose**: All project documentation organized by topic
**Git Status**: All documentation is committable

#### docs/migration/
Migration guides and strategies.

| File | Purpose |
|------|---------|
| `00_rds_dlt_migration_guide.md` | Complete 8-12 week DLT migration guide |

#### docs/analysis/
Technical analysis and architecture documents.

| File | Purpose |
|------|---------|
| `dim_fde_dlt_analysis.md` | FDE table DLT conversion analysis |
| `workflow_dlt_analysis.md` | Workflow-level DLT analysis |

#### docs/investigations/
Investigation reports and problem-solving documentation.

| File | Purpose |
|------|---------|
| `DATA_LOSS_INVESTIGATION_REPORT.md` | Data loss incident investigation |
| `FIX_FIVETRAN_PK_CONFIG.md` | Fivetran primary key configuration fix |
| `SOLUTION_RESET_TABLE.md` | Table reset solution documentation |
| `AUDIT_README.md` | Workspace audit tool documentation |

### results/ - Script Outputs

**Purpose**: Store outputs from script executions
**Git Status**: ENTIRE DIRECTORY GITIGNORED

#### results/audit_results/
Audit reports and JSON exports.

| File Type | Example |
|-----------|---------|
| Text reports | `audit_report_20251024_135142.txt` |
| JSON data | `audit_detailed_20251024_135142.json` |
| Notebook exports | `notebooks_20251024_143907.json` |

#### results/logs/
Execution logs from scripts.

| File Type | Example |
|-----------|---------|
| Log files | `audit_run.log` |

**Note**: This directory is gitignored to prevent committing potentially sensitive output data.

### scripts/ - Python Scripts

**Purpose**: All Python scripts organized by functional category
**Git Status**: All scripts are committable

#### scripts/analysis/
Workflow and cost analysis tools.

| Script | Purpose |
|--------|---------|
| `analyze_all_workflows.py` | Analyze all Databricks workflows in workspace |
| `analyze_rds_workflow.py` | Deep analysis of RDS workflow structure |
| `analyze_table_impact.py` | Understand table dependencies and impact |
| `cost_analysis.py` | Estimate and analyze Databricks compute costs |

**Use Cases:**
- Understanding workflow architecture
- Identifying dependencies
- Cost optimization
- Migration planning

#### scripts/audit/
Workspace auditing and resource identification.

| Script | Purpose |
|--------|---------|
| `workspace_audit.py` | Comprehensive workspace audit (v1) |
| `workspace_audit_v2.py` | Enhanced workspace audit (v2) |
| `notebook_audit.py` | Notebook-specific usage audit |
| `quick_audit.py` | Fast audit for quick checks |
| `top_notebook_creators.py` | Identify top notebook creators by volume |

**Use Cases:**
- Identifying inactive resources
- Finding unused notebooks
- Understanding workspace usage patterns
- Planning workspace cleanup
- Cost reduction initiatives

#### scripts/validation/
Data validation and integrity checks.

| Script | Purpose |
|--------|---------|
| `check_actual_row_state.py` | Verify actual row state in tables |
| `check_all_rows.py` | Validate all rows in target tables |
| `check_hidden_rows.py` | Detect soft-deleted or hidden rows |
| `check_pk_value.py` | Validate primary key values |
| `check_table_stats.py` | Generate table statistics and health metrics |
| `check_workflows_pipelines.py` | Validate workflow and pipeline configurations |

**Use Cases:**
- Data integrity validation
- Primary key consistency checks
- Detecting data quality issues
- Pre-migration validation
- Post-migration verification

#### scripts/investigation/
Debugging and investigation tools.

| Script | Purpose |
|--------|---------|
| `investigate_dim_fde.py` | Investigate issues with dim_fde table |
| `investigate_oct13_update.py` | Investigate specific October 13 update issue |
| `investigate_sync_failure.py` | Debug synchronization failures |
| `query_deleted_rows.py` | Find and analyze deleted rows |

**Use Cases:**
- Troubleshooting data issues
- Root cause analysis
- Data loss investigation
- Sync failure debugging

#### scripts/pipeline/
Delta Live Tables pipeline code and validation.

| Script | Purpose |
|--------|---------|
| `dlt_fde_pipeline.py` | Main DLT pipeline for FDE table migration |
| `validate_dlt_output.py` | Validate DLT pipeline outputs against source |

**Use Cases:**
- DLT pipeline implementation
- Pipeline output validation
- Migration verification

#### scripts/testing/
Connection and consistency testing tools.

| Script | Purpose |
|--------|---------|
| `test_connection.py` | Test Databricks connectivity |
| `test_pk_consistency.py` | Test primary key consistency across tables |

**Use Cases:**
- Verifying setup
- Testing connectivity
- Pre-deployment checks
- Continuous validation

#### scripts/utils/
Utility scripts for common tasks.

| Script | Purpose |
|--------|---------|
| `get_table_history.py` | Retrieve Delta table history |
| `get_table_history_json.py` | Export table history as JSON |

**Use Cases:**
- Data lineage tracking
- Change history analysis
- Audit trail generation

## File Naming Conventions

### Scripts
- Use descriptive names: `analyze_`, `check_`, `investigate_`, `test_`, `validate_`
- Use underscores for word separation: `analyze_all_workflows.py`
- Keep names concise but clear

### Documentation
- Use uppercase for major reports: `DATA_LOSS_INVESTIGATION_REPORT.md`
- Use descriptive names: `00_rds_dlt_migration_guide.md`
- Include dates in filenames when relevant

### Output Files
- Include timestamps: `audit_report_20251024_135142.txt`
- Use descriptive prefixes: `audit_`, `notebook_`, `detailed_`

## Adding New Files

### Adding a New Script

1. Determine the appropriate category:
   - Analysis? → `scripts/analysis/`
   - Validation? → `scripts/validation/`
   - Investigation? → `scripts/investigation/`
   - Testing? → `scripts/testing/`
   - Utility? → `scripts/utils/`

2. Create the script with proper header:
```python
#!/usr/bin/env python3
"""
Script Name: my_script.py
Purpose: Brief description
Usage: python scripts/category/my_script.py
"""
```

3. Load credentials properly:
```python
from dotenv import load_dotenv
import os

load_dotenv('config/.env')
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')
```

4. Update relevant documentation

### Adding New Documentation

1. Determine the appropriate category:
   - Migration guide? → `docs/migration/`
   - Technical analysis? → `docs/analysis/`
   - Investigation report? → `docs/investigations/`

2. Create the document with proper header
3. Update this PROJECT_STRUCTURE.md
4. Reference from main README.md if relevant

### Adding Data Files

1. **Small samples** (< 1MB):
   - Place in `data/samples/`
   - Can be committed to git
   - Document in README

2. **Large exports** (> 1MB):
   - Place in `data/exports/`
   - Automatically gitignored
   - Document how to regenerate if needed

## Security Checklist

Before committing any changes, verify:

- [ ] No credentials in committed files
- [ ] No `.env` or `.databrickscfg` files (except templates)
- [ ] No large data files in `data/exports/`
- [ ] No sensitive output in `results/`
- [ ] Configuration files are in `config/` directory
- [ ] Templates (`.example` files) contain no real credentials

## Maintenance

### Regular Tasks

1. **Weekly**: Review `results/` directory size
2. **Monthly**: Clean up old audit reports
3. **Quarterly**: Review and archive old investigation reports
4. **As needed**: Update documentation when adding features

### Archive Process

When archiving old files:

1. Create `archive/` directory at the appropriate level
2. Move old files with date range: `archive/2024-q4/`
3. Update documentation to reflect changes

## Questions?

Refer to:
- Main [README.md](../README.md) for general project information
- [config/README.md](../config/README.md) for configuration help
- Individual script headers for usage information

---

**Document Version**: 1.0
**Last Updated**: 2024-10-29
