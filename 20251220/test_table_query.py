#!/usr/bin/env python3
"""
Test script to diagnose DESCRIBE DETAIL failures
"""

import os
import requests
import json

# Databricks configuration
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
WAREHOUSE_ID = "9b7a58ad33c27fbc"

def test_table(table_name):
    """Test DESCRIBE DETAIL on a specific table"""
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements/"
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    query = f"DESCRIBE DETAIL `{table_name}`"

    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": "50s"
    }

    print(f"Testing table: {table_name}")
    print(f"Query: {query}")
    print("=" * 80)

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code}")
        print(response.text)
        return

    result = response.json()
    print("Full Response:")
    print(json.dumps(result, indent=2))

    status = result.get('status', {})
    state = status.get('state')

    print("\n" + "=" * 80)
    print(f"State: {state}")

    if state != 'SUCCEEDED':
        error_info = status.get('error', {})
        print(f"Error Code: {error_info.get('error_code')}")
        print(f"Error Message: {error_info.get('message')}")
        print(f"Full Error Info:")
        print(json.dumps(error_info, indent=2))

# Test a few different types of tables
test_tables = [
    "crm._fivetran_setup_test.setup_test_staging_17b3c1e8_bef5_4b36_a6f0_df0eea6c5fa6",
    "crm.aln.activerowversion",
    "rds.pg_rds_public.properties"
]

for table in test_tables:
    print("\n" + "=" * 80)
    print(f"TEST: {table}")
    print("=" * 80)
    test_table(table)
    print("\n")
