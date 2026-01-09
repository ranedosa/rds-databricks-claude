# Quick Reference Guide - Census Sync Operations

**For:** Daily operations and troubleshooting
**Last Updated:** January 7, 2026

---

## 🚀 Quick Commands

### Trigger Syncs
```bash
# CREATE sync (Sync A)
curl -X POST -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394022/trigger

# UPDATE sync (Sync B)
curl -X POST -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394041/trigger
```

### Check Status
```bash
# Sync A status
curl -s -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394022/sync_runs | jq '.data[0] | {status, records_processed, records_updated, records_failed}'

# Sync B status
curl -s -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394041/sync_runs | jq '.data[0] | {status, records_processed, records_updated, records_failed}'
```

---

## 📊 Key Information

### Sync IDs
- **Sync A (CREATE):** 3394022
- **Sync B (UPDATE):** 3394041

### Connection IDs
- **Databricks:** 58981
- **Salesforce:** 703012

### Sync URLs
- **Sync A:** https://app.getcensus.com/syncs/3394022
- **Sync B:** https://app.getcensus.com/syncs/3394041

### Source Tables
- **CREATE:** `crm.sfdc_dbx.properties_to_create` (735 rows)
- **UPDATE:** `crm.sfdc_dbx.properties_to_update` (7,881 rows)

### Destination
- **Salesforce Object:** Product_Property__c
- **Sync Key:** Snappt_Property_ID__c (External ID)

---

## 📁 Important Files

### Documentation
- **`DAY2_SESSION_SUMMARY.md`** - Complete session documentation
- **`PILOT_RESULTS.md`** - Pilot test results and validation checklist
- **`QUICK_MANUAL_SETUP_GUIDE_FINAL.md`** - Manual configuration guide
- **`QUICK_REFERENCE.md`** - This file

### Scripts
- **`run_pilot_syncs.py`** - Automated sync execution (has input prompt)
- **`save_sync_ids.py`** - Helper to save sync IDs

### Data
- **`sync_a_id.txt`** - Sync A ID
- **`sync_b_id.txt`** - Sync B ID
- **`census_ids.json`** - Connection IDs

---

## 🔧 Common Operations

### Run Full Rollout (Day 3)

**Prerequisites:**
1. Remove LIMIT 50 from Census models
2. Validate pilot results in Salesforce
3. Make GO/NO-GO decision

**Commands:**
```bash
# Trigger both syncs
curl -X POST -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394022/trigger

curl -X POST -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/3394041/trigger

# Monitor (run in separate terminals)
watch -n 30 'curl -s -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" https://app.getcensus.com/api/v1/syncs/3394022/sync_runs | jq ".data[0]"'

watch -n 30 'curl -s -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" https://app.getcensus.com/api/v1/syncs/3394041/sync_runs | jq ".data[0]"'
```

### Check Databricks Source Data
```sql
-- Check CREATE queue
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;

-- Check UPDATE queue
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;

-- View sample CREATE records
SELECT * FROM crm.sfdc_dbx.properties_to_create LIMIT 10;

-- View sample UPDATE records
SELECT * FROM crm.sfdc_dbx.properties_to_update LIMIT 10;
```

### Validate in Salesforce
```sql
-- Check recently synced properties
SELECT
  Snappt_Property_ID__c,
  Name,
  ID_Verification_Enabled__c,
  Bank_Linking_Enabled__c,
  Fraud_Detection_Enabled__c,
  LastModifiedDate
FROM Product_Property__c
WHERE LastModifiedDate >= YESTERDAY
ORDER BY LastModifiedDate DESC
LIMIT 100;

-- Count total properties
SELECT COUNT(*) FROM Product_Property__c;
```

---

## ⚠️ Troubleshooting

### Sync Failed

**Check error message:**
```bash
curl -s -H "Authorization: Bearer secret-token:HyMHBwFx95V4gdjdqufvfZuz" \
  https://app.getcensus.com/api/v1/syncs/{SYNC_ID}/sync_runs | \
  jq '.data[0] | {status, error_message, error_detail}'
```

**Common issues:**
- Field permission errors → Check Salesforce field-level security
- Data type mismatches → Review field mappings
- Sync key conflicts → Check for duplicate Snappt_Property_ID__c values
- Rate limiting → Wait and retry

### High Error Rate

**If error rate > 10%:**
1. **STOP** - Pause sync
2. Review errors in Census UI
3. Check sample failed records
4. Fix root cause
5. Retry with smaller batch

### View Data Issues

**If source view counts are wrong:**
```sql
-- Refresh Day 1 views
-- Re-run VIEW1, VIEW2, VIEW3, VIEW4 creation scripts
```

---

## 📈 Performance Expectations

### Pilot (50 records each)
- **Sync A:** ~52 seconds
- **Sync B:** ~53 seconds
- **Total:** ~2 minutes

### Full Rollout (estimated)
- **Sync A (735):** ~15 minutes
- **Sync B (7,881):** ~2.5 hours
- **Total:** ~3 hours

### Throughput
- ~50 records/minute average
- Census rate limiting may vary

---

## ✅ Success Criteria

### Per Sync Run
- ✅ Error rate < 10%
- ✅ No sync key conflicts
- ✅ Execution time reasonable
- ✅ No field permission errors

### Data Quality
- ✅ Feature flags match Databricks
- ✅ Timestamps populated
- ✅ No duplicate records
- ✅ Address fields complete
- ✅ Property names correct

---

## 📞 Contacts

**Salesforce Admin:** [Contact for External ID changes, field permissions]
**Databricks Admin:** [Contact for view issues, data quality]
**Census Support:** support@getcensus.com

---

## 🔗 Useful Links

- **Census Dashboard:** https://app.getcensus.com/syncs
- **Sync A:** https://app.getcensus.com/syncs/3394022
- **Sync B:** https://app.getcensus.com/syncs/3394041
- **Census API Docs:** https://docs.getcensus.com/basics/api
- **Databricks Workspace:** https://dbc-9ca0f5e0-2208.cloud.databricks.com

---

## 📅 Maintenance Schedule

**Daily:**
- Check sync run status
- Review error logs if any

**Weekly:**
- Validate data quality in SF
- Compare sample records with Databricks
- Check for data drift

**Monthly:**
- Full reconciliation report
- Update field mappings if needed
- Review sync frequency

---

## 🚨 Emergency Procedures

### Pause Syncs Immediately
1. Go to Census UI
2. Navigate to sync
3. Click "Pause"
4. Investigate issue

### Rollback (if needed)
- Census doesn't support rollback
- Manual data fixes required in Salesforce
- Use backup data from Databricks views

### Escalation
1. Check Census UI for detailed errors
2. Review Salesforce logs
3. Contact Census support with sync IDs
4. Provide error logs and timestamp

---

**Need Help?** See `DAY2_SESSION_SUMMARY.md` for complete documentation
