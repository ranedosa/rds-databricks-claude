"""
Configure Census Sync B (UPDATE) via API
Updates existing properties in Salesforce from properties_to_update view
"""
import requests
import json
import sys

CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
IDS_PATH = "/Users/danerosa/rds_databricks_claude/20260105/census_ids.json"
PILOT_FILTER_PATH = "/Users/danerosa/rds_databricks_claude/20260105/pilot_update_properties.csv"

def load_config():
    """Load Census API credentials"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_ids():
    """Load connection IDs"""
    try:
        with open(IDS_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ IDs file not found. Run census_api_setup.py first!")
        sys.exit(1)

def load_pilot_ids():
    """Load pilot property IDs from CSV"""
    import csv
    pilot_ids = []

    with open(PILOT_FILTER_PATH, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            pilot_ids.append(row['rds_property_id'])

    return pilot_ids[:50]  # First 50

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def create_sync_b(config, conn_ids):
    """Create Sync B (UPDATE) configuration"""

    url = f"{config['api_base_url']}/syncs"
    headers = get_headers(config['api_key'])

    # Load pilot IDs for filter
    pilot_ids = load_pilot_ids()
    pilot_filter = "rds_property_id IN ('" + "','".join(pilot_ids) + "')"

    print(f"\n📋 Pilot filter includes {len(pilot_ids)} properties")

    # Sync configuration
    sync_config = {
        "source_attributes": {
            "connection_id": conn_ids['databricks_connection_id'],
            "object": {
                "type": "table",
                "table_catalog": "crm",
                "table_schema": "sfdc_dbx",
                "table_name": "properties_to_update"
            }
        },
        "destination_attributes": {
            "connection_id": conn_ids['salesforce_destination_id'],
            "object": "product_property__c"
        },
        "mappings": [
            # Primary Key for UPDATE
            {"from": {"type": "column", "data": "snappt_property_id_c"}, "to": "snappt_property_id__c", "is_primary_identifier": True},

            # Core Identifiers
            {"from": {"type": "column", "data": "rds_property_id"}, "to": "snappt_property_id__c"},
            {"from": {"type": "column", "data": "sfdc_id"}, "to": "sf_property_id__c"},
            {"from": {"type": "column", "data": "short_id"}, "to": "short_id__c"},
            {"from": {"type": "column", "data": "company_id"}, "to": "company_id__c"},

            # Property Attributes
            {"from": {"type": "column", "data": "property_name"}, "to": "name"},
            {"from": {"type": "column", "data": "address"}, "to": "property_address_street__s"},
            {"from": {"type": "column", "data": "city"}, "to": "property_address_city__s"},
            {"from": {"type": "column", "data": "state"}, "to": "property_address_state_code__s"},
            {"from": {"type": "column", "data": "postal_code"}, "to": "property_address_postal_code__s"},
            {"from": {"type": "column", "data": "company_name"}, "to": "company_name__c"},

            # Feature Flags
            {"from": {"type": "column", "data": "idv_enabled"}, "to": "id_verification_enabled__c"},
            {"from": {"type": "column", "data": "bank_linking_enabled"}, "to": "bank_linking_enabled__c"},
            {"from": {"type": "column", "data": "payroll_enabled"}, "to": "connected_payroll_enabled__c"},
            {"from": {"type": "column", "data": "income_insights_enabled"}, "to": "income_verification_enabled__c"},
            {"from": {"type": "column", "data": "document_fraud_enabled"}, "to": "fraud_detection_enabled__c"},

            # Feature Timestamps
            {"from": {"type": "column", "data": "idv_enabled_at"}, "to": "id_verification_start_date__c"},
            {"from": {"type": "column", "data": "bank_linking_enabled_at"}, "to": "bank_linking_start_date__c"},
            {"from": {"type": "column", "data": "payroll_enabled_at"}, "to": "connected_payroll_start_date__c"},
            {"from": {"type": "column", "data": "income_insights_enabled_at"}, "to": "income_verification_start_date__c"},
            {"from": {"type": "column", "data": "document_fraud_enabled_at"}, "to": "fraud_detection_start_date__c"},

            # Metadata
            {"from": {"type": "column", "data": "created_at"}, "to": "rds_created_date__c"},
            {"from": {"type": "column", "data": "rds_last_updated_at"}, "to": "rds_last_updated_date__c"},

            # Aggregation Metrics (NEW - unique to UPDATE sync)
            {"from": {"type": "column", "data": "active_property_count"}, "to": "active_property_count__c"},
            {"from": {"type": "column", "data": "total_feature_count"}, "to": "total_feature_count__c"},
            {"from": {"type": "column", "data": "is_multi_property"}, "to": "is_multi_property__c"}
        ],
        "operation": "upsert",  # UPDATE mode (upsert = update or insert)
        "schedule_frequency": "manual",  # Don't schedule yet
        "paused": True,  # Start paused
        "field_behavior": "specific_properties",
        "advanced_configuration": {
            "source_filter": pilot_filter  # PILOT FILTER
        }
    }

    print("\n" + "="*80)
    print("CREATING CENSUS SYNC B (UPDATE)")
    print("="*80)
    print(f"\nSource: crm.sfdc_dbx.properties_to_update")
    print(f"Destination: Salesforce product_property__c")
    print(f"Operation: UPSERT (update existing records)")
    print(f"Sync Key: snappt_property_id__c")
    print(f"Field Mappings: {len(sync_config['mappings'])}")
    print(f"Pilot Filter: {len(pilot_ids)} properties")

    try:
        response = requests.post(url, headers=headers, json=sync_config)
        response.raise_for_status()
        sync = response.json()

        print(f"\n✅ Sync B (UPDATE) created successfully!")
        print(f"   Sync ID: {sync.get('id', 'N/A')}")
        print(f"   Status: {sync.get('status', 'N/A')}")
        print(f"\n📋 View in Census: https://app.getcensus.com/syncs/{sync.get('id')}")

        # Save sync ID
        with open('/Users/danerosa/rds_databricks_claude/20260105/sync_b_id.txt', 'w') as f:
            f.write(str(sync.get('id')))

        return sync.get('id')

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error creating sync: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def main():
    """Main function"""
    print("\n" + "="*80)
    print("CENSUS SYNC B (UPDATE) - CONFIGURATION")
    print("="*80)

    try:
        config = load_config()
        conn_ids = load_ids()

        print(f"\n✅ Using Databricks Connection ID: {conn_ids['databricks_connection_id']}")
        print(f"✅ Using Salesforce Destination ID: {conn_ids['salesforce_destination_id']}")

        sync_id = create_sync_b(config, conn_ids)

        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print(f"\n1. Review sync configuration in Census UI")
        print(f"2. Run run_pilot_syncs.py to execute both pilots")
        print(f"3. Validate results in Salesforce")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
