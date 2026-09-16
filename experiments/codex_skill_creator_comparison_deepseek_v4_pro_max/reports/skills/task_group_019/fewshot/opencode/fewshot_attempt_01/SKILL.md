---
name: licensing-review
description: Perform structured licensing eligibility reviews using a shared REST+SQL licensing environment. Use this skill whenever the task involves contractor license applications, liquor license transfers, alcohol renewal queues, or any batch/single-application eligibility decision that requires cross-referencing multiple API-sourced records (bonds, insurance, violations, inspections, incidents, site evidence, license history, policies, correspondence) and producing a strictly templated JSON output. Trigger on phrases like contractor application review, liquor license staff package, alcohol renewal screening, licensing eligibility, or any prompt that supplies a TASK_ENV_BASE_URL with licensing data endpoints and an answer template.
---

# Licensing Review

## Overview

This skill covers structured licensing eligibility reviews against a shared
task-environment data service. The review always follows the same skeleton:

1. Read the output template to lock in every required field, allowed code set,
   ordering rule, and enumeration.
2. Gather all relevant records from the environment's REST endpoints -- in
   parallel where possible -- and supplement with SQL when the prompt permits.
3. Cross-reference the records to identify each application's posture, classify
   deficiencies, map those to required corrective actions, and assess risk.
4. Assemble the final JSON strictly against the template. Never add prose,
   markdown, citations, or keys not shown in the template.

## Step-by-step workflow

### Step 1: Absorb the template first

Before fetching any data, read the `answer_template.json` provided in the
prompt. Pay attention to:

- The exact top-level keys (e.g. `application_decisions` + `summary`,
  `queue` + `summary`, or a flat staff-package object).
- Every allowed value in every enum. Do not invent codes; use only what the
  template lists.
- Ordering directives: *ascending by application_id*, *lexicographic*, *by
  date ascending*, *remove duplicates*.
- The rule that missing or non-applicable lists must be set to `[]`, never
  `null` or omitted.
- The number of expected items (e.g. "exactly 8", "target queue size 10").

Keep the template open while you work. Every key you write must be traceable
back to it.

### Step 2: Gather data from the environment

The prompt always provides a `<TASK_ENV_BASE_URL>` and lists the relevant GET
endpoints. Call them **in parallel** -- they are independent reads.

When the prompt mentions `POST /api/sql`, you may use it to run arbitrary
SQL queries against the environment's database. Always include the required
header:

```
X-Task-Token: licensing-review-019
```

Wait until the REST data lands before deciding whether SQL queries are needed.
Common reasons to reach for SQL:

- You need to filter a large dataset by a date boundary the REST endpoint
  cannot express (e.g. "violations before a stated cutoff date").
- A REST response is paginated or truncated and you need the full set.
- You want to join two data sources that the REST layer does not combine.

When you use SQL, prefer `SELECT` statements that project only the columns you
actually need. Start with a broad query to confirm the schema, then narrow.

Record every endpoint call in your execution so you can later verify that
nothing was skipped.

### Step 3: Cross-reference the data

This is the core reasoning step and it varies by domain. The general approach:

**Identify every target.** Whether the task lists eight application IDs, one
license number, or a range of licensees, start by enumerating the targets
exactly as the prompt names them. Do not add or drop targets.

**Resolve identity.** When a data source uses a different identifier (e.g. a
violation record keyed by address rather than license number), match targets
by the strongest available key: license number first, then facility name,
then street address. Flag uncertain matches in the output when the template
has a `match_confidence` field.

**Classify posture.** For each target, decide its disposition using the
template's determination enum. The reasoning is:

- **APPROVE / issue_restricted**: No material deficiencies in financial
  coverage, endorsements, experience, compliance history, or site evidence.
  All required documents are current and verified.
- **HOLD / request_follow_up**: One or more addressable deficiencies exist
  but none are disqualifying. The applicant can fix them before the next
  review cycle.
- **DENY / deny**: A hard blocker exists -- active suspension, unresolved
  serious violation/complaint, expired coverage that cannot be backdated,
  or a pattern that makes approval unsafe.

**Map deficiencies to actions.** For each deficiency you find, derive the
corresponding required action from the template's `deficiency_codes` and
`required_actions` lists. The mapping is domain-specific (see the reference
files), but the principle is: every deficiency you assert must be grounded in
actual data, and every action must match a deficiency you've cited.

**Assess risk.** Risk derives from the combination of deficiencies and
qualitative flags:

- `high`: active suspension, board-level complaint, safety inspection failure,
  multiple expired coverages, or a serious violation overlapping the review
  window.
- `medium`: one or two addressable deficiencies (bond shortfall, expired
  insurance, pending endorsement, single safety recheck) with no suspension.
- `low`: zero deficiencies, all documentation verified and current.

**Check policy impact.** If the task provides a `/api/policies` endpoint, read
it and compare current policy requirements against each application's data.
Mark `policy_impacted: true` when a deficiency would not exist under the prior
baseline or when a current policy standard creates a material review flag that
would not have applied before. If the prompt provides no policy endpoint or
the endpoint returns nothing actionable, keep `policy_impacted: false` for all
non-impacted entries and `true` only where you can demonstrate the linkage.

### Step 4: Build the JSON output

Follow the template precisely:

- **Ordering.** Sort list items as the template directs. Application IDs
  lexicographically, violation IDs by date-then-id, codes alphabetically.
- **Empty lists.** When no codes or IDs apply, write `[]`. Never `null`,
  never omit the key.
- **No extra keys.** The template defines the schema; do not add fields.
- **No prose.** The output is raw JSON. No markdown fences, no commentary,
  no trailing explanation.

Before finalizing, re-read the template and verify every required key is
present, every list has the correct length, and every enum value is from the
allowed set.

---

## Reference files

When the task domain is clear from the prompt, read the relevant reference:

- [api-guide.md](references/api-guide.md) -- Endpoint details, SQL patterns,
  and the shared authentication token.
- [decision-patterns.md](references/decision-patterns.md) -- Domain-specific
  heuristics for contractor batches, liquor staff packages, and alcohol
  renewal queues.

Only read a reference file when you need its specific guidance. The workflow
above is sufficient for many tasks on its own.
