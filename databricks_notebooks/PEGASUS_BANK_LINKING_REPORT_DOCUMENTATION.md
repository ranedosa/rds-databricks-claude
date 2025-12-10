# Pegasus Residential Bank Linking Beta - Applicant Report Documentation

## Executive Summary

This Databricks notebook provides **applicant-level reporting** for Pegasus Residential's bank linking beta program. It delivers a comprehensive view of each individual applicant's journey through the bank account linking verification process, enabling Pegasus to track adoption, identify issues, and measure success at a granular level.

**Notebook Location:**
`/Users/dane@snappt.com/pegasus_bank_linking_applicant_report`

**Databricks URL:**
https://dbc-9ca0f5e0-2208.cloud.databricks.com/workspace/Users/dane@snappt.com/pegasus_bank_linking_applicant_report

---

## What Problem Does This Solve?

### Business Context

Pegasus Residential is running a beta program for **Bank Account Linking (BAL)** - a feature that allows applicants to verify their income and assets by securely connecting their bank accounts, rather than manually uploading documents. As with any beta program, Pegasus needs visibility into:

1. **Is the program being used?** (Adoption tracking)
2. **Is it working correctly?** (Issue detection)
3. **What are the outcomes?** (Pass/fail recommendations)
4. **Is the full workflow being completed?** (ID verification correlation)

### The Challenge

Prior reporting approaches provided **aggregated metrics** (e.g., "85 applicants used bank linking this week"), but Pegasus needed **applicant-level detail** to:

- Identify exactly which applicants used bank linking
- Track the complete journey for each applicant from bank linking → ID verification → verification outcome
- Pinpoint specific applicants experiencing issues
- Correlate bank linking usage with ID verification completion
- Provide pass/fail recommendations with reasons for each applicant
- Detect workflow anomalies (missing steps, long completion times, multiple attempts)

### Requirements from JIRA Task

The Pegasus team specifically requested:

> **What must be included:**
> - Clear view of bank linking adoption and usage
> - Number of applications run through bank linking
> - Number of applications run through ID verification (these should closely correlate)
> - Pass / Fail recommendations tied to outcomes
> - Clear indication of whether the program is being used as intended
> - Visibility into decisions made
> - Callouts for any glitches or issues, if present
>
> **Critical:** The data should be at an **applicant level**

Daniel Cooper's "dream state" vision:
> "Each applicant would show:
> - IDV: ✓
> - Bank Linking: ✓
> - Connected Payroll: ✗
> - Bank Statements: ✗
> - Pay Stubs: ✓
> - Ruling: Pass/Fail and a reason"

---

## How Does This Notebook Solve It?

### High-Level Approach

This notebook queries the Snappt production database (`rds.pg_rds_public` schema) to construct a complete, applicant-by-applicant view of the bank linking workflow. It does this in **4 comprehensive report sections**:

1. **Applicant-Level Detail** - Individual applicant records
2. **Executive Summary** - High-level KPIs
3. **Issue Detection** - Glitches and anomalies
4. **Property Performance** - Comparison across properties

### Technical Architecture

The notebook uses **Common Table Expressions (CTEs)** to progressively build up data from multiple source tables, then combines them into final reports.

#### Source Tables Queried

| Table | Purpose |
|-------|---------|
| `properties` | Identify Pegasus properties |
| `property_features` | Filter to BAL-enabled properties only |
| `entries` | Application submissions |
| `folders` | Link entries to properties and companies |
| `companies` | Filter to Pegasus Residential |
| `applicants` | Individual applicant information |
| `applicant_submissions` | Submission events |
| `applicant_submission_document_sources` | Track document source types (BANK_LINKING, CONNECTED_PAYROLL, DOCUMENT_UPLOAD) |
| `id_verifications` | ID verification completion and status |
| `income_verification_submissions` | Income verification outcomes |
| `asset_verification_submissions` | Asset verification outcomes |

#### Key Filtering Logic

```sql
-- Only Pegasus Residential
WHERE c.name = 'Pegasus Residential'

-- Only properties with bank linking enabled
WHERE pf.feature_code = 'bank_linking' AND pf.state = 'enabled'

-- Only recent applications (last 7 days)
AND e.inserted_at >= current_date() - INTERVAL 7 DAYS

-- Only applications submitted after BAL was enabled for that property
AND e.submission_time >= bal.date_bal_enabled
```

---

## Report Section Breakdown

### Section 1: Applicant-Level Detail

