## Private Wealth Advisory Structured Output Skill

### Overview

This skill handles private wealth advisory planning tasks that require querying a REST API for client data, resolving conflicts across data sources, computing tax and estate-planning figures, and returning a structured JSON object conforming to a provided answer template.

The advisory domain covers Roth conversions, RMD projections, ILIT Crummey funding, GRAT vs. CRAT trust comparisons, and estate liquidity action plans. Each task follows the same general workflow but uses a distinct output schema defined by an `answer_template.json` payload.

### Environment

The advisory API base URL is read from the environment variable `GDPEVO_ENV_BASE_URL`. If that variable is not set, fall back to `API_BASE`. The URL ends with a trailing `/`. Verify connectivity with `GET /` before making data calls.

### API Endpoint Reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check |
| GET | `/api/clients` | List all client records |
| GET | `/api/clients/{client_id}` | Single client record (profile, CRM notes, signed data) |
| GET | `/api/source-documents` | Source documents (attorney memos, signed profiles, custodian exports, CRM notes, stale marketing intakes) |
| GET | `/api/retirement-accounts` | Retirement account exports (custodian data) |
| GET | `/api/life-insurance` | Life insurance policy records |
| GET | `/api/trust-candidates` | Trust candidate data (GRAT, CRAT parameters) |
| GET | `/api/policies/tax` | Tax policy constants (estate tax rates, exclusion amounts, income tax brackets, gift tax annual exclusion) |
| GET | `/api/rmd-factors` | Required minimum distribution (RMD) life-expectancy factors by age |
| GET | `/portal/client/{client_id}` | Client portal view (may aggregate data from multiple sources) |

### General Workflow

1. **Read the task inputs.** From the task directory, read:
   - `input/prompt.txt` — the system prompt describing the advisory role and high-level task.
   - `input/payloads/request_memo.md` — the advisor request memo with client ID, engagement description, and planning horizon.
   - `input/payloads/answer_template.json` — the required output schema (object type, required keys, field types and enums).

2. **Gather data from the API.** Using `curl` or an equivalent HTTP client, call every relevant endpoint. Favor targeted calls (e.g., `GET /api/clients/{client_id}`) over listing all records. Always fetch:
   - The client record
   - Source documents applicable to that client
   - Retirement accounts (if the task involves Roth conversions or RMDs)
   - Life insurance records (if the task involves ILITs or estate liquidity)
   - Trust candidates (if the task involves GRAT/CRAT comparison)
   - Tax policy constants
   - RMD factors (if the task involves RMD projections)

3. **Resolve source conflicts.** Client records from different advisory systems (custodian exports, CRM imports, signed profiles, attorney memos, stale marketing intakes) may disagree on key fields. Apply these priority rules:
   - For **profile/personal** data (DOB, marital status, beneficiaries): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
   - For **account/financial** data (balances, account types, FMV): `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`.
   - For **policy/insurance** data (death benefit, premium, policy date): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE`.
   - For **goal/planning** data (estate objectives, charitable intent): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
   - For **asset** data (portfolio composition, asset values): `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CRM_NOTE`.
   - When timestamps are available, prefer the most recent record within the same priority tier.
   - Record the controlling source for each domain in the `source_resolution` output block.

4. **Compute the required figures.** Use tax policy constants from `/api/policies/tax` and RMD factors from `/api/rmd-factors` for all calculations. Always round USD amounts to cents (two decimal places). Use integer years and ISO 8601 dates (`YYYY-MM-DD`).

5. **Produce the JSON output.** Format a single JSON object matching the answer template exactly. Use the field enums, types, and key names as specified. Do not include commentary, prose, or markdown fencing outside the JSON object.

### Analysis Types

#### roth_conversion_rmd

Computes a staged Roth conversion plan and compares baseline vs. post-conversion RMD tax liability through a planning horizon.

Key computations:
- **Conversion plan**: Determine first conversion year (typically the planning year), number of conversion years, annual conversion amount, total converted, and total conversion tax (annual amount × number of years × marginal income tax rate from tax policy).
- **RMD projection**: Compute first RMD year from client age and RMD starting age (from tax policy). Use RMD factors from `/api/rmd-factors` to project annual RMD amounts with and without conversion, then compute taxes (RMD amount × marginal rate) and sum through the horizon year.
- **Legacy projection**: Project Roth and traditional IRA balances to the horizon year, accounting for conversions and RMDs. Assign an heir tax profile enum based on the proportion of Roth vs. traditional assets.
- **Recommendation**: Choose `STAGED_ROTH_CONVERSION`, `DEFER`, or `NO_CONVERSION` based on tax savings and feasibility. Set suitability and risk flag accordingly.

#### ilit_crummey_implementation

Evaluates an Irrevocable Life Insurance Trust (ILIT) with Crummey withdrawal notice requirements for the first premium cycle.

Key computations:
- **Gift plan**: Determine annual exclusion per beneficiary from tax policy. Multiply by beneficiary count to get annual exclusion capacity. Compare with annual premium to compute the premium gap.
- **Administration timeline**: Set contribution date, notice due date (typically 7 days after contribution), withdrawal window end (30 days after notice), and earliest premium payment date (day after withdrawal window closes). Determine whether a dedicated bank account is required.
- **Estate result**: Death benefit from the policy. Estate inclusion risk: if formalities (Crummey notices, separate account, proper timing) are met and premium is within exclusion capacity, risk is `LOW_IF_FORMALITIES_MET`. If premium exceeds exclusion capacity, flag `EXCLUSION_SHORTFALL`. If policy was transferred within 3 years, flag `THREE_YEAR_LOOKBACK`. Combine flags when both apply.
- **Recommendation**: Choose primary action based on whether full premium fits within Crummey capacity, whether lifetime exemption covers the gap, or whether a lookback period requires disclosure.

#### trust_comparison

Compares GRAT (Grantor Retained Annuity Trust) and CRAT (Charitable Remainder Annuity Trust) strategies and recommends one.

Key computations:
- **Estate context**: Taxable estate, estate tax exposure (taxable estate × estate tax rate), liquid assets available, and liquidity gap (exposure minus liquid assets).
- **GRAT valuation**: Use trust candidate data for GRAT assumptions (funding amount, annuity rate, term years, IRS §7520 rate). Project remainder to heirs and estate tax reduction.
- **CRAT valuation**: Use trust candidate data for CRAT assumptions (funding amount, annuity rate, term years, §7520 rate). Project charitable remainder and income tax deduction. Assess family transfer fit.
- **Recommendation**: Choose based on whether the client's primary goal is family transfer (`CHILDREN_TRANSFER_PRIORITY` → GRAT) or philanthropy (`PHILANTHROPIC_PRIORITY` → CRAT). Designate the alternate strategy's role.

#### estate_liquidity_action_plan

Combines ILIT and trust transfer analysis into a coordinated action plan for estate liquidity.

Key computations:
- **Estate context**: Same as trust_comparison — taxable estate, estate tax exposure, liquidity gap.
- **ILIT analysis**: Same gift plan and estate inclusion risk logic as ilit_crummey_implementation.
- **Trust transfer**: Same GRAT/CRAT comparison as trust_comparison, but presented as a trust transfer recommendation alongside the ILIT.
- **Recommendation**: Choose a combined primary action. Determine sequencing based on dependencies (ILIT typically first, then trust transfer). Set risk flag.
- **Action set**: A sorted list of concrete action items, chosen from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`. Always sort alphabetically.

