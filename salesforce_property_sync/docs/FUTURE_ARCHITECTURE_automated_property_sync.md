# Future Architecture: Automated Property & Feature Sync

**Date:** 2025-11-21
**Status:** Implementation Plan
**Goal:** Fully automated, end-to-end property and feature data sync

---

## Overview

We need **two Census syncs** working together:

1. **Sync 1: New Properties** (INSERT) - Creates new property records with feature data
2. **Sync 2: Feature Updates** (UPDATE) - Keeps feature data accurate for existing properties

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Snappt Production Database (RDS PostgreSQL)                     │
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │ public.properties    │                                       │
│  │ (18,941 records)     │                                       │
│  └──────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Fivetran sync
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Databricks (Unity Catalog)                                      │
│                                                                  │
│  ┌──────────────────────┐     ┌─────────────────────────────┐  │
│  │ rds.pg_rds_public.   │     │ crm.sfdc_dbx.               │  │
│  │ properties           │◄────┤ product_property_w_features │  │
│  │                      │     │ (22,784 records)            │  │
│  └──────────────────────┘     └─────────────────────────────┘  │
│             │                              │                    │
│             │                              │                    │
│             │  ┌───────────────────────────┘                    │
│             │  │                                                │
│             ▼  ▼                                                │
│  ┌─────────────────────────────────────────────────┐           │
│  │ VIEW: crm.sfdc_dbx.new_properties_with_features │           │
│  │ (Properties not yet in Salesforce)              │           │
│  └─────────────────────────────────────────────────┘           │
│             │                                                   │
│             │                                                   │
│             │  ┌────────────────────────────────────┐           │
│             │  │ VIEW: crm.sfdc_dbx.                │           │
│             │  │ product_property_feature_sync      │           │
│             │  │ (Existing properties w/ mismatches)│           │
│             │  └────────────────────────────────────┘           │
│             │                              │                    │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              │ Census Sync 1 (INSERT)       │ Census Sync 2 (UPDATE)
              │                              │
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Salesforce                                                       │
│                                                                  │
│  ┌──────────────────────────────────────────┐                   │
│  │ product_property_c (staging table)       │                   │
│  │                                           │                   │
│  │ - Basic property data                    │                   │
│  │ - Product feature flags (14 fields)      │                   │
│  │ - Product enablement dates               │                   │
│  └──────────────────────────────────────────┘                   │
│              │                                                   │
│              │ Salesforce Flow triggers                          │
│              │ "Product Property | After | Rollup Flow"          │
│              ▼                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ property_c (production table)            │                   │
│  │ (216,892 records)                        │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sync 1: New Properties with Features (INSERT)

### Purpose
Create new property records in Salesforce with **complete feature data from day 1**.

### Source
**Databricks View:** `crm.sfdc_dbx.new_properties_with_features`

### Query
```sql
CREATE OR REPLACE VIEW crm.sfdc_dbx.new_properties_with_features AS
SELECT
    -- Property identifiers
    CAST(rds.id AS STRING) as snappt_property_id_c,
    CAST(rds.id AS STRING) as reverse_etl_id_c,

    -- Basic property info
    rds.name,
    rds.entity_name as entity_name_c,
    rds.address as address_street_s,
    rds.city as address_city_s,
    rds.state as address_state_code_s,
    rds.zip as address_postal_code_s,
    rds.phone as phone_c,
    rds.email as email_c,
    rds.website as website_c,
    rds.logo as logo_c,
    rds.unit as unit_c,
    rds.status as status_c,
    CAST(rds.company_id AS STRING) as company_id_c,
    rds.company_short_id as company_short_id_c,
    rds.short_id as short_id_c,
    rds.bank_statement as bank_statement_c,
    rds.paystub as paystub_c,
    rds.unit_is_required as unit_is_required_c,
    rds.phone_is_required as phone_is_required_c,
    rds.identity_verification_enabled as identity_verification_enabled_c,

    -- Product feature flags from product_property_w_features
    COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
    feat.fraud_enabled_at as fraud_detection_start_date_c,
    feat.fraud_updated_at as fraud_detection_updated_date_c,

    COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
    feat.iv_enabled_at as income_verification_start_date_c,
    feat.iv_updated_at as income_verification_updated_date_c,

    COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
    feat.idv_enabled_at as id_verification_start_date_c,
    feat.idv_updated_at as id_verification_updated_date_c,

    COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
    feat.idv_only_enabled_at as idv_only_start_date_c,
    feat.idv_only_updated_at as idv_only_updated_date_c,

    COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
    feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
    feat.payroll_linking_updated_at as connected_payroll_updated_date_c,

    COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
    feat.bank_linking_enabled_at as bank_linking_start_date_c,
    feat.bank_linking_updated_at as bank_linking_updated_date_c,

    COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
    feat.vor_enabled_at as vor_start_date_c,
    feat.vor_updated_at as vor_updated_date_c,

    -- Required for Salesforce
    FALSE as not_orphan_record_c,
    TRUE as trigger_rollups_c

FROM rds.pg_rds_public.properties rds
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON CAST(rds.id AS STRING) = feat.property_id
LEFT JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE
    -- Only include properties NOT yet in Salesforce
    sf.snappt_property_id_c IS NULL
    AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
    AND rds.status = 'ACTIVE'
ORDER BY rds.updated_at DESC;
```

