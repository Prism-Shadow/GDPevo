# Licensing Environment Review Skill

## Overview

This skill produces structured JSON decisions for state licensing board tasks by querying a shared licensing environment API and applying board policy rules. It covers three task archetypes:

1. **Contractor Batch Eligibility Review** — batch determination for contractor license applications
2. **Restricted Liquor License Staff Package** — single-application staff review for restricted liquor licenses
3. **Alcohol Renewal Manual Review Queue** — ranked manual-review queue for alcohol license renewals

## Environment Access

Read `environment_access.md` (staged in the work directory) to obtain:
- **Base URL** (format: `http://task-env:<port>/`)
- **Auth header** for POST /api/sql (header name and token value)
- **Allowed endpoint list**

Never attempt paths not listed in that file. Always substitute `<TASK_ENV_BASE_URL>` in prompts with the actual base URL from `environment_access.md`.

## General Procedure

1. **Parse the prompt** to identify the task archetype, target application(s)/license(s), applicable endpoints, and any date parameters.
2. **Fetch all relevant endpoints** from the licensing environment. Use GET endpoints for each data domain the prompt lists. If cross-referencing is needed, use POST `/api/sql` with the auth header from `environment_access.md`.
3. **Fetch current policies** via GET `/api/policies` — this is needed in every task type to determine whether a 2025 policy baseline changes the analysis (the `policy_impacted` flag).
4. **Apply decision rules** (see archetype-specific sections below).
5. **Read the answer template** from `input/payloads/answer_template.json` to confirm the exact field names, allowed enum values, ordering requirements, and list lengths.
6. **Emit only the JSON object** — no prose, markdown, comments, or extra keys.

## Archetype 1: Contractor Batch Eligibility Review

### When to use
The prompt names a batch of contractor application IDs (e.g., C-TRx-NNN) and asks for eligibility determinations.

### Data endpoints
- GET `/api/policies`
- GET `/api/contractor/applications`
- GET `/api/contractor/bonds`
- GET `/api/contractor/insurance`
- GET `/api/contractor/license-history`
- GET `/api/contractor/violations`
- GET `/api/contractor/correspondence`
- GET `/api/contractor/inspections`
- POST `/api/sql`

### Decision rules per application

#### Determination logic
1. **DENY** if any of:
   - Active suspension on license history (no reinstatement recorded).
   - Unresolved serious violation or complaint.
   - Multiple compounding deficiencies that make approval infeasible (e.g., active suspension + experience shortfall + insurance not current).

2. **HOLD** if deficiencies exist that can be remedied:
   - Bond shortfall or cancelled bond.
   - Insurance expired, not current, or short of required coverage.
   - Endorsement missing or pending (not yet verified).
   - Experience shortfall (documentation gap).
   - Inspection document gap or safety recheck needed.
   - Open minor violation (not serious enough for denial).

3. **APPROVE** only when zero deficiency codes apply.

#### Deficiency code assignment
Cross-reference each application record against bond, insurance, license-history, violations, inspections, and endorsement data:
- **active_suspension** — active suspension record in license history with no clearance date.
- **bond_cancelled** / **no_active_bond** — bond record shows cancelled or no active bond on file.
- **bond_shortfall** — bond amount below the required threshold per policy.
- **insurance_expired** / **insurance_not_current** — insurance end date before the review date.
- **insurance_pending** — insurance application filed but not yet bound.
- **insurance_shortfall** — coverage amount below policy requirement.
- **endorsement_missing** / **endorsement_not_verified** — required specialty endorsement absent or not verified.
- **endorsement_pending** — endorsement application filed but verification incomplete.
- **experience_shortfall** — documented experience hours below the threshold.
- **inspection_doc_gap** — inspection report missing required documentation.
- **inspection_safety_recheck** — safety recheck flagged and not cleared.
- **open_minor_violation** — minor violation unresolved but not serious.
- **open_serious_violation** / **unresolved_serious_complaint** — serious violation or complaint with no resolution.

#### Required action mapping
Each deficiency code maps to one required action:
| Deficiency | Action |
|---|---|
| active_suspension | board_review_suspension / clear_suspension + board_review |
| bond_cancelled / no_active_bond | obtain_current_bond / file_active_bond |
| bond_shortfall | increase_bond_amount / increase_bond |
| insurance_expired | provide_current_insurance / renew_insurance |
| insurance_not_current | provide_current_insurance |
| insurance_pending | verify_insurance_binding |
| insurance_shortfall | increase_insurance_amount / increase_insurance |
| endorsement_missing | obtain_required_endorsement / verify_endorsement |
| endorsement_not_verified | verify_endorsement |
| endorsement_pending | verify_pending_endorsement |
| experience_shortfall | submit_experience_evidence / document_experience |
| inspection_doc_gap | clear_document_gap |
| inspection_safety_recheck | complete_safety_recheck |
| open_minor_violation | resolve_minor_violation_review |
| open_serious_violation / unresolved_serious_complaint | resolve_serious_violation / resolve_complaint (+ board_review) |

