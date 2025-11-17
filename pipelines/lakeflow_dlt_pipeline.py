# Databricks notebook source
# MAGIC %md
# MAGIC # Lakeflow Connect - RDS PostgreSQL to Delta Lake
# MAGIC
# MAGIC **Source:** AWS RDS PostgreSQL - `public` schema
# MAGIC **Destination:** Unity Catalog - `rds.pg_rds_public`
# MAGIC **Mode:** Full initial load + Continuous CDC (Change Data Capture)
# MAGIC **Tables:** 20 core business tables
# MAGIC
# MAGIC ## Pipeline Configuration
# MAGIC
# MAGIC This Delta Live Tables pipeline uses Lakeflow Connect to:
# MAGIC 1. Perform initial full load of all 20 tables
# MAGIC 2. Enable continuous CDC via PostgreSQL logical replication
# MAGIC 3. Maintain Delta tables with near real-time updates
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - PostgreSQL logical replication enabled
# MAGIC - `lakeflow_user` created with proper permissions
# MAGIC - Connection `rds_postgres_public` created in Databricks
# MAGIC - Pipeline configured with serverless compute

# COMMAND ----------

import dlt
from pyspark.sql.functions import *

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Connection details (set via pipeline configuration)
CONNECTION_NAME = "rds_postgres_public"
SOURCE_SCHEMA = "public"

# List of tables to sync (Top 20 from usage analysis)
TABLES = [
    "entries",
    "folders",
    "applicants",
    "income_verification_reviews",
    "proof",
    "properties",
    "companies",
    "applicant_submission_document_sources",
    "income_verification_submissions",
    "applicant_submissions",
    "id_verifications",
    "users",
    "property_features",
    "income_verification_results",
    "rent_verifications",
    "api_keys",
    "unauthenticated_session",
    "rent_verification_events",
    "fraud_submissions",
    "fraud_reviews"
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Ingestion Functions
# MAGIC
# MAGIC Each table is defined as a DLT streaming table that reads from the Lakeflow Connect connection.

# COMMAND ----------

# entries - Most heavily used table (51,917 queries)
@dlt.table(
    name="entries",
    comment="Application entries - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def entries():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/entries")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.entries")
    )

# COMMAND ----------

# folders - Second most used (40,317 queries)
@dlt.table(
    name="folders",
    comment="Document folders - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def folders():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/folders")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.folders")
    )

# COMMAND ----------

# applicants - Third most used (29,951 queries)
@dlt.table(
    name="applicants",
    comment="Applicant records - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def applicants():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/applicants")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.applicants")
    )

# COMMAND ----------

# income_verification_reviews (26,262 queries)
@dlt.table(
    name="income_verification_reviews",
    comment="Income verification reviews - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def income_verification_reviews():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/income_verification_reviews")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.income_verification_reviews")
    )

# COMMAND ----------

# proof (24,800 queries)
@dlt.table(
    name="proof",
    comment="Proof documents - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def proof():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/proof")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.proof")
    )

# COMMAND ----------

# properties (22,140 queries)
@dlt.table(
    name="properties",
    comment="Property records - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def properties():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/properties")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.properties")
    )

# COMMAND ----------

# companies (19,724 queries)
@dlt.table(
    name="companies",
    comment="Company records - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def companies():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/companies")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.companies")
    )

# COMMAND ----------

# applicant_submission_document_sources (11,085 queries)
@dlt.table(
    name="applicant_submission_document_sources",
    comment="Applicant submission document sources - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def applicant_submission_document_sources():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/applicant_submission_document_sources")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.applicant_submission_document_sources")
    )

# COMMAND ----------

# income_verification_submissions (10,312 queries)
@dlt.table(
    name="income_verification_submissions",
    comment="Income verification submissions - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def income_verification_submissions():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/income_verification_submissions")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.income_verification_submissions")
    )

# COMMAND ----------

# applicant_submissions (7,329 queries)
@dlt.table(
    name="applicant_submissions",
    comment="Applicant submissions - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def applicant_submissions():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/applicant_submissions")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.applicant_submissions")
    )

# COMMAND ----------

# id_verifications (3,696 queries)
@dlt.table(
    name="id_verifications",
    comment="ID verifications - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def id_verifications():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/id_verifications")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.id_verifications")
    )

# COMMAND ----------

# users (3,261 queries)
@dlt.table(
    name="users",
    comment="User accounts - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def users():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/users")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.users")
    )

# COMMAND ----------

# property_features (2,335 queries)
@dlt.table(
    name="property_features",
    comment="Property features - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def property_features():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/property_features")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.property_features")
    )

# COMMAND ----------

# income_verification_results (1,153 queries)
@dlt.table(
    name="income_verification_results",
    comment="Income verification results - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def income_verification_results():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/income_verification_results")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.income_verification_results")
    )

# COMMAND ----------

# rent_verifications (710 queries)
@dlt.table(
    name="rent_verifications",
    comment="Rent verifications - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def rent_verifications():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/rent_verifications")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.rent_verifications")
    )

# COMMAND ----------

# api_keys (329 queries)
@dlt.table(
    name="api_keys",
    comment="API keys - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def api_keys():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/api_keys")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.api_keys")
    )

# COMMAND ----------

# unauthenticated_session (306 queries)
@dlt.table(
    name="unauthenticated_session",
    comment="Unauthenticated sessions - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def unauthenticated_session():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/unauthenticated_session")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.unauthenticated_session")
    )

# COMMAND ----------

# rent_verification_events (225 queries)
@dlt.table(
    name="rent_verification_events",
    comment="Rent verification events - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def rent_verification_events():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/rent_verification_events")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.rent_verification_events")
    )

# COMMAND ----------

# fraud_submissions (222 queries)
@dlt.table(
    name="fraud_submissions",
    comment="Fraud submissions - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def fraud_submissions():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/fraud_submissions")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.fraud_submissions")
    )

# COMMAND ----------

# fraud_reviews (209 queries)
@dlt.table(
    name="fraud_reviews",
    comment="Fraud reviews - ingested from PostgreSQL via Lakeflow Connect",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
def fraud_reviews():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "delta")
            .option("cloudFiles.connectionName", CONNECTION_NAME)
            .option("cloudFiles.schemaLocation", f"dbfs:/pipelines/rds_public_lakeflow/schemas/fraud_reviews")
            .table(f"{CONNECTION_NAME}.{SOURCE_SCHEMA}.fraud_reviews")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete
# MAGIC
# MAGIC All 20 tables are now configured for streaming ingestion via Lakeflow Connect.
# MAGIC
# MAGIC ### Next Steps:
# MAGIC 1. Create the DLT pipeline in Databricks UI pointing to this notebook
# MAGIC 2. Configure pipeline settings:
# MAGIC    - Mode: Continuous
# MAGIC    - Compute: Serverless
# MAGIC    - Target: rds.pg_rds_public
# MAGIC 3. Start the pipeline
# MAGIC 4. Monitor initial full load
# MAGIC 5. Verify CDC is working after full load completes
