 # Wealth Advisory Structured Output Skill

This skill equips a coding agent to produce structured JSON outputs for a private wealth advisory team by querying an advisory API, resolving conflicting source records, computing planning figures, and returning a template-conformant JSON object.

## Context

The agent acts as a support analyst for a private wealth advisory team. Each engagement asks for a structured JSON planning output for a specific client. The harness provides the advisory API base URL (usually as `API_BASE` in the environment) and a local request memo. The skill covers five analysis types.

## General Workflow

### Step 1 — Read the request memo and the answer template

1. Read `input/payloads/request_memo.md` to identify:
   - The client ID.
   - The engagement description (determines which analysis type applies).
   - Any horizon year or special constraints.
2. Read `input/payloads/answer_template.json` to understand the required output schema, key names, types, and enum values.
3. Determine the `analysis_type` by matching the template's `required_top_level_keys` to one of the five known analysis types (see below).

### Step 2 — Gather data from the advisory API

The API base URL is exposed by the harness, typically as the environment variable `API_BASE`. All endpoints are read-only `GET` calls.

**Available endpoints:**

| Endpoint | Purpose |
|---|---|
| `GET /` | Health check |
| `GET /api/clients` | List all client records (may contain duplicates from different source systems) |
| `GET /api/clients/{client_id}` | Single-client summary (may aggregate across sources) |
| `GET /api/source-documents` | Metadata and provenance for all source documents |
| `GET /api/retirement-accounts` | Retirement account balances, types (traditional, Roth), account sources |
| `GET /api/life-insurance` | Policy details: death benefit, premiums, ownership, beneficiaries, policy source |
| `GET /api/trust-candidates` | Trust-eligible assets, projected growth rates, available trust structures |
| `GET /api/policies/tax` | Tax brackets, exemption amounts, exclusion limits, rates by year |
| `GET /api/rmd-factors` | RMD divisors by age, first-RMD-age rules |
| `GET /portal/client/{client_id}` | Human-readable client portal page (supplementary context) |

Call every endpoint relevant to the analysis type. Cross-reference values because records from different source systems may conflict.

### Step 3 — Resolve conflicting source records

Clients may have multiple records because they were imported from different advisory systems at different times. When values conflict, prefer sources in this order of authority:

1. **SIGNED_PROFILE** — highest authority for client demographics, goals, beneficiary designations, and policy elections.
2. **ATTORNEY_MEMO** — highest authority for asset titles, trust structures, and legal-planning goals (but not for daily account balances).
3. **CUSTODIAN_EXPORT** — highest authority for current account balances, holdings, and tax-lot data.
4. **CRM_NOTE** — advisory notes; use only when no higher-authority source exists.
5. **STALE_MARKETING_INTAKE** — lowest authority; prefer any other source.

**Resolution rules by field category:**

- **Profile fields** (name, beneficiaries, goals, risk tolerance): prefer `SIGNED_PROFILE`.
- **Account balances / holdings**: prefer `CUSTODIAN_EXPORT`.
- **Asset valuation / trust funding data**: prefer `ATTORNEY_MEMO` for valuation estimates, `CUSTODIAN_EXPORT` for settled balances.
- **Life insurance policy details** (death benefit, premium): prefer `SIGNED_PROFILE` over `CUSTODIAN_EXPORT` over `CRM_NOTE`.
- Always record the chosen source in the `source_resolution` block using the exact enum values from the template.

### Step 4 — Compute the structured output

Using the resolved values, compute every field required by the template. Follow these computation and formatting rules:

- **USD amounts**: round to cents (two decimal places), expressed as JSON numbers (not strings).
- **Dates**: ISO 8601 `YYYY-MM-DD` format.
- **Enums**: use exactly the values listed in the template's `fields` block; do not invent new enum members.
- **Integers**: output as JSON numbers without a decimal point.
- **Booleans**: output as JSON `true` or `false`.
- **Lists**: sort alphabetically when the template requires it (e.g., `action_set`).

#### Analysis-type-specific computation notes

