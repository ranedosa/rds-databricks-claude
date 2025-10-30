# CLEAR Dashboard - Widget Explanation

This document explains each widget in the CLEAR Dashboard and what insights they provide. This dashboard focuses on monitoring the adoption and usage of CLEAR (an identity verification provider) compared to Incode across different property types and integration configurations.

## Core Data Tables

### 1. Total Properties - non OIF
**Widget Type:** Table
**What it shows:** All active properties that are not using OneIncomeForms (OIF) integration, including:
- Property name, ID, and company information
- Identity verification provider configuration
- Property status and creation date
**Business Value:** Provides a baseline view of all non-OIF properties that could potentially use IDV services

### 2. Total Properties - Yardi OIF
**Widget Type:** Table
**What it shows:** Properties integrated with Yardi OIF, including:
- Property and company details
- Integration configuration (name and type)
- IDV provider settings
- Integration activation dates
**Business Value:** Shows properties using Yardi integration that could benefit from IDV services

### 3. Total Properties - Realpage OIF
**Widget Type:** Table
**What it shows:** Properties integrated with RealPage OIF, including:
- Property and company details
- Integration configuration
- IDV provider settings
- Integration activation dates
**Business Value:** Shows properties using RealPage integration that could benefit from IDV services

## Provider Distribution Analysis - Properties

### 4. Incode Properties - non OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** Non-OIF properties currently configured with Incode as their IDV provider
**Business Value:** Identifies properties that could be migrated from Incode to CLEAR

### 5. CLEAR Properties - non OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** Non-OIF properties currently configured with CLEAR as their IDV provider
**Business Value:** Shows successful CLEAR adoption in the non-OIF segment

### 6. Incode Properties - Yardi OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** Yardi OIF properties using Incode for identity verification
**Business Value:** Identifies Yardi-integrated properties for potential CLEAR migration

### 7. CLEAR Properties - Yardi OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** Yardi OIF properties using CLEAR for identity verification
**Business Value:** Shows CLEAR adoption within Yardi-integrated properties

### 8. Incode Properties - Realpage OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** RealPage OIF properties using Incode for identity verification
**Business Value:** Identifies RealPage-integrated properties for potential CLEAR migration

### 9. CLEAR Properties - Realpage OIF (IDV Enabled)
**Widget Type:** Table
**What it shows:** RealPage OIF properties using CLEAR for identity verification
**Business Value:** Shows CLEAR adoption within RealPage-integrated properties

## Provider Distribution Metrics

### 10. CLEAR vs Incode - Non-OIF Properties (Percentage)
**Widget Type:** Pie Chart / Metric
**What it shows:** Percentage distribution of CLEAR vs Incode usage across non-OIF properties with IDV enabled
**Business Value:** Quick visual reference for market share in non-OIF segment

### 11. CLEAR vs Incode - Yardi OIF Properties (Percentage)
**Widget Type:** Pie Chart / Metric
**What it shows:** Percentage distribution of CLEAR vs Incode usage across Yardi OIF properties
**Business Value:** Shows adoption rate in Yardi-integrated environments

### 12. CLEAR vs Incode - Realpage OIF Properties (Percentage)
**Widget Type:** Pie Chart / Metric
**What it shows:** Percentage distribution of CLEAR vs Incode usage across RealPage OIF properties
**Business Value:** Shows adoption rate in RealPage-integrated environments

## Submission Volume Analysis

### 13. Total IDV Submissions
**Widget Type:** Table
**What it shows:** All identity verification submissions within the selected date range, including:
- Full submission details from id_verifications table
- Property and company names
- Provider results
**Parameters:** Submission Date Range (default: current month)
**Business Value:** Complete view of all IDV activity for detailed analysis

### 14. Incode IDV Submissions
**Widget Type:** Table
**What it shows:** Submissions specifically using Incode as the provider
**Parameters:** Submission Date Range (default: current month)
**Business Value:** Detailed view of Incode submission volume and patterns

### 15. CLEAR IDV Submissions (All)
**Widget Type:** Table
**What it shows:** All submissions using CLEAR as the provider
**Parameters:** Submission Date Range (default: current month)
**Business Value:** Complete view of CLEAR usage and adoption

### 16. CLEAR vs Incode Submissions (Percentage)
**Widget Type:** Pie Chart
**What it shows:** Percentage distribution of actual submissions between CLEAR and Incode providers
**Parameters:** Submission Date Range (default: current month)
**Business Value:** Shows actual market share based on submission volume, not just property configuration

## CLEAR Flow Type Analysis

### 17. CLEAR IDV Submissions - Enhanced Flow
**Widget Type:** Table
**What it shows:** CLEAR submissions using the "full" flow type (enhanced verification)
**Parameters:** Submission Date Range
**Business Value:** Shows usage of CLEAR's more comprehensive verification process

