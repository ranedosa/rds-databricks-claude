# New RDS → Salesforce Sync Architecture

**Date:** January 6, 2026
**Status:** Ready for Implementation
**Author:** Claude Code
**Estimated Timeline:** 3-4 weeks

---

## 📋 EXECUTIVE SUMMARY

This document outlines a complete ground-up redesign of the RDS → Salesforce property sync architecture to solve critical data synchronization issues.

### Current Problems

1. **1,081 properties** missing from Salesforce (11.9% of active properties)
2. **507 P1 critical properties** with features not visible to Sales/CS teams
3. **799 properties** with feature mismatches (IDV enabled in RDS but FALSE in SF)
4. **2,410 properties** blocked by duplicate SFDC IDs (many-to-1 relationships)
5. **Chicken-and-egg problem** with production IDs preventing new property creation
6. **~90% sync accuracy** (target: 99%+)

### Proposed Solution

A new architecture with three key innovations:

1. **Aggregation Layer** - Handles many-to-1 relationships at the source
2. **Two-Sync Strategy** - Separate Census syncs for create vs update
3. **Business Rules in SQL** - Transparent, testable, auditable aggregation logic

### Expected Outcomes

- **1,081 properties** will be created in Salesforce
- **507 P1 critical properties** with features will become visible
- **799 feature mismatches** will be resolved
- **2,410 blocked properties** will start syncing correctly
- **Sync accuracy** will improve from ~90% to 99%+
- **Future-proof architecture** that scales and maintains easily

---

## 📚 DOCUMENTATION STRUCTURE

This implementation plan is split across multiple documents for readability:

### 1. **Main Implementation Plan (Phase 1)**
   - **File:** `IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md`
   - **Contents:**
     - Architecture overview
     - Phase 1: Build Databricks Views (Days 1-3)
       - Step 1.1: Create `rds_properties_enriched` view
       - Step 1.2: Create `properties_aggregated_by_sfdc_id` view (CORE INNOVATION)
       - Step 1.3: Create `properties_to_create` view
       - Step 1.4: Create `properties_to_update` view
       - Step 1.5: Create `property_sync_audit_log` table
       - Step 1.6: Create `sync_monitoring_dashboard` view
   - **Deliverables:** All Databricks views and tables with full SQL scripts

### 2. **Phases 2-3: Validation & Census Configuration**
   - **File:** `IMPLEMENTATION_PLAN_PHASE2_TO_PHASE6.md`
   - **Contents:**
     - Phase 2: Validation & Testing (Days 4-5)
       - Data quality validation
       - Business case validation (Park Kennedy, P1 properties, etc.)
       - Edge case testing
     - Phase 3: Census Configuration (Week 2, Days 1-3)
       - Census Sync A: Create New Properties
       - Census Sync B: Update Existing Properties
       - Testing procedures
   - **Deliverables:** Validation suite, Census sync configurations

### 3. **Phases 4-6: Rollout & Operations**
   - **File:** `IMPLEMENTATION_PLAN_PHASE4_TO_PHASE6.md`
   - **Contents:**
     - Phase 4: Pilot Rollout (Week 2, Days 4-5)
       - Test on 50+50 properties
       - Validate end-to-end flow
     - Phase 5: Full Rollout (Week 3)
       - Execute full syncs (1,081 + 7,980 properties)
       - 48-hour monitoring
       - Success criteria
     - Phase 6: Monitoring & Documentation (Week 4)
       - Operational dashboard
       - Automated alerts
       - Runbooks
       - Knowledge transfer
   - **Deliverables:** Production rollout, monitoring, documentation

---

## 🎯 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│               DATABRICKS TRANSFORMATION LAYER               │
└─────────────────────────────────────────────────────────────┘

[1] SOURCE TABLES
    ├─ rds.pg_rds_public.properties
    └─ rds.pg_rds_public.property_features

                         ↓

[2] AGGREGATION LAYER ★ (NEW - Core Innovation)
    ├─ rds_properties_enriched
    │  └─ Properties + features joined (1 row per RDS property)
    │
    └─ properties_aggregated_by_sfdc_id ★★
       └─ Many-to-1 aggregation (1 row per SFDC ID)
       └─ Union logic for features
       └─ Audit trail of contributing properties

                         ↓