### Census Configuration

**Model:**
- Name: `New Properties with Features`
- Source: Databricks view `crm.sfdc_dbx.new_properties_with_features`

**Sync:**
- Name: `New Properties → Salesforce (INSERT)`
- Destination: Salesforce `Product_Property__c`
- Sync Key: `Reverse_ETL_ID__c` or `snappt_property_id_c`
- Sync Behavior: **INSERT** new records only
- Schedule: **Daily at 2am** (or hourly if needed)

**Field Mappings:**
- All 44 fields (21 property fields + 23 feature fields)
- See complete list in appendix

### Key Points

✅ **Includes feature data from day 1** - No need for backfill later
✅ **Only syncs NEW properties** - WHERE clause ensures no duplicates
✅ **Self-filtering** - View automatically excludes properties already in SF
✅ **Scheduled** - Runs daily to catch new properties

---

## Sync 2: Feature Updates for Existing Properties (UPDATE)

### Purpose
Keep feature data accurate for properties **already in Salesforce**.

### Source
**Databricks View:** `crm.sfdc_dbx.product_property_feature_sync` (already created!)

### Query
```sql
CREATE OR REPLACE VIEW crm.sfdc_dbx.product_property_feature_sync AS
SELECT
    sf.snappt_property_id_c,
    sf.reverse_etl_id_c,
    sf.name,

    -- Feature flags (correct data from product_property_w_features)
    COALESCE(feat.fraud_enabled, FALSE) as fraud_detection_enabled_c,
    feat.fraud_enabled_at as fraud_detection_start_date_c,
    feat.fraud_updated_at as fraud_detection_updated_date_c,

    COALESCE(feat.iv_enabled, FALSE) as income_verification_enabled_c,
    feat.iv_enabled_at as income_verification_start_date_c,
    feat.iv_updated_at as income_verification_updated_date_c,

    COALESCE(feat.idv_enabled, FALSE) as id_verification_enabled_c,
    feat.idv_enabled_at as id_verification_start_date_c,
    feat.idv_updated_at as id_verification_updated_date_c,

    COALESCE(feat.idv_only_enabled, FALSE) as idv_only_enabled_c,
    feat.idv_only_enabled_at as idv_only_start_date_c,
    feat.idv_only_updated_at as idv_only_updated_date_c,

    COALESCE(feat.payroll_linking_enabled, FALSE) as connected_payroll_enabled_c,
    feat.payroll_linking_enabled_at as connected_payroll_start_date_c,
    feat.payroll_linking_updated_at as connected_payroll_updated_date_c,

    COALESCE(feat.bank_linking_enabled, FALSE) as bank_linking_enabled_c,
    feat.bank_linking_enabled_at as bank_linking_start_date_c,
    feat.bank_linking_updated_at as bank_linking_updated_date_c,

    COALESCE(feat.vor_enabled, FALSE) as verification_of_rent_enabled_c,
    feat.vor_enabled_at as vor_start_date_c,
    feat.vor_updated_at as vor_updated_date_c

FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
    ON sf.snappt_property_id_c = feat.property_id
WHERE
    -- Only include properties where SF data != actual data
    (sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE)
     OR sf.income_verification_enabled_c != COALESCE(feat.iv_enabled, FALSE)
     OR sf.id_verification_enabled_c != COALESCE(feat.idv_enabled, FALSE)
     OR sf.idv_only_enabled_c != COALESCE(feat.idv_only_enabled, FALSE)
     OR sf.connected_payroll_enabled_c != COALESCE(feat.payroll_linking_enabled, FALSE)
     OR sf.bank_linking_enabled_c != COALESCE(feat.bank_linking_enabled, FALSE)
     OR sf.verification_of_rent_enabled_c != COALESCE(feat.vor_enabled, FALSE))
ORDER BY sf.name;
```

### Census Configuration

**Model:**
- Name: `Product Property Feature Updates`
- Source: Databricks view `crm.sfdc_dbx.product_property_feature_sync`

