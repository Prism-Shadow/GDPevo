# Aster Legal Deal Desk — SKILL

## Environment

The only remote environment entrypoint is `GDPEVO_ENV_BASE_URL` (see `environment_access.md`).
All deal data lives behind the Deal Desk Web/API. Do not read local `env/` source files or use localhost.

## API Usage

### Fetch a deal (all data in one response)

```
GET {GDPEVO_ENV_BASE_URL}/api/deals/{deal_id}
```

Returns a single JSON object with these top-level keys:

| Key | Contents |
|-----|----------|
| `deal` | Deal profile, parties, economics, draft terms, schedules, negotiation context, record links |
| `clauses` | Clause records with draft/playbook/policy values, calculation base, source doc, version status |
| `documents` | Full-text or structured sections for term sheets, draft agreements, client emails, cap tables, financials, material contracts, disclosure schedules, template provisions |
| `policy` | Policy rules with approval categories, escalation triggers, thresholds, fallback positions |
| `benchmarks` | Market benchmarks with sample sizes, percentiles, and topic/industry metadata |

### List all deals

```
GET {GDPEVO_ENV_BASE_URL}/api/deals
```

Returns deal summaries (count, deal_id, structure, parties, economics, dates, status, policy_id).

## Data Precedence Rules

**CRITICAL — follow this order strictly:**

1. **Active deal documents** (version_status `"ACTIVE"`) — the source of truth.
2. **Latest written client instructions** (the client email, typically `DOC-{DEAL}-EMAIL-03`) — override generic policy where they conflict.
3. **Active policy/playbook rules** — apply where not superseded by client instructions.
4. **Active cap table** (`DOC-{DEAL}-CAP-ACTIVE`) — supersedes any stale cap table export.

**Never use:**
- Documents with `version_status: "STALE"` — these are audit-only artifacts.
- Documents with `version_status: "TEMPLATE"` — generic form language that may conflict with deal-specific terms.
- Benchmarks from different industries or older years flagged as distractors ("Older sample retained as distractor").

## Version Status Convention

| Status | Meaning | Use? |
|--------|---------|------|
| `ACTIVE` | Current and authoritative | **Yes — primary source** |
| `STALE` | Superseded, audit trail only | No |
| `TEMPLATE` | Generic drafting system import | No |

When a stale clause shares a `topic` with an active clause, always use the active one. Stale clauses and templates exist as distractors.

## Numeric Conventions

- **Currency amounts**: integer US dollars, no commas, no currency symbols.
  - Example: `184000000` not `$184,000,000`.
- **Percentages**: decimal number rounded to two decimal places, expressed as percentage points.
  - Example: `10.00` for 10%, `0.75` for 0.75%, `2.50` for 2.5%.
- **Months**: integer number of months.
- **Null for N/A**: use `null` for numeric fields that do not apply.
- **Empty lists**: use `[]` for empty list fields, never `null`.

### Key Calculations

- **Per-share price**: `null` when the active cap table provides no share count. Basis: `"NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE"`.
- **Price per percent point**: `equity_value / 100`, integer dollars.
- **NWC collar as percent of EV**: `(collar / equity_value) * 100`, rounded to 2 decimal places.
- **Escrow/cap amounts**: `headline_value * percent / 100`, integer dollars.
- **Consideration allocation**: each seller's proceeds = `ownership_percent * consideration_component`, integer dollars.
- **RTF deviation**: `draft_percent - policy_threshold_percent`, rounded to 2 decimal places.

## Enum Conventions

- Use **exactly** the enum values from the answer template — no aliases, no abbreviations, no synonyms.
- Match case exactly: enum values are `UPPER_SNAKE_CASE`.
- For structures: `STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`, `CARVE_OUT`, `ROLLOVER_STOCK_PURCHASE`.
- For client side: `BUYER`, `SELLER`.
- For basket types: `DEDUCTIBLE`, `TIPPING`, `NONE`.
- For NWC mechanics: `DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`, `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR`, `NO_POST_CLOSING_ADJUSTMENT`, `TRUE_UP_AGAINST_ACTIVE_BALANCE_SHEET`, `SELLER_BUDGET_BASELINE`, `NONE`.
- For consent conditions: `CLOSING`, `COVENANT`, `NOTICE`, `POST_CLOSING_NOTICE`.
- For regulatory: `SIZE_OF_PERSON_TEST_NOT_MET`, `REPORTABLE_THRESHOLDS_MET`, `COUNSEL_MEMO_MISSING`, `NOT_APPLICABLE`, `THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS`, `SIZE_OF_PERSON_NOT_MET`, `UNKNOWN`.
- For policy status: `WITHIN_POLICY`, `APPROVAL_REQUIRED`, `OVERRIDE_APPLIED`, `ESCALATE_IF_CHANGED`, `ESCALATE`, `NOT_APPLICABLE`.

## Sorting Rules (strict — enforced by the judge)