#### Risk tier
- **high** — any DENY-level finding (active suspension, serious violation), or ≥3 compounding deficiencies.
- **medium** — any HOLD-level deficiency but no DENY-level finding.
- **low** — zero deficiencies (APPROVE only).

#### Policy impacted
Set `policy_impacted: true` when the current 2025 contractor policy baseline creates a deficiency or material review flag that would not have applied under the prior baseline. Check `/api/policies` for the current vs. prior standards on bond amounts, insurance minimums, endorsement requirements, and experience thresholds.

#### Summary fields
- Count approve/hold/deny determinations.
- List high-risk application IDs (ascending order).
- List policy-impacted application IDs (ascending order).
- List stale or unverified correspondence IDs — from `/api/contractor/correspondence`, select correspondence records that are unverified, stale (past expected response date with no reply), or whose status is not "closed"/"resolved". Sort ascending.

#### Ordering
- `application_decisions`: ascending by application_id.
- All code/action lists within each decision: ascending lexical order.
- All summary ID lists: ascending lexical order.

## Archetype 2: Restricted Liquor License Staff Package

### When to use
The prompt names a single liquor license application ID (e.g., L-TRx-NNN) and a location ID (e.g., LOC-TRx), asking for a structured staff package.

### Data endpoints
- GET `/api/policies`
- GET `/api/liquor/applications`
- GET `/api/liquor/settlements`
- GET `/api/liquor/privileges`
- GET `/api/liquor/incidents`
- GET `/api/liquor/site-evidence`
- POST `/api/sql` (if available)

### Decision rules

#### Recommended posture
1. **deny** — active disqualifying incident (e.g., unresolved serious assault), or tax hold with no clearance path.
2. **request_follow_up** — verification gaps exist (missing signage evidence, conflicting floor plans, open incident, missing site photos, conflicting police memo) but are remediable. This is the most common posture when gaps are present.
3. **issue_restricted** — all verification gaps resolved, controls in place, no open incidents requiring follow-up.

#### Same premises basis
Set `same_premises_basis_applies: true` when the application involves a transfer or continuation at the same physical premises where a prior license was held (check application data and settlement records for transfer/same-premises indicators). False if the location is new or changed.

#### Covered risk codes
From incidents, privileges, settlements, and policy data, identify which risk categories are actively covered by existing controls. Common codes include: AFTER_HOURS, ASSAULT, MINOR_SALE, SALE_TO_MINOR, SAME_PREMISES, NOISE, PATIO_BOUNDARY, CAMERA_COVERAGE, FOOD_SERVICE_GAP, TAX_HOLD, PUBLIC_SAFETY, ID_CHECK. Include only risks for which there is evidence of an active control or settlement term addressing that risk.

#### Verification gap codes
Compare site-evidence records against required documentation. Flag each gap:
- Missing control signage → CONTROL_SIGNAGE_CURRENT_MISSING / control_signage_missing
- Conflicting signage → CONTROL_SIGNAGE_CONFLICTING
- Missing site photo → SITE_PHOTO_MISSING
- Conflicting floor plan → FLOOR_PLAN_CONFLICTING / FLOOR_PLAN_STALE / floor_plan_conflicting
- Missing neighbor notice → NEIGHBOR_NOTICE_MISSING
- Missing camera evidence → camera_evidence_missing
- Missing food service evidence → food_service_evidence_missing
- Late-night monitoring gap → late_night_monitoring_needed
- Open incident needing follow-up → OPEN_INCIDENT_FOLLOW_UP
- Conflicting police memo → POLICE_MEMO_CONFLICTING / police_memo_identity_note
- Unresolved tax hold → TAX_CLEARANCE_MISSING / tax_hold_unresolved

Note: exact allowed enum values vary by task — always read the answer template for the specific code set.

#### Standard obligation codes vs. location-specific control codes
- **Standard obligations**: obligations that apply to all licenses of this class by default (e.g., ID_CHECK, HOURS, FOOD_SERVICE). Check `/api/policies` for the class baseline.
- **Location-specific controls**: additional or enhanced controls tied to this specific location (e.g., CCTV, SECURITY, PATIO, NOISE). Check privileges and site-evidence for location-specific conditions.

#### First 90-day plan
Design a monitoring schedule:
- **first_30_days**: items needing immediate verification (e.g., control_signage_recheck, id_check_observation, security_cctv_walkthrough, camera_export_test, food_service_service_area_check, police_memo_follow_up, control_signage_review).
- **days_31_60**: items needing operational confirmation (e.g., after_hours_visit, late_night_closing_visit).
- **days_61_90**: items for sustained compliance checks (e.g., noise_log_review, noise_patio_boundary_check, patio_boundary_check, tax_clearance_check, incident_log_review).

