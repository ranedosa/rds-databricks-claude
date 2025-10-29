# RDS Databricks Migration & Analysis Project

A comprehensive toolkit for migrating RDS workflows to Databricks Delta Live Tables (DLT) and performing workspace audits, data validation, and cost analysis.

## Overview

This project contains tools and documentation for:
- **DLT Migration**: Converting notebook-based Databricks workflows to Delta Live Tables
- **Data Auditing**: Analyzing workspace usage, identifying unused resources
- **Data Validation**: Checking data integrity, table consistency, and primary key validation
- **Investigation Tools**: Debugging data loss, sync failures, and configuration issues
- **Cost Analysis**: Estimating and optimizing Databricks compute costs

## Project Structure

```
rds_databricks_claude/
├── README.md                    # This file
├── .env.example                 # Template for environment variables
├── .gitignore                   # Git ignore rules (protects sensitive data)
├── requirements.txt             # Python dependencies
├── setup.sh                     # Quick start setup script
│
├── config/                      # Configuration files (GITIGNORED - SENSITIVE!)
│   ├── .env                     # Environment variables (create from .env.example)
│   ├── .databrickscfg           # Databricks CLI config
│   ├── .databrickscfg.example   # Template for Databricks config
│   └── README.md                # Config setup instructions
│
├── docs/                        # Documentation
│   ├── migration/               # DLT migration guides
│   │   └── 00_rds_dlt_migration_guide.md
│   ├── analysis/                # Analysis documentation
│   │   ├── dim_fde_dlt_analysis.md
│   │   └── workflow_dlt_analysis.md
│   └── investigations/          # Investigation reports
│       ├── DATA_LOSS_INVESTIGATION_REPORT.md
│       ├── FIX_FIVETRAN_PK_CONFIG.md
│       └── SOLUTION_RESET_TABLE.md
│
├── scripts/                     # Python scripts organized by purpose
│   ├── analysis/                # Workflow & cost analysis
│   │   ├── analyze_all_workflows.py
│   │   ├── analyze_rds_workflow.py
│   │   ├── analyze_table_impact.py
│   │   └── cost_analysis.py
│   ├── audit/                   # Workspace auditing tools
│   │   ├── workspace_audit.py
│   │   ├── workspace_audit_v2.py
│   │   ├── notebook_audit.py
│   │   ├── quick_audit.py
│   │   └── top_notebook_creators.py
│   ├── validation/              # Data validation & checks
│   │   ├── check_actual_row_state.py
│   │   ├── check_all_rows.py
│   │   ├── check_hidden_rows.py
│   │   ├── check_pk_value.py
│   │   ├── check_table_stats.py
│   │   └── check_workflows_pipelines.py
│   ├── investigation/           # Debugging & investigation
│   │   ├── investigate_dim_fde.py
│   │   ├── investigate_oct13_update.py
│   │   ├── investigate_sync_failure.py
│   │   └── query_deleted_rows.py
│   ├── pipeline/                # DLT pipeline code
│   │   ├── dlt_fde_pipeline.py
│   │   └── validate_dlt_output.py
│   ├── testing/                 # Connection & consistency tests
│   │   ├── test_connection.py
│   │   └── test_pk_consistency.py
│   └── utils/                   # Utility scripts
│       ├── get_table_history.py
│       └── get_table_history_json.py
│
├── data/                        # Data files (GITIGNORED - LARGE FILES!)
│   ├── samples/                 # Sample data
│   │   └── databricks_sample_pks.txt
│   └── exports/                 # Exported data (JSON, CSV, etc.)
│       └── enterprise_property_history_20days.json
│
├── results/                     # Script outputs (GITIGNORED)
│   ├── audit_results/           # Audit reports
│   └── logs/                    # Execution logs
│
└── .claude/                     # Claude Code configuration
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Databricks workspace access
- Databricks CLI installed
- Git

### 2. Setup

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Credentials

**IMPORTANT**: Never commit your credentials to Git!

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Copy environment template
cp .env.example config/.env

# Copy Databricks config template
cp config/.databrickscfg.example config/.databrickscfg

# Edit the files and add your actual credentials
# config/.env - Add your Databricks host and token
# config/.databrickscfg - Add your Databricks CLI config
```

