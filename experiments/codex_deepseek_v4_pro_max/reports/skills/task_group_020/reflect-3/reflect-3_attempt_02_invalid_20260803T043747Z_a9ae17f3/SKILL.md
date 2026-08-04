## When to Use

Use this skill whenever the task involves reviewing an M&A deal, preparing a negotiation memo, building an issue register, assembling an economics package, creating a committee escalation deck, or producing any structured deliverable from the M&A Deal Workbench. The workbench surfaces deal records, draft terms, playbook rules, policy thresholds, cap tables, employee records, consents, regulatory filings, benchmarks, risk estimates, diligence findings, material contracts, and notes through consistent REST API routes and a read‑only SQL endpoint.

## Entry Points

### Gather All Available Records for a Deal

Start by fetching the deal header and every linked collection. Use the deal record `links` block to discover available sub‑resources. At minimum pull:

- `/api/deals/{deal_id}`
- `/api/deals/{deal_id}/terms`
- `/api/deals/{deal_id}/benchmarks`
- `/api/deals/{deal_id}/risk-estimates`
- `/api/deals/{deal_id}/regulatory`
- `/api/deals/{deal_id}/consents`
- `/api/deals/{deal_id}/employees`
- `/api/deals/{deal_id}/material-contracts`
- `/api/deals/{deal_id}/cap-table`
- `/api/deals/{deal_id}/diligence-findings`
- `/api/deals/{deal_id}/notes`

If the deal references a playbook, pull `/api/playbooks/{playbook_id}/rules`. If it references a policy, pull `/api/policies/{policy_id}/thresholds`.

### Cross‑Table Checks with SQL

When available, use `POST /api/query` with `{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}` to validate counts, inspect schemas, or join across tables. Explore available tables with `SELECT name FROM sqlite_master WHERE type='table'`.

### List All Deals or Resources

- `GET /api/deals` returns every deal in the workbench (useful for context or finding related projects).
- `GET /api/playbooks` and `GET /api/policies` list available playbooks and policies.

## Core Analytical Framework

### 1. Compare Draft Terms Against Playbook or Policy Rules

For each draft term, find the corresponding playbook rule (by `category`) or policy threshold (by `category`). Determine whether the draft value:

- **Exceeds** a seller‑protective limit → `draft_exceeds_playbook`
- **Falls below** a buyer‑protective floor → `draft_below_playbook`
- **Violates** a boolean or structural policy requirement → `out_of_policy`
- **Is absent** but the playbook/policy requires it → `missing_required_term`
- **Matches** the acceptable range → `in_policy`

Pay close attention to the `basis` field on every term and rule. A term keyed to `purchase price` uses the deal's headline purchase price; a term keyed to `enterprise value` may use a different denominator. Use the deal's `headline_value` for purchase‑price calculations unless a source explicitly states a different basis.

### 2. Identify Missing Terms from Surrounding Data

When a term is absent from the draft but the surrounding deal data shows it is needed, flag it as `missing_required_term`. Evidence can come from:

- Employee records showing service‑credit requirements or PTO liability
- Consent records showing required closing consents
- Regulatory records showing HSR or other filing obligations
- Material contracts showing consent or assignment triggers
- Diligence findings exposing unmitigated risk
- Benchmarks showing market‑standard provisions that are absent

### 3. Cross‑Reference with Benchmarks and Risk Estimates

- **Benchmarks**: Compare numeric draft values (e.g., cap percent, survival months, fee percent) against benchmark quartiles to contextualize the negotiation position.
- **Risk estimates**: Map each issue to the relevant risk category (closing certainty, indemnity leakage, transition disruption) and capture the low/high exposure range.

### 4. Handle Staleness and Distractors

Some terms carry a `staleness_flag` of `"stale"`. Exclude stale terms from escalation registers, issue lists, and active negotiation matrices unless the instructions explicitly require them. Similarly, exclude in‑policy terms and non‑committee distractor categories when building committee escalation packages.

## Calculation Conventions