### 18. CLEAR IDV Submissions - Basic Flow
**Widget Type:** Table
**What it shows:** CLEAR submissions using the "lite" flow type (basic verification)
**Parameters:** Submission Date Range
**Business Value:** Shows usage of CLEAR's streamlined verification process

### 19. CLEAR Submissions - Basic vs Enhanced Over Time
**Widget Type:** Stacked Bar Chart / Time Series
**What it shows:** Daily breakdown of CLEAR submissions by flow type (Enhanced vs Basic)
**Parameters:** Submission Date Range (default: past 4 days)
**Business Value:** Reveals usage patterns and preferences between verification depths

## Success Rate Analysis

### 20. CLEAR IDV Submissions - Pass vs Fail Rate (Total)
**Widget Type:** Pie Chart / Metric
**What it shows:** Overall success rate for all CLEAR submissions (both flow types)
**Parameters:** Submission Date Range
**Business Value:** Shows overall CLEAR verification effectiveness

### 21. CLEAR IDV Submissions - Pass vs Fail Rate (Enhanced)
**Widget Type:** Pie Chart / Metric
**What it shows:** Success rate specifically for Enhanced (full) flow submissions
**Parameters:** Submission Date Range
**Business Value:** Shows effectiveness of comprehensive verification process

### 22. CLEAR IDV Submissions - Pass vs Fail Rate (Basic)
**Widget Type:** Pie Chart / Metric
**What it shows:** Success rate specifically for Basic (lite) flow submissions
**Parameters:** Submission Date Range
**Business Value:** Shows effectiveness of streamlined verification process

## Failure Analysis

### 23. CLEAR IDV Submissions - Failure Reasons
**Widget Type:** Bar Chart
**What it shows:** Breakdown of specific verification checks that failed, including:
- Check names from provider_results
- Count of failures for each check type
**Parameters:** Submission Date Range
**Business Value:** Identifies common failure points and helps improve applicant guidance

## Key Insights for Data Analysis

### Provider Migration Tracking
- Monitor CLEAR adoption across different integration types (non-OIF, Yardi, RealPage)
- Compare property configuration vs actual submission volume
- Identify properties still on Incode for potential migration

### Flow Type Optimization
- Understand when properties use Enhanced vs Basic verification
- Track success rates for each flow type
- Optimize verification requirements based on use case

### Success Rate Monitoring
- Compare pass rates between CLEAR and Incode
- Identify failure patterns to improve applicant experience
- Track verification quality across different flow types

### Integration Performance
- Monitor how CLEAR performs across different PMS integrations
- Identify integration-specific issues or patterns
- Support troubleshooting and optimization efforts

## Dashboard Usage Notes

**Date Range Parameters:** Many widgets include date range filters (default: current month or past 4 days). Adjust these to analyze different time periods.

**Provider Comparison:** The dashboard separates Incode (including NULL values) from CLEAR to show clear adoption metrics.

**Flow Type Tracking:** CLEAR supports two flow types:
- **Enhanced (full):** More comprehensive identity verification
- **Basic (lite):** Streamlined verification process

**Data Sources:**
- Properties: `rds.pg_rds_public.properties`
- Companies: `rds.pg_rds_public.companies`
- Enterprise Properties: `rds.pg_rds_enterprise_public.enterprise_property`
- Integration Config: `rds.pg_rds_enterprise_public.enterprise_integration_configuration`
- IDV Submissions: `rds.pg_rds_public.id_verifications`

## Business Use Cases

**Sales & Growth Team:**
- Track CLEAR adoption rate across customer segments
- Identify properties for CLEAR migration outreach
- Demonstrate CLEAR usage to prospective customers

**Customer Success:**
- Monitor customer adoption of CLEAR
- Identify customers still using Incode for migration conversations
- Support troubleshooting with flow type and failure analysis

**Product & Engineering:**
- Track usage patterns between Enhanced and Basic flows
- Monitor success rates to identify optimization opportunities
- Analyze failure reasons to improve verification process

**Executive Leadership:**
- High-level view of CLEAR market share (properties and submissions)
- Success rate metrics to demonstrate value
- Adoption trends across different integration types

## Dashboard Maintenance

This dashboard pulls real-time data from the RDS PostgreSQL database via Fivetran sync. No code changes are required to maintain it - all metrics update automatically as:
- New properties are added
- Properties change IDV providers
- New submissions are processed
- Integration configurations change

For questions about specific metrics or to request new widgets, contact the Data Engineering team.

---

**Document Version:** 1.0
**Created:** 2025-10-30
**Dashboard Owner:** grayson@snappt.com
**Data Source:** RDS PostgreSQL via Databricks Unity Catalog
