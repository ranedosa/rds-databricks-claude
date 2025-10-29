#!/bin/bash
# Quick Start Script for 00_RDS DLT Migration
# Run this to set up your development environment

set -e  # Exit on error

echo "=========================================="
echo "00_RDS DLT Migration - Quick Start"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create workspace directories
echo -e "${BLUE}Step 1: Creating workspace directories...${NC}"
mkdir -p notebooks
mkdir -p monitoring
mkdir -p tests
mkdir -p docs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 2: Export current notebooks for analysis
echo -e "${BLUE}Step 2: Exporting current notebooks from Databricks...${NC}"
echo "This will help us understand what each task does."
echo ""

NOTEBOOKS=(
  "snappt/unity_fde:notebooks/unity_fde.py"
  "snappt/dash_fde_iv_submissions:notebooks/income_verification.sql"
  "snappt/iv_fde_ax:notebooks/iv_fde_ax.sql"
  "snappt/iv_master_results:notebooks/iv_master_results.sql"
  "snappt/unity_av_fde:notebooks/unity_av_fde.sql"
  "snappt/roi_fraud_reduction_submission_level:notebooks/roi_fraud_reduction.sql"
)

for notebook in "${NOTEBOOKS[@]}"; do
  IFS=':' read -r source dest <<< "$notebook"
  echo "  Exporting: $source"
  databricks workspace export "/Repos/dbx_git/dbx/$source" \
    --profile m2m \
    --format SOURCE > "$dest" 2>/dev/null || echo "    (Note: May not exist or require different path)"
done
echo -e "${GREEN}✓ Notebooks exported to ./notebooks/${NC}"
echo ""

# Step 3: Test existing DLT code
echo -e "${BLUE}Step 3: Validating existing DLT pipeline code...${NC}"
if [ -f "dlt_fde_pipeline.py" ]; then
  echo -e "${GREEN}✓ Found dlt_fde_pipeline.py${NC}"
  echo "  This contains the unity_fde DLT code (Bronze/Silver/Gold layers)"
  echo ""

  # Show summary
  echo "  Pipeline contains:"
  grep -E "^def (bronze_|silver_|dim_)" dlt_fde_pipeline.py | sed 's/def /    - /' | sed 's/(.*://'
  echo ""
else
  echo -e "${YELLOW}⚠ dlt_fde_pipeline.py not found in current directory${NC}"
  echo "  Expected location: ./dlt_fde_pipeline.py"
  echo ""
fi

# Step 4: Create monitoring notebook
echo -e "${BLUE}Step 4: Creating monitoring notebook...${NC}"
cat > monitoring/compare_outputs.py << 'EOF'
# Databricks notebook source
# MAGIC %md
# MAGIC # DLT Output Validation
# MAGIC
# MAGIC Compare DLT pipeline output with production tables.
# MAGIC Run this after each DLT pipeline execution during parallel testing.

# COMMAND ----------

# DBTITLE 1,Configuration
production_table = "product.fde.dim_fde"
dlt_table = "team_sandbox.data_engineering.dlt_test_dim_fde"

# COMMAND ----------

# DBTITLE 1,Schema Comparison
print("=" * 80)
print("SCHEMA COMPARISON")
print("=" * 80)

prod_schema = spark.table(production_table).schema
dev_schema = spark.table(dlt_table).schema

prod_cols = set([f.name for f in prod_schema.fields])
dev_cols = set([f.name for f in dev_schema.fields])

missing = prod_cols - dev_cols
extra = dev_cols - prod_cols

if missing:
    print(f"❌ Missing columns in DLT: {missing}")
else:
    print("✅ No missing columns")

if extra:
    print(f"⚠️  Extra columns in DLT: {extra}")
else:
    print("✅ No extra columns")

if not missing and not extra:
    print("✅ Schemas match perfectly!")

# COMMAND ----------

# DBTITLE 1,Row Count Comparison
print("=" * 80)
print("ROW COUNT COMPARISON")
print("=" * 80)

prod_count = spark.table(production_table).count()
dev_count = spark.table(dlt_table).count()

print(f"Production: {prod_count:,}")
print(f"DLT:        {dev_count:,}")
print(f"Difference: {abs(prod_count - dev_count):,}")

if prod_count == dev_count:
    print("✅ Row counts match!")
else:
    pct_diff = abs(prod_count - dev_count) / prod_count * 100
    print(f"❌ Row counts differ by {pct_diff:.2f}%")

# COMMAND ----------

# DBTITLE 1,Key Statistics Comparison
print("=" * 80)
print("KEY STATISTICS COMPARISON")
print("=" * 80)

comparison_sql = f"""
SELECT
  'Production' as source,
  COUNT(*) as total_rows,
  COUNT(DISTINCT property_id) as unique_properties,
  COUNT(DISTINCT submission_id) as unique_submissions,
  COUNT(DISTINCT document_id) as unique_documents,
  MIN(submission_datetime) as earliest_submission,
  MAX(submission_datetime) as latest_submission
FROM {production_table}

UNION ALL

SELECT
  'DLT' as source,
  COUNT(*) as total_rows,
  COUNT(DISTINCT property_id) as unique_properties,
  COUNT(DISTINCT submission_id) as unique_submissions,
  COUNT(DISTINCT document_id) as unique_documents,
  MIN(submission_datetime) as earliest_submission,
  MAX(submission_datetime) as latest_submission
FROM {dlt_table}
"""

spark.sql(comparison_sql).show(truncate=False)

# COMMAND ----------

# DBTITLE 1,Missing Records Analysis
print("=" * 80)
print("MISSING RECORDS ANALYSIS")
print("=" * 80)

