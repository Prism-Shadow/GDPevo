# Aster Legal Deal Desk — Agent Skill

## Environment

- **Base URL**: `http://34.46.77.124:9020` (set as `GDPEVO_ENV_BASE_URL`).
- **Access**: All data retrieval uses `curl` via Bash. Never use `WebFetch` — the environment is an internal IP not reachable from the web fetch service.
- **Health check**: `GET /api/health` returns system stats (deals, documents, policies, clauses, benchmarks counts) and a seed number.

## API Endpoints (prefer JSON over HTML scraping)

| Endpoint | Returns | Use |
|---|---|---|
| `GET /api/deals/{DEAL_ID}` | JSON: `deal`, `clauses`, `documents`, `policy`, `benchmarks` | **Primary data source** for any deal. One call gets everything. |
| `GET /api/policies/{POLICY_ID}` | JSON: policy metadata, rules, and `linked_deals` (summary of each linked deal) | Policy thresholds, preferred/fallback, escalation triggers, approval categories. |
| `GET /api/benchmarks?industry={INDUSTRY}` | JSON: benchmarks filtered by industry | Find industry-relevant benchmarks for quantification. |
| `GET /clauses/compare?deal_id={DEAL_ID}` | HTML with embedded JSON in `<pre>` tags and tables | Clause-level comparison: draft vs playbook values, thresholds, status badges. |
| `GET /deals/{DEAL_ID}` | HTML with embedded JSON in `<details class="raw"><pre>` blocks | Full deal page: economics, parties, schedules, client positions, draft terms, clause comparison, active/stale docs. |
| `GET /policies/{POLICY_ID}` | HTML with embedded JSON | Policy rule details in human-readable tables plus raw JSON. |
| `GET /documents/{DOC_ID}` | HTML with embedded JSON | Individual document details (cap table records, email instructions, financial schedules). |

> **Pattern**: Every HTML page has `<details class="raw"><summary>Raw … JSON</summary><pre>{…}</pre></details>` — extract with `grep -oP '<pre>\K(.*?)(?=</pre>)'` or parse within `<details class="raw">` blocks.

## Data Model

### Deal structure (from `/api/deals/{DEAL_ID}`)

```
deal                    — codename, client, side, structure, status, target, headline/equity value,
                          signing_date, closing_deadline, industry, policy_id, buyer, seller
  ├── economics         — basket, escrows, consideration_mix, indemnity_cap, survival_periods,
  │                       working_capital, break_fee_percent, reverse_termination_fee_percent
  ├── parties           — buyers[], sellers[] (with estimated_proceeds, ownership_percent, role),
  │                       committee_members[], key_employees[], representatives[]
  ├── schedules         — cap_table, employment_terms, ip_transition, material_contracts[],
  │                       regulatory_status, transition_services, stale_cap_table
  ├── client_positions  — escalation[], fallback[], preferred[] (narrative)
  ├── draft_terms       — narrative descriptions of current draft positions
  └── negotiation_context — batna, ownership_dynamics, rationale, strategic_notes
clauses[]               — clause_id, clause_code, topic, draft_value, playbook_value, policy_threshold,
                          calculation_base, source_doc_id, version_status (ACTIVE|STALE)
documents[]             — doc_id, doc_type, title, version_status, effective_date, sections[]
policy                  — policy_id, version, rules[] (rule_id, topic, preferred, fallback_position,
                          threshold, approval_category, escalation_triggers[])
benchmarks[]            — benchmark_id, topic, industry, year, mean/median_percent, range_low/high,
                          sample_size, count_above_threshold
```

### Document types
- `term_sheet`, `draft_agreement`, `email` (client instructions), `cap_table`, `financial_schedule`, `material_contracts`, `disclosure_schedule`, `committee_charter`, `template_provision`

### Status badges
- **ACTIVE** (green) — current, authoritative source
- **STALE** (amber) — superseded, retain for audit only — **never use as primary source**
- **TEMPLATE** (gray/muted) — generic drafting system boilerplate — **ignore unless confirmed by active client instructions**

## Source Precedence (CRITICAL)