**Purpose:** The core report showing every applicant's complete journey.

**Key CTEs:**
1. `bal_enabled_properties` - List of BAL-enabled properties
2. `applicant_base` - Core applicant and entry information
3. `bank_linking_usage` - Which features each applicant used (Bank Linking, Connected Payroll, Document Upload)
4. `id_verification_status` - ID verification completion and success
5. `income_verification_results` - Income verification pass/fail
6. `asset_verification_results` - Asset verification pass/fail
7. `issue_detection` - Automated anomaly flagging

**Output Columns:**

| Column | Description |
|--------|-------------|
| `entry_id` | Unique application entry ID |
| `applicant_id` | Unique applicant ID |
| `applicant_name` | Applicant's full name |
| `applicant_email` | Applicant's email |
| `property_name` | Property they applied to |
| `submission_date` | Date of application |
| `used_bank_linking` | YES/NO - Did they use bank linking? |
| `bank_linking_submissions` | Number of bank linking attempts |
| `bank_linking_duration_minutes` | Time from first to last attempt |
| `used_connected_payroll` | YES/NO - Used connected payroll? |
| `used_document_upload` | YES/NO - Used document upload? |
| `id_verification_count` | Number of ID verifications |
| `id_verification_status` | SUCCESS, FAILED, etc. |
| `id_verified` | YES/NO - Successfully verified? |
| `correlation_status` | CORRELATED, MISSING_ID_VERIFICATION, ID_ONLY, NO_VERIFICATION |
| `income_verification_count` | Number of income verifications |
| `income_review_status` | ACCEPTED, REJECTED, etc. |
| `income_pass_fail` | PASS or FAIL |
| `income_rejection_reasons` | Reasons if rejected |
| `asset_verification_count` | Number of asset verifications |
| `asset_review_status` | ACCEPTED, REJECTED, etc. |
| `asset_pass_fail` | PASS or FAIL |
| `asset_rejection_reasons` | Reasons if rejected |
| `overall_recommendation` | PASS, FAIL, PENDING, NO_DECISION |
| `usage_assessment` | PROPER_USAGE, INCOMPLETE_WORKFLOW, NOT_USING_BANK_LINKING, PARTIAL_USAGE |
| `issue_flag` | NO_ID_VERIFICATION, NO_VERIFICATION_RESULTS, MULTIPLE_ATTEMPTS, LONG_COMPLETION_TIME |
| `issue_description` | Human-readable explanation of the issue |
| `hours_since_submission` | Time since application submitted |
| `processing_timeliness` | TIMELY or DELAYED (>48 hours) |

**Correlation Status Logic:**

This is a **critical field** that addresses the requirement that "bank linking and ID verification should closely correlate."

```sql
CASE
    WHEN used_bank_linking = 1 AND id_verification_count > 0 THEN 'CORRELATED'
    WHEN used_bank_linking = 1 AND id_verification_count = 0 THEN 'MISSING_ID_VERIFICATION'
    WHEN used_bank_linking = 0 AND id_verification_count > 0 THEN 'ID_ONLY'
    ELSE 'NO_VERIFICATION'
END as correlation_status
```

- `CORRELATED` = ✅ Expected behavior - both bank linking and ID verification present
- `MISSING_ID_VERIFICATION` = ⚠️ **Problem** - Bank linking used but no ID verification (this was showing 0% in previous reports)
- `ID_ONLY` = Applicant did ID verification but not bank linking
- `NO_VERIFICATION` = Neither bank linking nor ID verification present

**Usage Assessment Logic:**

Determines if the program is being used as intended:

```sql
CASE
    WHEN used_bank_linking = 1 AND id_verification_count > 0
         AND (income_verification_count > 0 OR asset_verification_count > 0)
    THEN 'PROPER_USAGE'

    WHEN used_bank_linking = 1 AND id_verification_count = 0
    THEN 'INCOMPLETE_WORKFLOW'

    WHEN used_bank_linking = 0
    THEN 'NOT_USING_BANK_LINKING'

    ELSE 'PARTIAL_USAGE'
END as usage_assessment
```

- `PROPER_USAGE` = ✅ All steps completed (bank linking → ID verification → verification results)
- `INCOMPLETE_WORKFLOW` = ⚠️ Bank linking started but workflow not completed
- `NOT_USING_BANK_LINKING` = Traditional document upload method
- `PARTIAL_USAGE` = Some steps present but not complete

**Issue Detection Logic:**

