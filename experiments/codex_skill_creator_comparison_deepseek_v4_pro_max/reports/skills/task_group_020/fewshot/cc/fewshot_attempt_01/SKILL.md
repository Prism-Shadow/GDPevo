---
name: deal-workbench
description: >
  Use when analyzing M&A deals through a running deal workbench REST API.
  Triggers on any prompt mentioning a deal workbench at <TASK_ENV_BASE_URL>,
  deal IDs like PRJ_XXXXXX, seller or buyer APA/SPA review, committee
  escalation packages, transition reviews, deviation matrices, or workbench
  API routes like /api/deals, /api/playbooks, /api/policies, /api/query.
  Always use this skill when the task involves comparing draft deal terms
  against playbook or policy rules, producing structured JSON deal-analysis
  outputs, or gathering workbench data for M&A counsel deliverables.
---

# M&A Deal Workbench Skill

Use a running M&A deal workbench REST API to produce structured deal-analysis
outputs: issue registers, closing and economics packages, committee escalation
memos, transition reviews, and deviation matrices.

## Core Workflow

Every task follows the same sequence. Do not skip steps.

### Step 1: Read the Answer Template

The prompt includes an `input/payloads/answer_template.json`. Read it first,
before fetching any workbench data. The template defines:

- The exact output JSON shape, including every required top-level field
- Allowed enum values for every classification field
- Units (currency, percent_points, months) and rounding rules
- Stable identifier lists for issues, terms, or redlines

The template is authoritative for output structure. Do not invent fields it
does not define. Do not omit fields it marks required.

### Step 2: Gather All Relevant Workbench Data

Fetch data in parallel where possible. The mandatory baseline for nearly every
task starts with three fetches:

1. Deal record: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>`
2. Draft terms: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/terms`
3. Rules: `GET <TASK_ENV_BASE_URL>/api/playbooks/<playbook_id>/rules` or
   `GET <TASK_ENV_BASE_URL>/api/policies/<policy_id>/thresholds`

Then fetch supporting records based on what the template demands:

- Consents, material contracts, regulatory, employees, risk estimates,
  benchmarks, documents, notes, cap table, diligence findings

If the prompt mentions read-only SQL, send:

```
POST <TASK_ENV_BASE_URL>/api/query
Body: {"token": "deal-workbench-readonly", "sql": "<SELECT statement>"}
```

Read `references/api.md` for the full endpoint reference including response
shapes, field names, and direct-route alternatives.

### Step 3: Run the Analysis

Apply the playbook rules or policy thresholds against the draft terms. See
Analysis Methodology below for the detailed comparison logic.

### Step 4: Produce the Output JSON

Return only the JSON object conforming to the answer template. No markdown
fences, no explanatory prose, no preamble. The output must parse as JSON
directly.

## Analysis Methodology

### Playbook-Driven Issue Classification

For each playbook rule in scope:

1. **Find the matching draft term.** Search the terms from
   `/api/deals/<deal_id>/terms` for one that addresses the same subject as the
   playbook rule. Match by category or clause subject matter, not by exact
   term ID. Record the draft term's ID in `source_term_ids`. If no draft term
   addresses the subject, `source_term_ids` is an empty array `[]`.

2. **Classify the issue status:**
   - `missing_required_term` — draft has no term for this subject but the
     playbook requires one. Recommended action: `add`.
   - `draft_exceeds_playbook` — draft term exists but its value is worse for
     the client than the playbook fallback. Recommended action: `revise`.
   - `draft_below_playbook` — draft term exists but is weaker than the
     playbook requires (e.g., missing reverse break fee, indemnity cap too
     low for buyer protection). Recommended action: `revise` or `add`.
   - `in_policy` — draft is within acceptable bounds (between preferred and
     fallback, or matching required values).
   - `out_of_policy` — draft violates a committee policy threshold. Used in
     escalation packages; in playbook reviews, `draft_exceeds_playbook` is
     the equivalent.

