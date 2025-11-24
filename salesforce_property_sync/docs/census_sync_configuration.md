# Census Sync Configuration Guide
## RDS Properties → Salesforce product_property__c

**Objective:** Sync 1,297 ACTIVE properties from RDS to Salesforce staging table

---

## Census Sync Configuration

### 1. Sync Key (Unique Identifier)

**Source Field (RDS):**
```
id
```
- This is the property UUID in `rds.pg_rds_public.properties`

**Destination Field (Salesforce):**
```
snappt_property_id_c
```
- This is the custom field in Salesforce that stores the RDS property ID

### Why This Sync Key?

The `snappt_property_id_c` field in Salesforce is the **foreign key** that links back to the RDS `properties.id`. This ensures:
- ✓ Each property is uniquely identified
- ✓ No duplicates are created
- ✓ Future updates to the same property will match correctly
- ✓ The link between RDS and Salesforce is maintained

---

## Census Sync Settings

### Sync Mode
**Recommended:** `Update or Create (Upsert)`

- If `snappt_property_id_c` doesn't exist → **INSERT** new record
- If `snappt_property_id_c` exists → **UPDATE** existing record

Since these are all new properties, Census will perform INSERT operations.

### Alternative: `Create Only (Insert)`
- Only inserts new records
- Fails if `snappt_property_id_c` already exists
- More conservative, prevents accidental updates

---

## Field Mapping

| RDS Source Field | Salesforce Destination Field | Notes |
|------------------|------------------------------|-------|
| `id` | `snappt_property_id_c` | **SYNC KEY** - Must be mapped |
| `name` | `name` | Property name |
| `entity_name` | `entity_name_c` | Legal entity name |
| `address` | `address_street_s` | Street address |
| `city` | `address_city_s` | City |
| `state` | `address_state_code_s` | State code (e.g., "CA") |
| `zip` | `address_postal_code_s` | ZIP/postal code |
| `phone` | `phone_c` | Phone number |
| `email` | `email_c` | Email address |
| `website` | `website_c` | Website URL |
| `logo` | `logo_c` | Logo URL |
| `unit` | `unit_c` | Number of units |
| `status` | `status_c` | ACTIVE/DISABLED |
| `company_id` | `company_id_c` | Company UUID |
| `company_short_id` | `company_short_id_c` | Company short ID |
| `short_id` | `short_id_c` | Property short ID |
| `bank_statement` | `bank_statement_c` | Document setting |
| `paystub` | `paystub_c` | Document setting |
| `unit_is_required` | `unit_is_required_c` | Boolean |
| `phone_is_required` | `phone_is_required_c` | Boolean |
| `identity_verification_enabled` | `identity_verification_enabled_c` | Boolean |

### Required Fields (Set Default Values)

These fields should be set with default values in Census:

| Field | Default Value | Type |
|-------|---------------|------|
| `not_orphan_record_c` | `false` | Boolean |
| `trigger_rollups_c` | `true` | Boolean |
| `reverse_etl_id_c` | Same as `id` | String |

---

## Step-by-Step Census Setup

### Step 1: Create Model in Census

**Source:** Databricks SQL Warehouse

**SQL Query:**
```sql
SELECT
    CAST(id AS STRING) as id,  -- Convert UUID to string for Salesforce
    name,
    entity_name,
    address,
    city,
    state,
    zip,
    phone,
    email,
    website,
    logo,
    unit,
    status,
    CAST(company_id AS STRING) as company_id,
    company_short_id,
    short_id,
    bank_statement,
    paystub,
    unit_is_required,
    phone_is_required,
    identity_verification_enabled,
    inserted_at,
    updated_at
FROM rds.pg_rds_public.properties
WHERE status = 'ACTIVE'
    AND (sfdc_id IS NULL OR sfdc_id = '')
    AND id NOT IN (
        SELECT CAST(snappt_property_id_c AS STRING)
        FROM hive_metastore.salesforce.product_property_c
        WHERE snappt_property_id_c IS NOT NULL
    )
```

**Model Name:** `rds_properties_missing_from_salesforce`

---

### Step 2: Create Sync in Census

1. **Choose Model:** `rds_properties_missing_from_salesforce`

2. **Choose Destination:** Salesforce (your connected instance)

3. **Choose Object:** `Product_Property__c`

4. **Sync Key:**
   - Source Field: `id`
   - Destination Field: `Snappt_Property_ID__c` (API name: `snappt_property_id_c`)

