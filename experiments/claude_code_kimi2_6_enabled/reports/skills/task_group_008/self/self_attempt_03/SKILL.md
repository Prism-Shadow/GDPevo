# Roth Conversion RMD Analysis Skill

## 1. Task Overview

This task produces a structured JSON analysis evaluating whether a Roth conversion strategy is appropriate for a given client. The analysis covers:
- Conversion plan (timing, amounts, tax cost)
- RMD projections (baseline vs. conversion scenarios)
- Legacy/estate outcomes
- Source resolution (which data sources govern)
- Recommendation (suitability, risk flags, primary action)

**Output format:** Strict JSON conforming to the provided `answer_template.json` schema. The top-level object must contain exactly: `task_id`, `client_id`, `analysis_type`, `recommendation`, `conversion_plan`, `rmd_projection`, `legacy_projection`, `source_resolution`.

**Important:** Numbers must be JSON numbers (not strings). USD amounts are rounded to cents (2 decimal places). Dates use ISO format where requested.

---

## 2. Input Files

Every task provides three staged files in `input/payloads/`:
1. **`prompt.txt`** — Describes the client and high-level ask (e.g., "Evaluate Roth conversion for client_id CL-001").
2. **`request_memo.md`** — **The authoritative business logic document.** Contains specific calculation rules, horizon year, source-resolution overrides, and edge-case handling for this client.
3. **`answer_template.json`** — JSON schema specifying required keys, field types, and enums.

**Procedure:**
1. Read `prompt.txt` to identify `client_id`.
2. Read `request_memo.md` carefully — rules vary per client (liquidity checks, tax-bracket guardrails, signed-profile requirements, etc.).
3. Read `answer_template.json` to confirm the exact output schema.

---

## 3. Data Gathering

### 3.1 API Endpoints
The environment exposes a remote API. The primary endpoint discovered is:
- `GET {GDPEVO_ENV_BASE_URL}/api/clients` — Returns all client records.

The request_memo may reference additional endpoints (e.g., `/api/v1/data?client_id=<id>`, `/api/v1/account-ledger?client_id=<id>`). If those endpoints are unavailable, the client record from `/api/clients` and any data embedded in the request_memo itself serve as the authoritative source.

**Data needed from sources:**
- `age`, `filing_status` (e.g., MFJ, SINGLE), `marital_status`
- `planning_year`, `estate_value`, `liquid_assets`
- Traditional IRA balance, Roth IRA balance
- `heir_tax_rate` (if available)
- Source metadata: whether a `SIGNED_PROFILE` exists, whether `CUSTODIAN_EXPORT` or `CRM_NOTE` data is present

### 3.2 Source Resolution Hierarchy
When sources conflict, use this precedence (the request_memo may override for a specific client):

**Profile data (age, filing status, heir info):**
1. `SIGNED_PROFILE`
2. `ATTORNEY_MEMO`
3. `CUSTODIAN_EXPORT`
4. `CRM_NOTE`
5. `STALE_MARKETING_INTAKE`

**Account data (IRA balances):**
1. `CUSTODIAN_EXPORT`
2. `SIGNED_PROFILE`
3. `CRM_NOTE`

**Critical edge case — Missing signed profile:**
If no `SIGNED_PROFILE` exists for the client, the controlling profile source falls back to `CUSTODIAN_EXPORT` or `CRM_NOTE`. Some memos explicitly require `primary_action = NO_CONVERSION` and zero out all conversion amounts when no signed profile is present. Always defer to the request_memo for the specific override.

---

## 4. Conversion Plan Calculation

### 4.1 Core Formula (default case)
1. **Deduction:** Subtract available Roth balances from total IRA balance. The remainder is the **traditional balance** to convert.
2. **Horizon:** `conversion_years` = number of years from `planning_year` through `horizon_year` (inclusive).
3. **Positive years:** `conversion_years_positive` = number of years within the horizon that have a positive conversion amount. The request_memo may specify this directly.
4. **First conversion year:** `first_conversion_year` = the first year within the horizon with a positive conversion amount. The request_memo may specify this (it is **not** always `planning_year`).
5. **Annual amount:** `annual_conversion_amount` = traditional balance ÷ `conversion_years_positive`, rounded to cents.
6. **Total converted:** `total_converted` = traditional balance (the full amount to be converted over the plan).
7. **Total conversion tax:** `total_conversion_tax` = `total_converted` × effective tax rate, rounded to cents.

### 4.2 Tax Bracket Lookups
- Obtain the tax bracket schedule from the source referenced in the request_memo (often `filing_status_brackets` or embedded table).
- Determine the client's **effective tax rate** (weighted average of brackets for their taxable income).
- Determine the client's **marginal tax rate** (top bracket their taxable income reaches).
- **RMD tax calculations must use the effective tax rate, not the marginal rate.**

