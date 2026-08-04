This skill helps an agent process structured licensing-review tasks by connecting to a remote licensing environment, fetching relevant business records, and generating machine‑readable JSON decisions.

## When to Use

Use this skill whenever a prompt asks you to review contractor, liquor, or alcohol license applications and directs you to a `<TASK_ENV_BASE_URL>` for data retrieval.

## Environment Access

The licensing environment is available at the base URL given in the prompt as `<TASK_ENV_BASE_URL>`. Connect to it like this:

- **GET endpoints**: Fetch records directly; no special headers are needed beyond standard HTTP.
- **POST /api/sql**: Run SELECT queries against the environment's database. You must include two headers:
  - `Content-Type: application/json`
  - `X-Task-Token: licensing-review-019`
  - The JSON body takes `"query"` (a SELECT string), `"params"` (an array of bind values), and an optional `"limit"` integer.

The following GET endpoints may be available depending on the task domain:

### Contractor Domain
- `GET /api/policies`
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`

### Liquor Domain
- `GET /api/policies`
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`

### Alcohol Domain
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`

When the prompt lists a `POST /api/sql` endpoint, use it to run targeted SQL queries (e.g., `SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name`) to explore the schema and retrieve specific records that are not directly exposed through the GET endpoints.

## Step‑by‑Step Workflow

### 1. Read the Prompt and the Answer Template

- Read `input/prompt.txt` to understand the task type, the target application IDs, any review date, and the relevant endpoints.
- Read `input/payloads/answer_template.json` to learn the exact JSON structure, allowed enum values, and ordering rules your answer must follow.

### 2. Identify the Task Domain

Classify the task into one of three domains based on the prompt's application‑ID prefix and endpoint hints:

- **Contractor batch eligibility** (`C-TR*‑*` prefix): uses `/api/contractor/*` endpoints.
- **Liquor license staff package** (`L-TR*‑*` prefix): uses `/api/liquor/*` endpoints.
- **Alcohol renewal manual‑review queue** (`AL-TR*‑*` prefix): uses `/api/alcohol/*` and `/api/renewal/*` endpoints.

### 3. Fetch All Relevant Records

For the identified domain, call every GET endpoint listed in the prompt. Save the responses for decision‑making. If the prompt includes `POST /api/sql`, also explore the database schema to discover additional tables and run targeted queries for data that supplements the GET responses.

### 4. Apply Business Rules to Each Application

#### Contractor Batch Review

For each target application, cross‑reference data from policies, applications, bonds, insurance, license‑history, violations, correspondence, and inspections.

- **Determination**:
  - `DENY` when the applicant has an active suspension, an unresolved serious complaint or violation, or a mandatory safety recheck that has not been cleared.
  - `HOLD` when deficiencies exist but are fixable (e.g., bond shortfall, expired insurance, pending endorsement, experience shortfall, minor violation, inspection document gap).
  - `APPROVE` when no deficiencies are found across any checked category.
- **Deficiency codes**: List every applicable code from the template's allowed values, sorted alphabetically. Use an empty array when none apply.
- **Required actions**: Map each deficiency to its corresponding corrective action from the template's allowed values, sorted alphabetically.
- **Risk tier**:
  - `high` when the application has a `DENY` determination or multiple serious issues.
  - `medium` when the application has a `HOLD` determination with fixable issues.
  - `low` when the application is `APPROVE` with no issues.
- **policy_impacted**: Set to `true` when the current policy baseline (2025) introduces a new requirement that would not have flagged the application under the prior baseline — for example, a new endorsement requirement, a higher bond minimum, or a stricter experience threshold. Set to `false` when the deficiency would exist under either baseline.

- **Summary**: Count approve/hold/deny. Collect high‑risk IDs, policy‑impacted IDs, and stale/unverified correspondence IDs (those where correspondence records show pending, unverified, or no‑response status), all sorted ascending.

#### Liquor License Staff Package

For the single target application, cross‑reference policies, applications, settlements, privileges, incidents, and site evidence.

- **recommended_posture**:
  - `issue_restricted` when risks are covered by current controls and all required evidence is in order.
  - `request_follow_up` when verification gaps exist (missing camera/food‑service evidence, unresolved tax holds, conflicting floor plans, police memo issues, signage problems, or missing site photos / neighbor notices). If the gap is serious the posture may still be `request_follow_up` to give the applicant time to resolve.
  - `deny` when there are major unresolved incidents, an open tax hold with no resolution path, or fundamental eligibility problems.
- **same_premises_basis_applies**: `true` when the application is for a license at the same premises as a prior license; `false` otherwise. Derive this from location and prior‑license data.
- **covered_risk_codes**: Risk areas where current controls (CCTV, security, hours restrictions, ID checks, food service) already provide coverage. Include only the codes that are actually covered.
- **verification_gap_codes**: Evidence or documentation gaps that prevent full verification (missing camera exports, missing food‑service proof, conflicting floor plans, late‑night monitoring needed, unresolved tax holds, missing signage/neighbor notices/police memos/site photos).
- **standard_obligation_codes**: Ordinary obligations required for this license class (e.g., ID_CHECK, HOURS, FOOD_SERVICE, CCTV, SECURITY, NOISE, PATIO, DELIVERY). Include only those that are standard for the class, not location‑specific add‑ons.
- **location_specific_control_codes**: Controls currently active at this specific location beyond standard obligations.
- **first_90_day_plan**: A sequenced list of monitoring checks, each with a `check_code` and a `timing` (`first_30_days`, `days_31_60`, `days_61_90`). Plan checks that address the verification gaps — for example, a camera export test in the first 30 days if camera evidence is missing, a late‑night closing visit in days 31–60 if late‑night monitoring is needed.
- **escalation_trigger_codes**: Conditions that should trigger staff escalation (after‑hours service, missing camera coverage, footage not produced, unavailable food service, noise/patio breach, uncleared tax hold, unreported violent incident, minor sale, patio boundary failure, ID check failure). Include every trigger that is plausible given the verification gaps and risk profile.

#### Alcohol Renewal Queue

For the target license range, fetch licensees, violations, and renewal rules. Apply the boundary date from the prompt.

- **Ranking**: Rank licensees 1 through N by descending severity. Prioritize by violation count and recency, with exact matches ranked higher than close‑address or uncertain matches. Licensees with the same match confidence and similar violation profiles should be ordered by most‑recent‑violation descending.
- **Violation matching**: Match violations to licensees by license number. When a violation's address closely matches but the license number differs, classify the match as `close_address`. When the matching is ambiguous, classify as `uncertain`.
- **Boundary filter**: Exclude violations dated after the boundary date. Count only pre‑boundary violations in `violation_count` and `matched_violation_ids`.
- **match_confidence**: `exact` when the license number matches directly; `close_address` when address data suggests a match with a different or historical license number; `uncertain` when the link is tenuous.
- **risk_tier**: Based on violation severity and count. Use `high` for licensees with serious or numerous violations; `medium` for moderate profiles; `low` for minimal issues.
- **next_step_label**:
  - `board_review` for the top‑risk licensees (typically the highest‑ranked entries with serious patterns).
  - `manual_fine_check` for licensees needing fine verification.
  - `manual_ALERT_check` for licensees requiring ALERT system review.
  - `additional_record_check` for edge cases.
- **Summary**: Include `queue_size`, `boundary_date`, `post_boundary_violation_ids_excluded` (all violation IDs that fell after the boundary, sorted), `close_or_uncertain_match_license_numbers` (sorted), and `board_review_license_numbers` (sorted).

### 5. Produce the Output

Return only a single JSON object that matches the answer template. Follow every ordering rule:
- Sort arrays of codes/IDs alphabetically or as specified.
- Sort application decisions by `application_id` ascending.
- Sort queue entries by rank ascending.
- Use empty arrays (`[]`) when no codes/IDs apply.
- Include no prose, markdown, comments, or extra keys.

## Key Principles

- **Fetch first, decide second**: Always retrieve all available data before making any determination. Do not guess.
- **Template is authoritative**: The answer template defines the exact schema. Follow its enum values, ordering rules, and required keys exactly.
- **Cross‑reference thoroughly**: A single application may touch multiple data sources. Check bonds, insurance, history, violations, correspondence, and inspections holistically.
- **Policy baseline matters**: When policies have changed (e.g., a 2025 update), flag applications where the new baseline alone creates the issue.
- **Dates are YYYY-MM-DD**: Use this format whenever a date field is required.
