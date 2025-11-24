# Phase 2: Census Configuration for New Properties Sync

**Goal:** Configure Census to automatically sync new properties with feature data to Salesforce

**Time Required:** 1 hour

**Prerequisites:**
- ✅ Phase 1 complete (view created in Databricks)
- ✅ View `crm.sfdc_dbx.new_properties_with_features` exists
- ✅ Census account access with permissions to create syncs

---

## Overview

We're creating a Census sync that:
- **Reads from:** Databricks view `crm.sfdc_dbx.new_properties_with_features`
- **Writes to:** Salesforce `Product_Property__c`
- **Behavior:** INSERT (creates new records only)
- **Frequency:** Daily at 2am (or your preferred schedule)
- **Fields:** All 45 fields (property + features)

---

## Step-by-Step Configuration

### Step 1: Create Census Model (15 minutes)

**1.1: Navigate to Models**
1. Go to Census: https://app.getcensus.com/workspaces/33026
2. Click **"Models"** in left sidebar
3. Click **"New Model"** button

**1.2: Configure Model Source**
- **Name:** `New Properties with Features`
- **Connection:** Select your Databricks connection
- **Source Type:** Choose **"Table"** or **"View"**
- **Schema:** `crm.sfdc_dbx`
- **Table/View:** `new_properties_with_features`

**1.3: Preview Data**
- Click **"Preview"** to see sample data
- Verify you see:
  - Property fields (name, address, etc.)
  - Feature fields (fraud_detection_enabled_c, etc.)
  - All 45 fields present

**1.4: Save Model**
- Review settings
- Click **"Save"**
- Model is now ready to use

**Expected result:**
✅ Model created and showing in Models list
✅ Preview shows correct fields and data

---

### Step 2: Create Census Sync (20 minutes)

**2.1: Navigate to Syncs**
1. Click **"Syncs"** in left sidebar
2. Click **"New Sync"** button

**2.2: Select Source**
- **Source:** Choose the model you just created: `New Properties with Features`
- Click **"Next"**

**2.3: Select Destination**
- **Connection:** Salesforce
- **Object:** `Product_Property__c`
- Click **"Next"**

**2.4: Configure Sync Behavior**

This is crucial - we're INSERTING new records:

- **Sync Key:** `Reverse_ETL_ID__c` (External ID field in Salesforce)
  - Alternative: `snappt_property_id_c` if that's also marked as External ID
- **Sync Behavior:** **"Insert"** or **"Upsert"**
  - Choose **"Upsert"** (safer - will update if exists, insert if new)
- **Match On:**
  - Source field: `reverse_etl_id_c`
  - Destination field: `Reverse_ETL_ID__c`

**2.5: Configure Field Mappings**

Map all 45 fields from source to destination:

**Property Fields (21 fields):**

| Source Field (Databricks) | → | Destination Field (Salesforce) |
|---------------------------|---|-------------------------------|
| `snappt_property_id_c` | → | `snappt_property_id_c` |
| `reverse_etl_id_c` | → | `reverse_etl_id_c` |
| `name` | → | `name` |
| `entity_name_c` | → | `entity_name_c` |
| `address_street_s` | → | `address_street_s` |
| `address_city_s` | → | `address_city_s` |
| `address_state_code_s` | → | `address_state_code_s` |
| `address_postal_code_s` | → | `address_postal_code_s` |
| `phone_c` | → | `phone_c` |
| `email_c` | → | `email_c` |
| `website_c` | → | `website_c` |
| `logo_c` | → | `logo_c` |
| `unit_c` | → | `unit_c` |
| `status_c` | → | `status_c` |
| `company_id_c` | → | `company_id_c` |
| `company_short_id_c` | → | `company_short_id_c` |
| `short_id_c` | → | `short_id_c` |
| `bank_statement_c` | → | `bank_statement_c` |
| `paystub_c` | → | `paystub_c` |
| `unit_is_required_c` | → | `unit_is_required_c` |
| `phone_is_required_c` | → | `phone_is_required_c` |
| `identity_verification_enabled_c` | → | `identity_verification_enabled_c` |
| `not_orphan_record_c` | → | `not_orphan_record_c` |
| `trigger_rollups_c` | → | `trigger_rollups_c` |

