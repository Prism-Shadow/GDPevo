# Decision models by family

These are the reasoning rules for each licensing family. They are expressed in
terms of the **data** (records + `/api/policies` + `/api/renewal/rules`), not in
terms of any specific answer. Always emit only codes that appear in the current
task's `answer_template.json` `allowed_values`, and map each underlying fact to
whichever code that particular template uses (vocabularies differ between tasks).

General fact-vs-code principle: derive the **fact** from the data, then look up
the fact in the template's enum. If a template has no code for a fact (e.g. no
inspection codes, or no "open medium violation" code), that fact is simply not
reported for that task.

---

## A. Contractor batch eligibility

Output: `application_decisions` (one per target application id, ordered by
application_id) + `summary`. Per application: `determination`
(APPROVE/HOLD/DENY), `deficiency_codes`, `required_actions`, `risk_tier`
(low/medium/high), `policy_impacted` (bool).

### Data joins (per application id)
- `contractor_applications` — trade, requested_class, endorsement_status
  (`missing`/`pending`/`verified`/`not_required`), years_experience,
  prior_license_id, self_disclosed_issue.
- The applicable policy row in `/api/policies` (family `contractor`), matched by
  trade + requested_class (rule_code like `CON-PLU-ClassB`). It gives
  `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
  `required_endorsement`, `serious_open_violation_blocks`.
- `contractor_bonds` / `contractor_insurance` — filter to this application_id;
  find the **active** row (bonds: `status='active'`; insurance:
  `status='active'` AND `expiration_date >= review_date`).
- `contractor_license-history` — join by prior_license_id; `status='suspended'`
  is an active suspension.
- `contractor_violations` — match by `related_application_id = app` OR
  `license_id = prior_license_id`; only `status='open'` matter (severity
  minor/serious). Resolved/dismissed are ignored.
- `contractor_inspections` — match by related_application_id.
- `contractor_correspondence` — match by related_application_id.

`review_date` = the "review date" / currency date stated in the prompt; if none
is stated, use today's date.

### Facts → codes
| Fact (from data) | Typical code (name varies by template) | Action |
|---|---|---|
| No active bond (only cancelled/expired) | `bond_cancelled` **or** `no_active_bond` | obtain_current_bond / file_active_bond |
| Active bond amount < policy `minimum_bond` | `bond_shortfall` | increase_bond_amount / increase_bond |
| No active-and-current insurance, best on file is `status='pending'` | `insurance_pending` **or** `insurance_not_current` | verify_insurance_binding / provide_current_insurance |
| Active insurance whose `expiration_date < review_date` | `insurance_expired` | provide_current_insurance / renew_insurance |
| Active current insurance amount < policy `minimum_insurance` | `insurance_shortfall` | increase_insurance_amount / increase_insurance |
| Endorsement required by policy and status=`missing` | `endorsement_missing` **or** `endorsement_not_verified` | obtain_required_endorsement / verify_endorsement |
| Endorsement required and status=`pending` | `endorsement_pending` **or** `endorsement_not_verified` | verify_pending_endorsement / verify_endorsement |
| years_experience < policy `minimum_years_experience` | `experience_shortfall` | submit_experience_evidence / document_experience |
| License-history status = suspended | `active_suspension` | board_review_suspension / clear_suspension (+ board_review) |
| Open **serious** violation | `open_serious_violation` **or** `unresolved_serious_complaint` | resolve_serious_violation / resolve_complaint (+ board_review) |
| Open **minor** violation | `open_minor_violation` | resolve_minor_violation_review |
| Inspection finding `DOC_GAP` with result fail/conditional | `inspection_doc_gap` | clear_document_gap |
| Inspection finding `SAFETY_RECHECK` with result fail | `inspection_safety_recheck` | complete_safety_recheck |

Notes: an inspection with `result='pass'` or `finding_code='NONE'` is not a
deficiency. Endorsement `verified` or `not_required` → no endorsement
deficiency. Sort deficiency_codes and required_actions ascending; use `[]` when
none apply.

### Determination & risk tier
- **DENY** (risk `high`) if there is an active suspension **or** an open serious
  violation (the disqualifying facts; `serious_open_violation_blocks` in policy).
- **APPROVE** (risk `low`) if there are no deficiencies at all.
- **HOLD** (risk `medium`) otherwise — curable deficiencies (bond, insurance,
  endorsement, experience, minor violation, inspection gap).

### policy_impacted
True when a deficiency/flag arises from the **current** policy standard that
would not arise under the prior/legacy baseline (`POL-CON-LEGACY`, which sets
`minimum_bond_reduction` and `endorsement_required_for_specialty=false`). Read
the template's `policy_impacted` "meaning" note and reconcile. Strong signals:
- A `bond_shortfall` where the active bond amount is ≥ (`minimum_bond` −
  `minimum_bond_reduction`) but < `minimum_bond` — i.e. the shortfall exists only
  because of the stricter current minimum.
- An endorsement deficiency introduced by a current-policy endorsement
  requirement that the legacy baseline did not impose (specialty classes are the
  clearest case, since legacy `endorsement_required_for_specialty=false`; some
  templates extend this to any current required endorsement — judge from the
  template's meaning text and the policy effective dates vs. the legacy row).

### summary
- `approve_count` / `hold_count` / `deny_count` — counts of determinations.
- `high_risk_application_ids` — apps with risk_tier `high`, sorted.
- `policy_impacted_application_ids` — apps with `policy_impacted=true`, sorted.
- `stale_or_unverified_correspondence_ids` — every `contractor_correspondence`
  row whose `related_application_id` is a target and that is unverified
  (`verified_by_agency = 0`) **or** stale (notes indicate the attachment
  predates/ is stale). The `verified_by_agency` flag is authoritative over the
  free-text notes. Include distractor ids (e.g. `COR-DIS-...`) when they are
  linked to a target application. Sorted ascending.

---

## B. Restricted liquor staff package

Output object for one `application_id`: `recommended_posture`
(issue_restricted/request_follow_up/deny), `same_premises_basis_applies` (bool),
`covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`,
`location_specific_control_codes`, `first_90_day_plan` (`[{check_code, timing}]`),
`escalation_trigger_codes`.

### Data joins
- `liquor_applications` — the target application: `license_class`, `location_id`
  (usually also given in the prompt), requested_posture.
- `liquor_privileges` — rows for this `license_class`.
- `liquor_settlements` — rows for this `location_id`; parse `controls_json`
  (`{active, controls[], expires, review_required}`) and `basis_code`.
- `liquor_incidents` — rows for this `location_id`: `risk_code`, `severity`,
  `status`. Real location incidents drive risk; ignore dismissed distractors.
- `liquor_site-evidence` — rows for this `location_id`: `evidence_code`,
  `status` (`verified`/`conflicting`/`missing`).
- `/api/policies` family `liquor`: `POL-LIQ-001` (same-premises history matters,
  standard privileges separate from controls), `POL-LIQ-002` (major incidents
  trigger board review).

### Field derivations
- **standard_obligation_codes** = `obligation_code` of the class's privileges
  where `standard_required = 1`. (Ordinary obligations for the license class.)
- **location_specific_control_codes** = union of `controls` from settlements at
  the location whose `controls_json.active = true` (and not expired). These are
  the *current, location-tied* controls — kept separate from the standard
  obligations above.
- **same_premises_basis_applies** = true if any settlement at the location has
  `basis_code = SAME_PREMISES` (even an expired one — history matters).
- **covered_risk_codes** = risks the location currently has a control for. For
  each active settlement, its `basis_code` and its controls map to risk codes
  (e.g. control `PATIO`→`PATIO_BOUNDARY`, `HOURS`→`AFTER_HOURS`, `SECURITY`/
  `CCTV`→`ASSAULT`, `ID_CHECK`→`MINOR_SALE`/`SALE_TO_MINOR`). A real location
  incident risk is "covered" only if a current control **or** standard
  obligation addresses it; otherwise it is a gap/escalation, not covered.
- **verification_gap_codes** = site-evidence with `status` `conflicting` or
  `missing` (mapped to the code, distinguishing "current missing" where notes
  say "current"), **plus** open/`referred` incidents (open-incident-follow-up),
  **plus** expected-but-absent evidence (e.g. no camera/food-service evidence on
  file when the class/controls need it → camera/food_service evidence missing),
  **plus** late-night-monitoring-needed for late-service venues.
- **first_90_day_plan** = one check per verification gap / active control, timed
  by urgency: immediate verification items → `first_30_days`; behavioural /
  observational monitoring → `days_31_60`; ongoing boundary/noise checks →
  `days_61_90`. Use the template's `check_code` enum. Dedup check_code/timing
  pairs; sort per the template's ordering note (some sort by check_code, some
  keep operational sequence).
- **escalation_trigger_codes** = one trigger per covered-risk / active-control /
  open concern (e.g. active security/CCTV control → control-failure trigger;
  after-hours risk → after-hours trigger; open tax hold → tax-hold trigger;
  high-severity/major incident → major-incident trigger; unresolved referred
  minor sale → referred-minor-sale trigger).
- **recommended_posture**:
  - `deny` if there is a disqualifying, unresolved condition (e.g. a
    major/serious incident referred for board action with no covering controls,
    or a board order that blocks issuance).
  - `issue_restricted` if current controls cover the risks and there are no open
    verification gaps.
  - `request_follow_up` otherwise — controls exist but verification gaps remain
    (missing/conflicting evidence, open incidents). This is the common middle
    case when gaps are present but nothing is disqualifying.

Every array: dedup and sort per the template's ordering note.

---

## C. Alcohol renewal manual-review queue

Output: `queue` (ranked list, length = target queue size) + `summary`. Per
entry: `rank`, `license_no`, `facility_name`, `violation_count`,
`most_recent_violation_date`, `matched_violation_ids`, `match_confidence`
(exact/close_address/uncertain), `risk_tier`, `next_step_label`.

### Rules & data
- `/api/renewal/rules` gives the `release_boundary` (also in the prompt) and
  flags: `alert_flag_requires_manual_review`, `unpaid_fines_require_hold`,
  `late_rows_are_distractors`, `use_violations_on_or_before` (= boundary).
- `alcohol_licensees` — the target `license_no`s: `facility_name`, `address`,
  `successor_to`.
- `alcohol_violations` — match to each licensee.

### Matching & confidence
- **exact**: violations whose `license_no` equals the target.
- **close_address**: when a licensee is a successor (`successor_to` set), also
  pull the predecessor's violations (predecessor at the same `address`); if any
  such predecessor/address-matched violations are used, the entry's
  `match_confidence` is `close_address` (not exact).
- **uncertain**: use when the match is ambiguous (successor link without a clean
  address match, or address matches multiple licensees) — `POL-REN-001` says
  successor matches may be marked uncertain.
- If a successor's own exact violations already cover everything and the
  predecessor adds nothing, keep `exact`.

### Boundary filtering
- Keep only violations with `violation_date <= release_boundary`.
- Every candidate violation with `violation_date > boundary` (the `-LATE` rows)
  is dropped and listed in `summary.post_boundary_violation_ids_excluded`.

### Per-entry fields
- `violation_count` = count of matched, pre-boundary violations.
- `most_recent_violation_date` = max date among them.
- `matched_violation_ids` = sorted by `violation_date` ascending, then
  `violation_id` ascending.
- `next_step_label` (prioritised; use the template's enum):
  - `manual_ALERT_check` when **all** matched violations have `alert_flag = 1`
    (a pure alert-flagged history).
  - `board_review` for close_address/uncertain matches and the most severe
    cases (e.g. successor/predecessor histories, serious open violations,
    sale-to-minor concerns) that need board escalation.
  - `manual_fine_check` when there are unpaid/open fine balances to reconcile.
  - `additional_record_check` when the record set is insufficient to decide.
- `risk_tier` (low/medium/high) is a judgment from severity, disposition
  (open/pending unresolved), `alert_flag`, unpaid `fine_balance`, and volume of
  pre-boundary violations. Mostly-resolved, low-volume histories are `medium`/
  `low`; histories with serious/open/alert-flagged/unpaid items are `high`.

### Ranking
Assign ranks 1..N (no gaps) by sorting entries by **next_step_label priority**
(`board_review` > `manual_fine_check` > `manual_ALERT_check` >
`additional_record_check`), then by `most_recent_violation_date` **descending**
within each group.

### summary
- `queue_size` = length of the queue.
- `boundary_date` = the release boundary (YYYY-MM-DD).
- `post_boundary_violation_ids_excluded` = all dropped post-boundary candidate
  violation ids, sorted by violation_id ascending.
- `close_or_uncertain_match_license_numbers` = license_nos whose
  match_confidence is `close_address` or `uncertain`, sorted ascending.
- `board_review_license_numbers` = license_nos with `next_step_label =
  board_review`, sorted ascending.
