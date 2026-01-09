# Print-Friendly Checklists - How to Use

**Created:** January 6, 2026
**For:** 3-Day Implementation of RDS → Salesforce Sync Architecture

---

## 📁 WHAT YOU HAVE

You now have **4 print-friendly checklists** to guide you through the 3-day implementation:

### 1. **CHECKLIST_MASTER.md** ⭐ START HERE
- **Purpose:** High-level overview of entire project
- **Use:** Track overall progress across all 3 days
- **Print:** Print once, keep on desk throughout project
- **Contents:**
  - 3-day timeline at a glance
  - Daily status tracking
  - GO/NO-GO decision points
  - Final success metrics
  - Post-implementation tasks

### 2. **CHECKLIST_DAY1.md**
- **Purpose:** Hour-by-hour checklist for Day 1
- **Use:** Follow step-by-step on Day 1 (Foundation & Validation)
- **Print:** Print morning of Day 1
- **Duration:** 6-8 hours
- **Contents:**
  - Pre-flight checks
  - Create 6 views (4 views + audit table + monitoring)
  - Data quality validation (5 tests)
  - Business case validation (Park Kennedy, P1 properties, etc.)
  - Edge case testing
  - Export pilot data (50+50 properties)
  - GO/NO-GO for Day 2

### 3. **CHECKLIST_DAY2.md**
- **Purpose:** Hour-by-hour checklist for Day 2
- **Use:** Follow step-by-step on Day 2 (Census & Pilot)
- **Print:** Print morning of Day 2
- **Duration:** 6-8 hours
- **Contents:**
  - Configure Census Sync A (22 field mappings)
  - Configure Census Sync B (27 field mappings)
  - Execute pilot: Create 50 properties
  - Execute pilot: Update 50 properties
  - Validate Park Kennedy case
  - GO/NO-GO for Day 3

### 4. **CHECKLIST_DAY3.md**
- **Purpose:** Hour-by-hour checklist for Day 3
- **Use:** Follow step-by-step on Day 3 (Full Rollout)
- **Print:** Print morning of Day 3
- **Duration:** 6-8 hours
- **Contents:**
  - Pre-rollout checks
  - Execute Sync A: ~1,031 creates
  - Execute Sync B: ~7,930 updates
  - Comprehensive validation
  - Enable automated schedules
  - Create monitoring & runbook
  - Final stakeholder communication

---

## 📋 HOW TO USE THESE CHECKLISTS

### Before Day 1:
1. **Print all 4 checklists** (or view on tablet/second monitor)
2. Read `CHECKLIST_MASTER.md` to understand the big picture
3. Review `CHECKLIST_DAY1.md` to see what Day 1 entails
4. Block your calendar (6-8 hours per day, 3 consecutive days)
5. Verify all access (Databricks, Census, Salesforce)

### Each Morning:
1. Open the checklist for that day
2. Complete pre-flight section BEFORE starting
3. Follow the checklist step-by-step
4. Check off each box as you complete it
5. Fill in actual values (counts, times, results)
6. Note any issues in the space provided

### End of Each Day:
1. Complete the day's final report section
2. Update `CHECKLIST_MASTER.md` with that day's results
3. Make GO/NO-GO decision for next day
4. If GO: prep for tomorrow
5. If NO-GO: document blockers, schedule fix time

### After Day 3:
1. Complete final metrics in `CHECKLIST_MASTER.md`
2. Keep master checklist for reference
3. Use for post-implementation review
4. Refer to Week 1-2 checklists for follow-up tasks

---

## ✅ CHECKLIST FEATURES

Each daily checklist includes:

- **Time estimates** for each section
- **Clear instructions** for each task
- **Validation queries** to verify work
- **Space to record actual values** (fill in blanks)
- **GO/NO-GO decision points** at critical junctures
- **Troubleshooting notes** for common issues
- **References** to detailed docs for more info

---

## 🎯 CRITICAL CHECKPOINTS

Watch for these **GO/NO-GO decision points**:

