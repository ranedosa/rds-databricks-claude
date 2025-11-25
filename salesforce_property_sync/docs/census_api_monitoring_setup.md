# Census API Monitoring Setup

Monitor your Census syncs programmatically using the Census API.

---

## Quick Setup

### 1. Get Your Census API Key

1. Go to https://app.getcensus.com/
2. Click on your profile/settings (bottom left)
3. Navigate to **Settings** → **API Keys**
4. Click **Create New API Key**
5. Give it a name (e.g., "Databricks Monitoring")
6. Copy the API key

### 2. Add API Key to Config File

Open the config file:
```bash
code /Users/danerosa/rds_databricks_claude/config/census_credentials.json
```

Replace `YOUR_CENSUS_API_KEY_HERE` with your actual API key:

```json
{
  "api_key": "your_actual_api_key_here",
  "api_base_url": "https://app.getcensus.com/api/v1"
}
```

**⚠️ Security Note:** This file contains sensitive credentials. Do NOT commit it to git.

### 3. Install Required Package

```bash
pip install requests
```

### 4. Run the Monitoring Script

```bash
cd /Users/danerosa/rds_databricks_claude
source venv/bin/activate
python scripts/monitor_census_sync.py
```

---

## What the Script Does

The monitoring script will:

1. ✅ **List all your Census syncs**
   - Shows sync ID, label, status, and destination

2. 🔍 **Identify your product_property sync**
   - Automatically finds syncs related to Salesforce product_property

3. 📊 **Show recent sync runs**
   - Last 5 runs with status, timing, and statistics

4. 📈 **Display detailed statistics**
   - Records processed
   - Records created/updated
   - Failed/invalid records
   - Error messages if any

5. ⚠️ **Highlight issues**
   - Flags failed or invalid records
   - Shows error messages
   - Provides link to Census UI for details

---

## Example Output

```
================================================================================
CENSUS SYNC MONITOR
================================================================================
✅ Credentials loaded

================================================================================
FETCHING CENSUS SYNCS
================================================================================

Found 5 syncs

================================================================================
ALL CENSUS SYNCS
================================================================================

1. Sync ID: 12345
   Label: RDS Properties to Salesforce
   Status: active
   Destination: Product_Property__c
   ⭐ THIS LOOKS LIKE YOUR PROPERTY SYNC!

================================================================================
RECENT RUNS FOR: RDS Properties to Salesforce
================================================================================

1. Run ID: 67890
   Status: completed
   Started: 2025-11-21 10:45:00
   Completed: 2025-11-21 10:48:23
   Duration: 203.0 seconds
   📊 Stats:
      Processed: 1,297
      Updated: 0
      Created: 1,297
      Failed: 0
      Invalid: 0
   ✅ SUCCESS

================================================================================
LATEST RUN DETAILS: RDS Properties to Salesforce
================================================================================

Run ID: 67890
Status: completed
Created: 2025-11-21T10:45:00Z
Completed: 2025-11-21T10:48:23Z

📊 Record Statistics:
  Processed: 1,297
  Created: 1,297
  Updated: 0
  Failed: 0
  Invalid: 0
```

---

## Use Cases

### During Sync
Run the script to see real-time progress:
```bash
python scripts/monitor_census_sync.py
```

### Check for Errors
If the sync fails, the script will show:
- Number of failed records
- Error messages
- Link to Census UI for detailed logs

### Validate Success
After sync completes, verify:
- All 1,297 records were created
- No failed or invalid records
- Total processed matches expected count

---

## Troubleshooting

### Error: "Invalid API Key"
**Solution:** Double-check your API key in the config file

### Error: "Module 'requests' not found"
**Solution:** Run `pip install requests` in your virtual environment

### No syncs found
**Solution:**
- Verify your Census account has active syncs
- Check API key has correct permissions

### Script shows "No product_property syncs found"
**Solution:**
- The script tries to auto-detect based on sync name
- Look at the list of all syncs and identify yours manually
- Note the sync ID and you can monitor it directly

---

## Census API Documentation

Full API docs: https://docs.getcensus.com/basics/api

**Common Endpoints:**
- `GET /syncs` - List all syncs
- `GET /sync_runs` - List sync runs
- `GET /sync_runs/{id}` - Get run details
- `POST /syncs/{id}/trigger` - Manually trigger a sync

---

## Advanced Usage

### Monitor Specific Sync by ID

If you know your sync ID, you can monitor it directly:

```python
from scripts.monitor_census_sync import *

config = load_census_credentials()
sync = {'id': 'YOUR_SYNC_ID', 'label': 'Your Sync Name'}

# Monitor latest run
monitor_latest_run(config, sync)
```

### Get All Runs for Analysis

```python
runs = get_sync_runs(config, sync_id='YOUR_SYNC_ID', limit=50)

# Analyze success rate
total = len(runs)
successful = sum(1 for r in runs if r.get('status') == 'completed')
print(f"Success rate: {successful/total*100:.1f}%")
```

### Trigger Sync Programmatically

```python
import requests

url = f"{config['api_base_url']}/syncs/{sync_id}/trigger"
headers = get_headers(config['api_key'])

response = requests.post(url, headers=headers)
print(f"Sync triggered: {response.json()}")
```

---

## Next Steps

1. ✅ Set up API credentials
2. ✅ Run monitoring script during your sync
3. ✅ Check for errors and validate success
4. ✅ Use validation queries in Databricks to confirm records created

**Validation Query:**
```sql
-- Run in Databricks
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
  AND reverse_etl_id_c IS NOT NULL
```

Should return 1,297 if all records were created successfully!
