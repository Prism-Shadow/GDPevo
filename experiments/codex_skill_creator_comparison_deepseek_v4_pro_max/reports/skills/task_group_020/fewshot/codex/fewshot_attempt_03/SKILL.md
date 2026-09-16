---
name: ma-deal-workbench
description: M&A deal negotiation and analysis using a structured deal workbench API. Use when Codex needs to analyze acquisition agreements, prepare issue registers, closing packages, escalation memos, transition reviews, or deviation matrices from deal workbench data. Triggers on requests involving deal terms, playbook comparisons, purchase-price calculations, consent analysis, employee transition, regulatory review, indemnity economics, or structured M&A position documents. Supports both seller-side and buyer-side perspectives.
---

# M&A Deal Workbench

Analyze M&A deals using the structured deal workbench REST API. Gather deal records,
compare draft terms against playbook rules or policy thresholds, compute dollar
amounts from headline purchase price, and return structured JSON conforming to
the provided answer template.

## Quick Start

1. Read the provided `input/prompt.txt` and `input/payloads/answer_template.json`.
2. Identify the deal ID, client side, and playbook or policy ID from the prompt.
3. Gather all relevant workbench records. Use [API Reference](references/api_endpoints.md)
   for endpoint details.
4. Compare each draft term against the applicable playbook rules or policy
   thresholds. See [Domain Model](references/data_model.md) for field semantics and
   [Task Patterns](references/task_patterns.md) for task-type guidance.
5. Compute dollar amounts from the headline purchase price unless a source
   explicitly states a different basis.
6. Return only valid JSON matching the answer template shape. Do not include
   explanatory prose, markdown fences, or commentary outside the JSON.

## Core Workflow

### Step 1: Parse the Task

From the prompt, extract:
- `deal_id` (e.g., `PRJ_JUNIPER`)
- `client_side` ("seller" or "buyer") -- infer from language like "seller-side counsel" or "buyer-side counsel"
- The applicable playbook ID (e.g., `PB_SELLER_A`, `PB_BUYER_A`) or policy ID (e.g., `POL_MA_2025_A`)
- The answer template from `input/payloads/answer_template.json`

### Step 2: Gather Data

Use `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>` to get the deal header
(headline value, parties, structure). Then gather records relevant to the task
type. Common API endpoints are documented in [API Reference](references/api_endpoints.md).

Always fetch, at minimum, the deal record, terms, and the playbook or policy.
Fetch additional records (consents, employees, regulatory, benchmarks,
risk estimates, cap table, material contracts, diligence findings, notes)
based on what the answer template requires.

If cross-table verification is needed, use `POST /api/query` with the
read-only token as documented in the API reference.

### Step 3: Compare and Classify

For each draft term relevant to the answer template:

1. **Find the draft value** from the terms endpoint response.
2. **Find the corresponding playbook rule** or policy threshold.
3. **Classify the issue status:**
   - `draft_exceeds_playbook` / `draft_below_playbook`: draft value is worse than the playbook position
   - `missing_required_term`: playbook requires a term absent from the draft
   - `in_policy` / `out_of_policy`: for policy-based comparisons
4. **Assign risk rating** (`LOW`, `MEDIUM`, `HIGH`) based on risk estimates or:
   - `HIGH`: closing certainty, indemnity/escrow with material dollar exposure, missing required protections
   - `MEDIUM`: mechanical/administrative gaps, survival periods, allocations
   - `LOW`: minor deviations or cosmetic items
5. **Determine recommended action** (`add`, `revise`, `delete`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`)

For playbook-based comparisons, use preferred and fallback values from the
playbook rules. For policy-based comparisons, use threshold values and
check benchmark support when available.

### Step 4: Compute Dollar Amounts

Unless a source record specifies a different basis, compute money amounts
from the deal's headline purchase price (`headline_value` from the deal record):

- `draft_amount = draft_percent * headline_value / 100`
- `preferred_amount = preferred_percent * headline_value / 100`
- `fallback_amount = fallback_percent * headline_value / 100`
- `delta_to_fallback = |draft_amount - fallback_amount|`

Round all dollar values to integers. Round percentages to the precision
specified by the answer template (typically two decimal places for percent
points, four for holder percentages).

### Step 5: Populate the Answer Template

Match every field in the answer template. Use only the allowed enums defined
in the template. Leave fields that do not apply to the current issue as `null`.
Sort issues and priority lists as directed by the template.

## Cross-Cutting Rules

### Seller-Side Perspective

- Identify terms the buyer's draft imposes that deviate from seller playbook.
- Treat missing seller-protective terms as issues when deal data shows they
  are needed (e.g., missing reverse break fee when buyer financing condition
  exists; missing HSR covenant when deal size exceeds HSR threshold).
- Prioritize issues that expose the seller to closing risk or economic leakage.

### Buyer-Side Perspective

- Identify terms where the seller's draft falls short of buyer playbook
  protections.
- Treat missing buyer-protective terms as issues (e.g., missing closing
  consents, missing HSR condition, missing escrow provisions).
- Prioritize issues that expose the buyer to indemnity leakage, closing
  uncertainty, or employee continuity gaps.

### Priority Ordering

Order issues from highest to lowest negotiation priority:
1. Closing certainty issues first (financing conditions, regulatory
   conditions, reverse break fees, consent conditions).
2. Indemnity and escrow economics next (caps, baskets, survival, materiality
   scrapes, escrow mechanics).
3. Employee and transition terms (continuity, PTO, TSA scope).
4. Restrictive covenant terms (non-competes, non-solicits).
5. Administrative terms last (governing law, tax allocation, transfer tax
   splits).

### Source ID Tracking

Use stable IDs from the workbench records. When a term is missing entirely,
use an empty array for `source_term_ids`. Cross-reference consent IDs,
contract IDs, employee IDs, and regulatory record IDs from the relevant
endpoints.

## Reference Files

- [API Reference](references/api_endpoints.md): Complete workbench API surface
- [Domain Model](references/data_model.md): Entity relationships and field semantics
- [Task Patterns](references/task_patterns.md): Task-type-specific instructions
