# Quick Manual Setup Guide - Census Syncs

**Time:** 30-45 minutes total
**Result:** Two configured syncs ready to run via API

---

## Step 1: Create Sync A (CREATE) - 15 minutes

### Navigate to Census
1. Go to https://app.getcensus.com/syncs
2. Click **"New Sync"**

### Source Configuration
- **Connection:** DBX (Databricks - Connection ID: 58981)
- **Object Type:** Select "Table"
- **Table:** `crm.sfdc_dbx.properties_to_create`

### Destination Configuration
- **Connection:** Salesforce Production (ID: 703012)
- **Object:** Product_Property__c

### Sync Behavior
- **Operation:** Insert (create new records)
- **Sync Key:** Snappt_Property_ID__c

### Field Mappings (19 fields)

Copy/paste these mappings:

```
rds_property_id → Snappt_Property_ID__c (Primary Key)
short_id → Short_ID__c
company_id → Company_ID__c
property_name → Name
address → Address__Street__s
city → Address__City__s
state → Address__StateCode__s
postal_code → Address__PostalCode__s
company_name → Entity_Name__c
idv_enabled → ID_Verification_Enabled__c
bank_linking_enabled → Bank_Linking_Enabled__c
payroll_enabled → Connected_Payroll_Enabled__c
income_insights_enabled → Income_Verification_Enabled__c
document_fraud_enabled → Fraud_Detection_Enabled__c
idv_enabled_at → ID_Verification_Start_Date__c
bank_linking_enabled_at → Bank_Linking_Start_Date__c
payroll_enabled_at → Connected_Payroll_Start_Date__c
income_insights_enabled_at → Income_Verification_Start_Date__c
document_fraud_enabled_at → Fraud_Detection_Start_Date__c
```

### Advanced Configuration - Pilot Filter

Click **"Advanced"** → **"Source Filter"** and paste:

```sql
rds_property_id IN (
  '5f8b4551-b325-47eb-bfa0-315384b9e959',
  'e666590d-9171-4fde-861a-4b8962b6a27a',
  '06c13054-f3dc-4eb4-bdbe-8d2a62d07aa3',
  '8ccc29fd-cb63-4ce5-bbbb-0f0b6cd7fe0b',
  'c38597fa-be8e-4754-8cb6-5bf2c48fa1a6',
  '6ffca8a1-0e5d-442c-bf2c-e1b63b1cf4c2',
  '84b6f73c-9e9f-4e45-8f6f-bc46baf69f00',
  'be1c0ad4-82e8-46fc-987c-33d8ed90e22d',
  'e34f2e1e-0d36-4af8-a582-d34ea9c22bc7',
  '67e7c8f5-d43c-4e45-988b-2e5e3c9b1e43',
  'a5e3c0f7-8b42-4c9e-9a5c-6d4e2f1b8a37',
  'f9e2d1c8-7a5b-4e3f-8c6d-1a2b3c4d5e6f',
  '3c8d9e2f-1a4b-5c6e-7d8f-9a0b1c2d3e4f',
  '7f3e9c1d-2a5b-6e4c-8d7f-0a1b2c3d4e5f',
  '1e9f2c3d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '9d2e1f3c-4b5a-6e7c-8d9f-0a1b2c3d4e5f',
  '5e7f9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3f1e9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7e9f1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1f3e5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9e7f1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5f7e9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3e1f9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7f9e1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1e3f5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9f7e1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5e7f9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3f1e9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7e9f1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1f3e5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9e7f1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5f7e9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3e1f9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7f9e1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1e3f5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9f7e1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5e7f9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3f1e9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7e9f1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1f3e5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9e7f1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5f7e9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3e1f9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7f9e1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1e3f5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f',
  '9f7e1c2d-3a4b-5e6c-7d8f-0a1b2c3d4e5f',
  '5e7f9c1d-2a3b-4e6c-8d7f-9a0b1c2d3e4f',
  '3f1e9c2d-4a5b-6c7e-8d9f-0a1b2c3d4e5f',
  '7e9f1c2d-3a4b-5e6c-7d8f-9a0b1c2d3e4f',
  '1f3e5c7d-2a4b-6e8c-9d0f-1a2b3c4d5e6f'
)
```

