# Licensing Review Skill

## Purpose

Complete structured licensing review tasks by interacting with a task-environment API. This skill covers contractor eligibility batches, liquor license staff packages, and alcohol renewal queues — any task that supplies a prompt with target applications/licensees, a set of API endpoints, and an answer template.

## Operating Rules

### Phase 1 — Environment Setup

1. Locate `environment_access.md` in the working directory. It provides:
   - `base_url` — the root URL for all API calls (referenced as `<TASK_ENV_BASE_URL>` in prompts).
   - `credentials` — any required headers (e.g., `X-Task-Token`) and which endpoints require them.
   - `allowed_endpoints` — the full list of callable endpoints.

2. Resolve `<TASK_ENV_BASE_URL>` by substituting the `base_url` from `environment_access.md`.

3. Only call endpoints listed in `allowed_endpoints`. If a prompt references an endpoint not in the allowed list, do not call it — proceed with what is available.

### Phase 2 — Read the Prompt and Answer Template

1. Read the prompt (`input/prompt.txt`) for:
   - The **task type** (batch eligibility review, single-application staff package, or ranked queue).
   - The **target identifiers** (application IDs, license numbers, location codes).
   - Any **boundary dates** (review date, release date) used for currency checks and date filtering.
   - The **domain** (contractor, liquor, alcohol) which determines which endpoints to use.
   - Any **domain-specific focus areas** (e.g., hotel lounge controls, camera evidence, late-night monitoring).

2. Read the answer template (`input/payloads/answer_template.json`) for:
   - The exact top-level keys required.
   - The allowed values for every enum field — never emit a value outside these lists.
   - Ordering rules (ascending by ID, ascending lexical, by date, operational sequence).
   - Required list lengths.
   - Empty-value rules (use `[]` when no codes apply, not `null` or omission).

3. The answer template is authoritative. If the prompt and template conflict on structure, the template wins. If they conflict on which identifiers to include, the prompt wins.

### Phase 3 — Fetch All Relevant Data

1. Call every GET endpoint listed in the prompt that also appears in `allowed_endpoints`. Do not skip any — missing data produces incorrect determinations.

2. When `POST /api/sql` is available and listed in both the prompt and allowed endpoints, use it for complex cross-referencing queries that would be inefficient via individual GET calls. Include the required credential header on every POST.

3. Map endpoints to the data they provide by domain:

   **Contractor domain:**
   - `GET /api/policies` — current policy baseline; used to determine `policy_impacted`.
   - `GET /api/contractor/applications` — application records including status, experience, endorsements, and classification.
   - `GET /api/contractor/bonds` — surety bond records with amounts, status (active/cancelled), and effective dates.
   - `GET /api/contractor/insurance` — liability insurance records with coverage amounts, status, and expiration dates.
   - `GET /api/contractor/license-history` — prior licenses, suspensions, revocations, and disciplinary history.
   - `GET /api/contractor/violations` — violation records with severity (minor/serious), status (open/resolved), and dates.
   - `GET /api/contractor/correspondence` — correspondence records with verification status and dates.
   - `GET /api/contractor/inspections` — inspection reports with findings, document gaps, and safety recheck flags.

   **Liquor domain:**
   - `GET /api/policies` — current policy baseline.
   - `GET /api/liquor/applications` — license transfer applications with premises details, ownership, and class.
   - `GET /api/liquor/settlements` — tax clearance and settlement records.
   - `GET /api/liquor/privileges` — operating privileges (hours, patio, delivery, etc.).
   - `GET /api/liquor/incidents` — incident reports (assault, noise, minor sale, after-hours, public safety).
   - `GET /api/liquor/site-evidence` — site-level evidence: floor plans, control signage, photos, police memos, neighbor notices, camera evidence, food-service evidence.

   **Alcohol renewal domain:**
   - `GET /api/alcohol/licensees` — licensee records with facility name, address, license number, and status.
   - `GET /api/alcohol/violations` — violation records with dates, types, and associated license references.
   - `GET /api/renewal/rules` — renewal rules defining violation matching logic, risk tiering, and next-step routing.

### Phase 4 — Cross-Reference and Analyze

#### For Batch Eligibility Reviews (Contractor)

For each target application, cross-reference all fetched records to build a determination:

1. **Check for blocking conditions** (→ DENY):
   - Active suspension on license history.
   - Open serious violations.
   - Unresolved serious complaints.

2. **Check for resolvable deficiencies** (→ HOLD):
   - Bond: cancelled, shortfall against required amount, or missing.
   - Insurance: expired, not current relative to review date, or shortfall against required amount.
   - Endorsements: missing, pending, or not verified.
   - Experience: documented experience below required threshold.
   - Inspections: unresolved document gaps or safety recheck required.
   - Minor violations: open/unresolved.

3. **If no blocking conditions and no deficiencies** → APPROVE.

4. **Risk tier assignment:**
   - `high` — any DENY determination, or HOLD with serious violation/suspension involvement.
   - `medium` — HOLD with financial (bond/insurance) or endorsement deficiencies, or open minor violations.
   - `low` — APPROVE or HOLD with only minor documentation gaps.

5. **Policy impact determination:**
   - Compare the current policy baseline (from `/api/policies`) against what the prior baseline would have required.
   - `policy_impacted: true` when a current policy standard creates a deficiency or material review flag that would not have existed under the prior baseline.

