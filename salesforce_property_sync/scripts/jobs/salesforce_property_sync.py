# Databricks notebook source
"""
Salesforce to Snappt Property Sync Job
========================================

This job syncs new properties from Salesforce to Snappt API:
1. Reads properties added in last 24 hours from crm.salesforce.property
2. Writes them to a temp table
3. Checks if property exists in rds.pg_rds_public.properties (using sfdc_id)
4. Creates missing properties via Snappt API POST request
5. Verifies successful creation

Schedule: Daily cron job

Author: Data Engineering Team
Created: 2024-11-04
"""

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration and Imports

# COMMAND ----------

import requests
import json
from datetime import datetime, timedelta
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

# COMMAND ----------

# MAGIC %md
# MAGIC ## Job Configuration

# COMMAND ----------

# Snappt API Configuration
SNAPPT_API_URL = "https://enterprise-api.test.snappt.com/properties"
SNAPPT_API_TOKEN = dbutils.secrets.get(scope="snappt-api", key="bearer-token")  # Fallback to env var for testing

# Database Configuration
SALESFORCE_TABLE = "crm.salesforce.property"
RDS_PROPERTIES_TABLE = "rds.pg_rds_public.properties"
TEMP_TABLE = "team_sandbox.data_engineering.temp_new_salesforce_properties"

# Time Configuration
LOOKBACK_HOURS = 24

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def get_new_salesforce_properties():
    """
    Query Salesforce for properties added in the last 24 hours.
    Returns DataFrame with new properties.
    """
    lookback_time = datetime.now() - timedelta(hours=LOOKBACK_HOURS)

    query = f"""
        SELECT
            id as sf_property_id,
            name as sf_property_name,
            company_id_c as sf_company_id,
            company_name_c as sf_account_name,
            address_street_s,
            address_city_s,
            address_state_s,
            address_postal_code_s,
            unit_c as sf_property_unit_count,
            email_c as sf_property_manager_email,
            status_c as sf_property_status,
            createddate as sf_created_date
        FROM {SALESFORCE_TABLE}
        WHERE createddate >= '{lookback_time.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_c = 'Active'
        ORDER BY createddate DESC
    """

    df = spark.sql(query)
    print(f"Found {df.count()} new properties in Salesforce from last {LOOKBACK_HOURS} hours")
    return df

# COMMAND ----------

def write_to_temp_table(df):
    """
    Write new Salesforce properties to temp table for tracking.
    """
    # Add processing metadata
    df_with_metadata = df.withColumn("processing_timestamp", F.current_timestamp()) \
                         .withColumn("sync_status", F.lit("pending"))

    # Write to temp table (overwrite mode for daily run)
    df_with_metadata.write.mode("overwrite").saveAsTable(TEMP_TABLE)
    print(f"Written {df_with_metadata.count()} records to {TEMP_TABLE}")

    return df_with_metadata

# COMMAND ----------

def check_property_exists_in_rds(sfdc_id):
    """
    Check if a property with the given sfdc_id exists in RDS.
    Returns True if exists, False otherwise.
    """
    query = f"""
        SELECT COUNT(*) as count
        FROM {RDS_PROPERTIES_TABLE}
        WHERE sfdc_id = '{sfdc_id}'
    """

    result = spark.sql(query).collect()[0]['count']
    return result > 0

# COMMAND ----------

def create_property_in_snappt(property_data):
    """
    Create a property in Snappt via API POST request.

    Args:
        property_data: dict with property information

    Returns:
        tuple: (success: bool, response_data: dict, error_message: str)
    """
    # Build API payload
    payload = {
        "name": property_data.get('sf_property_name'),
        "email": property_data.get('sf_property_manager_email'),
        "address": property_data.get('address_street_s'),
        "city": property_data.get('address_city_s'),
        "state": property_data.get('address_state_s'),
        "zip": property_data.get('address_postal_code_s'),
        "unit": property_data.get('sf_property_unit_count'),
        "status": property_data.get('sf_property_status', 'Active'),
        "pmcName": property_data.get('sf_account_name', 'Unknown Company'),
        "sfdc_id": property_data.get('sf_property_id')  # Include SFDC ID for tracking
    }

    # Build headers
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {SNAPPT_API_TOKEN}"
    }

    try:
        # Make API request
        response = requests.post(SNAPPT_API_URL, json=payload, headers=headers, timeout=30)

        # Check response
        if response.status_code in [200, 201]:
            return True, response.json(), None
        else:
            error_msg = f"API returned status {response.status_code}: {response.text}"
            return False, None, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return False, None, error_msg

