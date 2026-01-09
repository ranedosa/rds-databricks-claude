# Duplicate sfdc_id Resolution Strategy

**Problem:** Multiple RDS properties sharing the same `sfdc_id` breaks the Salesforce sync workflow.

**Impact:**
- Feature sync fails (join failures)
- New property sync skips properties with `sfdc_id` populated
- Customer confusion (wrong property in Salesforce)
- Data integrity issues

---

## Decision Framework

For each duplicate sfdc_id group, answer these questions:

### 1. Which property is the "source of truth"?

**Indicators of the correct property:**
- ✅ Status = `ACTIVE`
- ✅ Has features enabled
- ✅ Most recent activity (updated_at)
- ✅ Has recent submissions/applicants
- ✅ Users are actively using it
- ✅ Customer expects to see this one in Salesforce

**Indicators of outdated/wrong property:**
- ❌ Status = `DISABLED` or `DELETED`
- ❌ No features enabled
- ❌ No recent activity
- ❌ Old inserted_at date
- ❌ Duplicate/test property

---

### 2. What is the relationship between duplicates?

**Common patterns:**

#### Pattern A: Migration/Replacement
```
Old Property (DISABLED) → New Property (ACTIVE)
```
- Property was migrated/recreated
- Old one should be cleaned up
- New one should be in Salesforce

**Resolution:** Clear sfdc_id from old, let new one sync

---

#### Pattern B: Test/Duplicate Creation
```
Real Property (ACTIVE) + Test Property (ACTIVE)
```
- Accidental duplicate created
- Test property should be removed
- Real property should keep sfdc_id

**Resolution:** Mark test as DELETED, clear its sfdc_id

---

#### Pattern C: Multiple Active Properties (Legitimate)
```
Property A (ACTIVE) + Property B (ACTIVE) - Different entities
```
- Actually different properties that need separate Salesforce records
- Both should be active
- sfdc_id collision is the error

**Resolution:** One needs new Salesforce record (clear sfdc_id)

---

## Resolution Strategies

### Strategy 1: Clear sfdc_id from Old/Inactive Properties (Most Common)

**When to use:**
- Old property is DISABLED/DELETED
- New property is ACTIVE with features
- New property not yet in Salesforce

**Steps:**
```sql
-- Step 1: Clear sfdc_id from old property
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id = '<old-property-id>'
  AND status IN ('DISABLED', 'DELETED');

-- Step 2: Wait for Fivetran sync

-- Step 3: Run sync job 1061000314609635
-- New property will be detected as "new" and synced with features
```

**Pros:**
- Clean, uses existing workflow
- New property gets proper feature sync
- Creates proper ID mappings

**Cons:**
- Creates new Salesforce record (old one remains)
- May need to clean up old Salesforce record

---

### Strategy 2: Update Salesforce to Point to New Property

**When to use:**
- Need to preserve existing Salesforce record
- Salesforce record has important history/relationships
- Don't want a new record

**Steps:**
```sql
-- Step 1: Clear sfdc_id from old property in RDS
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id = '<old-property-id>';

-- Step 2: In Salesforce, update the product_property record:
-- - Snappt_Property_ID__c = <new-property-id>
-- - SF_Property_ID__c = <sfdc_id>

-- Step 3: Wait for Fivetran to sync Salesforce → Databricks

-- Step 4: Rebuild feature tables
-- Run: /Workspace/Shared/census_pfe

-- Step 5: Run feature sync job
```

**Pros:**
- Preserves Salesforce record
- Maintains relationships/history

**Cons:**
- Requires manual Salesforce update
- Multi-step process
- More complex

---

### Strategy 3: Mark Old Property as DELETED

**When to use:**
- Old property is obsolete
- No active usage
- Safe to remove from system

**Steps:**
```sql
-- Mark as deleted and clear sfdc_id
UPDATE rds.pg_rds_public.properties
SET status = 'DELETED',
    sfdc_id = NULL
WHERE id = '<old-property-id>';

-- Then use Strategy 1 or 2 for the remaining property
```

**Pros:**
- Cleanest data model
- Removes confusion
- Prevents future issues

**Cons:**
- Permanent change
- May affect historical reporting

---

## Triage Priority

### Priority 1: ACTIVE Properties with Features (URGENT)

**Criteria:**
- Status = ACTIVE
- Has features enabled
- NOT in Salesforce

**Example:** Park Kennedy
- ACTIVE property with 4 features enabled
- NOT syncing to Salesforce
- Customer impact

**Action:** Resolve immediately using Strategy 1

---

### Priority 2: ACTIVE Properties without Features (HIGH)

**Criteria:**
- Status = ACTIVE
- No features enabled yet
- May get features soon

**Risk:** Will break when features are enabled

**Action:** Resolve within 1 week

---

### Priority 3: DISABLED/DELETED Properties (MEDIUM)

**Criteria:**
- Status = DISABLED or DELETED
- No active usage
- Data hygiene issue

**Risk:** Lower immediate impact, but causes confusion

**Action:** Clean up in batch during maintenance

---

## Batch Cleanup Script

For handling multiple duplicates at once:

```sql
-- Step 1: Identify all old/inactive properties with duplicate sfdc_ids
WITH duplicate_sfdc_ids AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

old_properties_to_clear AS (
    SELECT p.id
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_sfdc_ids d ON p.sfdc_id = d.sfdc_id
    WHERE p.status IN ('DISABLED', 'DELETED')
)

-- Preview what will be cleared
SELECT
    p.id,
    p.name,
    p.status,
    p.sfdc_id,
    p.inserted_at
FROM rds.pg_rds_public.properties p
INNER JOIN old_properties_to_clear o ON p.id = o.id
ORDER BY p.inserted_at DESC;

-- Step 2: Execute cleanup (uncomment to run)
/*
UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL
WHERE id IN (SELECT id FROM old_properties_to_clear);
*/
```