### 4.3 Liquidity Guardrail
If the request_memo specifies a liquidity check:
- Compute the annual conversion amount.
- If `annual_conversion_amount > (liquid_assets − reserve)` (commonly `reserve = 50,000`), do **not** convert. Set conversion amounts to 0 or follow the memo's specific instruction (e.g., cap the amount, set primary_action to DEFER).

### 4.4 Tax-Bracket Guardrail
If the request_memo specifies a tax-bracket guardrail:
- Ensure the annual conversion keeps the client's taxable income within their current bracket.
- If converting pushes taxable income into the next bracket, run a **no-conversion scenario**:
  - `annual_conversion_amount = 0`
  - `total_converted = 0`
  - `total_conversion_tax = 0`
  - `conversion_rmd_tax_through_horizon = baseline_rmd_tax_through_horizon`

### 4.5 No-Conversion Override
Some clients explicitly require `primary_action = NO_CONVERSION` (e.g., when no signed profile exists, or when the memo defers conversion pending executed profile). In these cases:
- Set all conversion amounts to 0.
- Set total conversion tax to 0.
- Ensure `conversion_rmd_tax_through_horizon` equals `baseline_rmd_tax_through_horizon`.

---

## 5. RMD Projection Calculation

### 5.1 First RMD Year
- Use the IRS rule: first RMD year is the year the client turns 73.
- Compute from `planning_year` and current `age`.

### 5.2 Uniform Lifetime Table / Nearest-Age Method
- Use the IRS Uniform Lifetime Table factors.
- **Nearest-age method:** Round the client's age to the nearest integer; `.5` rounds up.
- RMD for a year = account balance at start of year ÷ Uniform Lifetime Table factor for the client's nearest age in that year.

### 5.3 Baseline vs. Conversion Scenarios
- **Baseline:** No Roth conversion; RMDs are taken from the full traditional balance each year.
- **Conversion:** Traditional balance is reduced by conversions; RMDs are taken from the remaining traditional balance.
- For each year through the horizon, compute the RMD amount, then multiply by the **effective tax rate** to get the RMD tax for that year.
- Sum across all years to get:
  - `baseline_rmd_tax_through_horizon`
  - `conversion_rmd_tax_through_horizon`
- `rmd_tax_savings_through_horizon` = `baseline_rmd_tax_through_horizon` − `conversion_rmd_tax_through_horizon`

### 5.4 Important Notes
- Roth IRAs do **not** have RMDs during the owner's lifetime.
- The same tax bracket lookup must be used for both baseline and conversion scenarios.
- Always round final USD totals to cents.

---

## 6. Legacy Projection Calculation

1. **Projected Roth balance at horizon:** Start with existing Roth balance + total converted − any growth/withdrawals assumptions per memo. If no growth assumption is given, the Roth balance at horizon = existing Roth + total converted.
2. **Projected traditional balance at horizon:** Start with traditional balance − total converted. RMDs reduce this further through the horizon.
3. **Heir tax profile:**
   - Determine `heir_tax_rate`. If not explicitly given, assume it equals the client's current effective tax rate.
   - If `heir_tax_rate < 25%` → `MOSTLY_TAX_FREE`
   - If `heir_tax_rate >= 25%` → `MOSTLY_TAXABLE`
   - Otherwise → `MIXED_TAXABLE_AND_TAX_FREE`

---

## 7. Recommendation Logic

The request_memo may specify exact suitability rules. The common pattern observed:

### 7.1 Suitability
- **DEFER** if: `age > 70` OR `liquid_assets < 2 × conversion_years` OR no signed profile exists (per memo override).
- **BORDERLINE** if: `age > 65` OR `marginal_rate > 28%` OR `roth_fraction > 0.30`.
- **SUITABLE** otherwise.

### 7.2 Primary Action
- `STAGED_ROTH_CONVERSION` — Default when conversion is viable and suitable.
- `DEFER` — When suitability is DEFER or liquidity is insufficient.
- `NO_CONVERSION` — When explicitly mandated by the memo (e.g., missing signed profile, or conversion pushes into next bracket with no-conversion scenario).

### 7.3 Risk Flag
- `TAX_BRACKET_MANAGEMENT` — When the conversion amount is large enough to push taxable income into a higher bracket, or when the memo explicitly flags this.
- `LIQUIDITY_CONSTRAINT` — When liquid assets are insufficient relative to conversion plan or annual conversion exceeds liquid assets minus reserve.
- `RMD_NEAR_TERM` — When the client is close to RMD age (e.g., age 72 or first RMD year is within the near term).

