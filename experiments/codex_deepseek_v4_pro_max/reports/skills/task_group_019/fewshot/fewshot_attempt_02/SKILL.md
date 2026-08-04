 # Licensing Review Skill

 ## Overview

 This skill provides reusable instructions for reviewing contractor, liquor, and alcohol license applications, renewals, and transfers in a shared licensing environment. The environment exposes REST endpoints for policy, application, financial-coverage, violation, correspondence, and inspection data, plus a SQL endpoint for cross-referencing records.

 Apply this skill whenever a prompt references `<TASK_ENV_BASE_URL>`, the licensing-review token, or recognizable licensing endpoints. The instructions below are domain-agnostic methodology; do not copy task-specific answer values from training examples.

 ## Environment Setup

 The base URL is provided in the prompt as `<TASK_ENV_BASE_URL>`. Use it for all API calls.

 All GET endpoints accept no special headers.

 The POST `/api/sql` endpoint requires:
- Header `Content-Type: application/json`
- Header `X-Task-Token: licensing-review-019`
- JSON body: `{"query": "<SELECT statement>", "params": ["<value>", ...], "limit": <optional integer>}`

 Always paginate or limit broad queries to avoid timeouts. Use the `limit` field when appropriate.

 ## Domain Detection

 Determine which domain the task belongs to by inspecting the prompt:

| Signal | Domain |
|---|---|
| References `contractor/applications`, contractor application IDs like `C-TR*-*`, contractor-specific endpoints (bonds, insurance, license-history, inspections) | **Contractor Licensing** |
| References `liquor/applications`, liquor application IDs like `L-TR*-*`, liquor-specific endpoints (settlements, privileges, incidents, site-evidence) | **Liquor License** |
| References `alcohol/licensees`, alcohol license IDs like `AL-TR*-*`, renewal rules | **Alcohol Renewal** |

## Domain: Contractor Licensing Batch Review

### Endpoints

