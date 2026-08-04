## When to Use

Use this skill when the task involves reviewing, adjudicating, or preparing staff packages for licensing applications in a regulated domain (contractor, liquor, or alcohol licensing). The skill covers structured data gathering from a REST API environment, SQL-based schema exploration, policy-driven eligibility analysis, and production of JSON decision outputs conforming to a provided answer template.

## Environment

The licensing data service is available at a base URL provided as `<TASK_ENV_BASE_URL>`. All endpoints return JSON.

### Authentication for SQL

The `POST /api/sql` endpoint requires:
- Header `Content-Type: application/json`
- Header `X-Task-Token: licensing-review-019`
- JSON body: `{"query": "<SQL>", "params": ["<value>"], "limit": <integer>}`

Params are positional (`?` placeholders). Limit is optional; include it for safety on large tables.

### Available REST Endpoints

**Policy & Rules:**
- `GET /api/policies` — current policy baseline
- `GET /api/renewal/rules` — renewal-specific rules

**Contractor Domain:**
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`

**Liquor Domain:**
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`

**Alcohol Domain:**
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`

## Operating Procedure

### Step 1 — Schema Discovery

Before analyzing any applications, explore the data schema:

1. Call `GET /api/policies` to load the current policy baseline.
2. Call `POST /api/sql` with `SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name` to list all tables.
3. For each table of interest, call `POST /api/sql` with `PRAGMA table_info(<table_name>)` to inspect columns.

### Step 2 — Gather All Evidence

For every target application or license identifier in the task:

1. Query every domain-relevant GET endpoint (the endpoints return all records; filter client-side).
2. Use SQL queries to cross-reference records, join tables, or filter where REST endpoints are insufficient.
3. Collect: bond records, insurance records, violation/complaint records, license history, correspondence, inspections, and any domain-specific evidence (settlements, privileges, incidents, site evidence).

### Step 3 — Apply Policy Rules

Evaluate each application against the policy baseline from `/api/policies`:

- **Bonds**: Check if a bond exists, is active (not cancelled), and meets the required amount. A bond shortfall or cancellation is a deficiency.
- **Insurance**: Check if insurance is current relative to the review date, and whether coverage amounts meet policy minimums. Expired or insufficient insurance is a deficiency.
- **Violations**: Identify open (unresolved) violations. Serious violations are higher severity than minor ones. Resolved violations do not create deficiencies.
- **Endorsements**: Check whether required specialty endorsements are present and verified. Missing or pending endorsements are deficiencies.
- **Experience**: Verify that documented experience meets the minimum duration/scope required by policy.
- **Suspensions**: An active suspension on the license history is a blocking deficiency.
- **Correspondence**: Stale or unverified correspondence may flag additional review.
- **Inspections**: Gaps in required inspection documentation or unresolved safety rechecks are deficiencies.

### Step 4 — Determine Outcome

For each application, assign a determination:

- `APPROVE` / `issue_restricted`: No deficiencies found; all requirements met.
- `HOLD` / `request_follow_up`: Deficiencies exist but are resolvable with further action.
- `DENY` / `deny`: Blocking deficiencies (active suspension, unresolvable gaps).

Select the exact enum values from the answer template schema — different task types use different determination vocabularies.

### Step 5 — Assign Risk Tier

| Tier | Criteria |
|------|----------|
| `low` | No deficiencies, or only minor administrative gaps. |
| `medium` | One or more resolvable deficiencies, no active suspension or serious unresolved violations. |
| `high` | Active suspension, open serious violations, multiple concurrent deficiencies, or policy-impacted edge cases. |

### Step 6 — Produce Output

1. Read the provided `answer_template.json` (or equivalent schema file) in full.
2. Build the output object key-by-key, using exactly the allowed enum values and key names.
3. For array fields: sort as specified (usually ascending/lexical), use empty arrays (`[]`) when no items apply, never `null`.
4. Order application-level entries by `application_id` ascending.
5. For summary objects: compute counts and collect IDs from the application-level decisions — the summary must be internally consistent with the individual decisions.
6. Output only the JSON object — no prose, markdown, citations, or extra keys.

## Domain-Specific Notes

### Contractor Licensing

- The review date matters for financial coverage: bonds and insurance must be current as of the review date.
- `policy_impacted` is true when a 2025-era policy creates a deficiency that would not have existed under prior rules.
- Deficiency codes map to required actions: each deficiency implies one or more corrective actions.

### Liquor Licensing

- `same_premises_basis_applies`: Whether the existing premises-control framework covers the location.
- `covered_risk_codes`: Risks that are already mitigated by current controls.
- `verification_gap_codes`: Evidence or documentation that is missing, stale, or conflicting.
- `standard_obligation_codes`: Normal license-class obligations.
- `location_specific_control_codes`: Controls tied to the specific site.
- `first_90_day_plan`: Monitoring checks with timing buckets (`first_30_days`, `days_31_60`, `days_61_90`).
- `escalation_trigger_codes`: Conditions that should prompt field staff intervention.

### Alcohol Renewal Queue

- A `boundary_date` separates violations that count toward the queue from those excluded (post-boundary).
- Licensees are matched to violations by identity/address; match confidence is `exact`, `close_address`, or `uncertain`.
- Ranking prioritizes: higher violation counts, more recent violations, higher risk tier, lower match confidence.
- `next_step_label` directs staff to the appropriate follow-up workflow.

## SQL Query Patterns

- Table discovery: `SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name`
- Column inspection: `PRAGMA table_info('<table>')`
- Filtered lookup: `SELECT * FROM <table> WHERE <column> = ?` with params array
- Multi-table join for cross-referencing records across domains
- Always use parameterized queries with `?` placeholders and the `params` array; never interpolate values into SQL strings.

## Common Pitfalls

- Do not assume endpoint coverage is complete — use SQL to verify or fill gaps.
- Do not include prose, markdown, or extra keys in the output JSON.
- Do not skip reading the answer template — enum values and key names vary between task types.
- Empty list fields must be `[]`, not `null` or omitted.
- Summary counts must be derivable from the application-level decisions — keep them consistent.