### Day 1 → Day 2:
- ✅ All 6 views created successfully
- ✅ Park Kennedy validates correctly ← CRITICAL!
- ✅ Pilot data exported (50+50 IDs saved)
- ✅ No critical blockers

**If any ✗:** Fix before Day 2. Don't proceed with broken foundation.

### Day 2 → Day 3:
- ✅ Both Census syncs configured
- ✅ Pilot: 48+ of 50 created
- ✅ Pilot: 48+ of 50 updated
- ✅ Feature accuracy >97%
- ✅ Park Kennedy correct ← CRITICAL!
- ✅ Error rate <3%

**If any ✗:** Fix before Day 3. Don't do full rollout if pilot fails.

### Day 3 Checkpoints:
- **After Sync A:** 1,000+ created, error rate <5%
- **After Sync B:** 7,500+ updated, error rate <5%
- **Final:** All success criteria met

**If ✗:** Document, investigate, may need remediation work.

---

## 📊 WHAT TO FILL IN

As you work, fill in these blanks on checklists:

### Actual Values:
- Row counts (e.g., "Expected: ~1,081 | Actual: ______")
- Percentages (e.g., "Error rate: ____%")
- Times (e.g., "Start time: ____________")
- File locations (e.g., "Pilot IDs saved: ____________")

### Status Indicators:
- ✓ or ✗ for YES/NO questions
- PASS or FAIL for test results
- GO or NO-GO for decisions

### Notes:
- Document any issues in "Notes" sections
- Write resolutions applied
- Flag items for follow-up

---

## 🚨 WHEN TO STOP

**STOP immediately if:**

1. **Day 1:** Park Kennedy case fails validation
   - This means aggregation logic is broken
   - Must fix before proceeding

2. **Day 2:** Pilot has >10% error rate
   - This indicates systematic problem
   - Must fix before full rollout

3. **Day 3:** Salesforce status page shows issues
   - Don't rollout during SF outage
   - Reschedule for next day

4. **Any day:** Census sync shows >10% error rate
   - Pause sync immediately
   - Investigate root cause
   - Fix before continuing

**How to stop:**
- Pause Census syncs (if running)
- Document where you stopped
- Note all error details
- Schedule troubleshooting session
- Resume when issue resolved

---

## 💡 TIPS FOR SUCCESS

### General:
- ✅ **Print checklists** - physical paper helps track progress
- ✅ **Use pen** - check boxes and fill in values as you go
- ✅ **Don't skip validation** - each test catches different issues
- ✅ **Take breaks** - 30 min between major sections
- ✅ **Stay hydrated** - 6-8 hours is a long day
- ✅ **No distractions** - Slack DND, no meetings

### Day 1:
- Park Kennedy is your canary - if it fails, stop immediately
- Export pilot IDs carefully - you NEED these for Day 2
- Don't rush validation - it saves time on Days 2-3