- **Dollar amounts**: Compute from the deal's `headline_value` (purchase price) unless a term's `basis` field or playbook rule explicitly names a different base (e.g., `enterprise value`, `upfront_cash`). All dollar fields must be integers.
- **Percentages**: Render as decimal numbers (e.g., `12.50` for 12.5%). Follow the precision requested by the answer template (typically two decimal places for percent points, four for holder percentages, one for other contexts).
- **Month values**: Always integers.
- **Delta calculations**: For `draft_exceeds_playbook`, delta = draft − fallback. For `draft_below_playbook`, delta = fallback − draft. The result should be a positive integer in dollars or months.

## Output Discipline

### Match the Answer Template Exactly

Every task supplies an `input/payloads/answer_template.json`. Treat it as the authoritative JSON schema. The template defines:

- The exact top‑level fields required
- The allowed enum values for every constrained field
- The nested object structure and field names
- The precision and unit conventions

Do not invent field names, add extra wrapper objects, or change the hierarchy. If the template shows `"field": null`, replace `null` with the correct value but keep the field present. If the template provides an enum via `"value1 | value2"`, choose exactly one of those strings.

### Validate Before Submitting

- Every issue or term object must include every field listed in the template, even when the value is `null`, `0`, `false`, or an empty array.
- `issue_id` and `term_id` values must be stable, unique, and sourced from the workbench records.
- Summary metrics must be internally consistent with the register (e.g., counts match the array lengths, totals sum correctly).
- Priority orders and negotiation sequences should rank by risk and financial impact: highest risk and largest dollar exposure first.

### No Narrative Outside JSON

Return only the JSON answer object. Do not include explanatory prose, Markdown fences, or commentary before or after the JSON.

## Deal‑Side Awareness

- **Seller‑side tasks**: The playbook typically sets ceilings (caps, escrow maximums, survival limits). Protect against buyer drafts that exceed those ceilings.
- **Buyer‑side tasks**: The playbook typically sets floors (minimum caps, minimum survival periods, required protections). Push back against seller drafts that fall short.
- **Committee escalation**: Policy thresholds define hard limits. Any term breaching a restricted threshold must be escalated regardless of negotiation posture.

## API Reference Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/deals` | List all deals |
| GET | `/api/deals/{id}` | Deal header and links |
| GET | `/api/deals/{id}/terms` | Current draft terms |
| GET | `/api/deals/{id}/cap-table` | Capitalization table |
| GET | `/api/deals/{id}/consents` | Third‑party consents |
| GET | `/api/deals/{id}/employees` | Employee records |
| GET | `/api/deals/{id}/material-contracts` | Material contracts |
| GET | `/api/deals/{id}/regulatory` | Regulatory status |
| GET | `/api/deals/{id}/benchmarks` | Market benchmarks |
| GET | `/api/deals/{id}/risk-estimates` | Risk exposure ranges |
| GET | `/api/deals/{id}/diligence-findings` | Diligence findings |
| GET | `/api/deals/{id}/notes` | Deal team notes |
| GET | `/api/deals/{id}/documents` | Documents index |
| GET | `/api/playbooks` | List playbooks |
| GET | `/api/playbooks/{id}/rules` | Playbook rules |
| GET | `/api/policies` | List policies |
| GET | `/api/policies/{id}/thresholds` | Policy thresholds |
| POST | `/api/query` | Read‑only SQL (token: `deal-workbench-readonly`) |

## Workflow Checklist

1. Read the task prompt and the answer template side by side.
2. Fetch the deal header; note `deal_id`, `client_side`, `playbook_id`, `policy_id`, `headline_value`, and `transaction_type`.
3. Pull all linked sub‑resources. Use SQL for cross‑checks when needed.
4. If a playbook applies, load its rules. If a policy applies, load its thresholds.
5. For each draft term, find the matching playbook rule or policy threshold. Determine issue status, risk rating, and quantify the deviation.
6. Scan employee, consent, regulatory, contract, and diligence records for missing required terms.
7. Populate the answer template field by field, using exact enum values and following the template's precision and unit rules.
8. Compute summary metrics last, deriving them from the issue register data.
9. Validate internal consistency, then return only the JSON.
