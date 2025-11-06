# Salesforce to Snappt Property Sync Job - Setup Guide

## Overview

This Databricks job syncs new properties from Salesforce to Snappt API on a daily schedule.

**Notebook Location:** `/scripts/jobs/salesforce_property_sync.py`

## What the Job Does

1. **Queries Salesforce** - Reads properties added in the last 24 hours from `crm.salesforce.property`
2. **Writes to Temp Table** - Stores new properties in `team_sandbox.data_engineering.temp_new_salesforce_properties`
3. **Checks RDS** - Verifies if property already exists in `rds.pg_rds_public.properties` using `sfdc_id` column
4. **Creates in Snappt** - If property doesn't exist, makes POST request to Snappt API to create it
5. **Verifies Creation** - Confirms the property appears in RDS after creation

## Prerequisites

### 1. Databricks Secret Scope Setup

You need to create a secret scope to store the Snappt API token securely:

```bash
# Using Databricks CLI
databricks secrets create-scope snappt-api

# Add the API bearer token
databricks secrets put-secret snappt-api bearer-token
# This will open an editor - paste the token: 5f5770c2-0563-11ee-be56-0242ac120003
```

**Alternative:** If you don't want to use secrets, you can modify line 32 in the notebook:
```python
# Change this line:
SNAPPT_API_TOKEN = dbutils.secrets.get(scope="snappt-api", key="bearer-token")

# To this (hardcoded - not recommended for production):
SNAPPT_API_TOKEN = "5f5770c2-0563-11ee-be56-0242ac120003"
```

### 2. Required Tables/Databases

Ensure these tables are accessible in your workspace:
- `crm.salesforce.property` - Source Salesforce data
- `rds.pg_rds_public.properties` - Target RDS properties table
- `team_sandbox.data_engineering` - Schema for temp table (will be auto-created)

### 3. Required Libraries

The notebook uses these Python libraries (should be pre-installed in Databricks):
- `requests` - For API calls
- `pyspark` - For data processing

## Setup Instructions

### Step 1: Upload Notebook to Databricks Workspace

1. Log into your Databricks workspace
2. Navigate to **Workspace** → **Users** → **{your-email}**
3. Create a folder structure: `rds_databricks_claude/scripts/jobs/`
4. Click **Import** and upload `salesforce_property_sync.py`

### Step 2: Configure Databricks Secrets (Recommended)

```bash
# Create secret scope
databricks secrets create-scope snappt-api

# Add bearer token
databricks secrets put-secret snappt-api bearer-token
# Paste: 5f5770c2-0563-11ee-be56-0242ac120003
```

### Step 3: Create the Databricks Job

1. Go to **Workflows** in Databricks
2. Click **Create Job**
3. Configure the job:

   **Job Settings:**
   - **Name:** `Salesforce to Snappt Property Sync`
   - **Task name:** `salesforce_property_sync`
   - **Type:** Notebook
   - **Path:** `/Users/{your-email}/rds_databricks_claude/scripts/jobs/salesforce_property_sync`
   - **Cluster:** Select an existing cluster or create new

   **Schedule (Cron):**
   - **Schedule type:** Scheduled
   - **Cron expression:** `0 0 2 * * ?` (Daily at 2:00 AM PST)
   - **Timezone:** `America/Los_Angeles`

   **Advanced Settings:**
   - **Max concurrent runs:** 1
   - **Timeout:** 3600 seconds (1 hour)
   - **Retries:** 2
   - **Retry on timeout:** Enabled

   **Notifications:**
   - **On failure:** Add your email
   - **On success:** Optional

4. Click **Create**

### Step 4: Test the Job

Before scheduling, test the job manually:

1. Open the notebook in Databricks
2. Attach to a cluster
3. Run all cells manually to verify:
   - Tables are accessible
   - API authentication works
   - Temp table is created successfully
   - Properties are processed correctly

## Configuration Options

You can modify these variables in the notebook (lines 24-32):

```python
# API Configuration
SNAPPT_API_URL = "https://enterprise-api.test.snappt.com/properties"

# Database Configuration
SALESFORCE_TABLE = "crm.salesforce.property"
RDS_PROPERTIES_TABLE = "rds.pg_rds_public.properties"
TEMP_TABLE = "team_sandbox.data_engineering.temp_new_salesforce_properties"

# Time Configuration
LOOKBACK_HOURS = 24  # How far back to check for new properties
```

