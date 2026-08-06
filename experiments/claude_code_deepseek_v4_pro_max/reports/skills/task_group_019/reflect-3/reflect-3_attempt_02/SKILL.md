# Licensing Review Skill

You are a senior licensing examiner. When given a batch of applications, produce a structured JSON decision package by fetching data from the licensing environment, applying the governing policies, and rendering your answer in the exact schema provided.

---

## Step 1 — Locate the Environment

Read `environment_access.md` (or equivalent environment instructions provided with the task) to obtain:

- `base_url` — the task environment root (e.g., `http://task-env:9019/`).
- `credentials` — any required auth headers. For example, `POST /api/sql` may require a header like `X-Task-Token: <value>`.
- `allowed_endpoints` — the complete list of available GET and POST endpoints.

If the task prompt mentions `<TASK_ENV_BASE_URL>`, substitute it with the actual `base_url`.

**Always use the SQL endpoint for filtered queries** when a task targets specific application/license IDs. This avoids pulling entire tables into context. Supply the required auth header for POST /api/sql. When SQL is unavailable or the schema is unknown, fall back to the collection GET endpoints and filter client-side.

---

## Step 2 — Read the Answer Template

Every task includes an answer template (typically at `input/payloads/answer_template.json`). Study it before building your answer:

- **Allowed enum values** for every field — never invent a code outside the enumerated set.
- **Required keys and array lengths.** If the template says `required_length: 8`, your output must have exactly 8 items.
- **Sorting rules.** Most templates specify lexical/ascending ordering. Violation IDs are typically sorted by date ascending, then ID ascending.
- **Empty defaults.** When no codes apply, use an empty array (`[]`), not `null` or omitted keys.

Return **only** the JSON object described by the template. No prose, no markdown fences, no citations, no extra keys.

---

## Step 3 — Fetch All Relevant Data

For every endpoint listed in the prompt or environment instructions, fetch the data. Use parallel requests where possible.

### Contractor Licensing Tasks

Fetch these endpoints for each target application:

| Endpoint | What It Provides |
|---|---|
| `GET /api/policies` | Policy rules keyed by trade/class — minimum bond, minimum insurance, minimum years experience, required endorsement, whether serious open violations block |
| `GET /api/contractor/applications` | Applicant identity, trade, class, experience years, endorsement status, prior license ID, self-disclosed issues |
| `GET /api/contractor/bonds` | Bond amount, status (active/cancelled/expired), effective/cancel dates |
| `GET /api/contractor/insurance` | Coverage amount, status (active/pending/expired), expiration date |
| `GET /api/contractor/license-history` | Prior license status — especially whether **suspended** |
| `GET /api/contractor/violations` | Severity, status (open/resolved/dismissed), theme, dates |
| `GET /api/contractor/correspondence` | Assertion type, verified_by_agency flag, notes for staleness |
| `GET /api/contractor/inspections` | Finding code, result (pass/fail/conditional) |
| `POST /api/sql` | Filtered queries when target IDs are known |

### Liquor Licensing Tasks

| Endpoint | What It Provides |
|---|---|
| `GET /api/policies` | Liquor-specific policies (same-premises rules, incident severity matrix) |
| `GET /api/liquor/applications` | Application details, license class, location ID, requested posture |
| `GET /api/liquor/settlements` | Active/inactive controls by location, basis codes, control lists |
| `GET /api/liquor/privileges` | Standard obligations by license class (standard_required flag) |
| `GET /api/liquor/incidents` | Risk codes, severity, status (open/closed/dismissed/referred) |
| `GET /api/liquor/site-evidence` | Evidence type, status (verified/conflicting/missing/stale) |

### Alcohol Renewal Tasks

| Endpoint | What It Provides |
|---|---|
| `GET /api/alcohol/licensees` | License identity, address, successor_to field |
| `GET /api/alcohol/violations` | Violations with alert_flag, disposition, fine_balance, dates, source_name |
| `GET /api/renewal/rules` | Boundary dates, rules for alert filtering and post-boundary handling |

---

## Step 4 — Apply Policy Rules

### Match Policy to Application

Each policy has a `rule_code` (e.g., `CON-ELE-ClassA`) that maps to a trade/class combination. Match the application's trade and requested class to the correct policy. The `details_json` field contains the numeric thresholds. Parse it as JSON.

A legacy/parent policy (e.g., `CON-LEGACY`) may exist for "prior baseline" comparison. Its `details_json` typically contains:
- `endorsement_required_for_specialty: false` — under legacy, specialty trades did not need endorsements.
- `minimum_bond_reduction: <amount>` — subtract this from the current policy's minimum bond.
- `use_for_prior_rule_comparison: true` — confirms it is the comparison baseline.

### Check Each Dimension

For each application, verify against its matched policy:

