---
name: licensing-review
description: Complete structured licensing review tasks for contractor, liquor, and alcohol renewal domains. Use this skill whenever a prompt mentions licensing review, contractor applications, liquor license transfer, alcohol renewal queue, licensing board, eligibility batch, staff package, manual review queue, renewal screen, or asks you to call licensing environment APIs ending in /api/policies, /api/contractor/, /api/liquor/, /api/alcohol/, or /api/renewal/. Trigger on any task that references a TASK_ENV_BASE_URL with licensing endpoints and an answer_template.json payload.
---

# Licensing Review

You are an expert licensing examiner working inside a restricted task environment. Every task follows the same core pattern: read the prompt, fetch all relevant domain data from REST and SQL endpoints, cross-reference that data against policy rules, and produce a strictly conformant JSON answer matching an answer-template schema.

## Core Workflow

Always follow this sequence. Never skip a step.

### Step 1 — Orient

Read the prompt fully and extract:

- **Target applications/licenses** — a list or single identifier.
- **Task family** — contractor batch, liquor staff package, or alcohol renewal queue. The endpoints listed in the prompt tell you which family it is.
- **TASK_ENV_BASE_URL** — The base URL for the licensing environment. The prompt uses `<TASK_ENV_BASE_URL>` as a placeholder; read the actual value from `environment_access.md` if the prompt does not spell it out.
- **Review date or boundary date** — If the prompt gives a specific date, record it. For contractor tasks it is the review date for financial-coverage currency. For renewal tasks it is the boundary date for violation inclusion.
- **Answer template path** — Always `input/payloads/answer_template.json`.

### Step 2 — Read the Answer Template

Read `input/payloads/answer_template.json` first. This template is the contract — it defines every required key, the allowed enum values, ordering rules, and what empty values look like. Internalize it before you make any data calls so you know what you are building toward.

### Step 3 — Fetch Policies

Call `GET {base}/api/policies`. Parse the response. Every policy object has a `details_json` field containing rule parameters as a JSON string. Parse `details_json` with a real JSON parser (not substring matching).

Key policy fields across domains:

| Field | Meaning |
|-------|---------|
| `minimum_bond` | Required bond amount in dollars |
| `minimum_insurance` | Required insurance coverage in dollars |
| `minimum_years_experience` | Required years of experience |
| `required_endorsement` | Required endorsement code, or `null` when none is required |
| `serious_open_violation_blocks` | Whether an open serious violation blocks approval |
| `current_site_evidence_required` | Whether current site evidence is mandatory (liquor) |
| `same_premises_history_matters` | Whether same-premises history is relevant (liquor) |

The policy whose `rule_code` mentions "LEGACY" or whose `details_json` contains `use_for_prior_rule_comparison: true` is the prior baseline. A current 2025 policy whose requirements differ from the legacy baseline creates a **policy impact**: a deficiency or flag that would not have existed under the old rules. Mark `policy_impacted: true` for any application where at least one deficiency is driven by a new-or-tighter requirement not present in the baseline.

### Step 4 — Fetch Domain Data

Call every GET endpoint listed in the prompt. Do not skip any — you will miss critical cross-references.

**Contractor batch endpoints:**
- `GET {base}/api/contractor/applications` — target applicant records
- `GET {base}/api/contractor/bonds` — bond certificates
- `GET {base}/api/contractor/insurance` — insurance certificates
- `GET {base}/api/contractor/license-history` — prior license records, suspensions
- `GET {base}/api/contractor/violations` — open/closed violation records
- `GET {base}/api/contractor/correspondence` — correspondence logs
- `GET {base}/api/contractor/inspections` — inspection records

**Liquor staff-package endpoints:**
- `GET {base}/api/liquor/applications` — application record
- `GET {base}/api/liquor/settlements` — settlement/board-order records
- `GET {base}/api/liquor/privileges` — license privilege records
- `GET {base}/api/liquor/incidents` — incident reports
- `GET {base}/api/liquor/site-evidence` — site evidence records

**Alcohol renewal endpoints:**
- `GET {base}/api/alcohol/licensees` — licensee records
- `GET {base}/api/alcohol/violations` — violation records
- `GET {base}/api/renewal/rules` — renewal rule records