Automatically flags potential problems:

```sql
CASE
    WHEN used_bank_linking = 1 AND id_verification_count = 0
    THEN 'NO_ID_VERIFICATION'

    WHEN used_bank_linking = 1 AND income_verification_count = 0 AND asset_verification_count = 0
    THEN 'NO_VERIFICATION_RESULTS'

    WHEN bank_linking_submissions > 3
    THEN 'MULTIPLE_ATTEMPTS'

    WHEN (UNIX_TIMESTAMP(last_bank_linking_time) - UNIX_TIMESTAMP(first_bank_linking_time)) / 60 > 60
    THEN 'LONG_COMPLETION_TIME'

    ELSE NULL
END as issue_flag
```

Each issue includes a human-readable description explaining the potential problem.

---

### Section 2: Executive Summary

**Purpose:** High-level KPIs for quick assessment of program health.

**Metrics Provided:**

| Metric | Description | Target |
|--------|-------------|--------|
| Total Applicants | Baseline count | - |
| Bank Linking Adoption | % of applicants using bank linking | >50% |
| ID Verification Adoption | % of applicants completing ID verification | >80% |
| **Bank Linking + ID Verification** | **% of bank linking users who also have ID verification** | **>95%** |
| Passed Recommendations | % of bank linking users who passed | >80% |
| Failed Recommendations | % of bank linking users who failed | <20% |
| Applicants with Issues | % flagged with potential problems | <10% |

**Key Formula:**

The **critical correlation metric** that was showing 0% in previous reports:

```
Bank Linking + ID Verification Rate =
  (Count of applicants with BOTH bank linking AND ID verification) /
  (Count of applicants with bank linking) × 100
```

If this is low (<80%), it indicates a workflow problem where applicants are using bank linking but not completing ID verification.

---

### Section 3: Issue Detection

**Purpose:** Detailed breakdown of all detected glitches and anomalies.

**Output:**

| Column | Description |
|--------|-------------|
| `issue_flag` | Issue type identifier |
| `issue_description` | Explanation of the problem |
| `applicant_count` | Number of applicants affected |
| `affected_properties` | Which properties see this issue |
| `first_occurrence` | When this issue first appeared |
| `last_occurrence` | Most recent occurrence |

**Issue Types:**

1. **NO_ID_VERIFICATION**
   - Description: "Bank linking used but no ID verification found - possible data sync issue"
   - Action: Check if ID verification step is being triggered correctly

2. **NO_VERIFICATION_RESULTS**
   - Description: "Bank linking used but no income/asset verification results - possible processing failure"
   - Action: Investigate backend processing pipeline

3. **MULTIPLE_ATTEMPTS**
   - Description: "More than 3 bank linking submissions - user may be experiencing difficulties"
   - Action: Review UX; applicant may be confused or encountering errors

4. **LONG_COMPLETION_TIME**
   - Description: "Took more than 60 minutes to complete - possible abandonment and return"
   - Action: Check for workflow interruptions; may indicate applicant difficulty

---

### Section 4: Property-Level Performance

**Purpose:** Compare bank linking performance across different Pegasus properties to identify best and worst performers.

**Output Columns:**

| Column | Description |
|--------|-------------|
| `property_name` | Name of the property |
| `total_applicants` | Total applications to this property |
| `bank_linking_users` | Count who used bank linking |
| `adoption_rate_pct` | % adoption of bank linking |
| `id_correlation_pct` | % of bank linking users who also have ID verification |
| `success_rate_pct` | % of bank linking users who passed verification |
| `issues_detected` | Count of applicants with flagged issues |

**Use Cases:**

- Identify properties with low adoption (may need marketing/education)
- Identify properties with low correlation (may have technical issues)
- Identify properties with low success rates (may have applicant quality issues)
- Compare "control" properties to optimize rollout strategy

---

## How to Use This Notebook

### Running the Report

1. **Open the notebook** in Databricks (URL at top of this document)
2. **Click "Run All"** at the top of the notebook
3. **Wait 20-30 seconds** for all cells to execute
4. **Review the 4 result tables** that appear below each cell

### Interpreting Results

#### For Weekly Pegasus Updates:

**Page 1: Executive Summary**
- Share the metrics table showing adoption, correlation, and pass rates
- Highlight any metrics below target (e.g., <95% correlation)

**Page 2: Applicant Detail (filtered)**
- Export applicants with `issue_flag IS NOT NULL` to investigate problems
- Export applicants with `correlation_status = 'MISSING_ID_VERIFICATION'` if correlation is low