Use all of:
- `GET /api/policies`
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`
- `POST /api/sql` (for cross-reference queries)

### Output Schema

Return a JSON object with two top-level keys:

**`application_decisions`** — array of objects, one per target application, ordered ascending by `application_id`. Each object has:

- `application_id` (string): the application identifier from the prompt
- `determination` (enum): `APPROVE`, `HOLD`, or `DENY`
- `deficiency_codes` (array of strings, sorted ascending): codes describing problems found. Use empty array `[]` when no deficiencies exist.
- `required_actions` (array of strings, sorted ascending): remedial steps. Use empty array `[]` when none.
- `risk_tier` (enum): `low`, `medium`, or `high`
- `policy_impacted` (boolean): whether a current policy standard creates a deficiency or review flag that would not have applied under the prior baseline

**`summary`** — object with:

- `approve_count` (integer)
- `hold_count` (integer)
- `deny_count` (integer)
- `high_risk_application_ids` (array of strings, sorted ascending)
- `policy_impacted_application_ids` (array of strings, sorted ascending)
- `stale_or_unverified_correspondence_ids` (array of strings, sorted ascending): correspondence records that are stale or unverified

### Determination Logic

Evaluate each application by cross-referencing data from all contractor endpoints:

- **APPROVE**: No deficiencies found across bonds, insurance, license history, violations, inspections, endorsements, experience, or correspondence.
- **HOLD**: One or more correctable deficiencies exist (e.g. expired insurance, bond shortfall, missing endorsement, experience gap, open minor violation, inspection document gap). The applicant can remedy these.
- **DENY**: One or more non-correctable or severe blockers exist (e.g. active suspension, open serious violation, combination of multiple severe deficiencies).

### Deficiency Codes (Complete Set)

Use only codes from this closed vocabulary. Match each deficiency to the API data observed:

- `active_suspension` — license history shows an active suspension
- `bond_cancelled` — bond record shows cancelled/null status
- `bond_shortfall` — bond amount is below required threshold
- `endorsement_missing` — required endorsement not found in application
- `endorsement_pending` — endorsement exists but not yet verified/confirmed
- `experience_shortfall` — documented experience below minimum
- `inspection_doc_gap` — inspection records have documentation gaps
- `inspection_safety_recheck` — inspection flagged for safety re-inspection
- `insurance_expired` — insurance policy has expired relative to review date
- `insurance_pending` — insurance application pending, not yet bound
- `insurance_shortfall` — insurance coverage below required amount
- `open_minor_violation` — unresolved minor violation
- `open_serious_violation` — unresolved serious violation

Additional codes used in some contractor variants:
- `insurance_not_current` — insurance is present but not current as of review date
- `endorsement_not_verified` — endorsement record exists but cannot be verified
- `no_active_bond` — no active bond on file
- `unresolved_serious_complaint` — serious complaint that remains unresolved

Always use the codes that match the answer template's `allowed_values` for the specific task. If the template lists different codes, prefer the template's vocabulary.

### Required Actions (Complete Set)

Map each deficiency to the corresponding required action. Use the template's `allowed_values`:

- `board_review_suspension` — escalate suspension for board review
- `clear_document_gap` — resolve inspection documentation gaps
- `complete_safety_recheck` — schedule and pass safety re-inspection
- `increase_bond_amount` — raise bond to required minimum
- `increase_insurance_amount` — raise insurance coverage to required minimum
- `obtain_current_bond` — secure a current, active bond
- `obtain_required_endorsement` — acquire the missing endorsement
- `provide_current_insurance` — submit proof of current insurance
- `resolve_minor_violation_review` — resolve open minor violation
- `resolve_serious_violation` — resolve open serious violation
- `submit_experience_evidence` — provide additional experience documentation
- `verify_insurance_binding` — confirm insurance binding status
- `verify_pending_endorsement` — confirm pending endorsement status

Additional actions used in some contractor variants:
- `document_experience` — submit experience documentation
- `file_active_bond` — file a current bond
- `verify_endorsement` — verify endorsement status
- `increase_insurance` — increase insurance coverage
- `increase_bond` — increase bond amount
- `renew_insurance` — renew expired insurance
- `board_review` — escalate to board review
- `resolve_complaint` — resolve open complaint
- `clear_suspension` — clear active suspension

Always use actions from the template's `allowed_values` for the specific task.

### Risk Tier Logic

- **low**: APPROVE with no deficiencies
- **medium**: HOLD with correctable deficiencies
- **high**: DENY or presence of suspension, serious violations, or multiple severe deficiencies

### Policy Impacted Logic

`policy_impacted` is `true` when a current-year policy standard creates a deficiency or material review flag that would not have existed under the prior policy baseline. Cross-reference `/api/policies` response with the application data to determine this.

### Summary Computation

Count determinations to populate `approve_count`, `hold_count`, `deny_count`. Collect all high-risk and policy-impacted application IDs from the decisions. For `stale_or_unverified_correspondence_ids`, scan correspondence records for any that are stale (older than expected response window) or unverified — include their IDs sorted ascending.

## Domain: Liquor License Staff Package

### Endpoints

Use all of:
- `GET /api/policies`
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`
- `POST /api/sql` (when available; some tasks omit SQL access)

### Output Schema

Return a single JSON object (not an array) with these top-level keys:

- `application_id` (string): the target application ID from the prompt
- `recommended_posture` (enum): `issue_restricted`, `request_follow_up`, or `deny`
- `same_premises_basis_applies` (boolean)
- `covered_risk_codes` (array of strings, sorted ascending, no duplicates)
- `verification_gap_codes` (array of strings, sorted ascending, no duplicates)
- `standard_obligation_codes` (array of strings, sorted ascending, no duplicates)
- `location_specific_control_codes` (array of strings, sorted ascending, no duplicates)
- `first_90_day_plan` (array of objects with `check_code` and `timing`, sorted ascending by `check_code`)
- `escalation_trigger_codes` (array of strings, sorted ascending, no duplicates)

### Posture Logic

- **issue_restricted**: Application can be approved with restricted conditions. Risks are covered by existing controls or can be mitigated with standard obligations.
- **request_follow_up**: Gaps exist that require additional evidence, verification, or follow-up before a decision. The applicant or field staff must provide more information.
- **deny**: Unresolvable blockers exist (e.g. major unresolved incidents, tax holds, evidence of disqualifying behavior).

