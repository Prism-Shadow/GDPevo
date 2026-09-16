---
name: licensing-review
description: >
  State licensing review workflows for contractor eligibility batches,
  restricted liquor license staff packages, and alcohol renewal manual-review
  queues. Use this skill whenever the user mentions contractor licensing,
  liquor license review, alcohol renewal screening, licensing board decisions,
  license application review, compliance staff packages, or any task that
  involves fetching licensing data from a REST API and producing a structured
  JSON decision output. Even when the user does not explicitly name the domain,
  if they describe a batch of applications, a license review package, or a
  ranked compliance queue tied to licensing endpoints, use this skill.
---

# State Licensing Review

Follow this workflow for any state licensing review task: contractor
eligibility, restricted liquor staff packages, or alcohol renewal queues.

## Core Workflow

The task always follows this sequence. Do not skip steps.

### Step 1: Read the Answer Template

Read `input/payloads/answer_template.json` before anything else. This is your
output contract. Every allowed value, every required key, every ordering rule
lives in the template. This is the single most important file in the task.

From the template, extract:
- Every required top-level key and its type
- Every allowed enum value for each field
- Every ordering constraint (sort ascending by what, remove duplicates)
- Whether empty arrays are used for absent values or omitted
- Any date format requirements

The template is the authority. The prompt may summarize it, but the template
is the definitive schema.

### Step 2: Identify the Domain

From the prompt and template, determine which domain workflow applies:

- **Contractor**: application_decisions array with determination/deficiency_codes/required_actions/risk_tier per application. Load [references/contractor.md](references/contractor.md).
- **Liquor**: single-application staff package with recommended_posture, covered_risk_codes, verification_gap_codes, standard_obligation_codes, location_specific_control_codes, first_90_day_plan, escalation_trigger_codes. Load [references/liquor.md](references/liquor.md).
- **Alcohol Renewal**: ranked queue with license_no, violation_count, matched_violation_ids, match_confidence, risk_tier, next_step_label. Load [references/alcohol-renewal.md](references/alcohol-renewal.md).

If the template structure does not clearly match one of the three, read all
three reference files and determine which is closest. The reference files
contain the domain-specific rules you need.

### Step 3: Discover the Environment

Find `<TASK_ENV_BASE_URL>` in the prompt. If it is a placeholder, read
`/work/environment_access.md` for the actual base URL and any required
authentication headers.

Every task provides a shared licensing environment with REST endpoints and
optionally a POST /api/sql endpoint. The prompt lists which endpoints are
relevant for this specific task — use only those unless you discover a need
for others.

### Step 4: Fetch All Relevant Data

Call every endpoint listed in the prompt. Do not call endpoints the prompt
does not list unless the data you need is clearly missing.

Default order, when the prompt does not specify:
1. `GET /api/policies` — always first; establishes the current policy baseline
2. The primary entity endpoint (applications, licensees, etc.)
3. Supporting endpoints (bonds, insurance, violations, incidents, etc.)

Use `POST /api/sql` when:
- You need to cross-reference records that the REST endpoints do not join
- You need to filter or aggregate in ways the REST endpoints do not support
- The prompt explicitly suggests SQL access

For POST /api/sql, include the required authentication header from
environment_access.md.

### Step 5: Match Vocabulary to the Template

This is the most common failure point. Every task uses its own vocabulary
strings. The answer_template.json defines the exact set of allowed values.

**Rule**: The template's allowed_values list is exhaustive. Use only those
strings. Do not import code strings from other tasks, from the reference
files, or from your own reasoning.

When the reference file lists alternative names for the same concept (e.g.,
`bond_cancelled` vs `no_active_bond`, `CONTROL_SIGNAGE_CONFLICTING` vs
`control_signage_missing`), pick the one that appears in the template's
allowed_values. If neither appears, the concept may not apply to this task
schema.

### Step 6: Apply Domain Rules

With all data fetched and the template understood, apply the domain-specific
rules from the loaded reference file. The reference files contain:

