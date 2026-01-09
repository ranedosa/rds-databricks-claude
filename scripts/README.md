# Scripts Directory

Automation scripts for RDS to Salesforce sync operations.

## daily_validation.py

Automated daily validation script that checks system health.

### What it checks:
- ✅ Coverage hasn't dropped below 90%
- ✅ NULL company names spike (<50)
- ✅ Syncs ran recently (within 2 hours)
- ✅ Queue sizes within normal range

### Usage:

```bash
# Run manually
python3 scripts/daily_validation.py

# Run with verbose output (shows metrics)
python3 scripts/daily_validation.py --verbose

# Dry run (no alerts sent)
python3 scripts/daily_validation.py --dry-run
```

### Scheduling:

**Option A: Cron (recommended for server deployment)**
```bash
# Add to crontab (runs daily at 3:00 AM)
0 3 * * * cd /path/to/rds_databricks_claude && python3 scripts/daily_validation.py
```

**Option B: Databricks Job**
1. Create Python Notebook in Databricks
2. Copy script content
3. Schedule: Daily at 3:00 AM PT
4. Timeout: 10 minutes
5. Retry: 2 times

**Option C: Manual (for testing)**
```bash
# Run manually when needed
python3 scripts/daily_validation.py
```

### Exit Codes:
- `0`: All checks passed
- `1`: One or more checks failed
- `2`: Fatal error (script crashed)

### Dependencies:
```bash
pip install databricks-sql-connector
```

### Environment Variables:
```bash
export DATABRICKS_TOKEN="your-token-here"
```

### Alert Configuration:

Currently prints alerts to console. To enable email/Slack:

1. **Email (SendGrid):**
   ```bash
   pip install sendgrid
   export SENDGRID_API_KEY="your-key-here"
   ```
   Uncomment SendGrid code in `send_alert_notification()` function

2. **Slack:**
   ```bash
   pip install slack-sdk
   export SLACK_BOT_TOKEN="your-token-here"
   ```
   Uncomment Slack code in `send_alert_notification()` function

### Testing:

```bash
# Test with dry run (no alerts sent)
python3 scripts/daily_validation.py --dry-run --verbose

# Verify all checks pass
echo $?  # Should be 0 if healthy
```

### Integration with Operations:

This script is referenced in:
- `OPERATIONS_RUNBOOK.md` - Daily operations section
- `PRODUCTION_READINESS_CHECKLIST.md` - Phase 1.4
- Production plan: `/Users/danerosa/.claude/plans/sparkling-hugging-axolotl.md`

## Future Scripts

Additional automation scripts to be added:
- `send_alert.py` - Centralized alert helper (email/Slack/PagerDuty)
- `sync_report.py` - Weekly sync performance report
- `cleanup_duplicates.py` - Remove duplicate Salesforce records
- `test_sync.py` - End-to-end sync validation

## Documentation

For full operational procedures, see:
- `OPERATIONS_RUNBOOK.md` - Complete operations guide
- `20260105/QUICK_REFERENCE.md` - Quick command reference
- `COMPREHENSIVE_PROJECT_CONTEXT.md` - Full project history