3. **Assign risk rating:**
   - `HIGH` — affects closing certainty, creates significant dollar exposure,
     or is a deal-blocker
   - `MEDIUM` — material but manageable issue
   - `LOW` — housekeeping item or negligible dollar impact

4. **Assign recommended_action:**
   - `delete` — remove the term entirely
   - `add` — insert a missing required term
   - `revise` — adjust an existing term toward the playbook position
   - `accept` — draft is acceptable as-is
   - `approve` / `approve_with_conditions` / `reject` — committee decisions
   - `escalate` — needs higher-level decision

5. **Map to business_outcome** when the template requires it. Assign each
   issue to the primary business outcome it affects.

### Quantitative Calculations

**Dollar amounts from percentages:** Multiply the percentage (as a decimal) by
the headline purchase price from the deal record, unless a source record
explicitly states a different basis.

Example: 10% escrow on a $400M deal = 0.10 × 400,000,000 = 40,000,000.

**Delta calculations:** Subtract the draft value from the required position
value. Use the fallback value as the target when computing deltas unless the
template field name explicitly references the preferred position.

**Rounding:** Currency amounts to integer dollars (no decimal places).
Percentages to the decimal places specified in the answer template (typically
two for percent points, one for holder percentages, four for fully-diluted
percentages). Months to integers.

**Null vs. zero:** Use `null` when a field does not apply to an issue. Use `0`
only when zero is the actual value (e.g., a draft with no reverse break fee has
`draft_percent: 0.0` and `draft_amount_dollars: 0`). Use `[]` not `null` for
array fields with no entries.

### Priority Ordering

Order issues from highest negotiation priority to lowest. The typical order:

1. Closing certainty (financing conditions, reverse break fees, HSR/regulatory
   conditions, consent closing conditions)
2. Economic protection (escrow, indemnity caps, baskets, survival periods,
   materiality scrapes, NWC adjustments)
3. Operational and people (employee continuity, transition services,
   restrictive covenants)
4. Structural housekeeping (tax allocation, governing law, forum selection)

Within each tier, sort by dollar exposure: larger impact first.

### Handling Missing Terms

When a playbook rule requires a term absent from the draft:

- Set `issue_status` to `missing_required_term`
- Set `source_term_ids` to `[]`
- Set `recommended_action` to `add`
- For quantitative fields: set draft values to the appropriate null/zero based
  on what "absent" means. A missing escrow provision has `draft_percent: null`;
  a missing reverse break fee has `draft_percent: 0.0` and
  `draft_amount_dollars: 0`
- Fill required position fields from the playbook

### Policy-Driven Escalation (Committee Packages)

When the task involves committee escalation against a policy rather than a
playbook:

1. Compare each draft term against its corresponding policy threshold. A
   policy defines hard numeric or structural limits.
2. Include only terms that are `out_of_policy` in the escalation list. Do not
   include in-policy terms in the main escalation array.
3. List excluded in-policy terms explicitly in the aggregate summary so the
   committee knows they were reviewed.
4. Include benchmark comparisons when the workbench provides benchmark data.
   Classify the draft's position: `at_or_below_median`,
   `between_median_and_upper_quartile`, `at_upper_quartile`, or
   `above_upper_quartile`. Use `not_applicable` when no benchmark exists for
   the category.
5. Every recommendation must include `required_conditions` — specific,
   actionable steps to bring the term into compliance or mitigate the risk.

## Output Conventions

### JSON-Only Output

Return only the JSON object. No markdown fences, no explanatory prose, no
preamble. The output must be parseable as JSON directly. The evaluator expects
the raw JSON and will reject wrapped output.

### Field Completeness

Every field declared as required in the answer template must appear in the
output, even when its value is `null`, `0`, `[]`, or `false`. Never omit a
required field.

### Stable Identifiers

