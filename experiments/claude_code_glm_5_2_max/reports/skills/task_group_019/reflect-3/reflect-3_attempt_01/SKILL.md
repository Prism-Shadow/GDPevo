---
name: licensing-board-review
description: Review and decide State licensing-board application batches (contractor eligibility, restricted liquor transfers, alcohol renewal queues) against a shared licensing data service. Use when the task involves contractor applications/bonds/insurance/violations, restricted liquor license staff packages, or alcohol renewal manual-review queues against a policies + records data service. Produces structured JSON decisions conforming to a per-task answer template.
---

# Licensing-Board Batch Review

You are acting as a senior licensing examiner / staff reviewer for a State licensing
environment. The environment exposes **policies** plus several **records** data services
(three families: contractor, liquor, alcohol-renewal). Each task asks for a structured
JSON decision conforming to a per-task `answer_template.json`.

The work is deterministic rule-application, not free-form judgment. The difficulty is
**data completeness and careful field mapping**, not reasoning depth. Follow the
procedure below in order.

## 0. Read the task's own schema first

Every task ships `input/payloads/answer_template.json` (or equivalent). **Read it before
solving.** It defines:

- the exact top-level keys,
- the allowed enum values for each coded field (deficiency codes, action codes, risk
  tiers, posture values, match-confidence values, next-step labels, etc.),
- ordering rules (sort ascending by code / by application_id / by rank / by date),
- list-length requirements (e.g. "exactly 8 applications", "queue length 10"),
- whether codes may repeat and whether nested objects (e.g. `{check_code, timing}`) are
  required.

**The allowed-value sets are task-specific.** Two contractor tasks in the same run can
use different deficiency-code and action-code vocabularies (e.g. one uses
`bond_cancelled`/`obtain_current_bond`, another uses `no_active_bond`/`file_active_bond`).
Never carry a code from one task's enum into another. If a condition has no matching code
in the task's enum, do not invent one — either omit it or pick the closest explicitly
listed code and note the choice.

Emit **only** the JSON object the template requires: no prose, no markdown, no extra keys,
no candidate explanations. Sort every list exactly as the template specifies; ordering is
scored. Use empty arrays `[]` when nothing applies.

## 1. Authoritative data: use SQL, not only the REST endpoints

The task prompt lists `GET /api/...` endpoints. **These REST endpoints are incomplete.**
They silently omit records for the train/test target IDs (e.g. bonds and insurance for
several contractor applications are simply absent from the REST feed). A "clean" record
absence from REST usually means "the REST feed dropped it," **not** "no coverage on file."

The authoritative source is the `POST /api/sql` endpoint, which mirrors the same tables
with the **complete** row set. Always pull records through SQL.

- Table names are the REST path with `/` → `_` and the family prefix kept, e.g.
  `contractor_bonds`, `contractor_insurance`, `liquor_settlements`, `alcohol_violations`,
  `renewal_rules`, `policies`.
- SQL is restricted: **only `SELECT`** is allowed; `SELECT *` and `sqlite_master`/`PRAGMA`
  are blocked. Name columns explicitly, e.g.
  `SELECT application_id, bond_id, amount, status, cancel_date FROM contractor_bonds WHERE application_id IN (...)`.
- Use `WHERE ... IN ('id1','id2',...)` to fetch only target rows.

**Cross-check for completeness:** after pulling a target's records, confirm the target ID
has the records you'd expect (a contractor application should have ≥1 bond and ≥1
insurance row). If a REST fetch shows zero financial records for an application that is
clearly active, re-pull that application's rows via SQL before concluding "no coverage."

Load `policies` (and `renewal_rules`, `liquor_privileges`) from SQL as well — policy
thresholds and rule flags live there as JSON in a `details_json` column.

## 2. Build the policy baseline

From `policies`, build a lookup keyed by **(trade, requested_class)** for the contractor
family. Each contractor policy carries, in `details_json`:

