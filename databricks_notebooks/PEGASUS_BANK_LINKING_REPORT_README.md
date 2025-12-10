# Pegasus Residential Bank Linking Beta - Applicant Level Report

## Overview

This report provides **applicant-level detail** for Pegasus Residential's bank linking beta program, addressing all key requirements:

✅ **Clear view of bank linking adoption and usage**
✅ **Number of applications through bank linking**
✅ **Number of applications through ID verification** (with correlation tracking)
✅ **Pass/Fail recommendations tied to outcomes**
✅ **Clear indication of whether program is used as intended**
✅ **Visibility into decisions made**
✅ **Callouts for glitches or issues**
✅ **Data at applicant level** (not aggregated)

## Files Included

### 1. `pegasus_applicant_level_report.sql`
Pure SQL queries that can be run directly in any SQL environment (Databricks SQL, DBeaver, etc.)

**Contains 4 separate queries:**
- **Main Applicant-Level Report** - Complete view of each applicant's journey
- **Executive Summary** - High-level KPIs and metrics
- **Issue Breakdown** - Detailed view of detected glitches
- **Property Performance** - Comparison across Pegasus properties

### 2. `pegasus_bank_linking_applicant_report.py`
Databricks Python notebook with all queries formatted for Databricks execution with visual displays

**Contains 4 sections:**
1. Applicant-Level Detail (main report)
2. Executive Summary Metrics
3. Issue Detection & Breakdown
4. Property-Level Performance

## How to Use

### Option 1: Import Databricks Notebook (Recommended)

1. **Upload to Databricks:**
   - Go to Databricks Workspace
   - Navigate to `/Users/[your-email]/`
   - Click "Import"
   - Upload `pegasus_bank_linking_applicant_report.py`

2. **Run the Notebook:**
   - Open the imported notebook
   - Run all cells (Cmd+Shift+Enter or Run All)
   - Each section will display interactive tables

3. **Export Results:**
   - Use Databricks' built-in export (CSV, Excel)
   - Or uncomment the export cells at the bottom

### Option 2: Run SQL Queries Directly

