# M&A Deal Workbench Skill

## Purpose

Solve structured M&A transaction counsel tasks using a running deal workbench. The workbench serves deal records, draft terms, playbook rules, policy thresholds, and diligence data through a REST API and optional read-only SQL. Every task requires gathering data from the workbench, comparing draft positions against a governing framework (playbook or policy), producing a structured JSON answer that conforms to a supplied answer template, and returning only that JSON.

## Core Workflow

Follow this sequence for every task; skip steps only when the task scope explicitly excludes them.

### 1. Read the prompt and template together

- Extract `deal_id`, `client_side` (buyer or seller), and the governing framework (`playbook_id` or `policy_id`) from the prompt.
- Read `input/payloads/answer_template.json` to learn the exact output shape, allowed enums, stable IDs, required fields, units, and ordering rules.
- Note any task-specific filters: e.g., "only current terms," "exclude stale," "only out-of-policy," "transition/separation focus only."

### 2. Fetch the deal record

```
GET {base}/api/deals/{deal_id}
```

Record these values from the deal object — they anchor every calculation:
- `headline_value` — the headline purchase price; use as the default basis for all dollar-amount derivations.
- `upfront_cash`, `stock_value`, `milestone_value` — use only when a task explicitly asks for a different basis.
- `playbook_id` or `policy_id` — which rule set governs.
- `client_side`, `client_name`, `counterparty_name`, `target_name`, `signing_date`, `meeting_date`, `transaction_type`, `industry`, `status`.

### 3. Fetch the governing framework

For **playbook-driven** tasks:
```
GET {base}/api/playbooks/{playbook_id}/rules
```
Each rule has: `category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`, `required_action`, `risk_default`, `notes`.

For **policy-driven** tasks:
```
GET {base}/api/policies/{policy_id}/thresholds
```
Each threshold has: `category`, `policy_standard`, `threshold_value`, `threshold_unit`, `approval_required`, `restricted_flag`, `notes`.

### 4. Fetch draft terms

```
GET {base}/api/deals/{deal_id}/terms
```

Each term has: `term_id`, `category`, `draft_value` (text), `numeric_value`, `unit`, `basis`, `source_document`, `clause_ref`, `staleness_flag` (`"current"` or `"stale"`), `counterparty_rationale`.

**Staleness rule:** Exclude terms with `staleness_flag: "stale"` unless the task explicitly asks for them.

### 5. Fetch all relevant sub-records

Pull every sub-record the prompt mentions plus any that could supply values the template requires. Common endpoints:

| Endpoint | What it provides |
|---|---|
| `/api/deals/{id}/consents` | Required/optional consents, counterparties, amounts at risk |
| `/api/deals/{id}/employees` | Headcounts, PTO liabilities, service-credit requirements, WARN risk |
| `/api/deals/{id}/regulatory` | HSR requirement, regulatory approval type, hell-or-high-water status |
| `/api/deals/{id}/benchmarks` | Market medians, upper quartiles, sample sizes by category |
| `/api/deals/{id}/risk-estimates` | Exposure ranges (low/high) by category |
| `/api/deals/{id}/notes` | Deal-team guidance on posture, counterparty rationale, diligence follow-ups |
| `/api/deals/{id}/material-contracts` | Contract-level revenue, consent types, anti-assignment/COC flags |
| `/api/deals/{id}/diligence-findings` | Identified risks with amounts, severity, topics |
| `/api/deals/{id}/cap-table` | Holder-level shares, percentages, security classes |
| `/api/deals/{id}/documents` | Document metadata (not always needed) |

### 6. Use SQL for cross-table checks (when needed)

```
POST {base}/api/query
{"token": "deal-workbench-readonly", "sql": "<query>"}
```

