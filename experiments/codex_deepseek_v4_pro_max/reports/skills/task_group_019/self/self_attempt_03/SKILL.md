 # Licensing Review Skill

## Overview

This skill enables an agent to process structured licensing-review tasks (contractor licensing, liquor licensing, alcohol renewal) against a shared licensing environment API. The agent reads task inputs, fetches data from the environment, applies domain decision rules, and returns a JSON answer conforming to a supplied output schema.

## Task Discovery

When invoked on a licensing-review task, expect the working directory to contain:

- A natural-language `prompt.txt` describing the task, target identifiers, and any special parameters (review dates, queue sizes, release boundaries).
- An `answer_template.json` defining the exact output schema, allowed values, ordering constraints, and whether empty values use `[]`.
- An `environment_access.md` providing the base URL, allowed HTTP endpoints, auth token header, and SQL access instructions.

Always read all three inputs before making any API calls.

## Environment Connection

1. Extract the base URL from `environment_access.md`. It is the value associated with `Base URL:`.
2. Note the auth token header name and value (e.g., `X-Task-Token: <value>`). Include this header in every API request.
3. Identify which GET endpoints are allowed and which POST endpoints (typically `/api/sql`) are available.

## API Interaction Rules

### GET Requests

- Use the exact endpoint paths listed in `environment_access.md`.
- Include the auth token header on every request.
- Accept `application/json` responses.
- If an endpoint returns an empty result or 404, treat it as no data for that resource — do not retry indefinitely.

### POST /api/sql

- Only use if `POST /api/sql` is listed in `environment_access.md`.
- Send `Content-Type: application/json` and the auth token header.
- Body format: `{"query": "<SELECT statement>", "params": ["<value>", ...], "limit": <integer optional>}`.
- Use parameterized queries with `?` placeholders and the `params` array — never interpolate values directly into the query string.
- Start with schema discovery: `SELECT name FROM sqlite_master WHERE type = ? ORDER BY name` with `params: ["table"]` to learn available tables. Then inspect column schemas with `PRAGMA table_info(<table>)` or `SELECT * FROM <table> LIMIT 1` before writing domain queries.
- Use SQL to correlate data across tables when the GET endpoints return denormalized or incomplete views.

## Domain Data Sources

Based on the task domain (contractor, liquor, or alcohol), fetch from these endpoints:

### Contractor Licensing
- `GET /api/policies` — current policy baseline that may create new deficiencies or review flags.
- `GET /api/contractor/applications` — application records with status, endorsements, experience claims.
- `GET /api/contractor/bonds` — surety bond records with amounts, statuses, effective dates.
- `GET /api/contractor/insurance` — liability insurance records with coverage amounts, expiry dates.
- `GET /api/contractor/license-history` — prior licenses, suspensions, revocations.
- `GET /api/contractor/violations` — complaint and violation records with severity and resolution status.
- `GET /api/contractor/correspondence` — board correspondence with dates and verification status.
- `GET /api/contractor/inspections` — inspection records with findings and document gaps.

### Liquor Licensing
- `GET /api/policies` — policy baseline affecting license conditions.
- `GET /api/liquor/applications` — application details, license class, location.
- `GET /api/liquor/settlements` — settled or pending enforcement actions.
- `GET /api/liquor/privileges` — active privileges and endorsements tied to the license or location.
- `GET /api/liquor/incidents` — incident reports (assault, noise, minor sales, etc.) at the location.
- `GET /api/liquor/site-evidence` — site photos, floor plans, signage evidence, police memos, tax clearances.

### Alcohol Renewal
- `GET /api/alcohol/licensees` — licensee records with facility names, addresses, license numbers.
- `GET /api/alcohol/violations` — violation records with dates, descriptions, resolution status.
- `GET /api/renewal/rules` — renewal rule definitions, ranking criteria, risk thresholds.

## Decision Framework

### Contractor Eligibility Determinations

Evaluate each application against these dimensions and assign `APPROVE`, `HOLD`, or `DENY`:

- **Bond status**: Active bond with sufficient coverage amount vs. cancelled, expired, or shortfall.
- **Insurance status**: Current policy with sufficient coverage vs. expired or shortfall.
- **Endorsements**: Required endorsements verified vs. missing or pending.
- **Experience**: Documented experience meets threshold vs. shortfall.
- **License history**: Active suspensions → DENY or HOLD. Prior revocations increase risk.
- **Violations**: Open serious violations → at minimum HOLD. Open minor violations → flag for review.
- **Inspections**: Safety recheck needed or document gaps → HOLD with required actions.
- **Correspondence**: Stale or unverified correspondence increases risk tier.
- **Policy impact**: A current policy baseline that creates a deficiency not present under prior rules → flag `policy_impacted: true`.

