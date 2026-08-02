---
name: licensing-review-decisions
description: >-
  Produce structured JSON decisions for State licensing-board review tasks that read
  from a shared licensing-environment API and must conform exactly to a provided
  answer_template.json. Covers the three recurring task families: (A) contractor batch
  eligibility review, (B) restricted liquor-license staff package, (C) alcohol renewal
  manual-review queue. Use whenever a prompt casts you as a licensing examiner / renewal
  or staff reviewer, references a `<TASK_ENV_BASE_URL>` with `/api/...` endpoints, and
  asks for JSON matching `input/payloads/answer_template.json`.
---

# Licensing-review structured decisions

You are given a licensing-review prompt plus an `answer_template.json`. Fetch records
from a shared licensing environment, apply the policy-driven rules, and return **only** a
JSON object that conforms exactly to the template. See `reference/data_model.md` for
full endpoint schemas, policy fields, and code-mapping tables.

## 0. Golden rules (apply to every task)

1. **The `answer_template.json` is the contract.** Output exactly its top-level keys and
   item keys, use only enum values from its `allowed_values`, honour every `ordering`
   note, and include nothing else — no prose, markdown, comments, citations, or extra
   keys. Enum vocabularies differ between tasks; never carry codes over from another task.
2. **Read `environment_access.md` for network access** — base URL and the
   `X-Task-Token` for `POST /api/sql`. Do not hard-code them.
3. **Filter hard to the prompt's targets.** The environment is one shared pool holding
   many unrelated rows (`*-DIS-*`, `*-TE2-*`, other locations, `INC-DIS-*`, `EV-DIS-*`).
   Work only the exact application/location/license IDs the prompt names.
4. **Pick the current record, drop the historical twin.** Entities carry a current row
   (`...-A`, `active`, "Current …", `controls_json.active=true`) plus historical
   distractors (`...-OLD`, `cancelled`/`expired`, `active=false`, past `expires`,
   post-boundary `-LATE`). Use the current one for eligibility; use history only where a
   rule explicitly needs it (suspension, successor, excluded lists).
5. **Empty list, not null/omit,** when nothing applies. **Deduplicate** code lists.
   Dates are `YYYY-MM-DD`.
6. **Make the summary self-consistent** with the item-level decisions (counts sum to the
   required length; id lists are derived from the items).
7. Parse from the prompt: target IDs, location/license IDs, the **review/boundary date**,
   the **queue/target size**, and the license class. Confirm your item count equals the
   template's `required_length`/`length`.

## 1. Get the data

Prefer `POST /api/sql` (send `{"query":"SELECT ..."}` with the `X-Task-Token` header) to
filter and join straight to the target IDs — table name = endpoint path with `/`→`_`
(e.g. `contractor_applications`), results cap at 200 rows, `SELECT`-only. GET endpoints
return the full array if you'd rather filter in code. Always parse each policy's
`details_json` (it is a JSON string). Identify the task family from the endpoints/prompt.

## 2. Family A — Contractor batch eligibility review

Endpoints: `policies` + `contractor/{applications,bonds,insurance,license-history,
violations,correspondence,inspections}`. Output: `application_decisions[]`
(`application_id, determination, deficiency_codes[], required_actions[], risk_tier,
policy_impacted`) + `summary`.