**Sync:**
- Name: `Feature Updates → Salesforce (UPDATE)`
- Destination: Salesforce `Product_Property__c`
- Sync Key: `Reverse_ETL_ID__c` or `snappt_property_id_c`
- Sync Behavior: **UPDATE** existing records only
- Schedule: **Hourly** or **Daily**

**Field Mappings:**
- 23 feature fields only (no property fields)
- See complete list in appendix

### Key Points

✅ **Only syncs mismatches** - WHERE clause filters to properties needing updates
✅ **Self-healing** - Automatically catches changes in product_property_w_features
✅ **Efficient** - Won't hit Flow limits (only updates what changed)
✅ **Scheduled** - Runs hourly/daily to keep data accurate

---

## Implementation Steps

### Phase 1: Create New Properties View (1 hour)

**Step 1.1: Create Databricks notebook**

Create: `/Users/dane@snappt.com/new_properties_with_features_view`

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # New Properties with Features View
# MAGIC Creates view for Census to sync NEW properties to Salesforce

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW crm.sfdc_dbx.new_properties_with_features AS
# MAGIC SELECT
# MAGIC     -- [Full query from above]
# MAGIC FROM rds.pg_rds_public.properties rds
# MAGIC LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
# MAGIC LEFT JOIN hive_metastore.salesforce.product_property_c sf
# MAGIC WHERE sf.snappt_property_id_c IS NULL
# MAGIC   AND rds.status = 'ACTIVE';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Verify the view
# MAGIC SELECT
# MAGIC     COUNT(*) as new_properties,
# MAGIC     SUM(CASE WHEN fraud_detection_enabled_c = TRUE THEN 1 ELSE 0 END) as with_fraud,
# MAGIC     SUM(CASE WHEN income_verification_enabled_c = TRUE THEN 1 ELSE 0 END) as with_iv
# MAGIC FROM crm.sfdc_dbx.new_properties_with_features;
```

**Step 1.2: Run notebook**
- Execute in Databricks
- Verify view created
- Check record count

**Step 1.3: Test query**
```sql
SELECT * FROM crm.sfdc_dbx.new_properties_with_features LIMIT 10;
```

---

### Phase 2: Configure Census Sync 1 - New Properties (1 hour)

**Step 2.1: Create Census model**
1. Go to Census → Models → New Model
2. Name: `New Properties with Features`
3. Connection: Databricks
4. Source: Table/View
5. Table: `crm.sfdc_dbx.new_properties_with_features`
6. Save

**Step 2.2: Create Census sync**
1. Go to Census → Syncs → New Sync
2. Name: `New Properties → Salesforce (INSERT)`
3. Source: Model from step 2.1
4. Destination: Salesforce `Product_Property__c`
5. Sync Key: `Reverse_ETL_ID__c` → `reverse_etl_id_c`
6. Sync Behavior: **INSERT** (create new records)
7. Map all 44 fields (see appendix)
8. Save

**Step 2.3: Test sync**
1. Run manually
2. Check first 10 records
3. Validate in Salesforce:
   - Property data correct
   - Feature fields populated
   - Workflow triggers properly

**Step 2.4: Schedule**
- Schedule: Daily at 2am
- Or: Hourly if new properties need faster sync

---

### Phase 3: Update Existing Feature Sync (30 minutes)

**Step 3.1: Verify view exists**
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_sync;
```

This view was already created in our earlier work!

**Step 3.2: Update existing Census sync**

You already have this: https://app.getcensus.com/workspaces/33026/syncs/3326019/overview

**Verify configuration:**
- ✅ Source: `crm.sfdc_dbx.product_property_feature_sync`
- ✅ Sync Behavior: UPDATE
- ✅ Field mappings: 23 feature fields
- ⏳ Schedule: Set to hourly or daily

**Step 3.3: Run initial backfill**
- This will fix the existing 2,815 properties
- After this, only changes will be synced

**Step 3.4: Schedule**
- Hourly: Catches changes quickly
- Daily: Sufficient for most use cases

---

### Phase 4: Monitor & Validate (ongoing)

**Step 4.1: Validation queries**

```sql
-- Check for properties without feature data
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
WHERE sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE);
-- Should return 0 after syncs are working

-- Check new properties view
SELECT COUNT(*) FROM crm.sfdc_dbx.new_properties_with_features;
-- Should decrease as properties get synced

-- Check feature sync view
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_sync;
-- Should be 0 or very low after initial backfill
```

**Step 4.2: Census monitoring**
- Check Census sync runs daily/weekly
- Monitor for errors
- Set up alerts for failures