### Source Resolution

Every output must include a `source_resolution` block naming the controlling source for each data domain. The enum values are:

- `SIGNED_PROFILE` — most authoritative for personal, beneficiary, and goal data.
- `ATTORNEY_MEMO` — most authoritative for asset valuation data; second-tier for profile and goals.
- `CUSTODIAN_EXPORT` — most authoritative for account balances and holdings.
- `CRM_NOTE` — medium-priority source; may have stale or incomplete data.
- `STALE_MARKETING_INTAKE` — least authoritative; only used when no other source exists.

### Output Formatting Rules

- **At top level**: a single JSON object — no wrapping array, no markdown code fences, no prose before or after.
- **Numbers**: JSON numbers (not strings), rounded to two decimal places for USD values.
- **Dates**: ISO 8601 strings (`YYYY-MM-DD`).
- **Years**: JSON integers.
- **Booleans**: JSON `true` or `false`.
- **Enums**: exactly as specified in the answer template, with no variations in case or spelling.
- **Key order**: irrelevant except where the template explicitly requires alphabetical sorting (e.g., `action_set`).
- **Missing/optional fields**: omit keys that are not applicable rather than setting them to `null`. Only include keys listed in the template's `fields` block.
- **Task identifier**: set `task_id` to the directory name of the task (e.g., `train_001`, `test_001`). Set `client_id` to the stable client identifier from the request memo.

### Error Handling

- If the API base URL cannot be reached, check that the environment is running and `GDPEVO_ENV_BASE_URL` is set.
- If a client record returns 404, verify the client ID from the request memo.
- If multiple data sources are irreconcilable, prefer the source with the highest priority tier and note it in `source_resolution`.
- If a required computation input (e.g., tax rate, RMD factor) is missing from the API, flag the issue rather than guessing.

### Computational Conventions

- **Estate tax**: `estate_tax_exposure = taxable_estate × estate_tax_rate` (rate from `/api/policies/tax`).
- **Liquidity gap**: `liquidity_gap_before_planning = max(0, estate_tax_exposure − liquid_assets_available)`.
- **RMD**: `rmd_amount = prior_year_end_balance / distribution_period_factor`. Factor from `/api/rmd-factors` by attained age in the distribution year.
- **RMD tax**: `rmd_tax = rmd_amount × marginal_income_tax_rate` (rate from `/api/policies/tax`).
- **Conversion tax**: `conversion_tax = converted_amount × marginal_income_tax_rate`.
- **Gift exclusion capacity**: `annual_exclusion_per_beneficiary × beneficiary_count` (exclusion amount from `/api/policies/tax`).
- **Present value / remainder projections**: Use standard financial formulas with the §7520 rate from tax policy. GRAT remainder = `funding_amount × (1 + growth_rate)^term_years − annuity_payments_sum`. CRAT charitable remainder = `funding_amount × (1 + §7520_rate)^(−term_years) × charitable_remainder_factor`.
- Use USD throughout. Always round to two decimal places with standard rounding.
