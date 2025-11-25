# Phase 2 Checklist: Census Configuration

**Time:** 1 hour
**Status:** Ready to start

---

## Quick Start

**Step 1: Create Model (15 min)**
- [ ] Go to Census → Models → New Model
- [ ] Name: `New Properties with Features`
- [ ] Connection: Databricks
- [ ] Table: `crm.sfdc_dbx.new_properties_with_features`
- [ ] Preview data - verify 45 fields visible
- [ ] Save

**Step 2: Create Sync (20 min)**
- [ ] Go to Census → Syncs → New Sync
- [ ] Source: `New Properties with Features` model
- [ ] Destination: Salesforce `Product_Property__c`
- [ ] Sync Key: `Reverse_ETL_ID__c`
- [ ] Sync Behavior: **Upsert**
- [ ] Map all 45 fields (see guide for list)
- [ ] Name: `New Properties → Salesforce (INSERT with Features)`
- [ ] Save

**Step 3: Test (15 min)**
- [ ] Run sync with limit: First 10 records
- [ ] Check Census results: 10 created, 0 failed
- [ ] Check Salesforce: 10 new records visible
- [ ] Verify property data correct
- [ ] Verify feature fields populated

**Step 4: Full Run (10 min)**
- [ ] Run sync without limit
- [ ] Monitor progress
- [ ] Check results: Low failure rate
- [ ] Spot check in Salesforce

**Step 5: Schedule (5 min)**
- [ ] Configure schedule: Daily at 2:00 AM
- [ ] Enable schedule
- [ ] Test schedule with "Run Now"

**Step 6: Alerts (5 min)**
- [ ] Set up failure notifications
- [ ] Configure email/Slack alerts

---

## Field Mapping Quick Reference

**Property Fields (21):**
All fields map source → destination with same name:
- snappt_property_id_c
- reverse_etl_id_c
- name, entity_name_c
- address_street_s, address_city_s, address_state_code_s, address_postal_code_s
- phone_c, email_c, website_c, logo_c
- unit_c, status_c
- company_id_c, company_short_id_c, short_id_c
- bank_statement_c, paystub_c
- unit_is_required_c, phone_is_required_c
- identity_verification_enabled_c
- not_orphan_record_c, trigger_rollups_c

**Feature Fields (23):**
All map source → destination with same name:
- fraud_detection_enabled_c, fraud_detection_start_date_c, fraud_detection_updated_date_c
- income_verification_enabled_c, income_verification_start_date_c, income_verification_updated_date_c
- id_verification_enabled_c, id_verification_start_date_c, id_verification_updated_date_c
- idv_only_enabled_c, idv_only_start_date_c, idv_only_updated_date_c
- connected_payroll_enabled_c, connected_payroll_start_date_c, connected_payroll_updated_date_c
- bank_linking_enabled_c, bank_linking_start_date_c, bank_linking_updated_date_c
- verification_of_rent_enabled_c, vor_start_date_c, vor_updated_date_c

**Pro tip:** Field names match exactly - Census should auto-map most fields!

---

## Validation Checklist

After setup:
- [ ] Model shows correct data in preview
- [ ] Sync created with 45 field mappings
- [ ] Test run: 10/10 records succeeded
- [ ] Feature data visible in Salesforce
- [ ] Full run completed
- [ ] Schedule enabled (daily 2am)
- [ ] Alerts configured
- [ ] Documented sync URL

---

## Quick Troubleshooting

**Can't find view in Census?**
→ Check connection has access to `crm` catalog
→ Refresh Census schema browser

**Sync key not found?**
→ Try `snappt_property_id_c` instead
→ Or ask SF admin to mark field as External ID

**Records failing?**
→ Check Census error details
→ May need to sync in batches (50 at a time)
→ Could be Salesforce Flow hitting limits again

**Feature data all False?**
→ Verify source data has features enabled
→ Check field mappings are correct

---

## After Phase 2

**What's Next:**
1. Run your existing feature update sync (fixes 2,815 properties)
2. Schedule it hourly/daily
3. Monitor both syncs for a week
4. System is fully automated!

**You'll Have:**
- ✅ New properties sync automatically with features
- ✅ Existing properties stay accurate
- ✅ No manual work needed
- ✅ Self-healing system

---

## Links

**Full Guide:** `/docs/PHASE_2_CENSUS_CONFIGURATION.md`
**Future Architecture:** `/docs/FUTURE_ARCHITECTURE_automated_property_sync.md`
**Your Existing Sync:** https://app.getcensus.com/workspaces/33026/syncs/3326019/overview

---

**Let's do this!** 🚀