**Step 4.3: Data quality checks**
- Run validation queries weekly
- Spot check random properties in Salesforce
- Verify feature data matches RDS

---

## How It Works Together

### Scenario 1: New Property Created in RDS

```
1. New property inserted into rds.pg_rds_public.properties
2. Fivetran syncs to Databricks (within minutes)
3. Property appears in crm.sfdc_dbx.new_properties_with_features view
4. Census Sync 1 runs (daily at 2am)
5. Property inserted into Salesforce with ALL feature data
6. Salesforce Flow triggers, creates property_c record
7. ✅ Complete - property in Salesforce with features
```

**Timeline:** New property appears in Salesforce within ~2-24 hours (depending on schedule)

---

### Scenario 2: Product Enabled for Existing Property

```
1. Product enabled in Snappt app (e.g., Fraud Detection turned on)
2. product_property_w_features table updated
3. Fivetran syncs to Databricks crm.sfdc_dbx.product_property_w_features
4. Property appears in crm.sfdc_dbx.product_property_feature_sync view (mismatch detected)
5. Census Sync 2 runs (hourly)
6. Feature fields updated in Salesforce product_property_c
7. ✅ Complete - Salesforce reflects new product enablement
```

**Timeline:** Feature change appears in Salesforce within 1-2 hours

---

### Scenario 3: Product Disabled for Property

```
1. Product disabled in Snappt app
2. product_property_w_features updated (fraud_enabled = FALSE)
3. Fivetran syncs to Databricks
4. Property appears in feature_sync view (mismatch: SF shows TRUE, actual is FALSE)
5. Census Sync 2 runs
6. Feature field updated to FALSE in Salesforce
7. ✅ Complete - Salesforce shows product as disabled
```

**Timeline:** Within 1-2 hours

---

## Benefits of This Architecture

### Automated End-to-End

✅ **No manual CSV uploads** - Everything automated
✅ **No manual backfills** - Self-healing system
✅ **No missing data** - Features included from day 1

### Efficient

✅ **Only syncs what's needed** - New properties or changed features
✅ **Won't hit Flow limits** - Small batches of updates
✅ **Fast** - Changes appear within hours

### Reliable

✅ **Self-healing** - Mismatches automatically detected and fixed
✅ **Always current** - Views show real-time data
✅ **Auditable** - Census logs all sync activity

### Maintainable

✅ **Simple** - Two syncs, two views
✅ **Standard patterns** - Census best practices
✅ **Well documented** - Everything explained

---

## Monitoring & Alerts

### Key Metrics to Track

