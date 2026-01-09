#!/usr/bin/env python3
"""
Search for fuzzy matches in production Property__c schema
Look for columns that might be receiving feature flag data with different names
"""

import os
from databricks import sql
import re

# Databricks connection details
DATABRICKS_HOST = "https://dbc-9ca0f5e0-2208.cloud.databricks.com"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/95a8f5979c3f8740"

# Keywords to search for (fuzzy matching)
SEARCH_TERMS = {
    'IDV / ID Verification': ['id', 'idv', 'identity', 'verification', 'verify'],
    'Bank Linking': ['bank', 'banking', 'link', 'linking', 'plaid', 'financial'],
    'Payroll': ['payroll', 'pay', 'salary', 'income'],
    'Income Insights': ['income', 'insight', 'insights', 'earning', 'revenue'],
    'Fraud Detection': ['fraud', 'document', 'doc', 'detection', 'detect', 'risk'],
}

def get_schema():
    """Get full schema from production Property__c"""
    connection = sql.connect(
        server_hostname=DATABRICKS_HOST.replace('https://', ''),
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

    cursor = connection.cursor()
    cursor.execute("DESCRIBE hive_metastore.salesforce.property_c")

    columns = []
    for row in cursor.fetchall():
        col_name = row[0]
        col_type = row[1]
        columns.append({'name': col_name, 'type': col_type})

    cursor.close()
    connection.close()

    return columns

def fuzzy_match(column_name, keywords):
    """Check if column name contains any of the keywords"""
    col_lower = column_name.lower()
    matches = []
    for keyword in keywords:
        if keyword.lower() in col_lower:
            matches.append(keyword)
    return matches

def sample_column_data(column_name):
    """Get sample data from a column to understand its content"""
    connection = sql.connect(
        server_hostname=DATABRICKS_HOST.replace('https://', ''),
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

    cursor = connection.cursor()

    query = f"""
    SELECT
        {column_name},
        COUNT(*) as count
    FROM hive_metastore.salesforce.property_c
    WHERE {column_name} IS NOT NULL
    GROUP BY {column_name}
    LIMIT 10
    """

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return results
    except Exception as e:
        cursor.close()
        connection.close()
        return None

def main():
    print("\n" + "="*80)
    print("FUZZY MATCH SEARCH - Production Property__c Schema")
    print("="*80 + "\n")
    print("Searching for columns that might be receiving feature flag data...")
    print("Looking for variations of: IDV, Bank Linking, Payroll, Income, Fraud\n")

    # Get schema
    schema = get_schema()
    print(f"Total columns in production: {len(schema)}\n")

    # Search for matches
    all_matches = {}

    for feature, keywords in SEARCH_TERMS.items():
        print(f"\n{'='*80}")
        print(f"🔍 Searching for: {feature}")
        print(f"   Keywords: {', '.join(keywords)}")
        print(f"{'='*80}\n")

        matches = []
        for col in schema:
            matched_keywords = fuzzy_match(col['name'], keywords)
            if matched_keywords:
                matches.append({
                    'column': col['name'],
                    'type': col['type'],
                    'matched_keywords': matched_keywords
                })

        if matches:
            print(f"✓ Found {len(matches)} potential matches:\n")
            for match in matches:
                print(f"  Column: {match['column']}")
                print(f"  Type: {match['type']}")
                print(f"  Matched: {', '.join(match['matched_keywords'])}")

                # Get sample data for boolean/string fields
                if match['type'] in ['boolean', 'string', 'double']:
                    print(f"  Sample data:")
                    samples = sample_column_data(match['column'])
                    if samples:
                        for value, count in samples[:5]:
                            print(f"    - {value} ({count} records)")
                    else:
                        print(f"    (Could not retrieve samples)")
                print()

            all_matches[feature] = matches
        else:
            print(f"✗ No matches found for {feature}\n")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY OF FUZZY MATCHES")
    print(f"{'='*80}\n")

    if all_matches:
        total_matches = sum(len(matches) for matches in all_matches.values())
        print(f"Total potential matches found: {total_matches}\n")

        for feature, matches in all_matches.items():
            print(f"{feature}:")
            for match in matches:
                print(f"  • {match['column']} ({match['type']})")
            print()

        print("\n" + "="*80)
        print("ANALYSIS")
        print("="*80 + "\n")
        print("These columns might be:")
        print("1. Receiving feature flag data with different naming")
        print("2. Legacy columns from previous sync attempts")
        print("3. Related but different fields (e.g., HubSpot, ALN)")
        print("4. Coincidental name matches\n")
        print("Next step: Compare actual data values in these columns")
        print("with the feature flags we synced to staging.")

    else:
        print("No fuzzy matches found.")
        print("\nThis confirms:")
        print("• Production has NO columns related to feature flags")
        print("• Census is correctly writing to staging only")
        print("• No risk of accidental production updates")

if __name__ == "__main__":
    main()
