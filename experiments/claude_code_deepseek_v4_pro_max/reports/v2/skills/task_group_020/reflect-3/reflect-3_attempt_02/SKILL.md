# Aster Legal Deal Desk — Reusable Skill

## Environment

Use the shared Deal Desk Web/API environment at `<TASK_ENV_BASE_URL>` as provided in the task prompt. The application serves both HTML pages and structured JSON API endpoints from the same base URL.

## Core API Endpoints

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /api/health` | System status and record counts | `{status, counts: {deals, documents, policies, clauses, benchmarks}}` |
| `GET /api/deals/{DEAL_ID}` | Full deal bundle | `{deal, clauses, documents, policy, benchmarks}` |
| `GET /api/policies/{POLICY_ID}` | Policy rules and metadata | `{policy_id, rules: [...], client, version}` |
| `GET /api/documents/{DOC_ID}` | Single document | `{doc_id, doc_type, sections: [...], version_status}` |
| `GET /deals/{DEAL_ID}` | HTML deal page with embedded raw JSON in `<details class="raw">` blocks | Useful as fallback; prefer `/api/deals/` |

**Always prefer `/api/deals/{DEAL_ID}`** — it returns the complete deal, all active/stale clauses, all documents with section text, the controlling policy rules, and relevant benchmarks in one call. This avoids multiple round-trips.

## Data Hierarchy and Source Precedence

### Document Status Lifecycle
```
ACTIVE  → supersedes all others; use this data
STALE   → retained for audit; do NOT use (check `version_status` or `status` field)
TEMPLATE → generic drafting-system import; do NOT use (conflicts with current policy)
```

### Precedence Rules (strongest first)
1. **Latest written client instruction email** — the `DOC-*-EMAIL-03` document with `doc_type: "email"`. Its sections contain `Instruction summary`, `Fallbacks`, `Escalations`, and `Strategic context`. These override general policy.
2. **Active client playbook/policy** — the `policy_id` linked on the deal. Each rule has `preferred`, `fallback_position`, `threshold`, `escalation_triggers`, and `approval_category`.
3. **Active draft agreement** — `DOC-*-DRAFT-02`. Contains current draft terms and negotiation posture.
4. **Active cap table** — `DOC-*-CAP-ACTIVE`. Check `status: "ACTIVE"` and compare `as_of` date against any stale cap table.
5. **Material contracts schedule** — `DOC-*-MATCON-05`. Lists contracts with revenue/cost, condition type, and consent requirements.
6. **Term sheet** — `DOC-*-TERM-01`. The signed commercial foundation.
7. **Stale cap tables and template provisions** — ignore for data but note their doc IDs in source document lists and risk-memo overrides when the active version supersedes them.

### Clause Version Status
Each clause in the `/api/deals/` response carries `version_status`:
- `ACTIVE` — use this clause's draft_value, playbook_value, policy_threshold
- `STALE` or `TEMPLATE` — ignore; the system retains these as distractors

## Numerical Conventions

| Type | Format | Example |
|---|---|---|
| Currency (USD) | Integer, whole dollars, no commas/symbols | `184000000` |
| Percentages | Number, two decimal places, expressed as percentage points | `7.50` (not `0.075`) |
| Months | Integer | `24` |
| Ownership percent | Number, two decimal places | `44.20` |
| Boolean | JSON boolean | `true` / `false` |
| Nullable fields | JSON `null` when not applicable or not calculable | `"per_share_price_usd": null` |

### Common Computations
- **Dollar amount from percent**: `floor(round(headline_value * percent / 100))` — always cross-check against explicit amounts in the deal economics or clause data if available
- **Seller gross proceeds**: `ownership_percent × headline_value / 100`
- **Per-share price**: `null` when the active cap table lacks a share count; set `per_share_price_basis` to `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`
- **Price per percent point**: `headline_value / 100` (whole dollars)
- **NWC collar as % of equity**: `round((collar / equity_value) * 100, 2)`
- **Escrow amounts**: use the explicit amounts from the deal economics when present; compute from percent only if amounts are absent

## Controlled Enum Values

All enum values use UPPER_SNAKE_CASE. Match exactly — do not abbreviate, hyphenate, or transform.

### Deal-Level Enums
- `structure`: `STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`, `CARVE_OUT`, `ROLLOVER_STOCK_PURCHASE`
- `client_side`: `BUYER`, `SELLER`
- `basket_type`: `DEDUCTIBLE`, `TIPPING`, `NONE`

### Policy/Escalation Status Enums
- Policy status: `WITHIN_POLICY`, `ESCALATE`, `ESCALATE_IF_CHANGED`, `OVERRIDE_APPLIED`, `APPROVAL_REQUIRED`, `NOT_APPLICABLE`
- Approval categories: `DEAL_LEAD`, `LEGAL_RISK_COMMITTEE`, `REGULATORY_COUNSEL`, `EMPLOYMENT_COUNSEL`, `FINANCE_COMMITTEE`, `HR_COMMITTEE`, `IP_COUNSEL`, `OPERATIONS_COMMITTEE`, `EXECUTIVE_COMMITTEE`, `SELLER_STEERING_COMMITTEE`, `BOARD_TRANSACTION_COMMITTEE`

### Severity and Routing
- `severity` / `risk_tier`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `committee_route`: `BOARD_TRANSACTION_COMMITTEE`, `CLIENT_BUSINESS_LEAD`, `NO_COMMITTEE_ROUTE`

### Closing Conditions
- `condition_type`: `CLOSING`, `COVENANT`, `NOTICE`, `POST_CLOSING_NOTICE`
- `consent_condition_status`: `MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`, `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS`, `NO_MATERIAL_CONSENTS_REQUIRED`
- HSR condition: `HSR_CLOSING_CONDITION`, `NO_HSR_CONDITION_COOPERATION_ONLY`, `NOT_ADDRESSED`
- HSR basis: `SIZE_OF_PERSON_TEST_NOT_MET`, `REPORTABLE_THRESHOLDS_MET`, `COUNSEL_MEMO_MISSING`, `NOT_APPLICABLE`

### Non-Compete and Employment
- Non-compete scope: `TARGET_PRODUCTS_AND_CURRENT_TERRITORIES`, `WORLDWIDE_ALL_AFFILIATES`, `NO_NON_COMPETE`, `OTHER_LIMITED_SCOPE`
- Required offer standard: `BUYER_COMPARABLE_OFFERS_ALL_BUSINESS_EMPLOYEES`, `BUYER_OFFERS_SELECTED_CRITICAL_EMPLOYEES`, `NO_EMPLOYEE_COVENANT_REQUIRED`, `SELLER_RETAINS_EXCLUDED_EMPLOYEES_ONLY`

## List Ordering Rules

- **Seller allocations**: sort by `seller_name` ascending (or `seller_id` ascending when IDs are used)
- **Material consents**: sort by `contract_name` ascending
- **Employment employees**: sort by displayed employee name ascending
- **Issue registers**: sort by `issue_id` ascending
- **Escalation terms**: sort by `term_id` alphabetically
- **Code lists** (e.g., mae_omitted_carveouts, required_service_codes, override_codes): sort alphabetically
- **Source document IDs**: sort ascending
- **Committee members**: use exact displayed names, sorted ascending

## Task-Type Workflow Patterns

### Buyer-Side SPA Term Population (like train_001)
1. Fetch `/api/deals/{DEAL_ID}` for the target deal
2. Extract from `deal`: structure, target, buyer, seller, signing_date, closing_deadline, headline_value, equity_value, policy_id
3. Extract from `deal.economics`: consideration_mix, escrows, basket, indemnity_cap, survival_periods, working_capital
4. Extract from `deal.schedules`: cap_table (source_doc_id, as_of, status), material_contracts, employment_terms, regulatory_status, ip_transition, transition_services
5. Extract from `deal.parties`: sellers list (name, ownership_percent, role, estimated_proceeds)
6. Check `deal.client_positions` for escalation/fallback/preferred guidance
7. Cross-check economics against policy rules for policy_status fields
8. Compute per-share price or set null with basis explanation
9. Sort all lists per ordering rules

### Seller-Side APA Counterparty Review (like train_002)
1. Fetch `/api/deals/{DEAL_ID}`
2. Identify ACTIVE clauses; ignore STALE/TEMPLATE clauses at the same topic
3. Compare each active clause's `draft_value` against `playbook_value` and `policy_threshold`
4. Cross-reference against client email (`DOC-*-EMAIL-03`) for preferred/fallback/escalation positions
5. For each material deviation, create an issue with: issue_id from the controlled enum, severity, recommended_action, corrected_value (only relevant normalized fields), and source_ids (clause IDs, policy rule IDs, document IDs)
6. The `corrected_value` object uses only fields from the `corrected_value_allowed_fields` schema — never invent field names
7. Mark non-material topics as not issues (omit them)

### Committee Escalation Analysis (like train_003)
1. Fetch `/api/deals/{DEAL_ID}` including committee charter document if present
2. Identify every clause whose draft_value exceeds the policy_threshold
3. For each escalation term: determine deviation_code, severity, committee_route, approval_recommendation, recommendation, and quantification
4. Quantify economic exposure: compute draft_amount, excess above threshold, and exposure_basis
5. Aggregate: sum total_quantified_exposure and total_policy_excess across all terms
6. Populate strategic_context from deal.negotiation_context and deal.parties (ownership_context, batna, strategic_rationale)
7. Set benchmark_memo_required based on committee charter or policy guidance

### Seller-Side Carve-Out APA Review (like train_004)
1. Fetch `/api/deals/{DEAL_ID}`
2. Identify priority issues from active clauses — focus on TSA, employee transfer, restrictive covenants, IP transition, escrow, and closing deadline
3. For each priority issue: map clause_code to issue_id from the controlled enum
4. Populate transition_flags with structured findings for each transition area
5. TSA: compare draft duration and services against needed_services and required_duration from schedules
6. Employee: compare draft offer % against policy standard
7. Restrictive covenants: compare draft years/scope against policy maximums
8. IP: compare draft phase-out months and access scope against policy limits
9. Escrow and deadline: compute days from signing and compare against minimum

### Buyer-Side First-Draft SPA (like train_005)
1. Fetch `/api/deals/{DEAL_ID}`
2. Build draft_terms from deal profile: structure, parties, headline/equity values, dates
3. Compute seller allocations: multiply each seller's ownership_percent by each consideration component (cash_at_close, seller_note, rollover_equity, earnout); verify total matches headline_value
4. Build indemnity block: escrow percents and amounts, cap, basket, survival periods
5. Build closing conditions: material consents as closing conditions vs post-closing notice, HSR status and position, other approvals
6. Determine drafting positions from deal.draft_terms and deal.client_positions
7. Run policy checks: for each policy rule (ESCROW, CAP, BASKET, CONSENTS, HSR, NONCOMPETE, NWC), compare draft values against policy thresholds
8. Build risk_memo_overrides when active client instructions or deal-specific facts supersede template/stale material
9. The `hsr_override_basis` comes from the regulatory_status.basis text

## Common Pitfalls

1. **Using stale/template data**: Always check `version_status`. ACTIVE → use. STALE/TEMPLATE → ignore but record IDs for override documentation.
2. **Wrong seller_group / buyer name**: Use the exact name from `deal.seller` or `deal.buyer`, not from the parties list (which may list multiple entities).
3. **Employment employee names**: Use the full displayed name from `deal.parties.key_employees`, sorted alphabetically.
4. **Policy status at boundary**: "Exceeds X%" means > X%, not ≥ X%. A value at exactly the threshold is WITHIN_POLICY.
5. **Computed vs explicit amounts**: Prefer explicit dollar amounts from the deal economics or clause data. Compute only when values are absent.
6. **Null vs zero**: Zero dollars (`0`) means the item exists at zero value. `null` means the item is not applicable or not calculable.
7. **Client instructions override policy**: The client email's preferred/fallback/escalation positions take precedence over general policy rules.
8. **Missing clauses**: Not every topic has an active clause. Absence of an active clause for a topic (e.g., no active MAE clause) may mean the topic is not an issue for that deal — do not invent issues.
9. **Corrected values**: Include only fields relevant to the specific issue. Never include fields from other issue types.
10. **Benchmark relevance**: Use benchmarks from the same industry and year as the deal. Older/irrelevant-industry benchmarks are distractors.
