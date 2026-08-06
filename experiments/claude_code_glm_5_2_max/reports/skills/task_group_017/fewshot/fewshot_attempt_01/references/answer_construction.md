# Answer Construction — Mapping Hub Evidence to Output

This reference defines the *method* for translating Investigation Review Hub records
into the structured JSON answer. It is generic: it never names a specific matter, record
ID, count, or category code. Apply it through the lens of the current task's
`answer_template.json` enums.

## Severity / risk_level mapping

Rank each defect on the template's severity/risk enum (`critical`, `high`, `medium`,
`low` — exact order varies; use the enum's own precedence). General guidance:

- **critical** — a source lost or destroyed *after* the litigation hold; privilege
  exposure to a government or adverse party that mandates disclosure; any defect that
  blocks the entire production.
- **high** — privilege log gap (withheld > logged); third-party waiver risk;
  responsiveness miscode that leaves a responsive document unproduced; an uncollected
  personal source; a missing required record that should exist.
- **medium** — system purge or deleted channel *with an available archive* that limits
  the loss; over-designation of business-only counsel copies.
- **low** — pre-hold, policy-compliant destruction (destruction that occurred before the
  hold date under a documented retention policy and is not a preservation failure).

When two defects of different severity touch the same record, the record's severity is
the higher of the two.

## issue_type / status / production_impact selection