**Page 3: Issue Breakdown**
- Share the issue summary showing types and counts
- Note any trending issues (increasing `applicant_count` over time)

#### For Internal Analysis:

**Full Applicant Detail:**
- Use filters to drill into specific scenarios:
  - `WHERE overall_recommendation = 'FAIL'` - Review all failures
  - `WHERE usage_assessment = 'INCOMPLETE_WORKFLOW'` - Find workflow dropouts
  - `WHERE processing_timeliness = 'DELAYED'` - Find slow processing

**Property Performance:**
- Identify outlier properties for targeted investigation
- Use top performers as case studies for best practices

### Exporting Data

**Option 1: Databricks UI**
- Click on any result table
- Click the download icon
- Choose CSV or Excel format

**Option 2: Save to Delta Table**
- Uncomment the last cell in the notebook
- Results will be saved to a permanent Delta table
- Can be queried by other notebooks or BI tools

**Option 3: Scheduled Email**
- Set up a Databricks Job to run this notebook weekly
- Configure email notification with CSV attachments
- Recipients receive automated reports every Monday morning

---

## Key Insights This Report Provides

### 1. Adoption Tracking

**Question:** How many applicants are using bank linking?

**Answer:** See `Bank Linking Adoption` in Executive Summary, or count applicants with `used_bank_linking = 'YES'` in Applicant Detail.

**Drill-down:** Property Performance section shows which properties have highest/lowest adoption.

---

### 2. Correlation Analysis

**Question:** Are applicants who use bank linking also completing ID verification?

**Answer:** See `Bank Linking + ID Verification` metric in Executive Summary.

**Drill-down:** Filter Applicant Detail to `correlation_status = 'MISSING_ID_VERIFICATION'` to see exactly which applicants are affected.

**Previous Problem:** This was showing 0% in the old aggregated report, but we couldn't identify which applicants were affected. Now we can.

---

### 3. Success Measurement

**Question:** What percentage of bank linking applicants pass verification?

**Answer:** See `Passed Recommendations` in Executive Summary, or calculate from Applicant Detail:
```
Pass Rate = (Count where overall_recommendation = 'PASS') / (Total bank linking users) × 100
```

**Drill-down:** Review `income_rejection_reasons` and `asset_rejection_reasons` for failed applicants to understand why.

---

### 4. Workflow Validation

**Question:** Is the program being used as intended (complete workflow)?

**Answer:** See `usage_assessment` field in Applicant Detail:
- `PROPER_USAGE` count = Number using program correctly
- Target: >90% of bank linking users should show PROPER_USAGE

**Drill-down:** Filter to `usage_assessment = 'INCOMPLETE_WORKFLOW'` to find applicants dropping out mid-process.

---

### 5. Issue Identification

**Question:** What problems are applicants encountering?

**Answer:** See Issue Detection section for summary by issue type.

**Drill-down:** Filter Applicant Detail to specific `issue_flag` values to get list of affected applicants with full context (property, date, etc.).

---

## Technical Implementation Details

### Join Strategy

The notebook uses **applicant_id** as the primary key to join all CTEs together:

```sql
FROM applicant_details ad
LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
LEFT JOIN issue_detection iss ON ad.applicant_id = iss.applicant_id
```

**Why LEFT JOIN?**
- Not all applicants complete every step
- LEFT JOIN ensures we see all applicants even if they're missing some verification steps
- NULL values are handled gracefully with COALESCE and CASE statements

### Aggregation Functions

Each CTE uses aggregation to collapse multiple records per applicant into single values:

- `MAX(CASE WHEN ... THEN 1 ELSE 0 END)` - Boolean flags (0/1)
- `COUNT(DISTINCT ...)` - Count unique records
- `CONCAT_WS(', ', COLLECT_SET(...))` - Concatenate distinct values
- `MIN(...)` / `MAX(...)` - First/last timestamps

### Databricks SQL Syntax

The notebook uses **Spark SQL** (Databricks dialect):

- `CONCAT_WS()` instead of `STRING_AGG()` for string aggregation
- `COLLECT_SET()` to get distinct values before concatenation
- `UNIX_TIMESTAMP()` for time calculations
- `INTERVAL '7 DAYS'` for date math

---

## Customization and Extension

### Adjusting Date Range

Change the 7-day lookback:

