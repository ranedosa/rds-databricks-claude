#!/usr/bin/env python3
"""
Investigate 524 records with missing key fields
"""
import os
from databricks import sql

host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")
connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/95a8f5979c3f8740",
    access_token=os.getenv("DATABRICKS_TOKEN")
)
cursor = connection.cursor()

try:
    print("="*80)
    print("INVESTIGATING 524 RECORDS WITH MISSING KEY FIELDS")
    print("="*80)
    print()

    # STEP 1: Break down by which fields are missing
    print("STEP 1: Identify which specific fields are missing")
    print("-"*80)

    query = """
    SELECT
        CASE
            WHEN snappt_property_id_c IS NULL AND name IS NULL AND company_name_c IS NULL THEN 'all_three_missing'
            WHEN snappt_property_id_c IS NULL AND name IS NULL THEN 'snappt_id_and_name_missing'
            WHEN snappt_property_id_c IS NULL AND company_name_c IS NULL THEN 'snappt_id_and_company_missing'
            WHEN name IS NULL AND company_name_c IS NULL THEN 'name_and_company_missing'
            WHEN snappt_property_id_c IS NULL THEN 'only_snappt_id_missing'
            WHEN name IS NULL THEN 'only_name_missing'
            WHEN company_name_c IS NULL THEN 'only_company_missing'
            ELSE 'other'
        END as missing_pattern,
        COUNT(*) as count
    FROM crm.salesforce.product_property
    WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
      AND _fivetran_deleted = false
      AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
    GROUP BY missing_pattern
    ORDER BY count DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    print(f"\nMissing Field Patterns:")
    total = sum(row[1] for row in results)
    for pattern, count in results:
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {pattern:<35} {count:>5} ({pct:>5.1f}%)")
    print(f"  {'TOTAL':<35} {total:>5}")
    print()

    # STEP 2: Break down by Sync A (creates) vs Sync B (updates)
    print("STEP 2: Determine if issues are from Sync A or Sync B")
    print("-"*80)

    query_sync_breakdown = """
    SELECT
        CASE
            WHEN DATE(created_date) = '2026-01-08' THEN 'Sync_A_Creates_Jan8'
            WHEN DATE(last_modified_date) = '2026-01-09' AND DATE(created_date) != '2026-01-09' THEN 'Sync_B_Updates_Jan9'
            ELSE 'Other'
        END as sync_source,
        COUNT(*) as count
    FROM crm.salesforce.product_property
    WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
      AND _fivetran_deleted = false
      AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
    GROUP BY sync_source
    ORDER BY count DESC
    """

    cursor.execute(query_sync_breakdown)
    sync_results = cursor.fetchall()

    print(f"\nIssues by Sync Source:")
    for source, count in sync_results:
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {source:<30} {count:>5} ({pct:>5.1f}%)")
    print()

    # STEP 3: Sample records with missing fields
    print("STEP 3: Sample records with missing fields")
    print("-"*80)

    query_samples = """
    SELECT
        id,
        name,
        snappt_property_id_c,
        company_name_c,
        short_id_c,
        sf_property_id_c,
        created_date,
        last_modified_date,
        CASE
            WHEN DATE(created_date) = '2026-01-08' THEN 'Sync_A'
            WHEN DATE(last_modified_date) = '2026-01-09' THEN 'Sync_B'
            ELSE 'Other'
        END as source
    FROM crm.salesforce.product_property
    WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
      AND _fivetran_deleted = false
      AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
    LIMIT 20
    """

    cursor.execute(query_samples)
    samples = cursor.fetchall()

    print(f"\nSample Records (first 20):")
    print(f"{'Source':<8} {'Name':<30} {'Snappt_ID':<38} {'Company':<30}")
    print("-"*120)
    for row in samples:
        sf_id, name, snappt_id, company, short_id, sf_prop_id, created, modified, source = row
        name_display = (name[:27] + "...") if name and len(str(name)) > 30 else (name or "NULL")
        snappt_display = (snappt_id[:35] + "...") if snappt_id and len(str(snappt_id)) > 38 else (snappt_id or "NULL")
        company_display = (company[:27] + "...") if company and len(str(company)) > 30 else (company or "NULL")
        print(f"{source:<8} {str(name_display):<30} {str(snappt_display):<38} {str(company_display):<30}")
    print()

    # STEP 4: Check if sf_property_id_c is populated for these records
    print("STEP 4: Check if other identifying fields are populated")
    print("-"*80)

    query_other_fields = """
    SELECT
        SUM(CASE WHEN sf_property_id_c IS NOT NULL THEN 1 ELSE 0 END) as has_sf_property_id,
        SUM(CASE WHEN short_id_c IS NOT NULL THEN 1 ELSE 0 END) as has_short_id,
        SUM(CASE WHEN reverse_etl_id_c IS NOT NULL THEN 1 ELSE 0 END) as has_reverse_etl_id,
        COUNT(*) as total
    FROM crm.salesforce.product_property
    WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
      AND _fivetran_deleted = false
      AND (snappt_property_id_c IS NULL OR name IS NULL OR company_name_c IS NULL)
    """

    cursor.execute(query_other_fields)
    other_fields = cursor.fetchall()[0]
    has_sf_id, has_short_id, has_reverse_etl, total = other_fields

    print(f"\nOther identifying fields present:")
    print(f"  Records with sf_property_id_c:  {has_sf_id:>5} ({100*has_sf_id/total:.1f}%)")
    print(f"  Records with short_id_c:        {has_short_id:>5} ({100*has_short_id/total:.1f}%)")
    print(f"  Records with reverse_etl_id_c:  {has_reverse_etl:>5} ({100*has_reverse_etl/total:.1f}%)")
    print()

    # STEP 5: Check source views to see if nulls exist there
    print("STEP 5: Check if nulls exist in Census source views")
    print("-"*80)

    # Check properties_to_create view
    query_create_view = """
    SELECT
        SUM(CASE WHEN rds_property_id IS NULL THEN 1 ELSE 0 END) as null_rds_id,
        SUM(CASE WHEN property_name IS NULL THEN 1 ELSE 0 END) as null_name,
        SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as null_company,
        COUNT(*) as total
    FROM crm.sfdc_dbx.properties_to_create
    """

    try:
        cursor.execute(query_create_view)
        create_view_results = cursor.fetchall()[0]
        null_id, null_name, null_company, view_total = create_view_results

        print(f"\nproperties_to_create view (Sync A source):")
        print(f"  Total records: {view_total}")
        print(f"  NULL rds_property_id: {null_id}")
        print(f"  NULL property_name:   {null_name}")
        print(f"  NULL company_name:    {null_company}")
    except Exception as e:
        print(f"\n⚠️  Could not query properties_to_create: {e}")

    # Check properties_to_update view
    query_update_view = """
    SELECT
        SUM(CASE WHEN rds_property_id IS NULL THEN 1 ELSE 0 END) as null_rds_id,
        SUM(CASE WHEN property_name IS NULL THEN 1 ELSE 0 END) as null_name,
        SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as null_company,
        COUNT(*) as total
    FROM crm.sfdc_dbx.properties_to_update
    """

    try:
        cursor.execute(query_update_view)
        update_view_results = cursor.fetchall()[0]
        null_id, null_name, null_company, view_total = update_view_results

        print(f"\nproperties_to_update view (Sync B source):")
        print(f"  Total records: {view_total}")
        print(f"  NULL rds_property_id: {null_id}")
        print(f"  NULL property_name:   {null_name}")
        print(f"  NULL company_name:    {null_company}")
    except Exception as e:
        print(f"\n⚠️  Could not query properties_to_update: {e}")

    print()

    # STEP 6: Check RDS source for one sample record
    print("STEP 6: Compare sample record to RDS source")
    print("-"*80)

    # Get one record with issues and check RDS
    query_sample_with_id = """
    SELECT
        snappt_property_id_c,
        name,
        company_name_c
    FROM crm.salesforce.product_property
    WHERE (DATE(created_date) = '2026-01-08' OR DATE(last_modified_date) = '2026-01-09')
      AND _fivetran_deleted = false
      AND snappt_property_id_c IS NOT NULL
      AND (name IS NULL OR company_name_c IS NULL)
    LIMIT 1
    """

    cursor.execute(query_sample_with_id)
    sample = cursor.fetchall()

    if sample:
        sample_id = sample[0][0]
        print(f"\nSample record in Salesforce:")
        print(f"  snappt_property_id_c: {sample[0][0]}")
        print(f"  name:                 {sample[0][1] or 'NULL'}")
        print(f"  company_name_c:       {sample[0][2] or 'NULL'}")

        # Check RDS for this property
        query_rds = f"""
        SELECT
            p.property_id,
            p.name,
            c.name as company_name
        FROM rds.pg_rds_public.properties p
        LEFT JOIN rds.pg_rds_public.companies c ON p.company_id = c.company_id
        WHERE p.property_id = '{sample_id}'
          AND p._fivetran_deleted = false
        """

        try:
            cursor.execute(query_rds)
            rds_results = cursor.fetchall()

            if rds_results:
                print(f"\nSame record in RDS source:")
                print(f"  property_id:    {rds_results[0][0]}")
                print(f"  name:           {rds_results[0][1] or 'NULL'}")
                print(f"  company_name:   {rds_results[0][2] or 'NULL'}")
                print(f"\n✓ Record exists in RDS")

                # Compare
                if rds_results[0][1] is None:
                    print(f"  ⚠️  name is also NULL in RDS source")
                if rds_results[0][2] is None:
                    print(f"  ⚠️  company_name is also NULL in RDS source")
            else:
                print(f"\n⚠️  Record NOT found in RDS source")
        except Exception as e:
            print(f"\n⚠️  Could not query RDS: {e}")
    else:
        print("\n⚠️  No sample records found with snappt_property_id_c to check")

    print()

    # FINAL SUMMARY
    print("="*80)
    print("SUMMARY & ROOT CAUSE ANALYSIS")
    print("="*80)
    print()
    print(f"Total records with missing fields: {total}")
    print()
    print("Key Findings:")
    print("-"*80)

    for source, count in sync_results:
        pct = (count / total * 100) if total > 0 else 0
        print(f"  • {source}: {count} records ({pct:.1f}%)")

    print()
    print("Most common missing pattern:")
    if results:
        top_pattern, top_count = results[0]
        print(f"  • {top_pattern}: {top_count} records")

    print()
    print("Next Steps:")
    print("-"*80)
    print("  1. Review sample records above")
    print("  2. Check if RDS source data also has nulls")
    print("  3. Determine if these are:")
    print("     a) Legitimate missing data (fix in RDS)")
    print("     b) Sync errors (re-run sync)")
    print("     c) Expected edge cases (document)")
    print()

finally:
    cursor.close()
    connection.close()
