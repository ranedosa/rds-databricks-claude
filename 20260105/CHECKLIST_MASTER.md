# MASTER CHECKLIST: 3-Day Implementation

**Project:** RDS → Salesforce Sync Architecture
**Implementer:** ____________________
**Start Date:** ____________________
**Target Completion:** ____________________ (3 days later)

---

## 📋 PROJECT OVERVIEW

### What You're Building
- **Goal:** Fix RDS → Salesforce property sync (1,081 missing + 7,980 to update)
- **Approach:** Ground-up rebuild with aggregation layer + 2 Census syncs
- **Timeline:** 3 days (6-8 hours each)
- **Risk:** Medium (good validation + pilot before full rollout)

### Expected Outcomes
- ✓ 1,081 properties created in Salesforce
- ✓ 7,980 properties updated with correct data
- ✓ 507 P1 critical properties visible
- ✓ 2,410 multi-property cases unblocked
- ✓ 97%+ feature accuracy
- ✓ Automated syncs every 15/30 minutes

---

## 📅 THREE-DAY TIMELINE

```
DAY 1: Foundation & Validation (6-8 hours)
├─ Morning: Build all Databricks views
├─ Afternoon: Comprehensive validation
└─ End: Views proven correct ✓

DAY 2: Census & Pilot (6-8 hours)
├─ Morning: Configure both Census syncs
├─ Afternoon: Test on 100 properties
└─ End: Pilot successful ✓

DAY 3: Full Rollout (6-8 hours)
├─ Morning: Sync 1,081 creates
├─ Midday: Sync 7,980 updates
└─ Afternoon: Validate + monitor ✓
```

---

## ✅ DAY 1: FOUNDATION & VALIDATION

**Date:** ____________ | **Duration:** ______ hours | **Status:** PENDING / IN PROGRESS / COMPLETE

### Pre-Flight
- [ ] All access verified (Databricks, Salesforce)
- [ ] Calendar blocked (6-8 hours)
- [ ] Implementation plan downloaded

### Morning (9:00 AM - 12:00 PM)
- [ ] View 1: `rds_properties_enriched` created _(9:00-9:30)_
- [ ] View 2: `properties_aggregated_by_sfdc_id` created ⭐ _(9:30-10:30)_
- [ ] View 3: `properties_to_create` created _(10:30-11:00)_
- [ ] View 4: `properties_to_update` created _(11:00-11:30)_
- [ ] Audit table + monitoring view created _(11:30-12:00)_
- [ ] **CHECKPOINT:** All 6 views working ✓

### Afternoon (12:30 PM - 5:00 PM)
- [ ] Data quality validation: 5/5 tests passed _(12:30-1:30)_
- [ ] **CRITICAL:** Park Kennedy case validates correctly _(1:30-2:30)_
- [ ] P1 Critical properties identified: ~507 _(1:30-2:30)_
- [ ] Multi-property cases validated: ~2,410 _(1:30-2:30)_
- [ ] Edge cases tested, no blocking issues _(2:30-3:30)_
- [ ] Pilot data exported (50+50 IDs saved) _(3:30-4:30)_
- [ ] Day 1 report created _(4:30-5:00)_

### Day 1 Results
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Views Created | 6 | ___/6 | ✓ / ✗ |
| Tests Passed | 5 | ___/5 | ✓ / ✗ |
| Park Kennedy | Correct | ✓ / ✗ | ✓ / ✗ |
| Pilot Data | Saved | ✓ / ✗ | ✓ / ✗ |

### GO/NO-GO for Day 2
- [ ] All views created successfully
- [ ] Park Kennedy validates correctly ← CRITICAL
- [ ] Pilot data exported (50+50 IDs)
- [ ] No critical blockers

**Decision:** GO ✓ / NO-GO ✗

**Notes:** _______________________________________________________________

---

## ✅ DAY 2: CENSUS CONFIGURATION & PILOT

**Date:** ____________ | **Duration:** ______ hours | **Status:** PENDING / IN PROGRESS / COMPLETE

### Pre-Flight
- [ ] Day 1 completed successfully
- [ ] Pilot IDs ready (50 CREATE + 50 UPDATE)
- [ ] Census workspace access verified
- [ ] Calendar blocked (6-8 hours)

### Morning (9:00 AM - 12:00 PM)
- [ ] Census Sync A configured (Create Only) _(9:00-10:30)_
  - [ ] Sync key: rds_property_id → snappt_property_id__c
  - [ ] Mode: Create Only ← CRITICAL
  - [ ] All 22 field mappings added
  - [ ] Pilot filter added (50 properties)
- [ ] Census Sync B configured (Update Only) _(10:30-12:00)_
  - [ ] Sync key: snappt_property_id_c → snappt_property_id__c
  - [ ] Mode: Update Only ← CRITICAL
  - [ ] Update mode: Replace ← CRITICAL
  - [ ] All mappings + aggregation fields
  - [ ] Pilot filter added (50 properties)
