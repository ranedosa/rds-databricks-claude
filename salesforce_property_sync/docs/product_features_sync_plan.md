# Product Features Sync Plan
## Syncing Feature Enablement Data to Salesforce

**Date:** 2025-11-21
**Priority:** HIGH

---

## Problem Statement

The `crm.sfdc_dbx.product_property_w_features` table contains critical product enablement data that is **NOT currently syncing to Salesforce**.

**Missing Data:**
- Which Snappt products are enabled for each property (FD, IV, IDV, etc.)
- When products were enabled/disabled
- Product update timestamps

**Impact:**
- Salesforce has no visibility into product adoption
- Cannot report on which properties use which products
- Cannot build workflows based on product status
- Missing key revenue/product analytics

---

## Current State

### Source Data: `crm.sfdc_dbx.product_property_w_features`

**Records:** 22,784 properties with feature data

**Key Fields:**
- `property_id` (UUID) - Links to RDS properties.id
- `sfdc_id` - Salesforce property_c ID
- `product_property_id` - Salesforce product_property_c ID (if exists)
- **Feature Flags** (boolean):
  - `fraud_enabled`
  - `iv_enabled` (Income Verification)
  - `idv_enabled` (Identity Verification)
  - `idv_only_enabled`
  - `payroll_linking_enabled` (Connected Payroll)
  - `bank_linking_enabled`
  - `vor_enabled` (Verification of Rent)
- **Timestamps**:
  - `*_enabled_at` - When feature was first enabled
  - `*_updated_at` - When feature status last changed

### Destination: Salesforce `product_property_c`

**Current Fields:** Has standard property data (name, address, etc.)

**Missing:** All product feature enablement fields

---

## Solution Options

### Option 1: Add Feature Fields to Existing Sync ⭐ RECOMMENDED

**Approach:**
Update your Census sync to include feature fields from `product_property_w_features`

**Pros:**
- Single source of truth
- All data in one sync
- Simpler to maintain

**Cons:**
- Need to ensure fields exist in Salesforce first
- Requires Salesforce admin to add custom fields

**Steps:**
1. **Salesforce Admin:** Add custom fields to `Product_Property__c` object:
   - `Fraud_Enabled__c` (Checkbox)
   - `Fraud_Enabled_At__c` (Date/Time)
   - `IV_Enabled__c` (Checkbox)
   - `IV_Enabled_At__c` (Date/Time)
   - `IDV_Enabled__c` (Checkbox)
   - `IDV_Enabled_At__c` (Date/Time)
   - `IDV_Only_Enabled__c` (Checkbox)
   - `Payroll_Linking_Enabled__c` (Checkbox)
   - `Bank_Linking_Enabled__c` (Checkbox)
   - `VOR_Enabled__c` (Checkbox - Verification of Rent)
   - (Add *_Updated_At fields as needed)

2. **Update Census Source Query:**
   ```sql
   SELECT
       -- Existing fields
       CAST(rds.id AS STRING) as id,
       rds.name,
       rds.address,
       ... (all current fields)

       -- Add feature fields
       feat.fraud_enabled,
       feat.fraud_enabled_at,
       feat.fraud_updated_at,
       feat.iv_enabled,
       feat.iv_enabled_at,
       feat.iv_updated_at,
       feat.idv_enabled,
       feat.idv_enabled_at,
       feat.idv_updated_at,
       feat.idv_only_enabled,
       feat.idv_only_enabled_at,
       feat.idv_only_updated_at,
       feat.payroll_linking_enabled,
       feat.payroll_linking_enabled_at,
       feat.payroll_linking_updated_at,
       feat.bank_linking_enabled,
       feat.bank_linking_enabled_at,
       feat.bank_linking_updated_at,
       feat.vor_enabled,
       feat.vor_enabled_at,
       feat.vor_updated_at

   FROM rds.pg_rds_public.properties rds
   LEFT JOIN crm.sfdc_dbx.product_property_w_features feat
       ON CAST(rds.id AS STRING) = feat.property_id
   WHERE rds.status = 'ACTIVE'
       AND (rds.sfdc_id IS NULL OR rds.sfdc_id = '')
   ```

3. **Map Fields in Census:**
   - `fraud_enabled` → `Fraud_Enabled__c`
   - `fraud_enabled_at` → `Fraud_Enabled_At__c`
   - etc.

4. **Sync Data:**
   - Resync existing properties with feature data
   - Future syncs will include feature fields

---

### Option 2: Separate Feature Data Sync

**Approach:**
Create a second Census sync specifically for product features

**Pros:**
- Can deploy independently
- Doesn't affect existing property sync
- Can update feature data without touching property data

**Cons:**
- More complex (2 syncs to maintain)
- Requires coordination between syncs

**Steps:**
1. **Salesforce Admin:** Add custom fields (same as Option 1)

2. **Create New Census Model:**
   ```sql
   SELECT
       CAST(property_id AS STRING) as snappt_property_id,
       product_property_id,
       fraud_enabled,
       fraud_enabled_at,
       fraud_updated_at,
       iv_enabled,
       iv_enabled_at,
       iv_updated_at,
       idv_enabled,
       idv_enabled_at,
       idv_updated_at,
       idv_only_enabled,
       payroll_linking_enabled,
       bank_linking_enabled,
       vor_enabled
   FROM crm.sfdc_dbx.product_property_w_features
   WHERE product_property_id IS NOT NULL  -- Only sync if property exists in SF
   ```

