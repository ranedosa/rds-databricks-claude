# Sales-Focused IDV Results Dashboard - Widget Explanation

**Date:** 2025-10-30
**Dashboard Type:** Customer-Facing Sales Dashboard
**Purpose:** Showcase identity verification results and performance to customers during sales demos and business reviews

---

## Dashboard Filters (Interactive Controls)

### 1. Company Name Filter
**Widget Type:** Multi-Select Dropdown
**What it shows:** List of all companies with IDV-enabled properties
**Business Value:** Allows sales team to instantly filter entire dashboard to a specific customer during demos
**Customer Benefit:** Shows their specific performance data in isolation

### 2. Property Name Filter
**Widget Type:** Multi-Select Dropdown (Cascading)
**What it shows:** Properties filtered by selected company
**Business Value:** Drill down to specific property performance for detailed discussions
**Customer Benefit:** Identifies top-performing and underperforming locations

### 3. Date Range Selector
**Widget Type:** Date Range Picker
**What it shows:** Customizable date range (default: last 30 days)
**Business Value:** Compare performance across different time periods (weekly, monthly, quarterly)
**Customer Benefit:** Track improvement trends and seasonal patterns

---

## Executive Summary (Key Performance Indicators)

### 4. Total IDV Scans
**Widget Type:** Counter
**What it shows:** Total number of identity verifications processed in selected timeframe
**Business Value:** Demonstrates platform usage and adoption
**Customer Benefit:** Shows volume of fraud prevention coverage

### 5. Pass Rate Percentage
**Widget Type:** Counter (Color-Coded)
**What it shows:** Percentage of verifications that passed (Green >90%, Yellow 80-90%, Red <80%)
**Business Value:** Key success metric for customer satisfaction
**Customer Benefit:** Measures applicant quality and process effectiveness

### 6. Active Properties
**Widget Type:** Counter
**What it shows:** Number of properties with IDV scans during timeframe
**Business Value:** Shows platform adoption breadth
**Customer Benefit:** Confirms rollout success across portfolio

### 7. Active Companies
**Widget Type:** Counter
**What it shows:** Number of companies using IDV (primarily for aggregate view)
**Business Value:** Demonstrates platform scale for prospects
**Customer Benefit:** Validates peer usage and industry adoption

---

## Performance Trends Over Time

### 8. Daily Pass/Fail Volume Trend
**Widget Type:** Stacked Bar Chart
**What it shows:** Daily breakdown of verification results by status (Pass/Fail/Needs Review)
**Key Insight:** Shows volume trends and identifies anomaly days
**Business Value:** Spots quality issues quickly, demonstrates consistent performance
**Customer Benefit:** Validates service reliability and helps plan for peak periods

### 9. Weekly Pass Rate Trend
**Widget Type:** Line Chart
**What it shows:** Pass rate percentage tracked week-over-week
**Key Insight:** Reveals performance improvement or degradation trends
**Business Value:** Proves value delivery over time
**Customer Benefit:** Shows ROI through improving verification success rates

---

## Status Distribution Analysis

### 10. Pass/Fail/Review Distribution
**Widget Type:** Pie Chart
**What it shows:** Percentage breakdown of all verification statuses
**Key Insight:** Quick visual of overall health (ideal: 90%+ green)
**Business Value:** Simple, powerful visual for executive presentations
**Customer Benefit:** Easy-to-understand performance snapshot

### 11. Top Failure Reasons
**Widget Type:** Horizontal Bar Chart
**What it shows:** Top 10 reasons why verifications fail, sorted by frequency
**Key Insight:** Identifies systemic issues vs. random failures
**Business Value:** Drives actionable process improvements
**Customer Benefit:** Shows specific areas to coach applicants or adjust requirements

**Common Failure Reasons:**
- Document quality issues
- Photo mismatch
- Expired identification
- Information inconsistency
- Blurry or incomplete images

---

## Provider Performance Comparison

### 12. CLEAR vs Incode Performance
**Widget Type:** Grouped Bar Chart
**What it shows:** Side-by-side comparison of pass rates and volumes between IDV providers
**Key Insight:** Demonstrates relative value of each provider
**Business Value:** Justifies provider selection and migration decisions
**Customer Benefit:** Validates investment in premium verification services

---

## Geographic Performance

### 13. Performance by State
**Widget Type:** Table (Color-Coded by Pass Rate)
**What it shows:** Breakdown of properties, scans, and pass rates by state
**Key Insight:** Reveals geographic patterns in verification success
**Business Value:** Identifies regional training needs or market characteristics
**Customer Benefit:** Optimizes regional operations and resource allocation

**Columns:**
- State
- Number of Properties
- Total Scans
- Passed
- Failed
- Pass Rate %

