# Salesforce Sync Blocked Properties Report

**Generated:** January 5, 2026
**Query Date:** Current live data from Databricks
**Purpose:** Comprehensive list of properties not syncing to Salesforce due to duplicate SFDC IDs

---

## EXECUTIVE SUMMARY

### Current Impact (Live Data)

| Metric | Count | Impact |
|--------|-------|--------|
| **Total ACTIVE properties blocked** | **2,410** | Cannot sync updates to Salesforce |
| **Properties with enabled features** | **2,058** | Features not visible in Salesforce |
| **Properties NOT in Salesforce** | **643** | Completely missing from CRM |
| **Features enabled but NOT in SF** | **507** | 🔴 CRITICAL - Customer impact |
| **Unique duplicate SFDC ID groups** | **1,978** | Duplicate groups requiring resolution |

### Business Impact

**🔴 CRITICAL - P1 (507 properties)**
- Have enabled features (Fraud Detection, Income Verification, Bank Linking, etc.)
- Are ACTIVE in RDS
- Are NOT appearing in Salesforce at all
- **Impact:** Sales/CS teams cannot see customer features, reporting is inaccurate, customers may not see their enabled services

**🟡 HIGH - P2 (1,551 properties)**
- Have enabled features
- Are IN Salesforce but feature updates are blocked from syncing
- **Impact:** Feature changes not propagating to Salesforce, stale data in CRM

**🟢 MEDIUM - P3 (136 properties)**
- No features enabled yet
- Not in Salesforce
- **Impact:** Will be blocked when features are enabled in future

---

## ROOT CAUSE ANALYSIS

### The Problem

Multiple properties in RDS share the same `sfdc_id` value:
- When Census tries to sync, it expects a 1:1 relationship
- Multiple RDS properties → Same Salesforce record causes sync failures
- Features from multiple properties need to be aggregated

### Why This Happens

1. **Property migrations:** Old DISABLED properties kept their sfdc_id
2. **Property name changes:** New property created, old one disabled
3. **Management company changes:** Different properties share same Salesforce account
4. **Legitimate many-to-1 relationships:** Multiple RDS properties map to one SF account

### Critical Discovery (Dec 23, 2025)

**Original assumption (Dec 19):** Duplicates = data integrity problem requiring cleanup
**New finding (Dec 23):** Many-to-1 relationships are **VALID BY DESIGN**

**Solution:** Implement feature aggregation layer instead of cleanup

---

## PRIORITY BREAKDOWN

### 🔴 P1 - CRITICAL: 507 Properties
**Features Enabled BUT NOT in Salesforce**

These properties have real customers with enabled features that are NOT visible in Salesforce:

**Top Examples:**
- Villa Capri Rental Homes (5 features enabled)
- Mosaic at Miramar Town Center (5 features)
- Broadway Chapter (5 features)
- Axis Grand Crossing (4 features)
- Twelve12 Apartments (4 features)

**Action Required:**
1. Identify why these properties aren't in Salesforce
2. Determine which SFDC ID they should use
3. Implement feature aggregation to sync them

**Files:**
- `P1_CRITICAL_properties_with_features_not_in_sf.csv` (507 records)

---

### 🟡 P2 - HIGH: 1,551 Properties
**Features Enabled, IN Salesforce, But Updates Blocked**

These properties are in Salesforce but feature updates don't sync:

**Top Examples:**
- Magnolia Pointe (5 features)
- Greens at Stonecreek (5 features)
- 2050 Morningside (5 features)
- Vinoy at St Johns (5 features)
- Expo at Forest Park (5 features)

**Action Required:**
1. Implement feature aggregation logic
2. Aggregate features from multiple properties sharing same SFDC ID
3. Update Census sync to use aggregated data

**Files:**
- `P1_P2_all_properties_with_features.csv` (2,058 records)

---

### 🟢 P3 - MEDIUM: 136 Properties
**No Features Yet, Not in Salesforce**

Properties blocked from future feature sync:

**Action Required:**
- Include in long-term aggregation solution
- Lower priority (no immediate customer impact)

---

## SOLUTION APPROACH

Based on the December 23 discovery, the solution requires **feature aggregation** rather than duplicate cleanup.

### Key Questions to Answer (from WORKFLOW_REDESIGN_QUESTIONS.md)