## Table Schemas

### Source: crm.salesforce.property
- `id` - Salesforce property ID (used as sfdc_id)
- `name` - Property name
- `company_id_c` - Salesforce company ID
- `company_name_c` - Company/account name
- `address_street_s` - Street address
- `address_city_s` - City
- `address_state_s` - State
- `address_postal_code_s` - ZIP code
- `unit_c` - Unit count
- `email_c` - Property manager email
- `status_c` - Property status
- `createddate` - When property was created in Salesforce

### Target: rds.pg_rds_public.properties
- `id` - Primary key
- `sfdc_id` - Salesforce property ID (used for matching)
- `name` - Property name
- `email` - Property manager email
- `address` - Street address
- `city` - City
- `zip` - ZIP code
- Other fields...

### Temp Table: team_sandbox.data_engineering.temp_new_salesforce_properties
This table stores properties processed in the current run and includes:
- All fields from Salesforce query
- `processing_timestamp` - When the job ran
- `sync_status` - Status field (currently set to "pending")

## Snappt API Details

**Endpoint:** `https://enterprise-api.test.snappt.com/properties`

**Method:** POST

**Headers:**
```json
{
  "accept": "application/json",
  "content-type": "application/json",
  "Authorization": "Bearer 5f5770c2-0563-11ee-be56-0242ac120003"
}
```

**Payload:**
```json
{
  "name": "Property Name",
  "email": "manager@example.com",
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94102",
  "unit": 100,
  "status": "Active",
  "pmcName": "Company Name",
  "sfdc_id": "a01Dn00000HHNKjIAP"
}
```

## Monitoring and Troubleshooting

### View Job Runs
1. Go to **Workflows** → **Jobs**
2. Click on **Salesforce to Snappt Property Sync**
3. View **Runs** tab for execution history

### Check Temp Table
```sql
SELECT *
FROM team_sandbox.data_engineering.temp_new_salesforce_properties
ORDER BY sf_created_date DESC
```

### Check Recently Created Properties in RDS
```sql
SELECT
  p.id,
  p.name,
  p.sfdc_id,
  p.inserted_at,
  c.name as company_name
FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE p.inserted_at >= CURRENT_DATE
ORDER BY p.inserted_at DESC
```

### Common Issues

**Issue:** "Secret scope not found"
- **Solution:** Create the secret scope: `databricks secrets create-scope snappt-api`

**Issue:** "Table not found: crm.salesforce.property"
- **Solution:** Verify you have access to the Salesforce catalog/database

**Issue:** "API authentication failed"
- **Solution:** Verify the bearer token is correct in secrets or hardcoded value

**Issue:** "Property not appearing in RDS after creation"
- **Solution:** Check if there's a delay in the Fivetran sync from Snappt → RDS. The job retries 3 times with 5-second delays.

## Maintenance

### Changing the Schedule
1. Go to **Workflows** → **Jobs** → **Salesforce to Snappt Property Sync**
2. Click **Edit schedule**
3. Modify cron expression or timezone
4. Save changes

### Updating API Token
```bash
# Update the secret
databricks secrets put-secret snappt-api bearer-token
# Paste new token value
```

### Changing Lookback Period
Edit the notebook and change `LOOKBACK_HOURS = 24` to desired value (e.g., 48 for 2 days)

## Job Output

The job prints a detailed summary at the end of each run:

```
================================================================================
JOB SUMMARY
================================================================================
Total properties processed:     5
Already existed in RDS:         2
Created via API:                3
Failed to create:               0
Successfully verified in RDS:   3
Verification failed:            0

Completed at: 2024-11-04 02:15:32
================================================================================
```

## Next Steps

1. Upload the notebook to Databricks
2. Set up secrets (or use hardcoded token for testing)
3. Create the job with daily schedule
4. Run manually to test
5. Monitor first few scheduled runs
6. Adjust lookback period or schedule as needed

## Support

For issues or questions:
- Check Databricks job logs for detailed error messages
- Review temp table for properties that were processed
- Verify API connectivity using the test script: `create_property_api.py`
- Contact Data Engineering team

---

**Created:** 2024-11-04
**Notebook:** `/scripts/jobs/salesforce_property_sync.py`
**Schedule:** Daily at 2:00 AM PST