**1. New properties view size**
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.new_properties_with_features;
```
- **Expected:** Small number (10-50 at most)
- **Alert if:** > 100 (sync may not be running)

**2. Feature sync view size**
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.product_property_feature_sync;
```
- **Expected:** 0-50 (small mismatches)
- **Alert if:** > 500 (something's wrong)

**3. Census sync success rate**
- Monitor in Census UI
- Alert on failures
- Review error logs

**4. Total properties in Salesforce**
```sql
SELECT COUNT(*) FROM hive_metastore.salesforce.product_property_c;
```
- **Expected:** Growing over time
- **Alert if:** Decreasing (data loss)

### Weekly Health Check

Run these queries weekly:

```sql
-- 1. Properties in RDS but not in Salesforce
SELECT COUNT(*)
FROM rds.pg_rds_public.properties rds
LEFT JOIN hive_metastore.salesforce.product_property_c sf
WHERE sf.snappt_property_id_c IS NULL
  AND rds.status = 'ACTIVE';
-- Should be 0 or very small

-- 2. Properties with incorrect feature data
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c sf
LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
WHERE sf.fraud_detection_enabled_c != COALESCE(feat.fraud_enabled, FALSE);
-- Should be 0

-- 3. Properties synced in last 7 days
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) >= CURRENT_DATE() - INTERVAL 7 DAYS;
-- Should show regular activity
```

---

## Troubleshooting Guide

### Issue: New properties not appearing in Salesforce

**Check:**
1. Is property in `new_properties_with_features` view?
2. Did Census Sync 1 run?
3. Any errors in Census sync logs?
4. Is property status = 'ACTIVE'?

**Fix:**
- Run Census sync manually
- Check view query for filters
- Review Census error details

---

### Issue: Feature data not updating

**Check:**
1. Is property in `product_property_feature_sync` view?
2. Did Census Sync 2 run?
3. Is feature actually different in product_property_w_features?

**Fix:**
- Verify feature data in source table
- Run feature sync manually
- Check Salesforce for locks

---

### Issue: Census hitting Flow limits

**Symptoms:**
- Sync shows "completed" but many failures
- Error message mentions Flow governor limits

**Fix:**
1. Feature sync should only update small batches
2. If still hitting limits, reduce sync frequency
3. Or ask SF admin to optimize Flow

---

## Migration Plan from Current State

### Current State
- Properties synced without feature data
- 2,815 properties need feature backfill
- No automated ongoing sync

### Migration Steps

**Week 1:**
- [x] Run Census Sync 2 to fix existing 2,815 properties (already configured)
- [ ] Create `new_properties_with_features` view
- [ ] Set up Census Sync 1 for new properties
- [ ] Test with 10 new properties

**Week 2:**
- [ ] Schedule both Census syncs
- [ ] Run for 1 week and monitor
- [ ] Fix any issues

**Week 3:**
- [ ] Validate data accuracy
- [ ] Document final configuration
- [ ] Train team on monitoring

**Ongoing:**
- [ ] Weekly health checks
- [ ] Monthly data quality review
- [ ] Update documentation as needed

---

## Cost Considerations

### Census Sync Volumes

**Sync 1 (New Properties):**
- Frequency: Daily
- Volume: ~5-20 properties/day (estimate)
- Annual: ~1,800-7,300 syncs/year

**Sync 2 (Feature Updates):**
- Frequency: Hourly
- Volume: ~10-50 updates/hour (estimate)
- Annual: ~87,000-438,000 syncs/year

**Total Census API calls:** ~100k-450k/year

Check if this fits within your Census plan limits.

---

## Appendix

### Complete Field List - Sync 1 (New Properties)

**Property Fields (21):**
1. snappt_property_id_c
2. reverse_etl_id_c
3. name
4. entity_name_c
5. address_street_s
6. address_city_s
7. address_state_code_s
8. address_postal_code_s
9. phone_c
10. email_c
11. website_c
12. logo_c
13. unit_c
14. status_c
15. company_id_c
16. company_short_id_c
17. short_id_c
18. bank_statement_c
19. paystub_c
20. unit_is_required_c
21. phone_is_required_c
22. identity_verification_enabled_c
23. not_orphan_record_c
24. trigger_rollups_c

**Feature Fields (23):**
25. fraud_detection_enabled_c
26. fraud_detection_start_date_c
27. fraud_detection_updated_date_c
28. income_verification_enabled_c
29. income_verification_start_date_c
30. income_verification_updated_date_c
31. id_verification_enabled_c
32. id_verification_start_date_c
33. id_verification_updated_date_c
34. idv_only_enabled_c
35. idv_only_start_date_c
36. idv_only_updated_date_c
37. connected_payroll_enabled_c
38. connected_payroll_start_date_c
39. connected_payroll_updated_date_c
40. bank_linking_enabled_c
41. bank_linking_start_date_c
42. bank_linking_updated_date_c
43. verification_of_rent_enabled_c
44. vor_start_date_c
45. vor_updated_date_c

**Total:** 45 fields

### Complete Field List - Sync 2 (Feature Updates)

**Feature Fields Only (23):**
1. fraud_detection_enabled_c
2. fraud_detection_start_date_c
3. fraud_detection_updated_date_c
4. income_verification_enabled_c
5. income_verification_start_date_c
6. income_verification_updated_date_c
7. id_verification_enabled_c
8. id_verification_start_date_c
9. id_verification_updated_date_c
10. idv_only_enabled_c
11. idv_only_start_date_c
12. idv_only_updated_date_c
13. connected_payroll_enabled_c
14. connected_payroll_start_date_c
15. connected_payroll_updated_date_c
16. bank_linking_enabled_c
17. bank_linking_start_date_c
18. bank_linking_updated_date_c
19. verification_of_rent_enabled_c
20. vor_start_date_c
21. vor_updated_date_c

Plus identifiers:
22. snappt_property_id_c (for matching)
23. reverse_etl_id_c (for matching)

---

## Summary

### What You'll Have

✅ **Fully automated property sync** - New properties flow to Salesforce automatically
✅ **Feature data from day 1** - No backfills needed for new properties
✅ **Self-healing feature sync** - Changes automatically detected and synced
✅ **Efficient & reliable** - Only syncs what's needed, handles errors gracefully
✅ **Easy to monitor** - Clear metrics and health checks

### Total Time to Implement

- Create views: 1 hour
- Configure Census: 1.5 hours
- Test & validate: 1 hour
- **Total: ~3.5 hours**

### Maintenance

- Weekly health checks: 15 minutes
- Monthly data quality review: 30 minutes
- Ad-hoc troubleshooting: As needed

---

**This is the complete future architecture for automated property and feature syncing!**