```sql
-- Current (last 7 days)
AND e.inserted_at >= current_date() - INTERVAL 7 DAYS

-- Change to 30 days
AND e.inserted_at >= current_date() - INTERVAL 30 DAYS

-- Change to specific date
AND e.inserted_at >= '2025-12-01'
```

### Adding New Issue Types

Extend the `issue_detection` CTE:

```sql
CASE
    -- Existing issues...
    WHEN <your_condition> THEN 'YOUR_ISSUE_FLAG'
    ELSE NULL
END as issue_flag
```

### Filtering to Specific Properties

Add a WHERE clause at the end:

```sql
WHERE property_name IN ('Property A', 'Property B')
```

### Adding New Metrics

Extend the `Executive Summary` query with additional UNION ALL blocks:

```sql
UNION ALL

SELECT
    'Your New Metric',
    your_calculation,
    your_percentage
FROM applicant_summary
```

---

## Data Freshness and Accuracy

### Data Source

All data comes from the **production Snappt database** (`rds.pg_rds_public` schema), which is:

- Updated in real-time as applications are submitted
- Reflects the current state of all verifications
- Includes all historical data since BAL was enabled

### Lookback Window

The default **7-day window** includes:

- All applicants who **inserted** an application in the last 7 days
- Only applications to **BAL-enabled properties**
- Only applications **submitted after BAL was enabled** for that property

This ensures we're only looking at applicants who had the opportunity to use bank linking.

### Known Limitations

1. **Lagging ID Verifications:** If there's a delay between bank linking and ID verification, an applicant may temporarily show `MISSING_ID_VERIFICATION` before the ID verification record appears.

2. **Multiple Applicants per Entry:** A single entry may have multiple applicants (co-applicants). Each applicant is tracked separately.

3. **Resubmissions:** If an applicant resubmits, they may appear multiple times (different entry_ids). Filter to most recent by `submission_time` if needed.

---

## Comparison to Previous Approach

### Old Approach (Aggregated Daily Metrics)

**What it showed:**
- "85 applications used bank linking this week"
- "0% correlation between bank linking and ID verification"
- Daily time-series charts

**Limitations:**
- ❌ Couldn't identify which specific applicants had issues
- ❌ Couldn't drill down to applicant level
- ❌ Couldn't track individual journeys
- ❌ When correlation was 0%, couldn't diagnose why

### New Approach (Applicant-Level Detail)

**What it shows:**
- Every individual applicant with their complete journey
- Exact list of applicants with correlation issues
- Full context for each applicant (property, dates, outcomes)

**Advantages:**
- ✅ Can identify specific applicants to investigate
- ✅ Can track complete workflows applicant-by-applicant
- ✅ Can export affected applicants for targeted follow-up
- ✅ When correlation is low, can see exactly who and why

---

## Maintenance and Support

### Regular Updates Needed

**None required** - this report queries production data in real-time.

### Schema Changes to Monitor

If the database schema changes, update the notebook:

- Table name changes
- Column name changes
- New verification types added
- New feature codes added

### Performance Considerations

Current query performance: **~10-20 seconds**

If performance degrades:
1. Check if date range is too wide (more than 30 days)
2. Verify indexes exist on join columns
3. Consider materializing CTEs as temp tables for complex queries

---

## Success Metrics

This report enables Pegasus to track:

✅ **Adoption:** Is bank linking being used?
Target: >50% of applicants

✅ **Correlation:** Are bank linking users completing ID verification?
Target: >95% correlation

✅ **Success:** Are applicants passing verification?
Target: >80% pass rate

✅ **Quality:** Is the workflow being completed properly?
Target: >90% showing PROPER_USAGE

✅ **Reliability:** Are there technical issues?
Target: <10% with issue flags

---

## Conclusion

This notebook solves Pegasus's need for **granular, applicant-level visibility** into their bank linking beta program. By providing four comprehensive report sections, it enables:

1. **Executive stakeholders** to track high-level KPIs
2. **Product managers** to measure adoption and success
3. **Engineering teams** to identify and debug technical issues
4. **Support teams** to investigate specific applicant problems

The report's applicant-level approach (vs. aggregated metrics) is the key differentiator, enabling true root-cause analysis and targeted interventions when issues arise.

---

## Contact

For questions, enhancements, or issues with this notebook:
- **Creator:** Dane Rosa
- **Team:** Data Engineering / Analytics
- **Documentation Date:** December 9, 2025
- **Last Updated:** December 9, 2025