Your `config/.env` should look like:
```bash
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi1234567890abcdef
```

Your `config/.databrickscfg` should look like:
```ini
[DEFAULT]
host = https://dbc-xxxxx.cloud.databricks.com
token = dapi1234567890abcdef
```

### 4. Verify Connection

```bash
python scripts/testing/test_connection.py
```

## Common Tasks

### Running a Workspace Audit

```bash
python scripts/audit/workspace_audit.py
# Results saved to: results/audit_results/audit_report_[timestamp].txt
```

### Analyzing Workflows

```bash
python scripts/analysis/analyze_all_workflows.py
```

### Validating Data

```bash
# Check table statistics
python scripts/validation/check_table_stats.py

# Validate primary keys
python scripts/validation/check_pk_value.py

# Check for hidden/deleted rows
python scripts/validation/check_hidden_rows.py
```

### Cost Analysis

```bash
python scripts/analysis/cost_analysis.py
```

## Security Best Practices

### Sensitive Files Protection

This project is configured to **protect sensitive information**:

- **`config/` directory** - Contains all credentials (fully gitignored)
- **`.env` file** - Environment variables with API tokens (gitignored)
- **`.databrickscfg` file** - Databricks CLI credentials (gitignored)
- **`data/exports/` directory** - Large data exports (gitignored)
- **`results/` directory** - Script outputs that may contain sensitive data (gitignored)

### Before Committing

**ALWAYS check** that you're not committing sensitive files:

```bash
# Check what will be committed
git status

# Verify no sensitive files are staged
git diff --cached

# Never commit these files:
# - config/.env
# - config/.databrickscfg
# - Any file containing API tokens or passwords
```

### What's Safe to Commit

You can safely commit:
- All Python scripts in `scripts/`
- Documentation in `docs/`
- `.env.example` and `.databrickscfg.example` (templates only)
- `requirements.txt`
- `README.md` and other documentation
- `.gitignore` file

## Documentation

### Project Setup & Workflow
- [**Daily Workflow**](docs/DAILY_WORKFLOW.md) - **START HERE EACH DAY** - Branch management guide
- [Git Worktree Workflow](docs/GIT_WORKTREE_WORKFLOW.md) - Multi-branch development workflow
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Detailed structure documentation
- [Audit README](docs/AUDIT_README.md) - Workspace audit tool guide

### Migration Guides
- [00_RDS DLT Migration Guide](docs/migration/00_rds_dlt_migration_guide.md) - Complete 8-12 week migration plan
- [Dim FDE DLT Analysis](docs/analysis/dim_fde_dlt_analysis.md) - Technical analysis of FDE table migration
- [Workflow DLT Analysis](docs/analysis/workflow_dlt_analysis.md) - Workflow-level migration analysis

### Investigation Reports
- [Data Loss Investigation](docs/investigations/DATA_LOSS_INVESTIGATION_REPORT.md)
- [Fix Fivetran PK Config](docs/investigations/FIX_FIVETRAN_PK_CONFIG.md)
- [Solution: Reset Table](docs/investigations/SOLUTION_RESET_TABLE.md)

## Script Categories

### Analysis Scripts (`scripts/analysis/`)
Analyze workflows, costs, and table impacts.

**Key scripts:**
- `analyze_all_workflows.py` - Analyze all Databricks workflows
- `cost_analysis.py` - Estimate compute costs
- `analyze_table_impact.py` - Understand table dependencies

### Audit Scripts (`scripts/audit/`)
Audit workspace resources to identify unused assets.

**Key scripts:**
- `workspace_audit.py` - Comprehensive workspace audit
- `quick_audit.py` - Fast audit for quick checks
- `notebook_audit.py` - Analyze notebook usage

**Features:**
- Identify inactive jobs (not run in 90+ days)
- Find unused notebooks
- Analyze cluster utilization
- Generate detailed reports

### Validation Scripts (`scripts/validation/`)
Validate data integrity and consistency.

**Key scripts:**
- `check_table_stats.py` - Table statistics and health checks
- `check_pk_value.py` - Primary key validation
- `check_all_rows.py` - Row count validation
- `check_hidden_rows.py` - Detect soft-deleted rows

