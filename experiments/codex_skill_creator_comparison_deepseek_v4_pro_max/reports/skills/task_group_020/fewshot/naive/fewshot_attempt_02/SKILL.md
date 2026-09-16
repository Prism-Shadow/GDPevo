---
name: deal-workbench
description: Navigate the M&A deal workbench API to analyze purchase agreements, compare terms against playbooks and policies, and produce structured deal reports including issue registers, closing packages, escalation memos, transition reviews, and deviation matrices.
---

# Deal Workbench Skill

Use the M&A deal workbench REST API to gather deal records, draft terms, playbook rules, policy thresholds, risk estimates, employee data, consents, material contracts, regulatory facts, cap tables, benchmarks, diligence findings, and deal notes, then produce structured JSON reports for M&A deal analysis.

## Environment

The workbench runs at a base URL provided in the task prompt as `<TASK_ENV_BASE_URL>`. Substitute that URL in all API calls. Unless the prompt specifies a different token, use `deal-workbench-readonly` for the read-only SQL endpoint.

## API Reference

All GET endpoints return JSON. Detailed reference is in [reference/api_surface.md](reference/api_surface.md). Key endpoints:

| Endpoint                                    | Purpose                                              |
| ------------------------------------------- | ---------------------------------------------------- |
| `/api/deals/<id>`                           | Deal metadata, headline value, parties, status       |
| `/api/deals/<id>/terms`                     | Current draft terms with term IDs and values         |
| `/api/deals/<id>/documents`                 | Deal documents (ancillaries, disclosure schedules)   |
| `/api/deals/<id>/benchmarks`                | Market data for term comparison                      |
| `/api/deals/<id>/risk-estimates`            | Modeled risk amounts (low/high), risk category IDs   |
| `/api/deals/<id>/cap-table`                 | Holder breakdowns, share counts, security classes    |
| `/api/deals/<id>/consents`                  | Third-party consents, approval requirements          |
| `/api/deals/<id>/employees`                 | Employee counts, PTO liabilities, service credit     |
| `/api/deals/<id>/material-contracts`        | Key contracts, annual revenues, consent triggers     |
| `/api/deals/<id>/regulatory`                | HSR status, thresholds, filing requirements          |
| `/api/deals/<id>/diligence-findings`        | Findings for NWC, special indemnity, privacy         |
| `/api/deals/<id>/notes`                     | Counsel notes, negotiation context                   |
| `/api/playbooks`                            | List available playbooks                             |
| `/api/playbooks/<id>/rules`                 | Playbook rules: preferred/fallback values per term   |
| `/api/policies`                             | List available policies                              |
| `/api/policies/<id>/thresholds`             | Committee policy thresholds                          |
| `/api/search?q=<text>`                      | Cross-deal search                                    |
| POST `/api/query`                           | Read-only SQL with token `deal-workbench-readonly`   |

### SQL Usage

POST to `/api/query` with JSON body `{"token": "deal-workbench-readonly", "query": "<SQL>"}`. Use for cross-table checks or when a single GET endpoint would miss related records. Prefer GET endpoints first and fall back to SQL when relationships are not surfaced by the REST API.

## General Methodology

### Step 1: Gather the deal baseline

Fetch the deal record, draft terms, the applicable playbook or policy, and risk estimates first. These four sources establish the analytical baseline:

- Deal record gives headline value, parties, deal structure (stock vs asset), and status.
- Draft terms are the baseline from which every deviation is measured.
- Playbook rules (for position work) or policy thresholds (for escalation work) define the target.
- Risk estimates attach dollar ranges to specific risk IDs.

### Step 2: Pull supporting records based on task scope

| If the task involves                  | Also fetch                                                                    |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| Employee terms, PTO, service credit   | `/api/deals/<id>/employees`                                                   |
| Closing consents, third-party risk    | `/api/deals/<id>/consents`, `/api/deals/<id>/material-contracts`              |
| HSR, regulatory conditions            | `/api/deals/<id>/regulatory`                                                  |
| Economics, holder allocation          | `/api/deals/<id>/cap-table`                                                   |
| Benchmarks for market comparison      | `/api/deals/<id>/benchmarks`                                                  |
| Diligence findings (NWC, privacy)     | `/api/deals/<id>/diligence-findings`                                          |
| Transition/Tax/IP carveout terms      | `/api/deals/<id>/documents`, `/api/deals/<id>/material-contracts`             |
| Negotiation history or context        | `/api/deals/<id>/notes`                                                       |

### Step 3: Compare draft terms against the authoritative source

For playbook-based tasks (position work for a client side):

1. Fetch `/api/playbooks/<playbook_id>/rules`.
2. For each rule, find the matching draft term by term ID or subject matter.
3. Classify each deviation:
   - `draft_exceeds_playbook` — draft value higher than playbook preferred/fallback, or more burdensome.
   - `draft_below_playbook` — draft value lower than playbook preferred/fallback, or less protective.
   - `missing_required_term` — playbook requires the term but no matching draft term exists.
   - `in_policy` — draft matches preferred or is within acceptable range.
