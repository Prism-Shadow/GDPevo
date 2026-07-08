# Skill: Structured Financial JSON Generation from Portfolio Data

## When to Use

Use this skill when given a prompt and one or more JSON payload files that describe a portfolio management, risk analysis, or performance attribution task, and you must produce a structured JSON answer conforming to a strict schema template.

## Overview

These tasks require reading financial data from a request JSON, performing precise quantitative calculations, and emitting a response JSON that exactly matches a provided schema template. The schema defines required top-level keys, field types, enum values, ordering rules, and numeric precision. Errors in calculation, field ordering, or enum values will cause rejection.

## Step-by-Step Procedure

### 1. Read All Input Files

Read the `prompt.txt`, the request JSON (e.g., `desk_request.json`, `review_request.json`, `allocation_request.json`, `risk_meeting_memo.json`, `committee_request.json`), and the `answer_template.json`. Do not skip any file — the prompt may contain critical context (e.g., benchmark definitions, lookback periods, calculation conventions) not repeated in the JSON.

### 2. Map the Schema Requirements

From `answer_template.json`, extract and document:

- **Required top-level keys** — the exact key names and their order.
- **Field definitions** — for each key, note:
  - `type` (string, number, boolean, list, enum)
  - `format` (e.g., `YYYY-MM-DD`)
  - `required_value` (exact literal required)
  - `precision` (decimal places for numbers)
  - `length` (for lists)
  - `item_order` (ordered list of names — output must match this order)
  - `allowed_values` (enum constraints)
  - `ordering_rule` (e.g., "alphabetical", "descending by weight")
  - `calculation` (formula description — follow exactly)

Create a checklist of every required field. Do not omit optional fields unless the schema explicitly marks them absent.

### 3. Extract Raw Data from the Request JSON

Identify all numerical inputs:
- Holdings: quantities, prices, market values, weights
- Market data: index levels, returns, dates
- Risk parameters: volatilities, correlations, VaR thresholds
- Cash flows, fees, accruals, FX rates

Organize data by entity (portfolio, benchmark, sleeve, asset class, security) and by time period (inception, YTD, quarterly, monthly).

### 4. Perform Calculations Methodically

For each calculated field in the schema, compute the value using the exact method specified. Common calculation patterns in these tasks:

#### Returns
- **Simple return**: `(End - Start) / Start`
- **Time-weighted / cumulative**: chain-link periodic returns
- **Annualized**: `(1 + total_return)^(365/days) - 1` or `(1 + total_return)^(12/months) - 1`
- **Benchmark returns**: apply the same method to benchmark levels

#### Portfolio Metrics
- **NAV**: sum of market values + cash - liabilities
- **Gross / Net exposure**: sum of absolute market values / NAV
- **Number of positions**: count of non-cash holdings
- **Cash weight**: cash / NAV

#### Attribution
- **Allocation effect**: `(Portfolio_weight - Benchmark_weight) × Benchmark_return`
- **Selection effect**: `Portfolio_weight × (Portfolio_return - Benchmark_return)`
- **Interaction / residual**: total active return - allocation - selection
- **Active return**: Portfolio_return - Benchmark_return

#### Risk Metrics
- **Volatility / standard deviation**: sample std dev of periodic returns (usually simple returns, not log)
- **Correlation (Pearson)**: of monthly simple returns from consecutive index levels
- **Beta**: `Cov(portfolio, benchmark) / Var(benchmark)`
- **VaR (parametric)**: `Portfolio_value × (Z_score × volatility - mean_return)` for the specified confidence and horizon
- **Max drawdown**: maximum peak-to-trough decline over the period
- **Tracking error**: std dev of active returns
- **Information ratio**: active return / tracking error
- **Sharpe ratio**: `(Portfolio_return - Risk_free) / Portfolio_volatility`

#### Allocation & Sleeves
- **Sleeve weight**: sleeve market value / total portfolio market value
- **Target deviation**: sleeve weight - target weight
- **Signal score**: weighted average of underlying signals (follow the exact weights in the prompt)
- **Correlation matrix**: Pearson correlation of monthly simple returns; output upper/lower triangle or full matrix per schema

