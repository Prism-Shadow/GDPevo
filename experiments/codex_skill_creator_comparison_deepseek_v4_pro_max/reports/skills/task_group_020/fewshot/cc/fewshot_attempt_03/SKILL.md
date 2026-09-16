---
name: manda-deal-review
description: |
  Analyze M&A deal documents against playbooks, policies, and committee
  thresholds to produce structured issue registers, closing-readiness
  packages, deviation matrices, escalation memos, and transition reviews.
  Use this skill whenever the user is reviewing a purchase agreement
  (APA or SPA), preparing a deal-issues matrix, building a closing
  checklist, creating an M&A committee escalation memo, running a
  seller-side or buyer-side deal review, or comparing draft terms
  against playbook positions.  This skill must be used even when the
  user describes the task in their own words without naming the skill.
  Trigger phrases include "review the buyer paper," "prepare a
  closing package," "escalation for the M&A committee," "seller
  issue register," "buyer deviation matrix," "carveout transition
  review," or any request that mentions a deal workbench, playbook
  rules, committee policy, or M&A term comparison.
---

# M&A Deal Review

Analyze M&A purchase-agreement terms against playbooks and policies
using the deal-workbench API.  Produce structured JSON outputs that
conform to the answer template supplied with the task.

## Workflow

Follow these steps in order.  Do not skip data-fetching before
analysis, and do not invent IDs or values that are not present in the
workbench records.

### 1. Understand the task

Read the user prompt completely.  Extract:

- **Task type** — issue register, closing package, escalation memo,
  transition review, deviation matrix, or similar.
- **Deal ID** — the workbench project code (e.g., `PRJ_JUNIPER`).
- **Client side** — `seller` or `buyer`.
- **Playbook or policy ID** — e.g., `PB_SELLER_A`, `PB_BUYER_A`,
  `POL_MA_2025_A`.
- **Answer template path** — always given as
  `input/payloads/answer_template.json`.
- **Specific endpoints the prompt highlights** — start with those.

### 2. Read the answer template

Read `input/payloads/answer_template.json` before fetching any
workbench data.  Memorise:

- The required top-level fields and their types.
- Allowed enum values for every field that uses enums.
- Which fields are nullable, which are required.
- Stable ID lists when the template provides them.

You must conform exactly to this schema.  Every field the template
declares must appear in your output; do not add fields the template
does not declare.

### 3. Gather workbench data

Fetch data from the workbench at `<TASK_ENV_BASE_URL>`.  Always begin
with the deal record and terms, then branch out based on the task
type.  See [references/workbench_api.md](references/workbench_api.md)
for the full endpoint catalogue and request conventions.

Minimum fetch for every task:
- `GET /api/deals/<deal_id>` — headline price, parties, dates, status.
- `GET /api/deals/<deal_id>/terms` — current draft terms.

If the task involves a playbook:
- `GET /api/playbooks/<playbook_id>/rules` — preferred, fallback, and
  prohibited positions.

If the task involves committee policy:
- `GET /api/policies/<policy_id>/thresholds` — approval thresholds.

Then fetch every endpoint the prompt mentions and every endpoint the
answer template field names suggest is relevant (e.g., if the template
has `holder_allocation`, fetch `/cap-table`; if it has
`required_consents`, fetch `/consents`; if it has
`material_contract_conditions`, fetch `/material-contracts`).

### 4. Compare draft terms against the playbook or policy

For every term the template covers, determine its status using the
comparison rules in
[references/analysis_patterns.md](references/analysis_patterns.md).

Broad status categories:
- `in_policy` — the draft matches the client's preferred or fallback
  position.
- `out_of_policy` — the draft violates a committee policy threshold.
- `draft_exceeds_playbook` — the draft is more aggressive than the
  client's fallback (bad for your client).
- `draft_below_playbook` — the draft is weaker than the client's
  fallback (bad for your client).
- `missing_required_term` — the draft is silent on something the
  playbook or policy requires.

For **seller-side** reviews: "exceeds playbook" means the buyer draft
gives the buyer more than the seller's fallback permits (e.g. higher
escrow %, longer survival, broader non-compete).

For **buyer-side** reviews: "below playbook" means the seller draft
gives the buyer less than the buyer's fallback requires (e.g. lower
indemnity cap %, shorter survival, no escrow).

### 5. Identify issues, assign risk, and build priorities

Every term that is not `in_policy` becomes an issue.  See
[references/analysis_patterns.md](references/analysis_patterns.md)
for risk-rating and priority-ordering rules.

General principles:
- **HIGH risk**: closing certainty, large dollar exposure, missing
  required terms with quantified impact, regulatory blockers.
- **MEDIUM risk**: indemnity mechanics with moderate dollar gaps,
  administrative terms that affect post-closing operations.
- **LOW risk**: housekeeping items, terms within negotiation range,
  notice-only conditions.

**Priority order** sorts issues from highest negotiation urgency to
lowest.  Closing certainty issues always lead; mechanics issues follow;
administrative terms come last.

### 6. Calculate dollar amounts

Use the calculation rules in
[references/calculation_guide.md](references/calculation_guide.md).
The single most important rule: **derive all dollar amounts from the
headline purchase price** unless a workbench record explicitly states
a different basis (e.g., upfront cash for escrow, equity value for
reverse termination fees).

### 7. Compile summary metrics

Aggregate issue counts, risk counts, quantified exposure ranges,
employee totals, consent counts, and any other template-required
summary fields.  Sum values from the issue register; do not invent
numbers.

### 8. Output JSON

Return exactly one JSON object.  No markdown fences, no leading or
trailing prose, no commentary outside the JSON body.  The JSON must
pass a strict schema validator against the answer template.

## Units and Conventions

These apply to every task unless the answer template explicitly says
otherwise.

| Item | Convention |
|------|-----------|
| Currency | Integer USD (no decimals, no commas, no `$` sign) |
| Percentages | Decimal number in percent points (e.g., `12.5` means 12.5%) |
| Months | Integer months |
| Dates | `YYYY-MM-DD` strings |
| Holder percentages | Four-decimal precision when required |
| IDs | Use stable IDs from the workbench; never invent IDs |
| Null fields | Set to `null` when the template permits it and no value exists |

## JSON-only Output Rule

The test solver will parse your entire response as JSON.  Do not
preface the JSON with explanatory text, do not wrap it in markdown
code fences, and do not add trailing commentary.  If you need to note
an assumption, encode it in a field the template provides.

## Reference Files

- [references/workbench_api.md](references/workbench_api.md) —
  Complete API endpoint catalogue and request patterns.
- [references/analysis_patterns.md](references/analysis_patterns.md) —
  How to classify issues, assign risk ratings, choose recommended
  actions, and build priority orderings.
- [references/calculation_guide.md](references/calculation_guide.md) —
  Dollar-amount derivation, percent conventions, delta/shortfall
  arithmetic, exposure-range aggregation, and employee-data rules.

Read the relevant reference when you need detail that the main
workflow above does not supply.  Use your judgment about which
reference to consult first based on the task type.
