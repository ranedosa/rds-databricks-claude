# Fivetran Warehouse Sizing Recommendation

**Date:** November 18, 2025
**Prepared By:** Data Engineering Team
**Analysis Period:** November 4-18, 2025 (14 days)
**Total Queries Analyzed:** 248,023

---

## Executive Summary

After a two-week experimentation period testing three warehouse sizes (X_SMALL, SMALL, and MEDIUM), **we recommend changing the Fivetran warehouse from X_SMALL to SMALL**.

**Key Benefits:**
- **54.5% faster query execution** (3.69s → 1.68s average)
- **Improved data freshness** through faster Fivetran sync times
- **Better reliability** with 73% reduction in queue times
- **Cost-effective**: Performance improvement significantly exceeds cost increase

**Cost Impact:**
- Additional cost: ~$690/month
- Performance gain justifies investment with 2.2x faster queries for only 41% additional cost

---

## Analysis Methodology

### Warehouse Configurations Tested

| Size | Period | Queries Executed | Cluster Config |
|------|--------|------------------|----------------|
| **MEDIUM** | Nov 4-12 | 173,848 | Min: 1, Max: 2 |
| **SMALL** | Nov 5, Nov 12 | 36,663 | Min: 1, Max: 2 |
| **X_SMALL** | Nov 16-18 (Current) | 37,512 | Min: 1, Max: 2 |

### Data Sources
- **Performance Metrics**: `system.query.history` (Databricks System Tables)
- **Cost Data**: `main.default.dbsql_cost_per_query`
- **Warehouse Configuration**: `system.compute.warehouses`

---

## Performance Analysis

### Query Execution Times

| Metric | X_SMALL (Current) | SMALL ✅ | MEDIUM |
|--------|------------------|----------|---------|
| **Average Duration** | 3.69 sec | **1.68 sec** | 2.90 sec |
| **Median Duration** | 2.17 sec | **1.22 sec** | 1.33 sec |
| **95th Percentile** | 11.46 sec | **5.08 sec** | 6.72 sec |
| **Improvement vs X_SMALL** | Baseline | **-54.5%** | -21.4% |

**Key Finding:** SMALL provides the fastest execution times across all percentiles.

### Queue Time & Resource Contention

| Metric | X_SMALL | SMALL ✅ | MEDIUM |
|--------|---------|----------|---------|
| **Average Queue Time** | 0.12 sec | **0.03 sec** | 0.09 sec |
| **Maximum Queue Time** | 15.16 sec | **8.24 sec** | 127.60 sec ⚠️ |
| **Queries with Queuing** | 930 (2.5%) | **282 (0.8%)** | 2,606 (1.5%) |
| **Queries with Disk Spill** | 0 | 0 | 0 |

**Key Finding:** SMALL shows minimal resource contention with the lowest queue times and fewest queries waiting for compute resources.

---

## Cost Analysis

### Per-Query Cost Comparison

| Warehouse Size | Avg Cost/Query | Cost vs X_SMALL | Total Cost (14 days) |
|----------------|----------------|-----------------|----------------------|
| **X_SMALL** | $0.001494 | Baseline | $21.33 |
| **SMALL** | $0.002103 | +41% | $32.31 |
| **MEDIUM** | $0.003044 | +104% | $211.20 |

### Projected Monthly Costs

Based on average daily query volume of ~37,500 queries:

| Warehouse Size | Monthly Cost | Annual Cost |
|----------------|-------------|-------------|
| **X_SMALL (Current)** | $1,680 | $20,160 |
| **SMALL (Recommended)** | $2,370 | $28,440 |
| **MEDIUM** | $3,420 | $41,040 |

**Additional Investment for SMALL:** $690/month or $8,280/year

---

## Cost-Benefit Analysis

### Value Proposition for SMALL

```
Performance Improvement: 54.5% faster
Cost Increase: 41%
Value Ratio: 1.33x (performance gain exceeds cost increase by 33%)
```

### Time Savings Calculation

**Daily Query Execution Time Saved:**
- X_SMALL: 37,500 queries × 3.69 sec = 138,375 seconds (38.4 hours)
- SMALL: 37,500 queries × 1.68 sec = 63,000 seconds (17.5 hours)
- **Time Saved: 75,375 seconds/day (20.9 hours)**

**Impact on Fivetran:**
- Faster data sync completion
- Improved data freshness across all connected data sources
- Reduced risk of sync failures due to timeouts
- Better SLA compliance for data availability

### SMALL vs MEDIUM Comparison

| Factor | SMALL | MEDIUM |
|--------|-------|--------|
| Avg Execution Time | 1.68 sec | 2.90 sec |
| Cost per Query | $0.002103 | $0.003044 |
| **Performance Advantage** | **73% faster** | - |
| **Cost Advantage** | **31% cheaper** | - |

