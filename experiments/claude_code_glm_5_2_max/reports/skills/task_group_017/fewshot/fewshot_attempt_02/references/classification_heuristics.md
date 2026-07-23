# Classification Heuristics

Generic rules for mapping Investigation Review Hub records onto an answer template's enums
and for deriving metrics. These are patterns, not values — apply them to whatever the hub
returns for the matter under analysis. Always confirm the exact allowed value exists in the
task's `answer_template.json` enum before using it; if a hub concept has no enum match,
choose the closest enum value or `other` rather than inventing one.

## Preservation / retention classification

Compare each retention event's `event_date` to the matter's `hold_date`:

- **Policy-destroyed pre-hold** (`event_date` < `hold_date`, governed by a `policy_section`):
  retention loss that was policy-compliant before the hold issued. Low risk. Action:
  document / no-action (e.g. `no_action_policy_loss` / `monitor_only`). Counts toward
  "pre-hold destroyed" metrics but **not** toward preservation-risk metrics.
- **Post-hold loss** (`event_date` >= `hold_date`, or `post_hold = 1` on a source):
  preservation failure after the duty attached. High/critical. Action: disclose
  preservation issue (+ forensic recovery if a device/source was lost). Counts toward
  post-hold-loss event metrics.
- **Active system loss** (e.g. deleted collaboration channel, purged custodian mail
  attributable to a system action): medium-to-high. Action: document the system gap; check
  for an available archive that limits the loss.
- **Auto-purge** (system retention window expired, e.g. voicemail/SMS retention): medium.
  Action: document the system gap; note the purge window in days.
- **Should-exist-missing** (a record the matter should have but doesn't, with no
  destruction event): high. Action: locate the missing record.
- **Available archive** (a retained source that can substitute for a loss): remediation
  path, not a loss. Action: collect/search the archive; record which categories the archive
  limits the loss for.

Volume metrics: sum `volume_count` only for events whose `volume_unit` matches the metric
(e.g. `boxes`). Distinguish pre-hold destroyed boxes from post-hold destroyed boxes by the
event-date-vs-hold-date test above.

## Source / collection classification (custodian_sources)

- `status = lost` (personal device, laptop, archive destroyed) → preservation failure,
  `source_status = lost`, `production_impact = source_lost`. Disclose + forensic recovery.
- `status = not_collected` (personal phone, personal messaging, personal email, board
  source) → collection gap / personal source gap, `source_status = not_collected`,
  `production_impact = source_missing`. Action: collect the source / collect personal
  device. Counts toward uncollected-personal-source / uncollected-board-source metrics.
- `status = partial` → partial collection; `production_impact` partial/underproduced.
- `status = collected` or an available archive → remediation source; record which
  categories it limits the loss for; do **not** count as a gap.

## Privilege classification (privilege_log + qc_findings + review_documents)

For each privilege entry, compute `unlogged = withheld_count − logged_count`:

- **Log gap**: `unlogged > 0` (withheld documents not entered on the privilege log).
  `production_impact = withheld_unlogged`. Action: supplement privilege log.
- **Third-party waiver**: `third_party = 1` (privileged communication shared with a
  non-privileged third party). `production_impact = privilege_exposure`. Action: waiver
  assessment and disclosure. `unlogged = 0` here (all withheld are logged); the exposure is
  the waiver, not a log gap.
- **Privilege miscoding**: privileged documents coded as nonprivileged (from QC findings /
  review documents). `production_impact = privilege_exposure` / `recode_needed`. Action:
  privilege recode and log / QC remediation. These are usually `withheld = 0` (they were
  produced, wrongly, as nonprivileged).
- **Over-designation / business-only counsel copy**: documents withheld as privileged that
  should not have been (e.g. business-only counsel copies). Correction type: downgrade.
  Action: QC remediation. `unlogged = 0` (all withheld are logged); the defect is
  over-withholding, not a log gap.

Privilege metric derivation:
- `withheld_privilege_docs` / `withheld_privileged_doc_count` — withheld docs across the
  selected incomplete-log blockers (read the template's metric description: some want *all*
  withheld for the matter, some want only the *selected incomplete-log blockers*).
- `logged_privilege_docs` — logged docs across the same selected set.
- `unlogged_privilege_docs` — withheld − logged across the same set (never negative).
- `third_party_waiver_doc_count` — docs on waiver-flagged entries.
- `miscoded_privileged_doc_count` — docs on miscoding QC findings.
- Re-derive each from the privilege/qc tables, not from the findings list, to avoid drift.

## Responsiveness classification (review_documents + qc_findings + production_stats)

- **Responsiveness miscode**: a responsive document coded nonresponsive (or vice versa),
  usually flagged by a QC finding or a `zero_claim_reason` contradicting the counts.
  `production_impact = not_produced` / `underproduced`. Action: recode and produce.
- **Zero-claim contradiction**: production stats report zero produced/responsive for a
  category while responsive documents exist (or a `zero_claim_reason` is contradicted by
  review documents). Treat as a responsiveness miscode anchored on the QC finding and the
  contradicting document IDs.

## Readiness rollup (when the contract is a readiness review)

Per category, synthesize a `readiness_status` from the set of blockers touching it:
- No open blockers → `ready`.
- A single blocker type → the matching `not_ready_*` status.
- Two or more distinct blocker types → `not_ready_multiple_blockers`, with
  `production_impact = multiple_impacts`.
`production_ready` / `rolling_production_ready` boolean is `false` if any P0/critical/open
blocker exists for any category; `true` only when none remain.

## Severity / priority ranking

Map hub `severity`/`risk_level` to the contract's enum (critical/high/medium/low). For the
action plan, rank by: (1) severity/risk descending, (2) disclosure obligations before
internal remediation, (3) stable ID ascending as a tiebreaker. P0 = critical / must
disclose; P1 = high; P2 = medium; P3 = low / monitor-only. Action `due_days` (when the
contract asks) should be tightest for P0 (a few days) and looser for lower priorities.

## Category rollup

For each category with any open finding, choose the rolled-up `status` as the **worst**
open finding's status type for that category, the rolled-up `production_impact` as the
worst impact, and gather all supporting record IDs across the category's findings into the
`source_refs`/`issue_refs`/`blocking_refs` list (sorted ascending, deduplicated).
`open_issue_count` = number of distinct open findings touching the category.
