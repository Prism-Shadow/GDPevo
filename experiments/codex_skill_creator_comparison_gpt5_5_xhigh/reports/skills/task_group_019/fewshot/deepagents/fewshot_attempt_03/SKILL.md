---
name: licensing-record-review
description: Structured licensing decision support for Codex tasks that use a shared task-environment API and require JSON-only answers for contractor eligibility batches, restricted liquor-license staff packages, or alcohol renewal manual-review queues. Use when prompts mention contractor applications, bonds, insurance, license history, violations, correspondence, inspections, restricted liquor settlements, site evidence, alcohol renewal rules, release boundaries, or manual-review queue ranking.
license: MIT
---

# Licensing Record Review

Use this skill to turn licensing-environment records into the exact JSON requested by the prompt's `answer_template.json`.

## Core Workflow

1. Read the prompt and the answer template before querying records.
2. Extract only the target identifiers named in the prompt: application IDs, location IDs, license numbers, review date, release boundary, and queue size.
3. Query the task environment using the staged base URL. Prefer per-ID filters. Do not learn from unrelated rows returned by broad endpoints.
4. Parse `details_json` and other JSON-in-string fields before applying rules.
5. Build the answer from the template's allowed keys and enum values. If a concept maps to different code names across templates, use the code names present in that template.
6. Sort arrays exactly as the template says. If the template accepts any order, still use a stable order unless it requests operational sequence.
7. Return only the final JSON object.

Optional helper:

```bash
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" contractor --ids C-EXAMPLE-001 C-EXAMPLE-002
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" liquor --applications L-EXAMPLE-001 --locations LOC-EXAMPLE
python skill/scripts/fetch_records.py --base-url "$TASK_ENV_BASE_URL" renewal --licenses AL-EXAMPLE-001 AL-EXAMPLE-002 --boundary YYYY-MM-DD
```

The helper prints fetched records only. You still apply the prompt template and reasoning below.

## Contractor Eligibility

Fetch `/api/policies`, contractor applications, bonds, insurance, license history, violations, correspondence, and inspections. For batches, process only the target application IDs and output decisions ordered by `application_id`.

Policy matching:

- Match contractor policy rows by trade and requested class using `rule_code`, `title`, and `details_json`.
- Use the prompt's review date. If only a quarter is named, use the end of that quarter as the financial-currentness date.
- Compare active financial records against the current policy's `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, and `required_endorsement`.
- Use the legacy contractor policy only to decide `policy_impacted`: mark true when a current policy threshold or endorsement requirement creates a deficiency that would not exist under the prior baseline.

Deficiency rules:

- Bond: require an active bond with no cancellation before the review date. If none exists, use the template's no-current-bond code such as `bond_cancelled` or `no_active_bond`. If active amount is below the policy minimum, use `bond_shortfall`.
- Insurance: require a current active policy through the review date and sufficient amount. Pending records map to `insurance_pending` or `insurance_not_current`. Expired active records map to `insurance_expired` or `insurance_not_current`. Insufficient amount maps to `insurance_shortfall`.
- Endorsement: if the policy requires an endorsement, `missing` maps to `endorsement_missing` or `endorsement_not_verified`; `pending` maps to `endorsement_pending` or `endorsement_not_verified`.
- Experience: years below the policy minimum maps to `experience_shortfall`.
- License history: a prior-license record with `status` of `suspended` maps to `active_suspension`.
- Violations: open serious records map to `open_serious_violation` or `unresolved_serious_complaint`; open minor records map to `open_minor_violation` when that enum exists. Ignore resolved or dismissed violations for current deficiencies unless the prompt specifically asks for history.
- Inspections: only use inspection codes the template supports. `DOC_GAP` with `fail` or `conditional` maps to document-gap codes. `SAFETY_RECHECK` with `fail` maps to safety-recheck codes. Ignore `NONE` and passing findings.

Determination and risk:

- `DENY` when an active suspension or unresolved serious/open complaint blocks eligibility.
- `APPROVE` only when no deficiency or required action applies.
- `HOLD` for all other curable deficiencies.
- Risk is `high` for deny/blocking cases, `low` for approve, and usually `medium` for non-blocking holds unless the template or prompt defines a stronger rule.

Required actions:

- Map every deficiency to the matching action enum in the template. Examples: bond shortfall to increase-bond action, no active bond to current-bond action, insurance expired/not current to current-insurance action, insurance shortfall to increase-insurance action, endorsement issues to verify/obtain endorsement action, experience shortfall to document/submit experience action, active suspension to suspension clearance and board review, serious open violation to complaint/violation resolution and board review.
- Include no action that has no corresponding deficiency unless the template explicitly requires board review for a blocking deficiency.
- Sort deficiency and action arrays lexically when requested.

Contractor summary:

