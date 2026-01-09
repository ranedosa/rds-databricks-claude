# Day 2: Hybrid Approach - Manual Setup + API Execution

**Strategy:** Create syncs manually in Census UI (30-45 min), then automate execution and monitoring via API.

**Why Hybrid?**
- Manual configuration: Guaranteed to work, visual feedback
- API execution: Fast, repeatable, automated monitoring

---

## Quick Start (3 Steps)

### Step 1: Create Syncs Manually (30-45 minutes)

Follow the guide: **`QUICK_MANUAL_SETUP_GUIDE.md`**

Key actions:
1. Create Sync A (CREATE) in Census UI
2. Create Sync B (UPDATE) in Census UI
3. Apply pilot filters (50 properties each)
4. Leave both syncs paused

### Step 2: Save Sync IDs (1 minute)

After creating both syncs, run:

```bash
cd /Users/danerosa/rds_databricks_claude/20260105
python3 save_sync_ids.py
```

This will prompt you to enter the Sync IDs and save them to files.

### Step 3: Run Pilot Tests via API (5-10 minutes)

```bash
python3 run_pilot_syncs.py
```

This will:
- Trigger Sync A (CREATE) automatically
- Monitor progress in real-time
- Wait for completion
- Trigger Sync B (UPDATE) automatically
- Monitor progress in real-time
- Report final results

---

## Files Overview

### Manual Setup Guides
- **`QUICK_MANUAL_SETUP_GUIDE.md`** ⭐ **START HERE**
  - Step-by-step UI configuration
  - All field mappings provided
  - Pilot filter SQL included

- **`CENSUS_SYNC_A_CREATE_GUIDE.md`**
  - Detailed guide for Sync A
  - Background context and rationale

### Pilot Data
- **`pilot_create_properties.csv`** - 50 properties for CREATE test
- **`pilot_update_properties.csv`** - 50 properties for UPDATE test
- **`PILOT_CREATE_FILTER.sql`** - SQL filter for Sync A
- **`PILOT_UPDATE_FILTER.sql`** - SQL filter for Sync B

### Automation Scripts ⭐ **USE THESE**
- **`save_sync_ids.py`** - Helper to save sync IDs after manual creation
- **`run_pilot_syncs.py`** - Trigger and monitor both syncs via API

### Day 1 Views (Already Created)
- `crm.sfdc_dbx.properties_to_create` - 735 rows
- `crm.sfdc_dbx.properties_to_update` - 7,881 rows

---

## Expected Timeline

| Task | Time | Status |
|------|------|--------|
| Create Sync A in Census UI | 15 min | ⏳ Pending |
| Create Sync B in Census UI | 15 min | ⏳ Pending |
| Save Sync IDs | 1 min | ⏳ Pending |
| Run automated pilot tests | 5-10 min | ⏳ Pending |
| Validate results in Salesforce | 10-15 min | ⏳ Pending |
| **Total** | **45-60 min** | |

---

## Success Criteria

### After Pilot Execution:
- ✅ Sync A: 50 records created (0 errors)
- ✅ Sync B: 50 records updated (0 errors)
- ✅ Error rate: < 10%

### After Salesforce Validation:
- ✅ New properties visible in Salesforce with correct data
- ✅ Updated properties show latest feature flags
- ✅ No duplicate records created
- ✅ Feature timestamps match Databricks source

---

## Decision Point: GO/NO-GO for Day 3

**GO Criteria:**
- ✅ Error rate < 10% for both syncs
- ✅ Data quality validated in Salesforce
- ✅ No unexpected side effects

**If GO:**
→ Proceed to Day 3: Full Rollout (remove pilot filters, sync all properties)

**If NO-GO:**
→ Debug issues, adjust configuration, retry pilot

---

## Why API Configuration Failed

We encountered 3 issues with Census API:
1. **Table object format**: Required complex nested structure
2. **Field mapping format**: Needed `{"type": "column", "data": "name"}` not simple strings
3. **Unknown 500 errors**: API returned internal errors without details

**Lessons learned:**
- Census UI is more reliable for initial configuration
- Census API is better suited for execution/monitoring
- Hybrid approach is most pragmatic

---

## Next Steps After Day 2

Once pilot succeeds:

**Day 3: Full Rollout**
1. Remove pilot filters from both syncs
2. Run full sync (735 CREATE + 7,881 UPDATE)
3. Monitor for errors
4. Validate representative sample in Salesforce
5. Schedule recurring syncs (daily/hourly)

**Ongoing Operations**
- Monitor sync health via Census dashboard
- Set up alerts for sync failures
- Review `crm.sfdc_dbx.daily_health_check` view
- Investigate and resolve any data quality issues

---

## Commands Cheat Sheet

```bash
# Navigate to working directory
cd /Users/danerosa/rds_databricks_claude/20260105

# Save sync IDs after manual creation
python3 save_sync_ids.py

# Run pilot tests
python3 run_pilot_syncs.py

# Check view counts
# (Run in Databricks SQL editor)
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;  -- Should be 735
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;  -- Should be 7,881
```

---

## Troubleshooting

### Sync IDs not saved
```bash
# Manually save sync IDs
echo "YOUR_SYNC_A_ID" > sync_a_id.txt
echo "YOUR_SYNC_B_ID" > sync_b_id.txt
```

### Pilot script can't find sync IDs
```bash
# Check files exist
ls -la sync_a_id.txt sync_b_id.txt

# View contents
cat sync_a_id.txt
cat sync_b_id.txt
```

### High error rate in pilot
- Review errors in Census UI sync run details
- Check Salesforce field permissions
- Verify data types match (boolean, date, string)
- Check for NULL values in required fields

---

**Current Status:** Ready for manual sync creation

**Next Action:** Follow `QUICK_MANUAL_SETUP_GUIDE.md` to create both syncs
