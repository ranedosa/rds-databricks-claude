# Databricks notebook source
# MAGIC %md
# MAGIC # Active Properties Analysis - Refined Count
# MAGIC
# MAGIC ## Objective
# MAGIC Count active properties, companies, and units while excluding:
# MAGIC - IDV Only properties (duplicates)
# MAGIC - Partner properties not listed in Customer Log
# MAGIC - Test/demo properties
# MAGIC - Phased buildings (e.g., "Phase 1", "Phase 2")
# MAGIC
# MAGIC ## Data Sources
# MAGIC - **Properties Table**: `rds.pg_rds_public.properties`
# MAGIC - **Customer Log**: Uploaded CSV file with onboarded properties

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Load Customer Log CSV
# MAGIC Upload the CSV file to DBFS or use it from a mounted location

# COMMAND ----------

# Load the Customer Log CSV
# NOTE: Update this path to where you upload the CSV file in DBFS
customer_log_df = spark.read.csv(
    "/FileStore/tables/Snappt_Customer_Log_Customer_Log_Onboarded.csv",
    header=True,
    inferSchema=True
)

# Clean up column names (remove leading/trailing spaces)
from pyspark.sql.functions import col, trim, upper, regexp_replace

customer_log_df = customer_log_df.select([
    col(c).alias(c.strip()) for c in customer_log_df.columns
])

# Display sample
display(customer_log_df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create a clean customer properties list
# MAGIC Filter for Live properties only and extract Salesforce IDs

# COMMAND ----------

from pyspark.sql.functions import lower, regexp_replace

# Get clean list of customer properties with SFDC IDs
customer_properties = customer_log_df.filter(
    col("Status") == "Live"
).select(
    trim(col("Property Name")).alias("customer_property_name"),
    trim(col("SFDC Property ID")).alias("sfdc_property_id")
).filter(
    # Only keep records with valid SFDC IDs
    col("sfdc_property_id").isNotNull() & (col("sfdc_property_id") != "")
).distinct()

print(f"Total Live Customer Properties with SFDC ID: {customer_properties.count()}")
display(customer_properties.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Load and prepare properties from RDS
# MAGIC Including property_features to identify IDV-only properties

# COMMAND ----------

# Load properties table with sfdc_id and IDV feature flag
properties_df = spark.sql("""
    SELECT
        p.id,
        p.name,
        p.company_id,
        p.unit,
        p.status,
        p.sfdc_id,
        p.created_at,
        p.updated_at,
        p.identity_verification_enabled,
        -- Check if property has IDV-only feature enabled
        MAX(CASE WHEN pf.feature_code LIKE '%idv%'
                   OR pf.feature_code LIKE '%identity_verification%'
                 THEN 1 ELSE 0 END) as is_idv_only
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf
        ON pf.property_id = p.id
        AND pf.state = 'enabled'
    WHERE p.status = 'ACTIVE'
    GROUP BY p.id, p.name, p.company_id, p.unit, p.status, p.sfdc_id,
             p.created_at, p.updated_at, p.identity_verification_enabled
""")

print(f"Total Active Properties in RDS: {properties_df.count()}")
print(f"Properties with SFDC ID: {properties_df.filter(col('sfdc_id').isNotNull()).count()}")
print(f"IDV-only Properties: {properties_df.filter(col('is_idv_only') == 1).count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Apply Exclusions

# COMMAND ----------

from pyspark.sql.functions import when, lit

# Join with customer log using SFDC ID (most reliable)
properties_with_customer = properties_df.join(
    customer_properties,
    properties_df.sfdc_id == customer_properties.sfdc_property_id,
    "inner"  # Inner join ensures only properties in Customer Log are included
)

print(f"Properties matched with Customer Log: {properties_with_customer.count()}")

# Apply additional exclusion filters
filtered_properties = properties_with_customer.filter(
    # Exclude IDV Only properties (using property_features table)
    (col("is_idv_only") == 0) &

    # Exclude test/demo properties (name pattern based)
    ~lower(col("name")).contains("test") &
    ~lower(col("name")).contains("demo") &
    ~lower(col("name")).contains("sample") &

    # Exclude phased buildings (name pattern based)
    ~lower(col("name")).contains("phase 1") &
    ~lower(col("name")).contains("phase 2") &
    ~lower(col("name")).contains("phase 3") &
    ~lower(col("name")).rlike("phase\\s*[0-9]")
)

print(f"Properties after all exclusions: {filtered_properties.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Calculate Final Metrics

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create temp view for SQL analysis
# MAGIC CREATE OR REPLACE TEMP VIEW filtered_properties_view AS
# MAGIC SELECT * FROM filtered_properties

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Final counts
# MAGIC SELECT
# MAGIC     COUNT(DISTINCT id) as active_properties,
# MAGIC     COUNT(DISTINCT company_id) as companies_with_active_properties,
# MAGIC     SUM(unit) as total_units
# MAGIC FROM filtered_properties_view

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Comparison with Original Query

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original query (for comparison)
# MAGIC SELECT
# MAGIC     'Original (No Filters)' as query_type,
# MAGIC     COUNT(DISTINCT p.id) as active_properties,
# MAGIC     COUNT(DISTINCT p.company_id) as companies_with_active_properties,
# MAGIC     SUM(p.unit) as total_units
# MAGIC FROM rds.pg_rds_public.properties p
# MAGIC WHERE p.status = 'ACTIVE'
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT
# MAGIC     'Filtered (Excluding IDV/Test/Phased/Non-Customer)' as query_type,
# MAGIC     COUNT(DISTINCT id) as active_properties,
# MAGIC     COUNT(DISTINCT company_id) as companies_with_active_properties,
# MAGIC     SUM(unit) as total_units
# MAGIC FROM filtered_properties_view

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Detailed Analysis - What Was Excluded?

# COMMAND ----------

# Show properties that were excluded
excluded_properties = properties_df.join(
    filtered_properties.select("id"),
    "id",
    "left_anti"
)

# Categorize exclusions
excluded_with_reason = excluded_properties.withColumn(
    "exclusion_reason",
    when(col("is_idv_only") == 1, "IDV Only (from property_features)")
    .when(lower(col("name")).contains("test") | lower(col("name")).contains("demo") | lower(col("name")).contains("sample"), "Test/Demo")
    .when(lower(col("name")).rlike("phase\\s*[0-9]"), "Phased Building")
    .otherwise("Not in Customer Log")
)

# Summary of exclusions
print("Exclusion Summary:")
excluded_with_reason.groupBy("exclusion_reason").count().orderBy(col("count").desc()).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Export Results

# COMMAND ----------

# Get final results
final_results = spark.sql("""
    SELECT
        COUNT(DISTINCT id) as active_properties,
        COUNT(DISTINCT company_id) as companies_with_active_properties,
        SUM(unit) as total_units
    FROM filtered_properties_view
""")

# Display final answer
display(final_results)

# COMMAND ----------

# Save excluded properties for review
excluded_with_reason.select(
    "id", "name", "company_id", "unit", "exclusion_reason"
).write.mode("overwrite").saveAsTable("rds.pg_rds_public.excluded_properties_analysis")

print("Excluded properties saved to: rds.pg_rds_public.excluded_properties_analysis")
