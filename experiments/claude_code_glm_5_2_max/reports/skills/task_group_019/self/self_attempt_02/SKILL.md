# Licensing Board Examiner — Reusable Skill

## Purpose

This skill solves structured licensing-application review tasks served by a shared licensing data environment. It covers three domain archetypes:

| Archetype | Domain | Typical scope |
|---|---|---|
| Contractor batch eligibility | Contractor licensing | Multiple applications per batch, APPROVE/HOLD/DENY decisions |
| Liquor restricted-license staff package | Liquor licensing | Single application + location, issuance posture + controls |
| Alcohol renewal manual-review queue | Alcohol renewal | Ranked queue of licenses, violation-matching, boundary date |

## Environment Access

1. **Base URL** — read from `environment_access.md` in the working directory (or `<TASK_ENV_BASE_URL>` placeholder in the prompt). Replace the placeholder with the actual base URL before making any request.
2. **Auth token** — `POST /api/sql` requires header `X-Task-Token: <value from environment_access.md>`. All `GET` endpoints are unauthenticated.
3. **Allowed endpoints only** — never attempt paths not listed in `environment_access.md` or the prompt.

## Step-by-Step Operating Procedure

### Step 1 — Read the prompt and identify the archetype

- **Contractor batch**: prompt mentions *contractor application batch*, *State Contractors Licensing Board*, application IDs with `C-` prefix, and endpoints under `/api/contractor/`.
- **Liquor staff package**: prompt mentions *restricted liquor license*, *staff package/review*, a single application ID with `L-` prefix, a location ID with `LOC-` prefix, and endpoints under `/api/liquor/`.
- **Alcohol renewal queue**: prompt mentions *renewal*, *manual-review queue*, license IDs with `AL-` prefix, a *release boundary date*, and endpoints under `/api/alcohol/` plus `/api/renewal/`.

### Step 2 — Read the answer template

Read `input/payloads/answer_template.json` before making any API calls. It defines:

- Required top-level keys and their ordering constraints.
- Allowed enum values for every coded field — **never invent codes**; only use values listed in the template.
- Sorting rules (ascending by ID, alphabetical, etc.).
- Whether empty arrays are acceptable for list fields.

### Step 3 — Fetch all relevant data

Call every endpoint listed in the prompt. The complete catalog by archetype:

| Endpoint | Contractor | Liquor | Alcohol renewal |
|---|:---:|:---:|:---:|
| `GET /api/policies` | ✓ | ✓ | |
| `GET /api/contractor/applications` | ✓ | | |
| `GET /api/contractor/bonds` | ✓ | | |
| `GET /api/contractor/insurance` | ✓ | | |
| `GET /api/contractor/license-history` | ✓ | | |
| `GET /api/contractor/violations` | ✓ | | |
| `GET /api/contractor/correspondence` | ✓ | | |
| `GET /api/contractor/inspections` | ✓ | | |
| `GET /api/liquor/applications` | | ✓ | |
| `GET /api/liquor/settlements` | | ✓ | |
| `GET /api/liquor/privileges` | | ✓ | |
| `GET /api/liquor/incidents` | | ✓ | |
| `GET /api/liquor/site-evidence` | | ✓ | |
| `GET /api/alcohol/licensees` | | | ✓ |
| `GET /api/alcohol/violations` | | | ✓ |
| `GET /api/renewal/rules` | | | ✓ |
| `POST /api/sql` (with token) | ✓ | ✓ | ✓ |

Fetch the **policies** endpoint first — policy baselines affect eligibility thresholds and must be incorporated before evaluating any application.

### Step 4 — Apply business rules

#### 4a. Contractor batch eligibility rules

For each application in the target batch:

1. **Determination** — evaluate in this priority order (first triggering condition wins):
   - `DENY` if the applicant has an **active suspension** in license history.
   - `HOLD` if any deficiency code applies (see below) but no deny-trigger is present.
   - `APPROVE` if no deficiencies are found.

2. **Deficiency codes** — assign from visible evidence:
   - Bond issues: `bond_cancelled`, `bond_shortfall`, `no_active_bond` (use code sets from the answer template for the specific batch).
   - Insurance issues: `insurance_expired`, `insurance_pending`, `insurance_shortfall`, `insurance_not_current`.
   - Endorsement issues: `endorsement_missing`, `endorsement_pending`, `endorsement_not_verified`.
   - Experience issues: `experience_shortfall`.
   - Violation/complaint issues: `open_minor_violation`, `open_serious_violation`, `unresolved_serious_complaint`.
   - Inspection issues: `inspection_doc_gap`, `inspection_safety_recheck`.

3. **Required actions** — each deficiency maps to a remediation action (e.g., `bond_shortfall` → `increase_bond_amount`; `insurance_expired` → `provide_current_insurance`). Use only action codes from the template.

4. **Risk tier**:
   - `high` — any serious violation, active suspension, or multiple deficiencies across categories.
   - `medium` — one or two minor deficiencies in a single category.
   - `low` — no deficiencies (APPROVE applications).

5. **Policy impacted** — `true` when a current policy baseline (from `/api/policies`) introduces a new requirement or threshold that would not have applied under the prior baseline, and that new requirement creates a deficiency or material flag for this application.

6. **Review date** — if the prompt specifies a review date, use it to decide whether financial coverage (bonds, insurance) is current. A document expiring before the review date is expired; one expiring on or after is current.

7. **Summary**:
   - `approve_count`, `hold_count`, `deny_count` — must be consistent with application-level decisions.
   - `high_risk_application_ids` — all applications with `risk_tier: "high"`, sorted ascending.
   - `policy_impacted_application_ids` — all applications with `policy_impacted: true`, sorted ascending.
   - `stale_or_unverified_correspondence_ids` — IDs from `/api/contractor/correspondence` that are stale (older than policy threshold) or unverified, sorted ascending.

