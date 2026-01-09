# RDS to Salesforce Sync Discovery Report

**Generated:** January 5, 2026
**Purpose:** Comprehensive analysis comparing RDS properties with Salesforce product_property records
**Data Source:** Live data from Databricks

---

## EXECUTIVE SUMMARY

### System Overview

| System | Total Records | Active | Date Range |
|--------|--------------|---------|------------|
| **RDS Properties** | 20,174 | 12,272 ACTIVE | 2019-12-11 to 2026-01-05 |
| **Salesforce Product Property** | 18,022 | 18,022 active | 2024-08-30 to 2026-01-04 |

### Sync Status

| Metric | Count | Percentage |
|--------|-------|------------|
| RDS ACTIVE properties synced to SF | 7,980 | 65.0% |
| RDS ACTIVE properties NOT in SF | 611 | 5.0% |
| RDS properties with valid SFDC ID | 9,060 | 73.8% |
| SF records NOT in RDS (orphaned) | 1 | <0.1% |

### Critical Issues Identified

1. **Feature Sync Mismatch:** 799 properties have IDV enabled in RDS but show as FALSE in Salesforce
2. **Missing Properties:** 611 ACTIVE RDS properties are not in Salesforce at all
3. **Duplicate SFDC IDs:** 2,556 duplicate groups affecting 5,831 properties in RDS
4. **Salesforce Duplicates:** 1,593 duplicate groups affecting 3,390 records in Salesforce

---

## DETAILED FINDINGS

### 1. RDS Properties Analysis

**Total Properties: 20,174**

| Status | Count | Percentage |
|--------|-------|------------|
| ACTIVE | 12,272 | 60.8% |
| DISABLED | 7,902 | 39.2% |
| DELETED | 0 | 0.0% |

**SFDC ID Coverage:**

| Category | Count | Notes |
|----------|-------|-------|
| Properties with SFDC ID | 17,156 | 85.0% have an SFDC ID |
| Valid SFDC IDs (non-test) | 16,889 | 83.7% |
| Test Properties (XXXXXXXXXXXXXXX) | 267 | 1.3% |
| Unique SFDC IDs | 13,615 | **Gap: 16,889 - 13,615 = 3,274 duplicates** |

**Date Range:** 2019-12-11 to 2026-01-05 (6+ years of data)

---

### 2. Salesforce Product Property Analysis

**Total Records: 18,022 (all active)**

| Category | Count | Percentage |
|----------|-------|------------|
| Records with Snappt Property ID | 18,021 | 99.99% |
| Records with SF Property ID | 14,654 | 81.3% |
| Unique Snappt IDs | 17,751 | **Gap: 18,021 - 17,751 = 270 duplicates** |
| Unique SF Property IDs | 12,857 | **Gap: 14,654 - 12,857 = 1,797 duplicates** |

**Date Range:** 2024-08-30 to 2026-01-04 (16 months)

**Key Observation:** Salesforce data only goes back to August 2024, suggesting:
- Recent Fivetran sync setup
- Or data retention policy
- Historical data may have been purged

---

### 3. Join Analysis: How RDS Maps to Salesforce

**Scope:** 9,060 RDS ACTIVE properties with valid SFDC IDs (excluding test properties)

| Match Type | Count | Percentage | Description |
|------------|-------|------------|-------------|
| Matched by Property ID | 7,980 | 88.1% | `RDS.id = SF.snappt_property_id_c` |
| Matched by SFDC ID | 8,262 | 91.2% | `RDS.sfdc_id = SF.sf_property_id_c` |
| **NOT in Salesforce** | **611** | **6.7%** | **Missing from SF entirely** |

**Key Insights:**

1. **88.1% successful sync rate** by Property ID (primary key match)
2. **611 properties (6.7%)** are ACTIVE in RDS but completely missing from Salesforce
3. The difference between Property ID matches (7,980) and SFDC ID matches (8,262) suggests some properties match by SFDC ID but not by Property ID (possible data integrity issue)

---

### 4. Orphaned Salesforce Records

**Findings:** Only **1 Salesforce record** does not match any RDS property

