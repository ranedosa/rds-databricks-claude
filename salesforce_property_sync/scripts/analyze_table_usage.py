# Databricks notebook source
# MAGIC %md
# MAGIC ## Top 50 Most Used Tables in Databricks
# MAGIC
# MAGIC This notebook analyzes query history to identify the most frequently accessed tables.
# MAGIC We'll use the system.query.history table to determine usage patterns.

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import datetime, timedelta

# Define analysis period (last 90 days for comprehensive view)
days_back = 90
start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

print(f"Analyzing table usage from {start_date} to present ({days_back} days)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Query System Tables for Table Access Patterns

# COMMAND ----------

# Query the system.query.history table
# This contains metadata about all queries run in the workspace
query_history_sql = f"""
SELECT
    statement_text,
    statement_type,
    executed_by,
    start_time,
    execution_status
FROM system.query.history
WHERE start_time >= '{start_date}'
    AND execution_status = 'FINISHED'
    AND statement_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE_TABLE_AS_SELECT')
"""

query_history = spark.sql(query_history_sql)

print(f"Total queries analyzed: {query_history.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Extract Table Names from Queries

# COMMAND ----------

# Extract table references from SQL statements
# This uses regex to find patterns like: catalog.schema.table or schema.table
import re

def extract_tables(statement):
    """Extract table references from SQL statement"""
    if not statement:
        return []

    # Common patterns for table references
    patterns = [
        r'\bFROM\s+([`"]?)(\w+\.?\w*\.?\w+)\1',
        r'\bJOIN\s+([`"]?)(\w+\.?\w*\.?\w+)\1',
        r'\bINTO\s+([`"]?)(\w+\.?\w*\.?\w+)\1',
        r'\bUPDATE\s+([`"]?)(\w+\.?\w*\.?\w+)\1',
        r'\bTABLE\s+([`"]?)(\w+\.?\w*\.?\w+)\1',
    ]

    tables = []
    statement_upper = statement.upper()

    for pattern in patterns:
        matches = re.finditer(pattern, statement_upper)
        for match in matches:
            table_name = match.group(2)
            # Filter out common SQL keywords that might be captured
            if table_name and table_name not in ['SELECT', 'WHERE', 'GROUP', 'ORDER', 'HAVING']:
                tables.append(table_name.lower())

    return list(set(tables))

# Register UDF
from pyspark.sql.types import ArrayType, StringType
extract_tables_udf = F.udf(extract_tables, ArrayType(StringType()))

# Apply to query history
queries_with_tables = query_history.withColumn(
    "tables_accessed",
    extract_tables_udf(F.col("statement_text"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Calculate Table Usage Metrics

# COMMAND ----------

# Explode tables to get one row per table access
table_usage = queries_with_tables.select(
    F.explode("tables_accessed").alias("table_name"),
    "executed_by",
    "start_time",
    "statement_type"
)

# Calculate aggregated metrics
table_metrics = table_usage.groupBy("table_name").agg(
    F.count("*").alias("total_queries"),
    F.countDistinct("executed_by").alias("unique_users"),
    F.min("start_time").alias("first_access"),
    F.max("start_time").alias("last_access"),
    F.count(F.when(F.col("statement_type") == "SELECT", 1)).alias("read_queries"),
    F.count(F.when(F.col("statement_type").isin(["INSERT", "UPDATE", "DELETE", "MERGE"]), 1)).alias("write_queries")
).orderBy(F.col("total_queries").desc())

# COMMAND ----------

# MAGIC %md
# MAGIC ### Top 50 Most Used Tables

# COMMAND ----------

# Get top 50 tables
top_50_tables = table_metrics.limit(50)

# Display results
display(top_50_tables)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Export Results to CSV

# COMMAND ----------

# Convert to Pandas for easy viewing and export
top_50_df = top_50_tables.toPandas()

# Add calculated columns for better insights
top_50_df['avg_queries_per_day'] = (top_50_df['total_queries'] / days_back).round(2)
top_50_df['read_write_ratio'] = (top_50_df['read_queries'] / (top_50_df['write_queries'] + 1)).round(2)
top_50_df['days_since_last_access'] = (
    (datetime.now() - top_50_df['last_access']).dt.total_seconds() / 86400
).round(1)

# Display summary
print(f"\n{'='*80}")
print(f"TOP 50 MOST USED TABLES (Last {days_back} days)")
print(f"{'='*80}\n")
print(top_50_df.to_string(index=False))

# Save to CSV
output_path = f"/dbfs/FileStore/table_usage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
top_50_df.to_csv(output_path, index=False)
print(f"\n\nResults saved to: {output_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Identify Potential Fivetran Tables

# COMMAND ----------

# Look for tables that might be from Fivetran (common naming patterns)
# Fivetran often uses specific schemas or prefixes
fivetran_patterns = ['fivetran', 'source', 'raw', 'staging', 'stg_', 'src_']

top_50_df['likely_fivetran'] = top_50_df['table_name'].apply(
    lambda x: any(pattern in x.lower() for pattern in fivetran_patterns)
)

fivetran_candidates = top_50_df[top_50_df['likely_fivetran'] == True]

print(f"\n{'='*80}")
print(f"POTENTIAL FIVETRAN-SOURCED TABLES IN TOP 50")
print(f"{'='*80}\n")

if len(fivetran_candidates) > 0:
    print(fivetran_candidates[['table_name', 'total_queries', 'unique_users', 'avg_queries_per_day']].to_string(index=False))
    print(f"\nFound {len(fivetran_candidates)} potential Fivetran tables in top 50")
else:
    print("No obvious Fivetran-sourced tables detected based on naming patterns.")
    print("You may need to manually identify which tables are sourced from PostgreSQL via Fivetran.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Alternative: Query Unity Catalog Directly

# COMMAND ----------

# If system.query.history doesn't have enough data, query Unity Catalog for table metadata
try:
    unity_catalog_sql = """
    SELECT
        table_catalog,
        table_schema,
        table_name,
        CONCAT(table_catalog, '.', table_schema, '.', table_name) as full_table_name,
        table_type,
        comment
    FROM system.information_schema.tables
    WHERE table_type = 'MANAGED'
       OR table_type = 'EXTERNAL'
    ORDER BY table_schema, table_name
    """

    all_tables = spark.sql(unity_catalog_sql)

    print(f"\nTotal tables in Unity Catalog: {all_tables.count():,}")
    print("\nSample of available tables:")
    display(all_tables.limit(20))

except Exception as e:
    print(f"Could not query Unity Catalog: {e}")
