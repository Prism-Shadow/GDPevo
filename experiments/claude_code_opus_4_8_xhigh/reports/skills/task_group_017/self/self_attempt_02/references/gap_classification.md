# Gap classification & enum mapping

The analytical core: decide which hub records are **material** issues, classify
each, and map it to *this template's* enum vocabulary. Enum strings vary per
task — the labels below are the recurring **concepts**; always emit the concrete
string from the current `answer_template.json`.

## 1. Retention / preservation (retention_events, custodian_sources)
Pivot on the matter's `hold_date`:
- **Policy-compliant pre-hold destruction** — `status=policy_destroyed_pre_hold`,
  or `event_date` < `hold_date` and age ≥ `retention_period_months`.
  → **Not a preservation failure.** Concept: `no_gap` / `no_action_policy_loss`.
  Report it (metrics may count destroyed boxes) but do not flag as spoliation.
- **Post-hold loss** — `status=post_hold_loss`, or `event_date` ≥ `hold_date`.
  → Material spoliation → **disclose preservation issue**. Highest severity.
- **Active-system loss / auto-purge** — `system_loss`, `auto_purged` (short
  retention windows, e.g. voicemail/chat). → Material if it hits responsive
  categories; remediate from backup/archive if one exists.
- **`should_exist_missing`** — a required record with no destruction event.
  → **locate missing record** / missing-required-record.
- **`retained` / available archive** — feeds part 4 (retained/available
  sources); it *limits irretrievable loss* for the categories it covers →
  action `collect_archive` / `search_archive`.

## 2. Collection sources (custodian_sources)
- `not_collected` / `partial_collection` with `issue_tags` like `collection_gap`
  or `scope_exception`, especially personal devices / personal email / messaging
  apps → **collection gap** / personal-source gap → collect the source.
- `available` / `in_review` with `issue_tags=routine` → not a material gap.

## 3. Responsiveness & production (review_documents, production_stats)
- Responsive docs with `produced_status=not_produced` (not privileged) →
  **responsiveness miscode / underproduced** → recode and produce.
- `production_stats.zero_claim_reason` non-empty but responsive docs exist for
  that category → **zero-claim contradiction** → readiness blocker.

## 4. Privilege (privilege_entries)
- `withheld_count` > `logged_count` (`incomplete_log`) → **privilege log gap**;
  `unlogged = withheld − logged` → supplement privilege log.
- `over_designated` (and often `family_mismatch`) → **over-designation /
  miscoded privilege** → privilege re-review / downgrade / recode.
- `third_party=1` (`third_party_waiver`) → **waiver assessment and disclosure**.

## 5. QC (qc_findings)
- `miscoded_privilege`, responsiveness miscodes → material → QC remediation /
  recode.
- `metadata_gap`, `duplicate_overlay`, and similar housekeeping → routine
  **noise**; exclude unless the template's metric/enum definitions pull them in.

## 6. Severity, priority, owner
- Severity/risk order: post-hold spoliation & disclosure-triggering gaps are
  `critical`/`high`; collection gaps and log gaps `high`/`medium`; recodes and
  over-designation `medium`; routine `low`.
- `priority` (`P0`–`P3`) and `priority_rank`/`rank` (1 = highest) track severity
  and production impact; take the hub's `remediation_actions.priority`/`severity`
  and `due_days` when present, else assign consistently.
- Map hub `remediation_actions.owner` (human-readable, e.g. "Privilege Team",
  "Review Operations", "Forensics") and `action_type` (e.g. `privilege_rework`,
  `qc_remediation`, `sampling_review`) onto the template's `owner` and
  `action_type` enums — pick the closest legal value.

## 7. Distractor / noise filter (do NOT treat as material unless scoped in)
- Actions/records with ids containing `NOISE`, or `action_type=sampling_review`
  at low priority.
- `issue_tags=routine`; QC `metadata_gap` / `duplicate_overlay`.
- Pre-hold policy-compliant destruction (material only as a reported count, not
  as a preservation failure).
- Clean/`available` sources and produced/closed categories with no open issue —
  omit from lists the template scopes to "material / non-complete" items only.

When a record is ambiguous, prefer the interpretation supported by the row's own
`status`/`issue_type`/`issue_tags` fields and the matter's `hold_date`, and keep
the same classification everywhere it appears (finding, category, source, metric,
action).