### Investigation Scripts (`scripts/investigation/`)
Debug and investigate data issues.

**Key scripts:**
- `investigate_sync_failure.py` - Debug sync failures
- `query_deleted_rows.py` - Find deleted/missing data
- `investigate_dim_fde.py` - Investigate FDE table issues

### Pipeline Scripts (`scripts/pipeline/`)
Delta Live Tables pipeline code and validation.

**Key scripts:**
- `dlt_fde_pipeline.py` - Main DLT pipeline for FDE migration
- `validate_dlt_output.py` - Validate DLT pipeline outputs

### Testing Scripts (`scripts/testing/`)
Test connections and data consistency.

**Key scripts:**
- `test_connection.py` - Test Databricks connectivity
- `test_pk_consistency.py` - Test primary key consistency

### Utility Scripts (`scripts/utils/`)
Helper utilities for common tasks.

**Key scripts:**
- `get_table_history.py` - Retrieve table history
- `get_table_history_json.py` - Export table history as JSON

## Development Workflow

### Starting Your Day (IMPORTANT!)

**Always start your work session with proper branch management:**

#### Option 1: Use Claude Code (Recommended)
```
/start-work
```
Claude will guide you through:
- Checking your current branch
- Helping you continue existing work or create a new feature branch
- Setting up worktrees for new features

#### Option 2: Use the Shell Script
```bash
./start-day.sh
```

**See**: [docs/DAILY_WORKFLOW.md](docs/DAILY_WORKFLOW.md) for complete daily workflow guide.

### Git Worktree Setup

This project uses **git worktrees** for efficient multi-branch development. This allows you to work on multiple branches simultaneously without switching contexts.

**See**: [docs/GIT_WORKTREE_WORKFLOW.md](docs/GIT_WORKTREE_WORKFLOW.md) for complete worktree documentation.

Quick start:
```bash
# Create a feature branch worktree
git worktree add -b feature/your-feature ../rds_databricks_claude-feature

# List all worktrees
git worktree list

# Work in the new worktree
cd ../rds_databricks_claude-feature
```

### Making Changes

1. **Start your day**: Run `/start-work` or `./start-day.sh`
2. **Create branch**: Always use feature branches for new work
3. **Make changes**: Edit scripts or documentation
4. **Test thoroughly**: Run validation and tests
5. **Commit frequently**: Clear, descriptive commit messages
6. **Merge to main**: When feature is complete

### Adding New Scripts

When adding new scripts:

1. Place in appropriate `scripts/` subdirectory
2. Add documentation at the top of the file
3. Update this README if adding a major new feature
4. Ensure script loads credentials from `config/.env`

Example script template:
```python
#!/usr/bin/env python3
"""
Script Name: my_new_script.py
Purpose: Brief description of what this script does
Usage: python scripts/category/my_new_script.py
"""

import os
from dotenv import load_dotenv

# Load credentials from config/.env
load_dotenv('config/.env')

DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')

# Your code here
```

## Troubleshooting

### "databricks: command not found"
```bash
pip install databricks-cli
```

### "Authentication errors"
```bash
# Verify your credentials in config/.databrickscfg
databricks workspace ls /
```

### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Scripts can't find config files
```bash
# Ensure config files are in the right location
ls -la config/

# Should show:
# config/.env
# config/.databrickscfg
```

## Contributing

When contributing to this project:

1. **Never commit credentials** - Double-check before committing
2. **Test your changes** - Run scripts to ensure they work
3. **Update documentation** - Keep README and docs in sync
4. **Follow structure** - Put files in the appropriate directories
5. **Use clear commit messages** - Explain what and why

## Resources

- [Databricks CLI Documentation](https://docs.databricks.com/dev-tools/cli/index.html)
- [Delta Live Tables Documentation](https://docs.databricks.com/delta-live-tables/index.html)
- [Databricks Best Practices](https://docs.databricks.com/delta-live-tables/best-practices.html)

## Contact

**Project Owner**: dane@snappt.com

For issues or questions, refer to the documentation or contact the project owner.

---

**Last Updated**: 2024-10-29
**Status**: Active Development
