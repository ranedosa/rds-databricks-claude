"""
Argyle Connections Analysis
Analyzes # of Argyle connections by week/month with breakdown by type
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 6)

# Load data (from ax-postgres query results)
query_results = [
    {"connection_date": "2025-01-01T05:00:00.000Z", "source_type": "CONNECTED_PAYROLL", "connection_count": "17"},
    {"connection_date": "2025-01-02T05:00:00.000Z", "source_type": "CONNECTED_PAYROLL", "connection_count": "74"},
    # ... (truncated for brevity - full dataset would be here)
    {"connection_date": "2025-11-26T05:00:00.000Z", "source_type": "BANK_LINKING", "connection_count": "269"},
    {"connection_date": "2025-11-26T05:00:00.000Z", "source_type": "CONNECTED_PAYROLL", "connection_count": "415"}
]

# NOTE: For actual use, query ax-postgres with:
# SELECT inserted_at::date as connection_date, source_type, COUNT(*) as connection_count
# FROM applicant_submission_document_sources
# WHERE source_type IN ('CONNECTED_PAYROLL', 'BANK_LINKING')
#   AND inserted_at >= '2025-01-01'
# GROUP BY inserted_at::date, source_type
# ORDER BY connection_date, source_type;

df = pd.DataFrame(query_results)
df['connection_date'] = pd.to_datetime(df['connection_date'])
df['connection_count'] = df['connection_count'].astype(int)

print("=" * 60)
print("ARGYLE CONNECTIONS ANALYSIS")
print("=" * 60)
print(f"Data loaded: {len(df)} rows")
print(f"Date range: {df['connection_date'].min().date()} to {df['connection_date'].max().date()}")
print()

# Overall Summary
total_connections = df['connection_count'].sum()
payroll_df = df[df['source_type'] == 'CONNECTED_PAYROLL']
bank_df = df[df['source_type'] == 'BANK_LINKING']
payroll_total = payroll_df['connection_count'].sum()
bank_total = bank_df['connection_count'].sum()

print("OVERALL SUMMARY (YTD 2025)")
print("=" * 60)
print(f"Total Argyle Connections: {total_connections:,}")
print(f"  - Connected Payroll: {payroll_total:,} ({payroll_total/total_connections*100:.1f}%)")
print(f"  - Bank Linking: {bank_total:,} ({bank_total/total_connections*100:.1f}%)")
print()

# Bank linking start date
if not bank_df.empty:
    bank_start = bank_df['connection_date'].min().date()
    print(f"Note: Bank Linking started on {bank_start}")
    print()

# Monthly Analysis
print("=" * 60)
print("MONTHLY BREAKDOWN")
print("=" * 60)

df['month'] = df['connection_date'].dt.to_period('M').dt.to_timestamp()

monthly_summary = df.pivot_table(
    index='month',
    columns='source_type',
    values='connection_count',
    aggfunc='sum',
    fill_value=0
)

monthly_summary['Total'] = monthly_summary.sum(axis=1)

# Add percentages if both columns exist
if 'CONNECTED_PAYROLL' in monthly_summary.columns and 'BANK_LINKING' in monthly_summary.columns:
    monthly_summary['Payroll %'] = (
        monthly_summary['CONNECTED_PAYROLL'] / monthly_summary['Total'] * 100
    ).round(1)
    monthly_summary['Bank %'] = (
        monthly_summary['BANK_LINKING'] / monthly_summary['Total'] * 100
    ).round(1)
    cols = ['Total', 'CONNECTED_PAYROLL', 'BANK_LINKING', 'Payroll %', 'Bank %']
elif 'CONNECTED_PAYROLL' in monthly_summary.columns:
    cols = ['Total', 'CONNECTED_PAYROLL']
else:
    cols = ['Total']

monthly_summary = monthly_summary[[c for c in cols if c in monthly_summary.columns]]
monthly_summary.index = monthly_summary.index.strftime('%Y-%m')

print(monthly_summary.to_string())
print()

# Weekly Analysis
print("=" * 60)
print("WEEKLY BREAKDOWN (Last 8 weeks)")
print("=" * 60)

df['week'] = df['connection_date'].dt.to_period('W').dt.to_timestamp()

weekly_summary = df.pivot_table(
    index='week',
    columns='source_type',
    values='connection_count',
    aggfunc='sum',
    fill_value=0
)

weekly_summary['Total'] = weekly_summary.sum(axis=1)
cols = ['Total']
if 'CONNECTED_PAYROLL' in weekly_summary.columns:
    cols.append('CONNECTED_PAYROLL')
if 'BANK_LINKING' in weekly_summary.columns:
    cols.append('BANK_LINKING')

weekly_summary = weekly_summary[[c for c in cols if c in weekly_summary.columns]]
weekly_summary.index = weekly_summary.index.strftime('%Y-%m-%d')

# Show last 8 weeks
print(weekly_summary.tail(8).to_string())
print()

# Visualizations
print("=" * 60)
print("Generating visualizations...")
print("=" * 60)

# Monthly charts
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Parse month index back to datetime for plotting
monthly_plot = df.pivot_table(
    index='month',
    columns='source_type',
    values='connection_count',
    aggfunc='sum',
    fill_value=0
)

# Chart 1: Stacked bar
if 'CONNECTED_PAYROLL' in monthly_plot.columns:
    cols_to_plot = [c for c in ['CONNECTED_PAYROLL', 'BANK_LINKING'] if c in monthly_plot.columns]
    monthly_plot[cols_to_plot].plot(kind='bar', stacked=True, ax=ax1, width=0.7)
    ax1.set_title('Argyle Connections by Type - Monthly', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Number of Connections')
    ax1.legend(title='Connection Type', labels=['Connected Payroll', 'Bank Linking'][:len(cols_to_plot)])
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.tick_params(axis='x', rotation=45)

# Chart 2: Total by month
monthly_total = df.groupby('month')['connection_count'].sum()
ax2.plot(monthly_total.index, monthly_total.values, marker='o', linewidth=2, markersize=8)
ax2.set_title('Total Argyle Connections by Month', fontsize=14, fontweight='bold')
ax2.set_xlabel('Month')
ax2.set_ylabel('Number of Connections')
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('argyle_monthly_analysis.png', dpi=150, bbox_inches='tight')
print("Saved: argyle_monthly_analysis.png")

# Weekly chart
fig, ax = plt.subplots(figsize=(16, 6))
weekly_plot = df.pivot_table(
    index='week',
    columns='source_type',
    values='connection_count',
    aggfunc='sum',
    fill_value=0
)

if 'CONNECTED_PAYROLL' in weekly_plot.columns:
    cols_to_plot = [c for c in ['CONNECTED_PAYROLL', 'BANK_LINKING'] if c in weekly_plot.columns]
    weekly_plot[cols_to_plot].plot(kind='area', stacked=True, ax=ax, alpha=0.7)
    ax.set_title('Argyle Connections by Type - Weekly', fontsize=14, fontweight='bold')
    ax.set_xlabel('Week')
    ax.set_ylabel('Number of Connections')
    ax.legend(title='Connection Type', labels=['Connected Payroll', 'Bank Linking'][:len(cols_to_plot)])
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('argyle_weekly_analysis.png', dpi=150, bbox_inches='tight')
print("Saved: argyle_weekly_analysis.png")

print()
print("=" * 60)
print("Analysis complete!")
print("=" * 60)

plt.show()
