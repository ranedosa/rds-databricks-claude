#!/usr/bin/env python3
"""
Park Kennedy Live Investigation
Uses databricks-sql-connector to run diagnostic queries
"""

import sys
import os

try:
    from databricks import sql
    import pandas as pd
except ImportError:
    print("ERROR: databricks-sql-connector not installed")
    print("Install with: pip install databricks-sql-connector pandas")
    sys.exit(1)

# Databricks connection settings
DATABRICKS_HOST = "dbc-9ca0f5e0-2208.cloud.databricks.com"
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
    print("ERROR: Could not find token in ~/.databrickscfg [pat] section")
    sys.exit(1)

def run_query(connection, query, description):
    """Execute a query and display results"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            print("No results found.\n")
            return None

        # Create pandas DataFrame for better display
        df = pd.DataFrame(rows, columns=columns)
        print(df.to_string(index=False))
        print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''} returned)\n")

        cursor.close()
        return df

    except Exception as e:
        print(f"ERROR: {str(e)}\n")
        return None

def main():
    print("\n" + "="*80)
    print("PARK KENNEDY FEATURE SYNC - LIVE INVESTIGATION")
    print("="*80)
    print(f"Host: {DATABRICKS_HOST}")
    print(f"Warehouse: {WAREHOUSE_ID}")
    print("="*80)

    # Connect to Databricks
    print("\nConnecting to Databricks...")
    try:
        connection = sql.connect(
            server_hostname=DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            access_token=token
        )
        print("✓ Connected successfully\n")
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}\n")
        sys.exit(1)

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
    df1 = run_query(connection, query1, "STEP 1: Park Kennedy in RDS Properties")

    # Query 2: Feature Events (limited to latest per feature)
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
        name,
        feature_code,
        event_type,
        inserted_at,
        _fivetran_deleted
    FROM ranked_events
    WHERE event_rank = 1
    ORDER BY feature_code
    """
    df2 = run_query(connection, query2, "STEP 2: Latest Feature Events for Park Kennedy")

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
    df3 = run_query(connection, query3, "STEP 3: Park Kennedy in product_property_w_features")

    # Query 4: Salesforce Records
    query4 = """
    SELECT
        id as salesforce_id,
        name,
        snappt_property_id_c,
        sf_property_id_c,
        fraud_detection_enabled_c as fraud,
        income_verification_enabled_c as iv,
        id_verification_enabled_c as idv,
        idv_only_enabled_c as idv_only,
        connected_payroll_enabled_c as payroll,
        bank_linking_enabled_c as bank,
        verification_of_rent_enabled_c as vor,
        is_deleted,
        created_date
    FROM crm.salesforce.product_property
    WHERE name LIKE '%Park Kennedy%'
    ORDER BY created_date DESC
    """
    df4 = run_query(connection, query4, "STEP 4: Park Kennedy in Salesforce")

    # Query 5: Sync Table
    query5 = """
    SELECT
        snappt_property_id_c,
        name,
        fraud_detection_enabled_c as fraud,
        income_verification_enabled_c as iv,
        id_verification_enabled_c as idv,
        bank_linking_enabled_c as bank,
        connected_payroll_enabled_c as payroll
    FROM crm.sfdc_dbx.product_property_feature_sync
    WHERE name LIKE '%Park Kennedy%'
    """
    df5 = run_query(connection, query5, "STEP 5: Park Kennedy in Sync Table (needs update)")

    # Query 6: ID Mapping Check
    query6 = """
    SELECT
        p.id as rds_property_id,
        p.sfdc_id as rds_sfdc_id,
        sf.id as sf_record_id,
        sf.snappt_property_id_c,
        sf.sf_property_id_c,
        CASE
            WHEN CAST(p.id AS STRING) = sf.snappt_property_id_c THEN '✓ MATCH'
            ELSE '✗ MISMATCH'
        END as id_status
    FROM rds.pg_rds_public.properties p
    FULL OUTER JOIN crm.salesforce.product_property sf
        ON sf.name LIKE CONCAT('%', p.name, '%')
    WHERE p.name LIKE '%Park Kennedy%' OR sf.name LIKE '%Park Kennedy%'
    """
    df6 = run_query(connection, query6, "STEP 6: ID Mapping Check")

    # Query 7: Duplicate Check
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
    df7 = run_query(connection, query7, "STEP 7: Duplicate Records Check")

    connection.close()

    # Analysis Summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80 + "\n")

    if df1 is not None and len(df1) > 0:
        print(f"✓ Park Kennedy found in RDS (property_id: {df1.iloc[0]['property_id']})")
    else:
        print("✗ Park Kennedy NOT found in RDS")

    if df2 is not None and len(df2) > 0:
        enabled_features = df2[df2['event_type'] == 'enabled']['feature_code'].tolist()
        print(f"✓ Features enabled in RDS: {', '.join(enabled_features) if enabled_features else 'NONE'}")
    else:
        print("✗ No feature events found in RDS")

    if df3 is not None and len(df3) > 0:
        print(f"✓ Park Kennedy found in product_property_w_features")
    else:
        print("✗ Park Kennedy NOT in product_property_w_features (PROBLEM!)")

    if df4 is not None:
        record_count = len(df4)
        if record_count > 1:
            print(f"⚠ DUPLICATE ISSUE: {record_count} Salesforce records found (LIKELY ROOT CAUSE!)")
        elif record_count == 1:
            print(f"✓ Single Salesforce record found")
        else:
            print("✗ Park Kennedy NOT in Salesforce")

    if df5 is not None and len(df5) > 0:
        print(f"✓ Park Kennedy IS in sync table (will be updated on next sync)")
    else:
        print("✗ Park Kennedy NOT in sync table (features may already match)")

    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