### Step 5 — Narrow with SQL (Always)

REST endpoints return a broad resultset. Use `POST {base}/api/sql` to narrow to your exact targets. This is critical for accuracy and efficiency.

**SQL auth:** Every POST to `/api/sql` requires the header `X-Task-Token: licensing-review-019`. Send it as a standard HTTP header, not in the request body.

**SQL endpoint mechanics:** The endpoint accepts a JSON body with a `query` field containing a SELECT statement. It returns an array of row objects. Use it to:
- Filter applications by the target ID list: `SELECT * FROM contractor_applications WHERE application_id IN ('C-...', ...)`
- Match bonds/insurance/violations to target applications by their ID prefixes
- Look up correspondence by ID pattern
- Join across tables when the endpoint supports it

Always write a focused query that returns only the rows you need. Use `IN (...)` with explicit IDs, never `SELECT *` without a WHERE clause if the table is large.

The exact table names and column names are discoverable from the REST responses. Use the field names from the REST JSON objects as your column names in SQL. If a REST endpoint returns objects with keys like `application_id`, `bond_amount`, `status`, those are your SQL column names.

### Step 6 — Cross-Reference and Decide

For each target application or license, assemble a complete picture by joining data across endpoints.

**Contractor decisions:**

For each target application, check:

1. **Bond status:** Does the applicant have an active bond? Is the bond amount ≥ the policy minimum for their trade/class? Map gaps to deficiency codes like `bond_cancelled` / `bond_shortfall` / `no_active_bond` (use the exact codes from the answer template).
2. **Insurance status:** Is insurance current as of the review date? Does coverage meet the policy minimum? Map gaps to `insurance_expired` / `insurance_not_current` / `insurance_shortfall`.
3. **Endorsement status:** Is the required endorsement verified? If the policy requires one and status is `missing` or `pending`, flag it. Use `endorsement_missing` / `endorsement_not_verified` / `endorsement_pending` per the template.
4. **Experience:** Does `years_experience` ≥ the policy minimum? Flag `experience_shortfall`.
5. **License history:** Any `active` suspension? Flag `active_suspension`. This blocks approval.
6. **Violations:** Any open serious violations? Flag per template codes. Open minor violations map to hold, serious to deny.
7. **Inspections:** Any unresolved safety rechecks or document gaps? Flag accordingly.
8. **Correspondence:** Any unverified or stale correspondence records? Collect their IDs for the summary.

**Determination logic:**
- **DENY** — active suspension, open serious violation, or multiple severe unresolved deficiencies where resolution is outside the applicant's immediate control.
- **APPROVE** — no deficiencies, all checks pass.
- **HOLD** — deficiencies exist but are resolvable (expired documents, shortfalls, missing endorsements, pending verifications).

**Risk tier:**
- **high** — any deny-level flag, or 2+ medium-severity deficiencies.
- **medium** — one or two resolvable deficiencies, no deny-level flags.
- **low** — no deficiencies.

**Liquor staff-package decisions:**

For the target application + location:

1. **Same-premises basis:** Check the application and site evidence for same-premises history. If the location has prior license records under the same or related entity, `same_premises_basis_applies` is `true`.
2. **Covered risks:** From settlements, privileges, and incidents, identify which risks are covered by existing controls (e.g., AFTER_HOURS, ASSAULT, MINOR_SALE, NOISE, etc.). Use only codes from the template's allowed values.
3. **Verification gaps:** From site evidence and incident records, identify gaps: missing photos, conflicting floor plans, stale control signage, open incident follow-ups, conflicting police memos, missing tax clearance. Use only template codes.
4. **Standard obligations:** Identify obligations that apply to this license class by default (ID_CHECK, HOURS, FOOD_SERVICE, etc.).
5. **Location-specific controls:** Identify controls currently active at this specific location (CCTV, SECURITY, NOISE, PATIO, etc.).
6. **First-90-day plan:** Propose monitoring checks with timing (first_30_days, days_31_60, days_61_90). Each check should address a specific verification gap or risk. Use only check_code/timing pairs from the template.
7. **Escalation triggers:** Define conditions that would prompt staff escalation (e.g., AFTER_HOURS_VIOLATION, CONTROL_SIGNAGE_NOT_VERIFIED). Use only template codes.

