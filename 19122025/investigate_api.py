#!/usr/bin/env python3
"""
Park Kennedy Investigation using Databricks REST API
"""

import requests
import json
import time
import os
from datetime import datetime

# Databricks config
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
WAREHOUSE_ID = "9b7a58ad33c27fbc"

# Get token from config
config_path = os.path.expanduser("~/.databrickscfg")
token = None
with open(config_path, 'r') as f:
    lines = f.readlines()
    in_pat_section = False
    for line in lines:
        line = line.strip()
        if line == '[pat]':
            in_pat_section = True
        elif line.startswith('['):
            in_pat_section = False
        elif in_pat_section and line.startswith('token'):
            token = line.split('=')[1].strip()
            break

if not token:
    print("ERROR: Could not find token")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def execute_query(query, description):
    """Execute a SQL query using Databricks SQL Execution API"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")

    # Execute query
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements/"
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": "30s"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            print(f"ERROR: API returned {response.status_code}")
            print(f"Response: {response.text}\n")
            return None

        result = response.json()

        # Check if query completed
        if result.get('status', {}).get('state') == 'SUCCEEDED':
            # Display results
            if 'result' in result and 'data_array' in result['result']:
                columns = [col['name'] for col in result['result'].get('manifest', {}).get('schema', {}).get('columns', [])]
                rows = result['result']['data_array']

                if not rows:
                    print("No results found.\n")
                    return None

                # Print header
                print(" | ".join(columns))
                print("-" * 80)

                # Print rows
                for row in rows:
                    print(" | ".join([str(val) if val is not None else 'NULL' for val in row]))

                print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})\n")
                return {'columns': columns, 'rows': rows}
            else:
                print("Query succeeded but no data returned\n")
                return None
        else:
            print(f"Query state: {result.get('status', {}).get('state')}")
            if 'status' in result and 'error' in result['status']:
                print(f"Error: {result['status']['error']}\n")
            return None

    except Exception as e:
        print(f"ERROR: {str(e)}\n")
        return None

# Main investigation queries
print("\n" + "="*80)
print("PARK KENNEDY FEATURE SYNC - INVESTIGATION")
print("="*80)

# Query 1: RDS Properties
query1 = """
SELECT
    id as property_id,
    name,
    short_id,
    status,
    sfdc_id,
    identity_verification_enabled
FROM rds.pg_rds_public.properties
WHERE name LIKE '%Park Kennedy%'
ORDER BY id
"""
result1 = execute_query(query1, "STEP 1: Park Kennedy in RDS Properties")

# Query 2: Latest Feature Events
query2 = """
WITH ranked_events AS (
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
)
SELECT
    property_id,
    feature_code,
    event_type,
    inserted_at,
    _fivetran_deleted
FROM ranked_events
WHERE event_rank = 1
ORDER BY feature_code
"""
result2 = execute_query(query2, "STEP 2: Latest Feature Events")

# Query 3: Aggregated Features
query3 = """
SELECT
    property_id,
    sfdc_id,
    product_property_id,
    fraud_enabled,
    iv_enabled,
    idv_enabled,
    idv_only_enabled,
    payroll_linking_enabled,
    bank_linking_enabled,
    vor_enabled
FROM crm.sfdc_dbx.product_property_w_features
WHERE property_id IN (
    SELECT CAST(id AS STRING) FROM rds.pg_rds_public.properties WHERE name LIKE '%Park Kennedy%'
)
"""
result3 = execute_query(query3, "STEP 3: Park Kennedy in product_property_w_features")

# Query 4: Salesforce Records
query4 = """
SELECT
    id as salesforce_id,
    name,
    snappt_property_id_c,
    sf_property_id_c,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c,
    bank_linking_enabled_c,
    is_deleted,
    created_date
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
ORDER BY created_date DESC
"""
result4 = execute_query(query4, "STEP 4: Park Kennedy in Salesforce")

# Query 5: Sync Table
query5 = """
SELECT
    snappt_property_id_c,
    name,
    fraud_detection_enabled_c,
    income_verification_enabled_c,
    id_verification_enabled_c
FROM crm.sfdc_dbx.product_property_feature_sync
WHERE name LIKE '%Park Kennedy%'
"""
result5 = execute_query(query5, "STEP 5: Park Kennedy in Sync Table")

# Query 6: Duplicate Check
query6 = """
SELECT
    snappt_property_id_c,
    COUNT(*) as record_count,
    COLLECT_LIST(id) as salesforce_ids
FROM crm.salesforce.product_property
WHERE name LIKE '%Park Kennedy%'
GROUP BY snappt_property_id_c
"""
result6 = execute_query(query6, "STEP 6: Duplicate Check")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80 + "\n")
