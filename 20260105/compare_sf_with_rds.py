#!/usr/bin/env python3
"""
Compare Salesforce Product_Property__c records with RDS source data
Validates that feature flags and timestamps match exactly
"""

import csv
import os
import sys
from databricks import sql
from datetime import datetime
from collections import defaultdict

# Databricks connection details
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"

# Field mappings: Salesforce field -> RDS field
FIELD_MAPPINGS = {
    'Snappt_Property_ID__c': 'rds_property_id',
    'Name': 'property_name',
    'Company_Name__c': 'company_name',
    'Company_ID__c': 'company_id',
    'Short_ID__c': 'short_id',
    'Address__Street__s': 'address',
    'Address__City__s': 'city',
    'Address__StateCode__s': 'state',
    'Address__PostalCode__s': 'postal_code',
    'ID_Verification_Enabled__c': 'idv_enabled',
    'Bank_Linking_Enabled__c': 'bank_linking_enabled',
    'Connected_Payroll_Enabled__c': 'payroll_enabled',
    'Income_Verification_Enabled__c': 'income_insights_enabled',
    'Fraud_Detection_Enabled__c': 'document_fraud_enabled',
    'ID_Verification_Start_Date__c': 'idv_enabled_at',
    'Bank_Linking_Start_Date__c': 'bank_linking_enabled_at',
    'Connected_Payroll_Start_Date__c': 'payroll_enabled_at',
    'Income_Verification_Start_Date__c': 'income_insights_enabled_at',
    'Fraud_Detection_Start_Date__c': 'document_fraud_enabled_at',
}

def parse_sf_csv(csv_file):
    """Parse Salesforce CSV export"""
    records = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    print(f"✓ Loaded {len(records)} records from Salesforce CSV")
    return records

def query_databricks(property_ids):
    """Query RDS data from Databricks"""
    print(f"\n→ Connecting to Databricks...")

    connection = sql.connect(
        server_hostname=DATABRICKS_HOST.replace('https://', ''),
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

    cursor = connection.cursor()

    # Build IN clause
    ids_str = "', '".join(property_ids)

    # Query both views to get all properties - select only the fields we need
    query = f"""
    SELECT
        rds_property_id,
        property_name,
        company_name,
        company_id,
        short_id,
        address,
        city,
        state,
        postal_code,
        idv_enabled,
        bank_linking_enabled,
        payroll_enabled,
        income_insights_enabled,
        document_fraud_enabled,
        idv_enabled_at,
        bank_linking_enabled_at,
        payroll_enabled_at,
        income_insights_enabled_at,
        document_fraud_enabled_at
    FROM (
        SELECT
            rds_property_id,
            property_name,
            company_name,
            company_id,
            short_id,
            address,
            city,
            state,
            postal_code,
            idv_enabled,
            bank_linking_enabled,
            payroll_enabled,
            income_insights_enabled,
            document_fraud_enabled,
            idv_enabled_at,
            bank_linking_enabled_at,
            payroll_enabled_at,
            income_insights_enabled_at,
            document_fraud_enabled_at
        FROM crm.sfdc_dbx.properties_to_create
        UNION ALL
        SELECT
            rds_property_id,
            property_name,
            company_name,
            company_id,
            short_id,
            address,
            city,
            state,
            postal_code,
            idv_enabled,
            bank_linking_enabled,
            payroll_enabled,
            income_insights_enabled,
            document_fraud_enabled,
            idv_enabled_at,
            bank_linking_enabled_at,
            payroll_enabled_at,
            income_insights_enabled_at,
            document_fraud_enabled_at
        FROM crm.sfdc_dbx.properties_to_update
    ) combined
    WHERE rds_property_id IN ('{ids_str}')
    """

    print(f"→ Querying Databricks for {len(property_ids)} properties...")
    cursor.execute(query)

    columns = [desc[0] for desc in cursor.description]
    rds_data = {}

    for row in cursor.fetchall():
        record = dict(zip(columns, row))
        rds_data[record['rds_property_id']] = record

    cursor.close()
    connection.close()

    print(f"✓ Retrieved {len(rds_data)} records from Databricks")
    return rds_data

def normalize_value(value, field_type):
    """Normalize values for comparison"""
    if value is None or value == '' or value == 'null':
        return None

    if field_type == 'boolean':
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).lower() == 'true'

    if field_type == 'date':
        if value is None:
            return None
        # Parse date from various formats
        if isinstance(value, str):
            # SF format: "2025-11-17" or ""
            if value == '':
                return None
            return value.split('T')[0] if 'T' in value else value
        # Databricks format: datetime object
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value).split()[0] if value else None

    return str(value).strip() if value else None