---

## Property-Level Performance

### 14. Property Performance Table
**Widget Type:** Sortable Table
**What it shows:** Detailed performance metrics for each property including:
- Property name and company
- Location (state, city)
- IDV provider
- Total scans, passed, failed, needs review
- Pass rate percentage
- First scan date
- Most recent scan date
- Days since last scan

**Key Insight:** Identifies high-performers and properties needing attention
**Business Value:** Enables targeted account management
**Customer Benefit:** Benchmarks properties against each other, drives best practice sharing

**Use Cases:**
- Identify properties with <90% pass rate for training
- Spot inactive properties (high "days since last scan")
- Recognize top-performing locations
- Compare similar property types

---

## Recent Submission Details

### 15. Recent Submissions Table
**Widget Type:** Detailed Table (Last 100 Records)
**What it shows:** Individual verification submissions with full details:
- Scan date and time
- Company and property names
- Property state
- Status (Pass/Fail/Needs Review)
- Specific failure reason (if failed)
- IDV provider used
- Verification level (Enhanced/Basic for CLEAR)
- Days ago (recency)

**Key Insight:** Granular audit trail for investigation
**Business Value:** Complete transparency builds trust
**Customer Benefit:** Enables spot-checking and dispute resolution

**Common Use Cases:**
- Verify specific applicant verification
- Investigate recent failures
- Audit verification quality
- Track provider performance

---

## Weekly Summary Metrics

### 16. Weekly Performance Summary
**Widget Type:** Line Chart with Multiple Series
**What it shows:** Week-by-week tracking of:
- Total scans
- Passed count
- Failed count
- Pass rate %

**Key Insight:** Smooths daily volatility to reveal true trends
**Business Value:** Better for quarterly business reviews
**Customer Benefit:** Clear view of sustained performance vs. daily noise

---

## Company Overview Table

### 17. Company Performance Overview
**Widget Type:** Aggregate Table
**What it shows:** Company-level summary showing:
- Company name and ID
- Number of properties
- Total scans
- Passed/Failed/Needs Review counts
- Pass rate
- First and most recent scan dates

**Key Insight:** Portfolio-level view for multi-property operators
**Business Value:** Account health dashboard for customer success
**Customer Benefit:** Demonstrates value across entire organization

---

## Sales Demo Strategy

### Opening (30 seconds)
**Start with Executive Summary counters:**
> "In the past 30 days, you've processed [X] verifications across [Y] properties with a [Z]% success rate."

**Impact:** Immediate, concrete value statement

### Performance Deep-Dive (2 minutes)
**Show trend charts:**
- Daily volume shows consistent usage
- Weekly pass rate shows improvement or stability
- Status distribution confirms quality

**Impact:** Builds confidence in service reliability

### Problem-Solving (2 minutes)
**Display failure reasons and property table:**
- Identify top failure patterns
- Show how data drives improvements
- Highlight properties needing attention

**Impact:** Positions solution as strategic partner, not just vendor

### Success Stories (1 minute)
**Filter to top-performing properties:**
- Show 95%+ pass rates
- Highlight volume growth
- Demonstrate geographic success

**Impact:** Proof of concept for expansion

### Next Steps (30 seconds)
**Recent submissions for transparency:**
- Live data, not canned demo
- Real applicant results
- Actionable insights

**Impact:** Trust through transparency

---

## Key Metrics Definitions

### Pass Rate
```
Pass Rate = (Passed Scans / Total Scans with Results) × 100
```
**Industry Benchmark:** 85-95% (varies by market)

### Status Types
- **PASS:** Identity verified successfully, applicant proceeds
- **FAIL:** Identity verification failed, requires alternative verification or rejection
- **NEEDS REVIEW:** Inconclusive result, manual review recommended

### Verification Levels (CLEAR Only)
- **Enhanced (Full):** Comprehensive identity verification with document validation, selfie matching, and additional checks
- **Basic (Lite):** Streamlined verification focusing on primary identity validation

---

## Data Freshness

- **Update Frequency:** Real-time (queries run on dashboard load)
- **Data Lag:** 5-30 minutes (Fivetran sync + DLT pipeline)
- **Historical Data:** All scans since IDV launch
- **Cache Duration:** 15 minutes

---

## When to Use This Dashboard

### ✅ Perfect For:
- **Sales Demos:** Showing prospects how reporting works
- **Customer Business Reviews:** Quarterly performance discussions
- **Account Management:** Tracking customer health
- **Executive Presentations:** High-level visual impact
- **Property Onboarding:** Reviewing initial rollout success