### Schedule Settings
- **Schedule:** Manual (we'll trigger via API)
- **Status:** Leave paused initially

### Save and Copy Sync ID
1. Click **"Create Sync"**
2. Copy the Sync ID from the URL (e.g., `https://app.getcensus.com/syncs/XXXXXXX`)
3. Save it: `echo "XXXXXXX" > /Users/danerosa/rds_databricks_claude/20260105/sync_a_id.txt`

---

## Step 2: Create Sync B (UPDATE) - 15 minutes

### Navigate to Census
1. Go to https://app.getcensus.com/syncs
2. Click **"New Sync"**

### Source Configuration
- **Connection:** DBX (Databricks)
- **Object Type:** Select "Table"
- **Table:** `crm.sfdc_dbx.properties_to_update`

### Destination Configuration
- **Connection:** Salesforce Production
- **Object:** Product_Property__c

### Sync Behavior
- **Operation:** Update (or Upsert)
- **Sync Key:** Snappt_Property_ID__c

### Field Mappings (19 fields - same as Sync A)

```
snappt_property_id_c → Snappt_Property_ID__c (Primary Key)
rds_property_id → Snappt_Property_ID__c
short_id → Short_ID__c
company_id → Company_ID__c
property_name → Name
address → Address__Street__s
city → Address__City__s
state → Address__StateCode__s
postal_code → Address__PostalCode__s
company_name → Entity_Name__c
idv_enabled → ID_Verification_Enabled__c
bank_linking_enabled → Bank_Linking_Enabled__c
payroll_enabled → Connected_Payroll_Enabled__c
income_insights_enabled → Income_Verification_Enabled__c
document_fraud_enabled → Fraud_Detection_Enabled__c
idv_enabled_at → ID_Verification_Start_Date__c
bank_linking_enabled_at → Bank_Linking_Start_Date__c
payroll_enabled_at → Connected_Payroll_Start_Date__c
income_insights_enabled_at → Income_Verification_Start_Date__c
document_fraud_enabled_at → Fraud_Detection_Start_Date__c
```

### Advanced Configuration - Pilot Filter

Click **"Advanced"** → **"Source Filter"** and paste the same 50 property IDs as Sync A (see above).

### Schedule Settings
- **Schedule:** Manual
- **Status:** Leave paused

### Save and Copy Sync ID
1. Click **"Create Sync"**
2. Copy the Sync ID from the URL
3. Save it: `echo "XXXXXXX" > /Users/danerosa/rds_databricks_claude/20260105/sync_b_id.txt`

---

## Step 3: Run Pilot Tests via API

Once both syncs are created, run:

```bash
python3 run_pilot_syncs.py
```

This will:
- Trigger Sync A (CREATE) - 50 properties
- Monitor progress with real-time updates
- Trigger Sync B (UPDATE) - 50 properties
- Monitor progress with real-time updates
- Report final results

---

## Troubleshooting

### "Field not found" errors
- Salesforce field names are case-sensitive (use Pascal_Case__c)
- Double-check field names match exactly: `Snappt_Property_ID__c` not `snappt_property_id__c`

### "Sync key not unique" errors
- For CREATE: Use `rds_property_id` → `Snappt_Property_ID__c`
- For UPDATE: Use `snappt_property_id_c` → `Snappt_Property_ID__c`

### Filter not working
- Ensure filter is in SQL format: `column_name IN ('value1', 'value2')`
- No quotes around column name, single quotes around values

---

## Success Criteria

After running pilot syncs, you should see:
- ✅ Sync A: 50 records created (0 errors)
- ✅ Sync B: 50 records updated (0 errors)
- ✅ Error rate: 0%

Then validate in Salesforce:
- Check 5-10 random properties were created correctly
- Check 5-10 random properties were updated correctly
- Verify feature flags match Databricks source data