Sort by check_code ascending within timing groups, unless the template specifies operational sequence ordering.

#### Escalation trigger codes
Identify events that would escalate the license to board review or enforcement:
- AFTER_HOURS_VIOLATION / after_hours_service
- MAJOR_INCIDENT_REPORTED / unreported_violent_incident
- CONTROL_SIGNAGE_NOT_VERIFIED
- REFERRED_MINOR_SALE_UNRESOLVED / minor_sale
- SECURITY_CCTV_CONTROL_FAILURE / missing_camera_coverage / footage_not_produced
- BOARD_ORDER_CONFLICT
- TAX_HOLD_REOPENED / open_tax_hold_uncleared
- noise_or_patio_breach / patio_boundary_failure
- food_service_not_available
- id_check_failure

#### Ordering
- All code arrays: ascending lexical order (or "any order" if the template allows it — check the template's ordering field).
- `first_90_day_plan`: check template ordering instruction (ascending by check_code vs. operational sequence).

## Archetype 3: Alcohol Renewal Manual Review Queue

### When to use
The prompt names a set of alcohol license numbers and a boundary date, asking for a ranked manual-review queue.

### Data endpoints
- GET `/api/alcohol/licensees`
- GET `/api/alcohol/violations`
- GET `/api/renewal/rules`
- POST `/api/sql`

### Decision rules

#### Violation matching
1. Load all violations for the target licensees.
2. **Exclude** any violations dated on or after the boundary date — these are `post_boundary_violation_ids_excluded`.
3. **Match** remaining violations to licensees by license number or by close address match.

#### Match confidence
- **exact**: violation record's license_no matches the target license number directly.
- **close_address**: violation record matches by address but the license_no differs (e.g., an old/different license at the same premises).
- **uncertain**: weak address match — possible but not confirmed.

#### Ranking formula
Rank by composite risk score (higher risk → lower rank number = higher priority). Score factors:
1. **Violation count** (more violations → higher risk).
2. **Most recent violation date** (more recent → higher risk, weighting recency).
3. **Violation severity** — check `/api/renewal/rules` for severity classifications.
4. **Match confidence** — exact > close_address > uncertain; exact matches with many violations rank higher.

Priority ordering heuristic: sort by (violation_count DESC, most_recent_violation_date DESC, match_confidence best-first), then assign rank 1 through N.

#### Risk tier
- **high**: ≥2 violations with at least one serious, or ≥3 total violations, or flagged in renewal rules as high-risk category.
- **medium**: 1–2 violations, none serious.
- **low**: 0 violations (rare in a review queue).

#### Next step label
- **board_review**: high-risk with serious violations or close/uncertain match requiring board adjudication.
- **manual_fine_check**: high or medium risk, violations suggest outstanding fines.
- **manual_ALERT_check**: lower-risk items needing verification of ALERT system flags.
- **additional_record_check**: uncertain matches needing further investigation.

#### Summary fields
- `queue_size`: number of entries (matches the target queue size from the prompt).
- `boundary_date`: as given in the prompt.
- `post_boundary_violation_ids_excluded`: all violation IDs with date ≥ boundary date, sorted ascending by ID.
- `close_or_uncertain_match_license_numbers`: license numbers with non-"exact" match confidence, sorted ascending.
- `board_review_license_numbers`: license numbers where next_step is board_review, sorted ascending.

#### Ordering
- Queue entries: ascending by rank (1 through N).
- `matched_violation_ids` per entry: sort by violation date ascending, then violation_id ascending.
- All summary lists: ascending by the relevant ID.

## Cross-cutting Rules

### Policy baseline check
Always fetch `/api/policies` first. Compare current policy requirements against prior baseline. If a 2025 policy change tightens a standard (higher bond minimum, new endorsement requirement, stricter insurance threshold), and that tighter standard creates a deficiency that wouldn't have existed before, mark `policy_impacted: true` for that application.

### Correspondence staleness
For contractor tasks, scan `/api/contractor/correspondence` for records where:
- Status is not "closed", "resolved", or "verified".
- The expected response date has passed without a reply, or the record is flagged stale/unverified.
- Include the correspondence IDs in `stale_or_unverified_correspondence_ids`.

### SQL endpoint usage
When cross-referencing across endpoints is complex (e.g., matching violations to licenses by address), use POST `/api/sql` with the auth header from `environment_access.md`. Pass the SQL query in the request body. This is especially useful for renewal queue tasks.

### Output discipline
- Return **only** the JSON object matching the answer template.
- No prose, no markdown, no comments, no keys not in the template.
- Use empty arrays (`[]`) when no codes apply.
- Ensure all enum values used are in the template's allowed_values list for that field.
- Verify list ordering matches the template's ordering instruction before finalizing.