**1. `roth_conversion_rmd`** — Roth conversion and RMD tax summary
- Compute a staged conversion plan: annual amount ≤ available tax-bracket headroom, spread over conversion_years.
- `total_converted = conversion_years × annual_conversion_amount`.
- `total_conversion_tax = total_converted × marginal_tax_rate`.
- RMD projections: apply RMD factors by attained age starting at the first RMD year; compute tax on distributions under baseline (no conversion) and under conversion scenarios.
- `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`.
- Legacy projections: grow remaining traditional and Roth balances to the horizon year using assumed growth rates from the API.
- `heir_tax_profile`: `MOSTLY_TAX_FREE` if Roth > 2× traditional; `MOSTLY_TAXABLE` if traditional > 2× Roth; otherwise `MIXED_TAXABLE_AND_TAX_FREE`.
- `conversion_years_positive` equals `conversion_years` (must be > 0 if `STAGED_ROTH_CONVERSION`).

**2. `ilit_crummey_implementation`** — ILIT Crummey funding cycle
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count`.
- `premium_gap = annual_premium - annual_exclusion_capacity` (floor at 0; if negative, gap is 0.00).
- `notices_required = beneficiary_count` (one Crummey notice per beneficiary).
- `contribution_date`: the date contributions are made. `notice_due_date`: 7 days after contribution. `withdrawal_window_end`: 30 days after notice due. `earliest_premium_payment_date`: day after withdrawal window ends.
- `dedicated_bank_account_required`: `true` if premium is non-zero.
- `projected_outside_estate_if_implemented`: equals death benefit if risk is `LOW_IF_FORMALITIES_MET`; otherwise compute proportionally.
- `tax_liquidity_support = death_benefit × effective_tax_rate` (typically ~40%).

**3. `trust_comparison`** — GRAT versus CRAT
- GRAT: use §7520 rate from tax policies; project remainder to heirs assuming growth rate from trust-candidates exceeds the hurdle; mortality inclusion risk is always `TERM_SURVIVAL_REQUIRED`.
- CRAT: compute present value of charitable remainder using term and §7520 rate; `estimated_income_tax_deduction` is a fraction of funding amount.
- `family_transfer_fit`: `LOW` if primary goal is children/heirs; `HIGH` if philanthropic. In practice, when comparing GRAT vs CRAT and recommending GRAT (children priority), CRAT's family transfer fit is `LOW`.
- `rationale_code`: `CHILDREN_TRANSFER_PRIORITY` when preferring GRAT; `PHILANTHROPIC_PRIORITY` when preferring CRAT.

**4. `estate_liquidity_action_plan`** — Combined estate liquidity, ILIT, and trust transfer
- Combines elements of ILIT analysis and trust comparison.
- Compute `liquidity_gap_before_planning = estate_tax_exposure - liquid_assets_available` (floor at 0).
- Build `action_set` as an alphabetically sorted list of applicable actions.
- GRAT is preferred for appreciating shares; CRAT for charitable remainder.

### Step 5 — Output the final JSON

Return only a JSON object that conforms to the answer template. No prose, no markdown fences, no commentary. Include every required top-level key. Set `task_id` to the task identifier provided by the harness (e.g., `train_001`, `test_001`).

## Analysis Type Identification

Match the template's `required_top_level_keys` to the analysis type:

| Required keys include... | analysis_type |
|---|---|
| `conversion_plan`, `rmd_projection` | `roth_conversion_rmd` |
| `gift_plan`, `administration` | `ilit_crummey_implementation` |
| `grat`, `crat` | `trust_comparison` |
| `ilit`, `trust_transfer`, `action_set` | `estate_liquidity_action_plan` |

If the template does not match one of these, stop and report the mismatch.

## Error Handling

- If an API endpoint returns an error or is unreachable, retry once. If still failing, note which data could not be obtained and proceed with the best available data from other sources.
- If source documents are irreconcilably contradictory (e.g., two SIGNED_PROFILE records with different values), prefer the most recently dated record.
- If a required computation cannot be completed due to missing data, use `0` or `0.00` for numeric fields and document the gap in source_resolution.
