# Databricks notebook source
# MAGIC %md
# MAGIC ## Top 50 Most Used Tables in RDS Catalog
# MAGIC
# MAGIC This notebook analyzes query history to identify the most frequently accessed tables
# MAGIC specifically within the **rds** catalog.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, ArrayType
from datetime import datetime, timedelta
import re

# COMMAND ----------

# Define analysis period
days_back = 90
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

print(f"Analyzing RDS catalog table usage from {start_date} to present ({days_back} days)")

# COMMAND ----------

# Query system.query.history for queries accessing rds catalog
query_history = spark.sql(f"""
    SELECT
        statement_text,
        executed_by,
        start_time,
        statement_type
    FROM system.query.history
    WHERE start_time >= '{start_date}'
        AND execution_status = 'FINISHED'
        AND statement_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE_TABLE_AS_SELECT')
        AND LOWER(statement_text) LIKE '%rds.%'
""")

total_queries = query_history.count()
print(f"Total queries referencing 'rds' catalog: {total_queries:,}")

# COMMAND ----------

# Function to extract table names from SQL statements
def extract_rds_tables(statement):
    """Extract rds.schema.table references from SQL statement"""
    if not statement:
        return []

    # Pattern to match rds.schema.table (with or without backticks/quotes)
    pattern = r'(?:from|join|into|update|table)\s+[`"]?rds\.(\w+)\.(\w+)[`"]?'

    matches = re.findall(pattern, statement.lower(), re.IGNORECASE)

    # Return full table names
    tables = [f"rds.{schema}.{table}" for schema, table in matches]

    return list(set(tables))

# Register UDF
extract_tables_udf = F.udf(extract_rds_tables, ArrayType(StringType()))

# COMMAND ----------

# Apply UDF to extract tables
queries_with_tables = query_history.withColumn(
    "rds_tables",
    extract_tables_udf(F.col("statement_text"))
)

# Filter to only queries that actually reference rds tables
queries_with_rds = queries_with_tables.filter(F.size("rds_tables") > 0)

print(f"Queries with extractable rds tables: {queries_with_rds.count():,}")

# COMMAND ----------

# Explode to get one row per table access
table_usage = queries_with_rds.select(
    F.explode("rds_tables").alias("table_name"),
    "executed_by",
    "start_time",
    "statement_type"
)

# COMMAND ----------

# Calculate usage metrics
table_metrics = table_usage.groupBy("table_name").agg(
    F.count("*").alias("total_queries"),
    F.countDistinct("executed_by").alias("unique_users"),
    F.min("start_time").alias("first_access"),
    F.max("start_time").alias("last_access"),
    F.sum(F.when(F.col("statement_type") == "SELECT", 1).otherwise(0)).alias("read_queries"),
    F.sum(F.when(F.col("statement_type").isin(["INSERT", "UPDATE", "DELETE", "MERGE"]), 1).otherwise(0)).alias("write_queries")
)

# Add calculated fields
table_metrics_enhanced = table_metrics.withColumn(
    "avg_queries_per_day",
    F.round(F.col("total_queries") / days_back, 2)
).withColumn(
    "days_since_last_access",
    F.datediff(F.current_date(), F.col("last_access"))
).withColumn(
    "read_percentage",
    F.round(F.col("read_queries") * 100.0 / F.col("total_queries"), 1)
)

# COMMAND ----------

# Get top 50 tables
top_50_rds_tables = table_metrics_enhanced.orderBy(F.col("total_queries").desc()).limit(50)

print(f"\n{'='*100}")
print(f"TOP 50 MOST USED TABLES IN RDS CATALOG (Last {days_back} days)")
print(f"{'='*100}\n")

# Display results
display(top_50_rds_tables)

# COMMAND ----------

# Convert to Pandas for detailed viewing and export
top_50_df = top_50_rds_tables.toPandas()

# Display formatted summary
print(f"\n{'='*100}")
print(f"DETAILED TABLE USAGE REPORT")
print(f"{'='*100}\n")

for idx, row in top_50_df.iterrows():
    print(f"{idx + 1}. {row['table_name']}")
    print(f"   Total Queries: {row['total_queries']:,} | Users: {row['unique_users']} | Avg/Day: {row['avg_queries_per_day']}")
    print(f"   Read: {row['read_queries']:,} ({row['read_percentage']}%) | Write: {row['write_queries']:,}")
    print(f"   Last Access: {row['days_since_last_access']} days ago\n")

# COMMAND ----------

# Save to CSV
output_path = f"/dbfs/FileStore/rds_catalog_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
top_50_df.to_csv(output_path, index=False)

print(f"\nResults saved to: {output_path}")
print(f"Download URL: https://<your-workspace>.cloud.databricks.com/files{output_path.replace('/dbfs', '')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Additional Analysis: Schema Breakdown

# COMMAND ----------

# Extract schema from table names
top_50_df['schema'] = top_50_df['table_name'].str.split('.').str[1]

schema_summary = top_50_df.groupby('schema').agg({
    'total_queries': 'sum',
    'table_name': 'count'
}).rename(columns={'table_name': 'table_count'}).sort_values('total_queries', ascending=False)

print(f"\n{'='*80}")
print(f"SCHEMA USAGE SUMMARY")
print(f"{'='*80}\n")
print(schema_summary.to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## List All Tables in RDS Catalog (from Unity Catalog Metadata)

# COMMAND ----------

# Query Unity Catalog for all rds tables
try:
    all_rds_tables = spark.sql("""
        SELECT
            table_catalog,
            table_schema,
            table_name,
            table_type,
            CONCAT(table_catalog, '.', table_schema, '.', table_name) as full_table_name
        FROM system.information_schema.tables
        WHERE table_catalog = 'rds'
            AND table_type IN ('MANAGED', 'EXTERNAL')
        ORDER BY table_schema, table_name
    """)

    total_rds_tables = all_rds_tables.count()
    print(f"\nTotal tables in RDS catalog: {total_rds_tables:,}")

    # Show which tables from rds catalog are NOT in the top 50 used
    all_rds_list = [row['full_table_name'] for row in all_rds_tables.select('full_table_name').collect()]
    top_50_list = top_50_df['table_name'].tolist()

    unused_or_rare = [t for t in all_rds_list if t not in top_50_list]

    print(f"\nTables in RDS catalog NOT in top 50 most used: {len(unused_or_rare)}")
    if len(unused_or_rare) > 0:
        print("\nSample of rarely used tables:")
        for table in unused_or_rare[:10]:
            print(f"  - {table}")

    # Display all rds tables
    print(f"\n{'='*80}")
    print("ALL TABLES IN RDS CATALOG")
    print(f"{'='*80}\n")
    display(all_rds_tables)

except Exception as e:
    print(f"Could not query Unity Catalog: {e}")
    print("Note: Ensure you have permissions to query system.information_schema.tables")
