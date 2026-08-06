# Legal-review classification & prioritization playbook

Map hub evidence to the fields every task template asks for. Templates rename enums per task, so
match on **meaning** and then pick the closest enum value the current `answer_template.json`
offers. Anchor each finding on a stable hub record ID.

## Issue taxonomy → classification → action → owner → priority

| Evidence (what you see in the hub) | Issue meaning | Severity | Production impact | Action | Owner | Priority |
|---|---|---|---|---|---|---|
| `retention_events.status = post_hold_loss` / `post_hold_partial_recovery`; or a custodian source `status = lost` (device/mailbox lost after hold) | Preservation failure after the legal hold; spoliation exposure | critical (source fully lost) / high (partial) | source_lost | disclose preservation issue / disclose to government (+ forensic_recovery if any recovery path) | outside_counsel (disclose); forensics/ediscovery_vendor (recover) | **P0** |
| `retention_events.status = should_exist_missing` (record that must exist per retention period is absent) | Missing required record | high | missing_record / source_missing | locate_missing_record | compliance_audit / records_management | P1–P2 |
| `retention_events.status = system_loss` / `auto_purged` **and no archive** | Active-system communication gap | medium | source_missing / underproduced | document_system_gap / monitor | it_messaging / ediscovery_vendor | P2 |
| custodian source `status = available` + `issue_tags` include `archive_available` (e.g. `teams_archive`, `email_archive`) | Archive that **limits** an otherwise-lost category (a remediation *source*, not a loss) | medium | source_available | search_archive / collect_archive | ediscovery_vendor | P1 |
| custodian source `status = not_collected` (personal email/phone/board site/Signal/SMS not collected) | Collection gap on a required source | high | source_missing | collect_source / collect_personal_device / collect_signal_messages | client_it / forensics | P1 |
| `privilege_entries.issue_type = third_party_waiver` (`third_party = 1`; privileged docs sent to a third party) | Privilege waiver / exposure | high | privilege_exposure / privilege_waiver | waiver_assessment_and_disclosure | privilege_counsel | P1 |
| `qc_findings.issue_type = miscoded_privilege` (privileged docs coded nonprivileged / exposed in production) | Privilege miscoding | high | privilege_exposure / recode_needed | privilege_recode_and_log / qc_remediation | review_qc / privilege_team | P1 |
| `production_stats.status = zero_claim_contradicted`; or `qc_findings.issue_type` in {`miscoded_nonresponsive`,`zero_claim_contradiction`}; supported by short-token `DOC-…` with `responsiveness=responsive`, `produced_status=not_produced` | Responsiveness miscode / zero-production claim contradicted | high | underproduced / not_produced | recode_and_produce | review_qc / review_vendor | P1 |
| `privilege_entries.issue_type = incomplete_log` with a real gap (`withheld_count > logged_count`) | Privilege-log gap (withheld but not fully logged) | high | withheld_unlogged | supplement_privilege_log | privilege_team | P1 |
| `privilege_entries.issue_type = over_designated` (business-only docs withheld as privileged) | Over-designation | medium | recode_needed / no_production_impact | downgrade / qc_remediation | privilege_team | **P2** (optional — see notes) |
| `retention_events` pre-hold, policy-compliant destruction (`policy_section` set, `event_date` before `hold_date`) | Benign policy loss — factually report, **do not remediate** | low | no_production_impact | no_action_policy_loss | records_management | P3 |
| `issue_tags = routine`; qc `family_break`/`date_normalization`/`near_duplicate`; notes like "ordinary review variance", "no production-impacting issue", "already remediated", "included to create similar labels"; docs already `produced` | Decoy / noise | — | — | **exclude entirely** | — | — |

### Priority mapping
`critical → P0`; `high` **with government-disclosure/preservation exposure → P0**, otherwise
`high → P1`; `medium → P2`; `low → P3`. `production_ready` / `rolling_production_ready` is
`false` whenever any material gap exists.

### Ordering ladder for the action plan (rank 1 = highest)
1. Disclose preservation loss / lost personal device (+ forensic recovery)  → P0
2. Locate should-exist-missing required records
3. Privilege waiver (third-party) → assess & disclose
4. Privilege miscoding → recode & log
5. Responsiveness miscode / zero-claim → recode & produce
6. Collect uncollected required source
7. Supplement incomplete privilege log
8. Search/collect available archive
9. Over-designation downgrade (P2)
10. No-action benign policy loss (P3)

Exact numeric ranks follow the template's `ordering_rules`; when the template sorts actions by
rank/priority, keep this relative order and renumber 1..n.

## Notes and judgment calls
- **Re-derive owner/priority/action** from this playbook. The hub's own `remediation_actions`
  rows have deliberately wrong owner/priority/action_type and include `*-NOISE-*` decoys; only
  their `target_ref` is a (partial) pointer to material records.
- **Documents are usually evidence, not standalone findings.** Include a `DOC-…` as a
  `source_ref` of the risk it proves (the deletion event, or the zero-claim QC finding). A
  responsive doc that is already `produced` is **not** a gap, even if substantively notable.
- **Over-designation is scope-dependent.** Include it (as a P2 downgrade/qc_remediation) when the
  task is a privilege-QC / production-readiness review; it is acceptable to omit purely-internal
  over-designation from a top-risks dashboard focused on exposure and preservation.
- **Categories** for any finding come from the record's `affected_categories` /
  `category_impacts` / `affected_category` / `category_code`. A category is "open"/affected iff a
  material record names it. Sort category-code lists ascending.

## Metric derivation
Compute from the **material** set only; fill every template metric key, using `0`/`[]`/`false`
when the matter has no such fact. Read each metric's own description for scope (some say
"selected blockers only").
- `unlogged = withheld_count − logged_count` (per selected incomplete-log entry; sum if several).
- Privilege doc counts: use `withheld_count`/`logged_count`, not `doc_count`.
- Box/volume counts: sum `volume_count` where `volume_unit` matches; split pre-hold vs post-hold
  by comparing `event_date` to `hold_date` (or by the pre/post status) when the template asks for
  both.
- Source counts: count distinct material sources per class (lost personal device, uncollected
  source, available archive, …).
- Category counts: `unique_affected_category_count` = distinct categories across material records;
  `categories_with_open_*` = the sorted list of those categories.