Use exact identifiers from workbench API responses. Never invent IDs. The
conventions are:
- Term IDs: `TERM_PRJ_XXXXXX_NN`
- Consent IDs: `CNS_PRJ_XXXXXX_NN`
- Material contract IDs: `MAT_PRJ_XXXXXX_NN`
- Employee IDs: `EMP_PRJ_XXXXXX_NN`
- Risk estimate IDs: `RSK_PRJ_XXXXXX_NN`
- Finding IDs: `FND_PRJ_XXXXXX_NN`
- Document IDs: `DOC_PRJ_XXXXXX_NN`

### Enum Values

Use exactly the enum strings defined in the answer template. Case-sensitive.
If the template says `risk_rating` values are `LOW`, `MEDIUM`, `HIGH`, never
substitute `low`, `medium`, or `high`.

## Task-Type Guidance

The workbench supports several deliverable types. When the prompt and template
indicate one of these, follow the specific shape described below.

### Issue Register (APA/SPA Review)

Compare the counterparty's draft against the client's playbook. Flag every
material deviation. Output has an `issue_register` array with one entry per
material issue, a `priority_order` array ordering issues by negotiation
priority, and `summary_metrics` with aggregated counts and dollar exposures.
Each issue includes a `required_position_code` that summarizes the client's ask
in a short snake_case string.

### Closing and Economics Package

Provide the deal team with a complete picture of economics, closing conditions,
covenants, and readiness. Output has an `economics` section with holder-level
consideration allocation (for stock deals), `closing_conditions` from consents
and material contracts, `covenants` for employment and restrictive covenants,
`regulatory` for HSR status, and `closing_readiness` with overall status,
blocker lists, and tradeable issues.

### Committee Escalation Memo

Escalate only the out-of-policy terms that need committee approval. Output has
a `memo` header with client, project, policy, and date metadata, an
`escalation_terms` array with only the violating terms (each with draft_metric,
policy_metric, delta, benchmark, exposure, recommendation, and
required_conditions), and an `aggregate_summary` that explicitly lists excluded
in-policy terms.

### Transition Review (Carveout APA)

Focus on separation and transition terms. Output has `transition_issues` for
each gap in the transition plan, `required_redlines` linking each redline to
its parent issue with `must_have_terms` detailing the exact position, and
`operational_risk` with quantified exposures and priority order. Covers TSA
scope/duration/fees, IP/domain transition, employee continuity, tax allocation,
transfer tax, governing law, and closing deadline.

### Deviation Matrix

Map every buyer position against the draft. Output has a `position_matrix` with
one row per material issue area (each with a `final_position` summarizing the
buyer's bottom line), a `closing_blockers` array listing every item that must
be resolved before closing, and `risk_totals` aggregating all quantified
exposures. Status fields like `basket_status`, `knowledge_qualifier_status`,
`escrow_agent_status`, `release_status` use `not_found_in_current_records` when
the draft omits the concept entirely.

## Common Pitfalls

- **Using zero instead of null:** When a field is not applicable, use `null`
  not `0`. A $0 reverse break fee is a real position; `null` means the concept
  is absent from the draft.
- **Forgetting the template:** Read it before gathering data so you know which
  fields matter and which API endpoints you need.
- **Mixing preferred and fallback:** Preferred is the ideal; fallback is the
  walk-away floor. Deltas usually reference fallback unless the field says
  otherwise.
- **Wrong rounding:** Integer dollars means no decimal places. Percent points
  means the percentage value (e.g., 14.0 means 14%, not 0.14).
- **Including in-policy terms in escalation:** Committee escalations only list
  out-of-policy terms; in-policy terms go in the exclusion list.
- **Inventing identifiers:** Only use IDs that appear in workbench responses.
  Never fabricate term, consent, or employee IDs.

## API Reference

For the complete endpoint catalog with response shapes, field names, and usage
notes, read `references/api.md` when you need detail beyond the workflow above.
Key endpoints are summarized in Step 2; the reference covers every endpoint,
including direct-route alternatives and the SQL query interface.
