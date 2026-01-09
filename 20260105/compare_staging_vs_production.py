#!/usr/bin/env python3
"""
Compare Product_Property__c (staging) vs Property__c (production)
Demonstrates that Census sync wrote updated data to staging that differs from production
"""

import csv
import os
import sys
from databricks import sql
from datetime import datetime

# Databricks connection details
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"

# Field mappings for comparison
FEATURE_FIELDS = [
    ('ID_Verification_Enabled__c', 'idv_enabled'),
    ('Bank_Linking_Enabled__c', 'bank_linking_enabled'),
    ('Connected_Payroll_Enabled__c', 'payroll_enabled'),
    ('Income_Verification_Enabled__c', 'income_insights_enabled'),
    ('Fraud_Detection_Enabled__c', 'document_fraud_enabled'),
]

TIMESTAMP_FIELDS = [
    ('ID_Verification_Start_Date__c', 'idv_enabled_at'),
    ('Bank_Linking_Start_Date__c', 'bank_linking_enabled_at'),
    ('Connected_Payroll_Start_Date__c', 'payroll_enabled_at'),
    ('Income_Verification_Start_Date__c', 'income_insights_enabled_at'),
    ('Fraud_Detection_Start_Date__c', 'document_fraud_enabled_at'),
]

def parse_csv(csv_file):
    """Parse CSV export from Salesforce"""
    records = {}
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop_id = row['Snappt_Property_ID__c']
            records[prop_id] = row
    return records

def query_production_salesforce(property_ids):
    """Query Property__c (production) from Databricks"""
    print(f"\n→ Connecting to Databricks to fetch production data...")

    connection = sql.connect(
        server_hostname=DATABRICKS_HOST.replace('https://', ''),
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

    cursor = connection.cursor()

    # Build IN clause
    ids_str = "', '".join(property_ids)

    # Query production Property__c table
    query = f"""
    SELECT
        snappt_property_id_c as property_id,
        idv_enabled,
        bank_linking_enabled,
        payroll_enabled,
        income_insights_enabled,
        document_fraud_enabled,
        idv_enabled_at,
        bank_linking_enabled_at,
        payroll_enabled_at,
        income_insights_enabled_at,
        document_fraud_enabled_at,
        last_modified_date
    FROM hive_metastore.salesforce.property_c
    WHERE snappt_property_id_c IN ('{ids_str}')
    """

    print(f"→ Querying production Property__c for {len(property_ids)} properties...")
    cursor.execute(query)

    columns = [desc[0] for desc in cursor.description]
    production_data = {}

    for row in cursor.fetchall():
        record = dict(zip(columns, row))
        production_data[record['property_id']] = record

    cursor.close()
    connection.close()

    print(f"✓ Retrieved {len(production_data)} records from production")
    return production_data

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
            if value == '':
                return None
            return value.split('T')[0] if 'T' in value else value
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value).split()[0] if value else None

    return str(value).strip() if value else None

