# Databricks notebook source
"""
DLT Pipeline for FDE Dimension Table
=====================================

This pipeline creates the FDE dimension table in the sandbox for testing.

Target: team_sandbox.data_engineering.dlt_test_dim_fde
Source: RDS PostgreSQL tables via Unity Catalog

Author: Data Engineering Team
Created: 2025-10-21
"""

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from functools import reduce

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Set pipeline to write to sandbox catalog for testing

# COMMAND ----------

# Pipeline configuration
CATALOG = "team_sandbox"
SCHEMA = "data_engineering"
TABLE_PREFIX = "dlt_test_"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def get_fde_exclusion_filter():
    """
    Returns a column expression for filtering out test/demo/deleted properties.
    This replicates the logic from the fde_exclusions view.
    """
    exclusion_conditions = [
        # Property name exclusions
        F.upper(F.col("properties_name")).like("%DELETE%"),
        F.upper(F.col("properties_name")).like("% TEST %"),
        F.upper(F.col("properties_name")).like("%-TEST%"),
        F.upper(F.col("properties_name")).like("% DEMO %"),
        F.upper(F.col("properties_name")).like("%-DEMO%"),
        F.upper(F.col("properties_name")).like("%DUPLICATE%"),
        F.upper(F.col("properties_name")).like("%WIMBLEDON OAKS-DUP%"),
        F.upper(F.col("properties_name")).like("%INTEGRATION%"),
        F.upper(F.col("properties_name")).like("%QA%"),
        F.upper(F.col("properties_name")).like("%SNAPPT%"),
        F.upper(F.col("properties_name")) == "ASHTESTPROP1",

        # Company name exclusions
        F.upper(F.col("companies_name")).like("%DELETE%"),
        F.upper(F.col("companies_name")).like("% TEST %"),
        F.upper(F.col("companies_name")).like("%-TEST%"),
        F.upper(F.col("companies_name")).like("% DEMO %"),
        F.upper(F.col("companies_name")).like("%-DEMO%"),
        F.upper(F.col("companies_name")).like("%DUPLICATE%"),
        F.upper(F.col("companies_name")).like("%WIMBLEDON OAKS-DUP%"),
        F.upper(F.col("companies_name")).like("%INTEGRATION%"),
        F.upper(F.col("companies_name")).like("%QA%"),
        F.upper(F.col("companies_name")) == "ASHTESTPROP1",

        # Specific company short_id exclusions
        F.col("companies_short_id").isin(["cwoLhzGeUl", "pX9b5O12S7", "rcqvovxhWu", "l6r65EDGMD", "9uEFnVe7qT"])
    ]

    # Combine all conditions with OR, then negate with ~
    combined_exclusions = reduce(lambda a, b: a | b, exclusion_conditions)

    # Also exclude the specific company ID
    specific_company_exclusion = F.col("companies_id") == "f18cf283-c79c-40b4-85e1-5cb7da6718a1"

    return ~(combined_exclusions & ~specific_company_exclusion)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Layer - Raw FDE Data
# MAGIC
# MAGIC This layer reads from RDS and performs the 11-way JOIN to create the base FDE dataset.

# COMMAND ----------

