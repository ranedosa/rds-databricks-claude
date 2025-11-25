"""
Create batch files for Census sync (50 records each)
"""
import csv
import os

INPUT_FILE = "/Users/danerosa/rds_databricks_claude/output/sync_payloads/sync_payload_ACTIVE_only_20251121_104454.csv"
OUTPUT_DIR = "/Users/danerosa/rds_databricks_claude/output/sync_payloads"
BATCH_SIZE = 50

print("\n" + "="*80)
print("CREATING BATCH FILES FOR CENSUS SYNC")
print("="*80)

# Read the full file
with open(INPUT_FILE, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    all_rows = list(reader)

total_rows = len(all_rows)
num_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division

print(f"\nInput file: {INPUT_FILE}")
print(f"Total records: {total_rows:,}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Number of batches: {num_batches}")

print(f"\n{'='*80}")
print("CREATING BATCH FILES")
print("="*80)

batch_files = []

for batch_num in range(num_batches):
    start_idx = batch_num * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, total_rows)
    batch_rows = all_rows[start_idx:end_idx]

    # Batch file name
    batch_filename = f"batch_{batch_num+1:03d}_records_{start_idx+1}-{end_idx}.csv"
    batch_filepath = os.path.join(OUTPUT_DIR, batch_filename)

    # Write batch file
    with open(batch_filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(batch_rows)

    batch_files.append(batch_filename)
    print(f"\n{batch_num+1}. Created: {batch_filename}")
    print(f"   Records: {len(batch_rows)} (rows {start_idx+1} to {end_idx})")

print(f"\n{'='*80}")
print("BATCH FILES CREATED")
print("="*80)

print(f"\n✅ Created {len(batch_files)} batch files")
print(f"\nLocation: {OUTPUT_DIR}/")

print(f"\n{'='*80}")
print("SYNC INSTRUCTIONS")
print("="*80)

print("""
How to use these batch files in Census:

METHOD 1: Upload and Sync Each Batch
1. Start with batch_001_records_1-50.csv (test batch)
2. Upload to Census
3. Run sync
4. If successful, continue with batch_002, batch_003, etc.

METHOD 2: Automate with Census API (Advanced)
- Use the Census API to programmatically upload and trigger each batch
- Monitor completion before starting next batch

RECOMMENDED APPROACH:
1. Test with batch_001 first (50 records)
2. If successful, try batch_002 and batch_003
3. If still working, you can increase batch size or continue with all batches
4. Monitor for any failures

VALIDATION after each batch:
- Check Census sync logs
- Verify records appear in product_property_c
- Ensure no Flow errors

""")

# Create a summary file
summary_file = os.path.join(OUTPUT_DIR, "batch_summary.md")
with open(summary_file, 'w') as f:
    f.write("# Batch Files Summary\n\n")
    f.write(f"**Created:** 2025-11-21\n\n")
    f.write(f"**Total Records:** {total_rows:,}\n\n")
    f.write(f"**Batch Size:** {BATCH_SIZE} records\n\n")
    f.write(f"**Number of Batches:** {num_batches}\n\n")
    f.write("## Batch Files\n\n")

    for i, filename in enumerate(batch_files, 1):
        start = (i-1) * BATCH_SIZE + 1
        end = min(i * BATCH_SIZE, total_rows)
        f.write(f"{i}. `{filename}` - Records {start} to {end}\n")

    f.write("\n## Sync Progress Tracker\n\n")
    f.write("Check off each batch as you complete it:\n\n")

    for i, filename in enumerate(batch_files, 1):
        f.write(f"- [ ] Batch {i}: `{filename}`\n")

    f.write("\n## Notes\n\n")
    f.write("- Start with batch_001 as a test\n")
    f.write("- Monitor for Flow errors\n")
    f.write("- If errors occur, reduce batch size further\n")
    f.write("- Validate each batch before continuing\n")

print(f"📝 Created summary file: batch_summary.md")
print(f"\n✅ All batch files ready for Census sync!")