- [ ] **CHECKPOINT:** Both syncs configured ✓

### Afternoon (12:30 PM - 5:00 PM)
- [ ] Pre-pilot validation complete _(12:30-1:00)_
- [ ] **Pilot Sync A:** 50 properties created _(1:00-2:00)_
  - Created: ___/50 (target: 48+)
  - Error rate: ___% (target: <5%)
- [ ] **Pilot Sync B:** 50 properties updated _(2:00-3:00)_
  - Updated: ___/50 (target: 48+)
  - Error rate: ___% (target: <3%)
  - Park Kennedy correct: ✓ YES / ✗ NO
- [ ] Pilot analysis & GO/NO-GO decision _(3:00-4:00)_
- [ ] Day 3 monitoring prepared _(4:00-5:00)_
- [ ] Stakeholders notified of Day 3 rollout

### Day 2 Results
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Sync A Config | ✓ | ✓ / ✗ | ✓ / ✗ |
| Sync B Config | ✓ | ✓ / ✗ | ✓ / ✗ |
| Pilot Create | 48+/50 | ___/50 | ✓ / ✗ |
| Pilot Update | 48+/50 | ___/50 | ✓ / ✗ |
| Feature Accuracy | >97% | ___% | ✓ / ✗ |
| Park Kennedy | Correct | ✓ / ✗ | ✓ / ✗ |

### GO/NO-GO for Day 3
- [ ] Both Census syncs configured correctly
- [ ] Pilot Sync A: 48+ of 50 created
- [ ] Pilot Sync B: 48+ of 50 updated
- [ ] Feature accuracy >97%
- [ ] Park Kennedy correct ← CRITICAL
- [ ] Error rate <3%
- [ ] No critical issues discovered

**Decision:** GO ✓ / NO-GO ✗

**Notes:** _______________________________________________________________

---

## ✅ DAY 3: FULL ROLLOUT & MONITORING

**Date:** ____________ | **Duration:** ______ hours | **Status:** PENDING / IN PROGRESS / COMPLETE

⚠️ **PRODUCTION ROLLOUT - POINT OF NO RETURN**

### Pre-Flight
- [ ] Day 2 pilot successful
- [ ] Stakeholder approval obtained
- [ ] Rollout window scheduled: ____________
- [ ] Salesforce status: 🟢 All green
- [ ] Calendar completely clear (6-8 hours)

### Morning (9:00 AM - 12:00 PM)
- [ ] Final pre-rollout checks complete _(9:00-9:30)_
  - [ ] View health good
  - [ ] SF API limits sufficient (>50%)
  - [ ] Baseline snapshot taken
- [ ] Sync A prepared (filter removed) _(9:30-9:45)_
- [ ] Stakeholders notified _(9:45-10:00)_
- [ ] **🚀 Sync A triggered:** ____________ (time) _(10:00)_
- [ ] Sync A monitored: Error rate ___% _(10:05-10:35)_
- [ ] Sync A validated: ___/1,031 created _(10:35-11:00)_
- [ ] **CHECKPOINT:** Sync A successful (>970 created, <5% errors) ✓
- [ ] Break & prepare Sync B _(11:00-11:30)_

### Midday (11:30 AM - 2:00 PM)
- [ ] Sync B prepared (filter removed) _(11:30-11:40)_
- [ ] **🚀 Sync B triggered:** ____________ (time) _(11:45)_
- [ ] Sync B monitored: Error rate ___% _(11:45-1:15)_
- [ ] Sync B validated: ___/7,930 updated _(1:15-2:00)_
- [ ] **CHECKPOINT:** Sync B successful (>7,500 updated, <5% errors) ✓

### Afternoon (2:00 PM - 5:00 PM)
- [ ] Comprehensive validation complete _(2:00-3:00)_
  - [ ] Properties missing: ___ (target: <100)
  - [ ] P1 properties: ___ (target: 500+)
  - [ ] Feature accuracy: ___% (target: >97%)
  - [ ] Multi-property: ___ (target: ~2,410)
- [ ] Issues investigated & resolved _(3:00-3:30)_
- [ ] Census schedules enabled (15min/30min) _(3:30-4:00)_
- [ ] Ongoing monitoring created _(4:00-4:30)_
- [ ] Final report & runbook created _(4:30-5:00)_
- [ ] Stakeholders notified of completion

### Day 3 Results
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Created (Sync A) | ~1,031 | ______ | ✓ / ✗ |
| Updated (Sync B) | ~7,930 | ______ | ✓ / ✗ |
| P1 Properties | 507 | ______ | ✓ / ✗ |
| IDV Accuracy | >97% | ___% | ✓ / ✗ |
| Bank Accuracy | >97% | ___% | ✓ / ✗ |
| Missing | <100 | ______ | ✓ / ✗ |
| Error Rate | <5% | ___% | ✓ / ✗ |

### Implementation Complete
- [ ] All success criteria met
- [ ] Automated syncs running
- [ ] Monitoring in place
- [ ] Runbook documented
- [ ] Stakeholders notified