### ❌ Not Ideal For:
- **Internal Operations:** Use "IDV Usage Dashboard" for capacity planning
- **Provider Migration:** Use "CLEAR Dashboard" for technical tracking
- **Fraud Analysis:** Use "Edited Submissions Dashboard" for fraud-specific insights
- **Billing/Finance:** Need dedicated revenue/cost tracking

---

## Competitive Advantages Demonstrated

### 1. Transparency
Unlike competitors, we show:
- Individual submission details
- Specific failure reasons
- Real-time data access

### 2. Actionable Insights
We don't just report pass/fail:
- Identify improvement opportunities
- Show geographic patterns
- Compare provider performance

### 3. Customer Empowerment
Dashboard enables customers to:
- Self-serve performance data
- Train teams based on failure patterns
- Benchmark properties against each other

### 4. Scalability
Visual proof of:
- Multi-property management
- Portfolio-wide visibility
- Enterprise-grade reporting

---

## Customization Options

### For Enterprise Customers:
- [ ] Add custom branding (logo, colors)
- [ ] Include customer-specific KPIs
- [ ] Embed in customer portal
- [ ] Scheduled email reports
- [ ] API access for data export

### For Sales Team:
- [ ] Clone per sales rep (personalized)
- [ ] Add notes/annotations
- [ ] Save common filter combinations
- [ ] Export to PDF for proposals
- [ ] Mobile-responsive view

---

## ROI Storytelling Framework

### Volume Impact
"You processed [X] verifications this month. At [$Y] per manual verification, you saved [X × Y] in operational costs."

### Quality Impact
"Your [Z]% pass rate means you're preventing [failed count] potential fraud cases, protecting your revenue and reputation."

### Efficiency Impact
"With [X] properties actively using IDV, you've standardized verification across your portfolio, reducing compliance risk."

### Time Impact
"Automated verification delivers results in [seconds/minutes], compared to [hours/days] for manual processes."

---

## Dashboard Evolution Roadmap

### Phase 2 Enhancements:
- [ ] Add benchmarking vs. industry averages
- [ ] Include cost/ROI calculations
- [ ] Applicant experience metrics (time to complete)
- [ ] Integration with fraud detection results
- [ ] Predictive analytics for volume forecasting

### Phase 3 Advanced Features:
- [ ] AI-powered insights and recommendations
- [ ] Automated anomaly detection and alerting
- [ ] Custom report builder
- [ ] Multi-language support
- [ ] White-label embedding for customer portals

---

## Related Dashboards

| Dashboard Name | Purpose | Audience | When to Use |
|---------------|---------|----------|-------------|
| **IDV Usage Dashboard** | Volume forecasting & capacity planning | Internal Ops | Internal planning meetings |
| **CLEAR Dashboard** | Provider adoption tracking | Internal Ops | Migration project management |
| **Edited Submissions Dashboard** | Fraud detection analysis | Sales/Ops | Fraud-focused demos |
| **Sales - IDV Results** (This) | Customer performance reporting | Sales/CS | Customer-facing meetings |

---

## Success Metrics for This Dashboard

### Dashboard Adoption:
- Sales team usage frequency
- Number of customer demos using dashboard
- Time saved vs. manual reporting

### Business Impact:
- Deals closed featuring dashboard
- Customer retention (correlated with dashboard access)
- Upsells driven by insights

### Customer Satisfaction:
- NPS score for reporting quality
- Feature requests for enhancements
- Self-service usage (customers accessing directly)

---

## Training & Onboarding

### For Sales Team:
1. **30-min intro session:** Dashboard navigation and filtering
2. **Demo practice:** Role-play customer presentations
3. **Cheat sheet:** Key talking points for each widget
4. **Q&A scenarios:** Handling common customer questions

### For Customers:
1. **Quick start guide:** 5-minute video walkthrough
2. **Use case library:** Example analyses
3. **Support contact:** How to get help
4. **Feedback channel:** Request features

---

## Appendix: Sample Customer Questions & Answers

**Q: "Why did this specific verification fail?"**
**A:** *Filter to Recent Submissions table, find the specific scan, show score_reason field.*

**Q: "How does our pass rate compare to industry average?"**
**A:** *Show their pass rate counter vs. benchmark (~90%). If above, highlight. If below, use Failure Reasons to identify improvements.*

**Q: "Which of our properties are performing best/worst?"**
**A:** *Sort Property Performance Table by pass rate, show top and bottom performers.*

**Q: "Has our performance improved since we started?"**
**A:** *Adjust date range to "since launch," show Weekly Trend chart with upward trajectory.*

**Q: "What's causing most of our failures?"**
**A:** *Point to Top Failure Reasons chart, explain the most common issue and remediation steps.*

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Dashboard Version:** 1.0 (To Be Built)
**Feedback:** #sales-enablement Slack channel
