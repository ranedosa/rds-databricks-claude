# Census Sync A (CREATE) - Configuration Guide

**Sync Name:** `RDS to SF - CREATE Properties (Sync A)`

**Purpose:** Create 735 new properties in Salesforce product_property table

**Source:** `crm.sfdc_dbx.properties_to_create` (Databricks view)

**Destination:** Salesforce `product_property` object

**Mode:** CREATE (insert new records)

---

## Step-by-Step Configuration

### 1. Create New Sync in Census

1. Log into Census (app.getcensus.com)
2. Click **"Syncs"** in left navigation
3. Click **"New Sync"** button
4. Select **Databricks** as source
5. Select **Salesforce** as destination

---

### 2. Configure Source (Databricks)

**Connection:** Select your existing Databricks connection

**Source Type:** Select **"Table"** or **"Model"**

**Source Object:**
```
crm.sfdc_dbx.properties_to_create
```

**Preview Data:** Click "Preview" to verify you see 735 rows

**Row Count Validation:**
- Should show: ~735 rows
- If different, stop and investigate

---

### 3. Configure Destination (Salesforce)

**Object:** `product_property__c` (or `product_property`)

**Operation:** **CREATE** (insert new records)

**Unique Identifier:** `sf_property_id__c` (or `sf_property_id_c`)

---

### 4. Field Mappings (22 Fields)

**Map these fields from source → destination:**

#### Core Identifiers (4 fields)

| Source Column | → | Salesforce Field | Notes |
|---------------|---|------------------|-------|
| `sfdc_id` | → | `sf_property_id__c` | Production SF Property ID |
| `rds_property_id` | → | `snappt_property_id__c` | RDS UUID |
| `short_id` | → | `short_id__c` | Short property ID |
| `company_id` | → | `company_id__c` | Company UUID |

#### Property Attributes (6 fields)

| Source Column | → | Salesforce Field | Notes |
|---------------|---|------------------|-------|
| `property_name` | → | `name` | Property name |
| `address` | → | `property_address_street__s` | Street address |
| `city` | → | `property_address_city__s` | City |
| `state` | → | `property_address_state_code__s` | State code |
| `postal_code` | → | `property_address_postal_code__s` | ZIP code |
| `company_name` | → | `company_name__c` | Company name |

#### Feature Flags - Boolean (5 fields)

| Source Column | → | Salesforce Field | Notes |
|---------------|---|------------------|-------|
| `idv_enabled` | → | `id_verification_enabled__c` | ID Verification |
| `bank_linking_enabled` | → | `bank_linking_enabled__c` | Bank Linking |
| `payroll_enabled` | → | `connected_payroll_enabled__c` | Payroll |
| `income_insights_enabled` | → | `income_verification_enabled__c` | Income Insights |
| `document_fraud_enabled` | → | `fraud_detection_enabled__c` | Document Fraud |

#### Feature Timestamps (5 fields)

| Source Column | → | Salesforce Field | Notes |
|---------------|---|------------------|-------|
| `idv_enabled_at` | → | `id_verification_start_date__c` | When IDV enabled |
| `bank_linking_enabled_at` | → | `bank_linking_start_date__c` | When Bank enabled |
| `payroll_enabled_at` | → | `connected_payroll_start_date__c` | When Payroll enabled |
| `income_insights_enabled_at` | → | `income_verification_start_date__c` | When IV enabled |
| `document_fraud_enabled_at` | → | `fraud_detection_start_date__c` | When Fraud enabled |

#### Metadata (2 fields)

| Source Column | → | Salesforce Field | Notes |
|---------------|---|------------------|-------|
| `created_at` | → | `rds_created_date__c` | RDS creation date |
| `rds_last_updated_at` | → | `rds_last_updated_date__c` | RDS last update |

---

### 5. Advanced Settings

**Sync Mode:** CREATE (one-way insert)

**Sync Key:** `sf_property_id__c` (Salesforce field that matches `sfdc_id`)

**Sync Behavior:**
- ✅ Create new records
- ❌ Do NOT update existing records
- ❌ Do NOT delete records

**Error Handling:**
- Stop sync if error rate > 10%
- Send alert to dane@snappt.com

**Schedule:** Manual (do not schedule yet - pilot test first)

---

### 6. Add Pilot Filter (IMPORTANT!)

Before running, add a filter to ONLY sync the 50 pilot properties:

**Filter Type:** WHERE clause or Include filter

**Filter Expression:**
```sql
rds_property_id IN (
  '5f8b4551-b325-47eb-bfa0-315384b9e959',  -- Perch
  'e666590d-9171-4fde-861a-4b8962b6a27a',  -- The Foundry at Stovehouse
  -- ... paste all 50 IDs from pilot_create_properties.csv
)
```

**To get the full list:**
Open `/Users/danerosa/rds_databricks_claude/20260105/pilot_create_properties.csv`
Copy the `rds_property_id` column (50 values)
Format as: `'id1', 'id2', 'id3', ...`

**Verify:** Census should show ~50 rows after filter applied

---

### 7. Test & Validate Configuration

**Before running:**

1. Click **"Test Connection"** → Should succeed
2. Click **"Preview Sync"** → Should show ~50 records
3. Review field mappings → All 22 fields mapped
4. Check filter → Only 50 pilot properties included
5. Verify sync mode → CREATE (not UPDATE)

**Validation Checklist:**
- [ ] Source: `properties_to_create` view ✓
- [ ] Destination: Salesforce product_property ✓
- [ ] Operation: CREATE ✓
- [ ] 22 fields mapped ✓
- [ ] Pilot filter applied (50 rows) ✓
- [ ] Test connection passed ✓

---

### 8. Save Sync (Do Not Run Yet!)

1. Click **"Save Sync"**
2. Name it: `RDS to SF - CREATE Properties (Pilot)`
3. **DO NOT click "Run Sync" yet**
4. We'll configure Sync B first, then run both pilots together

---

## Common Issues & Solutions

### Issue: Can't find `properties_to_create` view

**Solution:**
- Verify Databricks connection has access to `crm.sfdc_dbx` schema
- Try fully qualified name: `crm.sfdc_dbx.properties_to_create`
- Refresh Census connection

### Issue: Salesforce field names don't match

**Solution:**
- Salesforce custom fields end in `__c` (double underscore c)
- Standard fields have no suffix (e.g., `name`)
- Check actual field names in Salesforce Object Manager

### Issue: Field type mismatch (Boolean vs Text)

**Solution:**
- Census should auto-detect types
- If not, ensure source column is BOOLEAN (0/1 or TRUE/FALSE)
- May need to cast: `CAST(idv_enabled AS BOOLEAN)`

### Issue: Duplicate records error

**Solution:**
- Verify `sf_property_id__c` is truly unique in source
- Check for duplicates: `SELECT sfdc_id, COUNT(*) FROM properties_to_create GROUP BY 1 HAVING COUNT(*) > 1`
- Should return 0 rows

---

## Next Steps

After saving Sync A configuration:
1. Configure Sync B (UPDATE) next
2. Then run both pilots together
3. Validate results in Salesforce
4. Make GO/NO-GO decision for full rollout

---

**Status:** Ready to configure in Census

**Estimated Time:** 30-45 minutes to configure

**Stop if:** Field mapping errors, connection issues, or row count doesn't match expected 50 (with filter) or 735 (without filter)