1. **Latest written client instructions** (`email` type, ACTIVE status) — overrides everything
2. **Active playbook/policy** (ACTIVE `draft_agreement` + policy rules) — the governing standard
3. **Relevant benchmarks** (same industry, same year, same topic) — for quantification and market check
4. **Active term sheet** — commercial baseline, not legal authority
5. **STALE documents** — audit trail only; **do not use for answers**
6. **TEMPLATE documents** — generic boilerplate; **dangerous distractor** — template values (e.g., "10% escrow, 5-year worldwide non-compete") are NOT deal-specific and conflict with playbooks

### Identifying the right benchmark
- Match `industry` and `year` to the deal.
- Current year (2026) benchmarks are preferred.
- Older years and different industries are **distractors**.
- Prefer benchmarks flagged as "current" or without "outside core peer set" notes.

## Task Types and Workflows

### 1. Term Population (Buyer/Seller SPA first draft)
**Goal**: Populate deal terms, seller allocations, and closing flags from the deal record.
**Workflow**:
1. Call `/api/deals/{DEAL_ID}` — extract `deal.economics`, `deal.parties`, `deal.schedules`
2. Use ACTIVE cap table (`schedules.cap_table`) for seller allocations — ignore STALE cap table
3. Map `working_capital.mechanic` narrative to controlled enum:
   - "Dollar-for-dollar adjustment outside collar" → `DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`
   - "True-up against active balance sheet" → `TRUE_UP_AGAINST_ACTIVE_BALANCE_SHEET`
   - "Seller budget baseline" → `SELLER_BUDGET_BASELINE`
4. Map `basket.type` lowercase → uppercase enum: `deductible` → `DEDUCTIBLE`, `tipping` → `TIPPING`
5. Material consents `condition_type` mapping: `closing` → `CLOSING`, `covenant` → `COVENANT`, `government notice` → `NOTICE`, `post-closing notice` → `POST_CLOSING_NOTICE`
6. HSR basis mapping: "size-of-person test is not met" → `SIZE_OF_PERSON_TEST_NOT_MET`, "thresholds met" → `REPORTABLE_THRESHOLDS_MET`, "counsel memo missing" → `COUNSEL_MEMO_MISSING`
7. Employment agreement term: "Two-year" → 24 months

### 2. Counterparty Paper Review (Seller/APA mark-up review)
**Goal**: Compare active counterparty draft against client instructions + playbook, produce issue register.
**Workflow**:
1. Get `/api/deals/{DEAL_ID}` — extract `clauses[]` (filter `version_status: "ACTIVE"`), `policy.rules[]`, `deal.client_positions`, `deal.draft_terms`
2. For each ACTIVE clause, compare `draft_value` against `playbook_value` and policy `preferred`/`fallback_position`/`threshold`
3. Flag as issue if: draft violates policy preferred, exceeds threshold, or triggers escalation
4. Quantify economic issues: compute dollar amounts from percentages against `headline_value` or `equity_value`
5. Include `source_ids`: clause_id, policy rule_id, draft_agreement doc_id, email doc_id — NOT stale/template doc_ids
6. Skip clauses where draft aligns with policy (these are non-issues — do not include)

### 3. Committee Escalation Analysis
**Goal**: Identify terms needing committee escalation, quantify exposure, summarize routing.
**Workflow**:
1. Identify escalation_terms from clauses where draft violates policy thresholds
2. For each escalated term: assign `deviation_code`, quantify dollars/percentages, find matching benchmark
3. Only include terms that actually need escalation (exclude terms within policy)
4. Aggregate: determine `risk_tier` (CRITICAL if any term is CRITICAL or if combined exposure is large), `final_action`, committee routing
5. Derive `strategic_context` from `negotiation_context`: map batna text to `batna_code`, ownership text to `ownership_context`, rationale to `strategic_rationale`

### 4. Transition-Term Issue Package (Carve-out / structured flags)
**Goal**: Priority deviations + structured transition flags for employee, TSA, covenants, IP, escrow/deadline.
**Workflow**:
1. Get deal data + clause comparisons
2. For each transition category, compare draft against policy preferred/fallback/threshold
3. Only include `priority_issues` where there is a material deviation (draft differs from policy)
4. Populate `transition_flags` for all categories (employee_transfer, tsa_service_continuity, restrictive_covenants, ip_transition, escrow_and_deadline) — even if `issue_present: false`

