---
name: wealth-advisory-planner
description: "Structured wealth advisory planning for private wealth teams. Produces JSON outputs for Roth conversion and RMD analysis, ILIT Crummey funding implementation, GRAT vs CRAT trust comparisons, and combined estate liquidity action plans. Use when the task involves a client from the advisory environment, an answer_template.json with wealth advisory fields, API calls to the advisory API surface (clients, source documents, retirement accounts, life insurance, trust candidates, tax policies, RMD factors), or request memos referencing Roth conversions, ILIT, Crummey notices, GRAT, CRAT, estate liquidity, or source document conflict resolution."
license: MIT
compatibility: designed for deepagents-code
---

# Wealth Advisory Planner

## Overview

This skill produces structured JSON planning outputs for private wealth advisory engagements. It fetches from the advisory API, resolves conflicts across source documents, performs domain calculations, and returns JSON conforming to the supplied answer template.

## Workflow

1. Read the task `input/prompt.txt`, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
2. Extract `client_id` and `analysis_type` from the memo and template.
3. Gather data from the advisory API (see [references/api_surface.md](references/api_surface.md)).
4. Resolve source conflicts (see [references/source_resolution.md](references/source_resolution.md)).
5. Execute the analysis (see [references/analysis_types.md](references/analysis_types.md)).
6. Fill the answer template conforming to [references/answer_templates.md](references/answer_templates.md).
7. Output only the final JSON object with no surrounding prose.

### Step 1: Read Task Inputs

Read all three payload files in `input/payloads/` to understand the engagement:

- `prompt.txt`: Task framing and `API_BASE` reference
- `request_memo.md`: Client ID, engagement type, planning horizon, output instructions
- `answer_template.json`: Required JSON structure with all `required_top_level_keys` and field enums

The template's `analysis_type` enum value tells you which analysis to run.

### Step 2: Gather API Data

Fetch all data the analysis needs. Always set `API_BASE` from the prompt environment. Make all GET calls in parallel when possible.

Read [references/api_surface.md](references/api_surface.md) for the full API surface and field shapes. The minimum set per analysis type:

| Analysis Type | Endpoints to Fetch |
|---|---|
| roth_conversion_rmd | clients, source-documents, retirement-accounts, policies/tax, rmd-factors |
| ilit_crummey_implementation | clients, source-documents, life-insurance, policies/tax |
| trust_comparison | clients, source-documents, trust-candidates, policies/tax |
| estate_liquidity_action_plan | clients, source-documents, life-insurance, trust-candidates, policies/tax |

Always filter source-documents, retirement-accounts, life-insurance, and trust-candidates by `?client_id={client_id}`.

### Step 3: Resolve Source Conflicts

Source documents may disagree. Follow the priority rules in [references/source_resolution.md](references/source_resolution.md):

- SIGNED_PROFILE overrides ATTORNEY_MEMO, which overrides CRM_NOTE
- CUSTODIAN_EXPORT is authoritative for account balances. Never override with profile data.
- Beneficiary count always from SIGNED_PROFILE
- Life insurance data from the `/api/life-insurance` endpoint is authoritative

### Step 4: Execute Analysis

Read [references/analysis_types.md](references/analysis_types.md) for the full computation formulas. Key principles:

- Use `curl` to the `API_BASE` for all data; never hardcode values from training examples
- All monetary values in USD rounded to cents (2 decimals)
- Years as integers, dates as ISO YYYY-MM-DD
- Use the rmd-factors endpoint for RMD divisors; use the tax policy endpoint for all rates and thresholds
- Grow accounts year-by-year using `expected_return`; apply RMD divisors when age >= rmd_start_age
- For GRAT projections: compound the trust asset at `expected_growth_rate`, subtract annuity each year
- For CRAT projections: same compounding, subtract payout each year, cap term at `max_crat_term_years`

### Step 5: Fill Answer Template

Read [references/answer_templates.md](references/answer_templates.md) for template field reference. Conform exactly to the template's required_top_level_keys. Every value must match its declared type (number, string, boolean, enum, array). Enums must use the exact strings from the template.

Set `task_id` from the task directory name (e.g. `train_001`, `test_001`). Use the same identifier string that appears in the prompt or path.

### Step 6: Output

Return only the JSON object. No markdown fences, no explanatory prose, no trailing text. The JSON must be valid and parseable.

## Important Constraints

- Never output task-specific values from training examples as defaults. Always compute from API data.
- Do not use a Python script to fetch API data; use `curl` shell commands.
- Do not guess API values. Every number must come from an endpoint response.
- The `API_BASE` variable is supplied by the task harness; check the environment or prompt for the actual URL.
- `estate_tax_rate` is always 0.4, `rmd_start_age` is 73 (confirm from retirement account record).
- `planning_year` defaults to 2026 from the client record or tax policy.

## References

- [API Surface](references/api_surface.md) - Full endpoint listing with field shapes
- [Source Conflict Resolution](references/source_resolution.md) - Priority rules for conflicting documents
- [Analysis Types](references/analysis_types.md) - Computation formulas for each analysis type
- [Answer Templates](references/answer_templates.md) - Template field reference and enum values