5. **Sync Behavior:** `Update or Create (Upsert)`

6. **Map Fields:** (See field mapping table above)

7. **Set Constants:**
   - `not_orphan_record_c` → `false`
   - `trigger_rollups_c` → `true`
   - `reverse_etl_id_c` → `{{ row.id }}`

---

### Step 3: Configure Sync Schedule

**Recommended Schedule:**

**Initial Sync:**
- **Manual trigger** to sync all 1,297 properties
- Monitor for errors
- Validate in Salesforce

**Ongoing Sync:**
- **Incremental sync** every 1-6 hours
- Add filter: `WHERE updated_at > {last_sync_time}`
- Catches new properties as they're created in RDS

---

## Important Considerations

### 1. Salesforce Workflows

After properties are inserted into `product_property_c`, Salesforce workflows will:
- Process the records
- Create corresponding records in `property_c` (final production table)
- Populate additional fields
- Set `sf_property_id_c` field

**Monitor:** Check that workflows are executing and creating `property_c` records.

### 2. Error Handling

Common errors to watch for:
- **Required field missing:** Ensure all required Salesforce fields are mapped
- **Validation rules:** Check Salesforce validation rules on `Product_Property__c`
- **Duplicate detection:** Salesforce may have duplicate rules based on name/address
- **Data format:** Ensure phone numbers, emails, URLs are properly formatted

### 3. Batch Size

- Start with **small batch** (10-20 records) to test
- If successful, increase batch size
- Census typically handles 200-500 records per batch

### 4. Company ID Mapping

The `company_id_c` field references a company UUID. Ensure:
- The company exists in Salesforce
- The `company_id_c` field is properly configured to accept UUIDs
- Consider mapping `company_name_c` as well for easier identification

---

## Validation After Sync

### 1. Check Census Sync Logs
- Verify all 1,297 records synced successfully
- Review any errors or warnings

### 2. Verify in Salesforce
```sql
-- Run in Salesforce SOQL
SELECT COUNT()
FROM Product_Property__c
WHERE Snappt_Property_ID__c != null
AND CreatedDate = TODAY
```

### 3. Check property_c Creation
```sql
-- Run in Databricks
SELECT COUNT(*)
FROM hive_metastore.salesforce.property_c
WHERE snappt_property_id_c IN (
    SELECT CAST(snappt_property_id_c AS STRING)
    FROM hive_metastore.salesforce.product_property_c
    WHERE DATE(created_date) = CURRENT_DATE()
)
```

### 4. Verify Linkage
```sql
-- Run in Databricks
-- Check that new product_property_c records are linked to property_c
SELECT
    pp.snappt_property_id_c,
    pp.name as product_property_name,
    pp.sf_property_id_c,
    p.id as property_c_id,
    p.name as property_c_name
FROM hive_metastore.salesforce.product_property_c pp
LEFT JOIN hive_metastore.salesforce.property_c p
    ON pp.sf_property_id_c = p.id
WHERE DATE(pp.created_date) = CURRENT_DATE()
```

---

## Troubleshooting

### Issue: "Sync key field not found"
**Solution:** Ensure `Snappt_Property_ID__c` field exists in Salesforce `Product_Property__c` object

### Issue: "Required fields missing"
**Solution:** Check Salesforce object required fields and add to Census mapping

### Issue: "No records synced"
**Solution:**
1. Verify the source query returns records
2. Check Census filters
3. Verify Salesforce connection is active

### Issue: "Duplicate records created"
**Solution:**
1. Verify sync key is set correctly
2. Check if Salesforce has duplicate detection rules
3. Ensure `snappt_property_id_c` is unique in Salesforce

---

## Summary

**Sync Key Configuration:**
```
Source: id (RDS property UUID)
   ↓
Destination: snappt_property_id_c (Salesforce custom field)
```

This ensures proper linkage between RDS and Salesforce, preventing duplicates and maintaining data integrity.

---

## Next Steps

1. ✅ Set up Census model with the provided SQL query
2. ✅ Configure sync with `id` → `snappt_property_id_c` as sync key
3. ✅ Map all required fields
4. ✅ Test with 10-20 records
5. ✅ Full sync of 1,297 ACTIVE properties
6. ✅ Monitor Salesforce workflows
7. ✅ Validate records appear in `property_c`

---

**Questions?** Review the sync summary at:
`/Users/danerosa/rds_databricks_claude/output/sync_payloads/sync_summary_20251121_104454.md`