### Code Vocabularies

There are two liquor license variants with slightly different code sets. Always consult the task's answer template `allowed_values` for the exact vocabulary.

**Standard variant** (basic liquor transfer review):

Covered risk codes: `AFTER_HOURS`, `ASSAULT`, `FOOD_SERVICE_GAP`, `MINOR_SALE`, `NOISE`, `PUBLIC_SAFETY`, `SALE_TO_MINOR`, `SAME_PREMISES`, `TAX_HOLD`

Verification gap codes: `CONTROL_SIGNAGE_CONFLICTING`, `CONTROL_SIGNAGE_CURRENT_MISSING`, `FLOOR_PLAN_CONFLICTING`, `FLOOR_PLAN_STALE`, `NEIGHBOR_NOTICE_MISSING`, `OPEN_INCIDENT_FOLLOW_UP`, `POLICE_MEMO_CONFLICTING`, `SITE_PHOTO_MISSING`, `TAX_CLEARANCE_MISSING`

Standard obligation / location-specific control codes: `CCTV`, `DELIVERY`, `FOOD_SERVICE`, `HOURS`, `ID_CHECK`, `NOISE`, `PATIO`, `SECURITY`

90-day plan check codes: `after_hours_visit`, `control_signage_recheck`, `food_service_check`, `id_check_observation`, `noise_log_review`, `patio_boundary_check`, `police_memo_follow_up`, `security_cctv_walkthrough`, `tax_clearance_check`

Timing values: `first_30_days`, `days_31_60`, `days_61_90`

Escalation trigger codes: `AFTER_HOURS_VIOLATION`, `BOARD_ORDER_CONFLICT`, `CONTROL_SIGNAGE_NOT_VERIFIED`, `MAJOR_INCIDENT_REPORTED`, `REFERRED_MINOR_SALE_UNRESOLVED`, `SECURITY_CCTV_CONTROL_FAILURE`, `TAX_HOLD_REOPENED`

**Hotel-lounge variant** (focus on camera, food-service, and late-night monitoring):

Covered risk codes: `NOISE`, `PATIO_BOUNDARY`, `AFTER_HOURS`, `ASSAULT`, `MINOR_SALE`, `TAX_HOLD`, `FOOD_SERVICE_GAP`, `CAMERA_COVERAGE`, `ID_CHECK`

Verification gap codes: `camera_evidence_missing`, `food_service_evidence_missing`, `floor_plan_conflicting`, `late_night_monitoring_needed`, `tax_hold_unresolved`, `control_signage_missing`, `police_memo_identity_note`, `neighbor_notice_missing`, `site_photo_missing`

Standard obligation / location-specific control codes: `ID_CHECK`, `HOURS`, `SECURITY`, `FOOD_SERVICE`, `CCTV`, `PATIO`, `NOISE`, `DELIVERY`

90-day plan check codes: `camera_export_test`, `food_service_service_area_check`, `late_night_closing_visit`, `noise_patio_boundary_check`, `id_check_observation`, `control_signage_review`, `tax_clearance_review`, `incident_log_review`

Escalation trigger codes: `after_hours_service`, `missing_camera_coverage`, `footage_not_produced`, `food_service_not_available`, `noise_or_patio_breach`, `open_tax_hold_uncleared`, `unreported_violent_incident`, `minor_sale`, `patio_boundary_failure`, `id_check_failure`

### Cross-Referencing Logic

To determine covered risks, verification gaps, obligations, and controls:

1. Fetch all endpoint data for the target application and location.
2. Compare application details against policy requirements from `/api/policies`.
3. Check incident and settlement records for unresolved or high-severity items.
4. Check site evidence for missing or conflicting documentation.
5. Separate standard obligations (universal for the license class) from location-specific controls (tied to the specific premises).
6. For each risk, determine whether it is covered by existing controls or represents a verification gap.

### 90-Day Plan Construction

For each verification gap or identified risk, assign an appropriate `check_code` and `timing`:
- Immediate concerns → `first_30_days`
- Monitoring/observation items → `days_31_60`
- Follow-up verification → `days_61_90`

Sort the plan array ascending by `check_code`.