1. **Feature Aggregation Logic**
   - Union (ANY property has feature = enabled)?
   - ACTIVE properties only?
   - Most recent update wins?

2. **Which Properties Contribute?**
   - Only ACTIVE properties?
   - Include DISABLED properties?

3. **Conflict Resolution**
   - If properties have conflicting states, which wins?

4. **Metadata Aggregation**
   - `enabled_at` timestamps - which to use?
   - `feature_count` - sum or max?

### Recommended Implementation Steps

1. **Answer Clarification Questions**
   - Review `19122025/WORKFLOW_REDESIGN_QUESTIONS.md`
   - Define business rules for aggregation

2. **Create Aggregation Layer**
   - New view/table: `properties_aggregated_by_sfdc_id`
   - Aggregate features using defined rules
   - Ensure 1:1 relationship with SFDC IDs

3. **Update Census Sync**
   - Modify `census_pfe` notebook
   - Use aggregated view as source
   - Test with known duplicates

4. **Validate Results**
   - Test with Park Kennedy case
   - Verify top 20 impacted properties
   - Monitor sync job for errors

5. **Deploy and Monitor**
   - Run in staging first
   - Deploy to production
   - Monitor for 48 hours

---

## DATA FILES PROVIDED

All files saved to: `/Users/danerosa/rds_databricks_claude/`

### CSV Reports

1. **P1_CRITICAL_properties_with_features_not_in_sf.csv**
   - 507 properties with features enabled but NOT in Salesforce
   - Highest priority for immediate attention
   - Sorted by feature count (most features first)

2. **P1_P2_all_properties_with_features.csv**
   - 2,058 properties with enabled features (P1 + P2)
   - All properties requiring feature aggregation
   - Includes both in/out of Salesforce

3. **ALL_blocked_properties_comprehensive.csv**
   - 2,410 total ACTIVE properties blocked by duplicates
   - Complete dataset for analysis
   - Includes properties with and without features

4. **duplicate_sfdc_id_groups_summary.csv**
   - 1,978 unique duplicate SFDC ID groups
   - Shows how many ACTIVE properties share each SFDC ID
   - Summarizes feature counts per group

### JSON Data

5. **blocked_properties_report.json**
   - Raw query results from Databricks
   - Complete data with all columns
   - For programmatic processing

---

## DETAILED COLUMNS IN CSV FILES

| Column | Description |
|--------|-------------|
| `id` | RDS property UUID |
| `name` | Property name |
| `short_id` | Short property ID (e.g., "ig2NaqEzED") |
| `status` | Property status (all ACTIVE in this report) |
| `sfdc_id` | Salesforce ID (duplicated across multiple properties) |
| `inserted_at` | When property was created in RDS |
| `updated_at` | Last update timestamp |
| `duplicate_count` | How many properties share this SFDC ID |
| `salesforce_record_id` | Salesforce record ID if synced |
| `snappt_property_id_c` | Snappt property ID in Salesforce |
| `enabled_features_count` | Number of enabled features |
| `enabled_features` | List of enabled feature codes |
| `sync_status` | "In Salesforce" or "NOT in Salesforce" |

---

## SAMPLE DATA: TOP 20 MOST IMPACTED

| Property Name | Features | Sync Status | SFDC ID |
|---------------|----------|-------------|---------|
| Villa Capri Rental Homes | 5 | NOT in Salesforce | a01Dn00000HHJffIAH |
| Magnolia Pointe | 5 | In Salesforce | a01Dn00000HHvw7IAD |
| Greens at Stonecreek | 5 | In Salesforce | a01Dn00000HHihmIAD |
| 2050 Morningside | 5 | In Salesforce | a01Dn00000HHdEaIAL |
| Vinoy at St Johns | 5 | In Salesforce | a01UL00000WBKYvYAP |
| Expo at Forest Park | 5 | In Salesforce | a01Dn00000HHMvDIAX |
| Citrine on 67th | 5 | In Salesforce | a01UL000008JMOSYA4 |
| Nola Sky | 5 | In Salesforce | a01Dn00000HIwYHIA1 |
| Phillips Pass | 5 | In Salesforce | a01Dn00000HHVGAIA5 |
| Mosaic at Miramar Town Center | 5 | NOT in Salesforce | a01Dn00000HHllKIAT |
| Broadway Chapter | 5 | NOT in Salesforce | a01Dn00000HHfF7IAL |
| The Franklin at East Cobb | 5 | In Salesforce | a01Dn00000HHiD9IAL |
| Celsius Apartment Homes | 5 | In Salesforce | a01Dn00000HHJvQIAX |
| 26 at city point | 4 | In Salesforce | a01Dn00000HHdTtIAL |
| Axis Grand Crossing | 4 | NOT in Salesforce | a01Dn00000HHdTtIAL |
| Woodlands at the Preserve | 4 | In Salesforce | a01Dn00000HHcZUIA1 |
| Amarillo Gardens | 4 | In Salesforce | a01Dn00000HHGevIAH |
| Village on Memorial | 4 | In Salesforce | a01Dn00000HHssWIAT |
| Twelve12 Apartments | 4 | NOT in Salesforce | a01Dn00000HHa2LIAT |
| The Parker at Huntington Metro | 4 | In Salesforce | a01Dn00000HHUjxIAH |

