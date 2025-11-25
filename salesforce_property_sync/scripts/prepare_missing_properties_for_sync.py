"""
Prepare missing properties (no sfdc_id) for sync to product_property_c
"""
from databricks import sql
import os
import csv
import json
from datetime import datetime

# Databricks connection settings
DATABRICKS_SERVER_HOSTNAME = "dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")

def get_databricks_connection():
    """Create a Databricks SQL connection"""
    return sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

def get_missing_properties_detail():
    """Get detailed data for properties with no sfdc_id"""
    print("\n" + "="*80)
    print("EXTRACTING PROPERTIES FOR PRODUCT_PROPERTY_C CREATION")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Query to get properties that need to be created
    query = """
    SELECT
        rds_props.id as property_id,
        rds_props.name,
        rds_props.entity_name,
        rds_props.address,
        rds_props.city,
        rds_props.state,
        rds_props.zip,
        rds_props.phone,
        rds_props.email,
        rds_props.website,
        rds_props.logo,
        rds_props.unit as total_units,
        rds_props.status,
        rds_props.company_id,
        rds_props.company_short_id,
        rds_props.short_id,
        rds_props.bank_statement,
        rds_props.paystub,
        rds_props.unit_is_required,
        rds_props.phone_is_required,
        rds_props.identity_verification_enabled,
        rds_props.pmc_name,
        rds_props.inserted_at as created_date,
        rds_props.updated_at as last_modified_date
    FROM rds.pg_rds_public.properties rds_props
    LEFT JOIN hive_metastore.salesforce.product_property_c sf_product
        ON CAST(rds_props.id AS STRING) = sf_product.snappt_property_id_c
    WHERE sf_product.snappt_property_id_c IS NULL
        AND (rds_props.sfdc_id IS NULL OR rds_props.sfdc_id = '')
        AND rds_props.status != 'DELETED'
    ORDER BY rds_props.status DESC, rds_props.updated_at DESC
    """

    print("\nExecuting query to extract properties...")
    cursor.execute(query)
    results = cursor.fetchall()

    # Get column names
    columns = [desc[0] for desc in cursor.description]

    print(f"\nFound {len(results):,} properties to sync to product_property_c")

    cursor.close()
    conn.close()

    return columns, results

def get_company_mapping():
    """Get company mapping from RDS"""
    print("\n" + "="*80)
    print("EXTRACTING COMPANY INFORMATION")
    print("="*80)

    conn = get_databricks_connection()
    cursor = conn.cursor()

    # Get company data for mapping
    query = """
    SELECT
        id as company_id,
        name as company_name,
        short_id as company_short_id
    FROM rds.pg_rds_public.companies
    """

    print("\nExtracting company mapping...")
    cursor.execute(query)
    results = cursor.fetchall()

    company_map = {}
    for row in results:
        company_map[str(row[0])] = {
            'name': row[1],
            'short_id': row[2]
        }

    print(f"Mapped {len(company_map):,} companies")

    cursor.close()
    conn.close()

    return company_map

def analyze_missing_properties(columns, results):
    """Analyze the missing properties"""
    print("\n" + "="*80)
    print("ANALYSIS OF MISSING PROPERTIES")
    print("="*80)

    # Status breakdown
    status_counts = {}
    active_count = 0
    disabled_count = 0

    for row in results:
        status_idx = columns.index('status')
        status = row[status_idx]
        status_counts[status] = status_counts.get(status, 0) + 1

        if status == 'ACTIVE':
            active_count += 1
        elif status == 'DISABLED':
            disabled_count += 1

    print(f"\nStatus Breakdown:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count:,} properties")

    # Company breakdown (top 10)
    company_counts = {}
    company_id_idx = columns.index('company_id')
    for row in results:
        company_id = row[company_id_idx]
        if company_id:
            company_counts[company_id] = company_counts.get(company_id, 0) + 1

    print(f"\nTop 10 Companies with Missing Properties:")
    sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for company_id, count in sorted_companies:
        print(f"  {company_id}: {count:,} properties")

    return active_count, disabled_count

