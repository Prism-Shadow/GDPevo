 # Licensing Review Skill

 Solve structured licensing-examination tasks using a shared environment that exposes REST and SQL endpoints. Every task supplies a prompt describing the target entities, the relevant GET endpoints, and an `answer_template.json` schema. Use the environment to retrieve business records, interpret policies, and return a JSON answer that strictly conforms to the template.

 ## Environment

 - **Base URL** is provided in the prompt as `<TASK_ENV_BASE_URL>`.
 - **GET endpoints** return full lists; filter in your code or use the SQL endpoint for targeted queries.
 - **POST `/api/sql`** accepts `{"query": "<SELECT>", "params": ["<value>"], "limit": <int>}` with header `X-Task-Token: licensing-review-019`. Prefer parameterised queries with `?` placeholders. Only `SELECT` is allowed.
 - **`/api/policies`** applies to all task families (contractor, liquor, renewal). Always fetch it first.

 ## General Workflow

 1. **Read the prompt and answer template.** Identify the task family and the set of target entity IDs.
 2. **Fetch `/api/policies`.** Map each policy to a trade, license class, or rule using `rule_code`, `family`, or `details_json` fields.
 3. **Retrieve entity records** via the listed GET endpoints or the SQL endpoint. Use targeted SQL queries when available to avoid sifting through large responses.
 4. **Collect related records** by joining on identifiers:
    - Contractor tasks: bonds, insurance, license history (via `prior_license_id`), violations (via `related_application_id` and `license_id`), correspondence, inspections.
    - Liquor tasks: settlements (by `location_id`), privileges (by `license_class`), incidents, site evidence.
    - Renewal tasks: licensees, violations (by `license_no`), renewal rules.
 5. **Evaluate each entity against its applicable policy.** Derive determinations, deficiency codes, required actions, risk tiers, and policy-impact flags.
 6. **Build the JSON answer** matching the template exactly. Sort arrays as directed. Use empty arrays when no codes apply. Align summary counts with individual decisions.

 ## Policy Interpretation

 - Parse `details_json` inside each policy row to extract thresholds (`minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`, and blocking rules such as `serious_open_violation_blocks`).
 - The `CON-LEGACY` policy (`POL-CON-LEGACY`) defines a prior baseline. Compare current policy requirements against the legacy baseline to determine `policy_impacted`: true when a 2025-policy standard creates a deficiency or flag that would not apply under the prior baseline.
   - Legacy `minimum_bond_reduction` subtracts from the current policy minimum.
   - `endorsement_required_for_specialty: false` means Specialty trades had no endorsement requirement under legacy.

 ## Contractor Batch Review

 - Map each application's `trade` to a policy: Plumbing→CON-PLU-ClassB, HVAC→CON-HVA-ClassB, General Building→CON-GEN-ClassA, Roofing→CON-ROO-Limited, Solar→CON-SOL-Specialty, Electrical→CON-ELE-ClassA.
 - Match bonds and insurance by `application_id`. Prefer the record with `status = 'active'`; use the most recent when multiple active records exist.
 - Determine currency of financial coverage against the review date if one is specified; otherwise use the status field and expiration date.
 - **Bond checks:** `no_active_bond` when no active bond exists, `bond_shortfall` when active bond amount < policy minimum, `bond_cancelled` when the active bond was cancelled.
 - **Insurance checks:** `insurance_not_current` when status is not active, `insurance_expired` when expiration date is past the review date, `insurance_shortfall` when amount < policy minimum.
 - **Endorsement:** `endorsement_not_verified` when status is `missing` or `pending` and the policy requires one. `not_required` means no endorsement issue.
 - **Experience:** `experience_shortfall` when `years_experience` < `minimum_years_experience`.
 - **License history:** Check `prior_license_id` in the `contractor_license_history` table. A status of `suspended` maps to `active_suspension`.
 - **Violations:** Look for open violations with severity `serious` that are not resolved/dismissed. These trigger `unresolved_serious_complaint` and may force a DENY determination when the policy sets `serious_open_violation_blocks: true`. Open minor violations are flagged separately.
 - **Inspections:** `DOC_GAP`, `SAFETY_RECHECK`, and `UNVERIFIED_SITE` findings may influence risk assessment even if not represented as explicit deficiency codes.
 - **Correspondence:** Records with `verified_by_agency = 0` or notes indicating stale/unverified content should be collected for the `stale_or_unverified_correspondence_ids` summary field.
 - **Determination logic:**
   - `DENY` when there is an active suspension, an open serious violation (and the policy blocks on it), or an otherwise unfixable condition.
   - `HOLD` when deficiencies are present but correctable.
   - `APPROVE` when no deficiencies exist.
 - **Risk tier:** `high` when multiple serious deficiencies, active suspension, or open serious violations exist. `medium` for a few correctable issues. `low` when clean or nearly clean.

 ## Liquor License Staff Package

 - Match the target `application_id` to its `location_id` from the applications endpoint.
 - Query settlements, incidents, and site evidence by `location_id`.
 - Query standard obligations by `license_class` from the privileges endpoint; `standard_required = 1` codes become `standard_obligation_codes`.
 - **Active settlement:** The settlement with `controls_json.active = true` (check by parsing the JSON string). Its `controls` array becomes `location_specific_control_codes`. The `basis_code` indicates the risk basis; a `SAME_PREMISES` basis means `same_premises_basis_applies = true`.
 - **Covered risks:** Map active settlement controls to the risk codes they mitigate. Security controls cover ASSAULT/PUBLIC_SAFETY, CCTV covers AFTER_HOURS, HOURS covers AFTER_HOURS, NOISE covers NOISE, PATIO covers PATIO_BOUNDARY, ID_CHECK covers MINOR_SALE, FOOD_SERVICE covers FOOD_SERVICE_GAP.
 - **Verification gaps:** Examine site evidence and incident statuses. Missing/conflicting evidence yields codes like `camera_evidence_missing`, `food_service_evidence_missing`, `floor_plan_conflicting`, `control_signage_missing`, `police_memo_identity_note`. Open incidents yield `tax_hold_unresolved` or `OPEN_INCIDENT_FOLLOW_UP` (code set varies per template).
 - **First-90-day plan:** Derive check codes from the identified gaps and risk areas. Assign timing based on urgency: critical gaps in `first_30_days`, monitoring checks in `days_31_60`, ongoing verification in `days_61_90`.
 - **Escalation triggers:** Derived from open risks and evidence gaps. Include codes for missing coverage, unresolved holds, open incidents, and known violation patterns at the location.
 - **Posture:**
   - `issue_restricted` when controls and evidence are adequate with monitoring.
   - `request_follow_up` when gaps or open incidents need resolution before issuance.
   - `deny` when unfixable conditions or major unresolved risks exist.

 ## Alcohol Renewal Queue

 - Identify the applicable `renewal_rules` row by matching the `release_boundary` from the prompt.
 - **Boundary filtering:** Only count violations with `violation_date` on or before the boundary date.
 - **Distractor exclusion:** Exclude violations where `source_name = 'post_boundary_feed'` (these are `late_rows_are_distractors`).
 - **Successor handling:** When a licensee has `successor_to` populated, check for violations under the predecessor `license_no`. Mark `match_confidence` as `"uncertain"` for successor relationships per `successor_match_mark_uncertain`.
 - **Sorting violations:** Within each queue entry, sort `matched_violation_ids` by `violation_date` ascending, then `violation_id` ascending.
 - **Ranking:** Prioritize by severity and recency of open violations, unpaid fine amounts, and alert flags. Rules typically set `alert_flag_requires_manual_review: true` and `unpaid_fines_require_hold: true`.
 - **Next-step labels:** `manual_fine_check` for unpaid fines, `manual_ALERT_check` for alert-flagged violations, `board_review` for serious open issues or successor-uncertain cases, `additional_record_check` for low-risk entries needing only a file review.
 - **Summary fields:** List all excluded post-boundary violation IDs, all licenses with `close_or_uncertain` match confidence, and all licenses flagged for board review.

 ## Cross-Cutting Rules

 - Empty arrays are valid and expected when no codes apply to a field.
 - Sort array fields as directed by the template (often ascending/lexical).
 - Dates use `YYYY-MM-DD` format.
 - Do not include prose, markdown, comments, or keys outside the template schema.
 - When a template field is an enum, use only values from the allowed list.
 - The SQL endpoint supports parameterised queries with `?` and `params` array; always use this to avoid syntax errors with `LIKE` patterns.