Map the underlying fact pattern to the enum value the template defines. Common
fact-pattern → enum mappings (adapt names to the template's exact enum strings):

| Fact pattern | issue_type | source/retention status | production_impact |
|---|---|---|---|
| Source destroyed after hold | post_hold_loss / preservation_failure | destroyed / lost / post_hold_loss | source_lost |
| Source destroyed before hold under policy | (policy_destroyed_pre_hold) | policy_destroyed_pre_hold | no_production_impact |
| Required source never collected | collection_gap / uncollected_source | not_collected | source_missing |
| Personal phone/email/messaging not collected | personal_source_gap | not_collected | source_missing |
| Auto-purge / deleted channel with archive | active_system_loss / auto_purge | auto_purged / active_system_loss | (source_available if archive limits loss) |
| Responsive doc coded nonresponsive | responsiveness_miscode / responsive_miscoding | not_applicable | not_produced / underproduced |
| "Zero-claim" contradiction (completeness claim vs. missing responsive doc) | responsiveness_miscode | not_applicable | not_produced |
| Withheld > logged | privilege_log_gap | not_applicable | withheld_unlogged |
| Privileged coded nonprivileged (or reverse) | privilege_miscoding / miscoded_privilege | not_applicable | privilege_exposure / recode_needed |
| Privilege shared with third party | third_party_waiver | not_applicable | privilege_exposure / privilege_waiver |
| Business-only counsel copies withheld as privileged | over_designation | not_applicable | (qc remediation; often no production impact) |
| Record that should exist is missing | missing_required_record | should_exist_missing | missing_record |
| Archive available for collection | archive_available | available_archive | source_available |

## Count fields

For each finding/risk/issue/retention event, fill the count fields from the hub record:

- `document_count` — documents implicated by the record (use `0` if the record is a
  source/box-level event, not a document set).
- `withheld_count` — documents withheld as privileged in that record.
- `logged_count` — of those withheld, how many appear on the privilege log.
- `unlogged_count` — `withheld_count − logged_count` (this invariant must hold wherever
  both withheld and logged are meaningful).
- `volume_count` + `volume_unit` — physical/system volume when the record is measured in
  boxes, days, emails, sources, etc. Use the `volume_unit` enum exactly. Use `0`/`null`
  per field type when not applicable.

When a template has *only* `document_count` and no volume fields, put the relevant count
in `document_count` and omit volume.

## Category mapping

- `category_impacts` / `affected_categories` — the request category codes the record
  touches. Derive from the hub record's category linkage, not from guessing. Sort
  ascending.
- For category-level sections (`category_statuses`, `category_coverage`,
  `readiness_statuses`): iterate the matter's category set; for each category with at
  least one material open issue, collect every issue record touching it into the refs
  list and choose the dominant status/impact/action. `open_issue_count` is the count of
  distinct issue records summarized for that category.
- A category whose only issue is a *policy-compliant pre-hold loss* generally has
  `no_current_gap` / `no_open_gap` and is omitted from a "material non-complete" list.
- A category with both a source loss and a missing record may warrant a "mixed" status
  if the template offers one; otherwise use the more severe single status.

## Metrics computation

Compute every key the template lists — do not drop a metric because it is zero. Common
rollups (adapt key names to the template):

- **Issue/finding/risk counts** — `len()` of the corresponding section list.
- **Privilege docs** — sum `withheld_count`, `logged_count`, and
  `unlogged_count` across the privilege-related records the template scopes (some
  templates restrict to "selected incomplete-log blockers only" — read the field
  description). `unlogged = withheld − logged` must reconcile.
- **Waiver docs** — sum docs in third-party-waiver records.
- **Miscoded responsive docs** — sum docs in responsiveness-miscode records.
- **Miscoded privileged docs** — sum docs in privilege-miscoding records.
- **Missing required records** — count of `should_exist_missing` records.
- **Lost personal device / uncollected personal source counts** — count distinct
  personal sources in the relevant status.
- **Uncollected board source count** — count distinct non-personal required sources not
  collected.
- **Destroyed box counts** — sum `volume_count` where `volume_unit == boxes`. Split into
  pre-hold vs post-hold using the record's event_date vs hold_date.
- **Post-hold loss event count** — retention events with status `post_hold_loss` /
  destroyed after hold.
- **Pre-hold policy-destroyed event count** — retention events destroyed before hold
  under a policy.
- **Available archive count** — count of sources with an available/retained status.
- **Categories with open gaps / risk** — distinct union of category codes across all
  open material issues. `affected_category_count` / `unique_affected_category_count` is
  the length of that set.
- **Readiness boolean** (`rolling_production_ready`, `production_ready`) — `false` if
  any critical or high open gap exists that blocks production; `true` only when every
  category is complete/ready. Default to `false` when in doubt — a false "ready"
  understates risk worse than a cautious "not ready".
- **nonready_category_count** — count of categories with a non-ready readiness status.

## Priority actions / action plan

Build one action per remediation need, then sort by `priority_rank` (1 = highest).
Convention for ranking (adapt to the template's `action_type` and `owner` enums):

1. **P0 — disclose to government / disclose preservation issue.** Owner: outside
   counsel (or litigation counsel). Targets: post-hold losses, lost sources, privilege
   exposure / waiver that mandates disclosure. Due soonest.
2. **P0/P1 — forensic recovery / collect personal device / collect source.** Owner:
   forensics, ediscovery vendor, or client IT. Targets: uncollected personal sources,
   lost devices where recovery is possible.
3. **P1 — collect archive / search archive / restore from backup.** Owner: ediscovery
   vendor. Targets: available archives that limit a loss.
4. **P1 — recode and produce.** Owner: review QC / review vendor. Targets:
   responsiveness miscodes, zero-claim contradictions.
5. **P1 — supplement privilege log / privilege recode and log.** Owner: privilege team /
   privilege counsel. Targets: log gaps and privilege miscoding.
6. **P1 — waiver assessment and disclosure.** Owner: privilege counsel. Targets:
   third-party waiver records.
7. **P2 — QC remediation / locate missing record / custodian follow-up.** Owner: review
   QC, compliance audit, or records management. Targets: over-designation, missing
   records, follow-ups.
8. **P3 / low — no action / no_action_policy_loss / monitor only.** Owner: records
   management. Targets: pre-hold policy-compliant losses needing no action.

Each action carries `target_refs` (the hub record IDs it acts on, sorted ascending) and
`category_impacts`/`affected_categories` (sorted ascending). Use a stable `action_id`
scheme derived from the matter (e.g. `ACT-<matter-tag>-NNN`), or reuse the hub's own
remediation-action IDs when the hub provides them and the template permits.

## Owner mapping (typical)

| action_type | typical owner |
|---|---|
| disclose_to_government / disclose_preservation_issue | outside_counsel / litigation_counsel |
| forensic_recovery / collect_personal_device / collect_source | forensics / ediscovery_vendor / client_it |
| search_archive / collect_archive / restore_from_backup | ediscovery_vendor |
| recode_and_produce | review_qc / review_vendor |
| supplement_privilege_log / privilege_recode_and_log | privilege_team |
| waiver_assessment_and_disclosure | privilege_counsel |
| qc_remediation | review_qc / privilege_team |
| locate_missing_record | compliance_audit |
| document_system_gap / custodian_followup | it_messaging / records_management |
| no_action / no_action_policy_loss / monitor_only | records_management / legal_operations |

Always confirm the chosen `owner` is in the template's `owner` enum; if the obvious
owner is not listed, pick the closest listed owner.

## Stability and reconciliation checklist

- Every finding/risk/issue is anchored by exactly one stable hub record ID used as its
  key, and lists every supporting record ID in its refs.
- No record ID is invented, truncated, or reformatted.
- `unlogged_count == withheld_count − logged_count` wherever both apply.
- Metrics sums reconcile with the section lists (e.g. `top_risk_count == len(top_risks)`).
- `categories_with_open_gaps`/`categories_with_open_risk` is the sorted distinct union of
  all category_impacts across open issues — not just the categories with their own row.
- Every list sorted per `ordering_rules`; every enum value from the allowed set.