---

## COMPARISON WITH DECEMBER 19 ANALYSIS

### Original Analysis (Dec 19, 2025)

Based on snapshot from Dec 19:
- 2,541 duplicate SFDC ID groups
- 6,068 properties affected (ACTIVE + DISABLED)
- 3,391 DISABLED properties
- 2,677 ACTIVE properties
- ~2,500 ACTIVE properties blocked

### Current Analysis (Jan 5, 2026)

Current live data:
- 1,978 duplicate SFDC ID groups (ACTIVE only)
- 2,410 ACTIVE properties blocked
- 507 with features NOT in Salesforce (P1)
- 1,551 with features IN Salesforce but blocked (P2)

### Key Differences

1. **Scope:** Original included DISABLED properties, current is ACTIVE only
2. **Focus:** Original focused on cleanup, current focuses on properties needing sync
3. **Priority:** Current analysis prioritizes by customer impact (features enabled)
4. **Approach:** Original planned cleanup, current focuses on aggregation solution

---

## RELATED DOCUMENTATION

### Investigation Files (19122025 folder)
- `README.md` - Overview of duplicate investigation
- `WORKFLOW_REDESIGN_QUESTIONS.md` - 9 questions to answer before implementation
- `DUPLICATE_CLEANUP_SUMMARY.md` - Executive summary (based on old 1:1 model)
- `Phase1_Cleanup_Script.sql` - Cleanup script (ON HOLD pending aggregation approach)

### Salesforce Sync Documentation
- `salesforce_property_sync/SESSION_SUMMARY_product_feature_sync.md`
- `salesforce_property_sync/feature_sync_status_summary.md`

### Databricks Assets
- Sync Job: `1061000314609635` (00_sfdc_dbx_v2)
- Notebook: `/Workspace/Shared/census_pfe`
- Notebook: `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`

### Census
- Workspace: 33026
- Sync URL: https://app.getcensus.com/workspaces/33026/

---

## NEXT STEPS

### Immediate (This Week)

1. **Review this report** with team
2. **Answer 9 questions** in `WORKFLOW_REDESIGN_QUESTIONS.md`
3. **Prioritize P1 properties** - 507 properties with features not in SF
4. **Investigate top 5-10** P1 properties to understand patterns

### Short Term (Next 2 Weeks)

1. **Design aggregation logic** based on answers to questions
2. **Create aggregation view/table** in Databricks
3. **Update census_pfe notebook** to use aggregated data
4. **Test with known cases** (Park Kennedy, top 20 properties)

### Long Term (Next Month)

1. **Deploy aggregation solution** to production
2. **Monitor sync success rate** - target 95%+
3. **Validate P1 properties** appear in Salesforce with correct features
4. **Document new many-to-1 model** for team

---

## QUESTIONS?

For technical details, see:
- `19122025/WORKFLOW_REDESIGN_QUESTIONS.md` - Clarification questions
- `19122025/DUPLICATE_CLEANUP_ANALYSIS.md` - Technical deep dive
- `salesforce_property_sync/SESSION_SUMMARY_product_feature_sync.md` - Feature sync details

---

**Report Generated By:** Claude Code
**Query Source:** Databricks warehouse 9b7a58ad33c27fbc
**Data Freshness:** Live data as of January 5, 2026
**Contact:** Dane Rosa

---

*This report provides the comprehensive list of properties in Salesforce that haven't been updated due to duplicative SFDC IDs coming from the product (RDS properties) table.*