**Final Status:** SUCCESS ✓ / PARTIAL ⚠️ / NEEDS WORK ✗

**Notes:** _______________________________________________________________

---

## 📊 FINAL PROJECT METRICS

### Time Investment
| Day | Planned | Actual | Notes |
|-----|---------|--------|-------|
| Day 1 | 6-8 hrs | _____ hrs | ________________ |
| Day 2 | 6-8 hrs | _____ hrs | ________________ |
| Day 3 | 6-8 hrs | _____ hrs | ________________ |
| **Total** | **18-24 hrs** | **_____ hrs** | |

### Success Metrics
| Metric | Before | Target | Actual | Improvement |
|--------|--------|--------|--------|-------------|
| Properties in SF | 65% | 95%+ | ___% | +___% |
| Feature Accuracy | 90.1% | 97%+ | ___% | +___% |
| Properties Missing | 1,081 | <100 | _____ | -_____ |
| P1 Properties Synced | 0 | 507 | _____ | +_____ |
| Multi-Property Unblocked | 0 | 2,410 | _____ | +_____ |
| Sync Error Rate | ~15% | <5% | ___% | -___% |

### Business Impact
- ✓ Sales team can see _____ more properties with features
- ✓ CS team has accurate data for _____ previously blocked properties
- ✓ _____ P1 critical properties now visible
- ✓ Sync errors reduced by ____%
- ✓ Manual interventions eliminated (saving _____ hours/week)

---

## 🎯 POST-IMPLEMENTATION CHECKLIST

### Week 1 (Days 4-10) - Daily Monitoring
- [ ] **Day 4:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 5:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 6:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 7:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 8:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 9:** Run `daily_health_check`, review logs, address issues
- [ ] **Day 10:** Run `daily_health_check`, review logs, address issues

### Week 2 - Follow-Up Tasks
- [ ] Fix remaining issues (if any): ______________________________
- [ ] Run full validation suite (from 4-week plan)
- [ ] Write comprehensive documentation
- [ ] Set up automated alerts (Slack, email, PagerDuty)
- [ ] Create Databricks dashboard
- [ ] Schedule team training session: ____________ (date)
- [ ] Retrospective meeting: ____________ (date)

### Ongoing Operations
- [ ] **Daily (5 min):** Health check query
- [ ] **Weekly (30 min):** Feature accuracy check, review trends
- [ ] **Monthly (2 hrs):** Architecture review, assess rules, plan improvements

---

## 📞 CONTACTS & RESOURCES

**Key Contacts:**
- Implementer: ____________________
- Data Team Lead: ____________________
- On-Call: ____________________
- Stakeholder: ____________________

**Documentation:**
- Master Overview: `NEW_SYNC_ARCHITECTURE_README.md`
- Day 1 Details: `THREE_DAY_IMPLEMENTATION_PLAN.md`
- Day 3 Details: `THREE_DAY_PLAN_DAY3.md`
- Daily Operations: `QUICK_RUNBOOK.md`

**Checklists:**
- Day 1: `CHECKLIST_DAY1.md` ← Print this for Day 1
- Day 2: `CHECKLIST_DAY2.md` ← Print this for Day 2
- Day 3: `CHECKLIST_DAY3.md` ← Print this for Day 3
- Master: `CHECKLIST_MASTER.md` ← This file

**Census Syncs:**
- Sync A (Create): ____________ (Census sync ID)
- Sync B (Update): ____________ (Census sync ID)

---

## 🎓 LESSONS LEARNED

**What worked well:**
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

**What was challenging:**
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

**What we'd do differently next time:**
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

**Recommendations for others:**
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

---

## ✅ PROJECT SIGN-OFF

**Implementation Complete:**

Date: ____________________
Total Duration: ______ hours over ______ days
Final Status: SUCCESS ✓ / PARTIAL SUCCESS ⚠️ / NEEDS ADDITIONAL WORK ✗

**Signatures:**

Implementer: ____________________ Date: ____________

Data Team Lead: ____________________ Date: ____________

Stakeholder: ____________________ Date: ____________

---

## 🎉 CONGRATULATIONS!

**You've successfully implemented the new RDS → Salesforce sync architecture!**

### What You Built:
- ✓ Smart aggregation layer (handles many-to-1 relationships)
- ✓ Two-sync strategy (create vs update)
- ✓ Transparent business rules in SQL
- ✓ Full audit trail
- ✓ Automated syncs every 15/30 minutes
- ✓ Comprehensive monitoring

### Impact:
- 1,000+ properties now in Salesforce
- 7,500+ properties updated correctly
- 500+ critical properties visible to Sales/CS
- 2,400+ blocked properties unblocked
- 97%+ feature accuracy
- Scalable, maintainable architecture

**Thank you for your hard work!** Now maintain and monitor. 🚀

---

**For questions:** Contact implementer or refer to documentation listed above.
