"""
Census API Setup - Get connection IDs and destination info
Run this first to gather info needed for sync configuration
"""
import requests
import json
import sys

# Load Census credentials
CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"

def load_config():
    """Load Census API credentials"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def get_connections(config):
    """Get all source connections"""
    url = f"{config['api_base_url']}/sources"
    headers = get_headers(config['api_key'])

    print("\n" + "="*80)
    print("FETCHING SOURCE CONNECTIONS")
    print("="*80)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        connections = response.json()

        print(f"\n✅ Found {len(connections.get('data', []))} source connection(s)")

        for conn in connections.get('data', []):
            print(f"\n📊 Connection ID: {conn['id']}")
            print(f"   Name: {conn.get('name', 'N/A')}")
            print(f"   Type: {conn.get('type', 'N/A')}")

            # Look for Databricks connection
            if 'databricks' in conn.get('type', '').lower():
                print(f"   ⭐ DATABRICKS CONNECTION FOUND!")
                return conn['id']

        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching connections: {e}")
        return None

def get_destinations(config):
    """Get all destination connections"""
    url = f"{config['api_base_url']}/destinations"
    headers = get_headers(config['api_key'])

    print("\n" + "="*80)
    print("FETCHING DESTINATION CONNECTIONS")
    print("="*80)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        destinations = response.json()

        print(f"\n✅ Found {len(destinations.get('data', []))} destination(s)")

        for dest in destinations.get('data', []):
            print(f"\n🎯 Destination ID: {dest['id']}")
            print(f"   Name: {dest.get('name', 'N/A')}")
            print(f"   Type: {dest.get('type', 'N/A')}")

            # Look for Salesforce connection
            if 'salesforce' in dest.get('type', '').lower():
                print(f"   ⭐ SALESFORCE CONNECTION FOUND!")
                return dest['id']

        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching destinations: {e}")
        return None

def get_existing_syncs(config):
    """Get all existing syncs"""
    url = f"{config['api_base_url']}/syncs"
    headers = get_headers(config['api_key'])

    print("\n" + "="*80)
    print("FETCHING EXISTING SYNCS")
    print("="*80)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        syncs = response.json()

        print(f"\n✅ Found {len(syncs.get('data', []))} existing sync(s)")

        for sync in syncs.get('data', []):
            print(f"\n🔄 Sync ID: {sync['id']}")
            print(f"   Status: {sync.get('status', 'N/A')}")
            print(f"   Operation: {sync.get('operation', 'N/A')}")
            print(f"   Paused: {sync.get('paused', False)}")

            # Check if it's related to properties
            source_obj = sync.get('source_attributes', {}).get('object', {})
            print(f"   Source: {source_obj.get('name', 'N/A')}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching syncs: {e}")

def main():
    """Main function"""
    print("\n" + "="*80)
    print("CENSUS API SETUP - Gathering Configuration Info")
    print("="*80)

    try:
        config = load_config()
        print(f"\n✅ Loaded Census credentials from: {CONFIG_PATH}")
        print(f"   API URL: {config['api_base_url']}")

        # Get connections
        databricks_conn_id = get_connections(config)
        salesforce_dest_id = get_destinations(config)

        # Get existing syncs
        get_existing_syncs(config)

        # Summary
        print("\n" + "="*80)
        print("SUMMARY - Use These IDs for Sync Configuration")
        print("="*80)

        if databricks_conn_id:
            print(f"\n✅ Databricks Connection ID: {databricks_conn_id}")
        else:
            print(f"\n⚠️  Databricks Connection ID: Not found (will use 58981 from existing sync)")
            databricks_conn_id = 58981

        if salesforce_dest_id:
            print(f"✅ Salesforce Destination ID: {salesforce_dest_id}")
        else:
            print(f"⚠️  Salesforce Destination ID: Not found (check Census UI)")

        # Save IDs to file for next scripts
        ids = {
            'databricks_connection_id': databricks_conn_id,
            'salesforce_destination_id': salesforce_dest_id
        }

        with open('/Users/danerosa/rds_databricks_claude/20260105/census_ids.json', 'w') as f:
            json.dump(ids, f, indent=2)

        print(f"\n✅ Saved connection IDs to: census_ids.json")
        print(f"\n📋 Next step: Run configure_sync_a.py to create CREATE sync")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