**Feature Fields (23 fields):**

| Source Field | → | Destination Field |
|-------------|---|-------------------|
| `fraud_detection_enabled_c` | → | `fraud_detection_enabled_c` |
| `fraud_detection_start_date_c` | → | `fraud_detection_start_date_c` |
| `fraud_detection_updated_date_c` | → | `fraud_detection_updated_date_c` |
| `income_verification_enabled_c` | → | `income_verification_enabled_c` |
| `income_verification_start_date_c` | → | `income_verification_start_date_c` |
| `income_verification_updated_date_c` | → | `income_verification_updated_date_c` |
| `id_verification_enabled_c` | → | `id_verification_enabled_c` |
| `id_verification_start_date_c` | → | `id_verification_start_date_c` |
| `id_verification_updated_date_c` | → | `id_verification_updated_date_c` |
| `idv_only_enabled_c` | → | `idv_only_enabled_c` |
| `idv_only_start_date_c` | → | `idv_only_start_date_c` |
| `idv_only_updated_date_c` | → | `idv_only_updated_date_c` |
| `connected_payroll_enabled_c` | → | `connected_payroll_enabled_c` |
| `connected_payroll_start_date_c` | → | `connected_payroll_start_date_c` |
| `connected_payroll_updated_date_c` | → | `connected_payroll_updated_date_c` |
| `bank_linking_enabled_c` | → | `bank_linking_enabled_c` |
| `bank_linking_start_date_c` | → | `bank_linking_start_date_c` |
| `bank_linking_updated_date_c` | → | `bank_linking_updated_date_c` |
| `verification_of_rent_enabled_c` | → | `verification_of_rent_enabled_c` |
| `vor_start_date_c` | → | `vor_start_date_c` |
| `vor_updated_date_c` | → | `vor_updated_date_c` |

**Pro tip:** If field names match exactly, Census may auto-map some fields!

**2.6: Review and Name**
- **Sync Name:** `New Properties → Salesforce (INSERT with Features)`
- Review all settings
- Click **"Next"**

**2.7: Skip Schedule (for now)**
- We'll test manually first
- Click **"Create Sync"**

**Expected result:**
✅ Sync created successfully
✅ Appears in Syncs list
✅ Ready for testing

---

### Step 3: Test the Sync (15 minutes)

**3.1: Run Test Sync**
1. Find your sync in the Syncs list
2. Click on the sync name to open details
3. Click **"Run Sync"** button
4. In the dialog, choose:
   - **Test Mode:** Limit to first 10 records (optional but recommended)
   - **Confirm:** Click "Run Sync"

**3.2: Monitor the Run**
- Watch the sync progress
- Should complete in 1-5 minutes for 10 records
- Check for:
  - ✅ Records processed
  - ✅ Records created
  - ❌ Any errors

**3.3: Check Results in Census**
- Click into the sync run details
- Review:
  - **Records Created:** Should be 10 (if you limited)
  - **Records Failed:** Should be 0
  - **Error Details:** Check if any errors

**3.4: Validate in Salesforce**

Go to Salesforce and verify:

1. **Check records were created:**
   - Go to Product_Property__c object
   - Sort by Created Date (newest first)
   - Should see 10 new records

2. **Verify property data:**
   - Open one of the new records
   - Check fields:
     - ✅ Name is populated
     - ✅ Address is populated
     - ✅ IDs are correct

3. **Verify feature data:**
   - Scroll to feature fields
   - Check:
     - ✅ `fraud_detection_enabled_c` is TRUE or FALSE (not null)
     - ✅ `income_verification_enabled_c` is populated
     - ✅ Date fields have values (if feature is enabled)

4. **Check Salesforce Flow triggered:**
   - Wait 5-10 minutes
   - Check if records flowed to `property_c` table
   - If not, Flow may be having issues (see troubleshooting)

**Expected result:**
✅ 10 records created in Salesforce
✅ Property data correct
✅ Feature data populated
✅ No errors in Census

---

### Step 4: Run Full Sync (10 minutes)

**4.1: Remove Test Limit**
1. Go back to your sync
2. Click **"Run Sync"** again
3. This time: **Do NOT limit records**
4. Click "Run Sync"