### 5. First-Draft Term Population + Policy Checks
**Goal**: Populate all draft terms from deal record AND run policy compliance checks.
**Workflow**:
1. Populate `draft_terms` from deal API (structure, parties, economics, schedules)
2. Compute seller allocations: distribute consideration components (cash, note, rollover, earnout) per active cap table ownership percentages, respecting ownership dynamics (e.g., "founders prefer rollover" → allocate all rollover to founder sellers)
3. Run each policy rule against draft values: determine `WITHIN_POLICY` vs `APPROVAL_REQUIRED` vs `OVERRIDE_APPLIED` vs `ESCALATE_IF_CHANGED`
4. Identify `risk_memo_overrides`: active instructions superseding template, regulatory overrides, stale-to-active transitions
5. Generate `policy_summary` with conditional escalation triggers

## Numeric Conventions (universal)

| Type | Format | Example |
|---|---|---|
| Currency (USD) | Integer, no commas, no `$` | `184000000` |
| Percentages | Number, 2 decimal places, percentage points | `10.00` (not `0.10`) |
| Per-share price | Number or `null`, 2 decimal places | `null` if no share count |
| Months | Integer | `24` |
| Calendar days | Integer | `42` |
| Ownership percent | Number, 2 decimals | `44.20` |

### Computed values
- **price_per_as_converted_percent_point_usd**: `headline_value / 100` (integer)
- **per_share_price_usd**: `null` if cap table has no share count; otherwise `equity_value / fully_diluted_shares`
- **nwc_collar_percent_of_equity_value**: `(collar_usd / equity_value_usd) * 100` (2 decimals)
- **Escrow/cap dollar amounts**: `percent / 100 * headline_value` (integer)
- **Basket dollar amount**: `basket_percent / 100 * headline_value` (integer)
- **Seller gross_proceeds**: `ownership_percent / 100 * headline_value` — but prefer `estimated_proceeds` from active cap table when available

### Consideration allocation
- `total_consideration = cash_at_close + seller_note + rollover_equity + earnout` (must equal headline_value)
- When allocating across sellers, respect ownership dynamics (e.g., "founders prefer rollover" → all rollover to founders; "fund prefers cash" → fund gets mostly cash)
- Each seller's `total_proceeds` must equal their `estimated_proceeds` from the active cap table
- Default: allocate earnout and seller_note proportionally to ownership, with rollover allocated per dynamics, and cash making up the remainder

## Policy Check Logic

### Determining `WITHIN_POLICY` vs `ESCALATE`
- Compare draft value against policy `preferred` range first
- If draft is within preferred range → `WITHIN_POLICY`
- If draft exceeds preferred but is within `fallback_position` → `WITHIN_POLICY` (or `APPROVAL_REQUIRED` if fallback requires approval)
- If draft exceeds `threshold` → `ESCALATE` or `APPROVAL_REQUIRED`
- If draft triggers an `escalation_trigger` → mark accordingly
- "Exceeds" vs "at or above": "Escalate if general escrow exceeds 10%" means 10.0% does NOT trigger; 10.01% does

### Policy status enums
- `WITHIN_POLICY` — draft complies with preferred or approved fallback
- `APPROVAL_REQUIRED` — draft is within fallback range but requires approval
- `OVERRIDE_APPLIED` — a documented override justifies deviation
- `ESCALATE_IF_CHANGED` — currently compliant, but flag as trigger if counterparty proposes changes

### Approval categories (common)
- `DEAL_LEAD`, `LEGAL_RISK_COMMITTEE`, `FINANCE_COMMITTEE`, `EMPLOYMENT_COUNSEL`, `REGULATORY_COUNSEL`, `HR_COMMITTEE`, `OPERATIONS_COMMITTEE`, `IP_COUNSEL`, `SELLER_STEERING_COMMITTEE`, `BOARD_TRANSACTION_COMMITTEE`, `EXECUTIVE_COMMITTEE`

## Policy Registry

