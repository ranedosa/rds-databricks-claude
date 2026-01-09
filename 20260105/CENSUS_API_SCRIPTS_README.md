# Census API Configuration Scripts - README

**Purpose:** Automatically configure Census Sync A (CREATE) and Sync B (UPDATE) via API

**Estimated Time:** 5-10 minutes total (vs 1-2 hours manual configuration)

---

## 📋 Prerequisites

✅ Day 1 views created in Databricks
✅ Census API credentials in `/Users/danerosa/rds_databricks_claude/config/census_credentials.json`
✅ Pilot CSV files exported
✅ Python 3.x with `requests` library installed

---

## 🚀 Quick Start (3 Steps)

### Step 1: Configure Both Syncs (One Command)

```bash
cd /Users/danerosa/rds_databricks_claude/20260105
python3 configure_all_syncs.py
```

**What this does:**
1. Gets your Census connection IDs from API
2. Creates Sync A (CREATE) with 22 field mappings + pilot filter
3. Creates Sync B (UPDATE) with 27 field mappings + pilot filter
4. Saves sync IDs to files

**Expected output:**
```
✅ Sync A (CREATE) created successfully!
   Sync ID: 12345

✅ Sync B (UPDATE) created successfully!
   Sync ID: 12346
```

---

### Step 2: Review Syncs in Census UI (Optional)

1. Open: https://app.getcensus.com/syncs/{sync_id}
2. Verify field mappings look correct
3. Check pilot filter is applied (should show ~50 rows)

---

### Step 3: Run Pilot Tests

```bash
python3 run_pilot_syncs.py
```

**What this does:**
1. Triggers Sync A (CREATE) - syncs 50 new properties
2. Monitors progress until complete
3. Triggers Sync B (UPDATE) - syncs 50 existing properties
4. Monitors progress until complete
5. Reports success/failure

**Expected output:**
```
✅ Sync A (CREATE) completed successfully!
   Records Processed: 50
   Records Updated: 50
   Records Failed: 0

✅ Sync B (UPDATE) completed successfully!
   Records Processed: 50
   Records Updated: 50
   Records Failed: 0
```

---

## 📁 Files Created

### Configuration Scripts

1. **census_api_setup.py**
   - Gets Census connection IDs
   - Discovers Databricks and Salesforce connections
   - Saves IDs to `census_ids.json`

2. **configure_sync_a_create.py**
   - Creates Sync A (CREATE) configuration
   - Maps 22 fields
   - Adds pilot filter for 50 properties
   - Saves sync ID to `sync_a_id.txt`

3. **configure_sync_b_update.py**
   - Creates Sync B (UPDATE) configuration
   - Maps 27 fields (includes aggregation metrics)
   - Adds pilot filter for 50 properties
   - Saves sync ID to `sync_b_id.txt`

4. **configure_all_syncs.py** ⭐ **USE THIS**
   - Master script that runs all 3 above
   - One-command configuration

5. **run_pilot_syncs.py** ⭐ **USE THIS**
   - Triggers both pilot syncs
   - Monitors progress
   - Reports results

### Generated Files

- `census_ids.json` - Connection IDs from Census
- `sync_a_id.txt` - Sync A (CREATE) ID
- `sync_b_id.txt` - Sync B (UPDATE) ID

---

## 🔧 Manual Configuration (If Scripts Fail)

If the API scripts fail, you can still configure manually:

1. Follow: `CENSUS_SYNC_A_CREATE_GUIDE.md`
2. Use filter from: `PILOT_CREATE_FILTER.sql`
3. Repeat for Sync B (UPDATE)

---

## ⚠️ Troubleshooting

### Error: "Module 'requests' not found"

```bash
pip3 install requests
```

### Error: "Census API credentials not found"

Check: `/Users/danerosa/rds_databricks_claude/config/census_credentials.json`

Should contain:
```json
{
  "api_key": "secret-token:YOUR_KEY_HERE",
  "api_base_url": "https://app.getcensus.com/api/v1"
}
```

### Error: "Connection ID not found"

The script will use default connection ID `58981` from your existing sync.
If this fails, manually add to `census_ids.json`:
```json
{
  "databricks_connection_id": 58981,
  "salesforce_destination_id": YOUR_SF_CONNECTION_ID
}
```

### Error: "Pilot CSV not found"

Ensure these files exist:
- `/Users/danerosa/rds_databricks_claude/20260105/pilot_create_properties.csv`
- `/Users/danerosa/rds_databricks_claude/20260105/pilot_update_properties.csv`

---

## 📊 What Gets Configured

### Sync A (CREATE) Configuration

**Source:** `crm.sfdc_dbx.properties_to_create`
**Destination:** Salesforce `product_property__c`
**Operation:** INSERT (create new records)
**Sync Key:** `sf_property_id__c`
**Pilot Filter:** 50 property IDs from `pilot_create_properties.csv`

**Field Mappings (22):**
- 4 identifiers (sfdc_id, rds_property_id, short_id, company_id)
- 6 property attributes (name, address, city, state, postal_code, company_name)
- 5 feature flags (idv_enabled, bank_linking_enabled, etc.)
- 5 feature timestamps (*_enabled_at)
- 2 metadata fields (created_at, updated_at)

---

### Sync B (UPDATE) Configuration

**Source:** `crm.sfdc_dbx.properties_to_update`
**Destination:** Salesforce `product_property__c`
**Operation:** UPSERT (update existing records)
**Sync Key:** `snappt_property_id__c`
**Pilot Filter:** 50 property IDs from `pilot_update_properties.csv`

**Field Mappings (27):**
- Same 22 fields as Sync A, PLUS:
- 3 aggregation metrics (active_property_count, total_feature_count, is_multi_property)
- 2 additional identifiers for UPDATE mode

---

## ✅ Success Criteria

After running `run_pilot_syncs.py`, you should see:

**Sync A (CREATE):**
- ✅ 50 records processed
- ✅ 50 records created
- ✅ 0 records failed
- ✅ Error rate: 0%

**Sync B (UPDATE):**
- ✅ 50 records processed
- ✅ 50 records updated
- ✅ 0 records failed
- ✅ Error rate: 0%

**If error rate > 10%:**
- ❌ STOP - Do not proceed to Day 3
- Review errors in Census UI
- Check Salesforce field permissions
- Verify Databricks views have correct data

---

## 📋 Next Steps After Pilot Success

1. **Validate in Salesforce:**
   - Check 50 new records created
   - Check 50 existing records updated
   - Verify feature flags correct

2. **Run Databricks validation:**
   ```sql
   SELECT * FROM crm.sfdc_dbx.daily_health_check;
   ```

3. **Make GO/NO-GO decision:**
   - ✅ GO: Remove pilot filters, run full rollout (Day 3)
   - ❌ NO-GO: Debug issues, retry pilot

4. **Document results:**
   ```sql
   INSERT INTO crm.sfdc_dbx.sync_audit_log VALUES (
     'pilot_sync_a', 'Pilot Sync A', 'CREATE',
     CURRENT_TIMESTAMP(), 50, 50, 0, 0.0,
     CURRENT_USER(), 'Pilot test successful'
   );
   ```

---

## 🎯 Commands Summary

```bash
# 1. Configure both syncs (one command)
python3 configure_all_syncs.py

# 2. Run pilot tests
python3 run_pilot_syncs.py

# 3. (Optional) Run individual scripts
python3 census_api_setup.py
python3 configure_sync_a_create.py
python3 configure_sync_b_update.py
```

---

**Status:** Ready to run!

**Estimated Total Time:** 5-10 minutes

**Manual Configuration Time Saved:** 1-2 hours
