# Lakeflow Connect Setup - Checklist and Files

## What We've Created So Far

### 📊 Analysis Files
- **`50_most_used_tables.csv`** - Top 50 tables across all rds schemas
  - Shows 20 heavily-used tables in `pg_rds_public` schema
  - Usage metrics: query counts, users, read/write patterns

### 📖 Documentation Files
- **`lakeflow_setup_guide.md`** - Complete step-by-step setup guide
  - All 6 phases from PostgreSQL config to Fivetran migration
  - Troubleshooting tips
  - Monitoring queries

### 🔧 Configuration Files
- **`postgres_setup.sql`** - PostgreSQL configuration script
  - Creates `lakeflow_user` role
  - Grants replication and SELECT permissions
  - Validation queries

- **`lakeflow_dlt_pipeline.py`** - Delta Live Tables pipeline notebook
  - Defines all 20 tables for ingestion
  - Configured for streaming CDC
  - Ready to upload to Databricks

---

## Target Tables (20 from pg_rds_public)

1. entries (51,917 queries)
2. folders (40,317 queries)
3. applicants (29,951 queries)
4. income_verification_reviews (26,262 queries)
5. proof (24,800 queries)
6. properties (22,140 queries)
7. companies (19,724 queries)
8. applicant_submission_document_sources (11,085 queries)
9. income_verification_submissions (10,312 queries)
10. applicant_submissions (7,329 queries)
11. id_verifications (3,696 queries)
12. users (3,261 queries)
13. property_features (2,335 queries)
14. income_verification_results (1,153 queries)
15. rent_verifications (710 queries)
16. api_keys (329 queries)
17. unauthenticated_session (306 queries)
18. rent_verification_events (225 queries)
19. fraud_submissions (222 queries)
20. fraud_reviews (209 queries)

---

## Next Steps (In Order)

### ☐ Step 1: PostgreSQL Configuration
**Your Action Required:**
1. Enable logical replication on RDS:
   - AWS Console → RDS → Parameter Groups
   - Set `rds.logical_replication = 1`
   - Apply to instance and **reboot**

2. Run the setup script:
   - Connect to PostgreSQL as superuser
   - Execute `/Users/danerosa/rds_databricks_claude/pipelines/postgres_setup.sql`
   - Replace `<secure-password>` with a strong password
   - Replace `<database_name>` with your actual database name

3. Save credentials:
   - Username: `lakeflow_user`
   - Password: (the one you set)
   - RDS Endpoint: `<your-instance>.rds.amazonaws.com`
   - Database name: (your database)

**Verification:**
```sql
-- Run in PostgreSQL
SHOW wal_level;  -- Should return 'logical'
SELECT rolname FROM pg_roles WHERE rolname = 'lakeflow_user';  -- Should exist
```

---

### ☐ Step 2: Databricks Secret Management
**Next we'll do:**
- Create secret scope: `lakeflow-rds`
- Store the `lakeflow_user` password securely

**I can help with:** CLI commands to do this (will wait for your approval)

---

### ☐ Step 3: Create Lakeflow Connection
**Next we'll do:**
- Create connection in Databricks: `rds_postgres_public`
- Point to your RDS instance
- Test connection

**I can help with:** UI steps or API script (your choice)

---

### ☐ Step 4: Upload and Configure Pipeline
**Next we'll do:**
- Upload `lakeflow_dlt_pipeline.py` to your workspace
- Create DLT pipeline in Databricks UI
- Configure for serverless and continuous mode

**I can help with:** Uploading the notebook (after Steps 1-3 are done)

---

### ☐ Step 5: Start Initial Sync
**Next we'll do:**
- Start the pipeline
- Monitor full load progress
- Validate data

**I can help with:** Monitoring commands and validation queries

---

### ☐ Step 6: Verify CDC and Cutover
**Next we'll do:**
- Test real-time updates
- Run parallel with Fivetran for validation
- Migrate and deprecate Fivetran

---

## What to Do RIGHT NOW

**Please complete Step 1 (PostgreSQL Configuration):**

1. Check if you already have logical replication enabled:
   ```sql
   SHOW wal_level;
   ```
   - If it returns `logical`, skip the parameter group change
   - If not, you need to enable it and reboot

2. Run the PostgreSQL setup script to create the user

3. Let me know when Step 1 is complete, and I'll help with Step 2 (secrets)

---

## Questions?

- Not sure about your RDS endpoint? Check AWS Console → RDS → Databases
- Not sure about PostgreSQL version? `SELECT version();`
- Need help with any step? Just ask!

---

## Files Location Summary

```
/Users/danerosa/rds_databricks_claude/pipelines/
├── 50_most_used_tables.csv              # Usage analysis results
├── lakeflow_setup_guide.md              # Complete guide (all phases)
├── postgres_setup.sql                    # PostgreSQL setup script
├── lakeflow_dlt_pipeline.py             # DLT pipeline notebook
└── SETUP_CHECKLIST.md                   # This file
```
