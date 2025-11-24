# Sales-Focused IDV Results Dashboard - Build Guide

## Overview

This dashboard is designed specifically for **sales teams** to showcase ID verification results to customers during demos and business reviews. Unlike internal operational dashboards, this focuses on customer-facing metrics and insights.

**Created:** 2025-10-30
**Purpose:** Customer-facing sales presentations
**Target Users:** Sales team, Customer Success, Account Managers

---

## Dashboard Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  FILTERS: [Company ▼] [Property ▼] [Date Range: Last 30d ▼] │
├─────────────────────────────────────────────────────────────┤
│  📊 EXECUTIVE SUMMARY                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Total   │ │   Pass   │ │  Active  │ │  Active  │      │
│  │  Scans   │ │   Rate   │ │Properties│ │Companies │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────┤
│  📈 TRENDS & PERFORMANCE                                     │
│  ┌────────────────────────┐  ┌─────────────────────────┐   │
│  │ Pass/Fail Trend        │  │ Weekly Pass Rate        │   │
│  │ Over Time (Bar)        │  │ (Line Chart)            │   │
│  └────────────────────────┘  └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  🎯 STATUS DISTRIBUTION                                      │
│  ┌────────────────────────┐  ┌─────────────────────────┐   │
│  │ Pass/Fail/Review       │  │ Top Failure Reasons     │   │
│  │ (Pie Chart)            │  │ (Bar Chart)             │   │
│  └────────────────────────┘  └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  🏢 PROPERTY PERFORMANCE                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Property Name │ State │ Total │ Pass │ Fail │ Pass Rate ││
│  │ Brookfield    │  TX   │  150  │ 142  │  8   │   94.7%   ││
│  │ Greystar      │  CA   │  120  │ 110  │  10  │   91.7%   ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  📋 RECENT SUBMISSIONS (Last 100)                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Date │ Property │ State │ Status │ Provider │ Level     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Widget Specifications

### Row 1: Filters (Always Visible)
1. **Company Filter** - Dropdown, multi-select
2. **Property Filter** - Dropdown, multi-select (filtered by company)
3. **Date Range** - Date picker (default: last 30 days)

### Row 2: Executive Summary Counters
4. **Total IDV Scans** - Counter widget
5. **Pass Rate %** - Counter widget (green if >90%, yellow if 80-90%, red if <80%)
6. **Active Properties** - Counter widget
7. **Active Companies** - Counter widget

### Row 3: Trends Over Time
8. **Pass/Fail Trend** - Stacked bar chart (daily)
   - X-axis: Date
   - Y-axis: Count
   - Colors: Green (PASS), Red (FAIL), Gray (NEEDS REVIEW)

9. **Weekly Pass Rate Trend** - Line chart
   - X-axis: Week
   - Y-axis: Pass rate %
   - Show trend line

### Row 4: Status Distribution
10. **Pass/Fail/Review Distribution** - Pie chart
    - Colors: Green (PASS), Red (FAIL), Gray (NEEDS REVIEW)
    - Show percentages

11. **Top Failure Reasons** - Horizontal bar chart
    - Top 10 failure reasons
    - Sorted by count (highest first)

### Row 5: Provider Comparison (Optional)
12. **CLEAR vs Incode Performance** - Grouped bar chart
    - Compare pass rates between providers
    - Show total scans for each

### Row 6: Geographic Performance
13. **Performance by State** - Table or map
    - State, properties, total scans, pass rate
    - Color-coded by pass rate

### Row 7: Property-Level Detail
14. **Property Performance Table** - Detailed table
    - Sortable columns
    - Click to drill down
    - Color-coded pass rates

### Row 8: Recent Activity
15. **Recent Submissions** - Detailed table
    - Last 100 submissions
    - Full details for each scan
    - Sortable and filterable

---

## Key Metrics Explained

### Pass Rate Calculation
```
Pass Rate = (Passed Scans / Total Scans with Results) × 100
```

### Status Definitions
- **PASS:** Identity verification succeeded
- **FAIL:** Identity verification failed (see score_reason for details)
- **NEEDS REVIEW:** Manual review required

### Verification Levels (CLEAR only)
- **Enhanced (Full):** Comprehensive verification with additional checks
- **Basic (Lite):** Streamlined verification process

---

## SQL Queries Reference

All queries are located in: `/Users/danerosa/rds_databricks_claude/dashboards/sales_idv_results_dashboard_queries.sql`

### Query Parameters:
- `:start_date` - Filter start date (default: 30 days ago)
- `:end_date` - Filter end date (default: today)
- `:company_filter` - Company ID for filtering (optional)
- `:property_filter` - Property ID for filtering (optional)

---

## Building the Dashboard in Databricks

### Step 1: Create New Dashboard
1. Go to Databricks Workspace
2. Navigate to **Workspace** → **Create** → **Dashboard** (Lakeview)
3. Name it: **"Sales - IDV Results Dashboard"**

### Step 2: Add Datasets
For each query in the SQL file:
1. Click **Add** → **Dataset**
2. Paste the SQL query
3. Configure parameters:
   - `start_date`: DATE, default 30 days ago
   - `end_date`: DATE, default today
   - `company_filter`: TEXT, optional
   - `property_filter`: TEXT, optional
4. Name the dataset appropriately (e.g., "Executive Summary", "Property Performance")

### Step 3: Create Visualizations
Follow the widget specifications above to create each visualization:
1. **Counter widgets** for metrics
2. **Bar charts** for trends and distributions
3. **Pie charts** for status breakdown
4. **Tables** for detailed data
5. **Line charts** for time-based trends

