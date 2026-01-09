# 100 Largest Tables Analysis - December 20, 2025

## Summary

Successfully analyzed 200 tables across your Databricks workspace and identified the 100 largest by row count.

## Methodology

- **Approach**: Used row count as a proxy for table size (SELECT COUNT(*) on each table)
- **Catalogs Analyzed**: rds, crm, product, team_sandbox
- **Excluded**: __databricks_internal, tmp_enterprise_catalog, star, samples, system catalogs
- **Filtered Out**: Tables with "_fivetran" in the name
- **Analysis Time**: ~4 minutes to analyze 200 tables
- **Success Rate**: 100% (200 tables successfully analyzed)

## Top 10 Largest Tables (by row count)

| Rank | Table | Catalog | Schema | Row Count |
|------|-------|---------|--------|-----------|
| 1 | unity_fde | product | fde | 43,935,713 |
| 2 | unity_iv_fde_ax | product | iv | 23,620,699 |
| 3 | dim_av | product | av | 9,308,028 |
| 4 | purgedentities_bronze | crm | aln | 9,197,699 |
| 5 | unity_iv_master_results | product | iv | 8,868,341 |
| 6 | unity_iv_calculations | product | iv | 8,189,158 |
| 7 | properties_view_application_link_raw | crm | heap | 6,416,264 |
| 8 | sessions_raw | crm | heap | 5,967,397 |
| 9 | document_properties_training | rds | pg_rds_av_av | 5,599,956 |
| 10 | unity_agg_fde_iv_submissions | product | iv | 4,933,997 |

## Breakdown by Catalog (Top 100)

| Catalog | Number of Tables | Total Rows |
|---------|------------------|------------|
| product | 43 tables | ~140M rows |
| crm | 50 tables | ~68M rows |
| rds | 7 tables | ~6M rows |

## Key Findings

### Largest Tables by Domain

**Income Verification (product.iv)**
- unity_iv_fde_ax: 23.6M rows
- unity_iv_master_results: 8.9M rows
- unity_iv_calculations: 8.2M rows
- unity_agg_fde_iv_submissions: 4.9M rows
- unity_source_income_verification: 4.7M rows

**Fraud Detection Engine (product.fde)**
- unity_fde: 43.9M rows (LARGEST TABLE)
- unity_applicant_details: 4.9M rows
- unity_requests_clean: 4.7M rows

**Asset Verification (product.av)**
- dim_av: 9.3M rows
- raw_av2: 3,376 rows

**CRM/Heap Analytics (crm.heap)**
- properties_view_application_link_raw: 6.4M rows
- sessions_raw: 6.0M rows
- users_raw: 2.4M rows

**RDS (rds.pg_rds_av_av)**
- document_properties_training: 5.6M rows
- document_properties: (not in top 100)

### Small But Important Tables

Some critical tables have small row counts:
- crm.sfdc_dbx.new_properties_with_features: 7 rows
- crm.pendo tables: 4-7 rows each
- rds.pg_rds_av_av.audit_decision_codes: 3 rows

## Files Generated

1. **largest_tables_by_rows_top100.csv** - Top 100 tables with row counts
2. **all_table_row_counts.csv** - All 200 analyzed tables with row counts
3. **find_largest_tables_v3.py** - Python script used for analysis
4. **SUMMARY.md** - This file

## Limitations

**Note**: Row count is a proxy for table size but not perfect:
- Tables with large VARCHAR/BINARY columns may have fewer rows but use more storage
- Compressed Delta tables may have different storage footprints
- Partitioned tables may show misleading counts

**Better Approach for Future**:
- Query `system.information_schema.table_storage` for actual bytes (if available in your Databricks version)
- Use `DESCRIBE DETAIL` on Delta tables to get `sizeInBytes` (requires table-by-table queries)

## Recommendations

### Storage Optimization Candidates

**Product Catalog** (43 large tables):
- Consider archiving/partitioning old IV/FDE submissions
- Review if all unity_* tables are actively used
- Check if temp_* tables can be cleaned up

**CRM/Heap** (50 tables):
- heap.*_raw tables are large event logs - consider:
  - Archiving old events
  - Implementing retention policies
  - Using incremental processing

**ALN Bronze Tables** (crm.aln):
- purgedentities_bronze: 9.2M rows
- activerowversion_bronze: 859 rows
- Consider if bronze layer needs all historical data

### Tables to Investigate

1. **product.fde.unity_fde** - 43.9M rows (by far the largest)
   - What's the growth rate?
   - Is there a retention policy?
   - Can it be partitioned/archived?

2. **product.iv.unity_iv_fde_ax** - 23.6M rows
   - Second largest
   - Joins/denormalization opportunity?

3. **Temp Tables** - Several temp_mim* tables exist
   - Can these be cleaned up?
   - temp_mim10202025_corrected_document_upload: 3,325 rows
   - temp_mim10172025_corrected_document_upload: 3,113 rows

## Next Steps

1. ✅ Identified 100 largest tables by row count
2. ⏳ **TODO**: Get actual storage sizes in GB (requires different approach)
3. ⏳ **TODO**: Analyze growth trends over time
4. ⏳ **TODO**: Identify archival candidates
5. ⏳ **TODO**: Implement retention policies

## Questions for Stakeholders

- What's the retention policy for IV submissions?
- Can FDE data older than X months be archived?
- Are all heap analytics raw tables needed indefinitely?
- Should we implement automatic cleanup for temp_* tables?

---

**Analysis Date**: December 20, 2025
**Analyst**: Claude Code
**Script**: find_largest_tables_v3.py
**Runtime**: ~4 minutes for 200 tables
