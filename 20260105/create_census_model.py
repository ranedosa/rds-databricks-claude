"""
Create Census Model (Business Object) for properties_to_create
"""
import requests
import json
import sys

CONFIG_PATH = "/Users/danerosa/rds_databricks_claude/config/census_credentials.json"
IDS_PATH = "/Users/danerosa/rds_databricks_claude/20260105/census_ids.json"

def load_config():
    """Load Census API credentials"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_ids():
    """Load connection IDs"""
    with open(IDS_PATH, 'r') as f:
        return json.load(f)

def get_headers(api_key):
    """Get API headers"""
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def create_model(config, conn_ids, table_name, model_name):
    """Create a Census model from a Databricks table"""

    url = f"{config['api_base_url']}/models"
    headers = get_headers(config['api_key'])

    # Model configuration
    model_config = {
        "name": model_name,
        "description": f"Model for {table_name}",
        "query": f"SELECT * FROM `crm`.`sfdc_dbx`.`{table_name}`",
        "connection_id": conn_ids['databricks_connection_id']
    }

    print(f"\n📊 Creating Census model: {model_name}")
    print(f"   Query: {model_config['query']}")

    try:
        response = requests.post(url, headers=headers, json=model_config)
        response.raise_for_status()
        model = response.json()

        print(f"\n✅ Model created successfully!")
        print(f"   Model ID: {model.get('id', 'N/A')}")
        print(f"   Model Name: {model.get('name', 'N/A')}")

        return model.get('id')

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error creating model: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return None

def main():
    """Main function"""
    print("\n" + "="*80)
    print("CREATE CENSUS MODELS")
    print("="*80)

    config = load_config()
    conn_ids = load_ids()

    # Create model for properties_to_create
    model_create_id = create_model(
        config, conn_ids,
        "properties_to_create",
        "properties_to_create_model"
    )

    # Create model for properties_to_update
    model_update_id = create_model(
        config, conn_ids,
        "properties_to_update",
        "properties_to_update_model"
    )

    if model_create_id and model_update_id:
        # Save model IDs
        model_ids = {
            "create_model_id": model_create_id,
            "update_model_id": model_update_id
        }

        with open('/Users/danerosa/rds_databricks_claude/20260105/model_ids.json', 'w') as f:
            json.dump(model_ids, f, indent=2)

        print(f"\n✅ Both models created successfully!")
        print(f"   CREATE Model ID: {model_create_id}")
        print(f"   UPDATE Model ID: {model_update_id}")
        print(f"\n📋 Model IDs saved to: model_ids.json")
    else:
        print(f"\n❌ Failed to create one or more models")
        sys.exit(1)

if __name__ == "__main__":
    main()