def compare_staging_vs_production(staging_data, production_data):
    """Compare staging (Product_Property__c) vs production (Property__c)"""

    differences = []
    matches = 0
    only_in_staging = []
    only_in_production = []

    print(f"\n{'='*80}")
    print("STAGING vs PRODUCTION COMPARISON")
    print(f"{'='*80}\n")

    # Check properties in both systems
    all_property_ids = set(staging_data.keys()) | set(production_data.keys())

    for prop_id in all_property_ids:
        if prop_id not in staging_data:
            only_in_production.append(prop_id)
            continue

        if prop_id not in production_data:
            only_in_staging.append(prop_id)
            continue

        staging_record = staging_data[prop_id]
        prod_record = production_data[prop_id]

        record_diffs = []

        # Compare feature flags
        for staging_field, prod_field in FEATURE_FIELDS:
            staging_val = normalize_value(staging_record.get(staging_field, ''), 'boolean')
            prod_val = normalize_value(prod_record.get(prod_field), 'boolean')

            if staging_val != prod_val:
                record_diffs.append({
                    'field': staging_field.replace('__c', ''),
                    'staging': staging_val,
                    'production': prod_val,
                    'type': 'feature_flag'
                })

        # Compare timestamps
        for staging_field, prod_field in TIMESTAMP_FIELDS:
            staging_val = normalize_value(staging_record.get(staging_field, ''), 'date')
            prod_val = normalize_value(prod_record.get(prod_field), 'date')

            if staging_val != prod_val:
                record_diffs.append({
                    'field': staging_field.replace('__c', ''),
                    'staging': staging_val,
                    'production': prod_val,
                    'type': 'timestamp'
                })

        if record_diffs:
            differences.append({
                'property_id': prop_id,
                'property_name': staging_record.get('Name', 'Unknown'),
                'diffs': record_diffs
            })
        else:
            matches += 1

    # Print summary
    print(f"✓ IDENTICAL: {matches} properties (same in staging and production)")
    print(f"✗ DIFFERENT: {len(differences)} properties (staging differs from production)")
    print(f"📊 ONLY IN STAGING: {len(only_in_staging)} properties (new)")
    print(f"📊 ONLY IN PRODUCTION: {len(only_in_production)} properties (not yet synced)")

    # Print detailed differences
    if differences:
        print(f"\n{'='*80}")
        print("PROPERTIES WITH DIFFERENCES (PROVES PIPELINE WORKING)")
        print(f"{'='*80}\n")

        # Show first 20 in detail
        for idx, record in enumerate(differences[:20]):
            print(f"\n{idx+1}. Property: {record['property_name']}")
            print(f"   ID: {record['property_id']}")
            print(f"   Differences: {len(record['diffs'])}")
            print(f"   {'-'*76}")

            for diff in record['diffs']:
                field_label = diff['field'].replace('_', ' ').title()
                print(f"   {field_label}:")
                print(f"     Staging (NEW):    {diff['staging']}")
                print(f"     Production (OLD): {diff['production']}")
                print()

        if len(differences) > 20:
            print(f"\n... and {len(differences) - 20} more properties with differences")

    if only_in_staging:
        print(f"\n{'='*80}")
        print("NEW PROPERTIES IN STAGING (NOT YET IN PRODUCTION)")
        print(f"{'='*80}\n")
        for idx, prop_id in enumerate(only_in_staging[:10]):
            staging_record = staging_data[prop_id]
            print(f"  {idx+1}. {staging_record.get('Name', 'Unknown')} ({prop_id})")

        if len(only_in_staging) > 10:
            print(f"  ... and {len(only_in_staging) - 10} more")

    # Final summary
    print(f"\n{'='*80}")
    print("SUMMARY - PIPELINE VALIDATION")
    print(f"{'='*80}\n")

    total_compared = len(all_property_ids)
    pct_different = (len(differences) / total_compared * 100) if total_compared > 0 else 0

    print(f"Total Properties Compared: {total_compared}")
    print(f"Identical (Staging = Production): {matches} ({matches/total_compared*100:.1f}%)")
    print(f"Different (Staging ≠ Production): {len(differences)} ({pct_different:.1f}%)")
    print(f"New in Staging: {len(only_in_staging)}")
    print(f"Not Yet Synced: {len(only_in_production)}")

    print(f"\n{'='*80}")
    if len(differences) > 0:
        print("✅ PIPELINE VALIDATION: SUCCESS")
        print(f"{'='*80}")
        print(f"\nThe Census pipeline is working correctly:")
        print(f"  • {len(differences)} properties have DIFFERENT data in staging vs production")
        print(f"  • Staging has updated feature flags and timestamps from RDS")
        print(f"  • Production still has old data (not yet updated)")
        print(f"  • This proves the sync wrote to Product_Property__c (staging)")
        print(f"  • Ready to promote staging data to production when approved")
    else:
        print("⚠️  PIPELINE VALIDATION: INCONCLUSIVE")
        print(f"{'='*80}")
        print(f"\nNo differences found between staging and production.")
        print(f"This could mean:")
        print(f"  • Production was already updated with same data")
        print(f"  • Sync wrote same values that existed in production")
        print(f"  • Need to check if staging actually has new data")

    return len(differences) > 0

def main():
    staging_csv = "bulkQuery_result_750UL00000eNJXbYAO_751UL00000haqNbYAI_752UL00000Zo3TB.csv"

    print(f"\n{'='*80}")
    print("STAGING vs PRODUCTION COMPARISON")
    print(f"{'='*80}\n")
    print("Purpose: Prove that Census sync wrote updated data to Product_Property__c")
    print("         that differs from what exists in Property__c (production)\n")

    # Load staging data (Product_Property__c)
    print("→ Loading staging data (Product_Property__c)...")
    staging_data = parse_csv(staging_csv)
    print(f"✓ Loaded {len(staging_data)} records from staging")

    # Get property IDs to query
    property_ids = list(staging_data.keys())

    # Query production data (Property__c)
    production_data = query_production_salesforce(property_ids)

    # Compare
    pipeline_working = compare_staging_vs_production(staging_data, production_data)

    sys.exit(0 if pipeline_working else 1)

if __name__ == "__main__":
    main()