4. Treat missing terms the playbook requires as issues. A term is missing when no `source_term_ids` match the playbook rule.

For policy-based tasks (escalation work for committee review):

1. Fetch `/api/policies/<policy_id>/thresholds`.
2. Compare each draft term against its policy threshold.
3. Classify as `out_of_policy` when draft exceeds the threshold.
4. Exclude terms that are within policy, stale, or subject to a different governance path.

### Step 4: Assign risk ratings

Use risk estimates when available. Otherwise judge from business context:

- **HIGH**: Closing certainty at risk, large dollar exposure (indemnity cap in millions), missing required term with structural impact, regulatory condition unsatisfied.
- **MEDIUM**: Non-structural term with moderate dollar exposure, missing ancillary term, survival or basket gap.
- **LOW**: Administrative gaps, notice-only items, minor definitional issues.

### Step 5: Determine recommended action

| Action                      | When to use                                                                  |
| --------------------------- | ---------------------------------------------------------------------------- |
| `delete`                    | Buyer-favorable term with no seller playbook support; clear removal target   |
| `revise`                    | Term exists but value is wrong; replace with playbook or negotiated position |
| `add`                       | Term is missing from draft and playbook requires it                          |
| `accept`                    | Draft matches playbook or policy; no change needed                           |
| `approve`                   | Grant committee approval for a term                                          |
| `approve_with_conditions`   | Approve only if stated conditions are met                                    |
| `reject`                    | Reject the current draft position outright                                   |
| `escalate`                  | Raise to business lead or a higher governance body                           |

### Step 6: Quantify dollar impacts

Calculate amounts from the deal's headline purchase price unless a risk estimate, finding, or data record explicitly states a different basis. Conventions:

- `headline_value_dollars` comes from the deal record and is the default basis for percent calculations.
- For cap shortfalls: (fallback_percent - draft_percent) × headline value.
- For fee shortfalls: required_fee_dollars minus current draft value.
- For consent amounts at risk: sum of consent record amounts for required closing consents.
- For material contract revenue: sum of annual revenues for contracts requiring consent.
- Modeled exposure low/high: sum low/high values from risk estimates for relevant risk IDs.
- PTO liabilities: from employee endpoints.
- Stranded costs: from TSA-related risk estimates or findings.

### Step 7: Build the JSON output

Every task provides an `answer_template.json` in `input/payloads/`. Read that template and produce output matching its shape exactly. The template defines the schema, allowed enums, and required fields. Fill every field the template requires. Use `null` for fields where the information genuinely is not available. Use empty arrays `[]` for missing term IDs or empty relationship lists.

## Reusable Sub-Workflows

See [reference/workflows.md](reference/workflows.md) for detailed patterns for the five common task types:

1. **Seller Issue Register** (comparative: draft vs playbook)
2. **Buyer Closing and Economics Package** (stock deal SPA prep)
3. **M&A Committee Escalation** (policy-threshold review)
4. **Carveout APA Transition Review** (separation terms and redlines)
5. **Buyer Deviation Matrix** (position matrix with blockers)

## Conventions

### Units
- Currency: integer USD (no cents, no decimals).
- Percent values: decimal number in percent points (e.g., `12.5` means 12.5%, not 0.125). Round to:
  - Two decimal places for general percent points.
  - One decimal place when template says so.
  - Four decimal places for holder fully-diluted percentages.
- Months: integer months.
- Dates: `YYYY-MM-DD` strings.

### Stable IDs
Workbench records use stable IDs. Preserve them exactly as returned:

- Term IDs: `TERM_<DEAL>_NN` (e.g., `TERM_PRJ_JUNIPER_01`)
- Consent IDs: `CNS_<DEAL>_NN`
- Employee IDs: `EMP_<DEAL>_NN`
- Material contract IDs: `MAT_<DEAL>_NN`
- Risk estimate IDs: `RSK_<DEAL>_NN`
- Finding IDs: `FND_<DEAL>_NN`
- Document IDs: `DOC_<DEAL>_NN`
- Regulatory ID: `REG_<DEAL>`

### Priority Order
When a template requests `priority_order`:

- Terms affecting closing certainty (financing, HSR, reverse break fee) come first.
- Terms with largest dollar delta follow.
- Missing structural terms rank above revision items.
- Ancillary or boilerplate items rank last.

### Closing Blocker Classification
A closing blocker is any item that must be satisfied before the deal can close:

- Required third-party consents that are genuine closing conditions (not notice-only).
- Regulatory clearance (HSR) when the deal exceeds thresholds.
- Material contracts whose change-of-control clauses require consent.
- Missing terms that create a closing vulnerability.

## Output Rules

- Return only valid JSON matching the answer template. No explanatory prose outside the JSON.
- Use the enums defined in the template. Do not invent new values.
- Sort arrays as directed by the template (by `issue_id`, by `redline_id`, or by `priority_rank`).
- Include every required top-level field from the template.
- Do not copy any example values from this skill file; every value must come from the workbench API at runtime.