Available tables: `deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `consents`, `employees`, `regulatory`, `benchmarks`, `risk_estimates`, `deal_notes`, `material_contracts`, `diligence_findings`, `cap_table`, `documents`.

Use SQL when you need to verify counts, check for related records across deals, or confirm that no stale or duplicate rows affect the analysis.

### 7. Map draft terms to framework rules

For each draft term:
- Find the matching playbook rule or policy threshold by `category`.
- Compare `numeric_value` (or the text `draft_value` for non-numeric terms) against the framework's `limit_value` / `threshold_value`.
- Classify the term's status using the template's allowed `issue_status` values:
  - `in_policy` — draft complies with playbook/policy.
  - `out_of_policy` — draft exceeds or violates the threshold.
  - `draft_exceeds_playbook` — draft goes beyond the playbook maximum (seller-side).
  - `draft_below_playbook` — draft falls below the playbook minimum (buyer-side).
  - `missing_required_term` — a framework rule exists for a category with no corresponding current draft term, AND the surrounding deal data shows the term is needed.

### 8. Identify framework gaps

For every playbook rule or policy threshold whose `category` has NO corresponding current draft term, check whether the surrounding data (consents, employees, regulatory, risk estimates, notes) shows the term is needed. If so, classify as `missing_required_term` with an empty `source_term_ids` array. If the template provides a fixed list of stable issue/term IDs, use only those.

### 9. Calculate dollar amounts and deltas

**Default basis:** Use `headline_value` (headline purchase price) for all percentage-to-dollar calculations unless a source field explicitly states a different basis (e.g., `enterprise value` for reverse break fees, `equity value` for termination fees, `upfront_cash` for escrow).

**Percent → dollar:** `headline_value × (percent / 100)` — round to integer.

**Delta to fallback:** `draft_amount - fallback_amount` (positive means draft exceeds fallback).

**Exposure aggregation:** Sum risk-estimate `exposure_low` and `exposure_high` values across all relevant categories.

**Employee totals:** Sum `count` and `pto_liability` across all employee groups.

**Consent amounts:** Sum `amount_at_risk` for consents where `required_for_closing: "yes"`.

### 10. Prioritize

Rank issues from highest to lowest negotiation priority:
- Use the framework's `risk_default` (High → Medium → Low) as the primary sort.
- Within the same risk tier, prefer issues with larger quantified deltas or higher amounts at risk.
- Follow any ordering instruction in the template (e.g., "Sort by issue_id ascending").

### 11. Assemble the answer

- Use only the fields, enums, and stable IDs defined in the answer template.
- Include every required field; omit optional fields that are `null` only if the template permits.
- Use the exact enum strings (case-sensitive) from `allowed_enums` or inline enum comments.
- Sort arrays as directed (by `issue_id`, `priority_order`, `redline_id`, etc.).
- Double-check: all dollar values are integers, all percentages are the correct decimal precision, all months are integers, all dates are `YYYY-MM-DD`.

### 12. Validate before returning

- The answer must be a single valid JSON object — no markdown fences, no explanatory prose.
- Every `issue_id` / `term_id` / `consent_id` / `employee_id` / `contract_id` / `finding_id` must be a stable ID exactly as returned by the workbench.
- Every enum value must appear in the template's allowed list.
- Every numeric field must match the template's unit specification.

## Task-Type Variations

### Seller-side issue register (playbook-driven)
Client is seller comparing a buyer's draft APA against a seller playbook. Identify every term where the buyer draft exceeds, falls below, or omits a seller-protective position. Risk ratings follow the playbook's `risk_default`. Priority order is from highest negotiation importance to lowest.

### Buyer-side closing/economics package (playbook-driven)
Client is buyer preparing a comprehensive SPA review. Cover economics and holder-level consideration allocation, indemnity/escrow/survival mechanics, required consents, regulatory status, employee treatment, D&O tail, and closing readiness.

### Committee escalation package (policy-driven)
Client needs M&A Committee approval for out-of-policy terms. **Only** include current draft terms that are out of policy or restricted for committee approval. Exclude stale terms, in-policy terms, and terms whose approval level is below the committee. For each escalated term, provide the policy comparison, quantified delta, benchmark support, exposure estimate, recommendation, and required conditions.

### Transition/carveout review (playbook-driven)
Focus on separation-specific terms: transition services scope/duration/fees, IP/domain transition, employee continuity, purchase-price allocation, transfer taxes, consent conditions, outside-date protection, governing law/forum. Treat missing carveout-protective provisions as issues.

### SPA deviation matrix (playbook-driven)
Buyer-side review of specific SPA positions: indemnity cap/basket, survival/knowledge qualifiers, materiality scrape, escrow/holdback, consent closing conditions, HSR, material contracts. Classify each position against the buyer playbook and calculate shortfalls to preferred and fallback amounts.

## Reference: Common Framework Rules

### PB_SELLER_A (Seller Playbook)
| Category | Preferred | Fallback | Risk |
|---|---|---|---|
| financing_condition | No buyer financing condition | Reverse break fee ≥ 6.0% of enterprise value | High |
| indemnity_cap | Cap ≤ 10.0% of purchase price | Cap ≤ 12.5% for verified customer concentration risk | Medium |
| survival_period | 12 months | 15 months for customer contracts | Medium |
| escrow | ≤ 8.0% of purchase price | 10.0% with 12-month release | Medium |
| transition_services | ≤ 6 months | 9 months if fees cover stranded cost | High |

### PB_BUYER_A (Buyer Playbook)
| Category | Preferred | Fallback | Risk |
|---|---|---|---|
| indemnity_cap | Cap ≥ 12.0% of purchase price | 10.0% with special indemnity for findings | Medium |
| survival_period | ≥ 18 months | 15 months if escrow ≥ 10.0% | Medium |
| materiality_scrape | Full scrape for breach and damages | Breach-only scrape | High |
| consent_closing_condition | All material consents required | Top 10 revenue contracts | High |
| employee_service_credit | Credit prior service and honor PTO | Service credit for benefits only | Medium |

### POL_MA_2025_A (M&A Committee Policy)
| Category | Threshold | Approval |
|---|---|---|
| reverse_termination_fee | ≤ 4.0% of equity value | M&A Committee |
| fiduciary_out | Both superior proposal AND intervening event triggers, 5 biz-day match right | M&A Committee |
| rw_survival | ≤ 15 months | M&A Committee |
| mae_carveouts | ≤ 2 carveouts (general economic, natural disasters) | M&A Committee |
| termination_fee | ≤ 3.0% of equity value | General Counsel |
| voting_agreements | ≤ 35.0% of fully diluted shares | M&A Committee |

## Units and Precision (by convention across tasks)

- **Currency:** Integer USD (no decimals, no commas, no currency symbol in the value).
- **Percentages:** Decimal number in percent points (e.g., 12.5 means 12.5%). Precision to 1 or 2 decimal places as specified in the template.
- **Months:** Integer.
- **Dates:** `YYYY-MM-DD` string.
- **Holder percentages:** Four decimal places when specified (e.g., 0.1850).
- **Dollar amounts:** Compute from the correct purchase-price basis (headline, upfront cash, equity value, or enterprise value) as stated by the source record.