Risk tier assignment:
- `high`: active suspension, open serious violation, multiple concurrent deficiencies, or policy-triggered denial.
- `medium`: one or two fixable deficiencies (bond shortfall, endorsement pending, inspection gap).
- `low`: no deficiencies or only minor documentation gaps.

### Liquor License Posture

For restricted liquor license staff packages, assign `issue_restricted`, `request_follow_up`, or `deny`:

- Evaluate **same-premises basis**: whether the applicant operates at a location with prior incident or settlement history that triggers heightened scrutiny under the same-premises doctrine.
- Assess **covered risks**: which risk categories are adequately mitigated by existing controls (CCTV, security, ID checks, food service, hours restrictions, noise controls, patio boundaries).
- Identify **verification gaps**: missing or conflicting site evidence (floor plans, signage, police memos, neighbor notices, tax clearances, camera/food-service evidence).
- Distinguish **standard obligations** (ordinary license-class requirements) from **location-specific controls** (extra conditions imposed due to site history or risk profile).
- Build a **first-90-day monitoring plan** with timed check codes (`first_30_days`, `days_31_60`, `days_61_90`) covering inspections, evidence rechecks, and log reviews.
- Define **escalation triggers** that would cause field staff to elevate the license for further action.

### Alcohol Renewal Queue

For renewal manual-review queues:

- Apply the **release boundary date** from the prompt. Only violations on or before this date count toward the queue decision. Violations after the boundary are excluded and listed in the summary.
- Match licensees to violations by license number or facility identity. Assign match confidence:
  - `exact`: license number match.
  - `close_address`: facility name/address similarity match without exact license number.
  - `uncertain`: partial or ambiguous match.
- Rank by violation count (descending), then by recency of most recent violation (most recent first), then by risk tier.
- Assign risk tier based on violation severity, count, and recency.
- Assign next-step labels: `manual_fine_check`, `manual_ALERT_check`, `board_review`, or `additional_record_check` based on violation patterns and severity.
- The queue must contain exactly the target size specified in the prompt, with ranks 1 through N and no gaps.

## Output Construction

1. Parse `answer_template.json` completely. Note every required key, allowed enum value, ordering constraint, and type specification.
2. Build the JSON object key-by-key, ensuring:
   - Every required top-level key is present.
   - Every value is of the correct type (string, integer, boolean, array, object).
   - Enum values match the allowed set exactly (case-sensitive).
   - Arrays use the specified ordering (ascending lexical, ascending by date, or as specified).
   - Empty arrays (`[]`) are used when no codes or IDs apply — never `null` or omitted keys.
   - Integer fields are actual integers, not strings.
   - Boolean fields are `true` or `false`, not strings.
3. Ensure counts in summary objects are consistent with the item-level decisions. For example, `approve_count` + `hold_count` + `deny_count` must equal the total number of applications reviewed.
4. Sort all ID lists in summaries per the template's ordering instruction (typically ascending lexical).

## Output Discipline

- Return **only** the JSON object. No markdown fences, no prose preamble, no citations, no comments.
- Do not include any keys not present in the answer template, even if they seem useful.
- Do not wrap the JSON in a code block or add trailing text.
- The first character of the output must be `{` and the last must be `}` (or `[` / `]` if the template specifies an array root).

## Error Handling

- If an API endpoint is unreachable after one retry, note the failure and proceed with available data. Mark affected decisions conservatively (prefer HOLD over APPROVE when data is missing).
- If a target application or license ID from the prompt is not found in any API response, include it in the output with a conservative determination and note the gap through appropriate deficiency/verification codes.
- If the answer template specifies an allowed value that does not appear in the API data, do not invent it — only use codes supported by evidence.

## Sequence Summary

1. Read `prompt.txt`, `answer_template.json`, and `environment_access.md`.
2. Connect to the licensing environment using the base URL and auth token.
3. Fetch all relevant GET endpoints for the task domain.
4. Run SQL schema discovery and domain queries if `/api/sql` is available.
5. Correlate data across sources per the decision framework above.
6. Build the JSON output matching the answer template exactly.
7. Output the JSON with no additional text.
