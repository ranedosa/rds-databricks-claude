# Fixed Notebooks - Ready to Use

## ✅ All Schema Issues Resolved

I've fixed all the SQL schema issues found during testing:

1. **`id_verifications` table join** - Changed from `entry_id` to `applicant_detail_id`
2. **Removed non-existent columns:**
   - `decision` (doesn't exist in income/asset verification tables)
   - `calculated_income` (doesn't exist in income_verification_submissions)
3. **Replaced with actual columns:**
   - Using `review_eligibility` and `rejection_reason` instead

---

## 🎯 Recommended Notebook to Use

### **Python Notebook** (BEST OPTION)
```
https://dbc-9ca0f5e0-2208.cloud.databricks.com/workspace/Users/dane@snappt.com/pegasus_bank_linking_applicant_report
```

**Why use this one:**
- ✅ Properly structured with separate cells for each query
- ✅ All schema fixes applied
- ✅ Ready to "Run All" immediately
- ✅ Contains all 4 report sections:
  1. Applicant-Level Detail
  2. Executive Summary
  3. Issue Detection
  4. Property Performance

**How to use:**
1. Click the link
2. Click "Run All" at the top
3. Results will display in interactive tables below each cell
4. Export results using Databricks export options

---

## Alternative SQL Notebooks

### Simple Checkbox View
```
https://dbc-9ca0f5e0-2208.cloud.databricks.com/workspace/Users/dane@snappt.com/pegasus_simple_checkbox_view
```
- Contains 2 separate queries
- **Note:** Run each query individually (they can't run together in one cell)
- Query 1: Applicant checkbox view
- Query 2: Summary metrics

### Comprehensive Report
```
https://dbc-9ca0f5e0-2208.cloud.databricks.com/workspace/Users/dane@snappt.com/pegasus_comprehensive_applicant_report
```
- Contains 4 separate queries
- **Note:** Run each query individually
- All schema fixes applied

---

## Schema Changes Made

### Fixed Joins
**Before:**
```sql
LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.entry_id = ad.entry_id
```

**After:**
```sql
LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ad.applicant_id
```

### Fixed Column References
**Before:**
```sql
STRING_AGG(DISTINCT ivs.decision, ', ') as income_decisions,
SUM(ivs.calculated_income) as total_calculated_income
```

**After:**
```sql
STRING_AGG(DISTINCT ivs.rejection_reason, ', ') as income_rejection_reasons
-- Removed calculated_income (doesn't exist)
```

---

## Next Steps

1. **Open the Python notebook** (link above)
2. **Click "Run All"**
3. **Review the 4 sections of results:**
   - Applicant-Level Detail (main report showing each applicant)
   - Executive Summary (KPIs and percentages)
   - Issue Detection (glitches and anomalies)
   - Property Performance (metrics by property)

4. **Export results** as needed for Pegasus

---

## All Requirements Met

✅ Applicant-level data (not aggregated)
✅ Bank linking adoption tracking
✅ ID verification correlation
✅ Pass/Fail recommendations with reasons
✅ Program usage validation
✅ Decision visibility
✅ Automated issue detection

The notebooks are ready to use immediately!