**Note:** The request_memo may explicitly select the risk flag for a given client. When it does, follow it exactly.

---

## 8. Output Assembly

Construct a single JSON object with these exact top-level keys:

```json
{
  "task_id": "<folder name, e.g. train_001 or test_001>",
  "client_id": "<from prompt / memo>",
  "analysis_type": "roth_conversion_rmd",
  "recommendation": {
    "primary_action": "STAGED_ROTH_CONVERSION | DEFER | NO_CONVERSION",
    "suitability": "SUITABLE | BORDERLINE | DEFER",
    "risk_flag": "TAX_BRACKET_MANAGEMENT | LIQUIDITY_CONSTRAINT | RMD_NEAR_TERM"
  },
  "conversion_plan": {
    "first_conversion_year": <int>,
    "conversion_years": <int>,
    "conversion_years_positive": <int>,
    "annual_conversion_amount": <number>,
    "total_converted": <number>,
    "total_conversion_tax": <number>
  },
  "rmd_projection": {
    "horizon_year": <int>,
    "first_rmd_year": <int>,
    "baseline_rmd_tax_through_horizon": <number>,
    "conversion_rmd_tax_through_horizon": <number>,
    "rmd_tax_savings_through_horizon": <number>
  },
  "legacy_projection": {
    "projected_roth_balance_horizon": <number>,
    "projected_traditional_balance_horizon": <number>,
    "heir_tax_profile": "MOSTLY_TAX_FREE | MIXED_TAXABLE_AND_TAX_FREE | MOSTLY_TAXABLE"
  },
  "source_resolution": {
    "controlling_profile_source": "SIGNED_PROFILE | ATTORNEY_MEMO | CUSTODIAN_EXPORT | CRM_NOTE | STALE_MARKETING_INTAKE",
    "controlling_account_source": "CUSTODIAN_EXPORT | SIGNED_PROFILE | CRM_NOTE"
  }
}
```

### 8.1 Validation Checklist
- [ ] All required top-level keys are present.
- [ ] `analysis_type` is exactly `"roth_conversion_rmd"`.
- [ ] All enums match one of the permitted values exactly (case-sensitive).
- [ ] All USD amounts are numbers with at most 2 decimal places.
- [ ] `rmd_tax_savings_through_horizon` equals baseline minus conversion.
- [ ] `task_id` matches the task folder or memo identifier.
- [ ] `source_resolution` reflects the actual hierarchy used after resolving conflicts.

---

## 9. Common Pitfalls

1. **Ignoring the request_memo override.** The `request_memo.md` is authoritative. Two clients with the same age and filing status can have completely different rules (e.g., one requires NO_CONVERSION because of a missing signed profile).
2. **Using marginal rate for RMD tax.** The memo explicitly states: *"For RMD tax, use the effective tax rate, not the marginal rate."*
3. **Wrong first_conversion_year.** The first conversion year is **not** always `planning_year`. The memo may specify a later start year (e.g., `first_conversion_year = 2030` while `planning_year = 2026`).
4. **Forgetting Roth balance deduction.** Deduct available Roth balances from total IRA balance **before** computing the traditional balance to convert.
5. **Mismatching heir_tax_profile thresholds.** The threshold is strictly `< 25%` vs `>= 25%`.
6. **API endpoint assumptions.** Do not hardcode endpoint paths. The memo may reference `/api/v1/data` or `/api/v1/account-ledger`, but the actual available endpoints can vary by environment. Always verify what endpoints exist.
7. **Rationale vs. JSON.** Some memos ask for a plain-text rationale "not part of the JSON." The primary deliverable is always the JSON object; include rationale only if the memo explicitly requires it and the test harness expects it.
8. **Source resolution laziness.** Always check whether a `SIGNED_PROFILE` exists. If it does not, the controlling source and the recommendation may both change.

---

## 10. Quick Reference: Calculation Order

1. Gather client data (API + memo).
2. Resolve source hierarchy → set `source_resolution`.
3. Determine `horizon_year` from memo.
4. Compute `first_rmd_year` (age 73 rule).
5. Deduct Roth from total IRA → traditional balance.
6. Determine `conversion_years` and `conversion_years_positive`.
7. Compute `annual_conversion_amount`.
8. Apply liquidity guardrail if specified.
9. Apply tax-bracket guardrail if specified.
10. Compute `total_converted` and `total_conversion_tax`.
11. Run baseline RMD tax projection.
12. Run conversion RMD tax projection.
13. Compute `rmd_tax_savings_through_horizon`.
14. Compute legacy projection and `heir_tax_profile`.
15. Determine `suitability`, `primary_action`, and `risk_flag`.
16. Assemble and validate JSON.