- Counts must equal the per-application determinations.
- High-risk IDs are all decisions with `risk_tier` of `high`.
- Policy-impacted IDs are all decisions with `policy_impacted: true`.
- Stale or unverified correspondence IDs include records tied to target applications where `verified_by_agency` is false, or the record explicitly says the attachment is stale, unverified, or conflicts with the registry. Sort IDs lexically.

## Restricted Liquor Review

Fetch the target liquor application, all settlements for its location, privileges for the application license class, incidents for the location, site evidence for the location, and liquor policies.

Core derivation:

- `standard_obligation_codes`: privilege rows for the license class where `standard_required` is truthy.
- `location_specific_control_codes`: unique controls from active settlement `controls_json.controls` rows for the target location.
- `same_premises_basis_applies`: true when any settlement/history row for the location has `basis_code` of `SAME_PREMISES`, even if the current control set is different.
- `recommended_posture`: use `issue_restricted` only when current controls cover the risk profile and no material verification gap remains; use `request_follow_up` when controls can support issuance but evidence, incident, tax, signage, floor-plan, food-service, or camera checks remain; use `deny` for unresolved blocking risk that cannot be cured by restrictions.

Covered risks:

- Include active settlement basis codes that are covered by current active controls.
- Map active controls to related risk coverage: `HOURS` covers after-hours risk, `SECURITY` or `CCTV` covers assault/public-safety risks, `ID_CHECK` covers minor-sale or sale-to-minor risks, `NOISE` covers noise risk, `PATIO` covers patio-boundary risk, and `FOOD_SERVICE` covers food-service-gap risk.
- Standard obligations may cover ordinary license-class risks, but keep them separate from location-specific controls in the output.
- Do not count dismissed incidents as uncovered risk; use them only if the prompt asks for history or monitoring.

Verification gaps:

- Site evidence with `status: missing` maps to current-missing evidence codes for that evidence type.
- Site evidence with `status: conflicting` maps to conflicting evidence codes.
- Open, referred, or unresolved incidents map to open-incident or tax-hold follow-up gaps when the template has those codes.
- Missing camera or food-service evidence is a gap when the prompt or controls make camera coverage or meal service material.
- Use late-night monitoring gaps when after-hours history or operating-hours controls require field validation.

Plans and escalation triggers:

- First 30 days: evidence verification, control-signage rechecks, police memo follow-up, camera walkthrough/export tests, food-service checks, ID-check observation, and unresolved incident/tax checks.
- Days 31-60: after-hours or late-night closing visits.
- Days 61-90: noise, patio, and boundary follow-up unless the template asks for a different operational sequence.
- Escalation triggers mirror the risks and gaps: after-hours service, failed control/signage verification, camera or footage failure, food-service unavailability, minor-sale recurrence, major/violent incidents, unresolved tax hold, and noise/patio boundary breach. Use the exact enum names from the template.

## Alcohol Renewal Queue

Fetch target licensees, renewal rules, and violations for each target license. If a licensee has `successor_to`, also fetch violations for the successor license number and include only close address/name matches.

Boundary and matching:

- Use the prompt's release boundary or the matching `/api/renewal/rules.release_boundary`.
- Matched violations are known on or before the boundary. Exclude later records, especially `post_boundary_feed` rows, and list their IDs in the summary if requested.
- Exact target-license rows have `match_confidence: exact`.
- Successor rows with the same or close address/name have `match_confidence: close_address`.
- Use `uncertain` only when the prompt requires inclusion but identity is weaker than close address.
- Sort `matched_violation_ids` by violation date ascending, then ID ascending.

Risk and next step:

- `board_review` for severe public-safety facts: close/uncertain successor matches with serious open or pending rows, serious open/pending rows with substantial fine exposure, or sale-to-minor facts with substantial unresolved fine exposure.
- `manual_fine_check` when unpaid fines require hold and a matched violation has a substantial balance or a serious warning/balance pattern, after board-review cases are removed.
- `manual_ALERT_check` when alert flags require manual review and no stronger board or fine-check rule applies.
- `additional_record_check` for included records that lack the stronger board, fine, or alert triggers.
- Risk is `high` for board review, substantial fine checks, or serious open/pending violation patterns; `medium` for lesser alert/manual review; `low` only when the template permits low-risk queue entries.

Queue ordering:

- Rank by next-step severity first: board review, then manual fine check, then manual alert check, then additional record check.
- Within each severity group, order by most recent matched violation date descending, then violation count descending, then license number ascending.
- Fill ranks from 1 through the requested queue size with no gaps.

Renewal summary:

- `queue_size` equals the number of queue entries returned.
- `boundary_date` is the applied release boundary.
- `post_boundary_violation_ids_excluded` includes target-license violation IDs after the boundary, sorted lexically.
- `close_or_uncertain_match_license_numbers` includes licenses whose matched set used successor or uncertain records.
- `board_review_license_numbers` includes queue entries whose next step is `board_review`, sorted lexically.
