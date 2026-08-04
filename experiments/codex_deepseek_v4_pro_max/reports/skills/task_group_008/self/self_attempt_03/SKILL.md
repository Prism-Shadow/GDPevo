This skill equips you to complete structured wealth-advisory planning tasks for private-client engagements. You will connect to an advisory REST API, resolve conflicting client records, compute planning values, and return a single JSON object conforming to an answer template.

## Core Identity

You are supporting a private wealth advisory team. Your output is always machine-readable structured planning JSON returned to the advisor's planning system.

## Environment Setup

The advisory API base URL is supplied by the harness—typically the `API_BASE` environment variable. All API responses are JSON.

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health/root check |
| GET | `/api/clients` | List all clients |
| GET | `/api/clients/{client_id}` | Single client record |
| GET | `/api/source-documents` | Source documents (profiles, memos, CRM notes, etc.) |
| GET | `/api/retirement-accounts` | Retirement account exports |
| GET | `/api/life-insurance` | Life insurance policies |
| GET | `/api/trust-candidates` | Trust structures and candidates |
| GET | `/api/policies/tax` | Tax policy constants (brackets, exemptions, rates) |
| GET | `/api/rmd-factors` | RMD life-expectancy factors by age |
| GET | `/portal/client/{client_id}` | Human-readable client portal summary |

## Input Materials

Every task includes, in its `input/` directory:

- `prompt.txt` — The system prompt with task overview.
- `payloads/request_memo.md` — The advisor's engagement memo with client ID, engagement name, planning horizon (if applicable), and specific instructions.
- `payloads/answer_template.json` — The JSON schema defining required keys, field types, enums, and ordering constraints.

## General Workflow

Follow this sequence for every task:

1. **Read the request memo** — Extract the client ID, engagement type, planning horizon year (if any), and any special instructions.
2. **Read the answer template** — Note all required top-level keys, field types, enum values, and ordering rules. This is the exact shape your output must match.
3. **Fetch client data** — Call `GET /api/clients/{client_id}` for the primary client record.
4. **Fetch supporting data** — Based on the analysis type, fetch the relevant endpoints:
   - For Roth conversion / RMD tasks: `/api/retirement-accounts`, `/api/policies/tax`, `/api/rmd-factors`, `/api/source-documents`.
   - For ILIT / insurance tasks: `/api/life-insurance`, `/api/source-documents`, `/api/policies/tax`.
   - For trust comparison tasks: `/api/trust-candidates`, `/api/source-documents`, `/api/policies/tax`.
   - For estate liquidity tasks: all of the above.
5. **Resolve conflicting sources** — See Source Resolution below.
6. **Compute planning values** — Derive every field in the answer template from resolved data, applying tax policy constants, RMD factors, growth assumptions, and gift/estate tax rules as appropriate.
7. **Assemble and return JSON** — Produce exactly one JSON object. No prose, no markdown fences, no commentary.

## Source Resolution

Client records may conflict because they were imported from different advisory systems at different times. When values disagree, prefer the more authoritative source according to the hierarchy below.

### Source Authority Tiers (highest to lowest)

1. **SIGNED_PROFILE** — A client-signed financial profile. Most authoritative for goals, beneficiaries, and personal preferences.
2. **ATTORNEY_MEMO** — Attorney-prepared memorandum. Authoritative for asset titling, trust structures, and legal goals.
3. **CUSTODIAN_EXPORT** — Direct custodian/account export. Authoritative for account balances, holdings, and transaction-level data.
4. **CRM_NOTE** — Internal CRM note. Lower authority; may be outdated or unverified.
5. **STALE_MARKETING_INTAKE** — Old marketing intake form. Least authoritative; use only when no other source exists.

### Domain-Specific Hierarchies

- **Profile / personal data** (name, DOB, goals, beneficiaries): `SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE`
- **Account balances / holdings**: `CUSTODIAN_EXPORT > SIGNED_PROFILE > CRM_NOTE`
- **Life insurance policies**: `SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE`
- **Trust structures / goals**: `SIGNED_PROFILE > ATTORNEY_MEMO > CUSTODIAN_EXPORT > CRM_NOTE > STALE_MARKETING_INTAKE`
- **Asset titling / property**: `ATTORNEY_MEMO > SIGNED_PROFILE > CRM_NOTE`

When a source resolution field is required in the output (e.g., `controlling_profile_source`, `controlling_account_source`), report the source tier you actually relied on for that domain.

## Analysis Types

### roth_conversion_rmd

Roth conversion analysis with RMD projections. Compute staged annual conversions, compare baseline vs. conversion RMD tax through the horizon year, and project legacy balances.

Key computations:
- Determine first eligible conversion year and count of conversion years.
- Derive annual and total conversion amounts based on tax-bracket headroom.
- Compute total conversion tax at applicable marginal rates.
- Project baseline RMDs starting at the applicable RMD age using RMD factors by age.
- Project post-conversion RMDs on the reduced traditional balance.
- Grow Roth and traditional balances to the horizon year using appropriate growth assumptions.
- Classify the heir tax profile based on the ratio of Roth to traditional assets at horizon.

### ilit_crummey_implementation

ILIT (Irrevocable Life Insurance Trust) setup with Crummey notice administration for the first premium cycle.

Key computations:
- Determine annual exclusion per beneficiary from tax policy.
- Compute total exclusion capacity = per-beneficiary exclusion × beneficiary count.
- Compute premium gap = annual premium − exclusion capacity (positive gap requires lifetime exemption use).
- Derive Crummey notice timeline: contribution date → notice due date → withdrawal window end → earliest premium payment date.
- Assess estate inclusion risk based on policy acquisition timing (three-year lookback rule).
- Project death benefit outside the estate if properly administered.

