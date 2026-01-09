"""
Configure Census Sync B (UPDATE) via API - v2 with correct field names
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

    # Sync configuration - Using only fields that exist in Salesforce
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
            "object": "Product_Property__c"  # Pascal Case
        },
        "mappings": [
            # Primary Key for UPDATE - Use Snappt Property ID from SF
            {"from": {"type": "column", "data": "snappt_property_id_c"}, "to": "Snappt_Property_ID__c", "is_primary_identifier": True},

            # Core Identifiers
            {"from": {"type": "column", "data": "rds_property_id"}, "to": "Snappt_Property_ID__c"},
            {"from": {"type": "column", "data": "short_id"}, "to": "Short_ID__c"},
            {"from": {"type": "column", "data": "company_id"}, "to": "Company_ID__c"},

            # Property Attributes
            {"from": {"type": "column", "data": "property_name"}, "to": "Name"},
            {"from": {"type": "column", "data": "address"}, "to": "Address__Street__s"},
            {"from": {"type": "column", "data": "city"}, "to": "Address__City__s"},
            {"from": {"type": "column", "data": "state"}, "to": "Address__StateCode__s"},
            {"from": {"type": "column", "data": "postal_code"}, "to": "Address__PostalCode__s"},
            {"from": {"type": "column", "data": "company_name"}, "to": "Entity_Name__c"},

            # Feature Flags
            {"from": {"type": "column", "data": "idv_enabled"}, "to": "ID_Verification_Enabled__c"},
            {"from": {"type": "column", "data": "bank_linking_enabled"}, "to": "Bank_Linking_Enabled__c"},
            {"from": {"type": "column", "data": "payroll_enabled"}, "to": "Connected_Payroll_Enabled__c"},
            {"from": {"type": "column", "data": "income_insights_enabled"}, "to": "Income_Verification_Enabled__c"},
            {"from": {"type": "column", "data": "document_fraud_enabled"}, "to": "Fraud_Detection_Enabled__c"},

            # Feature Timestamps
            {"from": {"type": "column", "data": "idv_enabled_at"}, "to": "ID_Verification_Start_Date__c"},
            {"from": {"type": "column", "data": "bank_linking_enabled_at"}, "to": "Bank_Linking_Start_Date__c"},
            {"from": {"type": "column", "data": "payroll_enabled_at"}, "to": "Connected_Payroll_Start_Date__c"},
            {"from": {"type": "column", "data": "income_insights_enabled_at"}, "to": "Income_Verification_Start_Date__c"},
            {"from": {"type": "column", "data": "document_fraud_enabled_at"}, "to": "Fraud_Detection_Start_Date__c"}
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
    print(f"Destination: Salesforce Product_Property__c")
    print(f"Operation: UPSERT (update existing records)")
    print(f"Sync Key: Snappt_Property_ID__c")
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
    print("CENSUS SYNC B (UPDATE) - CONFIGURATION V2")
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