For each target application:
1. Map `(trade, requested_class)` → its contractor policy standard; read
   `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
   `required_endorsement`, `serious_open_violation_blocks`.
2. **Bond** (current = `active`, `cancel_date` null, effective by the review date):
   none current → `bond_cancelled`/`no_active_bond`; amount < minimum → `bond_shortfall`.
3. **Insurance** (current = `active`, `expiration_date` > review date): `pending` →
   `insurance_pending`/`insurance_not_current`; expired/lapsed → `insurance_expired`;
   amount < minimum → `insurance_shortfall`.
4. **Experience** < minimum → `experience_shortfall`.
5. **Endorsement** required and status `missing`/`pending` → `endorsement_missing`/
   `endorsement_pending`/`endorsement_not_verified` (`verified`/`not_required` = ok; do
   not treat as verified on the strength of unverified correspondence).
6. **License history** `suspended` → `active_suspension` (hard blocker).
7. **Violations** (by `related_application_id`): open + serious →
   `open_serious_violation`/`unresolved_serious_complaint` (hard blocker when
   `serious_open_violation_blocks`); open minor/medium → `open_minor_violation`.
8. **Inspections**: `DOC_GAP` → `inspection_doc_gap`; `SAFETY_RECHECK` →
   `inspection_safety_recheck` (only if in this template's vocab).
9. **Correspondence**: `verified_by_agency=0` or a "stale/predates" note → add its id to
   `stale_or_unverified_correspondence_ids`.

`required_actions` pair 1:1 with the deficiencies (see the reference table).
**Determination**: hard blocker (active suspension / open serious violation) → most
restrictive posture (`DENY`, or `HOLD` escalated to board review) per the policy flag;
any fixable coverage gap → `HOLD`; clean file → `APPROVE`. **`risk_tier`**: hard
blockers/multiple serious gaps → `high`; a fixable gap or two → `medium`; clean/trivial →
`low`. **`policy_impacted`** = the deficiency exists only under the current 2025 standard
vs. `POL-CON-LEGACY` (specialty-endorsement now required; or bond short only after the
$10k legacy reduction). Summary: `approve/hold/deny_count` (sum = count),
`high_risk_application_ids`, `policy_impacted_application_ids`,
`stale_or_unverified_correspondence_ids` — each sorted per the template.

## 3. Family B — Restricted liquor-license staff package

Endpoints: `policies` + `liquor/{applications,settlements,privileges,incidents,
site-evidence}`. One target `application_id`/`location_id`. Output keys:
`recommended_posture, same_premises_basis_applies, covered_risk_codes,
verification_gap_codes, standard_obligation_codes, location_specific_control_codes,
first_90_day_plan, escalation_trigger_codes` (+ `application_id`).

- **`standard_obligation_codes`** = `liquor_privileges` for this `license_class` where
  `standard_required=1` (ordinary obligations — kept separate from controls).
- **`location_specific_control_codes`** = the `controls` arrays of settlements at this
  location whose `controls_json.active=true` (current, not expired).
- **`same_premises_basis_applies`** = an active settlement at the location has
  `basis_code=SAME_PREMISES` (historic/inactive ones do not count).
- **`covered_risk_codes`** = risk bases addressed by those current active controls.
- **`verification_gap_codes`** = from **current** `site-evidence` with status
  `missing`/`stale`/`conflicting`, open incidents, and missing tax/neighbor items — map
  `evidence_code`+`status` (and open TAX_HOLD/late-night context) to the template's gap
  codes (see reference table). Only current evidence counts.
- **`first_90_day_plan`** = `{check_code, timing}` objects pairing the identified gaps and
  controls with `first_30_days` (urgent verification) → `days_31_60` → `days_61_90`
  (ongoing monitoring); dedupe pairs; order per template (by `check_code`, or operational
  sequence).
- **`escalation_trigger_codes`** = the template's triggers for the covered risks / controls
  that could fail.
- **`recommended_posture`**: unresolved major incident / board-review trigger / hard
  disqualifier → `deny`; open verification gaps remain → `request_follow_up`; controls in
  place and gaps minor/none → `issue_restricted`.

## 4. Family C — Alcohol renewal manual-review queue

Endpoints: `alcohol/{licensees,violations}` + `renewal/rules` (+ SQL). Output: `queue[]`
of the target size (`rank, license_no, facility_name, violation_count,
most_recent_violation_date, matched_violation_ids[], match_confidence, risk_tier,
next_step_label`) + `summary`.

1. Take the boundary date and queue size from the prompt; find the matching
   `renewal_rules` row (`release_boundary`).
2. Per target license, match `alcohol_violations` by `license_no`; keep only
   `violation_date <= boundary`. Post-boundary rows (`post_boundary_feed` / `-LATE`) are
   distractors → `post_boundary_violation_ids_excluded`.
3. `violation_count` = matched pre-boundary count; `most_recent_violation_date` = max of
   those; `matched_violation_ids` sorted by (`violation_date` asc, `violation_id` asc).
4. `match_confidence`: `exact` (direct license match), `uncertain` (`successor_to` set),
   `close_address` (matched by address, not exact license). Inactive predecessor permits
   (`active=0`) are not queue rows — they only inform a successor's `uncertain` history.
5. `risk_tier` from severity/count/unpaid fines/alert flags; `next_step_label` =
   `manual_fine_check` (unpaid `fine_balance>0`), `manual_ALERT_check` (`alert_flag=1`),
   `board_review` (serious/major or unpaid-fine hold), `additional_record_check`
   (close/uncertain match).
6. Rank `1..N` with no gaps (descending risk/severity/recency); queue length = target
   size exactly. Summary: `queue_size`, `boundary_date`,
   `post_boundary_violation_ids_excluded` (by `violation_id`),
   `close_or_uncertain_match_license_numbers`, `board_review_license_numbers` — sorted.

## 5. Finish

Validate against the template: exact keys, allowed enum values, orderings, list dedupe,
empty-list handling, self-consistent summary, item count. Emit the single JSON object as
the answer (write it to the template's `response_file` if one is named, e.g.
`answer.json`); output nothing else.