#### 4b. Liquor restricted-license staff package rules

1. **Recommended posture**:
   - `issue_restricted` — if all verification gaps are minor or resolved and no disqualifying risk exists.
   - `request_follow_up` — if verification gaps require additional documentation but are not fatal.
   - `deny` — if a disqualifying condition exists (e.g., unresolved serious incident, missing fundamental documentation).

2. **Same-premises basis** — `true` when the applicant has held a license for the same premises previously (check settlements and privileges data).

3. **Covered risk codes** — risks that existing controls or privileges already address (from the template's allowed set). Each code at most once.

4. **Verification gap codes** — risks or documentation gaps that remain unaddressed. Each code at most once.

5. **Standard obligation codes vs. location-specific control codes**:
   - *Standard obligations* — obligations that are ordinary required obligations for this license class (apply to all licensees of this type).
   - *Location-specific controls* — active controls tied specifically to this location (may overlap with standard obligations but should only include those with a location-specific basis).

6. **First 90-day plan** — monitoring checks for the first 90 days post-issuance:
   - Each entry has `check_code` and `timing` (`first_30_days`, `days_31_60`, `days_61_90`).
   - Focus urgent checks (safety, signage, ID procedures) in the first 30 days.
   - Follow-up and compliance-verification checks in days 31-60 and 61-90.
   - Remove duplicate check_code/timing pairs; sort as the template specifies.
   - For hotel-lounge contexts: emphasize camera/food-service evidence and late-night monitoring.

7. **Escalation trigger codes** — conditions that would escalate the license to board-level review or enforcement. Each code at most once.

8. **Use site evidence and incidents data** to populate risk, gap, and control fields. Cross-reference `/api/liquor/settlements` and `/api/liquor/privileges` for prior history.

#### 4c. Alcohol renewal manual-review queue rules

1. **Boundary date** — the prompt specifies a release boundary date. Only violations dated **on or before** the boundary count for queue ranking. Violations after the boundary are excluded and listed in `post_boundary_violation_ids_excluded`.

2. **Match violations to licensees** — join `/api/alcohol/licensees` with `/api/alcohol/violations` using the license number or facility identity. If direct join is ambiguous, use `POST /api/sql` with the auth token to query relationships.

3. **Match confidence**:
   - `exact` — license number matches directly.
   - `close_address` — address matches but license number differs or is missing.
   - `uncertain` — name similarity or partial match only.

4. **Risk tier** — based on violation count and severity:
   - `high` — multiple serious violations or any board-order-level violation.
   - `medium` — one serious or multiple minor violations.
   - `low` — one minor violation.

5. **Next step label**:
   - `board_review` — high-severity or repeat violations requiring board action.
   - `manual_ALERT_check` — ALERT-system flags found.
   - `manual_fine_check` — outstanding fine-related violations.
   - `additional_record_check` — uncertain matches needing verification.

6. **Ranking** — order the queue by:
   - Higher risk tier first (high > medium > low).
   - Within same tier: more violations first.
   - Within same count: most recent violation date first (latest first).
   - Ranks are integers 1 through N (where N = queue size from the prompt), no gaps.

7. **Summary**:
   - `queue_size` — number of queue entries.
   - `boundary_date` — the release boundary from the prompt.
   - `post_boundary_violation_ids_excluded` — IDs of violations dated after the boundary, sorted ascending by violation_id.
   - `close_or_uncertain_match_license_numbers` — licenses with non-`exact` match confidence, sorted ascending.
   - `board_review_license_numbers` — licenses with `next_step_label: "board_review"`, sorted ascending.

8. **Renewal rules** — fetch `/api/renewal/rules` and apply any rule-based disqualification or flagging logic specified there.

### Step 5 — Assemble the JSON output

1. **Strict template conformance** — every key, enum value, and ordering rule must match the answer template exactly. Do not include extra keys, prose, markdown, comments, or narrative.
2. **Ordering** — sort all lists as the template specifies (ascending by ID, alphabetical by code, etc.).
3. **Empty arrays** — use `[]` when no codes or IDs apply to a field; do not omit the key.
4. **Summary consistency** — per-application counts must add up to the total batch size; summary IDs must be a subset of the application IDs (or correspondence IDs, etc.) in the output.
5. **Return only the JSON object** — no wrapping, no explanation.

## General Principles

- **Policies first** — always fetch and incorporate the current policy baseline before evaluating eligibility.
- **No invented codes** — every coded value must come from the answer template's allowed set for that field.
- **Financial coverage dating** — when a review date is specified, use it as the cutoff for determining whether bonds or insurance are current.
- **Correspondence staleness** — correspondence records past the policy staleness threshold are flagged as stale; unverified records (no confirmation of receipt or response) are flagged as unverified. Both go into `stale_or_unverified_correspondence_ids`.
- **SQL endpoint** — use `POST /api/sql` (with the `X-Task-Token` header) for cross-entity joins or aggregations that are not easily derived from individual GET responses.
- **Boundary enforcement** — for renewal queues, strictly separate pre-boundary and post-boundary violations; exclude the latter from ranking but include them in the summary.
- **Hotel-lounge specificity** — for liquor packages involving hotel lounges, pay special attention to camera coverage, food-service evidence, and late-night monitoring controls.

## File Reference

- `environment_access.md` — base URL, auth token, allowed endpoint list.
- `input/payloads/answer_template.json` — schema, allowed values, ordering rules (task-specific; read each time).
