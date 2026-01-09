#!/usr/bin/env python3
"""
Helper script to save Census Sync IDs after manual creation
Run this after creating syncs in Census UI
"""

def main():
    print("\n" + "="*80)
    print("SAVE CENSUS SYNC IDs")
    print("="*80)

    print("\nAfter creating syncs in Census UI, enter the Sync IDs below.")
    print("(Find them in the URL: https://app.getcensus.com/syncs/XXXXXXX)")

    # Get Sync A ID
    print("\n" + "-"*80)
    sync_a_id = input("Enter Sync A (CREATE) ID: ").strip()

    if sync_a_id:
        with open('/Users/danerosa/rds_databricks_claude/20260105/sync_a_id.txt', 'w') as f:
            f.write(sync_a_id)
        print(f"✅ Saved Sync A ID: {sync_a_id}")
    else:
        print("⚠️  No Sync A ID entered")

    # Get Sync B ID
    print("\n" + "-"*80)
    sync_b_id = input("Enter Sync B (UPDATE) ID: ").strip()

    if sync_b_id:
        with open('/Users/danerosa/rds_databricks_claude/20260105/sync_b_id.txt', 'w') as f:
            f.write(sync_b_id)
        print(f"✅ Saved Sync B ID: {sync_b_id}")
    else:
        print("⚠️  No Sync B ID entered")

    # Summary
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)

    if sync_a_id and sync_b_id:
        print(f"\n✅ Both sync IDs saved successfully!")
        print(f"\nSync A (CREATE): {sync_a_id}")
        print(f"   View: https://app.getcensus.com/syncs/{sync_a_id}")
        print(f"\nSync B (UPDATE): {sync_b_id}")
        print(f"   View: https://app.getcensus.com/syncs/{sync_b_id}")
        print(f"\n📋 Run pilot tests:")
        print(f"   python3 run_pilot_syncs.py")
    else:
        print(f"\n⚠️  Please create both syncs and run this script again")

if __name__ == "__main__":
    main()