3. **Create Census Sync:**
   - Source: New model above
   - Destination: Salesforce `Product_Property__c`
   - Sync Key: `snappt_property_id` → `Snappt_Property_ID__c`
   - Sync Behavior: Update only (don't create new records)

4. **Schedule:**
   - Run daily or after property syncs complete
   - Updates feature flags for existing properties

---

## Field Mapping Guide

### Salesforce Field Naming Convention

| Source Field (Databricks) | Salesforce Field (API Name) | Type | Description |
|---------------------------|----------------------------|------|-------------|
| `fraud_enabled` | `Fraud_Enabled__c` | Checkbox | Fraud Detection enabled |
| `fraud_enabled_at` | `Fraud_Enabled_At__c` | Date/Time | When FD was enabled |
| `fraud_updated_at` | `Fraud_Updated_At__c` | Date/Time | Last FD status change |
| `iv_enabled` | `IV_Enabled__c` | Checkbox | Income Verification enabled |
| `iv_enabled_at` | `IV_Enabled_At__c` | Date/Time | When IV was enabled |
| `iv_updated_at` | `IV_Updated_At__c` | Date/Time | Last IV status change |
| `idv_enabled` | `IDV_Enabled__c` | Checkbox | Identity Verification enabled |
| `idv_enabled_at` | `IDV_Enabled_At__c` | Date/Time | When IDV was enabled |
| `idv_updated_at` | `IDV_Updated_At__c` | Date/Time | Last IDV status change |
| `idv_only_enabled` | `IDV_Only_Enabled__c` | Checkbox | IDV-only mode enabled |
| `idv_only_enabled_at` | `IDV_Only_Enabled_At__c` | Date/Time | When IDV-only was enabled |
| `payroll_linking_enabled` | `Payroll_Linking_Enabled__c` | Checkbox | Connected Payroll enabled |
| `payroll_linking_enabled_at` | `Payroll_Linking_Enabled_At__c` | Date/Time | When Payroll was enabled |
| `bank_linking_enabled` | `Bank_Linking_Enabled__c` | Checkbox | Bank Linking enabled |
| `bank_linking_enabled_at` | `Bank_Linking_Enabled_At__c` | Date/Time | When Bank Linking was enabled |
| `vor_enabled` | `VOR_Enabled__c` | Checkbox | Verification of Rent enabled |
| `vor_enabled_at` | `VOR_Enabled_At__c` | Date/Time | When VOR was enabled |

---

## Implementation Plan

### Phase 1: Salesforce Field Setup (Requires SF Admin)

1. **Create custom fields on `Product_Property__c` object**
   - Use naming convention above
   - Set appropriate field types (Checkbox, Date/Time)
   - Add to page layouts as needed
   - Set field-level security

2. **Estimated time:** 30-60 minutes

### Phase 2: Update Census Sync

**If using Option 1 (Recommended):**
1. Update existing Census model SQL to join with `product_property_w_features`
2. Add field mappings in Census
3. Test with small batch (10-20 records)
4. Full resync to populate feature data for existing properties

**If using Option 2:**
1. Create new Census model for features
2. Create new sync (update-only mode)
3. Test with small batch
4. Run full sync

3. **Estimated time:** 1-2 hours

### Phase 3: Validation

1. **Check Salesforce:**
   - Verify feature fields are populated
   - Spot check a few properties manually

2. **Run validation query:**
   ```sql
   -- Databricks
   SELECT
       pp.name,
       pp.fraud_detection_enabled_c,
       feat.fraud_enabled,
       pp.income_verification_enabled_c,
       feat.iv_enabled
   FROM hive_metastore.salesforce.product_property_c pp
   INNER JOIN crm.sfdc_dbx.product_property_w_features feat
       ON pp.snappt_property_id_c = feat.property_id
   WHERE pp.fraud_detection_enabled_c != feat.fraud_enabled
      OR pp.income_verification_enabled_c != feat.iv_enabled
   LIMIT 10
   ```

3. **Estimated time:** 30 minutes

---

## Benefits After Implementation

Once feature data is syncing:

✅ **Salesforce Reporting:**
- Report on product adoption by property
- Track which products are most popular
- Identify properties with multiple products

✅ **Workflows:**
- Trigger actions when products are enabled/disabled
- Send notifications to CSMs
- Update property records automatically

✅ **Analytics:**
- Product penetration rates
- Time-to-enable metrics
- Product mix analysis
- Revenue opportunity identification

✅ **Operational:**
- Single source of truth for product status
- No manual data entry needed
- Real-time product visibility

---

## Priority & Timeline

**Priority:** HIGH

**Estimated Total Time:** 2-3 hours (including SF admin work)

**Recommended Timeline:**
- **Week 1:** Salesforce field setup
- **Week 1:** Update Census sync
- **Week 1:** Test & validate
- **Week 2:** Full resync with feature data

---

## Questions for Stakeholders

1. **Are there other fields in `product_property_w_features` we should sync?**

2. **Who is the Salesforce admin to create these custom fields?**

3. **Do these fields already exist in Salesforce with different names?**
   - Check existing fields on `Product_Property__c` object

4. **Should we sync all properties or only ACTIVE ones?**

5. **How often should feature data sync?**
   - Daily?
   - Real-time (incremental)?
   - On-demand?

---

## Next Steps

1. **Review this plan** with Salesforce admin and Rev Ops team
2. **Get approval** to create custom fields
3. **Schedule implementation** (2-3 hour block)
4. **Execute Phase 1-3** per plan above
5. **Document** field usage for sales/CS teams

---

## Related Documentation

- Property Gap Analysis: `/docs/property_gap_analysis_summary.md`
- Census Sync Configuration: `/docs/census_sync_configuration.md`
- Sync Error Solution: `/docs/sync_error_solution.md`