**4.2: Monitor Full Run**
- Will take longer (5-30 minutes depending on record count)
- Watch for errors
- Check progress periodically

**4.3: Review Results**
- **Records Created:** Should equal count from Databricks view
- **Records Failed:** Should be 0 or very low
- If high failure rate, see troubleshooting

**4.4: Validate Sample in Salesforce**
- Check 5-10 random properties
- Verify data looks correct
- Check feature flags match expectations

**Expected result:**
✅ All new properties synced to Salesforce
✅ Failure rate < 1%
✅ Feature data correct

---

### Step 5: Schedule the Sync (5 minutes)

**5.1: Configure Schedule**
1. In your sync details, click **"Schedule"** tab
2. Choose frequency:
   - **Recommended:** Daily at 2:00 AM
   - Alternative: Every 6 hours
   - Alternative: Every 12 hours

**5.2: Time Zone**
- Select your time zone
- Ensure it matches your team's working hours

**5.3: Enable Schedule**
- Toggle **"Schedule Enabled"** to ON
- Click **"Save"**

**5.4: Test Schedule (Optional)**
- Click **"Run Now"** to test
- Verify it runs successfully

**Expected result:**
✅ Schedule configured and enabled
✅ Sync will run automatically
✅ Test run succeeds

---

## Step 6: Set Up Monitoring (10 minutes)

**6.1: Configure Census Alerts**

In Census:
1. Go to sync settings
2. Find **"Notifications"** or **"Alerts"**
3. Configure:
   - ✅ Alert on sync failure
   - ✅ Alert if > 10% records fail
   - ✅ Send to: Your email or Slack

**6.2: Create Dashboard Query**

Run this weekly in Databricks:

```sql
-- How many properties waiting to sync?
SELECT COUNT(*) as properties_pending
FROM crm.sfdc_dbx.new_properties_with_features;

-- Should be low (0-50) between syncs
-- Alert if > 100
```

**6.3: Set Up Slack/Email Alerts (Optional)**
- Configure Census to send notifications
- Set up weekly summary reports
- Alert on anomalies

---

## Validation Checklist

After setup is complete, verify:

- [ ] Census model created and previews correctly
- [ ] Census sync created with correct settings
- [ ] All 45 fields mapped
- [ ] Test sync (10 records) succeeded
- [ ] Test records visible in Salesforce
- [ ] Feature data populated correctly
- [ ] Full sync completed successfully
- [ ] Schedule configured (daily at 2am)
- [ ] Alerts/monitoring set up
- [ ] Documented sync URL and settings

**All checked?** ✅ Phase 2 complete!

---

## Troubleshooting

### Issue: Census Can't Find View

**Error:** "Table or view not found"

**Check:**
1. Is view name correct: `crm.sfdc_dbx.new_properties_with_features`?
2. Does Census connection have access to `crm` catalog?
3. Did Phase 1 notebook complete successfully?

**Fix:**
- Re-run Phase 1 notebook
- Check Census connection permissions
- Try refreshing Census schema browser

---

### Issue: Sync Key Field Not Found

**Error:** "Field `Reverse_ETL_ID__c` not found in Salesforce"

