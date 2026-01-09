#!/usr/bin/env python3
"""
Check the schema of production Property__c table
"""

import os
from databricks import sql

# Databricks connection details
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"

connection = sql.connect(
    server_hostname=DATABRICKS_HOST.replace('https://', ''),
    http_path=DATABRICKS_HTTP_PATH,
    access_token=DATABRICKS_TOKEN
)

cursor = connection.cursor()

print("\n" + "="*80)
print("PRODUCTION PROPERTY__C SCHEMA")
print("="*80 + "\n")

# Describe the table
cursor.execute("DESCRIBE hive_metastore.salesforce.property_c")

print("Column Name                          | Data Type")
print("-" * 80)

columns = []
for row in cursor.fetchall():
    col_name = row[0]
    col_type = row[1]
    columns.append(col_name)
    print(f"{col_name:40} | {col_type}")

print(f"\nTotal columns: {len(columns)}")

# Check for feature columns
print("\n" + "="*80)
print("FEATURE FLAG COLUMNS CHECK")
print("="*80 + "\n")

feature_columns = [
    'idv_enabled',
    'bank_linking_enabled',
    'payroll_enabled',
    'income_insights_enabled',
    'document_fraud_enabled',
    'idv_enabled_at',
    'bank_linking_enabled_at',
    'payroll_enabled_at',
    'income_insights_enabled_at',
    'document_fraud_enabled_at'
]

for col in feature_columns:
    if col in columns:
        print(f"  ✓ {col} - EXISTS")
    else:
        print(f"  ✗ {col} - MISSING")

# Sample a few records to see what data exists
print("\n" + "="*80)
print("SAMPLE RECORDS (First 3)")
print("="*80 + "\n")

cursor.execute("""
SELECT
    id,
    name,
    snappt_property_id_c,
    last_modified_date
FROM hive_metastore.salesforce.property_c
WHERE snappt_property_id_c IS NOT NULL
LIMIT 3
""")

for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]}")
    print(f"Snappt Property ID: {row[2]}")
    print(f"Last Modified: {row[3]}")
    print()

cursor.close()
connection.close()