- **Seller allocations**: sort by `seller_name` ascending (alphabetical).
- **Seller IDs**: sort by `seller_id` ascending (alphabetical). Create stable uppercase snake-case IDs from seller names.
- **Material consents / contracts**: sort by `contract_name` ascending (alphabetical).
- **Employment employees**: sort by displayed name ascending (alphabetical). Use exact names as shown in deal data (include titles, e.g. `"Mina Calder, founder/CTO"`).
- **Issues**: sort by `issue_id` ascending (alphabetical).
- **Policy checks**: sort by `check_id` ascending (alphabetical).
- **Source doc IDs**: sort alphabetically within lists.
- **Override codes**: sort alphabetically.
- **TSA services**: sort alphabetically.
- **MAE omitted carveouts**: sort alphabetically by carveout code.
- **Approval bodies**: sort alphabetically.
- **Conditional escalation triggers**: sort alphabetically.
- **Committee members**: sort alphabetically by name as displayed.
- **Primary driver term IDs**: sort alphabetically.
- **Other approvals**: sort alphabetically.
- **Required material consents**: sort by `contract_name` ascending.

## Field Population Rules

### Exact Names
Always use the **exact name** from the source data — never paraphrase, truncate, or alter. This applies to:
- Party names (buyer, seller, target, seller group)
- Employee names (keep titles if present in source)
- Contract names
- Document IDs
- Clause IDs
- Policy rule IDs
- Committee member names

### Material Consents
Only include contracts where `consent_required: true` in the `required_material_consents` list. Contracts where `consent_required: false` should go to `post_closing_notice_items` if their condition type is notice/covenant-based.

### Per-Share Price
When the cap table provides seller records with `ownership_percent` but no share count, set `per_share_price_usd` to `null` and `per_share_price_basis` to `"NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE"`.

### Policy Thresholds
When comparing draft values to policy thresholds in escalation analyses, use the **escalation threshold** (not the preferred range) as `policy_threshold_percent`. The deviation is `draft_percent - policy_threshold_percent`.

### Exposure Amounts
- Quantified exposures: use `EQUITY_VALUE` or `FULL_EQUITY_VALUE_UNCAPPED` as basis.
- Non-quantified legal risks: use `NON_QUANTIFIED_LEGAL_RISK`.
- For escrow/R&W survival exposure in public mergers, use `FULL_EQUITY_VALUE_UNCAPPED`.
- For RTF, exposure is the draft amount (full RTF obligation).

### TSA Service Codes
Use the deal-specific needed services from the disclosure schedule, not the policy's general list. Map to the allowed enum values: `ERP`, `FINANCE`, `IT`, `PAYROLL`, `PROCUREMENT`, `QUALITY_RECORDS`, `REGULATORY`.

### Benchmark References
When a deal's strategic context mentions a benchmark memo, include the deal-relevant benchmark ID, sample size, and count above threshold in quantification fields. Match benchmarks by **topic and industry** to the deal. Skip benchmarks flagged as "Older sample retained as distractor" or from different industries unless they are the only available source.

## Issue Identification (for review tasks)

When comparing a counterparty draft against the client playbook:
1. Identify every clause where the draft value deviates from the playbook preferred position.
2. Check whether the deviation triggers a policy escalation rule.
3. Determine severity based on the policy's escalation trigger language and the magnitude of deviation.
4. Choose the recommended action based on what the client instructions direct.
5. Only populate `corrected_value` with the fields relevant to that specific issue — do not carry over unrelated fields.
6. Include supporting document, clause, and policy rule IDs in `source_ids`.

## Drafting Positions (for first-draft tasks)

Derive position enums from the current deal state:
- `form_position`: Which party's form is used (`BUYER_FORM`, `SELLER_FORM`, etc.).
- `consideration_schedule_position`: Whether using the active cap table, allocation schedule, stale data, or counterparty draft.
- `escrow_cap_position`: Relationship between cap and escrow (`CAP_EQUALS_GENERAL_ESCROW`, etc.).
- `basket_position`: Type of basket in the draft (`DEDUCTIBLE_BASKET`, `TIPPING_BASKET`, `NO_BASKET`).
- `consent_position`: How material consents are treated.
- `hsr_position`: How HSR is handled in the draft.
- `earnout_position`: Earnout structure.
- `non_compete_position`: Non-compete scope.
- `transition_services_position`: TSA posture.
- `ip_transition_position`: IP transition approach.

## Common Pitfalls

1. **Using stale or template data**: Always check `version_status`. Template provisions and stale cap tables are traps.
2. **Wrong industry benchmarks**: Using a FinTech benchmark for a Cybersecurity deal, or a 2019 benchmark flagged as a distractor.
3. **Truncating names**: Employee names in source data include titles — keep them exactly as shown.
4. **Using preferred range instead of escalation threshold**: In escalation analyses, `policy_threshold_percent` is the threshold that triggers escalation, not the top of the preferred range.
5. **Including non-consent contracts in required_material_consents**: Only include items where `consent_required: true`.
6. **Sort errors**: All lists have a specific sort order. Alphabetical sort is the default.
7. **Including non-issues in issue registers**: The instructions say "omit non-issues." Do not include issue entries with `NO_ISSUE` recommended action.
8. **Wrong exposure basis**: Choose the right enum for each exposure type — don't use `EQUITY_VALUE` for non-quantified risks.
9. **Spreading corrected values across wrong issue IDs**: Each corrected value field belongs to a specific issue. Don't put `buyer_assumed_liability_covenant` in both `ASSUMED_LIABILITIES_AND_NWC` and `SURVIVAL_CAP_BASKET`.
10. **Policy thresholds as percentages vs preferred ranges**: The policy threshold is the escalation point (e.g., "above 5.5%"), not the preferred band (e.g., "at or below 5.0%").