| Policy ID | Client | Type | Version | Linked Deals |
|---|---|---|---|---|
| `P-BUYER-MIDMARKET-2026` | Northstar Capital Partners | BUYER_RISK_MEMO | 2026.2 | D-ALDER-447, D-HARBOR-562, D-LUMEN-908, etc. |
| `P-SELLER-APA-2026` | Meridian Seller Desk | SELLER_PLAYBOOK | 2026.1 | D-BRASS-219, D-QUARTZ-311, etc. |
| `P-PUBLIC-MERGER-COMMITTEE-2026` | Aster Public Company Committee | COMMITTEE_POLICY | 2026.3 | D-CYPRESS-735, D-NOVA-674, etc. |
| `P-CARVEOUT-OPS-2026` | Atlas Industrial Holdings | SELLER_PLAYBOOK | 2026.1 | D-ORBIT-384, D-ORCHID-385 |
| `P-HYBRID-INVEST-2026` | Kepler Growth Fund | BUYER_RISK_MEMO | 2026.2 | D-KEPLER-155 |
| `P-ROLLOVER-SPA-2026` | Solstice Strategic Capital | BUYER_RISK_MEMO | 2026.1 | D-SOLSTICE-820 |
| `P-STANDARD-FORM-2026` | Aster Legal Standard Forms | STANDARD_FORM | 2026.1 | Template boilerplate (not a client policy) |

## Output Conventions

- **JSON only** — no markdown, no prose, no explanatory text outside JSON
- **Sorting**: seller_allocations by `seller_name` ascending; material_consents by `contract_name` ascending; employees by displayed name ascending; issue lists by `issue_id` or `term_id` ascending; code lists (mae_omitted_carveouts, required_service_codes, conditional_escalation_triggers) alphabetically; source_doc_ids alphabetically
- **Null handling**: Use `null` for numeric fields that don't apply (not `0`, not omitted). Use `[]` for empty lists. Use `false` for boolean defaults.
- **Enum precision**: Match exactly — case-sensitive, underscores preserved. Map free-text descriptions to closest enum.
- **Condition type mapping**: `closing` → `CLOSING`, `covenant` → `COVENANT`, `government notice` → `NOTICE`, `post-closing notice` → `POST_CLOSING_NOTICE`, `TSA` → not a consent condition type (exclude from consent lists)
- **Employment employees**: Strip titles/roles — "Mina Calder, founder/CTO" → `"Mina Calder"`. Sort alphabetically by displayed name.

## Common Pitfalls

1. **Using stale cap tables** — always check `version_status: "ACTIVE"`; the stale cap table has different ownership percentages and dates
2. **Using template clauses as deal data** — templates say "Generic template value retained in drafting system" — ignore these
3. **Wrong industry benchmarks** — only use benchmarks matching the deal's industry AND current year
4. **WebFetch failure** — this is an internal IP; always use `curl` via Bash
5. **Including non-issues** — only include terms that actually deviate from policy (do not include `WITHIN_POLICY` items as issues)
6. **Currency precision** — always integer dollars; `18400000` not `18.4M` or `18400000.00`
7. **Percent confusion** — percentages are percentage points (e.g., `10.00` means 10%), not fractions (not `0.10`)
8. **Escalation boundary** — "exceeds X%" means > X%, not >= X%. A value exactly at the boundary is still within policy
9. **Incomplete allocation** — seller total_proceeds must sum to headline_value; each component (cash, note, rollover, earnout) must sum to its total
10. **Missing transition flags** — even when `issue_present: false`, populate the transition_flags structure with applicable data

## Deal ID Reference (Training Set)

| Deal ID | Codename | Client | Side | Structure | Headline | Policy |
|---|---|---|---|---|---|---|
| D-ALDER-447 | Alder Ridge | Northstar Capital Partners | BUYER | STOCK_PURCHASE | $184M | P-BUYER-MIDMARKET-2026 |
| D-BRASS-219 | Brass Foundry | BrassWorks Holdings | SELLER | ASSET_PURCHASE | $236M | P-SELLER-APA-2026 |
| D-CYPRESS-735 | Cypress Halo | Helios Health Systems | BUYER | MERGER | $1.18B | P-PUBLIC-MERGER-COMMITTEE-2026 |
| D-ORBIT-384 | Orbit Forge | Atlas Industrial Holdings | SELLER | CARVE_OUT | $312M | P-CARVEOUT-OPS-2026 |
| D-HARBOR-562 | Harbor Lantern | Northstar Capital Partners | BUYER | STOCK_PURCHASE | $198.5M | P-BUYER-MIDMARKET-2026 |