# Records in production but not in DLT
missing_in_dlt = spark.sql(f"""
SELECT COUNT(*) as cnt
FROM {production_table} p
LEFT ANTI JOIN {dlt_table} d
  ON p.property_id = d.property_id
  AND p.submission_id = d.submission_id
  AND COALESCE(p.document_id, 'NULL') = COALESCE(d.document_id, 'NULL')
""")

missing_count = missing_in_dlt.first()['cnt']
print(f"Records in Production but not in DLT: {missing_count:,}")

# Records in DLT but not in production
extra_in_dlt = spark.sql(f"""
SELECT COUNT(*) as cnt
FROM {dlt_table} d
LEFT ANTI JOIN {production_table} p
  ON p.property_id = d.property_id
  AND p.submission_id = d.submission_id
  AND COALESCE(p.document_id, 'NULL') = COALESCE(d.document_id, 'NULL')
""")

extra_count = extra_in_dlt.first()['cnt']
print(f"Records in DLT but not in Production: {extra_count:,}")

if missing_count == 0 and extra_count == 0:
    print("✅ All records match perfectly!")
else:
    print("❌ Records do not match - investigation needed")

# COMMAND ----------

# DBTITLE 1,Summary
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

schema_match = len(missing) == 0 and len(extra) == 0
count_match = prod_count == dev_count
records_match = missing_count == 0 and extra_count == 0

print(f"Schema Match:  {'✅ PASS' if schema_match else '❌ FAIL'}")
print(f"Count Match:   {'✅ PASS' if count_match else '❌ FAIL'}")
print(f"Records Match: {'✅ PASS' if records_match else '❌ FAIL'}")
print()

if schema_match and count_match and records_match:
    print("🎉 ALL VALIDATIONS PASSED!")
    print("DLT output matches production perfectly.")
else:
    print("⚠️  VALIDATIONS FAILED")
    print("Review the differences above and investigate root cause.")
EOF

echo -e "${GREEN}✓ Monitoring notebook created at monitoring/compare_outputs.py${NC}"
echo ""

# Step 5: Create checklist
echo -e "${BLUE}Step 5: Creating project checklist...${NC}"
cat > CHECKLIST.md << 'EOF'
# 00_RDS DLT Migration Checklist

## Week 1: Preparation
- [ ] Review migration guide (`00_rds_dlt_migration_guide.md`)
- [ ] Review analysis document (`workflow_dlt_analysis.md`)
- [ ] Set up development environment
- [ ] Export all notebooks (✓ Done by quick_start.sh)
- [ ] Analyze each notebook to understand outputs
- [ ] Create feature branch in Git
- [ ] Get team alignment and approval

## Week 2: Deploy Development Pipeline
- [ ] Create DLT pipeline in Databricks UI (`00_RDS_FDE_Pipeline_DEV`)
- [ ] Configure pipeline settings (see guide for details)
- [ ] Upload dlt_fde_pipeline.py to workspace
- [ ] Run first test in sandbox
- [ ] Validate output tables created
- [ ] Run monitoring/compare_outputs.py notebook

## Week 3: Parallel Testing
- [ ] Schedule DLT pipeline (offset from production)
- [ ] Run for 1 week in parallel
- [ ] Monitor daily with compare_outputs.py
- [ ] Log any differences found
- [ ] Verify stability

## Week 4: Performance Optimization
- [ ] Analyze performance metrics
- [ ] Compare costs with current workflow
- [ ] Apply optimizations if needed
- [ ] Re-test and validate

## Week 5: Production Preparation
- [ ] Create production DLT pipeline
- [ ] Create new 00_RDS_v2 workflow
- [ ] Update downstream notebooks to use new tables
- [ ] Get stakeholder approval for cutover

## Weeks 6-11: Add Downstream Tables
- [ ] Add income_verification to DLT (weeks 6-7)
- [ ] Add iv_fde_ax to DLT (weeks 6-7)
- [ ] Add iv_master_results to DLT (weeks 8-9)
- [ ] Add unity_av_fde to DLT (weeks 8-9)
- [ ] Add roi_fraud_reduction to DLT (weeks 10-11)

## Week 12: Cutover
- [ ] Run final parallel validation
- [ ] Get final stakeholder approval
- [ ] Execute cutover plan
- [ ] Monitor first few production runs
- [ ] Archive old workflow
- [ ] Update documentation
- [ ] Celebrate success! 🎉

## Success Criteria
- [ ] Pipeline runs 4x daily successfully
- [ ] Output matches production exactly
- [ ] Performance equal or better
- [ ] Costs equal or lower
- [ ] All stakeholders satisfied
EOF

echo -e "${GREEN}✓ Checklist created at CHECKLIST.md${NC}"
echo ""

# Step 6: Summary
echo -e "${BLUE}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "📁 Files created:"
echo "  - ./notebooks/              (exported notebooks for analysis)"
echo "  - ./monitoring/             (validation notebooks)"
echo "  - ./CHECKLIST.md           (project checklist)"
echo ""
echo "📋 Next steps:"
echo "  1. Review CHECKLIST.md"
echo "  2. Read 00_rds_dlt_migration_guide.md"
echo "  3. Analyze exported notebooks in ./notebooks/"
echo "  4. Create feature branch: git checkout -b feature/00-rds-dlt-migration"
echo "  5. Review dlt_fde_pipeline.py (already has unity_fde code!)"
echo ""
echo "📚 Key documents:"
echo "  - 00_rds_dlt_migration_guide.md  (Step-by-step guide)"
echo "  - workflow_dlt_analysis.md       (Analysis of all workflows)"
echo "  - dim_fde_dlt_analysis.md        (Technical details)"
echo ""
echo -e "${GREEN}Ready to start! 🚀${NC}"
echo ""
