#!/usr/bin/env python3
"""
Validate that company name fix was successful
Run this AFTER re-running both Census syncs
"""
import os
from databricks import sql
from datetime import datetime

host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")
connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/95a8f5979c3f8740",
    access_token=os.getenv("DATABRICKS_TOKEN")
)
cursor = connection.cursor()

print("="*80)
print("COMPANY NAME FIX VALIDATION")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
print()

try:
    # VALIDATION 1: Overall status distribution
    print("VALIDATION 1: Overall Fix Status")
    print("-"*80)

    query = """
    SELECT
        CASE
            WHEN sf.company_name_c = c.name THEN 'CORRECT'
            WHEN sf.company_name_c = p.name THEN 'STILL_BROKEN'
            WHEN sf.company_name_c IS NULL AND c.name IS NOT NULL THEN 'SF_NULL_BUT_DATA_EXISTS'
            WHEN sf.company_name_c IS NULL AND c.name IS NULL THEN 'LEGITIMATE_NULL'
            ELSE 'OTHER'
        END as status,
        COUNT(*) as count
    FROM crm.salesforce.product_property sf
    INNER JOIN rds.pg_rds_public.properties p
        ON sf.snappt_property_id_c = p.id
    LEFT JOIN rds.pg_rds_public.companies c
        ON p.company_id = c.id
        AND c._fivetran_deleted = false
    WHERE (DATE(sf.created_date) = '2026-01-08'
       OR DATE(sf.last_modified_date) >= '2026-01-09')
      AND sf._fivetran_deleted = false
    GROUP BY status
    ORDER BY count DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    total = sum(row[1] for row in results)
    print(f"\nTotal Day 3 synced properties: {total:,}\n")

    for status, count in results:
        pct = 100 * count / total if total > 0 else 0
        symbol = "✅" if status == "CORRECT" else ("❌" if status == "STILL_BROKEN" else "⚠️")
        print(f"  {symbol} {status:<30} {count:>6,} ({pct:>5.1f}%)")

    print()

    # Calculate success metrics
    correct_count = next((row[1] for row in results if row[0] == 'CORRECT'), 0)
    broken_count = next((row[1] for row in results if row[0] == 'STILL_BROKEN'), 0)

    correct_pct = 100 * correct_count / total if total > 0 else 0
    broken_pct = 100 * broken_count / total if total > 0 else 0

    print("="*80)
    if correct_pct >= 95 and broken_pct == 0:
        print("✅ FIX SUCCESSFUL!")
        print(f"   {correct_pct:.1f}% of properties have correct company names")
        print(f"   0% still broken")
    elif broken_pct > 0:
        print("❌ FIX INCOMPLETE")
        print(f"   {broken_pct:.1f}% of properties still have broken company names")
        print("   View fix may not have applied correctly")
        print("   Or Census may not have refreshed data")
    else:
        print("⚠️ PARTIAL SUCCESS")
        print(f"   {correct_pct:.1f}% correct (target: >95%)")
        print("   May need additional investigation")
    print("="*80)
    print()

    # VALIDATION 2: Sample of corrected records
    print("VALIDATION 2: Sample Corrected Records (Before vs After)")
    print("-"*80)

    query_samples = """
    SELECT
        p.name as property_name,
        sf.company_name_c as salesforce_company,
        c.name as rds_company,
        CASE
            WHEN sf.company_name_c = c.name THEN '✅ CORRECT'
            WHEN sf.company_name_c = p.name THEN '❌ BROKEN'
            WHEN sf.company_name_c IS NULL THEN '⚠️ NULL'
            ELSE '❓ OTHER'
        END as status
    FROM crm.salesforce.product_property sf
    INNER JOIN rds.pg_rds_public.properties p
        ON sf.snappt_property_id_c = p.id
    LEFT JOIN rds.pg_rds_public.companies c
        ON p.company_id = c.id
        AND c._fivetran_deleted = false
    WHERE (DATE(sf.created_date) = '2026-01-08'
       OR DATE(sf.last_modified_date) >= '2026-01-09')
      AND sf._fivetran_deleted = false
      AND p.name IN (
          'Hardware',
          'Rowan',
          'Skymor Wesley Chapel',
          'The Storey',
          'South and Twenty',
          'Calista Luxury Townhomes',
          'Fossil Cove',
          'Banner Hill'
      )
    """

    cursor.execute(query_samples)
    samples = cursor.fetchall()

    print(f"\n{'Property Name':<30} {'SF Company':<30} {'Actual Company':<30} {'Status':<15}")
    print("-"*120)

    for prop, sf_comp, rds_comp, status in samples:
        prop_display = (prop[:27] + "...") if prop and len(str(prop)) > 30 else (prop or "NULL")
        sf_display = (sf_comp[:27] + "...") if sf_comp and len(str(sf_comp)) > 30 else (sf_comp or "NULL")
        rds_display = (rds_comp[:27] + "...") if rds_comp and len(str(rds_comp)) > 30 else (rds_comp or "NULL")
        print(f"{str(prop_display):<30} {str(sf_display):<30} {str(rds_display):<30} {status:<15}")

    if not samples:
        print("  No sample records found (may have been excluded from Day 3 syncs)")

    print()

    # VALIDATION 3: NULL company analysis
    print("VALIDATION 3: NULL Company Name Analysis")
    print("-"*80)

    query_nulls = """
    SELECT
        COUNT(*) as total_nulls,
        SUM(CASE WHEN c.name IS NULL THEN 1 ELSE 0 END) as legitimate_nulls,
        SUM(CASE WHEN c.name IS NOT NULL THEN 1 ELSE 0 END) as should_have_company
    FROM crm.salesforce.product_property sf
    INNER JOIN rds.pg_rds_public.properties p
        ON sf.snappt_property_id_c = p.id
    LEFT JOIN rds.pg_rds_public.companies c
        ON p.company_id = c.id
        AND c._fivetran_deleted = false
    WHERE (DATE(sf.created_date) = '2026-01-08'
       OR DATE(sf.last_modified_date) >= '2026-01-09')
      AND sf._fivetran_deleted = false
      AND sf.company_name_c IS NULL
    """

    cursor.execute(query_nulls)
    total_nulls, legitimate, should_have = cursor.fetchall()[0]

    print(f"\nTotal NULL company names in SF: {total_nulls:,}")
    print(f"  Legitimate (no company in RDS): {legitimate:,}")
    print(f"  Should have company (sync issue): {should_have:,}")

    if should_have > 0:
        print(f"\n⚠️  WARNING: {should_have:,} records should have company names but don't")
        print("   This suggests the fix may not have fully propagated")
    else:
        print(f"\n✅ All NULL company names are legitimate")

    print()

    # VALIDATION 4: Before/After comparison
    print("VALIDATION 4: Estimated Before/After Metrics")
    print("-"*80)

    print("\nBefore Fix (estimated from investigation):")
    print(f"  Property name as company: ~6,300 (64%)")
    print(f"  NULL company names: ~3,300 (34%)")
    print(f"  Correct: ~200 (2%)")

    print(f"\nAfter Fix (current):")
    print(f"  Correct: {correct_count:,} ({correct_pct:.1f}%)")
    print(f"  Still broken: {broken_count:,} ({broken_pct:.1f}%)")
    print(f"  NULL (legitimate): {legitimate:,} ({100*legitimate/total:.1f}%)")

    print()

    # FINAL SUMMARY
    print("="*80)
    print("FINAL VALIDATION SUMMARY")
    print("="*80)
    print()

    all_pass = correct_pct >= 95 and broken_pct == 0 and should_have == 0

    if all_pass:
        print("✅ ALL VALIDATIONS PASSED")
        print()
        print("The company name fix has been successfully applied:")
        print(f"  • {correct_pct:.1f}% of properties have correct company names")
        print(f"  • 0% still have broken mappings")
        print(f"  • All NULL values are legitimate")
        print()
        print("Next steps:")
        print("  1. Update stakeholders with success notification")
        print("  2. Document fix in validation report")
        print("  3. Mark todos as complete")
    else:
        print("⚠️ VALIDATION ISSUES FOUND")
        print()
        print("Issues:")
        if correct_pct < 95:
            print(f"  • Only {correct_pct:.1f}% correct (target: >95%)")
        if broken_pct > 0:
            print(f"  • {broken_pct:.1f}% still have property name as company")
        if should_have > 0:
            print(f"  • {should_have:,} records missing company names unexpectedly")
        print()
        print("Recommended actions:")
        print("  1. Verify view fix was applied correctly")
        print("  2. Check if Census refreshed data sources")
        print("  3. Confirm syncs completed without issues")
        print("  4. Consider re-running fix process")

    print()

finally:
    cursor.close()
    connection.close()