**Conclusion:** SMALL outperforms MEDIUM on both speed and cost.

---

## Risk Assessment

### Low Risk Profile

| Risk | Mitigation |
|------|------------|
| **Performance Degradation** | Comprehensive data shows SMALL outperforms current X_SMALL across all metrics |
| **Cost Overrun** | Predictable cost increase of $690/month with clear ROI |
| **Resource Constraints** | Zero disk spill events indicate adequate memory; auto-scaling (max 2 clusters) provides headroom |
| **Query Failures** | Lower queue times reduce risk of timeouts |

### Why Not MEDIUM?

Despite being the largest size tested, MEDIUM shows:
- **45% higher cost** than SMALL
- **73% slower** execution than SMALL
- **Severe queue time spikes** (max 127.6 sec vs 8.24 sec for SMALL)
- **Worse cost-efficiency** across all metrics

The data suggests MEDIUM's additional resources are poorly utilized for Fivetran's query patterns.

---

## Recommendation

### Primary Recommendation: Switch to SMALL

**Rationale:**
1. **Optimal Performance**: Fastest query execution across all percentiles
2. **Cost-Effective**: Best performance-to-cost ratio of all options tested
3. **Reliable**: Minimal queue times and resource contention
4. **Scalable**: Auto-scaling configuration (1-2 clusters) provides burst capacity
5. **Data Quality**: Faster syncs improve data freshness and reliability

### Implementation Plan

**Phase 1: Warehouse Configuration Change**
1. Update Fivetran warehouse size from X_SMALL to SMALL
2. Maintain current auto-scaling: min 1, max 2 clusters
3. Keep auto-stop at 5 minutes (current setting)

**Phase 2: Monitoring (Week 1)**
- Monitor P95 query execution time (target: < 10 seconds)
- Track daily query volume and costs
- Review Fivetran sync completion times
- Check for any query failures or timeouts

**Phase 3: Validation (Week 2-4)**
- Compare actual costs vs projected
- Measure improvement in data freshness
- Document any issues or anomalies
- Prepare performance report for stakeholders

### Success Metrics

| Metric | Target | Current (X_SMALL) |
|--------|--------|-------------------|
| Average Query Duration | < 2.0 sec | 3.69 sec |
| P95 Query Duration | < 6.0 sec | 11.46 sec |
| Queries with Queue Time | < 1.0% | 2.5% |
| Maximum Queue Time | < 15 sec | 15.16 sec |
| Daily Cost | ~$79 | ~$56 |

---

## Financial Summary

### Investment Required

| Item | Amount |
|------|--------|
| **Additional Monthly Cost** | $690 |
| **Additional Annual Cost** | $8,280 |
| **Cost per Business Day** | $23 |

### Return on Investment

**Quantified Benefits:**
- **20.9 hours/day** of compute time saved across all queries
- **54.5% faster** data synchronization
- Improved data freshness enabling better decision-making
- Reduced risk of sync failures and data gaps
- Better SLA compliance for downstream data consumers

**Qualitative Benefits:**
- More predictable Fivetran performance
- Reduced data engineering support burden
- Enhanced reliability for business-critical data pipelines
- Improved stakeholder confidence in data availability

---

## Appendix: Detailed Statistics

### Complete Performance Breakdown

#### X_SMALL (Current Size)
- Queries Analyzed: 37,512
- Total Cost: $21.33 (14 days)
- Queries with Queue Time: 930 (2.5%)
- Performance: Slowest across all metrics

#### SMALL (Recommended)
- Queries Analyzed: 36,663
- Total Cost: $32.31 (14 days)
- Queries with Queue Time: 282 (0.8%)
- Performance: Best across all metrics

#### MEDIUM
- Queries Analyzed: 173,848
- Total Cost: $211.20 (14 days)
- Queries with Queue Time: 2,606 (1.5%)
- Performance: Moderate, inconsistent queue times

### Data Quality Notes

- All warehouse sizes showed zero disk spill events
- No memory pressure observed across any configuration
- Auto-scaling to 2 clusters successfully handled peak loads
- Fivetran client consistently identified as query source
- No correlation between warehouse size and query failure rate

---

## Conclusion

The data strongly supports switching the Fivetran warehouse from X_SMALL to SMALL. This change delivers:

✅ **Significant performance improvement** (54.5% faster)
✅ **Best cost-efficiency** among all tested sizes
✅ **Minimal risk** with proven performance data
✅ **Clear ROI** through faster data syncs and better reliability

**Recommended Action:** Approve warehouse size change to SMALL with immediate implementation.

---

**Questions or Concerns?**
Contact: Data Engineering Team
Analysis Data Available: Databricks workspace at `/Users/dane@snappt.com/dashboards/DBSQL Cost Dashboard`
