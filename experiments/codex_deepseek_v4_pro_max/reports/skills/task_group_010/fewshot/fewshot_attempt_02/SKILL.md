## When to Use

Use this skill whenever the task involves the **Asteria Investment Office** shared environment. The environment provides institutional portfolio, index, bond, issuer, allocation, and market data through a set of HTTP REST endpoints. Tasks typically ask the agent to produce a structured JSON decision file by combining current environment records with a local request payload, always conforming to a supplied answer template.

## Environment Connection

The Asteria Investment Office environment runs as an HTTP service. All data is retrieved via `GET` requests; no authentication is required.

**Base URL:** `http://task-env:9010/`

**Available Endpoints:**

| Endpoint | Purpose |
|---|---|
| `GET /` | Health / root check |
| `GET /api/portfolios` | List all portfolios and their metadata |
| `GET /api/portfolios/{portfolio_id}/holdings` | Holdings for a specific portfolio (replace `{portfolio_id}` with the target) |
| `GET /api/instruments/bonds` | Bond instrument catalog (security master for fixed-income) |
| `GET /api/issuers` | Issuer reference data (ratings, sectors, watchlist status) |
| `GET /api/market/energy` | Energy-sector market data and pricing |
| `GET /api/indices` | Equity and market index catalog |
| `GET /api/index-levels` | Current and historical index levels for all indices |
| `GET /api/index-levels/{index_id}` | Index-level time series for a specific index |
| `GET /api/allocation/opportunity-sets` | Taxonomy of allocation opportunity sets (asset class, region, currency) |
| `GET /api/allocation/prior-views` | Prior-quarter active allocation views (UW / N / OW) |
| `GET /api/macro-signals` | Macro signal scores and rationale codes |

Note: the environment may also expose a `/api/policies` endpoint for policy thresholds (duration bands, HY caps, concentration rules).

## General Workflow

Every Asteria task follows a consistent four-phase pattern:

### Phase 1 — Inventory the Input

Read every file under the task's `input/` directory:
- `prompt.txt` — the task brief, naming the portfolio, objective, and required outputs.
- `payloads/answer_template.json` — the exact JSON shape to return (keys, types, enums, precision, ordering rules).
- Any additional payload files (desk requests, meeting memos, committee requests, review requests) — local intake context that may contain **stale or unreconciled data**.

Identify from the prompt: the portfolio id, the date or quarter, the required computations, and which endpoints will be needed.

### Phase 2 — Query the Environment (Authoritative Source)

Call the relevant environment endpoints to fetch **current** records. The environment is always the authoritative book of record. Typical sequence:

1. **Portfolio holdings:** `GET /api/portfolios/{portfolio_id}/holdings` — current positions, market values, weights.
2. **Reference catalogs:** `GET /api/portfolios`, `GET /api/instruments/bonds`, `GET /api/issuers`, `GET /api/indices` — metadata needed to qualify instruments, check ratings, and validate ids.
3. **Market data:** `GET /api/index-levels`, `GET /api/index-levels/{index_id}`, `GET /api/market/energy` — current pricing and time series.
4. **Allocation data:** `GET /api/allocation/opportunity-sets`, `GET /api/allocation/prior-views`, `GET /api/macro-signals`, `GET /api/policies` — views, signals, and policy constraints for allocation or committee tasks.

### Phase 3 — Reconcile and Compute

Compare the local payload data against the environment data. When there is a conflict:
- **Environment data always takes precedence** over stale local payload data.
- If the local payload and environment agree, no conflict exists.
- Never propagate stale marks, unreconciled quantities, or outdated snapshots into the final answer.

Perform any required computations (e.g., Pearson correlations from monthly simple returns, weighted metrics, post-trade projections) using the current environment data. Round all numeric fields to the precision declared in the answer template.

### Phase 4 — Assemble the JSON Answer

Build the output strictly following the `answer_template.json`:

- Include every `required` / `required_top_level_keys` key.
- Use the exact `allowed_values` for enums — no synonyms or abbreviations.
- Respect declared `precision` on every numeric field.
- Sort list items according to the ordering rules in the template (e.g., ascending by `instrument_id`, alphabetical by index id, SELL before BUY).
- If a `required_value` is declared for a field, use that exact value.
- Do not include commentary, markdown fences, or extra keys outside the template.

## Data Precedence Rule

The prompt and templates consistently enforce this rule:

> **`current_environment_over_stale_payload`** — the environment service is the current book of record. Local payloads may contain earlier worksheets, stale snapshots, or desk notes that have not been reconciled. Always refresh from the environment before producing the final answer.

When a `data_precedence` field is required in the output, use `"current_environment_over_stale_payload"` if any material conflict was detected between the local payload and the environment. Use `"no_conflict_found"` only if the local data fully matches the environment.

## Common Task Types and Their Patterns

### Credit / Bond Trade Packages

These tasks ask for BUY/SELL trade tickets with post-trade metrics and constraint checks.

- Query portfolio holdings, bond catalog, issuer data, and market/energy endpoints.
- Filter eligible bonds by: rating (IG vs HY), sector/subsector, watchlist status, yield/carry, duration.
- Ensure the proposed package stays within HY caps, duration bands, issuer concentration limits, and subsector diversification rules.
- Compute post-trade weighted metrics (market value, HY%, duration, YTM).

### Correlation Reviews

These tasks compute Pearson correlations across an index universe over a monthly-level window.

- Query `/api/index-levels` or `/api/index-levels/{index_id}` for the date range.
- Compute monthly simple returns: `(level_t - level_{t-1}) / level_{t-1}`.
- Compute the Pearson correlation matrix for all pairs.
- Identify extreme pairs (highest positive, lowest/negative).
- Flag concentration patterns (e.g., China-Asia dependence).

### Allocation View Refreshes

These tasks produce active views (UW / N / OW) for named opportunity sets.

- Query `/api/allocation/opportunity-sets` for the taxonomy.
- Query `/api/allocation/prior-views` for the prior quarter's views.
- Query `/api/macro-signals` for current signal scores and rationale codes.
- Determine view changes (UP / DOWN / UNCHANGED) versus prior quarter.
- Assign conviction (LOW / MEDIUM / HIGH) based on signal strength.
- Map signals to rationale codes from the allowed enum.

### Committee Decision Files

These tasks combine correlation findings with allocation views for multi-asset sleeves.

- Follow the correlation-review pattern for the specified index subset.
- Follow the allocation-view pattern for the specified opportunity sets.
- Derive sleeve actions (trim / add / hold / hedge / monitor / rotate) from the combined correlation and allocation signals.
- Set rebalance trigger, concentration flag, and next-step recommendation.

## Precision and Formatting Rules

- **Numeric precision:** Always follow the template's declared precision (1, 2, or 3 decimals).
- **Dates:** Format as `YYYY-MM-DD` strings.
- **Enum values:** Use exactly the strings from `allowed_values` lists — case-sensitive, no variations.
- **List ordering:** Templates specify ordering rules (alphabetical, by action, by business priority). Follow them exactly.
- **Return observations:** For correlation windows, the number of return observations = number of level dates minus 1.

## Error Handling

- If an environment endpoint returns unexpected data or is unavailable, note the limitation and proceed with what is available, clearly flagging any gaps.
- If a local payload references an instrument or index not found in the environment catalog, exclude it and note the discrepancy.
- Do not fabricate data — all figures must be derived from environment responses or computed from those responses.
