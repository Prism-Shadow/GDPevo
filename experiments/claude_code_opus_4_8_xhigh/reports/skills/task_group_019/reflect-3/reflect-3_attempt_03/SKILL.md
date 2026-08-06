---
name: licensing-review
description: >-
  Solve structured licensing / regulatory review tasks that read a prompt plus a
  strict JSON answer template, query a licensing data service (REST + a SQL
  endpoint), apply agency policy logic to specific target records, and emit only
  JSON matching the template. Covers three task families: contractor batch
  eligibility review, restricted liquor-license staff package, and alcohol
  renewal manual-review queue. Use when a task gives target IDs, points at
  /api/... endpoints, and supplies input/payloads/answer_template.json.
---

# Licensing Review Solver

A task in this class gives you: (1) a `prompt.txt` naming target entities (and
sometimes a review/boundary date), (2) `input/payloads/answer_template.json`
describing the EXACT output schema (keys, enums, orderings), and (3) an
`environment_access.md` describing a read-only licensing **data service**. Your
job is to fetch the relevant records, apply the agency's policy logic, and return
**only** the JSON object the template specifies — no prose, markdown, comments,
citations, or extra keys.

There is no scoring feedback while solving. Reason the answer out and produce it
directly.

---

## 1. Read the task before touching data

- Parse `prompt.txt` for: the target IDs (and their ordering requirement), the
  license/agency family, and any explicit **review date** or **boundary date**
  and **target queue size**. Dates in the prompt drive "is coverage current"
  and "which violations count" decisions — use them literally.
- Parse `answer_template.json` completely. It is the source of truth for:
  - the exact **top-level keys** and per-item keys,
  - every field's **enum `allowed_values`** (code spellings differ between
    otherwise-similar tasks — always copy spellings from the template you were
    given, never from memory),
  - **ordering** rules (usually "ascending by id" or "ascending lexical", or a
    date-then-id sort for match lists), and de-duplication rules,
  - required list lengths, and where **empty arrays** are expected.

## 2. Access the data service (and beat the 200-row cap)

Read connection details from the task's own `environment_access.md`: the base
URL, the list of allowed `GET /api/...` endpoints, and the auth header/token
required by `POST /api/sql`. Do not hardcode these — each task supplies its own.
`reference/env_client.py` reads them for you.

Two endpoint styles exist:
- `GET /api/<resource>` — returns a JSON array of rows.
- `POST /api/sql` with `{"query": "SELECT ..."}` and the task's auth header —
  returns `{columns, rows, row_count, truncated, limit}`. It allows plain
  `SELECT ... WHERE ...`; it **blocks** `sqlite_master`, `PRAGMA`, and similar
  introspection.

**Critical:** both the GET arrays and the SQL endpoint are **capped at 200 rows**.
Some tables exceed 200 rows (e.g. contractor bonds, contractor insurance,
alcohol violations), so a plain `GET` silently drops records and will make target
entities look like they have *no* bond/insurance/violations. Always fetch
target-scoped, complete data with `POST /api/sql` using
`WHERE <key> IN (<your target ids>)` filters, and confirm the response has
`"truncated": false`. If truncated, narrow the filter.

SQL table-name notes:
- Table names use **underscores**. The license-history resource (GET path
  `/api/contractor/license-history`) is the SQL table
  `contractor_license_history` (a hyphen in SQL is a syntax error). Site
  evidence is `liquor_site_evidence`.
- Useful check: `SELECT COUNT(*) AS n FROM <table>` to see whether a table is
  over the cap.

**Read thresholds from data, never hardcode them.** `GET /api/policies` returns
rows whose `details_json` is a JSON *string* holding the numeric standards
(minimum bond/insurance/years, required endorsement, blocking flags). Renewal
boundary dates live in `GET /api/renewal/rules` (`details_json` +
`release_boundary`). Parse these; apply the row that matches the entity.

## 3. General output discipline

- Return exactly the template's top-level keys and per-item keys — nothing else.
- Use enum values spelled exactly as in the template. Sort every list as the
  template says (default ascending by id/code) and de-duplicate.
- Use `[]` where no code/id applies. Order the main item list by the id the
  template names (e.g. `application_id` ascending).
