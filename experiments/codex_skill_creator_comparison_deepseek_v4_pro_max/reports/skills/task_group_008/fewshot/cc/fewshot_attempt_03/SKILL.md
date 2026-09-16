---
name: private-wealth-advisory
description: >
  Prepare structured wealth advisory JSON outputs (Roth conversion, ILIT Crummey,
  GRAT/CRAT comparison, or estate liquidity action plans) using a private advisory
  data API. Use this skill when the user mentions private wealth, advisory API,
  Roth conversion RMD analysis, ILIT Crummey funding, GRAT vs CRAT comparison,
  estate liquidity planning, or needs to build a structured advisory JSON from
  client records fetched over HTTP. Use it whenever the task refers to `API_BASE`,
  `answer_template.json`, `request_memo.md`, or a task-group advisory environment.
---

# Private Wealth Advisory JSON Generator

You are supporting a private wealth advisory team. Your task is to produce a
single, validated JSON output by querying a task-group advisory API and
computing the financial projections for the assigned client engagement.

## Input materials

Every task provides three files:

1. **`prompt.txt`** — the task framing (client ID, analysis type, output rules)
2. **`payloads/request_memo.md`** — engagement context; may contain the
   planning horizon year (e.g. "Planning horizon year: 2046") and other
   scoping notes.
3. **`payloads/answer_template.json`** — the exact JSON shape to emit,
   including required keys, enums, and field types.

The advisory API base URL is supplied by the harness, usually exposed as
`API_BASE` after the shared environment starts. All endpoints return JSON.

## API reference

| Endpoint                         | Description                                   |
|----------------------------------|-----------------------------------------------|
| `GET /api/clients/{client_id}`   | Single client record                          |
| `GET /api/source-documents`      | All source documents (CRM, attorney, signed)  |
| `GET /api/retirement-accounts`   | All retirement account exports                |
| `GET /api/life-insurance`        | All life insurance policies                   |
| `GET /api/trust-candidates`      | All trust candidate parameters                |
| `GET /api/policies/tax`          | Tax constants: exclusion, exemption, brackets |
| `GET /api/rmd-factors`           | RMD divisor table by age                      |

Returned records are sparse collections. Filter by **`client_id`** to get the
relevant entity. For collection endpoints, issue one GET and filter locally.

## Overall workflow

1. Read the three input files to determine `client_id`, `analysis_type`, and
   the target schema.
2. Fetch every API endpoint once and extract client-specific records.
3. Resolve source conflicts using `references/source_resolution.md`.
4. Apply the formulas from `references/tax_formulas.md` for the given
   `analysis_type`.
5. Populate the JSON skeleton from the template using computed values and
   resolved enums.
6. Output **only** the final JSON object — no prose, no markdown fences.

## Source resolution

Conflicting source documents must be resolved deterministically before any
computation. The full rule chain is in `references/source_resolution.md`.
The short rule:

- **Client profile facts** (income, beneficiaries, rates, priority, intent):
  `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
- **Financial account records** (balances, returns):
  `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`.

When a higher-priority source is silent on a specific fact, fall through to the
next source in the chain.

## Analysis-type dispatch

Read `references/analysis_types.md` for step-by-step instructions for each
`analysis_type` value. The analysis types covered are:

- `roth_conversion_rmd`
- `ilit_crummey_implementation`
- `trust_comparison`
- `estate_liquidity_action_plan`

## Key computation concepts

See `references/tax_formulas.md` for the full formula catalog. High-level
summary:

- **Annual conversion amount** = `conversion_bracket_target` – `annual_non_ira_income`.
- **Total conversion tax** = `total_converted` × `marginal_tax_rate`.
- **First RMD year** = `planning_year` + (`rmd_start_age` – `age`).
- **RMD per year** = `beginning_balance` / `rmd_factor`.
- **GRAT remainder** = `asset` × `(1 + growth)^term` – `asset` × `annuity_rate` × `term`.
- **CRAT charitable remainder** = `asset` × `(1 + growth)^term` – `asset` × `payout_rate` × `term`.
- **Estate tax exposure** = `taxable_estate` × `estate_tax_rate`.
- **Annual exclusion capacity** = `exclusion_per_beneficiary` × `beneficiary_count`.

All USD amounts are rounded to cents (two decimal places). All dates use ISO
8601 format (`YYYY-MM-DD`).

## Enum selection guidance

The answer template defines the allowed enum values for each field. Select
among them as follows:

### roth_conversion_rmd

- `recommendation.primary_action`: `STAGED_ROTH_CONVERSION` when conversion
  years ≥ 1; `DEFER` when age is very close to RMD start and savings are
  marginal; `NO_CONVERSION` when conversion produces no tax benefit.
- `recommendation.suitability`: `SUITABLE` when savings are meaningful and the
  plan is executable; `BORDERLINE` when the RMD start is within 1–2 years;
  `DEFER` when benefits are negligible.
- `recommendation.risk_flag`: `TAX_BRACKET_MANAGEMENT` is the default for
  suitable conversions; use `LIQUIDITY_CONSTRAINT` when liquid assets are low
  relative to total conversion tax; use `RMD_NEAR_TERM` when the first RMD year
  is within 1–2 years.
- `legacy_projection.heir_tax_profile`: `MIXED_TAXABLE_AND_TAX_FREE` when
  horizon balances are split between Roth and Traditional; `MOSTLY_TAX_FREE`
  when Roth dominates; `MOSTLY_TAXABLE` when Traditional dominates.

### ilit_crummey_implementation

- `recommendation.primary_action` depends on `premium_gap` and
  `is_existing_policy_transfer`:
  - Gap = 0, not existing → `FUND_WITH_CRUMMEY_NOTICES`
  - Gap > 0, not existing → `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`
  - Existing transfer, gap = 0 → `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`
  - Existing transfer, gap > 0 → `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION`
- `recommendation.suitability`: `SUITABLE_WITH_ADMINISTRATION` when
  formalities are the only concern; `BORDERLINE` with a gap or lookback;
  `NOT_SUITABLE` when gap is large and lookback applies.
- `recommendation.risk_flag`: `LOW_IF_FORMALITIES_MET` when no gap and no
  lookback; `EXCLUSION_SHORTFALL` when gap > 0; `THREE_YEAR_LOOKBACK` when
  existing policy transfer; combine both when both apply.
- `estate_result.estate_inclusion_risk`: same as `recommendation.risk_flag`.

### trust_comparison

- `recommendation.preferred_strategy`: `GRAT` when `family_transfer_priority`
  is at least as high as `philanthropic_intent`; `CRAT` when philanthropic
  intent is high and family transfer priority is low.
- `recommendation.rationale_code`: `CHILDREN_TRANSFER_PRIORITY` for GRAT;
  `PHILANTHROPIC_PRIORITY` for CRAT.
- `recommendation.alternate_role`: `SECONDARY_CHARITABLE_TOOL` when GRAT is
  primary; `SECONDARY_FAMILY_TRANSFER_TOOL` when CRAT is primary.
- `crat.family_transfer_fit`: `LOW` when CRAT is chosen largely for charity;
  `MODERATE` when priorities are mixed; `HIGH` when CRAT carries meaningful
  family benefit.

### estate_liquidity_action_plan

- `recommendation.primary_action`: `COMBINE_ILIT_AND_GRAT` when both ILIT and
  trust tools are appropriate; `CRAT_WITH_LIQUIDITY_REVIEW` when charitable
  intent is strong and liquidity gap is large; `ILIT_WITH_EXEMPTION_REVIEW`
  when only the ILIT path is needed.
- `recommendation.sequencing`: `ILIT_FIRST_THEN_GRAT` is the default when
  combining; `TRUST_DECISION_FIRST` when the trust choice drives the plan;
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when formalities require attorney
  coordination.
- `action_set`: the sorted list of applicable actions. Include
  `ILIT_CRUMMEY_NOTICE_CYCLE` when an ILIT is part of the plan,
  `GRAT_FOR_APPRECIATING_SHARES` when GRAT is the preferred strategy,
  `CRAT_FOR_CHARITABLE_REMAINDER` when CRAT is the preferred strategy,
  `LIFETIME_EXEMPTION_ALLOCATION` when exemption is needed, and
  `ATTORNEY_DRAFT_REVIEW` for attorney coordination. Sort alphabetically.

## Administration dates (ILIT)

Compute administration dates from `planned_contribution_date`:

- `notice_due_date` = contribution date + 7 days
- `withdrawal_window_end` = contribution date + 30 days
- `earliest_premium_payment_date` = withdrawal_window_end + 1 day
- `dedicated_bank_account_required` = `true` (standard for ILIT Crummey)

## Output rules

- Produce the final JSON object exactly matching the template's required keys.
- All numbers: JSON numbers (not strings), rounded to cents.
- All dates: ISO `YYYY-MM-DD`.
- All enums: exactly as listed in the template, case-sensitive.
- `task_id`: use the value given in prompt.txt (e.g. `"train_001"`).
- `client_id`: use the value from the memo and prompt.
- `analysis_type`: from the template's required key set.
- `horizon_year`: from the request memo when present, otherwise default to the
  `planning_year` + 20.
- Do not include any text, explanation, or markdown outside the JSON object.

## References

- **[source_resolution.md](references/source_resolution.md)** — full source conflict resolution chain for every field.
- **[tax_formulas.md](references/tax_formulas.md)** — all formulas: RMD projection, GRAT/CRAT, ILIT, estate tax.
- **[analysis_types.md](references/analysis_types.md)** — per-analysis-type step-by-step guides and edge cases.

## Bundled scripts

- **[compute_rmd.py](scripts/compute_rmd.py)** — deterministic RMD projection engine.
  Run `python scripts/compute_rmd.py --help` for usage. Use it to validate
  Roth conversion outputs or to compute projections mechanically from a
  resolved facts JSON object.
