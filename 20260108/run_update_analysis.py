#!/usr/bin/env python3
"""
Run the update analysis SQL queries
"""
import os
from databricks import sql
import pandas as pd

# Read SQL file
with open('/Users/danerosa/rds_databricks_claude/analyze_feature_flag_updates.sql', 'r') as f:
    sql_content = f.read()

# Split by section markers
queries = []
current_query = []
for line in sql_content.split('\n'):
    if line.strip().startswith('-- ============') and current_query:
        # Start of new section, save previous query
        query_text = '\n'.join(current_query).strip()
        if query_text and not query_text.startswith('--'):
            queries.append(query_text)
        current_query = []
    elif not line.strip().startswith('--') or line.strip() == '':
        current_query.append(line)

# Add last query
if current_query:
    query_text = '\n'.join(current_query).strip()
    if query_text:
        queries.append(query_text)

# Connect to Databricks
host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")

connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/25145408b75455a6",
    access_token=os.getenv("DATABRICKS_TOKEN")
)

cursor = connection.cursor()

try:
    print("=" * 80)
    print("UPDATE IMPACT ANALYSIS - 7,820 PROPERTIES")
    print("=" * 80)
    print("What will change when you run the UPDATE sync?")
    print("=" * 80)
    print()

    # Run each query
    for i, query in enumerate(queries, 1):
        if i == 1:
            print("=" * 80)
            print("STEP 1: Feature Flag Changes")
            print("=" * 80)
            print()
        elif i == 2:
            print()
            print("=" * 80)
            print("STEP 2: Overall Summary")
            print("=" * 80)
            print()
        elif i == 3:
            print()
            print("=" * 80)
            print("STEP 3: Sample Properties with Changes (30 examples)")
            print("=" * 80)
            print()

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        if results:
            df = pd.DataFrame(results, columns=columns)
            print(df.to_string(index=False))
        else:
            print("No results")

    print()
    print("=" * 80)
    print("INTERPRETATION & RECOMMENDATION")
    print("=" * 80)
    print()
    print("Key Things to Check:")
    print()
    print("1. **Percentage Changing**: Is it reasonable?")
    print("   - <10% = Minor tweaks (expected)")
    print("   - 10-30% = Moderate updates (review carefully)")
    print("   - >50% = Major changes (verify this is intended)")
    print()
    print("2. **Turning OFF vs ON**: Are features being disabled?")
    print("   - Turning ON (false → true) = Good, enabling features")
    print("   - Turning OFF (true → false) = ⚠️ Review, could impact customers")
    print()
    print("3. **Sample Records**: Do the changes look correct?")
    print("   - Check if property names are familiar")
    print("   - Verify flag changes match expectations")
    print()
    print("✅ SAFE TO PROCEED IF:")
    print("   - % changes match your expectations")
    print("   - Mostly turning features ON (not OFF)")
    print("   - Sample records look correct")
    print("   - No unexpected patterns")
    print()
    print("⚠️ INVESTIGATE IF:")
    print("   - High % of properties changing unexpectedly")
    print("   - Many features being turned OFF")
    print("   - Sample shows incorrect data")

finally:
    cursor.close()
    connection.close()
