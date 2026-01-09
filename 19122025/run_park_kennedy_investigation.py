#!/usr/bin/env python3
"""
Park Kennedy Feature Sync Investigation
Executes diagnostic queries to identify why features aren't syncing
"""

import subprocess
import json
import sys

WAREHOUSE_ID = "9b7a58ad33c27fbc"

def run_query(query, description):
    """Execute a SQL query in Databricks and return results"""
    print(f"\n{'='*80}")
    print(f"QUERY: {description}")
    print(f"{'='*80}\n")

    # Write query to temp file
    with open('/tmp/query.sql', 'w') as f:
        f.write(query)

    # Execute using databricks CLI
    cmd = [
        'databricks', 'sql', 'execute',
        '--warehouse-id', WAREHOUSE_ID,
        '--file', '/tmp/query.sql',
        '-o', 'json'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data
            except json.JSONDecodeError:
                print(f"OUTPUT:\n{result.stdout}\n")
                return result.stdout
        else:
            print(f"ERROR: {result.stderr}\n")
            return None
    except subprocess.TimeoutExpired:
        print("ERROR: Query timed out\n")
        return None
    except Exception as e:
        print(f"ERROR: {str(e)}\n")
        return None

# Query 1: Find Park Kennedy in RDS
query1 = """
SELECT
    id as property_id,
    name,
    short_id,
    status,
    sfdc_id,
    identity_verification_enabled,
    inserted_at,
    updated_at
FROM rds.pg_rds_public.properties
WHERE name LIKE '%Park Kennedy%'
ORDER BY id
"""

# Query 2: Check feature events
query2 = """
SELECT
    pfe.property_id,
    p.name,
    pfe.feature_code,
    pfe.event_type,
    pfe.inserted_at,
    pfe._fivetran_deleted,
    ROW_NUMBER() OVER (PARTITION BY pfe.property_id, pfe.feature_code ORDER BY pfe.inserted_at DESC) as event_rank
FROM rds.pg_rds_public.property_feature_events pfe
JOIN rds.pg_rds_public.properties p ON p.id = pfe.property_id
WHERE p.name LIKE '%Park Kennedy%'
ORDER BY pfe.property_id, pfe.feature_code, pfe.inserted_at DESC
LIMIT 50
"""

# Query 3: Check product_property_w_features
query3 = """
SELECT
    property_id,
    sfdc_id,
    product_property_id,
    fraud_enabled,
    fraud_enabled_at,
    iv_enabled,
    iv_enabled_at,
    idv_enabled,
    idv_enabled_at,
    idv_only_enabled,
    idv_only_enabled_at,
    payroll_linking_enabled,
    payroll_linking_enabled_at,
    bank_linking_enabled,
    bank_linking_enabled_at,
    vor_enabled,
    vor_enabled_at
FROM crm.sfdc_dbx.product_property_w_features
WHERE property_id IN (
    SELECT CAST(id AS STRING) FROM rds.pg_rds_public.properties WHERE name LIKE '%Park Kennedy%'
)
"""

# Query 4: Check Salesforce records
query4 = """
SELECT
    id as salesforce_id,
    name,
    snappt_property_id_c,
    sf_property_id_c,
    reverse_etl_id_c,
    fraud_detection_enabled_c,
    fraud_detection_start_date_c,
    income_verification_enabled_c,
    income_verification_start_date_c,
    id_verification_enabled_c,
    id_verification_start_date_c,
    idv_only_enabled_c,
    idv_only_start_date_c,
    connected_payroll_enabled_c,
    connected_payroll_start_date_c,
    bank_linking_enabled_c,
    bank_linking_start_date_c,
    verification_of_rent_enabled_c,
    vor_start_date_c,
    is_deleted,
    created_date,
    last_modified_date
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
ORDER BY created_date DESC
"""

# Query 5: Check sync table
query5 = """
SELECT
    snappt_property_id_c,
    reverse_etl_id_c,
    name,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    connected_payroll_enabled_c,
    verification_of_rent_enabled_c,
    idv_only_enabled_c
FROM crm.sfdc_dbx.product_property_feature_sync
WHERE name LIKE '%Park Kennedy%'
"""

# Query 6: Check ID mapping
query6 = """
SELECT
    p.id as rds_property_id,
    p.name as rds_name,
    p.sfdc_id as rds_sfdc_id,
    sf.id as sf_record_id,
    sf.snappt_property_id_c,
    sf.sf_property_id_c,
    CASE
        WHEN CAST(p.id AS STRING) = sf.snappt_property_id_c THEN 'MATCH'
        ELSE 'MISMATCH'
    END as id_mapping_status
FROM rds.pg_rds_public.properties p
FULL OUTER JOIN crm.salesforce.product_property sf ON sf.name LIKE CONCAT('%', p.name, '%')
WHERE p.name LIKE '%Park Kennedy%' OR sf.name LIKE '%Park Kennedy%'
ORDER BY p.id
"""

# Query 7: Check for duplicates
query7 = """
SELECT
    snappt_property_id_c,
    COUNT(*) as record_count,
    COLLECT_LIST(id) as salesforce_ids,
    COLLECT_LIST(CAST(is_deleted AS STRING)) as deleted_status
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
GROUP BY snappt_property_id_c
"""

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PARK KENNEDY FEATURE SYNC INVESTIGATION")
    print("="*80)

    results = {}

    results['rds_properties'] = run_query(query1, "Step 1: Park Kennedy in RDS Properties")
    results['feature_events'] = run_query(query2, "Step 2: Feature Events for Park Kennedy")
    results['aggregated_features'] = run_query(query3, "Step 3: Park Kennedy in product_property_w_features")
    results['salesforce_records'] = run_query(query4, "Step 4: Park Kennedy in Salesforce")
    results['sync_table'] = run_query(query5, "Step 5: Park Kennedy in Sync Table")
    results['id_mapping'] = run_query(query6, "Step 6: ID Mapping Check")
    results['duplicates'] = run_query(query7, "Step 7: Duplicate Check")

    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)
    print("\nCheck the output above to identify the root cause.")
    print("\nKey things to look for:")
    print("  1. Are there 2 records in Salesforce? (Query 7)")
    print("  2. Do the IDs match correctly? (Query 6)")
    print("  3. Is Park Kennedy in product_property_w_features? (Query 3)")
    print("  4. Is Park Kennedy in the sync table? (Query 5)")
    print("  5. Are features enabled in RDS? (Query 2)")
