## When to use this skill

Use this skill when the task involves acting as a private-wealth advisory agent that produces structured JSON planning outputs. The skill applies whenever there is a `prompt.txt`, a `request_memo.md`, and an `answer_template.json` in the task input directory, and a task-group advisory API providing client, account, policy, and tax data.

## Role and stance

You are supporting a private wealth advisory team. Every response must be a single JSON object conforming to the supplied answer template. Never emit prose, explanations, or markdown outside the JSON payload. Treat the answer template as the authoritative schema; all keys listed under `required_top_level_keys` must be present, and every field must match its declared type, enum domain, and format.

## Input discovery

Three files define every engagement:

- `prompt.txt` – the role prompt containing the client ID, engagement name, and the instruction to use the advisory API.
- `payloads/request_memo.md` – the advisor's memo with client context, any planning-horizon year, and formatting requirements.
- `payloads/answer_template.json` – the JSON schema. The `type` is always `"object"`; `required_top_level_keys` names every top-level key; `fields` lists dotted paths with type/enum/format constraints; `ordering` documents any sort-order requirements (e.g. `action_set` sorted alphabetically).

Read all three before querying the API so you know which template sections you must fill.

## API access

The advisory API base URL is supplied by the harness as `API_BASE` (or `GDPEVO_ENV_BASE_URL`). All endpoints are read-only `GET` calls. Use `curl` or an HTTP client to retrieve data.

| Endpoint | Returns |
|---|---|
| `GET /` | API health / root |
| `GET /api/clients` | Array of all client summary records |
| `GET /api/clients/{client_id}` | Full client record for one client |
| `GET /api/source-documents` | Source documents linked to clients (signed profiles, attorney memos, CRM notes, etc.) |
| `GET /api/retirement-accounts` | Custodian account exports (balances, account types, owner ages) |
| `GET /api/life-insurance` | Life-insurance policy records (death benefit, premium, ownership, lookback) |
| `GET /api/trust-candidates` | Trust-structure options (GRAT, CRAT, etc.) with funding parameters |
| `GET /api/policies/tax` | Tax-policy constants (brackets, exclusion amounts, rates, thresholds) |
| `GET /api/rmd-factors` | IRS RMD divisor tables by age |
| `GET /portal/client/{client_id}` | Client portal overview |

Always start with the client-specific endpoint (`/api/clients/{client_id}`) to anchor the engagement, then pull supporting data from the domain endpoints relevant to the analysis type.

## Source-conflict resolution

Client records imported from different advisory systems may disagree. When they do, resolve according to the source-authority hierarchy below. The `source_resolution` section of the output template records which source was treated as controlling for each domain.

### General source hierarchy (most to least authoritative)

1. `SIGNED_PROFILE` – client-signed planning profile
2. `ATTORNEY_MEMO` – attorney-prepared memorandum
3. `CUSTODIAN_EXPORT` – latest custodian/account export
4. `CRM_NOTE` – advisor-entered CRM note
5. `STALE_MARKETING_INTAKE` – outdated marketing intake form

### Domain-specific overrides

- **Account values and positions** (`controlling_account_source`): `CUSTODIAN_EXPORT` > `SIGNED_PROFILE` > `CRM_NOTE`. Custodian data is authoritative for dollar balances.
- **Client goals and intentions** (`controlling_goal_source`): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
- **Asset titling and ownership** (`controlling_asset_source`): `ATTORNEY_MEMO` > `SIGNED_PROFILE` > `CRM_NOTE`.
- **Beneficiary designations** (`controlling_beneficiary_source`): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.
- **Insurance policy details** (`controlling_policy_source`): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE`.
- **Client profile data** (`controlling_profile_source`): `SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.

When a higher-authority source disagrees with a lower one, use the higher-authority value and record it in the corresponding `source_resolution` field. When two sources of equal authority disagree, prefer the one with the more recent date.

## Analysis types

The `analysis_type` field in the output template determines which business logic to apply. The memos reveal four engagement patterns; match the engagement description to one of them.

### roth_conversion_rmd

**Trigger**: memo mentions Roth conversion, RMD, staged conversions, or a planning-horizon year.

**Required data**: client record, retirement accounts, RMD factor table, tax policies.

**Key computations**:

