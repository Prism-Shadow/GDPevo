---
name: licensing-review
description: "Structured licensing review for state licensing board operations. Covers contractor application batch eligibility review (bond, insurance, endorsement, experience, violation, inspection, correspondence analysis), restricted liquor license staff packages (risk coverage, verification gaps, standard obligations, location-specific controls, 90-day monitoring plans, escalation triggers), and alcohol license renewal manual-review queues (violation matching, boundary-date filtering, risk-tier ranking, next-step routing). Use when the task involves contractor licensing decisions, liquor license transfer or issuance review, alcohol renewal screening, or any structured licensing board workflow that requires REST API data fetching from board endpoints and structured JSON output with determination codes, risk tiers, and summary statistics."
---

# Licensing Review

Structured licensing board operations covering three task families: contractor
batch eligibility, restricted liquor staff packages, and alcohol renewal
queues. All tasks consume data from a shared REST API environment and produce
structured JSON answers.

## Workflow Decision Tree

1. Read the task prompt, note the target application/license IDs, and locate
   the `answer_template.json` in `input/payloads/`.

2. Identify the task family:
   - **Contractor batch** (prompt mentions contractor/applications/bonds and
     multiple C- IDs): read [contractor.md](references/contractor.md).
   - **Liquor staff package** (prompt mentions liquor/applications and a single
     L- ID with a LOC- ID): read [liquor.md](references/liquor.md).
   - **Alcohol renewal queue** (prompt mentions alcohol/licensees and a ranked
     queue): read [alcohol.md](references/alcohol.md).

3. Fetch data using the fetch_data.py script or direct HTTP calls.

4. Build the answer: start from the answer_template.json schema, populate each
   field from the fetched data using the domain reference, and output only the
   JSON object.

## Data Fetching

### Automated script (recommended)

```
python scripts/fetch_data.py --base-url $TASK_ENV_BASE_URL --token $TASK_TOKEN --domain <domain>
```

Valid domains: `all`, `contractor`, `liquor`, `alcohol`, `renewal`.

The script writes one JSON object to stdout with keys like
`api_contractor_applications`, `api_liquor_incidents`, etc.

### Manual HTTP calls

When the script is not available or when fine-grained control is needed, use
curl:

```
curl -s -H "X-Task-Token: <token>" "<base_url>/api/contractor/applications"
```

### SQL endpoint

Use `POST /api/sql` when REST endpoints do not return records in a directly
joinable format. Send a JSON body with a `query` key, `Content-Type:
application/json`, and the `X-Task-Token` header.

## Domain References

- [contractor.md](references/contractor.md) - Contractor batch eligibility
  review. Deficiency codes, required actions, bond/insurance/endorsement
  mappings, policy impact rules, summary construction.
- [liquor.md](references/liquor.md) - Restricted liquor license staff package.
  Risk coverage, verification gaps, standard obligations vs. location-specific
  controls, 90-day monitoring plan, escalation triggers.
- [alcohol.md](references/alcohol.md) - Alcohol license renewal manual-review
  queue. Violation matching, boundary-date filtering, ranking methodology, risk
  tiers, next-step routing, summary construction.

## Answer Construction

### Start from the template

The `answer_template.json` in `input/payloads/` is authoritative for the
required keys, allowed enum values, and ordering rules. Build the answer by
populating each field from the fetched data.

### Ordering conventions

- Application/decision lists: sort by ID ascending (lexical).
- Code arrays within a decision: sort alphabetically.
- Summary ID lists: sort lexically ascending.
- Queue entries: ordered by rank ascending (1, 2, ..., N).
- Violation ID lists within queue entries: sort by date ascending, then ID
  ascending.
- First 90-day plan: order by intended operational sequence, not alphabetically.

### Empty values

Use empty arrays (`[]`) when no codes or IDs apply to a field. Use integers for
counts.

### Dates

Use YYYY-MM-DD format throughout.

## Common Patterns

### Policy impact detection

When `/api/policies` is available, compare the current policy baseline with the
prior baseline embedded in policy records. If a deficiency exists only because
a standard was recently raised (minimum bond, coverage threshold, new
endorsement requirement), flag `policy_impacted: true`.

### Stale correspondence identification

Read the correspondence endpoint. Flag any record where a status field (e.g.,
`status`, `verification_status`, `state`) indicates stale, unverified, pending,
or requires follow-up.

### Same-premises basis

For liquor tasks, check whether the target location shares physical premises
with an existing licensed entity. Look for shared-premises indicators in the
site evidence, application notes, or privilege records.

### Post-boundary violation exclusion

For alcohol renewal queues, filter violations strictly by violation_date before
or on the boundary date. List all excluded (post-boundary) violation IDs in the
summary.
