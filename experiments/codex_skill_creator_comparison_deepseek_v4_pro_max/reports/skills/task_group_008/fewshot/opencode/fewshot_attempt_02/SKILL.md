---
name: wealth-advisory-planner
description: Prepare structured private-wealth advisory JSON outputs for tax, retirement, estate, and insurance planning engagements. Use this skill whenever the task involves a private wealth advisory team, client planning outputs, Roth conversions, RMD projections, ILIT Crummey funding, GRAT/CRAT comparisons, estate liquidity action plans, or any structured advisory JSON with API-backed client data. Also use it when the task mentions advisory API base URLs, client IDs like CLT-XXXX, or an advisor request memo.
---

# Wealth Advisory Planning

This skill produces structured JSON for private wealth advisory engagements covering Roth conversions, ILIT Crummey funding, trust comparisons, and estate liquidity planning. All data comes from a task-group advisory API; no local computation can replace API lookups.

## High-level workflow

1. Parse the request memo for `client_id`, engagement type, and planning horizon.
2. Read the `answer_template.json` in the task payloads to know the exact output schema.
3. Query the advisory API for all relevant data endpoints.
4. Resolve conflicting source records using the priority rules below.
5. Compute numeric outputs using the formulas in [references/formulas.md](references/formulas.md).
6. Select enum values using the decision logic in [references/enums.md](references/enums.md).
7. Return a single JSON object matching the template; no prose outside the JSON.

## API reference

The harness exposes the advisory API at `API_BASE` or via the configured base URL from `environment_access.md`. All endpoints are read-only GETs. See [references/api-reference.md](references/api-reference.md) for the full endpoint catalog with field descriptions.

For any client engagement, query these endpoints in parallel, filtering by `client_id` where applicable:

- `GET /api/clients/{client_id}` — demographic, estate value, liquid assets, filing status
- `GET /api/source-documents` — filter to the client; used for profile facts, priority, and conflict resolution
- `GET /api/retirement-accounts` — filter to the client; traditional/roth balances, expected return, recommended conversion years
- `GET /api/life-insurance` — filter to the client; death benefit, premium, contribution date, existing-policy-transfer flag
- `GET /api/trust-candidates` — filter to the client; asset value, growth rate, GRAT/CRAT parameters
- `GET /api/policies/tax` — static tax constants (annual gift exclusion, estate tax exemption, estate tax rate, bracket targets, charitable deduction rate)
- `GET /api/rmd-factors` — static RMD divisor table by age

The `/api/clients` list endpoint is optional and only needed for client-id lookup or context.

## Source resolution

Client records may conflict because systems imported data at different times. Resolve every conflict using the priority hierarchy in [references/source-resolution.md](references/source-resolution.md). The controlling source for each fact category feeds both the `source_resolution` output and the numeric calculations.

The most recent `SIGNED_PROFILE` (by `effective_date`) is the default authority for profile facts (age, income, beneficiaries, filing status, philanthropic intent, family transfer priority). `CUSTODIAN_EXPORT` controls account balances, RMD start age, and expected returns. `ATTORNEY_MEMO` controls estate value and can override asset source selections for trust engagements.

A `CRM_NOTE` is stale and used only when no other source for that fact exists. A `STALE_MARKETING_INTAKE` source type, if present, ranks below CRM notes.

## Analysis dispatch

Read the request memo and the `answer_template.json` to determine the analysis type. The template’s `analysis_type` field (or the `required_top_level_keys`) tells you which output schema applies:

| Template signature | Analysis type | Reference section |
|---|---|---|
| `conversion_plan` + `rmd_projection` + `legacy_projection` | `roth_conversion_rmd` | [references/formulas.md](references/formulas.md): Roth Conversion |
| `gift_plan` + `administration` + `estate_result` | `ilit_crummey_implementation` | [references/formulas.md](references/formulas.md): ILIT Crummey |
| `grat` + `crat` + `estate_context` | `trust_comparison` | [references/formulas.md](references/formulas.md): Trust Comparison |
| `ilit` + `trust_transfer` + `action_set` | `estate_liquidity_action_plan` | [references/formulas.md](references/formulas.md): Estate Liquidity |

## Output rules

Every output must be a single JSON object with no surrounding prose or markdown. Apply these rules uniformly:

- `task_id` is the stable task identifier from the prompt (e.g., `"train_001"` or the test environment equivalent).
- `client_id` is the client identifier from the memo.
- All USD amounts are JSON numbers rounded to two decimal places (cents).
- All dates use ISO 8601 `YYYY-MM-DD` format.
- Enum values must exactly match the allowed values in the answer template; no approximations or near-matches.
- `action_set` arrays in estate liquidity outputs must be sorted alphabetically.
- Numbers must be JSON number types, never strings.

Use the bundled Python script [scripts/compute.py](scripts/compute.py) for deterministic numeric calculations. Call it with the relevant arguments for each analysis section; it prints JSON to stdout for integration into the final output.