### trust_comparison

Side-by-side GRAT vs. CRAT comparison for a client choosing between family transfer and charitable priorities.

Key computations:
- Compute taxable estate and estate tax exposure from resolved asset data.
- Determine liquidity gap before planning.
- Model GRAT: term, projected remainder to heirs (using §7520 rate / hurdle rate), estate tax reduction.
- Model CRAT: term, projected charitable remainder, income tax deduction (present value of remainder interest).
- Recommend the strategy that better matches stated client goals (family transfer vs. philanthropy).

### estate_liquidity_action_plan

Combined estate planning action set: ILIT for liquidity, trust transfer for tax reduction, and attorney coordination.

Key computations:
- Compute taxable estate, estate tax exposure, and liquidity gap.
- Evaluate ILIT fit: exclusion capacity, premium gap, inclusion risk.
- Evaluate trust transfer: GRAT vs. CRAT fit based on asset composition and goals.
- Assemble `action_set` as an alphabetically sorted list of recommended actions from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`.

## Enum Reference

### recommendation.primary_action

| Value | Meaning |
|-------|---------|
| `STAGED_ROTH_CONVERSION` | Proceed with staged Roth conversions |
| `DEFER` | Delay conversion to a future year |
| `NO_CONVERSION` | Conversion not recommended |
| `FUND_WITH_CRUMMEY_NOTICES` | Fund ILIT using Crummey withdrawal notices |
| `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL` | Cover premium gap with lifetime exemption |
| `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK` | Replace policy or accept three-year lookback |
| `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` | Disclose lookback risk and use exemption for gap |
| `COMBINE_ILIT_AND_GRAT` | Implement ILIT and GRAT together |
| `CRAT_WITH_LIQUIDITY_REVIEW` | Use CRAT with liquidity review |
| `ILIT_WITH_EXEMPTION_REVIEW` | ILIT with exemption allocation review |

### recommendation.suitability

| Value | Meaning |
|-------|---------|
| `SUITABLE` | Strategy is suitable |
| `BORDERLINE` | Marginal suitability; monitor |
| `DEFER` | Defer decision |
| `SUITABLE_WITH_ADMINISTRATION` | Suitable if formalities are followed |
| `NOT_SUITABLE` | Not suitable |

### recommendation.risk_flag

| Value | Meaning |
|-------|---------|
| `TAX_BRACKET_MANAGEMENT` | Risk centers on tax bracket management |
| `LIQUIDITY_CONSTRAINT` | Liquidity for conversion taxes is a concern |
| `RMD_NEAR_TERM` | RMD age is imminent |
| `LOW_IF_FORMALITIES_MET` | Low risk if Crummey formalities are met |
| `EXCLUSION_SHORTFALL` | Annual exclusion insufficient for premium |
| `THREE_YEAR_LOOKBACK` | Policy acquired within three-year lookback window |
| `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` | Both lookback and shortfall risks present |

### legacy_projection.heir_tax_profile

| Value | Meaning |
|-------|---------|
| `MOSTLY_TAX_FREE` | Majority of legacy in Roth / tax-free vehicles |
| `MIXED_TAXABLE_AND_TAX_FREE` | Roughly balanced between taxable and tax-free |
| `MOSTLY_TAXABLE` | Majority in traditional / taxable vehicles |

### estate_result.estate_inclusion_risk

Same enum as `recommendation.risk_flag`.

### trust_comparison enums

- `recommendation.preferred_strategy`: `GRAT`, `CRAT`
- `recommendation.rationale_code`: `CHILDREN_TRANSFER_PRIORITY`, `PHILANTHROPIC_PRIORITY`
- `recommendation.alternate_role`: `SECONDARY_CHARITABLE_TOOL`, `SECONDARY_FAMILY_TRANSFER_TOOL`
- `grat.mortality_inclusion_risk`: `TERM_SURVIVAL_REQUIRED`
- `crat.family_transfer_fit`: `LOW`, `MODERATE`, `HIGH`

### estate_liquidity_action_plan enums

- `recommendation.sequencing`: `ILIT_FIRST_THEN_GRAT`, `TRUST_DECISION_FIRST`, `ILIT_FIRST_THEN_ATTORNEY_REVIEW`
- `action_set` values (alphabetically sorted): `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`, `GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`, `LIFETIME_EXEMPTION_ALLOCATION`

## Formatting Rules

- **USD amounts**: JSON numbers rounded to cents (two decimal places).
- **Dates**: ISO 8601 strings (`YYYY-MM-DD`).
- **Numbers**: Always JSON number type, never string-encoded.
- **Lists**: When `action_set` is required, sort the list alphabetically. No other ordering constraints unless the template specifies them.
- **Booleans**: JSON `true` or `false`, not strings.

## Output Rules

- Return **only** the JSON object. No markdown fences, no surrounding prose, no explanation.
- Every key listed in the answer template's `required_top_level_keys` must be present.
- Every field value must match the declared type and, for enums, exactly one of the allowed values.
- `task_id` must reflect the current task context (e.g., `train_001`, `test_003`).
- If you cannot determine a value with confidence from available API data, use a reasonable default consistent with the resolved data rather than omitting the key.

## Error Handling

- If an API endpoint is unreachable, retry once; if still failing, use the best available data from other sources and note the controlling source as the one you relied on.
- If a client is not found, return an error JSON: `{"error": "CLIENT_NOT_FOUND", "client_id": "..."}`.
- If the answer template is missing or unreadable, return `{"error": "TEMPLATE_MISSING"}`.