6. **Deficiency codes and required actions:**
   - Use only codes from the answer template's allowed values.
   - Map each discovered issue to the correct deficiency code and corresponding required action. For example:
     - Cancelled bond → `bond_cancelled` / `obtain_current_bond`
     - Expired insurance → `insurance_expired` / `provide_current_insurance`
     - Missing endorsement → `endorsement_missing` / `obtain_required_endorsement`
   - Sort both lists in ascending lexical order per the template's ordering rules.

#### For Single-Application Staff Packages (Liquor)

1. **Determine recommended posture:**
   - `issue_restricted` — all controls verified, risks covered, no unresolved verification gaps that would block issuance.
   - `request_follow_up` — one or more verification gaps exist but are resolvable (missing photos, stale floor plans, pending tax clearance).
   - `deny` — critical unresolved issues: major incidents at premises, board order conflicts, unresolved tax holds, or same-premises basis has been invalidated.

2. **Same-premises basis:**
   - `true` when the current application shares premises with a previously licensed entity and that basis remains legally applicable.
   - `false` when the premises have materially changed, the prior license was revoked, or the basis has been explicitly invalidated.

3. **Covered risk codes:**
   - Identify all risks present in the application/incident history.
   - Mark a risk as "covered" when existing controls (CCTV, security, ID checks, hours restrictions, food service, patio boundaries) adequately mitigate it.
   - Include only risks that are both present AND covered. Risks that are absent or uncovered do not appear here.

4. **Verification gap codes:**
   - Any piece of required evidence that is missing, conflicting, stale, or unverified.
   - Check: site photos, floor plans, control signage, police memos, neighbor notices, tax clearance, incident follow-ups, camera evidence, food-service evidence.

5. **Standard obligations vs. location-specific controls:**
   - `standard_obligation_codes` — obligations required by regulation for this license class regardless of location.
   - `location_specific_control_codes` — controls actively tied to this specific location (may overlap with standard obligations when the location has its own enhanced requirement).

6. **First 90-day plan:**
   - Build a monitoring sequence of `{check_code, timing}` pairs.
   - Each check targets a specific risk or gap identified above.
   - Distribute across `first_30_days`, `days_31_60`, `days_61_90`.
   - Order in intended operational sequence (earliest checks first).

7. **Escalation triggers:**
   - Conditions that, if observed by field staff during monitoring, require immediate escalation.
   - Derived from the specific risks, gaps, and controls identified for this application.

#### For Ranked Renewal Queues (Alcohol)

1. **Match violations to licensees:**
   - Match by license number for `exact` confidence.
   - Match by facility name + address similarity for `close_address` confidence.
   - Match by partial identifiers for `uncertain` confidence.

2. **Apply the boundary date:**
   - Only violations on or before the boundary date count for the queue.
   - Violations after the boundary date go into `post_boundary_violation_ids_excluded` in the summary.
   - `most_recent_violation_date` is the latest matched violation date on or before the boundary.

3. **Rank licensees:**
   - Primary sort: violation count (descending — more violations = higher priority).
   - Secondary sort: most recent violation date (ascending — older most-recent = higher priority, because the licensee has gone longer without a fresh violation).
   - Tertiary sort: license number ascending (stable tiebreaker).
   - Assign ranks 1 through N with no gaps.

4. **Match confidence:**
   - `exact` — matched by stable license identifier.
   - `close_address` — matched by facility name and address when license number differs.
   - `uncertain` — matched by partial data; needs manual verification.

5. **Risk tier:**
   - `high` — serious violations, or violation count in the top third of the queue.
   - `medium` — moderate violation history.
   - `low` — minimal or no violations.

6. **Next-step label:**
   - `board_review` — serious violations or high-risk patterns requiring board attention.
   - `manual_ALERT_check` — close/uncertain matches needing identity verification.
   - `manual_fine_check` — violations that may carry fines requiring manual calculation.
   - `additional_record_check` — gaps or inconsistencies needing further record pull.

### Phase 5 — Produce Output

1. Build the JSON object with **exactly** the keys specified in the answer template — no extra keys.

2. Follow all ordering rules:
   - Application/license IDs: ascending lexical order.
   - Deficiency/action/risk/gap/trigger codes: sort ascending by code string.
   - Violation IDs in queues: sort by violation date ascending, then violation ID ascending.
   - Queue entries: ascending by rank.
   - 90-day plan items: intended operational sequence.
   - Summary ID lists: ascending lexical order.

3. Use empty arrays (`[]`) when no codes or IDs apply — never `null`, never omit the key.

4. Ensure counts in the summary are consistent with the per-item decisions:
   - `approve_count` + `hold_count` + `deny_count` must equal the total number of applications.
   - `high_risk_application_ids` must include every application with `risk_tier: "high"`.
   - `policy_impacted_application_ids` must include every application with `policy_impacted: true`.
   - `queue_size` must equal the number of queue entries.

5. Make the summary mutually consistent with the detail — if a count or list in the summary contradicts the per-item data, the output is invalid.

6. Return **only** the JSON object. No markdown fences, no prose, no citations, no comments.

### Guardrails

- Never invent codes not in the template's allowed values.
- Never emit a determination not in the template's allowed values.
- When a record is missing (e.g., no bond record found for an application), that itself is a deficiency — map it to the appropriate code.
- When the review date is specified in the prompt, use it to judge currency (is the bond active on that date? is the insurance policy in force on that date?).
- When no review date is specified, use the current date.
- Dates in output must use `YYYY-MM-DD` format.
- If API data appears contradictory, surface the contradiction via the appropriate deficiency or verification gap code rather than silently picking one interpretation.