- `first_rmd_year`: the calendar year the client reaches the RMD beginning age. Use the RMD beginning age from `/api/policies/tax` (commonly 73).
- `conversion_plan`: determine how many years remain before RMDs begin (`first_rmd_year - current_year`). Spread conversions across those years using an annual amount that stays within the current marginal bracket. Set `first_conversion_year` to the current or next calendar year.
- `rmd_projection`: compute baseline RMDs (no conversion) and post-conversion RMDs through `horizon_year` using the RMD divisor for each age. Apply the client's marginal tax rate to RMD amounts. `rmd_tax_savings_through_horizon = baseline_rmd_tax - conversion_rmd_tax`.
- `legacy_projection`: project Roth and traditional balances to `horizon_year` using the after-conversion balances and a reasonable growth rate. Classify `heir_tax_profile` based on the Roth/traditional ratio at horizon.

**Recommendation logic**:

- `STAGED_ROTH_CONVERSION` when the client has enough pre-RMD years and tax bracket headroom.
- `DEFER` when the client is near RMD age with limited conversion window but some benefit remains.
- `NO_CONVERSION` when the client is already in RMD territory or the tax cost exceeds projected savings.
- Suitability `SUITABLE` when tax savings are material and conversion tax is fundable; `BORDERLINE` when savings are small or liquidity is tight; `DEFER` when you recommended deferring.
- Risk flag: `TAX_BRACKET_MANAGEMENT` (bracket creep concern), `LIQUIDITY_CONSTRAINT` (conversion tax funding challenge), `RMD_NEAR_TERM` (limited runway).

### ilit_crummey_implementation

**Trigger**: memo mentions ILIT, Crummey, life-insurance trust, gift-tax exclusion, or premium funding cycle.

**Required data**: client record, life-insurance policies, tax policies.

**Key computations**:

- `planning_year`: the current calendar year or the year specified in the memo.
- `annual_exclusion_per_beneficiary`: the gift-tax annual exclusion amount from `/api/policies/tax`.
- `beneficiary_count`: number of ILIT beneficiaries from the client profile or policy record.
- `annual_exclusion_capacity = annual_exclusion_per_beneficiary × beneficiary_count`.
- `annual_premium`: the annual insurance premium from the life-insurance policy record.
- `premium_gap = annual_premium - annual_exclusion_capacity` (zero or negative means fully covered).
- `administration`: compute Crummey notice timeline. `contribution_date` is when funds transfer; `notice_due_date` is shortly after; `withdrawal_window_end` is typically 30 days from notice; `earliest_premium_payment_date` is after the withdrawal window closes.
- `dedicated_bank_account_required`: true (ILITs generally require a separate trust bank account).
- `estate_result.death_benefit`: from the policy record.
- `estate_inclusion_risk`: `LOW_IF_FORMALITIES_MET` when Crummey procedures are followed; `EXCLUSION_SHORTFALL` when premium exceeds exclusion capacity; `THREE_YEAR_LOOKBACK` when policy was recently transferred; `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both risks apply.
- `projected_outside_estate_if_implemented = death_benefit` (if formalities are met and lookback is clear).
- `tax_liquidity_support = death_benefit × effective_estate_tax_rate`.

**Recommendation logic**:

- `FUND_WITH_CRUMMEY_NOTICES` when premium ≤ exclusion capacity and no lookback concern.
- `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` when premium exceeds exclusion capacity.
- `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` when a three-year lookback period applies.
- `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when both shortfall and lookback apply.
- Suitability: `SUITABLE_WITH_ADMINISTRATION` when implementable with proper notices; `BORDERLINE` when gap or lookback create uncertainty; `NOT_SUITABLE` when risks are prohibitive.

### trust_comparison

**Trigger**: memo mentions GRAT versus CRAT, trust comparison, or choosing between grantor and charitable remainder trusts.

**Required data**: client record, trust candidates, tax policies.

**Key computations**:

- `estate_context`: use client asset totals and the applicable estate-tax rate from `/api/policies/tax` to compute `taxable_estate`, `estate_tax_exposure`, and `liquidity_gap_before_planning`.
- `grat`: `term_years` is the GRAT term from the trust candidate; project remainder using the applicable federal rate (AFR) and asset growth assumptions; estimate estate-tax reduction as remainder × estate tax rate; `mortality_inclusion_risk` is always `TERM_SURVIVAL_REQUIRED` (grantor must survive the term).
- `crat`: `term_years` from the trust candidate; project charitable remainder based on the CRAT payout rate and term; estimate income-tax deduction from the present value of the remainder; `family_transfer_fit` is `LOW` (primary benefit goes to charity), `MODERATE`, or `HIGH`.