- `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
  `required_endorsement` (may be `null` → no endorsement required),
  `serious_open_violation_blocks` (bool).

There is also a **`CON-LEGACY` / prior-baseline policy** carrying
`endorsement_required_for_specialty: false` and `minimum_bond_reduction: <n>`. It defines
the *prior* standard used for the `policy_impacted` flag (see §4).

For liquor, `POL-LIQ-001` (`same_premises_history_matters`,
`current_site_evidence_required`, `standard_privileges_separate_from_controls`) and
`POL-LIQ-002` (`major_incidents_trigger_board_review`) govern the staff-package logic.

For renewal, `renewal_rules` rows carry a `release_boundary` date plus flags in
`details_json`: `use_violations_on_or_before`, `late_rows_are_distractors`,
`alert_flag_requires_manual_review`, `unpaid_fines_require_hold`. Match the rule whose
`release_boundary` equals the date named in the prompt.

## 3. Per-family decision logic

### Contractor eligibility (applications, bonds, insurance, license-history, violations, correspondence, inspections)

For each target application, evaluate against its policy baseline. A "current" bond is a
row with `status = active` (the `-OLD` rows are historical and ignored except to show
prior state). A "current" insurance is `status = active`. **Financial coverage is judged
against the task's review date** (the prompt states it, e.g. `2025-07-18`; if no date is
stated, infer it from the newest `source_date`/`verified_date` in the batch and apply it
to all apps). An `active` insurance row whose `expiration_date` is before the review date
is **expired**, not current.

Map observations to the **task's own** deficiency-code and required-action enums:

- years_experience < policy minimum → experience shortfall (deficiency + action).
- endorsement_status: `missing`/`pending` when the policy requires an endorsement → the
  corresponding endorsement deficiency + "obtain/verify endorsement" action. `not_required`
  matches a `null` endorsement policy. `verified` is clean.
- bond: no active row, or active row cancelled/expired → "no active bond" / "bond
  cancelled" style code (use whichever the enum offers); active amount < minimum → bond
  shortfall; the remediation action matches (file/obtain current bond, or increase bond).
- insurance: no current active row or status `pending`/`expired` → "insurance not current"
  / "insurance expired" (per enum); active amount < minimum → insurance shortfall; amount
  ok but status pending → "not current" (action: provide/renew, as the enum allows).
- license-history `status = suspended` → active_suspension (board-review/clear-suspension
  action). `expired`/`revoked` are history, not active suspension.
- violations: a `serious` violation with `status = open` (or pending/unresolved) → open
  serious violation / unresolved serious complaint. When
  `serious_open_violation_blocks = true`, this **blocks** issuance (DENY). `minor` open →
  open minor violation. `resolved`/`dismissed` violations do **not** generate a deficiency
  (they're context only).
- correspondence: flagged separately at the summary level — see §5.
- inspections: only some tasks have inspection deficiency codes in their enum. Where the
  enum lacks an inspection code, an inspection finding (even `fail`) does **not** produce
  a deficiency; it is informational. Where the enum has codes, map by finding_code+result
  (e.g. `SAFETY_RECHECK`+fail → safety-recheck deficiency; `DOC_GAP`+fail/conditional →
  doc-gap; a `pass` result → no deficiency).

**Determination (APPROVE / HOLD / DENY):**

- DENY when a blocking condition applies (serious open violation with
  `serious_open_violation_blocks`, or an active suspension that cannot be cured short of
  board action — use DENY when the suspension itself blocks issuance, HOLD when it merely
  needs board review to clear).
- APPROVE when there are **no** deficiencies (curable or otherwise) under the task's enum.
- HOLD otherwise (deficiencies that the applicant can cure: shortfalls, missing
  endorsements, expired insurance, missing bond, open minor violations).

**Risk tier:** high when a DENY-level / blocking condition or an active suspension is
present; medium for multiple curable deficiencies; low for a single minor deficiency or a
clean file.

### Restricted liquor staff package (applications, settlements, privileges, incidents, site-evidence)

For the target application + location:

- **same_premises_basis_applies:** true when there is an **active** settlement with
  `basis_code = SAME_PREMISES` (and not expired); false when the same-premises settlement
  is inactive/expired even if one exists historically. Confirm by parsing each
  settlement's `controls_json` (`active` field + `expires`).
- **location_specific_control_codes:** the `controls` list of the **active** settlement only.
- **standard_obligation_codes:** from `liquor_privileges` for the application's
  `license_class` where `standard_required = 1` (these are the ordinary license-class
  obligations, separate from location controls). A code may appear in both lists.
- **covered_risk_codes:** incident/severity risks at the location that are addressed by an
  **active** control (map risk→control: AFTER_HOURS↔HOURS, ASSAULT↔SECURITY,
  NOISE↔NOISE, PATIO_BOUNDARY↔PATIO, MINOR_SALE/SALE_TO_MINOR↔ID_CHECK). Also include the
  active settlement's own `basis_code` when it is itself a risk. Do not list a risk as
  covered if the controlling obligation is only on an inactive settlement.
- **verification_gap_codes:** from `liquor_site_evidence` and open incidents. Take the
  **most recent** evidence row per `evidence_code`; map its status to a gap
  (e.g. CONTROL_SIGNAGE `missing`→`..._CURRENT_MISSING`, `conflicting`→`..._CONFLICTING`;
  POLICE_MEMO `conflicting`→`POLICE_MEMO_CONFLICTING`; FLOOR_PLAN `conflicting`/`stale`→
  `FLOOR_PLAN_CONFLICTING`/`FLOOR_PLAN_STALE`). An open/`referred` incident →
  `OPEN_INCIDENT_FOLLOW_UP`. An open TAX_HOLD → `TAX_CLEARANCE_MISSING`/tax-gap per enum.
  A required evidence type with **no** row at all (e.g. signage absent) → the
  `..._MISSING` gap for that type.
- **recommended_posture:** `issue_restricted` only when the same-premises basis is active,
  controls are current, and remaining items are monitoring-only (no open blocking
  incident, no unresolved verification gap that gates issuance). `request_follow_up` when
  there are open incidents or unverified/missing evidence that must be resolved before
  issuance. `deny` for a blocking major incident / board-order conflict.
- **first_90_day_plan** and **escalation_trigger_codes:** build from the gaps + active
  controls + open incidents (each gap generally yields a check in the plan and a trigger
  if it fails). Use each check_code/trigger at most once; timings are
  `first_30_days`/`days_31_60`/`days_61_90`.

### Alcohol renewal manual-review queue (licensees, violations, renewal_rules)

Build a ranked queue of the target license set.

- Match violations to each license. **Exact** match = same `license_no`. **Successor**
  match = `license_no` equals the licensee's `successor_to` old number → mark
  `uncertain`. Same-address-different-license matches may also be `close_address` per the
  rule flags; apply address matching only to the extent the task's rule set directs, and
  do **not** inflate the excluded set with unrelated licenses.
- Apply the **release boundary** from the matched `renewal_rule`: keep only violations with
  `violation_date <= boundary`. Rows dated after the boundary (the planted `*-LATE`
  distractor rows) are excluded and listed in `post_boundary_violation_ids_excluded`
  (sorted ascending by violation_id).
- Per license: `violation_count` = matched pre-boundary violations; sort
  `matched_violation_ids` by violation_date ascending then violation_id ascending;
  `most_recent_violation_date` = latest matched date; `match_confidence` = best-available
  tier among its matches (exact > close_address > uncertain).
- Rank by risk: serious-unresolved and open violations first, then violation count, then
  most-recent date. Assign `risk_tier` (high for serious-unresolved or many open; low for
  few/minor) and `next_step_label` (`board_review` for serious unresolved;
  `additional_record_check` for uncertain/successor matches; `manual_fine_check` when
  `fine_balance > 0` i.e. `unpaid_fines_require_hold`; `manual_ALERT_check` for
  `alert_flag` matches). Honor `alert_flag_requires_manual_review`.
- Summary: `queue_size`, `boundary_date`, the excluded id list,
  `close_or_uncertain_match_license_numbers`, and `board_review_license_numbers`, each
  sorted as specified. Ranks are integers 1..N with no gaps.

## 4. `policy_impacted` flag (contractor tasks)

`policy_impacted = true` **only** when a current-2025 policy standard creates a deficiency
or review flag that would **not** have applied under the prior (`CON-LEGACY`) baseline.
The legacy baseline differs in exactly two ways:

1. **Specialty endorsement was not required.** A specialty trade (e.g. Solar) whose
   current policy requires an endorsement (e.g. `SOL-PLUS`) and shows an endorsement
   deficiency → policy_impacted true. Non-specialty endorsements (e.g. `EE-1`, `PH-2`,
   `MECH-H`, `GB-A`) were already required under the baseline → not impacted by the
   endorsement alone.
2. **Bond minimum was lower by `minimum_bond_reduction`.** A bond shortfall where the
   amount is `>= (current_min − reduction)` but `< current_min` would have passed under
   the baseline → policy_impacted true. A bond that fails under both baselines (e.g. no
   active bond, or amount below the reduced floor) → not impacted.

Insurance requirements and experience thresholds are unchanged by the legacy baseline, so
insurance/experience deficiencies alone do **not** set policy_impacted.

## 5. Stale / unverified correspondence (contractor summary)

`stale_or_unverified_correspondence_ids` collects correspondence rows for the target
applications that are **either** unverified (`verified_by_agency = 0`) **or** stale (notes
mention "stale"/"predates application", or the attachment predates the application). Sort
ascending by correspondence_id. Agency-verified, current correspondence is excluded.

## 6. Assemble and verify the output

- Order list outputs exactly as the template demands (application_id / rank / code
  ascending; matched dates ascending).
- Make the batch summary internally consistent: `approve_count + hold_count + deny_count`
  must equal the number of decisions; `high_risk_application_ids` /
  `policy_impacted_application_ids` must equal the per-app flags; queue `queue_size` must
  equal the queue length and ranks must be 1..N contiguous.
- Re-read the target template one more time and confirm every field uses only allowed enum
  values and no extra keys are present.
- Return only the JSON object.