@dlt.table(
    name=f"{TABLE_PREFIX}bronze_fde_raw",
    comment="Bronze layer: Raw FDE data from RDS PostgreSQL with all source tables joined",
    table_properties={
        "quality": "bronze",
        "pipelines.reset.allowed": "true"
    }
)
def bronze_fde_raw():
    """
    Creates the raw FDE dataset by joining all source tables from RDS.
    This replicates the snappt_pgdb_temp_view logic.
    """

    # Read source tables
    companies = spark.table("rds.pg_rds_public.companies")
    properties = spark.table("rds.pg_rds_public.properties")
    folders = spark.table("rds.pg_rds_public.folders")
    entries = spark.table("rds.pg_rds_public.entries")
    applicants = spark.table("rds.pg_rds_public.applicants")
    proof = spark.table("rds.pg_rds_public.proof")
    property_features = spark.table("rds.pg_rds_public.property_features")

    # Read Unity Catalog tables
    epa_sipp_properties = spark.table("product_sandbox.fde.unity_epa_sipp_properties")
    agg_property_features = spark.table("product.fde.unity_agg_property_features")

    # Build the base dataset with all JOINs
    df = (
        companies.alias("c")
        # Join properties
        .join(
            properties.alias("pr"),
            F.col("c.id") == F.col("pr.company_id"),
            "left"
        )
        # Join EPA/SIPP properties
        .join(
            epa_sipp_properties.alias("es"),
            F.col("pr.id") == F.col("es.property_id"),
            "left"
        )
        # Join folders
        .join(
            folders.alias("f"),
            F.col("pr.id") == F.col("f.property_id"),
            "left"
        )
        # Join entries
        .join(
            entries.alias("e"),
            F.col("f.id") == F.col("e.folder_id"),
            "left"
        )
        # Join applicants
        .join(
            applicants.alias("a"),
            F.col("e.id") == F.col("a.entry_id"),
            "left"
        )
        # Join proof/documents
        .join(
            proof.alias("p"),
            F.col("e.id") == F.col("p.entry_id"),
            "left"
        )
        # Join property features
        .join(
            property_features.alias("pf"),
            F.col("pr.id") == F.col("pf.property_id"),
            "left"
        )
        # Join aggregated property features
        .join(
            agg_property_features.alias("apf"),
            F.col("pr.id") == F.col("apf.property_id"),
            "left"
        )
        # Select all columns with prefixes
        .select(
            # Companies
            F.col("c.id").alias("companies_id"),
            F.col("c.name").alias("companies_name"),
            F.col("c.address").alias("companies_address"),
            F.col("c.zip").alias("companies_zip"),
            F.col("c.city").alias("companies_city"),
            F.col("c.state").alias("companies_state"),
            F.col("c.logo").alias("companies_logo"),
            F.col("c.short_id").alias("companies_short_id"),
            F.col("c.inserted_at").alias("companies_inserted_at"),
            F.col("c.updated_at").alias("companies_updated_at"),

            # Properties
            F.col("pr.id").alias("properties_id"),
            F.col("pr.name").alias("properties_name"),
            F.col("pr.entity_name").alias("properties_entity_name"),
            F.col("pr.unit").alias("properties_unit"),
            F.col("pr.city").alias("properties_city"),
            F.col("pr.address").alias("properties_address"),
            F.col("pr.state").alias("properties_state"),
            F.col("pr.zip").alias("properties_zip"),
            F.col("pr.status").alias("properties_status"),
            F.col("pr.inserted_at").alias("properties_inserted_at"),
            F.col("pr.updated_at").alias("properties_updated_at"),
            F.col("pr.company_short_id").alias("properties_company_short_id"),
            F.col("pr.bank_statement").alias("deprecated_properties_bank_statement"),
            F.col("pr.paystub").alias("deprecated_properties_paystub"),
            F.col("pr.unit_is_required").alias("properties_unit_is_required"),
            F.col("pr.phone_is_required").alias("properties_phone_is_required"),
            F.col("pr.short_id").alias("properties_short_id"),
            F.col("pr.email").alias("properties_email"),
            F.col("pr.company_id").alias("properties_company_id"),
            F.col("pr.identity_verification_enabled").alias("properties_identity_verification_enabled"),
            F.col("pr.pmc_name").alias("properties_pmc_name"),
            F.col("pr.supported_doctypes").alias("properties_supported_doctypes"),
            F.col("pr.sfdc_id").alias("properties_sfdc_id"),

            # EPA/SIPP
            F.col("es.is_epa_property").alias("is_epa_property"),
            F.col("es.is_yardi_sipp_property").alias("is_yardi_sipp_property"),

            # Property Features
            F.col("pf.id").alias("property_features_id"),
            F.col("pf.feature_code").alias("property_features_feature_code"),
            F.col("pf.inserted_at").alias("property_features_inserted_at"),
            F.col("pf.updated_at").alias("property_features_updated_at"),
            F.col("pf.property_id").alias("property_features_property_id"),
            F.col("pf.state").alias("property_features_state"),

            # Aggregated Property Features
            F.col("apf.property_id").alias("agg_property_features_property_id"),
            F.col("apf.iv_enabled").alias("agg_property_features_iv_enabled"),
            F.col("apf.payroll_linking_enabled").alias("agg_property_features_payroll_linking_enabled"),
            F.col("apf.iv_enabled_at").alias("agg_property_features_iv_enabled_at"),
            F.col("apf.payroll_linking_enabled_at").alias("agg_property_features_payroll_linking_enabled_at"),
            F.col("apf.iv_updated_at").alias("agg_property_features_iv_updated_at"),
            F.col("apf.payroll_linking_updated_at").alias("agg_property_features_payroll_linking_updated_at"),

            # Folders
            F.col("f.id").alias("folders_id"),
            F.col("f.name").alias("folders_name"),
            F.col("f.status").alias("folders_status"),
            F.col("f.property_id").alias("folders_property_id"),
            F.col("f.result").alias("folders_result"),
            F.col("f.inserted_at").alias("folders_inserted_at"),
            F.col("f.updated_at").alias("folders_updated_at"),
            F.col("f.property_short_id").alias("folders_property_short_id"),
            F.col("f.property_name").alias("folders_property_name"),
            F.col("f.company_short_id").alias("folders_company_short_id"),
            F.col("f.dynamic_ruling").alias("folders_dynamic_ruling"),
            F.col("f.ruling_time").alias("folders_ruling_time"),
            F.col("f.company_id").alias("folders_company_id"),
            F.col("f.last_entry_id").alias("folders_last_entry_id"),

            # Applicants
            F.col("a.id").alias("applicants_id"),
            F.col("a.full_name").alias("applicants_full_name"),
            F.col("a.first_name").alias("applicants_first_name"),
            F.col("a.middle_initial").alias("applicants_middle_initial"),
            F.col("a.last_name").alias("applicants_last_name"),
            F.col("a.email").alias("applicants_email"),
            F.col("a.phone").alias("applicants_phone"),
            F.col("a.notification").alias("applicants_notification"),
            F.col("a.entry_id").alias("applicants_entry_id"),
            F.col("a.inserted_at").alias("applicants_inserted_at"),
            F.col("a.updated_at").alias("applicants_updated_at"),

            # Entries
            F.col("e.id").alias("entries_id"),
            F.col("e.status").alias("entries_status"),
            F.col("e.has_previously_submitted").alias("entries_has_previously_submitted"),
            F.col("e.folder_id").alias("entries_folder_id"),
            F.col("e.result").alias("entries_result"),
            F.col("e.inserted_at").alias("entries_inserted_at"),
            F.col("e.updated_at").alias("entries_updated_at"),
            F.col("e.short_id").alias("entries_short_id"),
            F.col("e.submission_time").alias("entries_submission_time"),
            F.col("e.suggested_ruling").alias("entries_suggested_ruling"),
            F.col("e.notification_email").alias("entries_notification_email"),
            F.col("e.report_complete_time").alias("entries_report_complete_time"),
            F.col("e.reviewer_id").alias("entries_reviewer_id"),
            F.col("e.twenty_two_hours_notification_sent_at").alias("entries_twenty_two_hours_notification_sent_at"),
            F.col("e.sixteen_hours_notification_sent_at").alias("entries_sixteen_hours_notification_sent_at"),
            F.col("e.review_status").alias("entries_review_status"),
            F.col("e.review_date").alias("entries_review_date"),
            F.col("e.unit").alias("entries_unit"),
            F.col("e.metadata").alias("entries_metadata"),
            F.col("e.note").alias("entries_note"),
            F.col("e.is_automatic_review").alias("entries_is_automatic_review"),

            # Proof/Documents
            F.col("p.id").alias("proof_id"),
            F.col("p.file").alias("proof_file"),
            F.col("p.type").alias("proof_type"),
            F.col("p.has_text").alias("proof_has_text"),
            F.col("p.has_password_protection").alias("proof_has_password_protection"),
            F.col("p.has_exceeded_page_limit").alias("proof_has_exceeded_page_limit"),
            F.col("p.entry_id").alias("proof_entry_id"),
            F.col("p.inserted_at").alias("proof_inserted_at"),
            F.col("p.updated_at").alias("proof_updated_at"),
            F.col("p.short_id").alias("proof_short_id"),
            F.col("p.note").alias("proof_note"),
            F.col("p.result").alias("proof_result"),
            F.col("p.suggested_ruling").alias("proof_suggested_ruling"),
            F.col("p.test_suggested_ruling").alias("proof_test_suggested_ruling"),
            F.col("p.result_edited_reason").cast("string").alias("proof_result_edited_reason"),
            F.col("p.result_insufficient_reason").alias("proof_result_insufficient_reason"),
            F.col("p.text_breakups_file").alias("proof_text_breakups_file"),
            F.col("p.is_automatic_review").alias("proof_is_automatic_review")
        )
        .distinct()
    )

    return df

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer - Cleaned FDE Data
# MAGIC
# MAGIC This layer applies data quality rules and filters out test/demo data.