**Recommendation logic**:

- Prefer `GRAT` when the memo indicates children/heirs are the priority (`CHILDREN_TRANSFER_PRIORITY`).
- Prefer `CRAT` when philanthropic goals dominate (`PHILANTHROPIC_PRIORITY`).
- The `alternate_role` describes what the non-preferred trust does: `SECONDARY_CHARITABLE_TOOL` (CRAT as secondary charitable vehicle when GRAT is primary) or `SECONDARY_FAMILY_TRANSFER_TOOL` (GRAT as secondary transfer vehicle when CRAT is primary).

### estate_liquidity_action_plan

**Trigger**: memo mentions estate liquidity, estate tax, ILIT combined with trust strategies, or attorney coordination.

**Required data**: client record, life-insurance policies, trust candidates, tax policies.

**Key computations**:

- `estate_context`: compute `taxable_estate`, `estate_tax_exposure`, and `liquidity_gap_before_planning` using asset totals and the estate-tax rate from tax policies.
- `ilit` section: same ILIT logic as the `ilit_crummey_implementation` type (exclusion capacity, premium gap, inclusion risk, projected outside estate).
- `trust_transfer` section: same trust logic as `trust_comparison` (preferred strategy, remainder to heirs, estate tax reduction, charitable remainder).
- `action_set`: derive from the combined analysis. Possible actions: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`. Always include actions that address the identified gaps; sort alphabetically.

**Recommendation logic**:

- `COMBINE_ILIT_AND_GRAT` when estate liquidity needs and heir transfer goals both apply.
- `CRAT_WITH_LIQUIDITY_REVIEW` when charitable intent and liquidity planning intersect.
- `ILIT_WITH_EXEMPTION_REVIEW` when life-insurance funding is the primary need.
- Sequencing: `ILIT_FIRST_THEN_GRAT` (fund ILIT, then transfer appreciating assets); `TRUST_DECISION_FIRST` (decide trust structure before funding); `ILIT_FIRST_THEN_ATTORNEY_REVIEW` (fund ILIT, then have attorney review the combined plan).

## Output formatting

Every response must follow these rules exactly:

- **JSON only**: the entire response is a single JSON object. No markdown fences, no prose preamble, no trailing text.
- **Numbers are JSON numbers**: `42`, `150000.00`, not `"42"` or `"150000.00"`.
- **USD amounts**: always round to cents (two decimal places). Do not include dollar signs or commas.
- **Dates**: ISO 8601 `YYYY-MM-DD` format.
- **Years**: plain integers (e.g., `2026`).
- **Booleans**: JSON `true` or `false`, not strings.
- **Enums**: use the exact uppercase strings from the template's enum lists.
- **Lists**: use JSON arrays. When `ordering` requires alphabetical sort, sort with standard lexicographic order.
- **Required keys**: every key listed in `required_top_level_keys` must be present, even if its value is `null` (only use `null` when the template explicitly allows it; otherwise provide a valid value).
- **Extra keys**: do not add keys beyond those defined in the template.
- **task_id**: use the stable task identifier from the prompt or memo context (e.g., the train/test directory name).

## Workflow summary

1. Read `prompt.txt` to identify the client ID and high-level engagement.
2. Read `payloads/request_memo.md` for the advisor's specific context, planning horizon, and formatting notes.
3. Read `payloads/answer_template.json` to understand the required output schema.
4. Set the API base URL from the harness environment variable (`API_BASE` or `GDPEVO_ENV_BASE_URL`).
5. Query `GET /api/clients/{client_id}` to anchor on the client record.
6. Query domain-specific endpoints based on the analysis type inferred from the memo.
7. Resolve any conflicts between data sources using the documented hierarchy and record controlling sources in `source_resolution`.
8. Compute all numeric fields using the formulas and decision rules for the analysis type.
9. Assemble the JSON object, validate all enum values and formats, and emit only that JSON.