---

## Prevention Strategy

### 1. Add Database Constraint (Recommended)

**If possible, add unique constraint:**
```sql
-- Prevent duplicate sfdc_ids
ALTER TABLE properties
ADD CONSTRAINT unique_sfdc_id UNIQUE (sfdc_id)
WHERE sfdc_id IS NOT NULL;
```

**Note:** May need to clean up existing duplicates first

---

### 2. Application-Level Validation

**In the application that sets sfdc_id:**
```python
def set_sfdc_id(property_id, sfdc_id):
    # Check for existing property with this sfdc_id
    existing = db.query(Property).filter(
        Property.sfdc_id == sfdc_id,
        Property.id != property_id
    ).first()

    if existing:
        raise ValueError(f"sfdc_id {sfdc_id} already in use by property {existing.id}")

    # Set the sfdc_id
    property.sfdc_id = sfdc_id
    db.commit()
```

---

### 3. Monitoring & Alerting

**Create alert for new duplicates:**
```sql
-- Run daily
SELECT
    sfdc_id,
    COUNT(*) as duplicate_count,
    COLLECT_LIST(id) as property_ids,
    COLLECT_LIST(status) as statuses
FROM rds.pg_rds_public.properties
WHERE sfdc_id IS NOT NULL
  AND inserted_at >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY sfdc_id
HAVING COUNT(*) > 1;
```

Send alert if any results found.

---

### 4. Sync Workflow Enhancement

**Improve the sync workflow to handle duplicates gracefully:**

**Option A: Use snappt_property_id as primary key**
```sql
-- Instead of:
left join salesforce.product_property_c pp
    on pp.sf_property_id_c = p.sfdc_id

-- Use:
left join salesforce.product_property_c pp
    on pp.snappt_property_id_c = CAST(p.id AS STRING)
```

**Option B: Add duplicate detection to sync job**
```sql
-- In new_properties_with_features, add check:
WHERE sf.snappt_property_id_c IS NULL
  AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
  AND rds.status = 'ACTIVE'
  -- New: Ensure sfdc_id not used by another property
  AND NOT EXISTS (
      SELECT 1
      FROM rds.pg_rds_public.properties p2
      WHERE p2.sfdc_id = rds.sfdc_id
        AND p2.id != rds.id
  )
```

---

## Recommended Action Plan

### Week 1: Immediate Issues
1. **Run the duplicate detection query** (Find_Duplicate_SFDC_IDs.ipynb)
2. **Identify Priority 1 cases** (ACTIVE with features, not in SF)
3. **Resolve Park Kennedy** using Strategy 1
4. **Resolve other Priority 1** cases (if any)

### Week 2: High Priority Cleanup
1. **Review Priority 2 cases** (ACTIVE without features)
2. **Create resolution plan** for each case
3. **Execute fixes** using appropriate strategy
4. **Verify in Salesforce** that features sync correctly

### Week 3: Batch Cleanup
1. **Run batch cleanup script** for Priority 3 (DISABLED/DELETED)
2. **Clear sfdc_id** from all inactive properties
3. **Monitor for sync issues**
4. **Document any edge cases**

### Week 4: Prevention
1. **Add database constraint** (if feasible)
2. **Implement monitoring** (daily duplicate check)
3. **Update sync workflow** to detect duplicates
4. **Document process** for team

---

## Testing Your Resolution

After fixing duplicates, verify:

```sql
-- 1. Check duplicate is resolved
SELECT COUNT(*) as should_be_1
FROM rds.pg_rds_public.properties
WHERE sfdc_id = '<the-sfdc-id>';

-- 2. Check property is in feature aggregation table
SELECT *
FROM crm.sfdc_dbx.product_property_w_features
WHERE property_id = '<property-id>';

-- 3. Check property appears in sync table (if features differ)
SELECT *
FROM crm.sfdc_dbx.product_property_feature_sync
WHERE snappt_property_id_c = '<property-id>';

-- 4. Check property synced to Salesforce
SELECT *
FROM crm.salesforce.product_property
WHERE snappt_property_id_c = '<property-id>';

-- 5. Verify features match
SELECT
    rds_features.iv_enabled as rds_iv,
    sf.income_verification_enabled_c as sf_iv,
    rds_features.bank_linking_enabled as rds_bank,
    sf.bank_linking_enabled_c as sf_bank
FROM crm.sfdc_dbx.product_property_w_features rds_features
JOIN crm.salesforce.product_property sf
    ON CAST(rds_features.property_id AS STRING) = sf.snappt_property_id_c
WHERE rds_features.property_id = '<property-id>';
```

---

## Summary

**Recommended Approach:**
1. **Strategy 1 (Clear sfdc_id)** for most cases - cleanest, uses existing workflow
2. **Strategy 3 (Mark DELETED)** for obsolete properties - best data hygiene
3. **Strategy 2 (Update Salesforce)** only when absolutely need to preserve SF record

**Key Principle:**
> Only ACTIVE properties that are the current "source of truth" should have sfdc_id populated.

**Prevention:**
> Add validation to prevent future duplicates - both at database and application level.

---

## Questions to Consider

Before implementing fixes, discuss with team:

1. **Historical data**: Do we need to preserve old Salesforce records?
2. **Reporting impact**: Will clearing sfdc_id affect historical reports?
3. **Customer communication**: Do customers need to know about record changes?
4. **Rollback plan**: What if something goes wrong?
5. **Testing environment**: Can we test on staging first?
6. **Maintenance window**: Do we need downtime for batch cleanup?

---

**Next Step:** Run the duplicate detection notebook and review results with team to create specific resolution plan for each duplicate group.