# COMMAND ----------

def verify_property_creation(sfdc_id, max_retries=3, retry_delay=5):
    """
    Verify that a property was successfully created in RDS.

    Args:
        sfdc_id: Salesforce property ID to verify
        max_retries: Number of times to check before giving up
        retry_delay: Seconds to wait between retries

    Returns:
        bool: True if property found in RDS, False otherwise
    """
    import time

    for attempt in range(max_retries):
        if check_property_exists_in_rds(sfdc_id):
            return True

        if attempt < max_retries - 1:
            print(f"Property {sfdc_id} not yet in RDS, waiting {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(retry_delay)

    return False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main Job Execution

# COMMAND ----------

def run_property_sync():
    """
    Main function that orchestrates the property sync process.
    """
    print("=" * 80)
    print("SALESFORCE TO SNAPPT PROPERTY SYNC JOB")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: Get new properties from Salesforce
    print("\n[Step 1] Querying new properties from Salesforce...")
    sf_properties_df = get_new_salesforce_properties()

    if sf_properties_df.count() == 0:
        print("No new properties found. Job complete.")
        return

    # Step 2: Write to temp table
    print("\n[Step 2] Writing to temp table...")
    temp_df = write_to_temp_table(sf_properties_df)

    # Step 3: Process each property
    print("\n[Step 3] Processing properties...")
    properties_to_process = temp_df.collect()

    results = {
        'total': len(properties_to_process),
        'already_exists': 0,
        'created_successfully': 0,
        'failed': 0,
        'verified': 0,
        'verification_failed': 0
    }

    for row in properties_to_process:
        sfdc_id = row['sf_property_id']
        property_name = row['sf_property_name']

        print(f"\n--- Processing: {property_name} (SFDC ID: {sfdc_id}) ---")

        # Check if already exists in RDS
        if check_property_exists_in_rds(sfdc_id):
            print(f"✓ Property already exists in RDS, skipping...")
            results['already_exists'] += 1
            continue

        # Convert Row to dict for API call
        property_data = row.asDict()

        # Create property via API
        print(f"→ Creating property in Snappt...")
        success, response_data, error_msg = create_property_in_snappt(property_data)

        if success:
            print(f"✓ API request successful")
            results['created_successfully'] += 1

            # Verify creation
            print(f"→ Verifying property creation in RDS...")
            if verify_property_creation(sfdc_id):
                print(f"✓ Property verified in RDS")
                results['verified'] += 1
            else:
                print(f"✗ Property not found in RDS after retries")
                results['verification_failed'] += 1
        else:
            print(f"✗ Failed to create property: {error_msg}")
            results['failed'] += 1

    # Step 4: Print summary
    print("\n" + "=" * 80)
    print("JOB SUMMARY")
    print("=" * 80)
    print(f"Total properties processed:     {results['total']}")
    print(f"Already existed in RDS:         {results['already_exists']}")
    print(f"Created via API:                {results['created_successfully']}")
    print(f"Failed to create:               {results['failed']}")
    print(f"Successfully verified in RDS:   {results['verified']}")
    print(f"Verification failed:            {results['verification_failed']}")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Return results for job monitoring
    return results

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Job

# COMMAND ----------

# Run the sync job
results = run_property_sync()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup and Monitoring Queries

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View the temp table with today's processed properties
# MAGIC SELECT * FROM team_sandbox.data_engineering.temp_new_salesforce_properties
# MAGIC ORDER BY sf_created_date DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check for properties that were created today in RDS
# MAGIC SELECT
# MAGIC   p.id,
# MAGIC   p.name,
# MAGIC   p.sfdc_id,
# MAGIC   p.inserted_at,
# MAGIC   c.name as company_name
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC LEFT JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
# MAGIC WHERE p.inserted_at >= CURRENT_DATE
# MAGIC ORDER BY p.inserted_at DESC