## Domain: Alcohol Renewal Review Queue

### Endpoints

Use all of:
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`
- `POST /api/sql`

### Output Schema

Return a JSON object with two top-level keys:

**`queue`** — array of exactly the target queue size (typically 10), ordered by ascending `rank` (1 through N with no gaps). Each entry:

- `rank` (integer): 1-based position in the queue
- `license_no` (string): stable license identifier
- `facility_name` (string): facility name from licensee data
- `violation_count` (integer): count of matched violations within the boundary
- `most_recent_violation_date` (string, YYYY-MM-DD): date of most recent matched violation
- `matched_violation_ids` (array of strings): IDs of all matched violations
- `match_confidence` (enum): `exact`, `close_address`, or `uncertain`
- `risk_tier` (enum): `high`, `medium`, or `low`
- `next_step_label` (enum): `board_review`, `manual_fine_check`, or `manual_ALERT_check`

**`summary`** — object with:

- `queue_size` (integer): total entries in the queue
- `boundary_date` (string, YYYY-MM-DD): the release boundary date from the prompt
- `post_boundary_violation_ids_excluded` (array of strings, sorted ascending): violation IDs that fall after the boundary date and were excluded
- `close_or_uncertain_match_license_numbers` (array of strings, sorted ascending): licenses with non-exact match confidence
- `board_review_license_numbers` (array of strings, sorted ascending): licenses flagged for board review

### Ranking Methodology

Rank licenses for manual review using this priority order:

1. **Violation recency**: Most recent violations first (descending date order). The boundary date in the prompt establishes the cutoff — only violations on or before this date count.
2. **Violation count**: More violations → higher priority, when recency is similar.
3. **Match confidence**: Exact matches rank above close/uncertain matches, all else equal.
4. **Risk tier**: High-risk licenses rank above medium.

### Violation Matching

Match violations to licensees using the following approach:

1. Query `/api/alcohol/violations` for all violation records.
2. Query `/api/alcohol/licensees` for all target licensees.
3. Match by exact license number when possible → `exact` confidence.
4. When only partial or address-based matches exist, use `close_address` or `uncertain` confidence.
5. Exclude violations dated after the boundary date. List these excluded IDs in `post_boundary_violation_ids_excluded`.

### Next-Step Labels

- **board_review**: License has violations serious enough to warrant board escalation.
- **manual_fine_check**: License needs manual verification of fines/penalties.
- **manual_ALERT_check**: License has alert-level concerns requiring specific review.

### Summary Computation

- `queue_size`: always equal to the number of queue entries (typically 10).
- `boundary_date`: copy from the prompt.
- `post_boundary_violation_ids_excluded`: all violation IDs with dates after the boundary.
- `close_or_uncertain_match_license_numbers`: licenses where match_confidence is not `exact`.
- `board_review_license_numbers`: licenses with `next_step_label` of `board_review`.

## Common Patterns

### SQL Queries

When the environment provides `POST /api/sql`, use it to:
- Cross-reference records across tables when relationships are not obvious from individual endpoints
- Verify that application/license IDs exist in related tables
- Count records matching specific criteria
- Identify stale or unverified correspondence by date comparisons

Always include a `limit` parameter for broad queries. Use parameterized queries with the `params` array.

### Sorting and Deduplication

- Sort all string arrays in ascending lexical order unless the answer template specifies otherwise.
- Remove duplicate entries from all arrays.
- Sort `application_decisions` by `application_id` ascending.
- Sort `queue` entries by `rank` ascending.

### Date Handling

- All dates should be in `YYYY-MM-DD` format.
- When a review date is specified in the prompt, use it to determine whether financial coverage (bonds, insurance) is current.
- For renewal tasks, the boundary date establishes which violations are in scope.

### Answer Template Compliance

1. Always read the task's `input/payloads/answer_template.json` first to understand the exact schema, allowed values, and ordering requirements.
2. The template's `allowed_values` lists are authoritative — use only those values even if similar codes appear in other domains.
3. Return only the JSON object described in the template. Do not include prose, markdown, citations, comments, or extra keys.
4. Match the exact key names, nesting, and types shown in the template.
