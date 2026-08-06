# Hub Schema Quick Reference

## Tables and columns

```
matters
  matter_id TEXT, name TEXT, agency TEXT, investigation_type TEXT,
  issued_date TEXT, hold_date TEXT, lead_partner TEXT, description TEXT, status TEXT

subpoena_categories
  matter_id TEXT, category_code TEXT, title TEXT, date_start TEXT, date_end TEXT,
  request_text TEXT, topic_tags TEXT

production_stats
  matter_id TEXT, batch_id TEXT, batch_date TEXT, category_code TEXT,
  produced_count INTEGER, withheld_count INTEGER, responsive_count INTEGER,
  nonresponsive_count INTEGER, status TEXT, zero_claim_reason TEXT, notes TEXT

custodian_sources
  source_id TEXT, matter_id TEXT, custodian_name TEXT, role TEXT,
  source_type TEXT, source_label TEXT, status TEXT, event_date TEXT,
  post_hold INTEGER, category_impacts TEXT, issue_tags TEXT, notes TEXT

review_documents
  doc_id TEXT, matter_id TEXT, title TEXT, doc_date TEXT, custodian_name TEXT,
  source_system TEXT, category_code TEXT, responsiveness TEXT,
  privilege_status TEXT, produced_status TEXT, issue_tags TEXT, summary TEXT

privilege_entries
  entry_id TEXT, matter_id TEXT, category_code TEXT, custodian_name TEXT,
  doc_count INTEGER, withheld_count INTEGER, logged_count INTEGER,
  issue_type TEXT, third_party INTEGER, notes TEXT

qc_findings
  finding_id TEXT, matter_id TEXT, batch_id TEXT, issue_type TEXT,
  doc_count INTEGER, affected_category TEXT, source_ref TEXT,
  severity TEXT, notes TEXT

retention_events
  event_id TEXT, matter_id TEXT, record_type TEXT, event_date TEXT,
  hold_date TEXT, policy_section TEXT, retention_period_months INTEGER,
  volume_count INTEGER, volume_unit TEXT, status TEXT,
  affected_categories TEXT, source_ref TEXT, notes TEXT

remediation_actions
  action_id TEXT, matter_id TEXT, action_type TEXT, priority TEXT,
  severity TEXT, owner TEXT, target_ref TEXT, due_days INTEGER,
  description TEXT
```

## Noise detection checklist

For each record, check these indicators before including as a material finding:

- [ ] Description/notes say "routine" or "noise" explicitly
- [ ] Description says "not one of the stable exception records"
- [ ] Notes say "no production-impacting issue has been escalated"
- [ ] Notes say "similar to escalated records in another matter"
- [ ] Notes say "re-sampling before escalation" needed
- [ ] Notes say "included to create similar labels across matters"
- [ ] Notes say "ordinary review variance"
- [ ] Notes say "minor metadata normalization issues" as sole issue
- [ ] Action ID contains "NOISE" suffix
- [ ] Summary mentions "noisy search result set"

If ANY are true, the record is likely noise. If NONE are true and the record has a concrete, specific issue description, it's material.

## Date comparison rule

- `hold_date` is the litigation hold date
- Events with `event_date < hold_date` are pre-hold
- Events with `event_date >= hold_date` are post-hold
- Post-hold losses/destructions are typically higher severity than pre-hold