[3] SYNC STRATIFICATION LAYER (NEW - Smart Routing)
    ├─ properties_to_create
    │  └─ Properties NOT in product_property yet
    │  └─ Source for Census Sync A
    │
    └─ properties_to_update
       └─ Properties already in product_property
       └─ Uses aggregated data (handles many-to-1)
       └─ Source for Census Sync B

                         ↓

[4] CENSUS REVERSE ETL (Two Syncs)
    ├─ Sync A: Create New Properties
    │  └─ Mode: Create Only
    │  └─ Key: RDS.id → snappt_property_id_c
    │  └─ Schedule: Every 15 minutes
    │
    └─ Sync B: Update Existing Properties
       └─ Mode: Update Only
       └─ Key: snappt_property_id_c (match existing)
       └─ Schedule: Every 30 minutes

                         ↓

┌─────────────────────────────────────────────────────────────┐
│                   SALESFORCE (Managed by SF)                │
└─────────────────────────────────────────────────────────────┘

[5] STAGING
    └─ product_property object
       ├─ snappt_property_id_c (from RDS.id - sync key)
       └─ sf_property_id_c (populated by SF workflow)

                         ↓

[6] PRODUCTION
    └─ Property object
       └─ Automated workflow: staging → production
```

---

## 🔑 KEY INNOVATIONS

### Innovation 1: Aggregation Layer

**Problem Solved:** Multiple RDS properties can share the same SFDC ID (production Salesforce Property ID). The old architecture couldn't handle this many-to-1 relationship.

**Solution:** The `properties_aggregated_by_sfdc_id` view aggregates multiple RDS properties into a single record per SFDC ID using clear business rules:

- **Feature Flags:** UNION logic (if ANY active property has feature enabled → TRUE)
- **Property Metadata:** From primary (most recently updated) active property
- **Timestamps:** Earliest enabled date across all active properties
- **Audit Trail:** Track which RDS properties contributed to each sync

**Example:** Park Kennedy property has 2 RDS records (1 ACTIVE with features, 1 DISABLED). The aggregation layer produces 1 record with features enabled (from the ACTIVE property only).

### Innovation 2: Two-Sync Strategy

**Problem Solved:** Census can't distinguish between "property doesn't exist" vs "property needs update" when using a single sync, leading to:
- Chicken-and-egg problem with production IDs
- Upsert confusion
- Sync failures for new properties

**Solution:** Separate syncs with different behaviors:
- **Sync A (Create):** Uses RDS.id as key, creates new staging records
- **Sync B (Update):** Uses snappt_property_id_c as key, updates existing records with aggregated data

### Innovation 3: Business Rules in SQL

**Problem Solved:** Aggregation logic was unclear, untestable, and hidden in Census configuration.

**Solution:** All business rules defined in SQL views:
- Transparent (anyone can read the view definition)
- Testable (query the view to see results)
- Auditable (git history tracks changes)
- Flexible (easy to modify rules by updating view)

---

## 📅 IMPLEMENTATION TIMELINE

| Phase | Duration | Risk | Key Deliverables |
|-------|----------|------|------------------|
| **Phase 1: Foundation** | 3 days | Low | All Databricks views created |
| **Phase 2: Validation** | 2 days | Low | Test suite, validation reports |
| **Phase 3: Census Config** | 3 days | Medium | Both Census syncs configured |
| **Phase 4: Pilot** | 2 days | Medium | 100 properties synced successfully |
| **Phase 5: Full Rollout** | 5 days | Medium-High | All properties synced, 48h monitoring |
| **Phase 6: Operations** | 5 days | Low | Dashboard, alerts, runbooks |
| **Total** | **20 days (4 weeks)** | | **Production-ready system** |

---

## ✅ SUCCESS CRITERIA

The implementation will be considered successful when:

1. **Sync Coverage**
   - [ ] >1,000 properties created in product_property (from 1,081 in queue)
   - [ ] >7,500 properties updated in product_property (from 7,980 in queue)
   - [ ] <50 active properties missing from Salesforce (<0.5%)

2. **Data Quality**
   - [ ] Feature sync accuracy >99% (up from ~90%)
   - [ ] 507 P1 critical properties now visible in Salesforce
   - [ ] 799 feature mismatches resolved
   - [ ] 2,410 multi-property cases aggregating correctly

3. **Operational Excellence**
   - [ ] Census syncs running on schedule (15min/30min)
   - [ ] Error rate <1%
   - [ ] Zero P0/P1 incidents during 48h monitoring
   - [ ] Dashboard shows all green metrics

4. **Team Readiness**
   - [ ] Runbook documented and reviewed
   - [ ] Team trained on new architecture
   - [ ] Alerts configured and tested
   - [ ] On-call rotation updated

---

## 🚀 GETTING STARTED

To begin implementation:

1. **Review this README** - Understand the architecture and timeline

2. **Read Phase 1 documentation**
   - Open `IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md`
   - Review all SQL scripts
   - Understand each view's purpose

3. **Complete Pre-Flight Checklist**
   - [ ] Databricks workspace access confirmed
   - [ ] Database permissions verified (`crm.sfdc_dbx` schema)
   - [ ] Source tables accessible
   - [ ] Census workspace access (workspace ID: 33026)
   - [ ] Salesforce permissions confirmed
   - [ ] Stakeholders notified of implementation plan

4. **Execute Phase 1** (3 days)
   - Run all SQL scripts from Phase 1
   - Validate each view after creation
   - Run validation queries
   - Get sign-off before proceeding

5. **Continue through phases** in order
   - Don't skip phases
   - Complete all checklist items
   - Get sign-off at each phase gate

---

## 📊 MONITORING & MAINTENANCE

After implementation, the following operational procedures will be in place:

### Daily (5 minutes)
- Check dashboard: `sync_monitoring_dashboard`
- Verify queue sizes: <50 for create, stable for update
- Review error rate: should be 0%

### Weekly (30 minutes)
- Review sync health trends (last 7 days)
- Check feature accuracy (should be >99%)
- Review any incidents/issues

### Monthly (2 hours)
- Architecture review meeting
- Assess if aggregation rules still appropriate
- Review stakeholder feedback
- Plan improvements

### Alerts
- **P0 Critical:** Census sync down (no syncs in 2 hours)
- **P1 High:** Error rate >5%, properties missing >100
- **P2 Medium:** Queue backlog >200, accuracy <95%

---

## 🔄 ROLLBACK PLAN

If critical issues are discovered during or after rollout:

1. **Immediately pause both Census syncs**
2. Assess scope of damage (query SF for recent changes)
3. If <100 records affected → Manual correction
4. If >100 records affected → Restore from Salesforce backup
5. Investigate root cause
6. Fix issue in views or Census configuration
7. Re-test on small batch (10-20 properties)
8. Resume syncs when issue resolved

**Rollback Checklist:**
- [ ] Census Sync A paused
- [ ] Census Sync B paused
- [ ] Scope assessment completed
- [ ] Root cause identified
- [ ] Fix implemented and tested
- [ ] Stakeholders notified
- [ ] Incident report filed

---

## 📖 RELATED DOCUMENTATION

### Historical Context
- `RDS_SALESFORCE_DISCOVERY_REPORT.md` - Initial investigation (Jan 5, 2026)
- `PIPELINE_ID_MAPPING_ISSUE.md` - Three-tier ID system explained
- `SALESFORCE_SYNC_BLOCKED_PROPERTIES_REPORT.md` - 2,410 blocked properties
- `CENSUS_CONFIGURATION_ANALYSIS.md` - Census sync analysis
- `19122025/WORKFLOW_REDESIGN_QUESTIONS.md` - Business rules questions

### Database Documentation
- `database_erd/` - Complete RDS database documentation (75 tables)

### Previous Work
- `salesforce_property_sync/` - November 2025 feature sync work

---

## 💡 BUSINESS RULES SUMMARY

For quick reference, here are the aggregation business rules:

1. **Which properties contribute?**
   - Only ACTIVE properties
   - DISABLED properties are ignored

2. **Feature flags aggregation:**
   - UNION logic: If ANY active property has feature enabled → TRUE
   - Example: Property A has IDV=TRUE, Property B has IDV=FALSE → Result: IDV=TRUE

3. **Feature timestamps:**
   - Use EARLIEST enabled date across all active properties
   - Example: Property A enabled IDV on Jan 1, Property B enabled on Jan 5 → Result: Jan 1

4. **Property metadata:**
   - Use data from PRIMARY property (most recently updated active property)
   - Name, address, company, etc. from primary property

5. **Audit trail:**
   - Track which RDS properties contributed to each aggregated record
   - Store count of active properties per SFDC ID
   - Log all sync operations in audit table

---

## 👥 TEAM & CONTACTS

**Implementation Team:**
- Data Engineering: [Lead name]
- Database Architect: [Name]
- On-Call Engineer: [Name]
- Stakeholder: [Name]

**Support Contacts:**
- Census Support: support@getcensus.com
- Salesforce Admin: [Name]
- Data Team Slack: #data-team

---

## 🎓 TRAINING & KNOWLEDGE TRANSFER

A 1-hour training session will be scheduled after Phase 6 completion covering:

1. Architecture walkthrough
2. Dashboard demo
3. Alert configuration
4. Runbook review
5. Troubleshooting practice
6. Q&A

**Required Attendees:**
- All data engineers
- All on-call rotation members

**Optional Attendees:**
- Data analysts
- Sales operations
- CS operations

---

## 📈 SUCCESS METRICS

We will track these metrics to measure success:

| Metric | Baseline | Target | Measurement Frequency |
|--------|----------|--------|----------------------|
| Properties in Salesforce | 65% | 95%+ | Daily |
| Feature sync accuracy | 90.1% | 99%+ | Daily |
| Properties missing | 1,081 | <50 | Daily |
| Sync error rate | ~15% | <1% | Real-time |
| P1 properties synced | 0/507 | 507/507 | One-time |
| Multi-property cases handled | 0/2,410 | 2,410/2,410 | One-time |

---

## 🏆 EXPECTED IMPACT

### For Sales Team
- All properties with features will be visible in Salesforce
- Feature data will be accurate and up-to-date
- No more "property missing" issues

### For CS Team
- Complete view of customer properties and features
- Accurate billing information
- Better customer support with complete data

### For Data Team
- Reliable, maintainable sync architecture
- Clear business rules in SQL (not hidden in configs)
- Full auditability of all syncs
- 99%+ accuracy (no more firefighting)

### For Engineering
- Scalable architecture that handles growth
- Easy to debug and troubleshoot
- Self-documenting (view definitions = business rules)
- Foundation for future enhancements

---

## 🔮 FUTURE ENHANCEMENTS

After successful implementation, consider these improvements:

1. **Real-time sync** - Reduce frequency to 5 minutes
2. **Change data capture** - Only sync changed records (more efficient)
3. **Bi-directional sync** - Sync changes from SF back to RDS
4. **Advanced aggregation** - Weighted features, priority rules, custom logic
5. **Self-healing** - Automatic recovery from common errors
6. **ML-based alerting** - Predict issues before they happen

---

## ❓ FAQ

**Q: Why rebuild from scratch instead of fixing the existing sync?**

A: The existing architecture has fundamental design flaws:
- Chicken-and-egg problem with IDs
- No support for many-to-1 relationships
- No clear aggregation rules
- Single sync trying to do both creates and updates

Fixing these piecemeal would be more complex than a clean rebuild.

**Q: What's the risk of data corruption?**

A: Low risk because:
- Phase 1 is read-only views (no writes to SF)
- Phase 4 pilot tests on small batch
- Comprehensive validation at each phase
- Rollback plan documented
- 48-hour monitoring after rollout

**Q: How long will the rollout take?**

A: 3-4 weeks total:
- Week 1: Build and validate views
- Week 2: Configure Census and pilot test
- Week 3: Full rollout and monitoring
- Week 4: Operationalize (dashboard, alerts, training)

**Q: Will there be downtime?**

A: No. The new architecture runs in parallel with existing sync until we're ready to cut over.

**Q: What if something goes wrong during rollout?**

A: We pause syncs immediately, assess damage, and execute rollback plan. All procedures are documented.

**Q: How do we maintain this going forward?**

A: Daily health checks (5 min), weekly reviews (30 min), monthly architecture reviews (2 hours). Runbook covers all common issues.

**Q: Can we modify the aggregation rules later?**

A: Yes! That's a key benefit of this architecture. Business rules are defined in SQL views, so updating them is as simple as modifying the view definition.

---

## 📝 VERSION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-06 | Claude Code | Initial implementation plan |

---

## ✍️ SIGN-OFF

**Prepared by:** Claude Code
**Date:** January 6, 2026
**Status:** Ready for stakeholder review and approval

**Approvals Required:**

- [ ] Data Team Lead: _________________ Date: _______
- [ ] Engineering Manager: _________________ Date: _______
- [ ] Sales Operations: _________________ Date: _______
- [ ] CS Operations: _________________ Date: _______

**Once all approvals obtained, proceed with Phase 1 implementation.**

---

**For questions or clarifications, contact the Data Team.**

**Ready to begin? Start with Phase 1: `IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md`**
