"""
Split feature backfill CSV into 50-record batches to avoid Salesforce Flow limits
"""
import csv
import os

input_file = "/Users/danerosa/rds_databricks_claude/output/sync_payloads/feature_backfill_20251121.csv"
output_dir = "/Users/danerosa/rds_databricks_claude/output/sync_payloads/feature_backfill_batches"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

print("\n" + "="*80)
print("CREATING FEATURE BACKFILL BATCH FILES")
print("="*80)

# Read the CSV
with open(input_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

total_records = len(rows)
batch_size = 50
num_batches = (total_records + batch_size - 1) // batch_size  # Ceiling division

print(f"\nTotal records: {total_records:,}")
print(f"Batch size: {batch_size}")
print(f"Number of batches: {num_batches}")
print(f"\nCreating batch files in: {output_dir}\n")

# Create batch files
for i in range(num_batches):
    start_idx = i * batch_size
    end_idx = min((i + 1) * batch_size, total_records)
    batch_rows = rows[start_idx:end_idx]

    batch_num = i + 1
    start_record = start_idx + 1
    end_record = end_idx

    filename = f"feature_backfill_batch_{batch_num:03d}_records_{start_record}-{end_record}.csv"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(batch_rows)

    print(f"✅ Created: {filename} ({len(batch_rows)} records)")

print("\n" + "="*80)
print("BATCH FILES CREATED SUCCESSFULLY")
print("="*80)
print(f"""
Total files created: {num_batches}
Location: {output_dir}

NEXT STEPS:
1. Upload batch files to Census one at a time OR all at once
2. Configure as UPDATE operation with Reverse_ETL_ID__c as sync key
3. Run batches sequentially to avoid Flow governor limits
4. Monitor progress through Census

This will update all {total_records:,} properties with correct feature data!
""")