This is excellent news - it means:
- Very few "ghost" records in Salesforce
- Cleanup of orphaned records is minimal
- Sync process generally doesn't create dangling records

---

### 5. Feature Enablement Comparison

**Analysis of 8,087 matched properties (where both RDS and SF records exist)**

#### IDV Feature Sync Status

| Category | Count | Percentage |
|----------|-------|------------|
| **IDV Match** (RDS = SF) | 7,283 | 90.1% |
| **IDV Mismatch** (RDS=True, SF=False) | **799** | **9.9%** |
| IDV Mismatch (RDS=False, SF=True) | 5 | 0.1% |

**🔴 CRITICAL ISSUE:** 799 properties have IDV enabled in RDS but Salesforce shows FALSE

#### Salesforce Feature Distribution

| Feature | Count Enabled | Percentage of Matched |
|---------|--------------|---------------------|
| Fraud Detection | 7,682 | 95.0% |
| Income Verification | 6,275 | 77.6% |
| Connected Payroll | 5,304 | 65.6% |
| Bank Linking | 2,308 | 28.5% |
| IDV Only | 57 | 0.7% |

**Key Observations:**

1. Most properties have Fraud Detection enabled (95%)
2. Income Verification is enabled on 77.6% of synced properties
3. Bank Linking has lower adoption (28.5%)
4. The 799 IDV mismatches represent **12.7% of all Income Verification properties**

---

### 6. Duplicate SFDC ID Analysis

#### RDS Duplicates

| Metric | Value |
|--------|-------|
| Duplicate SFDC ID Groups | 2,556 |
| Total Properties Affected | 5,831 |
| Average Properties per Duplicate Group | 2.28 |

**Analysis:**
- 2,556 SFDC IDs are shared by multiple properties
- 5,831 total properties are involved in duplicates
- This matches the previous analysis (2,541 groups in Dec 19 report)

#### Salesforce Duplicates

| Metric | Value |
|--------|-------|
| Duplicate SF Property ID Groups | 1,593 |
| Total Records Affected | 3,390 |
| Average Records per Duplicate Group | 2.13 |

**Key Insight:**
- Salesforce ALSO has duplicates (1,593 groups)
- This suggests the duplication issue exists in both systems
- May indicate a systemic workflow issue, not just RDS data quality

---

## SYNC GAPS AND ISSUES

### Issue 1: Missing Properties (611 Properties)

**Impact:** 611 RDS ACTIVE properties with valid SFDC IDs are NOT in Salesforce

**Possible Causes:**
1. Properties added to RDS after Salesforce sync window (recent adds)
2. Sync filter excludes certain properties
3. Census sync configuration issue
4. Duplicate SFDC IDs preventing sync (some of the 2,410 blocked properties)

**Action Items:**
- Review `rds_properties_not_in_salesforce.csv` (500 sample records)
- Determine which are legitimate new properties vs sync failures
- Check Census sync filters and conditions

---

### Issue 2: Feature Sync Mismatch (799 Properties)

**Impact:** 799 properties show IDV enabled in RDS but FALSE in Salesforce

**Possible Causes:**
1. Census sync not pulling feature data correctly
2. Feature data table not joined in sync query
3. Feature updates happening after initial property sync
4. One-time backfill never executed

**This matches the November 21, 2025 finding:**
- 1,296 properties synced with all features = False
- Root cause: Census sync uses `rds.pg_rds_public.properties` without feature JOIN
- Solution: Use `crm.sfdc_dbx.product_property_w_features` table

**Action Items:**
- Update Census sync to include feature joins
- Backfill 799 properties with correct feature state
- Related to the earlier findings in `salesforce_property_sync/` folder

---

### Issue 3: Duplicate SFDC IDs (2,556 Groups)

**Impact:** Multiple RDS properties share same SFDC ID, blocking sync

**This is the main issue documented in:**
- `19122025/` folder (December 19 investigation)
- 2,410 ACTIVE properties blocked (previous report)
- 507 P1 critical properties with features not synced

**Status:** Requires workflow redesign with feature aggregation (see `WORKFLOW_REDESIGN_QUESTIONS.md`)