**Recommended posture:**
- `issue_restricted` — risks are covered by controls, gaps are resolvable.
- `request_follow_up` — significant verification gaps need resolution before issuance.
- `deny` — unresolved serious incidents, tax holds, or material misrepresentations.

**Alcohol renewal queue:**

1. **Find the active renewal rule:** Match the boundary date from the prompt to `release_boundary` in a renewal rule. If the prompt lists a boundary date, use the rule matching it. The rule's `details_json` tells you: violations on or before the boundary date are included; late violations are excluded.
2. **Fetch licensees:** Get the target licensees.
3. **Fetch violations:** Get all violations and match them to licensees. A violation matches a licensee when its `license_no` field equals the licensee's ID, or when a close-address match is detected (same facility name pattern, similar address, but different license ID).
4. **Exclude post-boundary violations:** Violations with dates after the boundary are excluded from the queue ranking but recorded under `post_boundary_violation_ids_excluded`.
5. **Rank licensees:** Within the target queue size, rank by:
   - Primary: violation count (more violations = higher rank).
   - Secondary: most recent violation date (more recent = higher rank).
   - Tiebreaker: license ID ascending.
6. **Match confidence:**
   - `exact` — violation `license_no` exactly matches a target license.
   - `close_address` — address/facility-name match but different license ID.
   - `uncertain` — weaker signal, partial match only.
7. **Risk tier:** `high` for any match involving close_address, board-review flags, or alert flags. `medium` for lower-confidence matches with fewer violations.
8. **Next step:** `board_review` for high-risk or close-address matches. `manual_fine_check` for high violation counts with exact matches. `manual_ALERT_check` for alert-flagged licensees. `additional_record_check` for uncertain matches.

### Step 7 — Build the Output JSON

Produce exactly one JSON object matching the answer template.

**Mandatory rules:**
- Use only keys listed in the template. Do not add explanatory keys, prose, or commentary.
- Enum values must come from the template's `allowed_values` lists exactly — same case, same spelling, same underscores.
- Empty arrays (`[]`) when no codes apply. Never use `null`, `"none"`, or omit the key.
- Sort list items as the template specifies: ascending by ID, by date-then-ID, or lexically/alphabetically by code.
- Summary counts must be integers, not strings.
- Booleans must be `true`/`false`, not `"true"`/`"false"`.
- Dates must be YYYY-MM-DD strings.

**Confidence in decisions:** Your determinations must be traceable to specific API records. When a deficiency exists, you must be able to point to the bond/insurance/violation/inspection record that caused it. When a risk is covered, you must be able to name the settlement or privilege that covers it. Never guess — if data is missing or ambiguous, the conservative decision is HOLD (contractor) or `request_follow_up` (liquor).

### Step 8 — Self-Check Before Output

Before finalizing the JSON:

1. Is every application/license from the prompt present?
2. Are the items ordered as the template requires?
3. Are all enum values from the template's allowed lists?
4. Do summary counts add up?
5. Are empty fields empty arrays where the template says so?
6. Are dates in YYYY-MM-DD?
7. Is the output pure JSON with no markdown fences or surrounding text unless the prompt specifically asks for a wrapped format?

## Task-Family Quick Reference

### Contractor Batch (first contractor batch pattern)

Targets are `C-...` IDs. Endpoints: policies, contractor/applications, contractor/bonds, contractor/insurance, contractor/license-history, contractor/violations, contractor/correspondence, contractor/inspections. Output: `application_decisions` array + `summary` object.

**How policies drive decisions:** Each application's trade determines which policy rule applies. Find the policy matching the trade. Compare its `details_json` requirements (minimum_bond, minimum_insurance, minimum_years_experience, required_endorsement) against the application's actual bond/insurance/experience/endorsement records. A gap is a deficiency.

**Policy impact detection:** If a deficiency exists under the current policy but would not exist under the legacy baseline, mark `policy_impacted: true`. Example: a new endorsement requirement in 2025 that did not exist in the 2024 legacy rule.

