"""
Master Script - Configure Both Census Syncs A & B
Runs all configuration scripts in sequence
"""
import subprocess
import sys
import os

SCRIPTS_DIR = "/Users/danerosa/rds_databricks_claude/20260105"

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print("\n" + "="*80)
    print(f"RUNNING: {description}")
    print("="*80)

    script_path = os.path.join(SCRIPTS_DIR, script_name)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )

        print(result.stdout)

        if result.returncode == 0:
            print(f"\n✅ {description} completed successfully")
            return True
        else:
            print(f"\n❌ {description} failed")
            print(result.stderr)
            return False

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running {description}")
        print(e.stdout)
        print(e.stderr)
        return False

def main():
    """Main function"""
    print("\n" + "="*80 * 2)
    print("CENSUS CONFIGURATION - MASTER SCRIPT")
    print("Configuring Sync A (CREATE) and Sync B (UPDATE)")
    print("="*80 * 2)

    scripts = [
        ("census_api_setup.py", "Step 1: Get Census Connection IDs"),
        ("configure_sync_a_create.py", "Step 2: Configure Sync A (CREATE)"),
        ("configure_sync_b_update.py", "Step 3: Configure Sync B (UPDATE)")
    ]

    success_count = 0

    for script, description in scripts:
        if run_script(script, description):
            success_count += 1
        else:
            print(f"\n❌ Stopping - {description} failed")
            sys.exit(1)

    # Summary
    print("\n" + "="*80 * 2)
    print("CONFIGURATION COMPLETE")
    print("="*80 * 2)

    print(f"\n✅ Successfully configured {success_count}/{len(scripts)} scripts")

    # Read sync IDs
    try:
        with open(os.path.join(SCRIPTS_DIR, 'sync_a_id.txt'), 'r') as f:
            sync_a_id = f.read().strip()
        with open(os.path.join(SCRIPTS_DIR, 'sync_b_id.txt'), 'r') as f:
            sync_b_id = f.read().strip()

        print(f"\n📊 Sync A (CREATE) ID: {sync_a_id}")
        print(f"   View: https://app.getcensus.com/syncs/{sync_a_id}")

        print(f"\n📊 Sync B (UPDATE) ID: {sync_b_id}")
        print(f"   View: https://app.getcensus.com/syncs/{sync_b_id}")

    except FileNotFoundError:
        print(f"\n⚠️  Sync IDs not found (check for errors above)")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print(f"\n1. Review both syncs in Census UI")
    print(f"2. Verify field mappings are correct")
    print(f"3. Run: python run_pilot_syncs.py")
    print(f"4. Validate results in Salesforce")

if __name__ == "__main__":
    main()