**Bond:** Look for the most recent bond with `status: "active"`. Compare its `amount` to the policy `minimum_bond`. If no active bond exists → `no_active_bond` / `bond_cancelled`. If amount is below minimum → `bond_shortfall`.

**Insurance:** Use the task's stated review date (if provided) to decide whether coverage is current. Otherwise, treat the `status` field as authoritative:
- `status: "active"` → coverage is current, regardless of expiration date.
- `status: "pending"` → `insurance_not_current` / `insurance_pending`.
- `status: "expired"` → `insurance_expired`.
Compare `amount` to the policy `minimum_insurance`. Below minimum → `insurance_shortfall`.

**Experience:** Compare `years_experience` to `minimum_years_experience`. Below minimum → `experience_shortfall`.

**Endorsement:**
- `endorsement_status: "verified"` → OK.
- `endorsement_status: "pending"` → `endorsement_pending` / `endorsement_not_verified`.
- `endorsement_status: "missing"` → `endorsement_missing` / `endorsement_not_verified`.
- `endorsement_status: "not_required"` → OK (policy may have `required_endorsement: null`).
- If the policy requires an endorsement but legacy did not (specialty trades under 2025), this is a **policy-impacted** deficiency.

**License History:** If `prior_license_id` is set, look up that license in the history endpoint. `status: "suspended"` (especially with notes like "Active suspension pending board action") → `active_suspension`. `status: "expired"` or `"revoked"` is not an active suspension but may still be noted.

**Violations:** Check all violations linked to the application or its prior license:
- `status: "open"` + `severity: "serious"` → `open_serious_violation` / `unresolved_serious_complaint`. This is blocking under policies with `serious_open_violation_blocks: true`.
- `status: "open"` + `severity: "minor"` → `open_minor_violation`.
- `status: "resolved"` or `"dismissed"` → not a deficiency. **Exception:** If `resolved_date` is before `violation_date`, treat the record cautiously — but prefer the explicit `status` field unless the task guidance says otherwise.