**Correspondence for summary:** Any correspondence record where `status` is not `verified` or the record is stale counts toward `stale_or_unverified_correspondence_ids`.

### Liquor Staff Package (first liquor staff-package pattern)

Targets are `L-...` application ID and `LOC-...` location. Endpoints: policies, liquor/applications, liquor/settlements, liquor/privileges, liquor/incidents, liquor/site-evidence. Output: single application-level object with posture, risk codes, gap codes, obligations, controls, plan, and escalation triggers.

**How policies drive decisions:** Liquor policies define whether site evidence is required, whether same-premises history matters, and what settlement/privilege standards apply. The policy's `details_json` drives the `same_premises_basis_applies` and `covered_risk_codes` fields.

**Risk code mapping:** Incidents map to risk codes. Settlements that reference specific risks count as "covered." Incident records without matching settlements or controls are verification gaps.

**Hotel lounge specifics (hotel-lounge variant):** When the venue is a hotel lounge, pay extra attention to camera coverage, food-service evidence, and late-night monitoring. These are recurring verification-gap themes for hotel-lounge applications.

### Alcohol Renewal Queue (first alcohol renewal queue pattern)

Targets are `AL-...` license IDs. Endpoints: alcohol/licensees, alcohol/violations, renewal/rules. Output: `queue` array (ranked, exactly queue-size entries) + `summary` object.

**Rule selection:** The prompt's boundary date selects the renewal rule. If the prompt says "release boundary is YYYY-MM-DD", find the rule with `release_boundary: "YYYY-MM-DD"`. The rule's `details_json` field `use_violations_on_or_before` confirms the cutoff.

**Violation matching:** Match each violation to a licensee by `license_no`. Violations whose `license_no` exactly equals a target license ID are `exact` matches. Violations where the facility name or address closely resembles a target licensee but the license ID differs are `close_address` matches.

**Post-boundary exclusion:** Violations dated after the boundary date are excluded from the queue ranking and collected under `post_boundary_violation_ids_excluded`. This is how the answer template's `summary.post_boundary_violation_ids_excluded` field gets populated. Late violations (those after the boundary) do not affect rank, violation count, or most-recent date — they are recorded only in the exclusion list.

**Queue ordering:** Sort included licensees by violation count descending, then most-recent violation date descending, then license ID ascending. Take the top N where N is the target queue size. Assign ranks 1..N.

**Close/uncertain matches in summary:** Track license numbers that have at least one close_address or uncertain match in `close_or_uncertain_match_license_numbers`. Track license numbers whose `next_step_label` is `board_review` in `board_review_license_numbers`.

## Common Mistakes to Avoid

- **Not using SQL to narrow results.** REST endpoints return all records. Always use SQL to filter to your exact targets.
- **Forgetting the X-Task-Token header on POST /api/sql.** Every SQL call needs it. The token is `licensing-review-019`.
- **String-matching policy details_json instead of parsing it.** Use `JSON.parse` or equivalent. Policy values like `minimum_bond: NNNNN` must be treated as numbers for comparison, not strings.
- **Copying deficiency/action codes from one template into another task family.** The allowed enum values differ between templates — always read the current task's template.
- **Using null or omitting keys for empty fields.** Templates consistently require `[]` for empty arrays.
- **Wrong sort order.** Templates specify ordering precisely — follow it.
- **Missing post-boundary exclusion list in renewal queues.** Every target license typically has one late violation; collect them all.
- **Not distinguishing exact vs close_address matches.** The summary fields `close_or_uncertain_match_license_numbers` and `board_review_license_numbers` depend on getting this right.
- **Confusing standard obligations with location-specific controls.** Standard obligations apply to the license class; location-specific controls are currently active at the specific location. A CCTV system at the location is a location-specific control. An ID-check requirement that applies to all liquor licenses of this class is a standard obligation. Some codes appear in both lists — that is fine when the obligation is both standard and location-active.

## References

- [API Reference](references/api_reference.md) — Endpoint descriptions, common field names, and SQL table mapping.
- [Schema Patterns](references/schema_patterns.md) — How to read answer templates, enum matching, and output construction patterns.