def compare_records(sf_records, rds_data):
    """Compare Salesforce and RDS records field by field"""

    mismatches = []
    matches = 0
    missing_in_rds = []

    print(f"\n{'='*80}")
    print("FIELD-BY-FIELD COMPARISON")
    print(f"{'='*80}\n")

    for sf_record in sf_records:
        property_id = sf_record['Snappt_Property_ID__c']
        property_name = sf_record['Name']

        if property_id not in rds_data:
            missing_in_rds.append(property_id)
            continue

        rds_record = rds_data[property_id]
        record_mismatches = []

        # Compare each field
        for sf_field, rds_field in FIELD_MAPPINGS.items():
            if sf_field == 'Snappt_Property_ID__c':
                continue  # Skip ID field

            sf_value = sf_record.get(sf_field, '')
            rds_value = rds_record.get(rds_field)

            # Determine field type
            field_type = 'string'
            if 'Enabled__c' in sf_field:
                field_type = 'boolean'
            elif 'Date__c' in sf_field:
                field_type = 'date'

            # Normalize values
            sf_normalized = normalize_value(sf_value, field_type)
            rds_normalized = normalize_value(rds_value, field_type)

            # Compare
            if sf_normalized != rds_normalized:
                record_mismatches.append({
                    'field': sf_field,
                    'sf_value': sf_normalized,
                    'rds_value': rds_normalized,
                    'field_type': field_type
                })

        if record_mismatches:
            mismatches.append({
                'property_id': property_id,
                'property_name': property_name,
                'mismatches': record_mismatches
            })
        else:
            matches += 1

    # Print results
    print(f"✓ MATCHES: {matches} properties")
    print(f"✗ MISMATCHES: {len(mismatches)} properties")
    print(f"⚠ MISSING IN RDS: {len(missing_in_rds)} properties\n")

    if mismatches:
        print(f"\n{'='*80}")
        print("DETAILED MISMATCH REPORT")
        print(f"{'='*80}\n")

        for record in mismatches:
            print(f"\n❌ Property: {record['property_name']}")
            print(f"   ID: {record['property_id']}")
            print(f"   Mismatches: {len(record['mismatches'])}")
            print(f"   {'-'*76}")

            for mismatch in record['mismatches']:
                print(f"   Field: {mismatch['field']}")
                print(f"     Salesforce: {mismatch['sf_value']}")
                print(f"     RDS/Source: {mismatch['rds_value']}")
                print()

    if missing_in_rds:
        print(f"\n{'='*80}")
        print("MISSING IN RDS")
        print(f"{'='*80}\n")
        for prop_id in missing_in_rds:
            print(f"  - {prop_id}")

    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total SF Records: {len(sf_records)}")
    print(f"Perfect Matches: {matches} ({matches/len(sf_records)*100:.1f}%)")
    print(f"Records with Mismatches: {len(mismatches)} ({len(mismatches)/len(sf_records)*100:.1f}%)")
    print(f"Missing in RDS: {len(missing_in_rds)}")

    if len(mismatches) == 0 and len(missing_in_rds) == 0:
        print(f"\n✅ VALIDATION PASSED - All records match perfectly!")
        return True
    else:
        print(f"\n⚠️  VALIDATION FAILED - Found {len(mismatches)} mismatches")
        return False

def main():
    csv_file = "bulkQuery_result_750UL00000eNJXbYAO_751UL00000haqNbYAI_752UL00000Zo3TB.csv"

    print(f"\n{'='*80}")
    print("SALESFORCE ↔ RDS DATA VALIDATION")
    print(f"{'='*80}\n")

    # Load Salesforce data
    sf_records = parse_sf_csv(csv_file)

    # Extract property IDs
    property_ids = [r['Snappt_Property_ID__c'] for r in sf_records]

    # Query RDS data
    rds_data = query_databricks(property_ids)

    # Compare
    validation_passed = compare_records(sf_records, rds_data)

    sys.exit(0 if validation_passed else 1)

if __name__ == "__main__":
    main()
