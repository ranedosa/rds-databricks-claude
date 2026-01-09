#!/usr/bin/env python3
import os
from databricks import sql

host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")
connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/95a8f5979c3f8740",
    access_token=os.getenv("DATABRICKS_TOKEN")
)
cursor = connection.cursor()

print("="*80)
print("QUICK TEST: Verify Company Names Fixed")
print("="*80)
print()

# TEST 1: Check if property names are different from company names
print("TEST 1: Property Name vs Company Name")
print("-"*80)

query = """
SELECT
    property_name,
    company_name,
    CASE
        WHEN property_name = company_name THEN 'STILL_BROKEN'
        WHEN property_name != company_name THEN 'FIXED'
        WHEN company_name IS NULL THEN 'NULL'
        ELSE 'OTHER'
    END as status
FROM crm.sfdc_dbx.rds_properties_enriched
LIMIT 20
"""

cursor.execute(query)
results = cursor.fetchall()

print(f"{'Property Name':<40} {'Company Name':<40} {'Status':<15}")
print("-"*100)

status_counts = {}
for prop, comp, status in results:
    status_counts[status] = status_counts.get(status, 0) + 1
    prop_display = (prop[:37] + "...") if prop and len(str(prop)) > 40 else (prop or "NULL")
    comp_display = (comp[:37] + "...") if comp and len(str(comp)) > 40 else (comp or "NULL")
    symbol = "✅" if status == "FIXED" else ("❌" if status == "STILL_BROKEN" else "⚠️")
    print(f"{str(prop_display):<40} {str(comp_display):<40} {symbol} {status:<15}")

print()
print("Status Summary:")
for status, count in status_counts.items():
    pct = 100 * count / len(results)
    print(f"  {status:<20} {count:>3} ({pct:>5.1f}%)")

print()

# TEST 2: Check specific properties we know were broken
print("TEST 2: Known Broken Properties")
print("-"*80)

query_known = """
SELECT
    property_name,
    company_name
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_name IN (
    'Hardware',
    'Rowan',
    'Skymor Wesley Chapel',
    'The Storey',
    'South and Twenty'
)
"""

cursor.execute(query_known)
known_results = cursor.fetchall()

if known_results:
    print(f"\n{'Property Name':<30} {'Company Name':<30} {'Expected':<30}")
    print("-"*90)
    
    expected_companies = {
        'Hardware': 'Greystar',
        'Rowan': 'Greystar',
        'Skymor Wesley Chapel': 'Greystar',
        'The Storey': 'AVENUE5 RESIDENTIAL',
        'South and Twenty': 'RKW Residential'
    }
    
    all_correct = True
    for prop, comp in known_results:
        expected = expected_companies.get(prop, 'Unknown')
        is_correct = comp == expected
        symbol = "✅" if is_correct else "❌"
        print(f"{prop:<30} {comp or 'NULL':<30} {expected:<30} {symbol}")
        if not is_correct:
            all_correct = False
    
    print()
    if all_correct:
        print("✅ All known broken properties are now FIXED!")
    else:
        print("⚠️  Some properties still don't match expected companies")
else:
    print("⚠️  Known properties not found in view")

print()

# TEST 3: Overall statistics
print("TEST 3: Overall Statistics")
print("-"*80)

query_stats = """
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN property_name != company_name THEN 1 ELSE 0 END) as different,
    SUM(CASE WHEN property_name = company_name THEN 1 ELSE 0 END) as same,
    SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as nulls
FROM crm.sfdc_dbx.rds_properties_enriched
"""

cursor.execute(query_stats)
total, different, same, nulls = cursor.fetchall()[0]

print(f"\nTotal properties: {total:,}")
print(f"  Property != Company: {different:,} ({100*different/total:.1f}%)")
print(f"  Property = Company:  {same:,} ({100*same/total:.1f}%)")
print(f"  Company is NULL:     {nulls:,} ({100*nulls/total:.1f}%)")

print()
print("="*80)

if different / total >= 0.95:
    print("✅ VIEW FIX SUCCESSFUL!")
    print(f"   {100*different/total:.1f}% of properties have different property/company names")
    print()
    print("Next step: Re-run Census syncs to update Salesforce")
elif same > 0:
    print("❌ VIEW STILL BROKEN!")
    print(f"   {same:,} properties still have property name as company name")
    print("   The view fix may not have applied correctly")
elif different / total < 0.95:
    print("⚠️  PARTIAL FIX")
    print(f"   {100*different/total:.1f}% have different names (expected >95%)")
    print("   May be due to NULL companies")

print("="*80)

cursor.close()
connection.close()