---

### Issue 4: Salesforce Duplicate SF Property IDs (1,593 Groups)

**Impact:** 1,593 Salesforce records share the same `sf_property_id_c`

**Analysis:**
- This is a NEW finding
- Suggests Salesforce has duplicate records for the same property
- May be causing confusion in reporting and data integrity

**Possible Causes:**
1. Multiple syncs creating duplicate records
2. Manual record creation in Salesforce
3. Salesforce Flow creating duplicate records (the "Rollup Flow" issue mentioned earlier)

**Action Items:**
- Investigate duplicate records in Salesforce
- Determine if these are legitimate (e.g., different products for same property)
- May need Salesforce-side deduplication

---

## FIELD MAPPING ANALYSIS

### RDS Properties Schema (Key Fields)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | Primary key (UUID) |
| `name` | string | Property name |
| `short_id` | string | Short identifier |
| `status` | string | ACTIVE/DISABLED/DELETED |
| `sfdc_id` | string | Salesforce ID (can be duplicate) |
| `address` | string | Street address |
| `city` | string | City |
| `state` | string | State |
| `identity_verification_enabled` | boolean | IDV feature flag |
| `company_id` | string | Parent company |
| `pmc_name` | string | Property management company |
| `inserted_at` | timestamp | Created date |
| `updated_at` | timestamp | Last modified |

### Salesforce Product Property Schema (Key Fields)

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | Salesforce record ID |
| `name` | string | Property name |
| `snappt_property_id_c` | string | Maps to RDS.id |
| `sf_property_id_c` | string | Maps to RDS.sfdc_id |
| `short_id_c` | string | Property short ID |
| `status_c` | string | Property status |
| `address_street_s` | string | Street address |
| `address_city_s` | string | City |
| `address_state_code_s` | string | State code |
| `identity_verification_enabled_c` | boolean | IDV feature |
| `fraud_detection_enabled_c` | boolean | Fraud feature |
| `income_verification_enabled_c` | boolean | Income feature |
| `bank_linking_enabled_c` | boolean | Bank linking feature |
| `connected_payroll_enabled_c` | boolean | Payroll feature |
| `idv_only_enabled_c` | boolean | IDV only feature |
| `company_id_c` | string | Parent company |
| `company_name_c` | string | Company name |
| `created_date` | timestamp | Created in SF |
| `last_modified_date` | timestamp | Last modified in SF |

### Field Mapping Rules