def generate_sync_payload(columns, results, company_map):
    """Generate the sync payload for product_property_c"""
    print("\n" + "="*80)
    print("GENERATING SYNC PAYLOAD")
    print("="*80)

    # Map RDS fields to Salesforce product_property_c fields
    field_mapping = {
        'property_id': 'snappt_property_id_c',
        'name': 'name',
        'entity_name': 'entity_name_c',
        'address': 'address_street_s',
        'city': 'address_city_s',
        'state': 'address_state_code_s',
        'zip': 'address_postal_code_s',
        'phone': 'phone_c',
        'email': 'email_c',
        'website': 'website_c',
        'logo': 'logo_c',
        'total_units': 'unit_c',
        'status': 'status_c',
        'company_id': 'company_id_c',
        'company_short_id': 'company_short_id_c',
        'short_id': 'short_id_c',
        'bank_statement': 'bank_statement_c',
        'paystub': 'paystub_c',
        'unit_is_required': 'unit_is_required_c',
        'phone_is_required': 'phone_is_required_c',
        'identity_verification_enabled': 'identity_verification_enabled_c',
        'pmc_name': None,  # Not mapped to product_property_c
        'created_date': 'created_date',
        'last_modified_date': 'last_modified_date'
    }

    sync_records = []

    for row in results:
        record = {}
        for i, col_name in enumerate(columns):
            sf_field = field_mapping.get(col_name)
            if sf_field:
                value = row[i]

                # Add company name if we have company_id
                if col_name == 'company_id' and value and str(value) in company_map:
                    record['company_name_c'] = company_map[str(value)]['name']

                # Convert value types as needed
                if value is not None:
                    record[sf_field] = value

        # Add required fields for Salesforce
        record['reverse_etl_id_c'] = str(row[columns.index('property_id')])  # Use property_id as reverse ETL identifier
        record['not_orphan_record_c'] = False
        record['trigger_rollups_c'] = True

        sync_records.append(record)

    print(f"Generated {len(sync_records):,} sync records")

    return sync_records