### Day 2:
- Double-check every field mapping (Census is case-sensitive)
- Verify sync modes: A = "Create Only", B = "Update Only"
- Update mode must be "Replace" (not Merge)
- Save pilot IDs in Census filters (you'll remove them Day 3)

### Day 3:
- Check Salesforce status page BEFORE starting
- Monitor constantly during syncs (every 5-10 minutes)
- Have stakeholder approval in writing
- Don't rollback unless truly critical (>10% errors)

---

## 📞 IF YOU GET STUCK

### During Implementation:
1. **Check detailed docs:**
   - `THREE_DAY_IMPLEMENTATION_PLAN.md` (Days 1-2)
   - `THREE_DAY_PLAN_DAY3.md` (Day 3)
2. **Review architecture:**
   - `NEW_SYNC_ARCHITECTURE_README.md`
3. **Search for error message**
   - Census logs
   - Implementation plan PDFs

### Common Issues:
- **SQL errors:** Check table/column names (copy from plan)
- **Census errors:** Verify field mappings (case-sensitive)
- **Permission errors:** Check access to all systems
- **Validation fails:** Document, investigate, decide if blocking

### When to Ask for Help:
- Park Kennedy fails validation (Day 1)
- Pilot has >10% errors (Day 2)
- Full rollout has critical issues (Day 3)
- Unclear what a checklist item means

---

## 📚 REFERENCE DOCUMENTS

### For detailed instructions:
- **Architecture:** `NEW_SYNC_ARCHITECTURE_README.md`
- **Day 1-2:** `THREE_DAY_IMPLEMENTATION_PLAN.md`
- **Day 3:** `THREE_DAY_PLAN_DAY3.md`
- **Quick Start:** `QUICK_START_GUIDE.md` (executive summary)

### After implementation:
- **Daily ops:** `QUICK_RUNBOOK.md` (you'll create this Day 3)
- **Monitoring:** Views you create (daily_health_check, etc.)
- **Full plan:** 4-week plan files (for reference if needed)

---

## ✨ CHECKLIST EXAMPLE

Here's how to use a checklist section:

```
### Execute Pilot Sync A - Create 50 (1:00-2:00)

**Trigger Sync:**
- [ ] Go to Census → Sync A
- [ ] Verify filter shows 50 properties
- [✓] Click "Trigger Sync Now"          ← Checked off
- [✓] Start time: 1:05 PM               ← Filled in

**Monitor (10-15 minutes):**
- [✓] Watch Census dashboard
- [✓] Records processed: 50              ← Filled in
- [✓] Errors: 2                          ← Filled in
- [✓] Error rate: 4%                     ← Filled in

**Validate Results:**
- [✓] Sync completed (not still running)
- [✓] Census stats:
  - Created: 48/50                       ← Filled in
  - Errors: 2                            ← Filled in
  - Error rate: 4%                       ← Filled in
```

---

## 🎯 SUCCESS CRITERIA SUMMARY

By end of Day 3, you should have:

| Metric | Target | Your Actual |
|--------|--------|-------------|
| Properties Created | ~1,031 | ______ |
| Properties Updated | ~7,930 | ______ |
| P1 Properties | 507 | ______ |
| Feature Accuracy | >97% | ______% |
| Properties Missing | <100 | ______ |
| Error Rate | <5% | ______% |

**If all ✓:** Implementation successful! 🎉

**If some ✗:** Document issues, plan remediation, but likely still a success if close to targets.

---

## 📋 CHECKLIST FILES SUMMARY

| File | When to Use | Print? | Duration |
|------|-------------|--------|----------|
| `CHECKLIST_MASTER.md` | All 3 days | ✓ Print once | Reference |
| `CHECKLIST_DAY1.md` | Day 1 only | ✓ Print Day 1 | 6-8 hours |
| `CHECKLIST_DAY2.md` | Day 2 only | ✓ Print Day 2 | 6-8 hours |
| `CHECKLIST_DAY3.md` | Day 3 only | ✓ Print Day 3 | 6-8 hours |
| `CHECKLISTS_README.md` | Before starting | ✓ Print (optional) | Read once |

---

## 🚀 READY TO START?

1. **Print all checklists** (or open on second monitor)
2. **Read CHECKLIST_MASTER.md** (10 minutes)
3. **Review CHECKLIST_DAY1.md** (10 minutes)
4. **Complete pre-flight** (verify access)
5. **Block calendar** (3 days, 6-8 hours each)
6. **Set start date:** ____________
7. **Begin Day 1!**

---

## 🎓 FINAL TIPS

- **Be methodical:** Check every box, fill in every blank
- **Don't skip:** Each step builds on previous ones
- **Validate often:** Catches issues early when easy to fix
- **Take breaks:** You'll make better decisions when fresh
- **Stay calm:** If issues arise, checklist has troubleshooting
- **Document everything:** Future you will thank present you
- **Celebrate milestones:** End of each day is an achievement!

---

**Good luck with your implementation!** 🚀

You've got comprehensive checklists, detailed docs, and a proven plan.

**You can do this!** 💪

---

**Questions?** Review the implementation plan docs or contact your data team lead.