**Precision rule**: Round all numbers to the exact decimal places specified in the schema (commonly 3, 4, or 6). Do not truncate — round half-up. For percentages expressed as decimals (e.g., 0.0523), respect the schema's precision.

### 5. Respect Ordering Rules

The schema often enforces order within lists:
- `item_order` arrays dictate the exact sequence of list elements.
- `ordering_rule` fields may require sorting by name, weight, or return.
- Within pairs (e.g., correlation pairs), sort index IDs alphabetically unless instructed otherwise.

Always verify the output list order matches the schema before finalizing.

### 6. Handle Enums Exactly

Enum fields must contain one of the `allowed_values` exactly. Common enum sets include:
- Actions: `trim`, `add`, `hold`, `hedge`, `monitor`, `rotate`
- Views: `UW` (underweight), `N` (neutral), `OW` (overweight)
- Changes: `UP`, `DOWN`, `UNCHANGED`
- Conviction: `LOW`, `MEDIUM`, `HIGH`
- Rationale codes: `GROWTH_IMPROVES`, `RATE_CUT_SUPPORT`, `CREDIT_SPREAD_RISK`, `DOLLAR_DEFENSIVE`, `CHINA_DEPENDENCE`, `LATAM_DIVERSIFIER`, `INDIA_OFFSET`, `DURATION_SUPPORT`, `HY_VALUATION_RISK`, `EUROPE_RECOVERY`, `JAPAN_POLICY_RISK`, `NEUTRAL_BALANCE`
- Rebalance triggers: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`
- Next steps: `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`

Never invent values. Map the computed or narrative result to the closest allowed enum.

### 7. Construct the Output JSON

Build the JSON object with:
- All required top-level keys present
- Keys in the order specified by `required_top_level_keys` (or natural insertion order if not specified)
- Correct types for every field
- Correct list lengths
- Correctly ordered list items
- Correctly rounded numbers
- Exact enum values
- Exact required string literals (e.g., `portfolio_id: "PF-MA-HELIO"`)

### 8. Validate Before Returning

Run a self-check:
1. **Schema completeness**: Does every required top-level key exist?
2. **Type check**: Are all fields the correct JSON type?
3. **Enum check**: Are all enum values in the allowed list?
4. **Order check**: Do lists follow `item_order` or `ordering_rule`?
5. **Precision check**: Are numbers rounded to the specified decimal places?
6. **Calculation check**: Recompute at least one critical metric by hand to verify methodology.
7. **JSON validity**: Is the output parseable JSON with no trailing commas?

If any check fails, correct and re-validate.

## Common Pitfalls to Avoid

- **Using log returns when simple returns are specified** (or vice versa). The schema's `calculation` field usually specifies which to use.
- **Forgetting to annualize** returns or volatility when the output expects annualized figures.
- **Wrong sign on attribution** — allocation and selection effects can be positive or negative; do not force-positive.
- **Mixing gross vs. net** returns — check whether fees are deducted.
- **Incorrect VaR formula** — parametric VaR uses the portfolio value, Z-score, and volatility; verify the confidence level (95% → 1.645, 99% → 2.326).
- **Correlation matrix symmetry** — ensure matrix is symmetric and diagonal is 1.0 (or omitted, per schema).
- **Date formats** — use exactly `YYYY-MM-DD` unless specified otherwise.
- **Missing cash** in portfolio market value or weight calculations.
- **Off-by-one in drawdown** — max drawdown is the largest decline from a peak to a subsequent trough, not the final value from the peak.

## Example Workflow Summary

```
Read prompt.txt → Read request JSON → Read answer_template.json
↓
Map schema: keys, types, enums, precision, ordering, calculations
↓
Extract and organize all raw numerical data
↓
Calculate each field using the exact specified method
↓
Round to schema precision, select exact enum values
↓
Order lists per schema rules
↓
Build JSON object with all required keys
↓
Self-validate: completeness, types, enums, order, precision, JSON syntax
↓
Return final JSON
```