**Options:**
1. Use `snappt_property_id_c` instead (if it's an External ID)
2. Ask Salesforce admin to mark `Reverse_ETL_ID__c` as External ID
3. Use a different unique field

**How to check in Salesforce:**
- Go to Setup → Object Manager → Product_Property__c
- Click "Fields & Relationships"
- Look for fields with "External ID" checkbox checked

---

### Issue: Records Failing to Sync

**Error:** Various Salesforce errors

**Common causes:**

**1. Required fields missing:**
- Error mentions "required field"
- Fix: Map missing field in Census
- Or: Set default value in Census

**2. Salesforce Flow errors (again):**
- Error: "CANNOT_EXECUTE_FLOW_TRIGGER"
- Fix: Sync in smaller batches (50 at a time)
- Or: Ask Salesforce admin to optimize Flow

**3. Field mapping errors:**
- Error: "Invalid field" or "Field type mismatch"
- Fix: Check field types match (text → text, date → date)

**4. Duplicate records:**
- Error: "Duplicate external ID"
- Cause: Property already exists in Salesforce
- Fix: View should prevent this, but double-check view WHERE clause

---

### Issue: Feature Data All False

**Problem:** Properties created but all feature flags are False

**Check:**
1. Are features actually enabled for these properties?
   ```sql
   SELECT * FROM crm.sfdc_dbx.product_property_w_features
   WHERE property_id IN (select snappt_property_id_c from new_properties_with_features)
   AND (fraud_enabled = TRUE OR iv_enabled = TRUE);
   ```

2. Is Census mapping feature fields correctly?
   - Check field mappings in Census
   - Verify source → destination match

**If features should be enabled:**
- Properties may not have features enabled yet (correct)
- Or: product_property_w_features data may be missing

---

### Issue: Salesforce Flow Not Triggering

**Problem:** Records created in product_property_c but not flowing to property_c

**Timeline:** Flows can take 5-30 minutes to process

**Check:**
1. Wait 30 minutes and check again
2. Look in Salesforce Setup → Process Automation → Flows
3. Find "Product Property | After | Rollup Flow"
4. Check if it's active
5. Check if there are errors in Flow execution logs

**Fix:**
- If Flow is inactive, activate it
- If Flow has errors, contact Salesforce admin
- May need to manually trigger Flow

---

## Success Metrics

### Immediate (After Setup)
- ✅ Test sync: 10/10 records created
- ✅ Feature data populated in Salesforce
- ✅ No errors in Census logs

### Short-term (First Week)
- ✅ Daily syncs run successfully
- ✅ New properties appear in Salesforce within 24 hours
- ✅ View record count stays low (properties getting synced)

### Long-term (Ongoing)
- ✅ Failure rate < 1%
- ✅ No manual intervention needed
- ✅ Feature data accurate from day 1

---

## What Happens Now

### Daily Schedule
1. **2:00 AM:** Census reads from `new_properties_with_features` view
2. **2:01 AM:** Census syncs any new properties to Salesforce
3. **2:05 AM:** Salesforce Flow triggers
4. **2:30 AM:** Properties appear in final `property_c` table

### When New Property Created
```
Day 0, 10:00 AM: Property created in Snappt app (RDS)
Day 0, 10:15 AM: Fivetran syncs to Databricks
Day 0, 10:15 AM: Appears in new_properties_with_features view
Day 1, 02:00 AM: Census syncs to Salesforce
Day 1, 02:30 AM: Salesforce Flow creates property_c record
```

**Timeline:** New property in production Salesforce within ~16-24 hours

---

## Next Steps After Phase 2

### Phase 3: Update Existing Feature Sync (Already Done!)

Good news: You already have this configured!
- **Sync:** https://app.getcensus.com/workspaces/33026/syncs/3326019/overview
- **Purpose:** Updates feature data for existing properties
- **Status:** Ready, just needs to be scheduled

**To complete:**
1. Run the initial sync (fixes 2,815 properties)
2. Schedule it to run hourly or daily
3. Monitor for first week

### Complete System
After both phases:
- ✅ **Sync 1 (New Properties):** Creates new properties with features
- ✅ **Sync 2 (Feature Updates):** Keeps existing properties accurate
- ✅ **Fully automated:** No manual work needed
- ✅ **Self-healing:** Catches and fixes issues automatically

---

## Documentation Reference

**Related Docs:**
- Phase 1 assets: `/PHASE_1_ASSETS_CREATED.md`
- Future architecture: `/docs/FUTURE_ARCHITECTURE_automated_property_sync.md`
- Feature sync plan: `/docs/product_features_sync_plan.md`

**Census Syncs:**
- New Properties (this phase): [URL after creation]
- Feature Updates (existing): https://app.getcensus.com/workspaces/33026/syncs/3326019/overview

---

## Quick Reference

**View Name:** `crm.sfdc_dbx.new_properties_with_features`
**Census Model:** `New Properties with Features`
**Census Sync:** `New Properties → Salesforce (INSERT with Features)`
**Schedule:** Daily at 2:00 AM
**Fields:** 45 total (21 property + 23 feature + 2 control)
**Sync Behavior:** Upsert (Insert or Update)
**Sync Key:** `Reverse_ETL_ID__c`

---

**Phase 2 Complete!** ✅

You now have a fully automated system for syncing new properties with complete feature data to Salesforce!