# COMMAND ----------

@dlt.table(
    name=f"{TABLE_PREFIX}silver_fde_cleaned",
    comment="Silver layer: Cleaned FDE data with test/demo exclusions and data quality checks",
    table_properties={
        "quality": "silver",
        "pipelines.reset.allowed": "true"
    }
)
@dlt.expect_all({
    "valid_company_id": "companies_id IS NOT NULL",
    "valid_property_id": "properties_id IS NOT NULL"
})
@dlt.expect_or_drop("no_null_property_names", "properties_name IS NOT NULL")
def silver_fde_cleaned():
    """
    Applies business logic to filter out test/demo/deleted properties and companies.
    Also applies basic data quality expectations.
    """
    df = dlt.read(f"{TABLE_PREFIX}bronze_fde_raw")

    # Apply exclusion filter
    df_cleaned = df.filter(get_fde_exclusion_filter())

    return df_cleaned

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer - Dimension Table
# MAGIC
# MAGIC This is the final consumer-facing dimension table with renamed columns and business logic.

# COMMAND ----------

@dlt.table(
    name=f"{TABLE_PREFIX}dim_fde",
    comment="Gold layer: FDE dimension table for analytics and reporting (SANDBOX TEST)",
    table_properties={
        "quality": "gold",
        "pipelines.reset.allowed": "true",
        "pipelines.autoOptimize.zOrderCols": "property_id,submission_datetime,company_id"
    }
)
@dlt.expect_all({
    "valid_submission_status": """
        submission_status IS NULL OR
        submission_status IN ('pending', 'completed', 'cancelled', 'reviewing', 'failed')
    """,
    "valid_property_state": """
        property_state IS NULL OR
        LENGTH(property_state) = 2
    """
})
@dlt.expect_or_drop("valid_timestamps", """
    (submission_id IS NULL) OR
    (submission_id IS NOT NULL AND submission_datetime IS NOT NULL)
""")
def dim_fde():
    """
    Final dimension table with business-friendly column names and deduplication.
    This replicates the source_fde view logic with GROUP BY ALL.
    """
    df = dlt.read(f"{TABLE_PREFIX}silver_fde_cleaned")

    # Rename columns to business names
    df_renamed = df.select(
        # Company columns
        F.col("companies_id").alias("company_id"),
        F.col("companies_name").alias("company_name"),
        F.col("companies_address").alias("company_street_address"),
        F.col("companies_zip").alias("company_zip"),
        F.col("companies_city").alias("company_city"),
        F.col("companies_state").alias("company_state"),
        F.col("companies_logo").alias("company_logo"),
        F.col("companies_short_id").alias("company_short_id"),
        F.col("companies_inserted_at").alias("company_record_created_datetime"),

        # Property columns
        F.col("properties_id").alias("property_id"),
        F.col("properties_name").alias("property_name"),
        F.col("properties_entity_name").alias("property_legal_name"),
        F.col("properties_unit").alias("property_unit_count"),
        F.col("properties_city").alias("property_city"),
        F.col("properties_address").alias("property_street_address"),
        F.col("properties_state").alias("property_state"),
        F.col("properties_zip").alias("property_zip"),
        F.col("properties_status").alias("property_is_active"),
        F.col("properties_inserted_at").alias("property_record_created_datetime"),
        F.col("properties_updated_at").alias("property_record_updated_datetime"),
        F.col("properties_unit_is_required").alias("property_unit_is_required"),
        F.col("properties_phone_is_required").alias("property_phone_is_required"),
        F.col("properties_short_id").alias("property_short_id"),
        F.col("properties_email").alias("property_email"),
        F.col("properties_identity_verification_enabled").alias("property_identity_verification_enabled_flag"),
        F.col("properties_pmc_name").alias("property_pmc_name"),
        F.col("properties_supported_doctypes").alias("property_supported_doctypes"),
        F.col("properties_sfdc_id").alias("property_sfdc_id"),

        # Aggregated property features
        F.col("agg_property_features_property_id"),
        F.col("agg_property_features_iv_enabled"),
        F.col("agg_property_features_payroll_linking_enabled"),
        F.col("agg_property_features_iv_enabled_at"),
        F.col("agg_property_features_payroll_linking_enabled_at"),
        F.col("agg_property_features_iv_updated_at"),
        F.col("agg_property_features_payroll_linking_updated_at"),
        F.col("is_yardi_sipp_property"),
        F.col("is_epa_property"),

        # Folder columns
        F.col("folders_id").alias("folder_id"),
        F.col("folders_name").alias("folder_name"),
        F.col("folders_status").alias("folder_status"),
        F.col("folders_inserted_at").alias("folder_record_created_datetime"),
        F.col("folders_updated_at").alias("folder_record_updated_datetime"),
        F.col("folders_property_name").alias("folder_property_name"),
        F.col("folders_company_short_id").alias("folder_company_short_id"),
        F.col("folders_dynamic_ruling").alias("folder_dynamic_ruling"),
        F.col("folders_ruling_time").alias("folder_ruling_datetime"),
        F.col("folders_last_entry_id").alias("folder_last_submission_id"),

        # Applicant columns
        F.col("applicants_id").alias("applicant_id"),
        F.col("applicants_full_name").alias("applicant_full_name"),
        F.col("applicants_first_name").alias("applicant_first_name"),
        F.col("applicants_middle_initial").alias("applicant_middle_initial"),
        F.col("applicants_last_name").alias("applicant_last_name"),
        F.col("applicants_email").alias("applicant_email"),
        F.col("applicants_phone").alias("applicant_phone"),
        F.col("applicants_notification").alias("applicant_notification"),
        F.col("folders_result").alias("applicant_ruling"),
        F.col("folders_inserted_at").alias("applicant_record_created_datetime"),

        # Submission/Entry columns
        F.col("entries_id").alias("submission_id"),
        F.col("entries_status").alias("submission_status"),
        F.col("entries_has_previously_submitted").alias("submission_applicant_has_previously_submitted"),
        F.col("entries_result").alias("submission_ruling"),
        F.col("entries_short_id").alias("submission_short_id"),
        F.col("entries_submission_time").alias("submission_datetime"),
        F.col("entries_notification_email").alias("submission_notification_email"),
        F.col("entries_report_complete_time").alias("submission_report_completed_datetime"),
        F.col("entries_reviewer_id").alias("submission_reviewer_id"),
        F.col("entries_twenty_two_hours_notification_sent_at").alias("submission_twenty_two_hours_notification_sent_at"),
        F.col("entries_sixteen_hours_notification_sent_at").alias("submission_sixteen_hours_notification_sent_at"),
        F.col("entries_review_status").alias("submission_review_status"),
        F.col("entries_review_date").alias("submission_review_datetime"),
        F.col("entries_is_automatic_review").alias("submission_is_automatic_ruling"),
        F.col("entries_unit").alias("submission_unit"),
        F.col("entries_metadata").alias("submission_metadata"),
        F.col("entries_note").alias("submission_note"),

        # Document/Proof columns
        F.col("proof_id").alias("document_id"),
        F.col("proof_file").alias("document_file_name"),
        F.col("proof_type").alias("document_type"),
        F.col("proof_has_text").alias("document_has_text"),
        F.col("proof_has_password_protection").alias("document_has_password_protection"),
        F.col("proof_has_exceeded_page_limit").alias("document_has_exceeded_page_limit"),
        F.col("proof_inserted_at").alias("document_record_created_at"),
        F.col("proof_short_id").alias("document_short_id"),
        F.col("proof_note").alias("document_note"),
        F.col("proof_result").alias("document_ruling"),
        F.col("proof_suggested_ruling").alias("document_suggested_ruling"),
        F.col("proof_result_edited_reason").alias("document_ruling_edited_reason"),
        F.col("proof_result_insufficient_reason").alias("document_ruling_undetermined_reason"),
        F.col("proof_text_breakups_file").alias("document_text_breakups_file"),
        F.col("proof_is_automatic_review").alias("document_is_automatic_ruling")
    )

    # Apply GROUP BY ALL logic (remove duplicates)
    # Get all column names for deduplication
    all_columns = df_renamed.columns
    df_deduplicated = df_renamed.dropDuplicates(all_columns)

    return df_deduplicated

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation View
# MAGIC
# MAGIC Create a view for comparing sandbox results with production

# COMMAND ----------

@dlt.view(
    name=f"{TABLE_PREFIX}validation_summary",
    comment="Validation summary comparing sandbox DLT output with production table"
)
def validation_summary():
    """
    Creates a summary view for validation purposes.
    Compare row counts, check for data differences, etc.
    """
    sandbox_df = dlt.read(f"{TABLE_PREFIX}dim_fde")

    # Create validation metrics
    validation = sandbox_df.selectExpr(
        "COUNT(*) as total_rows",
        "COUNT(DISTINCT company_id) as unique_companies",
        "COUNT(DISTINCT property_id) as unique_properties",
        "COUNT(DISTINCT submission_id) as unique_submissions",
        "COUNT(DISTINCT document_id) as unique_documents",
        "MIN(submission_datetime) as earliest_submission",
        "MAX(submission_datetime) as latest_submission",
        "CURRENT_TIMESTAMP() as validation_timestamp"
    )

    return validation
