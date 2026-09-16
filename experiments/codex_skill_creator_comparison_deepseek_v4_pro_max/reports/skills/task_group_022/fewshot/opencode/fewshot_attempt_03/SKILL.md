---
name: atlas-ops-analyst
description: >-
  Analyze the Atlas Commerce Operations database through its authenticated REST
  API. Use this skill whenever the task involves Atlas data, Commerce
  Operations analytics, fulfillment metrics, refund reconciliation, carrier
  quality review, warehouse productivity, support health analysis, or any
  business-operations task that references a TASK_ENV_BASE_URL with
  /api/schema and /api/sql endpoints. This skill covers the complete workflow:
  reading the API schema and data dictionary, translating business definitions
  into SQL, building multi-step analytical queries, applying tiered
  classification rules, and writing results to an answer template.
---

# Atlas Commerce Operations Analyst

Analyze business data from an Atlas Commerce Operations workplace exposed
through a REST API. The API provides schema discovery, data-dictionary
lookup, read-only SQL, and (when the task scope demands it) a transactional
SQL endpoint with an audit log. Every task in this domain follows the same
structural pattern: a business narrative, one or more payload files containing
the analytical definitions, and a strict answer template.

## Core workflow

Follow this sequence for every task; do not skip steps or change the order.

### 1. Discover the schema

Start by calling the two read-only discovery endpoints so you understand what
tables and columns exist before you write any SQL.

    GET {task_env_base_url}/api/schema
    GET {task_env_base_url}/api/data-dictionary
    Authorization: Bearer atlas-ops-token-022

The schema response lists every table and column name with types. The data
dictionary adds business-facing descriptions, enum values, and relationships.
Use these to verify column names before embedding them in queries -- the
task's business definitions use human vocabulary that may not match the
physical column names exactly.

If column names differ from what the request facts suggest, map the business
terms to the physical columns you found in the schema. Document those mappings
in your reasoning so you stay consistent across queries.

### 2. Read the request facts and answer template

Every task ships with payload files. Read **all** of them before writing a
single query:

- The **request facts** JSON (named something like `*_request.json`) contains
  the business scope, cohort definitions, metric formulas, classification
  rules, rounding policies, and ranking orders. This is your source of truth
  for what to compute.
- The **answer template** JSON (`answer_template.json`) defines the exact
  output schema -- required fields, types, constraints, array ordering, and
  enum values. Every field you produce must satisfy these constraints.

Never infer business rules from the answer template alone. Always cross-check
against the request facts.

### 3. Translate business definitions into SQL building blocks

The request facts describe operations in plain language. Translate each
definition into a concrete query fragment before assembling the full query.
Read [references/patterns.md](references/patterns.md) for the recurring
translation patterns; the patterns cover:

- Cohort eligibility (date windows, tier filters, status conditions)
- Derived state classification (complete/on-time/exception)
- Rate computation with precision control
- Regional roll-ups and ranking
- FX conversion with daily rate tables
- Tiered status/risk classification
- Median computation
- Pre/post correction comparison
- Controlled transactional updates with audit verification

When the request facts define a classification rule (e.g. "an order is
complete only when..."), build the corresponding CASE expression and verify it
against every edge case the definition mentions. If the definition says "every
shipment" or "at least one", make sure your query handles empty sets, NULLs,
and boundary conditions correctly.

### 4. Build queries incrementally

Do not attempt one giant query. Break the problem into staged queries and
validate each stage:

1. **Count and verify eligibility**: Write the base query that filters the
   cohort. Count the rows and spot-check a few records against the business
   rules before proceeding.
2. **Add derived columns**: Layer in CASE expressions for completion status,
   breach flags, or exception markers. Verify with COUNT of each category.
3. **Aggregate**: Compute rates, sums, and groupings. Sanity-check that counts
   are internally consistent (e.g. complete + incomplete = total).
4. **Rank and order**: Apply the ranking rules from the request facts. Confirm
   tie-breakers match the documented order.
5. **Classify**: Apply tiered status/risk rules. Test boundary values to make
   sure thresholds are handled correctly.

For transactional tasks (data correction): read
[references/patterns.md](references/patterns.md) for the safe two-phase
approach -- pre-check, apply, verify post-state -- and always use
`POST /api/sql/transaction` for the mutation.

### 5. Round and format exactly as specified

The request facts define rounding and precision rules. Some tasks round only
final reported rates; others round intermediate values. Read the rounding
policy carefully and apply it at the right stage.

The answer template's JSON Schema constraints (e.g. `multipleOf: 0.0001`,
`precision: 2`) are non-negotiable. Validate every numeric field against its
schema before writing.

### 6. Assemble and write answer.json

Collect every computed value, populate the answer template structure, and
write `answer.json`. The output must:

- Contain exactly the fields in `required` -- no extras, no omissions
- Satisfy every `type`, `minimum`, `maximum`, `multipleOf`, `enum`, `pattern`,
  `minItems`, `maxItems`, and `uniqueItems` constraint
- Use the exact key and value casing from the template (camelCase vs
  snake_case matters)
- Contain no commentary, markdown fences, or explanatory text outside the JSON

Before writing, re-read the template's top-level constraints. Some templates
forbid arrays entirely (`"x-list-ordering"`), others require specific array
lengths, and some specify ordering rules you must follow.

## API reference

All endpoints, authentication, and request formats are documented in
[references/api-guide.md](references/api-guide.md). Read it when you need the
exact curl commands or response formats.

## Common mistakes

These are the traps that most frequently produce wrong answers:

- **Proceeding without reading the schema first.** Column names in the
  database rarely match the business vocabulary in the request facts exactly.
  Always map them.
- **Misinterpreting date-window boundaries.** The request facts state whether
  bounds are inclusive (`"boundary": "inclusive"` or `"inclusive": true`). Use
  `>=` and `<=` only when confirmed; otherwise default to the semantics in the
  facts.
- **Computing rates with the wrong denominator.** The request facts explicitly
  define denominators (e.g. "all eligible orders" vs "completed orders").
  When in doubt, re-read the definition.
- **Rounding intermediate values when the policy says "round only final."**
  Carry full precision through intermediate steps, then round at the end.
- **Mishandling NULLs in CASE expressions.** A shipment with no promised date
  should not satisfy a "delivered after promise" condition. Use explicit NULL
  guards.
- **Violating answer-template ordering rules.** When the template says "sorted
  ascending" or "ordered by X descending, then Y ascending", use explicit
  ORDER BY with the exact columns.
- **Changing data without the transactional endpoint.** For correction tasks,
  only `POST /api/sql/transaction` performs controlled writes. Do not attempt
  writes through the read-only SQL endpoint.
- **Overlooking the "correction applies exactly one row" constraint.** The
  request facts typically require exactly one business row to change. Verify
  this pre- and post-transaction.
