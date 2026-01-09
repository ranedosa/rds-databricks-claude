# Pipeline ID Mapping Issue: RDS → product_property → SF Properties

**Date:** January 5, 2026
**Issue:** Census sync confusion between staging and production IDs
**Impact:** 1,081 properties not syncing from RDS to product_property

---

## EXECUTIVE SUMMARY

### The Pipeline Architecture

```
[RDS Properties]  →  [product_property (staging)]  →  [Salesforce Properties (production)]
     Source              Census writes here              SF Workflow writes here
```

### The Problem

**RDS.sfdc_id contains PRODUCTION IDs, but Census needs to write to STAGING**

- `RDS.sfdc_id` = Production Salesforce Property ID (populated after workflow runs)
- `product_property.id` = Staging record ID (different from production)
- `product_property.sf_property_id_c` = Production ID (populated AFTER SF workflow)

**Census MUST use:**
- Source: `RDS.id` (UUID)
- Target: `product_property.snappt_property_id_c`

**Census must NOT use:**
- `RDS.sfdc_id` → anywhere (it's a production ID, not a staging key)

---

## CURRENT STATE ANALYSIS

### Pipeline Status

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| **NOT in staging yet** | **1,081** | **11.9%** | Need to be created in product_property |
| In staging, no production ID | 196 | 2.2% | Awaiting SF workflow to write to production |
| Complete pipeline (all IDs aligned) | 7,798 | 86.1% | Successfully synced through entire pipeline |
| **Total RDS ACTIVE properties** | **9,061** | **100%** | |

### Field Population in product_property

| Field | Records | Percentage | Purpose |
|-------|---------|------------|---------|
| `id` (staging ID) | 18,022 | 100% | Unique staging record ID |
| `snappt_property_id_c` | 18,021 | 99.99% | Links to RDS.id |
| `sf_property_id_c` | 14,654 | 81.3% | Production ID (after workflow) |

**Gap:** 3,368 staging records don't have `sf_property_id_c` yet (waiting for SF workflow)

---

## THE THREE-TIER ID SYSTEM

### 1. RDS Properties (Source)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | UUID | Primary key | `b6d1d00d-e4da-4d5f-8d10-539dcc267367` |
| `sfdc_id` | String (18 char) | PRODUCTION Salesforce Property ID | `a01UL00000d5mbrYAA` |
| `short_id` | String | Human-readable ID | `eD8kPq7w3J` |

**Critical:** `RDS.sfdc_id` points to the PRODUCTION Salesforce Properties object, NOT staging!

---

### 2. product_property (Staging in Salesforce)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | Salesforce ID | Staging record ID | `a13UL00000abc123YAC` |
| `snappt_property_id_c` | UUID (string) | Links to `RDS.id` | `b6d1d00d-e4da-4d5f-8d10-539dcc267367` |
| `sf_property_id_c` | Salesforce ID (18 char) | Production ID (after workflow) | `a01UL00000d5mbrYAA` |

**Key Insights:**
- `product_property.id` ≠ `RDS.sfdc_id` (different ID spaces)
- `snappt_property_id_c` should match `RDS.id` (this is the sync key!)
- `sf_property_id_c` gets populated AFTER Salesforce workflow runs

---

### 3. Salesforce Properties (Production)

| Field | Type | Purpose |
|-------|------|---------|
| `Id` | Salesforce ID | Production property record ID |

This is the final destination where `RDS.sfdc_id` and `product_property.sf_property_id_c` point to.

---

## CENSUS SYNC KEY OPTIONS ANALYZED

### ✅ OPTION 1: RDS.id → snappt_property_id_c (CORRECT)

```sql
-- Census should use this mapping
Source: RDS.id (UUID)
Target: product_property.snappt_property_id_c (UUID as string)
```

**Results:**
- Would match: **7,980 records (88.1%)**
- Would create: **1,081 new records**
- ✓ This is the CORRECT approach for staging sync
- ✓ Allows upserts to work properly
- ✓ New properties get created, existing properties get updated

---

### ❌ OPTION 2: RDS.sfdc_id → product_property.id (WRONG)

```sql
-- This NEVER works
Source: RDS.sfdc_id (production Salesforce ID)
Target: product_property.id (staging Salesforce ID)
```

**Results:**
- Would match: **0 records (0.0%)**
- These are completely different ID spaces
- `RDS.sfdc_id` = `a01UL00000d5mbrYAA` (production)
- `product_property.id` = `a13UL00000abc123YAC` (staging)
- They will NEVER match

---

### ⚠️ OPTION 3: RDS.sfdc_id → sf_property_id_c (WRONG)

```sql
-- This seems to work but is WRONG for staging sync
Source: RDS.sfdc_id (production Salesforce ID)
Target: product_property.sf_property_id_c (production Salesforce ID)
```

**Results:**
- Would match: **7,778 records (85.8%)**
- ⚠️ This LOOKS like it works because the IDs match
- ❌ BUT `sf_property_id_c` is populated AFTER the SF workflow runs
- ❌ New properties won't have `sf_property_id_c` yet
- ❌ Can't be used as the sync key TO staging
- ❌ This creates a chicken-and-egg problem

**Why this fails:**
1. New property in RDS needs to be written to `product_property`
2. Census tries to match on `RDS.sfdc_id` → `sf_property_id_c`
3. BUT `sf_property_id_c` is NULL (not written to production yet!)
4. Census can't find a match, creates duplicate or fails

---

## THE CHICKEN-AND-EGG PROBLEM

### Current (Broken) Flow:

```
1. RDS Property created with sfdc_id = null
2. Census tries to sync to product_property
   → Uses RDS.sfdc_id as key
   → sfdc_id is null or points to old production record
   → Can't match, sync fails
3. Property never gets to staging
4. Salesforce workflow never runs
5. Production record never created
```

### Correct Flow:

```
1. RDS Property created (sfdc_id can be anything)
2. Census syncs to product_property
   ✓ Uses RDS.id → snappt_property_id_c as key
   ✓ Upserts work correctly (update existing, create new)
   ✓ Property appears in product_property (staging)
3. Salesforce workflow triggers
   ✓ Creates production Salesforce Property record
   ✓ Writes production ID to sf_property_id_c
4. (Optional) Production ID syncs back to RDS.sfdc_id
```

---

## ROOT CAUSE: WHY IS RDS.sfdc_id CONFUSING?

### The Naming Problem

`RDS.sfdc_id` implies "Salesforce ID" but doesn't specify **which** Salesforce object:

| What it could mean | What it actually means |
|-------------------|------------------------|
| Staging ID (`product_property.id`) | ❌ No |
| Link to staging (`snappt_property_id_c`) | ❌ No |
| Production ID (`sf_property_id_c`) | ✅ **YES** |

**Better name would be:** `production_salesforce_property_id` or `sf_properties_id`

### The Timing Problem

`RDS.sfdc_id` gets populated at different times:

1. **New properties:** NULL until production record created
2. **Migrated properties:** May have old/stale production ID
3. **Updated properties:** May not match current staging record

This makes it **unreliable as a sync key** for staging.

---

## EVIDENCE FROM DATA ANALYSIS

### Test 1: What does RDS.sfdc_id actually point to?

```sql
Sample: 1,135 RDS ACTIVE properties with valid SFDC ID

RDS.sfdc_id matches product_property.id:        0 (0.0%)
RDS.sfdc_id matches sf_property_id_c:           855 (75.3%)
```

**Conclusion:** `RDS.sfdc_id` = production ID, NOT staging ID

---

### Test 2: Which key successfully matches records?

```sql
Total RDS ACTIVE properties: 9,061

Match by RDS.id → snappt_property_id_c:         7,980 (88.1%)  ✓
Match by RDS.sfdc_id → product_property.id:     0 (0.0%)        ✗
Match by RDS.sfdc_id → sf_property_id_c:        7,778 (85.8%)  ⚠️
```

**Conclusion:** Only `RDS.id → snappt_property_id_c` is reliable for staging sync

---

### Test 3: What about properties not in staging?

```sql
Properties NOT in staging: 1,081
- These have RDS.sfdc_id (production ID)
- But NO staging record yet
- Can't use RDS.sfdc_id to match (nothing to match TO)
- MUST use RDS.id to create new staging record
```

**Conclusion:** New properties require `RDS.id` as the sync key

---

## EXAMPLES FROM PIPELINE

### Example 1: Property NOT in Staging Yet

```
RDS:
  id: b6d1d00d-e4da-4d5f-8d10-539dcc267367
  name: "Calypso Apartments"
  sfdc_id: a01UL00000d5mbrYAA (production ID from old system)

product_property (staging):
  ❌ NO RECORD EXISTS

Salesforce Properties (production):
  ✓ May have old record with ID a01UL00000d5mbrYAA

Issue:
  - Census tries to sync to staging
  - If using RDS.sfdc_id, can't find staging record (doesn't exist)
  - Sync fails or creates wrong record

Solution:
  - Census uses RDS.id → snappt_property_id_c
  - Creates NEW staging record with snappt_property_id_c = RDS.id
  - SF workflow creates new production record
  - Updates sf_property_id_c with new production ID
```

---

### Example 2: Property in Staging, Awaiting Production

```
RDS:
  id: abc-def-ghi-123
  name: "New Property"
  sfdc_id: NULL (no production record yet)

product_property (staging):
  id: a13XYZ (staging ID)
  snappt_property_id_c: abc-def-ghi-123 ✓ Matches RDS.id
  sf_property_id_c: NULL (awaiting SF workflow)

Salesforce Properties (production):
  ❌ NOT CREATED YET

Status:
  ✓ Census sync worked (used RDS.id → snappt_property_id_c)
  ⏳ Waiting for SF workflow to create production record
  ⏳ sf_property_id_c will be populated when workflow runs
```

---

### Example 3: Complete Pipeline Success

```
RDS:
  id: xyz-789-abc-456
  name: "Established Property"
  sfdc_id: a01PROD123 (production ID)

product_property (staging):
  id: a13STAGE456 (staging ID)
  snappt_property_id_c: xyz-789-abc-456 ✓ Matches RDS.id
  sf_property_id_c: a01PROD123 ✓ Matches RDS.sfdc_id

Salesforce Properties (production):
  Id: a01PROD123 ✓ Matches both RDS.sfdc_id and sf_property_id_c

Status:
  ✓ All IDs aligned
  ✓ Census sync works (RDS.id → snappt_property_id_c)
  ✓ SF workflow completed
  ✓ Production record exists
```

---

## THE SOLUTION

### Census Sync Configuration

**CORRECT Configuration:**

```
Sync Name: RDS Properties to product_property (Staging)
Source: RDS.properties
Destination: Salesforce product_property (via Fivetran or direct)

Sync Key (CRITICAL):
  Source field: id
  Target field: snappt_property_id_c

Sync Mode: Update or Create
  - If snappt_property_id_c exists → UPDATE
  - If snappt_property_id_c doesn't exist → CREATE

Field Mappings:
  RDS.id                  → snappt_property_id_c (SYNC KEY)
  RDS.name                → name
  RDS.short_id            → short_id_c
  RDS.address             → address_street_s
  RDS.city                → address_city_s
  RDS.state               → address_state_code_s
  RDS.company_id          → company_id_c
  RDS.status              → status_c

DO NOT MAP:
  ❌ RDS.sfdc_id → sf_property_id_c
  (This gets populated by SF workflow, not by Census)
```

---

### What Happens After Fix?

**Immediate Results:**
1. **1,081 properties** currently not in staging will be created
2. **7,980 existing** staging records will continue to update correctly
3. **196 properties** awaiting production will get picked up by SF workflow

**Long-term Benefits:**
1. New RDS properties automatically create staging records
2. Updates propagate correctly from RDS → staging
3. SF workflow handles staging → production independently
4. No more chicken-and-egg problem with production IDs

---

## FIELD ROLES CLARIFIED

### RDS.id (UUID)
- **Purpose:** Primary key for RDS property
- **Stability:** Never changes
- **Used for:** Syncing RDS → product_property
- **Maps to:** `snappt_property_id_c` in staging

### RDS.sfdc_id (Salesforce ID, 18 char)
- **Purpose:** Track which production Salesforce Property this RDS property represents
- **Stability:** Can change during migrations/merges
- **Used for:** Reference only, NOT for syncing to staging
- **Maps to:** Eventually matches `sf_property_id_c` (but NOT used as sync key)

### product_property.id (Salesforce ID)
- **Purpose:** Primary key for staging record
- **Stability:** Unique per staging record
- **Used for:** Internal Salesforce operations
- **Maps to:** Nothing in RDS (staging-only ID)

### product_property.snappt_property_id_c (UUID as string)
- **Purpose:** Link staging record back to RDS
- **Stability:** Never changes (set once when record created)
- **Used for:** **THE SYNC KEY from RDS to staging**
- **Maps to:** `RDS.id`

### product_property.sf_property_id_c (Salesforce ID, 18 char)
- **Purpose:** Track which production record this staging record created
- **Stability:** Set by SF workflow, doesn't change after
- **Used for:** Tracking production ID
- **Maps to:** Eventually should match `RDS.sfdc_id`

---

## MONITORING & VALIDATION

### Queries to Monitor Pipeline Health

#### 1. Properties NOT in staging (should be ~0 after fix)

```sql
SELECT COUNT(*) as missing_from_staging
FROM rds.pg_rds_public.properties r
WHERE r.status = 'ACTIVE'
  AND r.sfdc_id IS NOT NULL
  AND r.sfdc_id != 'XXXXXXXXXXXXXXX'
  AND NOT EXISTS (
      SELECT 1 FROM crm.salesforce.product_property s
      WHERE CAST(r.id AS STRING) = s.snappt_property_id_c
        AND s.is_deleted = false
  )
```

**Target:** < 100 (allowing for very recent additions)

---

#### 2. Staging records awaiting production

```sql
SELECT COUNT(*) as awaiting_production
FROM crm.salesforce.product_property
WHERE is_deleted = false
  AND snappt_property_id_c IS NOT NULL
  AND sf_property_id_c IS NULL
```

**Target:** < 200 (properties in the SF workflow queue)

---

#### 3. ID alignment check

```sql
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN r.sfdc_id = s.sf_property_id_c THEN 1 END) as aligned,
    COUNT(CASE WHEN r.sfdc_id != s.sf_property_id_c THEN 1 END) as misaligned
FROM rds.pg_rds_public.properties r
INNER JOIN crm.salesforce.product_property s
    ON CAST(r.id AS STRING) = s.snappt_property_id_c
WHERE r.status = 'ACTIVE'
  AND r.sfdc_id IS NOT NULL
  AND r.sfdc_id != 'XXXXXXXXXXXXXXX'
  AND s.is_deleted = false
  AND s.sf_property_id_c IS NOT NULL
```

**Target:** > 95% aligned (allowing for recent updates in flight)

---

## FREQUENTLY ASKED QUESTIONS

### Q1: Why not use RDS.sfdc_id → sf_property_id_c as the sync key?

**A:** Because `sf_property_id_c` is populated AFTER the Salesforce workflow runs. For new properties, it's NULL, so there's nothing to match to. You'd never be able to create new staging records.

---

### Q2: Won't this create duplicate records if RDS.id changes?

**A:** `RDS.id` is a UUID primary key - it never changes. This is safer than using `RDS.sfdc_id` which can change during migrations/merges.

---

### Q3: What if a property has the wrong snappt_property_id_c?

**A:** This would require manual correction:
1. Update `product_property.snappt_property_id_c` to match correct `RDS.id`
2. Census will then match correctly on next sync
3. This should be rare (data corruption scenario)

---

### Q4: How do new properties get their production ID?

**A:**
1. Census creates staging record with `snappt_property_id_c` = `RDS.id`
2. Salesforce workflow picks up new staging record
3. Workflow creates production Salesforce Property record
4. Workflow writes production ID to `sf_property_id_c`
5. (Optional) Production ID syncs back to `RDS.sfdc_id`

---

### Q5: What about the duplicate SFDC ID issue?

**A:** That's a separate issue. Even with duplicates:
- Use `RDS.id → snappt_property_id_c` as sync key (works every time)
- Multiple RDS properties can have same `RDS.sfdc_id` (production ID)
- Each gets its own staging record (unique `snappt_property_id_c`)
- SF workflow can then aggregate features before writing to production

---

### Q6: Why does product_property have both snappt_property_id_c and sf_property_id_c?

**A:**
- `snappt_property_id_c` = **Backward reference** to RDS source (for syncing FROM RDS)
- `sf_property_id_c` = **Forward reference** to production (for tracking WHERE it went)
- Two different purposes, two different fields

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Verify Current Census Configuration

- [ ] Check Census sync for "RDS Properties to product_property"
- [ ] Identify which field is currently used as sync key
- [ ] If using `RDS.sfdc_id`, document current sync failures
- [ ] Export list of properties not in staging (baseline: 1,081)

### Phase 2: Update Census Sync Configuration

- [ ] Change sync key to: `RDS.id → snappt_property_id_c`
- [ ] Verify sync mode is "Update or Create" (not "Update Only")
- [ ] Ensure `RDS.sfdc_id` is NOT mapped to anything
- [ ] Test sync on 5-10 properties first (dev/staging environment)
- [ ] Verify new staging records created with correct `snappt_property_id_c`

### Phase 3: Run Full Sync

- [ ] Trigger full Census sync
- [ ] Monitor for errors
- [ ] Verify 1,081 new staging records created
- [ ] Check that existing 7,980 records still update correctly
- [ ] Run validation query #1 (missing from staging should drop to ~0)

### Phase 4: Monitor SF Workflow

- [ ] Verify SF workflow processes new staging records
- [ ] Check that `sf_property_id_c` gets populated
- [ ] Run validation query #2 (awaiting production should clear)
- [ ] Verify new production records created in Salesforce Properties

### Phase 5: Validate End-to-End

- [ ] Run validation query #3 (ID alignment check - target >95%)
- [ ] Spot-check 10-20 properties through entire pipeline
- [ ] Verify features sync correctly after production record created
- [ ] Document any remaining issues (should be minimal)

### Phase 6: Ongoing Monitoring

- [ ] Set up daily automated validation queries
- [ ] Alert if "missing from staging" > 100
- [ ] Alert if "awaiting production" > 200 for > 24 hours
- [ ] Monitor sync success rate (target: 99%+)

---

## RELATED ISSUES

### Issue 1: Duplicate SFDC IDs
**File:** `19122025/README.md`, `SALESFORCE_SYNC_BLOCKED_PROPERTIES_REPORT.md`

**Relationship:**
- This ID mapping issue is SEPARATE from duplicate SFDC IDs
- Even with duplicates, `RDS.id → snappt_property_id_c` works correctly
- Duplicates affect production sync, not staging sync
- After fixing ID mapping, implement feature aggregation for duplicates

---

### Issue 2: Missing Feature Data
**File:** `salesforce_property_sync/SESSION_SUMMARY_product_feature_sync.md`

**Relationship:**
- Features sync separately from property sync
- Once property is in staging, features should follow
- Feature aggregation may be needed for duplicate SFDC IDs
- ID mapping fix is prerequisite for feature sync fix

---

## FILES GENERATED

All files saved to: `/Users/danerosa/rds_databricks_claude/`

1. **PIPELINE_ID_MAPPING_ISSUE.md** (this file) - Complete analysis and solution
2. **pipeline_id_examples.csv** - 50 examples showing ID relationships
3. **rds_salesforce_discovery.json** - Raw query results
4. **table_schemas.json** - Complete schemas

---

## SUMMARY

### The Core Issue

**RDS.sfdc_id is a PRODUCTION ID, but Census is trying to write to STAGING**

### The Solution

**Use RDS.id → snappt_property_id_c as the sync key**

### The Impact

**1,081 properties will sync immediately, 7,980 continue working correctly**

### The Timing

**Estimated 2-4 hours to implement and validate**

---

**Next Step:** Update Census sync configuration and test on small batch first.

---

**Report By:** Claude Code
**Analysis Date:** January 5, 2026
**Data Source:** Live Databricks queries
**Contact:** Dane Rosa

---

*This document explains the three-tier ID system (RDS → product_property → SF Properties) and why Census must use RDS.id as the sync key to product_property, not RDS.sfdc_id.*
