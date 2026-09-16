---
name: advisory-planner
description: Build structured wealth advisory planning outputs for the private wealth advisory task environment. Use this skill whenever the user is supporting a private wealth advisory team, needs to prepare planning deliverables for a client engagement, or encounters the advisory API (task-env:9008). This covers Roth conversion RMD analysis, ILIT Crummey implementation, GRAT vs CRAT trust comparison, and estate liquidity action plans. Use it even when the user describes the work as "draft a tax summary," "prepare a client deliverable," "run the advisory numbers," or "put together the planning output."
---

# Advisory Planner

Generate structured JSON planning outputs for private wealth advisory engagements using the advisory task-environment API. The API serves client records, source documents, retirement accounts, life insurance policies, trust candidates, tax policy constants, and RMD divisor factors.

## When to use

This skill applies when the task involves:

- A private wealth advisory team asking for structured planning output
- A request-memo file naming a client ID and engagement type
- An answer template JSON defining the required output shape
- The advisory API at `http://task-env:9008`
- Client records that may conflict across multiple source systems

The API base URL is supplied by the task harness, usually exposed as `API_BASE` after the environment starts. If not set, default to `http://task-env:9008`.

## How this skill works

This skill gives you the knowledge to navigate the advisory API, resolve conflicting source documents, compute planning values, and produce valid JSON matching the answer template. It does **not** contain pre-computed values -- you must query the live API for every client engagement.

The references in [references/](references/) provide full API documentation and computation guides. Read them as needed during execution.

---

## Step 1: Understand the engagement

Read these files from the task input:

1. **`input/payloads/request_memo.md`** -- contains the client ID, engagement type, planning horizon year (if applicable), and output formatting rules
2. **`input/payloads/answer_template.json`** -- defines required top-level keys, field enums, and numeric formatting rules

The engagement type is identified by the `analysis_type` enum in the answer template:

- `roth_conversion_rmd` -- Roth conversion and RMD tax projection
- `ilit_crummey_implementation` -- ILIT Crummey funding cycle check
- `trust_comparison` -- GRAT versus CRAT numerical comparison
- `estate_liquidity_action_plan` -- combined estate liquidity and trust action plan

The `task_id` field in the output should match the task directory name (e.g., `train_001`, `test_001`).

---

## Step 2: Query the advisory API

Read the full API documentation at [references/api-reference.md](references/api-reference.md) for endpoint details. The core endpoints are:

| Endpoint | What it returns |
|---|---|
| `GET /api/clients` | All client summary records |
| `GET /api/clients/{client_id}` | Single client record |
| `GET /api/source-documents` | All source documents across clients |
| `GET /api/retirement-accounts` | All retirement accounts |
| `GET /api/life-insurance` | All life insurance policies |
| `GET /api/trust-candidates` | All trust candidate cases |
| `GET /api/policies/tax` | Tax policy constants (exemptions, brackets, rates) |
| `GET /api/rmd-factors` | RMD divisor factors by age |
| `GET /portal/client/{client_id}` | Client portal HTML (for context, not structured data) |

**Important:** The collection endpoints (`/api/clients`, `/api/source-documents`, `/api/retirement-accounts`, `/api/life-insurance`, `/api/trust-candidates`) return **all** records. You must filter by `client_id` to find records for the target client. However, you can also use the path parameter on singular endpoints: `/api/clients/{client_id}`.

For source documents, the API also supports query parameters: `GET /api/source-documents?client_id=CLT-1001`.

Query all relevant endpoints in parallel using separate HTTP requests. You need at minimum:

- Client record
- Source documents for the client
- Tax policies and RMD factors (shared across all clients)
- The engagement-specific resource: retirement accounts, life insurance, and/or trust candidates

---

## Step 3: Resolve conflicting sources

Multiple source documents may exist for one client because data was imported from different advisory systems at different times. The source types, ordered by authority:

1. **`SIGNED_PROFILE`** -- most recent and authoritative; the client's formally signed planning profile
2. **`ATTORNEY_MEMO`** -- attorney planning call notes; carries legal weight for trust and estate matters
3. **`CUSTODIAN_EXPORT`** -- trade-date-accurate account balances; the only source for retirement account data
4. **`CRM_NOTE`** -- older CRM import; superseded by newer sources
5. **`STALE_MARKETING_INTAKE`** -- oldest, least reliable; never controlling in the training examples

**Resolution rules:**

- **Profile data** (age, filing status, income, beneficiaries, marginal rate, liquid assets, estate value, philanthropic intent, family transfer priority): Use the most recent authoritative source. Typically `SIGNED_PROFILE` when available, otherwise fall back to `ATTORNEY_MEMO`, then `CRM_NOTE`. When sources agree on a fact, note that they agree. When they disagree, prefer the more recent and more authoritative source.
- **Account data** (traditional balance, Roth balance, expected return, RMD start age, recommended conversion years): `CUSTODIAN_EXPORT` is the only source. Use it directly.
- **Policy data** (death benefit, annual premium, contribution date, transfer status): The life-insurance API provides factual policy records. Use the API data directly. The `controlling_policy_source` resolution refers to which source document governs the policy *interpretation* (typically `SIGNED_PROFILE`).
- **Beneficiary data**: Use the signed profile's `beneficiary_count` when available. Older CRM imports may have stale beneficiary counts.
- **Asset/trust data**: The trust-candidates API provides trust-specific facts (asset value, growth rate, term years, annuity/payout rates). For the `controlling_asset_source` in a trust comparison, prefer `ATTORNEY_MEMO` when it is the more specific planning document for trust assets, even if a `SIGNED_PROFILE` also carries the same estate value.

**General principle:** When multiple sources provide the same fact and agree, record the most authoritative one as controlling. When they disagree, the more recent and more authoritative source wins. For account-level data, `CUSTODIAN_EXPORT` is always authoritative.

---

## Step 4: Compute the values

Read the computation guide at [references/computations.md](references/computations.md) for analysis-type-specific formulas.

**Common formatting rules:**

- All USD amounts rounded to cents (two decimal places)
- All dates in ISO `YYYY-MM-DD` format
- All numbers are JSON numbers, not strings
- The `action_set` field (estate_liquidity_action_plan only) must be sorted alphabetically

**Enum values:** Use only the enum values listed in the answer template's `fields` section. Do not invent new values.

---

## Step 5: Return the output

Return a single JSON object that conforms exactly to the `required_top_level_keys` in the answer template. No prose outside the JSON. No markdown fences, no explanation.

**Key rules:**

- Every key listed under `required_top_level_keys` must be present
- Every nested key shown in the `fields` section must be present (unless the answer template explicitly marks it as optional, which none of the training templates do)
- Enum fields must use exactly the string values defined in the template
- Numeric fields must be numbers, not strings
- USD values must be rounded to cents

---

## Reference files

- [references/api-reference.md](references/api-reference.md) -- Full API documentation for every endpoint
- [references/computations.md](references/computations.md) -- Computation formulas and workflows by analysis type

Read these references when specific endpoint details or computation formulas are needed during execution.
