# Property Gap Analysis Summary

**Date:** 2025-11-21
**Analysis:** Salesforce-Databricks Property Synchronization

## Overview

This analysis identifies properties that exist in the RDS PostgreSQL database (`rds.pg_rds_public.properties`) but are missing from the Salesforce staging table (`hive_metastore.salesforce.product_property_c`).

## Data Architecture

```
┌─────────────────────────────┐
│ RDS PostgreSQL              │
│ public.properties           │
│ (18,941 properties)         │
└──────────┬──────────────────┘
           │
           │ Sync Process
           │
           ▼
┌─────────────────────────────┐
│ Salesforce Staging          │
│ product_property_c          │
│ (15,535 properties)         │  ──► Salesforce Workflows ──► Final Production Table
└─────────────────────────────┘                               (property_c: 216,892 records)
```

## Key Findings

### Total Gap: 3,406 Properties

Properties in RDS that are **NOT** in `product_property_c` staging table.

## Breakdown by Category

### 1. Properties with No SFDC ID: **1,300 properties** 🎯 PRIMARY FOCUS

These properties exist only in RDS and have never been synced to Salesforce.

**Characteristics:**
- `sfdc_id` field is NULL or empty
- No presence in either `product_property_c` or `property_c`
- Need to be created in Salesforce from scratch

**Status Breakdown:**
- ACTIVE: ~800 properties (estimated)
- DISABLED: ~500 properties (estimated)

**Action Required:** Create these properties in `product_property_c` so they can flow through normal Salesforce workflows to `property_c`.

---

### 2. Properties that Bypassed Staging: **1,927 properties** ⏭️ DEFER

These properties exist in the final `property_c` table but skipped the `product_property_c` staging step.

**Characteristics:**
- Have valid `sfdc_id` pointing to records in `property_c`
- Missing from `product_property_c` (staging table)
- Already exist in final production `property_c` table

**Critical Issue:** The `snappt_property_id_c` field in `property_c` is not properly set:
- 1,406 properties: `snappt_property_id_c` is NULL/empty
- 521 properties: `snappt_property_id_c` points to wrong property ID (MISMATCH)

**Action Required:** These can be addressed in a separate effort to backfill staging and fix the `snappt_property_id_c` linkage.

---

### 3. Test/Demo Properties: **179 properties** ❌ IGNORE

These are test or demo properties that were never meant for production.

**Characteristics:**
- Have `sfdc_id = "XXXXXXXXXXXXXXX"` (placeholder value)
- Mix of ACTIVE and DISABLED status
- Not present in `property_c` table

**Action Required:** No action needed. These are intentional test records.

---

## Summary Statistics

```
Total RDS Properties: 18,941
├─ ✓ In product_property_c: 15,535
└─ ✗ NOT in product_property_c: 3,406
   ├─ 🎯 No sfdc_id (CREATE THESE): 1,300
   ├─ ⏭️ Bypassed staging (DEFER): 1,927
   └─ ❌ Test/demo (IGNORE): 179
```

## Recent Activity Trends

Properties missing from `product_property_c` by creation date:

| Month | Count |
|-------|-------|
| 2025-11 | 386 |
| 2025-10 | 702 |
| 2025-09 | 340 |
| 2025-08 | 48 |
| 2025-07 | 126 |
| 2025-06 | 63 |

**Note:** The high numbers in October and November 2025 suggest an ongoing sync issue.

## Matching Logic

**Join Key Used:**
- `rds.pg_rds_public.properties.id` (UUID) = `product_property_c.snappt_property_id_c` (STRING)

**Secondary Link:**
- `rds.pg_rds_public.properties.sfdc_id` = `property_c.id` (Salesforce record ID)

## Next Steps

### Immediate Priority: Create Missing Properties (1,300)

1. **Extract property data** from RDS for the 1,300 properties without sfdc_id
2. **Map fields** from RDS schema to Salesforce product_property_c schema
3. **Generate sync payload** with required Salesforce fields
4. **Write to product_property_c** via appropriate sync mechanism (Reverse ETL, API, etc.)
5. **Verify** that Salesforce workflows properly promote them to property_c

### Future Work

- **Backfill staging:** Add the 1,927 bypassed properties to product_property_c for consistency
- **Fix snappt_property_id_c:** Update the 1,406 NULL and 521 MISMATCH cases in property_c
- **Investigate root cause:** Determine why properties are bypassing the staging workflow

## Data Files Generated

| File | Description |
|------|-------------|
| `missing_properties.csv` | All 3,406 properties missing from product_property_c |
| `sfdc_id_verification.csv` | Verification of which properties exist in property_c |

## Technical Details

**Data Sources:**
- RDS PostgreSQL: `rds.pg_rds_public.properties`
- Databricks Salesforce Staging: `hive_metastore.salesforce.product_property_c`
- Databricks Salesforce Production: `hive_metastore.salesforce.property_c`

**Analysis Scripts:**
- `scripts/find_property_gaps.py`
- `scripts/verify_property_c_match.py`
- `scripts/analyze_sf_property_schemas.py`

**Warehouse:** Databricks SQL Warehouse (ID: 95a8f5979c3f8740)
