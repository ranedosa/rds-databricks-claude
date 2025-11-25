# Census Sync Quick Fix
## Using Reverse ETL ID as Sync Key

**Issue:** Only "Reverse ETL ID" appears in Census sync key dropdown

**Solution:** Use `Reverse_ETL_ID__c` as the sync key ✅

---

## Why This Happens

Census only shows fields marked as **External ID** in Salesforce for the sync key dropdown.

In your Salesforce `Product_Property__c` object:
- ✅ `Reverse_ETL_ID__c` is marked as External ID
- ❌ `Snappt_Property_ID__c` is NOT marked as External ID

---

## Correct Census Configuration

### Sync Key

**Source Field (CSV):**
```
reverse_etl_id_c
```

**Destination Field (Salesforce):**
```
Reverse ETL ID (reverse_etl_id_c)
```

**Sync Behavior:** `Update or Create (Upsert)`

---

## Field Mapping

Map the CSV columns to Salesforce fields:

| CSV Column | Salesforce Field |
|------------|------------------|
| `reverse_etl_id_c` | **Reverse ETL ID** (sync key) |
| `snappt_property_id_c` | `Snappt Property ID` |
| `name` | `Name` |
| `entity_name_c` | `Entity Name` |
| `address_street_s` | `Address Street` |
| `address_city_s` | `Address City` |
| `address_state_code_s` | `Address State Code` |
| `address_postal_code_s` | `Address Postal Code` |
| `phone_c` | `Phone` |
| `email_c` | `Email` |
| `website_c` | `Website` |
| `logo_c` | `Logo` |
| `unit_c` | `Unit` |
| `status_c` | `Status` |
| `company_id_c` | `Company ID` |
| `company_name_c` | `Company Name` |
| `company_short_id_c` | `Company Short ID` |
| `short_id_c` | `Short ID` |
| `bank_statement_c` | `Bank Statement` |
| `paystub_c` | `Paystub` |
| `unit_is_required_c` | `Unit Is Required` |
| `phone_is_required_c` | `Phone Is Required` |
| `identity_verification_enabled_c` | `Identity Verification Enabled` |
| `not_orphan_record_c` | `Not Orphan Record` |
| `trigger_rollups_c` | `Trigger Rollups` |

---

## How It Works

The sync payload I generated includes **both** fields with the same value:

```json
{
  "reverse_etl_id_c": "839861e0-fe60-48e4-b16e-f7935c9a6889",
  "snappt_property_id_c": "839861e0-fe60-48e4-b16e-f7935c9a6889"
}
```

- **`reverse_etl_id_c`** → Used as sync key (External ID for upsert)
- **`snappt_property_id_c`** → Mapped as regular field to maintain RDS linkage

Both fields store the same property UUID, so your RDS-Salesforce link is preserved!

---

## Why Have Two Fields?

**`reverse_etl_id_c`:**
- External ID field for Census/ETL operations
- Used for upsert matching
- Standard field across your org for Reverse ETL syncs

**`snappt_property_id_c`:**
- Business logic field
- Used by Salesforce workflows and reports
- Links to RDS database

---

## Step-by-Step Census Setup

### 1. Upload CSV
✅ You already did this with `sync_payload_ACTIVE_only_20251121_104454.csv`

### 2. Configure Sync
1. **Destination:** Salesforce Product_Property__c
2. **Sync Key:** Select "Reverse ETL ID" from dropdown
3. **Sync Behavior:** Update or Create (Upsert)

### 3. Map Fields
Map all the fields from the CSV to Salesforce fields (see table above).

**Important:** Make sure to map `snappt_property_id_c` from your CSV to the Salesforce `Snappt_Property_ID__c` field. This is NOT the sync key, but it's critical for maintaining the RDS link.

### 4. Run Test Sync
Start with a small batch (10-20 records) to verify:
- Records are created successfully
- Both `reverse_etl_id_c` and `snappt_property_id_c` are populated
- Salesforce workflows trigger and create records in `property_c`

---

## Validation Queries

After sync, run these queries to validate:

### 1. Check Records Were Created
```sql
-- Databricks
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c
WHERE reverse_etl_id_c IS NOT NULL
  AND DATE(created_date) = CURRENT_DATE()
```

### 2. Verify Both IDs Are Populated
```sql
-- Databricks
SELECT
    reverse_etl_id_c,
    snappt_property_id_c,
    name,
    status_c
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
LIMIT 10
```

### 3. Check RDS Linkage
```sql
-- Databricks
SELECT
    rds.id as rds_property_id,
    rds.name as rds_name,
    sf.snappt_property_id_c as sf_property_id,
    sf.name as sf_name
FROM rds.pg_rds_public.properties rds
INNER JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE DATE(sf.created_date) = CURRENT_DATE()
LIMIT 10
```

Should return matching records if linkage is working correctly.

---

## Alternative: Make snappt_property_id_c an External ID

If you want to use `snappt_property_id_c` directly as the sync key in the future, you can:

1. Go to Salesforce Setup
2. Navigate to Object Manager → Product Property
3. Find the `Snappt_Property_ID__c` field
4. Edit field properties
5. Check "External ID" checkbox
6. Save

Then it will appear in the Census sync key dropdown.

**However**, using `reverse_etl_id_c` is the **standard pattern** and works perfectly fine!

---

## Summary

✅ **Use:** `Reverse ETL ID` as sync key in Census

✅ **Map:** `snappt_property_id_c` column to `Snappt_Property_ID__c` field

✅ **Result:** Both fields populated with same UUID, linkage maintained

---

## Need Help?

If you encounter errors during sync:
1. Check Census sync logs for specific error messages
2. Verify field mappings match Salesforce API names
3. Check Salesforce validation rules on Product_Property__c object
4. Ensure all required fields are mapped

Let me know if you see any errors and I can help troubleshoot!