- How to map data findings to deficiency codes
- How to assign determinations (APPROVE/HOLD/DENY or issue_restricted/request_follow_up/deny)
- How to derive required actions from deficiencies
- How to risk-tier each application or queue entry
- How to detect policy impact
- How to build monitoring plans and escalation triggers (liquor)
- How to rank queue entries and assign match confidence (alcohol renewal)

### Step 7: Build the Output

Assemble the JSON output in the exact shape of the answer template:

- **Sorting**: Follow the template's ordering rules precisely. When the
  template says "ascending lexical order" or "ascending by application_id",
  sort exactly that way. For matched_violation_ids, the template typically
  requires sorting by violation date ascending, then by violation_id
  ascending as a secondary sort.
- **Empty values**: Use `[]` for empty arrays, `""` for empty strings. Do
  not omit required keys even when no data applies.
- **No extras**: Do not add keys that are not in the template. Do not
  include prose, markdown, citations, or comments outside the JSON.
- **Summary consistency**: Build summary fields by tallying the detailed
  decisions you already made. Do not construct the summary independently —
  it must be internally consistent with the application-level or queue-level
  decisions.

### Step 8: Validate Before Returning

Before writing the final answer, check:

1. Every required top-level key is present
2. Every array has the correct length (the template may specify required_length)
3. Every enum value comes from the template's allowed_values
4. Array entries are sorted as specified
5. No duplicate entries in arrays that forbid duplicates
6. Summary counts match the detailed decisions
7. Date strings use YYYY-MM-DD format
8. No prose or markdown outside the JSON object

## Domain-Independent Rules

These apply across all three domain workflows.

### Risk Tiering Logic

Risk tiers follow a consistent pattern across domains:

- **high**: The application or licensee has a blocking condition (active
  suspension, unresolved serious complaint/violation, board-level concern) or
  has three or more distinct deficiency codes or violations. A DENY
  determination always implies high risk.
- **medium**: Deficiencies or violations exist but are fixable. HOLD
  determinations typically map to medium risk unless high triggers are
  present.
- **low**: No deficiencies or violations. APPROVE determinations map to low.

### Policy Impact Detection

Policy impact means the current policy baseline (from `/api/policies`) creates
a deficiency or review flag that would not have existed under prior rules.
Detect it by asking: would this application have been APPROVE or have fewer
deficiencies under the previous policy? Common signals:

- New endorsement requirements that the applicant does not meet
- Increased bond or insurance minimums
- New experience thresholds
- New inspection or documentation requirements

### Correspondence Review

When the template includes stale_or_unverified_correspondence_ids:

1. Fetch `/api/contractor/correspondence`
2. Identify correspondence records where the status is unverified, unresolved,
   or the response is past the expected reply window
3. List the exact correspondence IDs from the API response
4. Sort ascending

### Multiple Applications Per Batch

When the task lists multiple application IDs:

1. Process each application independently against all relevant endpoints
2. Do not assume one application's data applies to another
3. Order the output array by application_id ascending
4. Each application gets its own deficiency_codes and required_actions arrays

### SQL Strategy

When using POST /api/sql:

- Start with `SELECT *` queries to explore table schemas
- Use JOINs to cross-reference entities when REST endpoints do not connect them
- Filter by the specific application/license IDs from the prompt
- For boundary-date filtering in renewal tasks, use `WHERE violation_date <= 'YYYY-MM-DD'`
- Include the X-Task-Token header from environment_access.md on every POST /api/sql call

## Common Mistakes to Avoid

1. **Using code strings from the wrong vocabulary**: Train-001 and train-004
   are both contractor tasks but use different deficiency code strings.
   Always match the template.
2. **Missing the answer template**: The prompt summarizes the task but the
   template defines the exact output contract. Read it first.
3. **Building the summary before the details**: Construct application_decisions
   or queue entries first, then tally the summary. Never work backwards.
4. **Adding prose or commentary to the JSON output**: The output must be pure
   JSON matching the template shape exactly.
5. **Forgetting the auth header on POST /api/sql**: Check environment_access.md
   for the required X-Task-Token value.
6. **Overlooking policy impact**: Always read /api/policies and compare
   against what each application would need under prior rules.
7. **Skipping correspondence review**: When the template has
   stale_or_unverified_correspondence_ids, you must review correspondence
   records for every application in the batch.