### Step 4: Add Filters
1. Add filter widgets at the top:
   - Company dropdown (uses Query 11)
   - Property dropdown (uses Query 12, cascades from company)
   - Date range picker
2. Link filters to all queries using parameters

### Step 5: Configure Layout
1. Arrange widgets according to the layout structure above
2. Set appropriate widget sizes
3. Add section headers using text widgets
4. Apply color schemes:
   - Green for positive metrics (PASS)
   - Red for negative metrics (FAIL)
   - Gray for neutral (NEEDS REVIEW)

### Step 6: Set Permissions
- **Owner:** Sales team lead
- **Can Edit:** Sales team, Customer Success
- **Can View:** All sales and CS users
- **Can Embed:** Yes (for customer-facing portals if needed)

---

## Customer-Facing Features

### What Makes This Sales-Ready:

1. **Clear, Non-Technical Language**
   - "Pass Rate" not "Success Rate"
   - "Verification" not "Scan"
   - "Properties" not "Property IDs"

2. **Visual Impact**
   - Color-coded status (green/red/gray)
   - Large counter widgets for key metrics
   - Trend charts show improvement over time

3. **Drill-Down Capability**
   - Start with high-level metrics
   - Click to see property-level detail
   - View individual submissions

4. **Actionable Insights**
   - Top failure reasons help improve submission quality
   - Geographic breakdown shows regional patterns
   - Provider comparison demonstrates value

5. **Flexible Filtering**
   - Show specific company data during demos
   - Compare time periods
   - Focus on specific properties

---

## Sales Team Talking Points

### Opening (Executive Summary)
> "Over the past 30 days, we've processed [X] identity verifications across your [Y] properties with a [Z]% pass rate."

### Performance Trends
> "Your pass rate has been consistently above 90%, showing excellent applicant quality and submission processes."

### Failure Analysis
> "When verifications do fail, the most common reason is [X], which suggests [actionable insight]."

### Geographic Insights
> "Your properties in [State] show particularly strong performance with a [X]% pass rate."

### Provider Value
> "Our CLEAR integration provides enhanced verification with [features], resulting in [benefits]."

---

## Refresh Schedule

- **Real-time:** Dashboard queries run on-demand when opened
- **Cache:** 15 minutes (configurable)
- **Data Lag:** Typically 5-30 minutes (Fivetran sync + DLT pipeline)

---

## Comparison to Other Dashboards

| Feature | Sales IDV Dashboard | CLEAR Dashboard | IDV Usage Dashboard |
|---------|-------------------|----------------|-------------------|
| **Audience** | Customer-facing | Internal Ops | Internal Ops |
| **Purpose** | Sales demos | Provider migration | Capacity planning |
| **Filtering** | Company/Property | None | Limited |
| **Detail Level** | Individual scans | Aggregate only | Property-level |
| **Metrics Focus** | Pass rate, trends | Provider adoption | Volume forecasting |
| **Visual Style** | Clean, simple | Technical | Analytical |

---

## Maintenance & Updates

### Regular Reviews:
- **Weekly:** Check for any query performance issues
- **Monthly:** Review with sales team for feedback
- **Quarterly:** Add new visualizations based on sales needs

### Data Quality Checks:
- Verify pass rate calculations are accurate
- Ensure filters are working correctly
- Check for missing or NULL values in key fields

### Future Enhancements:
- [ ] Add benchmarking against industry averages
- [ ] Include cost savings calculations
- [ ] Add applicant experience metrics
- [ ] Export capability for customer reports
- [ ] Mobile-responsive layout

---

## Troubleshooting

### Issue: Pass rate seems incorrect
- **Check:** Ensure query filters are applied correctly
- **Verify:** `results_provided_at IS NOT NULL` is in all queries
- **Confirm:** Date range matches expectations

### Issue: Filters not working
- **Check:** Parameter names match exactly (`:company_filter`, etc.)
- **Verify:** Cascading filters are configured properly
- **Test:** Clear all filters and reapply

### Issue: No data showing
- **Check:** Date range includes data
- **Verify:** Company/property has IDV enabled
- **Confirm:** Fivetran sync is running

---

## Contact & Support

**Dashboard Owner:** Data Engineering Team
**For Questions:** #data-team Slack channel
**For Dashboard Access:** Contact your Sales Manager
**For Technical Issues:** Create ticket in Jira (Data Team board)

---

## Appendix: Sample Use Cases

### Use Case 1: Quarterly Business Review
**Scenario:** Showing a customer their quarterly IDV performance

**Steps:**
1. Select customer's company in filter
2. Set date range to last quarter
3. Start with Executive Summary
4. Show trend charts (improvement over time)
5. Drill into property-level details
6. Discuss any patterns or anomalies

### Use Case 2: New Customer Demo
**Scenario:** Demonstrating IDV capabilities to a prospect

**Steps:**
1. Use aggregate view (no company filter)
2. Show overall pass rate and volume
3. Highlight failure reason breakdown
4. Demonstrate how filtering works
5. Show geographic performance
6. Explain provider comparison

### Use Case 3: Property Onboarding
**Scenario:** Reviewing IDV setup for a new property

**Steps:**
1. Filter to specific property
2. Set date range to "since launch"
3. Review initial scan volume
4. Check pass rate trends
5. Identify any failure patterns
6. Provide recommendations

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Next Review:** 2025-11-30