- Make summary/aggregate fields **consistent** with the per-item decisions
  (counts equal the number of items with that determination; id-lists equal the
  items that qualify).
- No prose, markdown, comments, or trailing explanation. Output is a single JSON
  object.

---

## Family A — Contractor batch eligibility review

Output: `application_decisions` (one per target application, ordered by
`application_id`) + a `summary`. Per application: `determination`
(APPROVE/HOLD/DENY), `deficiency_codes`, `required_actions`, `risk_tier`
(low/medium/high), `policy_impacted` (bool).

### Match each application to its policy
An application has `trade` and `requested_class`. The contractor policy is the
`family='contractor'` row whose `title` is `"<trade> <requested_class> application
standards"` (e.g. "Electrical Class A application standards", "Roofing Limited
application standards"). Its `details_json` gives `minimum_bond`,
`minimum_insurance`, `minimum_years_experience`, `required_endorsement`
(may be null), `serious_open_violation_blocks`. There is also a
`CON-LEGACY` / prior-baseline policy used for the `policy_impacted` comparison
(`endorsement_required_for_specialty: false`, `minimum_bond_reduction`).

### Compute deficiencies (each maps 1:1 to a required action)
Use the closest code spelling from the template's `allowed_values`; the two
common contractor vocabularies pair like this:

| Condition | deficiency (v1 / v2 spelling) | action (v1 / v2) |
|---|---|---|
| No current active bond (all bonds cancelled/expired, or none `status=active` with no `cancel_date`) | `bond_cancelled` / `no_active_bond` | `obtain_current_bond` / `file_active_bond` |
| Current bond `amount` < `minimum_bond` | `bond_shortfall` | `increase_bond_amount` / `increase_bond` |
| Insurance not current | `insurance_expired` (status `expired`) or `insurance_pending`/`insurance_not_current` | `provide_current_insurance`/`renew_insurance`/`verify_insurance_binding` |
| Current insurance `amount` < `minimum_insurance` | `insurance_shortfall` | `increase_insurance_amount` / `increase_insurance` |
| Endorsement required by policy but `endorsement_status` not in {verified, not_required} | `endorsement_missing`/`endorsement_pending`/`endorsement_not_verified` | `obtain_required_endorsement`/`verify_pending_endorsement`/`verify_endorsement` |
| `years_experience` < `minimum_years_experience` | `experience_shortfall` | `submit_experience_evidence` / `document_experience` |
| Prior license suspended | `active_suspension` | `board_review_suspension` / `clear_suspension` (+`board_review`) |
| Open serious violation linked to app | `open_serious_violation` / `unresolved_serious_complaint` | `resolve_serious_violation` / `resolve_complaint` (+`board_review`) |
| Open minor violation linked to app (only if the template has the code) | `open_minor_violation` | `resolve_minor_violation_review` |
| Inspection finding (only if the template has these codes) `DOC_GAP` / `SAFETY_RECHECK` | `inspection_doc_gap` / `inspection_safety_recheck` | `clear_document_gap` / `complete_safety_recheck` |

Details that matter:
- **Bond "current"** = a bond row with `status == active` and `cancel_date`
  null. Ignore cancelled/expired bonds. Pick the latest by `effective_date`.
- **Insurance "current"**: if a review date is given, current = `status active`
  AND `expiration_date >= review_date`. Otherwise assess by `status`. Map:
  `status expired` → the "expired"/renew code; `status pending`, or active-but-
  lapsed-past-review-date → the "not current"/"pending"/provide-current code.
  A shortfall (amount below minimum) is a *separate* code from currency.
- **Endorsement** only matters when the matched policy's `required_endorsement`
  is non-null. `not_required` and `verified` are clean.
- **Violation linkage**: a violation applies to an application when
  `related_application_id == application_id` OR (the application's
  `prior_license_id` is non-null AND `license_id == prior_license_id`). Only
  `status == open` violations create deficiencies; `resolved`/`dismissed` do not.
  Serious is a hard block; minor gets the minor code (if present); medium-open
  usually has no code. Ignore rows that match neither key (distractors).
- **Suspension**: read `contractor_license_history` by the app's
  `prior_license_id`; `status == suspended` is a suspension.

### Determination, risk, policy_impacted
- **DENY** if any *hard block*: an open serious violation, or an active
  suspension. **HOLD** if there are curable deficiencies but no hard block.
  **APPROVE** if there are no deficiencies.
- **risk_tier tracks the determination**: DENY → high, HOLD → medium,
  APPROVE → low.
- **policy_impacted = true** when a current-year policy standard creates a
  deficiency that would not exist under the legacy baseline. The two concrete
  cases: (a) a Specialty class with an endorsement deficiency (legacy did not
  require specialty endorsements), and (b) a bond shortfall that only exists
  because the current minimum is higher than legacy — i.e.
  `amount >= minimum_bond - legacy.minimum_bond_reduction` (the bond would have
  passed under the lower legacy minimum).

### Summary
- `approve_count`/`hold_count`/`deny_count` from the determinations.
- `high_risk_application_ids` = apps whose `risk_tier` is high.
- `policy_impacted_application_ids` = apps with `policy_impacted` true.
- `stale_or_unverified_correspondence_ids` = every correspondence row whose
  `related_application_id` is one of the targets and which is
  `verified_by_agency == 0` **or** whose notes indicate staleness
  (e.g. "stale", "predates"). **Include distractor rows** that meet the
  criterion — do not filter out ids that look like noise.
- All id-lists ascending; per-application `deficiency_codes`/`required_actions`
  sorted ascending and de-duplicated.

---

## Family B — Restricted liquor-license staff package

Output (one object): `application_id`, `recommended_posture`
(issue_restricted/request_follow_up/deny), `same_premises_basis_applies` (bool),
`covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`,
`location_specific_control_codes`, `first_90_day_plan` (list of
`{check_code, timing}`), `escalation_trigger_codes`. Join everything through the
application's `location_id` and `license_class`.

**Well-determined fields (compute these exactly):**
- `standard_obligation_codes` = `obligation_code` of the `liquor_privileges`
  rows for this `license_class` where `standard_required == 1`.
- `location_specific_control_codes` = union of the `controls` arrays from
  **active** settlements at the location (a settlement is active when its
  `controls_json.active == true`). Ignore inactive/expired settlements.
- `same_premises_basis_applies` = an **active** settlement with
  `basis_code == SAME_PREMISES` exists at the location.
- `covered_risk_codes` = the risks mitigated by the active controls (the prompt
  says "risks covered by current controls"). Map each active control to its risk
  using the template's risk vocabulary, e.g. NOISE→NOISE, PATIO→PATIO_BOUNDARY,
  HOURS→AFTER_HOURS, CCTV→CAMERA_COVERAGE, ID_CHECK→ID_CHECK,
  FOOD_SERVICE→FOOD_SERVICE_GAP, SECURITY→PUBLIC_SAFETY/ASSAULT; include
  SAME_PREMISES when an active same-premises basis applies.

**Discretion-based fields (derive consistently from evidence status + open
incidents; these are the hard part — be systematic):**
- `verification_gap_codes` from `liquor_site_evidence` and open incidents:
  - evidence `status == conflicting` → the matching `*_CONFLICTING` code
    (control signage, floor plan, police memo);
  - latest control-signage evidence `missing`/`stale` → current-signage-missing /
    `control_signage_missing`; floor plan `stale` → `FLOOR_PLAN_STALE`;
  - a police-memo note referencing an old/different name → identity note code;
  - **expected but absent** evidence, especially camera/CCTV and food-service for
    hotel/food classes → `camera_evidence_missing` / `food_service_evidence_missing`;
    likewise NEIGHBOR_NOTICE/SITE_PHOTO/TAX_CLEARANCE `missing` → their `*_MISSING`;
  - any open/referred incident → open-incident-follow-up; an open `TAX_HOLD`
    incident → `tax_hold_unresolved`; late-night/after-hours emphasis or an active
    noise settlement → `late_night_monitoring_needed`.
  Consider distractor evidence rows too — include a conflict/gap even if the row
  id looks like noise.
- `recommended_posture`: **deny** if a major (high-severity) unresolved/open
  incident or board-order conflict is present; otherwise **request_follow_up** if
  any verification gaps remain; otherwise **issue_restricted**.
- `first_90_day_plan`: one check per active control / standard obligation /
  verification gap, in operational sequence, using the template's `check_code`
  vocabulary (control-signage recheck, police-memo follow-up, security/CCTV or
  camera-export, food-service check, id-check observation, noise/patio boundary,
  tax-clearance review, incident-log review). Assign `timing`
  first_30_days / days_31_60 / days_61_90 by urgency (urgent gaps first). Sort /
  de-duplicate as the template requires.
- `escalation_trigger_codes`: map each active control, gap, and open incident to
  its forward-looking failure trigger (control-signage-not-verified,
  missing_camera_coverage, food_service_not_available, open_tax_hold_uncleared,
  unreported_violent_incident for an open assault, referred-minor-sale-unresolved,
  noise_or_patio_breach, etc.).

Sort every code list ascending and de-duplicate.

---

## Family C — Alcohol renewal manual-review queue

Output: `queue` (length = target size, `rank` 1..N contiguous, ordered by
ascending rank) + `summary`. Per queue item: `rank`, `license_no`,
`facility_name`, `violation_count`, `most_recent_violation_date`,
`matched_violation_ids`, `match_confidence` (exact/close_address/uncertain),
`risk_tier`, `next_step_label`.

### Boundary and matching
- Get the **boundary date** from the prompt (and confirm against the matching
  `renewal_rules` row: `use_violations_on_or_before` / `release_boundary`). Get
  the target queue size from the prompt.
- For each target licensee (select `alcohol_licensees` by the target license-no
  prefix), gather matched violations from `alcohol_violations`:
  - **Exact**: `alcohol_violations.license_no == licensee.license_no` →
    `match_confidence = exact`.
  - **Successor**: if `licensee.successor_to` is set, also include violations on
    that predecessor license and set `match_confidence = uncertain`
    (successor matches are marked uncertain).
  - **Address-only** rows (same `address`, different `license_no`) are
    **distractors** — do not include them when an exact license match exists.
    They belong to other licensees; `close_address` confidence only applies when
    there is no exact license record for the target.
- Keep only violations with `violation_date <= boundary`. Post-boundary rows
  (often `source == post_boundary_feed`, id suffix `-LATE`) are excluded
  distractors.

### Per-entry fields
- `violation_count` = number of matched pre-boundary violations.
- `most_recent_violation_date` = max `violation_date` among matched pre-boundary.
- `matched_violation_ids` sorted by `violation_date` ascending, then
  `violation_id` ascending.

### Classification (heuristic — apply the rule hints consistently)
Renewal-rule hints: `alert_flag_requires_manual_review`,
`unpaid_fines_require_hold`, serious → board. A reasonable, consistent scheme:
- unresolved serious (severity serious, disposition open/pending) →
  `next_step_label = board_review`, `risk_tier = high`;
- else unpaid fine (`fine_balance > 0`, open/pending) → `manual_fine_check`;
- else `alert_flag` present → `manual_ALERT_check`;
- else / uncertain match → `additional_record_check`.
- `rank`: order by priority (board_review first, then by recency/severity),
  ranks contiguous 1..N with no gaps.

### Summary
- `queue_size` (= N), `boundary_date`,
- `post_boundary_violation_ids_excluded` = the matched-license post-boundary ids
  that were dropped, sorted by `violation_id`,
- `close_or_uncertain_match_license_numbers` = licenses whose confidence is
  close_address or uncertain,
- `board_review_license_numbers` = licenses whose next step is board_review.

---

## Reference implementations

`reference/` contains runnable helpers that encode the logic above. They take
target ids / dates as parameters and read connection details from
`environment_access.md`; they contain no answers, only method.
- `env_client.py` — truncation-safe data access (`sql`, `get`, `inlist`).
- `contractor_review.py` — Family A (auto-adapts to the template's code vocabulary).
- `liquor_package.py` — Family B.
- `renewal_queue.py` — Family C.

Confidence notes for whoever extends these: the structural/derivable fields
(policy thresholds, coverage currency, privilege/settlement joins, matching &
boundary filtering, counts/dates/id lists, summary construction) are reliable.
The classification/ordering fields that depend on unstated agency discretion —
liquor `covered_risk`/`gaps`/`plan`/`escalation`/`posture`, and renewal
`risk_tier`/`next_step_label`/`rank` — are heuristics; derive them consistently
from the same evidence and rule hints, and always emit codes using the exact
spellings in the task's own answer template.