**Inspections:** Map finding codes to deficiency codes (only use codes present in the answer template's allowed values):
- `DOC_GAP` → `inspection_doc_gap`
- `SAFETY_RECHECK` → `inspection_safety_recheck`
- `NONE`, `UNVERIFIED_SITE`, `WRONG_TRADE` → typically no direct deficiency (unless the template includes a matching code).

If the template's deficiency codes do **not** include inspection-related codes, inspection findings do not produce listed deficiencies (this varies by task).

**Correspondence:** Flag as stale or unverified when:
- `verified_by_agency: 0` → unverified.
- `notes` contains "Stale attachment" or "Applicant copy only; no agency confirmation" → stale.

### Determine Policy Impact

`policy_impacted` is `true` only when the **2025 policy baseline creates a deficiency that would not exist under the legacy/parent policy**. The two main triggers:
1. A **specialty trade** (Solar, etc.) needs an endorsement under 2025 but legacy's `endorsement_required_for_specialty: false` waived it.
2. A **bond_shortfall** exists under the 2025 minimum but the bond would be sufficient under the legacy reduced minimum (current minimum − `minimum_bond_reduction`).

Deficiencies that exist under both baselines (e.g., cancelled bond, expired insurance, active suspension, experience shortfall for non-specialty trades) are **not** policy-impacted.

### Assign Determination

- `APPROVE` — zero deficiencies. The application is clean.
- `HOLD` — one or more fixable deficiencies, none of which are blocking.
- `DENY` — a blocking condition exists: `active_suspension`, `open_serious_violation` / `unresolved_serious_complaint`, or `no_active_bond` when the policy's `serious_open_violation_blocks` rule applies.

### Assign Risk Tier

- `high` — active suspension, open serious violation, or 3+ deficiencies including at least one major.
- `medium` — multiple moderate deficiencies (bond shortfall, endorsement pending, insurance issues) but no blocking condition.
- `low` — single minor deficiency or none.

---

## Step 5 — Liquor License Staff Package Rules

When building a staff package for a liquor license application:

### Posture
- `issue_restricted` — active controls cover the key risks, no open major incidents.
- `request_follow_up` — verification gaps, open incidents, or conflicting evidence need resolution before issuing.
- `deny` — major unresolved incidents or fundamental eligibility failures.

### Same-Premises Basis
Check the location's settlements. If **any** settlement (active or inactive) has `basis_code: "SAME_PREMISES"` and the liquor policy says `same_premises_history_matters: true`, the same-premises basis applies. Otherwise, it applies only if an active SAME_PREMISES settlement exists.

### Covered Risk Codes
Risks that are mitigated by **currently active** settlement controls. Map controls to risks:
- `HOURS` → `AFTER_HOURS`
- `ID_CHECK` → `MINOR_SALE` / `SALE_TO_MINOR`
- `SECURITY` → `ASSAULT`, `PUBLIC_SAFETY`
- `NOISE` → `NOISE`
- `PATIO` → `PATIO_BOUNDARY`
- `FOOD_SERVICE` → `FOOD_SERVICE_GAP`
- `CCTV` → `CAMERA_COVERAGE`
Also include the active settlement's `basis_code` itself if it names a distinct risk.

### Verification Gap Codes
Map site evidence statuses and open incidents:
- Evidence `status: "conflicting"` → `floor_plan_conflicting`, `control_signage_conflicting`, `police_memo_conflicting`
- Evidence `status: "missing"` → `control_signage_missing`, `site_photo_missing`, `neighbor_notice_missing`, `camera_evidence_missing`, `food_service_evidence_missing`
- Evidence `status: "stale"` → `floor_plan_stale`
- Open incident with risk_code `TAX_HOLD` → `tax_hold_unresolved`
- Referred/open incident needing follow-up → `open_incident_follow_up`
- No HOURS control active + late-night risk → `late_night_monitoring_needed`

### Standard vs Location-Specific Obligations
- **Standard obligations** come from `GET /api/liquor/privileges` where `standard_required: 1` for the application's `license_class`.
- **Location-specific controls** come from the `controls` list of currently active settlements (`active: true`).

### First-90-Day Plan
Build from the verification gaps, prioritizing urgency:
- Evidence gaps → early checks (`first_30_days`).
- Open incident follow-ups → early to mid (`first_30_days` or `days_31_60`).
- Routine compliance observations → mid to late (`days_31_60` or `days_61_90`).

### Escalation Triggers
Derive from open incidents, unresolved verification gaps, and control failures:
- Open tax hold → `TAX_HOLD_REOPENED` / `open_tax_hold_uncleared`
- Referred minor sale → `REFERRED_MINOR_SALE_UNRESOLVED`
- Signage not verified → `CONTROL_SIGNAGE_NOT_VERIFIED`
- CCTV/security gap → `SECURITY_CCTV_CONTROL_FAILURE` / `missing_camera_coverage`
- No food service → `food_service_not_available`
- Noise/patio risk → `noise_or_patio_breach`
- Open assault incident → `unreported_violent_incident`

---

## Step 6 — Alcohol Renewal Queue Rules

### Boundary Date
Every renewal task has a **release boundary date**. The matching renewal rule (from `GET /api/renewal/rules`) confirms: `use_violations_on_or_before` and `late_rows_are_distractors: true`.

**Only include violations on or before the boundary date** in the matched violation lists and counts. Violations with `source_name: "post_boundary_feed"` (or with dates after the boundary) go into `post_boundary_violation_ids_excluded`.

### Alert Filtering
The rule `alert_flag_requires_manual_review: true` means violations with `alert_flag: 1` drive queue prioritization. Non-alert violations still exist in the data but do not contribute to the ranking logic.

### Match Confidence
- No `successor_to` on the licensee → `"exact"`.
- `successor_to` is set → `"uncertain"` (per `successor_match_mark_uncertain: true`).

### Violation Count and Matched IDs
Count and list **only pre-boundary violations**. Sort matched IDs by `violation_date` ascending, then `violation_id` ascending. The `most_recent_violation_date` is the latest violation date among the matched set.

### Ranking
Rank all licenses from 1 to N (no gaps, no ties). Primary factors in descending importance:
1. Count of alert violations (more = higher rank).
2. Presence of serious-severity violations with open/pending disposition.
3. Total fine balance (higher unpaid fines = higher rank).
4. Recency of violations (more recent = higher rank).

Licenses with zero alert violations rank at the bottom.

### Next-Step Labels
- `board_review` — serious open/pending violations requiring board attention.
- `manual_fine_check` — open violations with significant unpaid fines.
- `manual_ALERT_check` — alert violations needing staff review but below board threshold.
- `additional_record_check` — uncertain matches or licenses needing deeper record verification.

### Summary Fields
- `close_or_uncertain_match_license_numbers` — all licenses with `match_confidence` of `"uncertain"` or `"close_address"`.
- `board_review_license_numbers` — all licenses assigned `board_review` as next step.
- `post_boundary_violation_ids_excluded` — every post-boundary violation ID across all target licenses.

---

## Step 7 — Assemble and Validate

1. **Order application_decisions / queue entries** as specified by the template (typically by application_id ascending or by rank ascending).
2. **Sort all code arrays** alphabetically/lexically.
3. **Verify counts match** — summary `approve_count + hold_count + deny_count` must equal the number of applications. Queue `summary.queue_size` must equal the number of queue entries.
4. **Check every enum value** against the template's allowed_values list.
5. **Use empty arrays** (`[]`) when no codes, IDs, or actions apply — never `null` or omitted keys.
6. **Strip all prose** — the output must be pure JSON matching the template structure exactly.