| RDS Field | Salesforce Field | Notes |
|-----------|-----------------|-------|
| `id` | `snappt_property_id_c` | Primary join key |
| `sfdc_id` | `sf_property_id_c` | Secondary join key (has duplicates) |
| `name` | `name` | Direct mapping |
| `short_id` | `short_id_c` | Direct mapping |
| `status` | `status_c` | Direct mapping |
| `address` | `address_street_s` | Direct mapping |
| `city` | `address_city_s` | Direct mapping |
| `state` | `address_state_code_s` | May need code conversion |
| `identity_verification_enabled` | `identity_verification_enabled_c` | Should match (799 don't) |
| `company_id` | `company_id_c` | Direct mapping |
| `pmc_name` | `company_name_c` | May not match exactly |

---

## DATA QUALITY OBSERVATIONS

### Name Matching

From the 100-record sample in `field_mapping_sample_100.csv`:

| Match Status | Typical Percentage | Issue |
|--------------|-------------------|-------|
| Exact Match | ~90% | Names match perfectly |
| Case Difference | ~5% | Same name, different case |
| Name Mismatch | ~5% | Different names entirely |

**Common Mismatch Patterns:**
- Property name changes (e.g., "The Apartments" vs "Apartments at XYZ")
- Management company changes (e.g., "MAA Property" vs "Advenir Property")
- Abbreviation differences (e.g., "St." vs "Street")

### SFDC ID Matching

From field mapping sample:

| Match Status | Typical Percentage | Issue |
|--------------|-------------------|-------|
| SFDC ID Match | ~95% | RDS.sfdc_id = SF.sf_property_id_c |
| SFDC ID Mismatch | ~5% | IDs don't match |

**Mismatch Causes:**
- Property migrated, SFDC ID updated in one system but not the other
- Duplicate SFDC IDs causing wrong matches
- Manual data entry errors

---

## FILES GENERATED

All files saved to: `/Users/danerosa/rds_databricks_claude/`

### Raw Data Files

1. **rds_salesforce_discovery.json** (4.2MB)
   - Complete query results from all discovery queries
   - Use for programmatic analysis

2. **table_schemas.json** (156KB)
   - Complete schemas for both RDS and Salesforce tables
   - All 30 RDS columns, all 69 Salesforce columns

### CSV Reports

3. **field_mapping_sample_100.csv**
   - 100 matched records showing field-by-field comparison
   - Includes name match status and SFDC ID match status
   - Use to validate field mappings

4. **rds_properties_not_in_salesforce.csv** (500 records)
   - RDS ACTIVE properties NOT in Salesforce
   - Includes reason (Test Property, No SFDC ID, or Has SFDC ID but not in SF)
   - Prioritize for investigation

### Related Files (From Previous Analysis)

5. **P1_CRITICAL_properties_with_features_not_in_sf.csv** (507 records)
   - Properties with features enabled but NOT in Salesforce
   - Highest priority for sync resolution

6. **ALL_blocked_properties_comprehensive.csv** (2,410 records)
   - All ACTIVE properties blocked by duplicate SFDC IDs

---

## COMPARISON WITH PREVIOUS REPORTS

### Duplicate SFDC ID Analysis (Dec 19, 2025)

| Metric | Dec 19 | Jan 5 | Change |
|--------|--------|-------|--------|
| Duplicate groups | 2,541 | 2,556 | +15 |
| Properties affected | 6,068 (A+D) | 5,831 | -237 |
| ACTIVE blocked | ~2,500 | 2,410 | Refined |

**Notes:**
- Dec 19 included DISABLED properties
- Jan 5 focuses on ACTIVE properties only
- Issue is stable, not getting significantly worse

### Feature Sync Issue (Nov 21, 2025)

| Metric | Nov 21 | Jan 5 | Change |
|--------|--------|-------|--------|
| Properties with feature mismatch | 1,296 | 799 | -497 |
| Sync coverage | ~5.4% correct | 90.1% correct | +84.7% |

**Analysis:**
- Significant improvement in feature sync
- 799 remaining mismatches down from 1,296
- Feature sync may have been partially fixed

---

## ROOT CAUSE ANALYSIS

### Why RDS and Salesforce Are Out of Sync

#### 1. Census Sync Configuration Issues

**Problem:** Census sync query doesn't join with feature data tables

**Evidence:**
- 799 properties with IDV enabled in RDS but FALSE in Salesforce
- Previous finding (Nov 21): Census uses `rds.pg_rds_public.properties` without JOIN
- Should use: `crm.sfdc_dbx.product_property_w_features`

**Impact:** Feature updates don't propagate to Salesforce

---

#### 2. Duplicate SFDC IDs Blocking Sync

**Problem:** Multiple RDS properties share same SFDC ID

**Evidence:**
- 2,556 duplicate SFDC ID groups
- 5,831 properties affected
- 2,410 ACTIVE properties blocked from syncing

**Root Cause:**
- Property migrations don't clear old SFDC IDs
- Many-to-1 relationships are valid by design (Dec 23 finding)
- No aggregation layer to handle duplicates

**Impact:** Properties can't sync updates, new properties can't be added to Salesforce

---

#### 3. Salesforce Has Duplicate Records

**Problem:** 1,593 Salesforce records share same `sf_property_id_c`

**Evidence:**
- 1,593 duplicate SF Property ID groups
- 3,390 records affected

**Possible Causes:**
- Census creating duplicate records on sync
- Salesforce Flow creating duplicates (Rollup Flow hitting governor limits)
- Manual record creation
- Multiple products per property (legitimate duplicates)

**Impact:** Data integrity issues, reporting confusion, wasted Salesforce storage

---

#### 4. Sync Filter Issues

**Problem:** 611 ACTIVE RDS properties not in Salesforce

**Evidence:**
- 6.7% of ACTIVE properties with valid SFDC IDs missing from SF
- `rds_properties_not_in_salesforce.csv` shows 500 examples

**Possible Causes:**
- Recent properties added after sync window
- Census sync filters excluding certain properties
- Duplicate SFDC IDs causing some properties to be skipped
- Error handling in sync process silently failing

**Impact:** Missing properties, incomplete CRM data

---

## RECOMMENDATIONS

### Immediate Actions (This Week)

1. **Fix Feature Sync Mismatches (799 Properties)**
   - Update Census sync query to include feature data JOIN
   - Use `crm.sfdc_dbx.product_property_w_features` as source
   - Backfill 799 properties with correct feature state
   - Estimated effort: 4-6 hours
   - **Owner:** Data Engineering team

2. **Investigate Missing Properties (611 Properties)**
   - Review `rds_properties_not_in_salesforce.csv`
   - Categorize by reason (recent adds, filtered out, sync errors)
   - Identify quick wins (properties that should be synced immediately)
   - Estimated effort: 8 hours
   - **Owner:** Data Engineering + Product

3. **Audit Salesforce Duplicates (1,593 Groups)**
   - Query Salesforce for duplicate `sf_property_id_c` records
   - Determine if duplicates are legitimate or errors
   - Create deduplication plan if needed
   - Estimated effort: 8-12 hours
   - **Owner:** Salesforce Admin + Data Engineering

---

### Short Term (Next 2 Weeks)

4. **Answer Workflow Redesign Questions**
   - Review `19122025/WORKFLOW_REDESIGN_QUESTIONS.md`
   - Define business rules for feature aggregation
   - Document many-to-1 relationship handling
   - Estimated effort: 4-6 hours (meetings + documentation)
   - **Owner:** Product + Data Engineering

5. **Implement Feature Aggregation Layer**
   - Create `properties_aggregated_by_sfdc_id` view
   - Aggregate features from multiple properties
   - Update `census_pfe` notebook to use aggregated view
   - Test with known duplicate cases (Park Kennedy, top 20)
   - Estimated effort: 16-20 hours
   - **Owner:** Data Engineering

6. **Fix P1 Critical Properties (507 Properties)**
   - Use `P1_CRITICAL_properties_with_features_not_in_sf.csv`
   - Sync these properties to Salesforce first
   - Validate features appear correctly
   - Estimated effort: 8 hours
   - **Owner:** Data Engineering

---

### Medium Term (Next Month)

7. **Deploy Complete Sync Solution**
   - Roll out feature aggregation to all properties
   - Update Census sync configuration
   - Monitor sync success rate (target: 95%+)
   - Estimated effort: 12-16 hours
   - **Owner:** Data Engineering

8. **Implement Sync Monitoring**
   - Daily job to detect sync gaps
   - Alert when properties fall out of sync
   - Dashboard showing sync health metrics
   - Estimated effort: 12 hours
   - **Owner:** Data Engineering

9. **Address Salesforce Duplicates**
   - Merge duplicate Salesforce records if appropriate
   - Update Salesforce Flows to prevent future duplicates
   - Document when duplicates are legitimate
   - Estimated effort: 16-20 hours
   - **Owner:** Salesforce Admin

---

### Long Term (Next Quarter)

10. **Prevent Future Duplicates**
    - Add application validation for SFDC ID updates
    - Implement proper migration workflow (clear old SFDC IDs)
    - Add database constraints where appropriate
    - Estimated effort: 20-24 hours
    - **Owner:** Engineering team

11. **Historical Data Validation**
    - Validate all 12,272 ACTIVE properties
    - Ensure feature state is correct in both systems
    - Backfill any missing historical data
    - Estimated effort: 24-32 hours
    - **Owner:** Data Engineering

---

## SUCCESS METRICS

### Sync Health Targets

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| RDS properties synced to SF | 65.0% | 95%+ | 4 weeks |
| Feature sync accuracy | 90.1% | 99%+ | 2 weeks |
| Properties NOT in SF | 611 | <100 | 4 weeks |
| Duplicate SFDC ID groups | 2,556 | <500 | 8 weeks |
| SF duplicate records | 1,593 | <100 | 8 weeks |

### Monitoring Dashboards

**Daily Metrics to Track:**
1. Number of RDS properties NOT in Salesforce
2. Number of feature mismatches (RDS ≠ SF)
3. New duplicate SFDC IDs detected
4. Census sync job success rate
5. Salesforce record count vs RDS active count

---

## TECHNICAL NOTES

### Query Performance

All queries executed successfully with typical runtime:
- Overview queries: 2-5 seconds
- Join analysis: 15-20 seconds
- Feature comparison: 20-25 seconds
- Duplicate analysis: 10-15 seconds

### Data Freshness

- RDS data: Real-time (Fivetran sync)
- Salesforce data: Real-time (Fivetran sync)
- Analysis timestamp: January 5, 2026

### Limitations

1. **Sample sizes**: Field mapping only includes 100 records, not_in_sf limited to 500
2. **Historical context**: Salesforce data only goes back to Aug 2024
3. **Feature data**: Only analyzed IDV feature in detail, other features need validation
4. **Deleted records**: Not included in this analysis

---

## APPENDIX: SQL Queries Used

### A. RDS Overview Query
```sql
SELECT
    COUNT(*) as total_properties,
    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_count,
    COUNT(CASE WHEN status = 'DISABLED' THEN 1 END) as disabled_count,
    COUNT(CASE WHEN sfdc_id IS NOT NULL THEN 1 END) as has_sfdc_id,
    COUNT(DISTINCT sfdc_id) as unique_sfdc_ids
FROM rds.pg_rds_public.properties
```

### B. Join Analysis Query
```sql
SELECT
    COUNT(DISTINCT r.id) as rds_active_properties,
    COUNT(DISTINCT CASE WHEN sf.id IS NOT NULL THEN r.id END) as matched_by_property_id,
    COUNT(DISTINCT CASE WHEN sf.id IS NULL THEN r.id END) as not_in_salesforce
FROM rds.pg_rds_public.properties r
LEFT JOIN crm.salesforce.product_property sf
    ON CAST(r.id AS STRING) = sf.snappt_property_id_c
WHERE r.status = 'ACTIVE'
  AND r.sfdc_id IS NOT NULL
  AND r.sfdc_id != 'XXXXXXXXXXXXXXX'
  AND sf.is_deleted = false
```

### C. Duplicate Detection Query
```sql
SELECT
    sfdc_id,
    COUNT(*) as duplicate_count
FROM rds.pg_rds_public.properties
WHERE sfdc_id IS NOT NULL
GROUP BY sfdc_id
HAVING COUNT(*) > 1
```

---

## CONTACTS & RESOURCES

### Related Documentation

- Duplicate SFDC ID investigation: `19122025/README.md`
- Workflow redesign questions: `19122025/WORKFLOW_REDESIGN_QUESTIONS.md`
- Feature sync session: `salesforce_property_sync/SESSION_SUMMARY_product_feature_sync.md`
- Blocked properties report: `SALESFORCE_SYNC_BLOCKED_PROPERTIES_REPORT.md`

### Databricks Assets

- Sync Job: 1061000314609635 (00_sfdc_dbx_v2)
- Warehouse: 9b7a58ad33c27fbc
- Census Workspace: 33026

### Key Tables

- `rds.pg_rds_public.properties` - Source RDS properties
- `crm.salesforce.product_property` - Salesforce sync target
- `crm.sfdc_dbx.product_property_w_features` - Feature aggregation (should be used)
- `rds.pg_rds_public.property_feature_events` - Feature enablement events

---

**Report Generated By:** Claude Code
**Analysis Date:** January 5, 2026
**Data Freshness:** Live data from Databricks
**Contact:** Dane Rosa

---

*This discovery report provides a comprehensive analysis of RDS and Salesforce property sync status, identifying gaps, duplicates, and data quality issues requiring resolution.*