1. **Copy SQL from** `pegasus_applicant_level_report.sql`
2. **Run in Databricks SQL Editor** or any SQL client
3. **Run each query separately** (they're delimited by comments)

## Report Structure

### 1. Applicant-Level Detail (Main Report)

**Key Columns:**
- **Identification:** entry_id, applicant_id, applicant_name, email, property_name, submission_date
- **Bank Linking Usage:** used_bank_linking, bank_linking_submissions, duration_minutes
- **Alternative Methods:** used_connected_payroll, used_document_upload
- **ID Verification:** id_verification_count, id_verification_status, correlation_status
- **Income Verification:** income_verification_count, income_review_status, income_pass_fail, income_decisions
- **Asset Verification:** asset_verification_count, asset_review_status, asset_pass_fail, asset_decisions
- **Overall:** overall_recommendation (PASS/FAIL/PENDING/NO_DECISION)
- **Usage Assessment:** usage_assessment (PROPER_USAGE/INCOMPLETE_WORKFLOW/NOT_USING_BANK_LINKING/PARTIAL_USAGE)
- **Issues:** issue_flag, issue_description
- **Timing:** hours_since_submission, processing_timeliness

**Correlation Status Values:**
- `CORRELATED` - Bank linking used AND ID verification completed (✅ Expected behavior)
- `MISSING_ID_VERIFICATION` - Bank linking used but NO ID verification (⚠️ Potential issue)
- `ID_ONLY` - ID verification completed but no bank linking used
- `NO_VERIFICATION` - No bank linking or ID verification

**Usage Assessment Values:**
- `PROPER_USAGE` - Bank linking + ID verification + verification results (✅ Program used correctly)
- `INCOMPLETE_WORKFLOW` - Bank linking used but missing ID verification (⚠️ Incomplete)
- `NOT_USING_BANK_LINKING` - Not using the bank linking feature
- `PARTIAL_USAGE` - Some components present but not complete workflow

### 2. Executive Summary

**Metrics Provided:**
- Total Applicants (baseline)
- Bank Linking Adoption Rate
- ID Verification Adoption Rate
- Bank Linking + ID Verification Correlation Rate (**KEY METRIC**)
- Pass Rate (% of bank linking users who passed)
- Fail Rate (% of bank linking users who failed)
- Issues Detected (% with flagged problems)

### 3. Issue Detection

**Issue Types Flagged:**
- `NO_ID_VERIFICATION` - Bank linking used but no ID verification found
- `NO_VERIFICATION_RESULTS` - Bank linking used but no income/asset results
- `MULTIPLE_ATTEMPTS` - More than 3 bank linking submissions (user difficulties)
- `LONG_COMPLETION_TIME` - Took more than 60 minutes to complete

**For Each Issue:**
- Issue flag and description
- Number of affected applicants
- Affected properties
- First and last occurrence timestamps

### 4. Property-Level Performance

**Metrics by Property:**
- Total applicants
- Bank linking users
- Adoption rate %
- ID correlation rate %
- Success rate %
- Issues detected count

## Key Metrics to Monitor

### 🎯 Primary Success Indicators

1. **Bank Linking Adoption Rate**
   - Target: >50% of eligible applicants
   - Current: See Executive Summary

2. **ID Verification Correlation Rate**
   - Target: >95% (bank linking users should also have ID verification)
   - **CRITICAL**: Previous reports showed 0% correlation - this was the main issue
   - Formula: `(Bank Linking + ID Verification) / Bank Linking Users * 100`

3. **Pass Rate**
   - Target: >80% of bank linking users pass verification
   - Formula: `Passed Applicants / Bank Linking Applicants * 100`

4. **Program Usage Assessment**
   - Target: >90% show "PROPER_USAGE"
   - Indicates program is being used as designed

### ⚠️ Warning Signs

1. **High "MISSING_ID_VERIFICATION" correlation status**
   - Suggests data sync issues or workflow problems

2. **High "MULTIPLE_ATTEMPTS" issue flag**
   - Users struggling with bank linking interface

3. **High "NO_VERIFICATION_RESULTS" issue flag**
   - Processing failures after bank linking submission

## Filtering and Customization

### Adjust Date Range

Change this line in all queries:
```sql
AND e.inserted_at >= current_date() - INTERVAL 7 DAYS
```

To a different range:
```sql
AND e.inserted_at >= current_date() - INTERVAL 30 DAYS  -- Last 30 days
AND e.inserted_at >= '2025-12-01'                        -- Since specific date
```

### Filter to Specific Property

Add this WHERE clause:
```sql
AND prop.name = 'Your Property Name'
```

### Filter to Specific Issue

In the main report, add:
```sql
WHERE iss.issue_flag = 'NO_ID_VERIFICATION'
```

## Comparison with Previous Approach

### Previous Report (Aggregated):
- ❌ Daily aggregated data (no applicant detail)
- ❌ No individual applicant tracking
- ❌ No pass/fail tied to specific applicants
- ❌ Limited visibility into individual decisions
- ❌ 0% ID verification correlation (couldn't diagnose)

### New Report (Applicant-Level):
- ✅ **Every applicant tracked individually**
- ✅ **Full journey visible** (bank linking → ID verification → decisions)
- ✅ **Pass/Fail tied to each applicant**
- ✅ **Complete decision visibility**
- ✅ **Can identify exactly which applicants have issues**
- ✅ **Can track correlation at individual level**

## Example Use Cases

### Use Case 1: Finding Applicants with Correlation Issues
```sql
-- From the main report, filter where:
WHERE correlation_status = 'MISSING_ID_VERIFICATION'
```

**Result:** List of specific applicants who used bank linking but have no ID verification record

### Use Case 2: Reviewing All Failed Applicants
```sql
WHERE overall_recommendation = 'FAIL'
  AND used_bank_linking = 'YES'
```

**Result:** All bank linking users who failed verification, with full detail on why

### Use Case 3: Tracking High-Value Applicants
```sql
WHERE used_bank_linking = 'YES'
  AND usage_assessment = 'PROPER_USAGE'
  AND overall_recommendation = 'PASS'
```

**Result:** Applicants who used the program correctly and passed (success stories)

### Use Case 4: Investigating Processing Delays
```sql
WHERE processing_timeliness = 'DELAYED'
  AND used_bank_linking = 'YES'
```

**Result:** Bank linking applications that are taking too long to process

## Troubleshooting

### Q: No results returned?
**A:** Check that:
- Pegasus Residential has bank linking enabled properties
- Date range includes recent applications
- Property features table is up to date

### Q: ID verification correlation still showing low?
**A:** Check the applicant-level detail report and filter to `correlation_status = 'MISSING_ID_VERIFICATION'` to see specific affected applicants. This may indicate:
- Data sync lag between systems
- ID verification not being triggered properly
- Applicants abandoning workflow before ID verification

### Q: Many applicants showing "PARTIAL_USAGE"?
**A:** Review the specific applicants to determine:
- Are they starting but not completing bank linking?
- Are verification results not being generated?
- Is there a workflow dropout point?

## Next Steps

After reviewing this report:

1. **Immediate Actions:**
   - Review Executive Summary for overall health
   - Check Issue Detection for critical problems
   - Filter main report for applicants with issues

2. **Deep Dives:**
   - Export applicants with `MISSING_ID_VERIFICATION` for investigation
   - Review `MULTIPLE_ATTEMPTS` cases for UX issues
   - Compare Property Performance to identify best/worst performers

3. **Ongoing Monitoring:**
   - Run this report weekly
   - Track trend in adoption rate
   - Monitor ID correlation rate closely
   - Flag new issue types as they emerge

## Support

For questions or issues with this report, contact:
- Data Engineering team
- Dane Rosa (report creator)

## Changelog

**Version 1.0** (2025-12-09)
- Initial release
- Applicant-level reporting
- Full correlation tracking
- Issue detection system
- Property-level comparison