def save_sync_files(columns, results, sync_records, active_count, disabled_count):
    """Save the sync data in multiple formats"""
    print("\n" + "="*80)
    print("SAVING SYNC FILES")
    print("="*80)

    output_dir = "/Users/danerosa/rds_databricks_claude/output/sync_payloads"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Save full detail CSV
    csv_path = f"{output_dir}/missing_properties_full_detail.csv"
    print(f"\n1. Saving full detail CSV: {csv_path}")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in results:
            writer.writerow(row)
    print(f"   ✓ Saved {len(results):,} records")

    # 2. Save sync payload as JSON
    json_path = f"{output_dir}/sync_payload_{timestamp}.json"
    print(f"\n2. Saving sync payload JSON: {json_path}")
    with open(json_path, 'w') as f:
        json.dump(sync_records, f, indent=2, default=str)
    print(f"   ✓ Saved {len(sync_records):,} records")

    # 3. Save sync payload as CSV (Salesforce field names)
    sf_csv_path = f"{output_dir}/sync_payload_{timestamp}.csv"
    print(f"\n3. Saving sync payload CSV: {sf_csv_path}")
    if sync_records:
        with open(sf_csv_path, 'w', newline='') as f:
            # Get all unique field names
            fieldnames = sorted(set().union(*[record.keys() for record in sync_records]))
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in sync_records:
                writer.writerow(record)
        print(f"   ✓ Saved {len(sync_records):,} records")

    # 4. Save ACTIVE properties only
    active_records = [r for r, row in zip(sync_records, results)
                      if row[columns.index('status')] == 'ACTIVE']
    active_csv_path = f"{output_dir}/sync_payload_ACTIVE_only_{timestamp}.csv"
    print(f"\n4. Saving ACTIVE properties only: {active_csv_path}")
    if active_records:
        with open(active_csv_path, 'w', newline='') as f:
            fieldnames = sorted(set().union(*[record.keys() for record in active_records]))
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in active_records:
                writer.writerow(record)
        print(f"   ✓ Saved {len(active_records):,} ACTIVE records")

    # 5. Create summary report
    summary_path = f"{output_dir}/sync_summary_{timestamp}.md"
    print(f"\n5. Saving summary report: {summary_path}")

    summary = f"""# Property Sync Summary

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

Properties to be synced to Salesforce `product_property_c` table.

## Statistics

- **Total Properties:** {len(results):,}
- **ACTIVE Properties:** {active_count:,}
- **DISABLED Properties:** {disabled_count:,}

## Files Generated

1. **Full Detail CSV:** `missing_properties_full_detail.csv`
   - All properties with full RDS schema
   - {len(results):,} records

2. **Sync Payload JSON:** `sync_payload_{timestamp}.json`
   - Ready for programmatic sync
   - Salesforce field names mapped
   - {len(sync_records):,} records

3. **Sync Payload CSV:** `sync_payload_{timestamp}.csv`
   - Ready for CSV import or Census/Reverse ETL
   - Salesforce field names mapped
   - {len(sync_records):,} records

4. **ACTIVE Only CSV:** `sync_payload_ACTIVE_only_{timestamp}.csv`
   - Only ACTIVE status properties
   - Recommended for initial sync
   - {len(active_records):,} records

## Field Mapping

| RDS Field | Salesforce Field |
|-----------|------------------|
| id | snappt_property_id_c |
| name | name |
| entity_name | entity_name_c |
| address | address_street_s |
| city | address_city_s |
| state | address_state_code_s |
| zip | address_postal_code_s |
| phone | phone_c |
| email | email_c |
| website | website_c |
| company_id | company_id_c |
| status | status_c |
| short_id | short_id_c |

## Sync Options

### Option 1: Census/Reverse ETL (Recommended)
- Upload `sync_payload_ACTIVE_only_{timestamp}.csv` to Census
- Map to Salesforce product_property_c object
- Configure sync to run incrementally

### Option 2: Salesforce Bulk API
- Use Salesforce Bulk API 2.0
- Upload CSV via Salesforce Data Loader or API
- Monitor for errors and validate

### Option 3: Custom Script
- Use the JSON payload with Salesforce REST API
- Batch insert in groups of 200 records
- Handle errors and retries

## Next Steps

1. Review the ACTIVE properties CSV
2. Validate data quality (addresses, phone numbers, etc.)
3. Choose sync method (Census recommended)
4. Test with a small batch (10-20 properties)
5. Monitor Salesforce workflows for property_c creation
6. Validate that properties appear in property_c table

## Notes

- Properties with DISABLED status can be synced later
- All properties will trigger Salesforce workflows to create records in property_c
- Monitor for duplicate detection rules in Salesforce
"""

    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"   ✓ Saved summary report")

    return {
        'full_csv': csv_path,
        'json': json_path,
        'sync_csv': sf_csv_path,
        'active_csv': active_csv_path,
        'summary': summary_path
    }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PREPARE MISSING PROPERTIES FOR SYNC")
    print("="*80)

    try:
        # Step 1: Extract missing properties
        columns, results = get_missing_properties_detail()

        # Step 2: Get company mapping
        company_map = get_company_mapping()

        # Step 3: Analyze the data
        active_count, disabled_count = analyze_missing_properties(columns, results)

        # Step 4: Generate sync payload
        sync_records = generate_sync_payload(columns, results, company_map)

        # Step 5: Save files
        files = save_sync_files(columns, results, sync_records, active_count, disabled_count)

        print("\n" + "="*80)
        print("PREPARATION COMPLETE")
        print("="*80)

        print("\n📁 Files generated:")
        for file_type, path in files.items():
            print(f"  - {file_type}: {path}")

        print("\n✅ Ready to sync to Salesforce product_property_c")
        print("\n📖 Review the summary file for next steps:")
        print(f"   {files['summary']}")

    except Exception as e:
        print(f"\nError during preparation: {e}")
        import traceback
        traceback.print_exc()
