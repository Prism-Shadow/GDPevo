 # Licensing Review Skill

 ## Purpose

 Provide structured decision support for state licensing reviews across three domains:
 contractor batch eligibility, restricted liquor-license staff packages, and alcohol
 renewal queues.  Use the shared licensing REST + SQL environment to gather evidence,
 cross-reference records, apply policy-driven deficiency and risk rules, and produce
 JSON-only answers that match supplied answer templates.

 ## Environment

 The licensing data service is reachable at `<TASK_ENV_BASE_URL>`.  Every request that
 writes or queries (including `POST /api/sql`) MUST include the header
 `X-Task-Token: licensing-review-019`.  Omit this header and the service returns 401.

 ### Endpoint inventory

 #### GET endpoints (read-only)

 | Endpoint                        | Domain        | Returns                                      |
 |---------------------------------|---------------|----------------------------------------------|
 | `/api/policies`                 | shared        | Active policy rules and effective dates.      |
 | `/api/contractor/applications`  | contractor    | Application details, endorsements, experience.|
 | `/api/contractor/bonds`         | contractor    | Bond records (amount, status, dates).         |
 | `/api/contractor/insurance`     | contractor    | Insurance policies (coverage, expiry).        |
 | `/api/contractor/license-history`| contractor   | Past licenses, suspensions, revocations.      |
 | `/api/contractor/violations`    | contractor    | Open and closed violation/complaint records.  |
 | `/api/contractor/correspondence`| contractor    | Letters, notices, verifications sent/received.|
 | `/api/contractor/inspections`   | contractor    | Inspection reports, outcomes, recheck flags.  |
 | `/api/liquor/applications`      | liquor        | Liquor license applications and status.       |
 | `/api/liquor/settlements`       | liquor        | Settlements, consent orders, tax holds.       |
 | `/api/liquor/privileges`        | liquor        | Operating privileges, hours, patio, delivery. |
 | `/api/liquor/incidents`         | liquor        | Police/incident reports tied to premises.     |
 | `/api/liquor/site-evidence`     | liquor        | Site photos, floor plans, camera diagrams.    |
 | `/api/alcohol/licensees`        | alcohol       | Alcohol license records and status.           |
 | `/api/alcohol/violations`       | alcohol       | Violations with dates, codes, dispositions.   |
 | `/api/renewal/rules`            | alcohol       | Renewal eligibility rules and thresholds.     |

 #### POST `/api/sql`

 Send a JSON body with `query`, optional `params` array, and optional `limit`:

 ```json
 {"query": "SELECT ...", "params": ["..."], "limit": 100}
 ```

 Use SQL for cross-entity joins, filtered lookups, or aggregations that the GET
 endpoints cannot express directly.  Prefer parameterised queries.  The backing
 store is SQLite; all standard SQLite functions and syntax are available.

 ### Discovery pattern

 When the prompt references `<TASK_ENV_BASE_URL>`, substitute it with the actual
 base URL from `environment_access.md` before making any request.  If the prompt
 does not mention a base URL, look for one in the environment-access file shipped
 alongside the task.

 ## Review Type A: Contractor Batch Eligibility

 ### Trigger

 The prompt lists multiple `C-` application IDs and refers to contractor endpoints
 (`/api/contractor/*`).  An `answer_template.json` will define an
 `application_decisions` array and a `summary` object.

 ### Data-gathering checklist

 1. `GET /api/policies` — note effective dates and any new or changed rules.
 2. `GET /api/contractor/applications` — extract each target application; record
    requested endorsements, claimed experience years, and application status.
 3. `GET /api/contractor/bonds` — for each applicant, check bond amount (must meet
    or exceed the required minimum), bond status (active vs. cancelled), and
    effective dates.
 4. `GET /api/contractor/insurance` — for each applicant, check coverage amount
    (must meet or exceed the required minimum), policy status (active vs. expired
    vs. pending), and whether the policy is current as of the review date.
 5. `GET /api/contractor/license-history` — look for active suspensions, prior
    revocations, or disciplinary actions that would block approval.
 6. `GET /api/contractor/violations` — identify open violations, classify as minor
    or serious, and note any unresolved complaints.
 7. `GET /api/contractor/correspondence` — flag any stale (unanswered beyond a
    reasonable window) or unverified correspondence that may indicate an
    unresolved issue.
 8. `GET /api/contractor/inspections` — check for failed inspections, required
    safety rechecks, or missing documentation flags.

 ### Decision framework

 For each application, evaluate the following dimensions and assign deficiency
 codes and required actions from the answer template's allowed-value lists.

 | Dimension          | Check                                                    | Deficiency Signal                        |
 |--------------------|----------------------------------------------------------|------------------------------------------|
 | Active suspension  | License history shows a current suspension.              | `active_suspension` → `board_review_suspension` |
 | Bond amount        | Bond amount < required minimum.                          | `bond_shortfall` → `increase_bond_amount` |
 | Bond status        | Bond is cancelled, lapsed, or missing.                   | `bond_cancelled` → `obtain_current_bond` |
 | Endorsement        | Required endorsement not held and no pending application.| `endorsement_missing` → `obtain_required_endorsement` |
 | Endorsement        | Required endorsement application is pending / unverified.| `endorsement_pending` → `verify_pending_endorsement` |
 | Experience         | Documented experience < required years or evidence gap.  | `experience_shortfall` → `submit_experience_evidence` |
 | Insurance amount   | Coverage amount < required minimum.                      | `insurance_shortfall` → `increase_insurance_amount` |
 | Insurance status   | Policy is expired or not current as of review date.      | `insurance_expired` → `provide_current_insurance` |
 | Insurance status   | Policy is pending / not yet bound.                       | `insurance_pending` → `verify_insurance_binding` |
 | Inspection         | Required inspection document missing or incomplete.      | `inspection_doc_gap` → `clear_document_gap` |
 | Inspection         | Safety recheck flagged after prior failure.              | `inspection_safety_recheck` → `complete_safety_recheck` |
 | Violations         | One or more open violations, classified as minor.        | `open_minor_violation` → `resolve_minor_violation_review` |
 | Violations         | One or more open violations, classified as serious.      | `open_serious_violation` → `resolve_serious_violation` |

 #### Determination rules

 - **DENY** when: active suspension exists, OR an open serious violation is
   present, OR multiple high-severity deficiencies combine (use judgment; an
   application with a serious violation AND multiple other gaps should be denied).
 - **APPROVE** when: zero deficiency codes apply — all bonds, insurance,
   endorsements, experience, inspections, and violations are clear.
 - **HOLD** for everything else: fixable deficiencies that do not rise to the
   deny threshold.

 #### Risk tier assignment

 - **high**: active suspension, open serious violation, or ≥3 deficiency codes.
 - **medium**: 1–2 deficiency codes without suspension or serious violation.
 - **low**: zero deficiency codes (paired with APPROVE).

 #### Policy impacted flag

 Set `policy_impacted` to `true` when the current active policy (from
 `/api/policies`) introduces a standard or threshold that creates a deficiency
 which would not have applied under the prior policy baseline.  Compare the
 current policy effective date and rules against the application's filing date or
 the previous policy version.  If the same deficiency would have existed under the
 old rules, the flag is `false`.

 ### Batch summary

 The `summary` object must be internally consistent with the per-application
 decisions:

 - `approve_count` / `hold_count` / `deny_count`: count each determination.
 - `high_risk_application_ids`: every application with `risk_tier` = `high`.
 - `policy_impacted_application_ids`: every application with `policy_impacted` =
   `true`.
 - `stale_or_unverified_correspondence_ids`: correspondence record IDs from the
   correspondence endpoint that are stale (unanswered past the expected response
   window) or whose verification status is not confirmed.  Include IDs for all
   target applications that have such correspondence, sorted ascending.

 ## Review Type B: Liquor License Staff Package

 ### Trigger

 The prompt names a single `L-` application ID and a `LOC-` location, and refers
 to liquor endpoints (`/api/liquor/*`).  The answer template will define keys for
 `recommended_posture`, `covered_risk_codes`, `verification_gap_codes`,
 `standard_obligation_codes`, `location_specific_control_codes`,
 `first_90_day_plan`, and `escalation_trigger_codes`.

 ### Data-gathering checklist

 1. `GET /api/policies` — note any policy rules that affect liquor licensing.
 2. `GET /api/liquor/applications` — locate the target application; record
    license class, requested privileges, and any flags.
 3. `GET /api/liquor/settlements` — check for tax holds, consent orders, or
    unresolved settlement conditions tied to the application or location.
 4. `GET /api/liquor/privileges` — review currently active operating privileges
    (hours, patio, delivery, security requirements).
 5. `GET /api/liquor/incidents` — look for police incidents, assault reports,
    noise complaints, minor-sale referrals tied to the premises.
 6. `GET /api/liquor/site-evidence` — examine site photos, floor plans, camera
    coverage diagrams, food-service area documentation, control signage photos.

 ### Decision framework

 #### Recommended posture

 - `issue_restricted`: all major risks are covered by existing controls or
   conditions; any remaining gaps are minor and can be addressed through the
   90-day monitoring plan.
 - `request_follow_up`: one or more verification gaps exist that must be
   resolved before a final decision; the application is not ready for issuance but
   is not clearly ineligible.
 - `deny`: the application has disqualifying issues (e.g., unremediated serious
   incidents, missing mandatory evidence that cannot be reasonably obtained,
   unresolved tax holds that block processing).

 #### Same-premises basis

 `same_premises_basis_applies` is `true` when the application involves a location
 that already holds or previously held a license, and the current review relies on
 that prior history for risk assessment or control continuity.  If the application
 is for a new, never-licensed premises, or the prior license history is not
 materially relevant, it is `false`.

 #### Covered risk codes

 Identify which risk categories are addressed by existing controls, conditions,
 or evidence already on file.  A risk is "covered" when there is a specific,
 verifiable control (CCTV, security plan, operating-hour restriction, signed
 settlement condition, etc.) that mitigates it.  Choose from the template's
 allowed values (which may include `NOISE`, `AFTER_HOURS`, `ASSAULT`,
 `MINOR_SALE`, `SAME_PREMISES`, `SALE_TO_MINOR`, `TAX_HOLD`,
 `FOOD_SERVICE_GAP`, `PUBLIC_SAFETY`, `PATIO_BOUNDARY`, `CAMERA_COVERAGE`,
 `ID_CHECK`, and similar codes).

 #### Verification gap codes

 Identify what evidence or confirmation is still missing.  Common gaps include:
 - Missing camera footage exports or camera-coverage diagrams.
 - Missing food-service area photographs or service documentation.
 - Conflicting or outdated floor plans.
 - Late-night monitoring plan not submitted.
 - Unresolved tax hold.
 - Missing, expired, or conflicting control signage.
 - Police memo with identity discrepancies or conflicting information.
 - Missing neighbour-notice documentation.
 - Missing site photographs.

 #### Standard obligations vs. location-specific controls

 `standard_obligation_codes` are requirements that apply to ALL licenses of this
 class regardless of location — typical obligations: `ID_CHECK`, `HOURS`,
 `FOOD_SERVICE`, `SECURITY`, `CCTV`, `PATIO`, `NOISE`, `DELIVERY`.  Include only
 those that are ordinary required obligations for the license class in question.

 `location_specific_control_codes` are active controls tied to THIS specific
 location, beyond the standard class obligations.  These may overlap with standard
 obligations in code values but are listed separately because they are
 location-driven rather than class-driven.

 #### First-90-day plan

 Build an ordered list of monitoring checks, each with a `check_code` and
 `timing`.  Sequence them operationally: start with foundational checks (signage
 review, ID-check observation) in the first 30 days, escalate to after-hours and
 high-risk checks in days 31–60, and reserve days 61–90 for boundary/noise checks
 that require a pattern of operation to evaluate.

 Typical check codes include:
 - `camera_export_test` / `security_cctv_walkthrough`
 - `food_service_service_area_check`
 - `late_night_closing_visit` / `after_hours_visit`
 - `noise_patio_boundary_check`
 - `id_check_observation`
 - `control_signage_review` / `control_signage_recheck`
 - `tax_clearance_review`
 - `incident_log_review`
 - `police_memo_follow_up`

 Timing buckets: `first_30_days`, `days_31_60`, `days_61_90`.

 #### Escalation trigger codes

 List conditions that, if observed during monitoring, should cause an immediate
 escalation to a supervisor or enforcement unit.  Derive these from the uncovered
 risks and verification gaps.  Common triggers:
 - `after_hours_service` / `AFTER_HOURS_VIOLATION`
 - `missing_camera_coverage` / `footage_not_produced`
 - `food_service_not_available`
 - `noise_or_patio_breach` / `patio_boundary_failure`
 - `open_tax_hold_uncleared`
 - `unreported_violent_incident` / `MAJOR_INCIDENT_REPORTED`
 - `minor_sale` / `REFERRED_MINOR_SALE_UNRESOLVED`
 - `id_check_failure`
 - `CONTROL_SIGNAGE_NOT_VERIFIED`
 - `SECURITY_CCTV_CONTROL_FAILURE`

 ## Review Type C: Alcohol Renewal Queue

 ### Trigger

 The prompt lists multiple `AL-` license numbers and a release boundary date,
 and refers to `/api/alcohol/*` and `/api/renewal/rules`.  The answer template
 defines a ranked `queue` array and a `summary`.

 ### Data-gathering checklist

 1. `GET /api/alcohol/licensees` — extract the target licensees.
 2. `GET /api/alcohol/violations` — collect all violations for the target
    licensees.
 3. `GET /api/renewal/rules` — read the renewal eligibility criteria, risk
    thresholds, and any scoring rules.

 ### Queue construction

 #### Step 1: Filter by release boundary

 Exclude any violation whose date is ON or AFTER the release boundary date.
 These are "post-boundary" violations that should not factor into the current
 renewal decision.  Track excluded violation IDs in the summary's
 `post_boundary_violation_ids_excluded` field.

 #### Step 2: Match violations to licensees

 For each target licensee, match the remaining (pre-boundary) violations.  Assign
 a `match_confidence`:
 - `exact`: violation record explicitly references the license number.
 - `close`: violation references a related entity (same owner, adjacent address)
   and the match is probable but not explicit.
 - `uncertain`: only indirect evidence ties the violation to the licensee.

 #### Step 3: Assign risk tiers

 Use the renewal rules and violation severity to assign `risk_tier`:
 - `high`: serious or repeated violations, or violations that match board-review
   criteria from `/api/renewal/rules`.
 - `medium`: non-trivial violations that require manual review but are not
   automatic board referrals.
 - `low`: no violations or only immaterial/administrative items.

 Note: licenses that require board review should also be listed in the summary's
 `board_review_license_numbers` array.

 #### Step 4: Rank the queue

 Order by descending risk (high → medium → low), then within each tier by
 descending violation count, then by most recent violation date (more recent =
 higher priority).  Assign sequential `rank` starting from 1.  Fill the queue to
 the target size specified in the prompt (e.g., 10).

 #### Step 5: Assign next-step labels

 Based on risk tier and violation pattern, assign a `next_step_label`:
 - `board_review`: automatic board referral (high risk with serious violations).
 - `manual_ALERT_check`: medium risk with flagged violations needing staff review.
 - `standard_renewal`: low risk, routine processing.
 - Use any other labels defined in the answer template's allowed values.

 #### Queue item fields

 Each queue item includes: `rank`, `license_number` (or `license_id`),
 `matched_violation_ids` (sorted ascending), `matched_violation_count`,
 `most_recent_violation_date`, `match_confidence`, `risk_tier`, `next_step_label`.

 ### Summary fields

 - `queue_size`: total items in the queue (matches target size).
 - `boundary_date`: the release boundary from the prompt.
 - `post_boundary_violation_ids_excluded`: all violation IDs filtered out in
   Step 1, sorted ascending.
 - `close_or_uncertain_match_license_numbers`: licensees with any violation
   matches that are not `exact`.
 - `board_review_license_numbers`: licensees flagged for board review.

 ## Output rules (all review types)

 1. **JSON only.**  Return a single JSON object that matches the supplied
    `answer_template.json` exactly in structure and key names.  No prose,
    markdown, code fences, comments, or extra keys.
 2. **Enum compliance.**  Every string field that has an `allowed_values` list
    must use only those values.  Do not invent new codes.
 3. **Ordering.**  Sort list items as specified in the template (usually
    ascending lexical for IDs/codes, ascending integer for ranks).
 4. **Empty arrays.**  Use `[]` (not `null` or absent) when no codes or items
    apply.
 5. **Internal consistency.**  Counts, lists, and per-item flags in the summary
    must agree with the per-application or per-item decisions.
 6. **Derivation, not fabrication.**  Every code, action, and determination must
    be traceable to specific data returned by the environment endpoints.  If the
    data does not support a code, do not include it.

 ## Workflow summary

 ```
 1. Read the prompt and answer template to identify the review type.
 2. Fetch ALL relevant GET endpoints for that review type.
 3. Use POST /api/sql for cross-entity lookups when needed.
 4. Apply the decision framework for the review type.
 5. Construct the JSON answer strictly per the template.
 6. Validate internal consistency between item-level decisions and summary.
 ```
