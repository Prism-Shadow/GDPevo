---
name: asteria-portfolio-analytics
description: Produce structured JSON outputs for Asteria Investment Office portfolio analytics tasks. Use this skill whenever the user mentions Asteria, investment office, institutional portfolio, credit strategy, equity correlation, allocation views, fixed-income rebalancing, risk rotation, investment committee JSON, or any task that references "PF-" portfolio identifiers. The skill covers trade construction, correlation computation, active allocation view generation, and multi-asset committee reporting against a shared environment service.
---

# Asteria Portfolio Analytics

## Overview

This skill supports institutional portfolio analytics at Asteria Investment Office. Every task follows a common pattern: read the local prompt and payloads, query the shared Asteria environment service, perform financial computations, check portfolio constraints, and produce a strict JSON output that matches a provided answer template.

Do not improvise the output schema or add narrative outside the JSON. The answer template is authoritative; fill it exactly.

## Common workflow

Follow this sequence for every Asteria task:

### 1. Read the task prompt and every local payload file

Start inside the task's `input/` directory. There will always be a `prompt.txt` and an `input/payloads/` directory containing at least an `answer_template.json`. Read them all before querying the environment. The template declares the exact output shape — required keys, enumeration values, ordering rules, numeric precision, and any required literal values (like a fixed `portfolio_id` or `task_id`).

Additional payload files provide intake context: desk requests, review memos, committee packets, allocation notes. They may contain **stale** marks, worksheet snapshots, or candidate shortlists from an earlier date. The task prompt typically warns about staleness. Treat payload data as directional guidance only; prefer the current environment service as the book of record.

### 2. Query the shared Asteria environment service

The base URL is documented in the task's environment context. Read that context (usually `environment_access.md` or a task-group `env/README.md`) for the exact URL and allowed endpoints. A typical base is `http://task-env:9010/`.

The environment provides these endpoint families (see [references/api.md](references/api.md) for full details):

- **Portfolios & holdings** — `/api/portfolios`, `/api/portfolios/{id}/holdings`
- **Instruments** — `/api/instruments/bonds`
- **Issuers** — `/api/issuers`
- **Market data** — `/api/market/energy`
- **Indices & levels** — `/api/indices`, `/api/index-levels`, `/api/index-levels/{id}`
- **Allocation** — `/api/allocation/opportunity-sets`, `/api/allocation/prior-views`
- **Macro signals** — `/api/macro-signals`

Query all endpoints relevant to the task in parallel where possible. The root endpoint (`GET /`) often returns an as-of date that should be used as the `as_of_date` field throughout the answer.

Always use the environment's current records over any stale payload data. When the environment and a payload conflict, use the environment and note the precedence in any `data_precedence` field.

### 3. Compute

Perform the computations the task requires. The main computation types are covered below in "Computational methods." Validate intermediate results before filling the template.

### 4. Fill the answer template

Produce exactly one JSON object matching the template. Follow every constraint the template declares:

- **Required keys** — every key listed in `required`, `required_top_level_keys`, or `required_keys` must appear.
- **Enumeration values** — use only values from the template's `allowed_values` lists. Do not coin new codes.
- **Ordering** — sort lists exactly as specified (alphabetical, by instrument_id, by action, by the payload's order, etc.).
- **Numeric precision** — round to the declared precision. For example, `precision: 1` means one decimal place; `precision: 2` means two; `precision: 3` means three. Do not carry extra digits.
- **Fixed literal values** — some fields have `required_value` (e.g., a specific `portfolio_id` or `task_id`). Use that exact string.

Return the JSON object and nothing else unless the prompt explicitly asks for commentary.

## Domain concepts

Understand these terms before working with the data:

- **Portfolio (PF-*)**: A managed investment portfolio identified by a code like `PF-EN-ALTA`, `PF-FI-LUMEN`, `PF-INT-NEXVEN`, `PF-MA-HELIO`.
- **Bond instrument (BND_*)**: A fixed-income security with an issuer, coupon, maturity date, rating, sector/subsector, yield-to-maturity (YTM), modified duration, and market value.
- **Investment grade (IG) vs. high yield (HY)**: Bonds rated BBB-/Baa3 or above are IG; below that are HY. HY bonds carry more credit risk and portfolios typically have an HY allocation cap.
- **Watchlist**: Issuers flagged for elevated credit risk. The risk team wants watchlisted exposure reduced or eliminated.
- **Modified duration**: A measure of interest-rate sensitivity in years. Portfolios have a CIO-approved duration band.
- **Yield to maturity (YTM)**: The annualized return if the bond is held to maturity, expressed as a percentage.
- **Index (IDX_*)**: An equity benchmark like `IDX_EM` (Emerging Markets), `IDX_CHINA`, `IDX_INDIA`, `IDX_LATAM`, `IDX_WORLD`, `IDX_EAFE`. Index levels are monthly time series.
- **Opportunity set**: A region/asset-class pairing used in allocation views (e.g., "Europe" equities, "U.S. Treasuries" duration, "EUR" currency).
- **View (UW / N / OW)**: Underweight, Neutral, or Overweight — the active allocation stance relative to policy weights.
- **Conviction (LOW / MEDIUM / HIGH)**: How strongly the team holds the view.
- **Rationale code**: A short enum explaining the driver behind a view (e.g., `GROWTH_IMPROVES`, `CHINA_DEPENDENCE`, `HY_VALUATION_RISK`).
- **Macro signal**: A quantitative score (positive = supportive, negative = headwind) used alongside prior views to determine allocation changes.
- **Risk overlay**: A portfolio-level tilt (e.g., `DURATION_QUALITY_TILT`) applied across all sleeves.

## Computational methods

### Pearson correlation of monthly simple returns

Given two time series of monthly index levels (consecutive month-end values), compute the Pearson correlation:

1. Calculate simple returns for each series: for each pair of consecutive levels `L[t-1]` and `L[t]`, return = `(L[t] - L[t-1]) / L[t-1]`.
2. The number of return observations is one fewer than the number of levels.
3. Compute the Pearson correlation coefficient between the two return series.

Use the script at [scripts/correlation.py](scripts/correlation.py) for reliable computation. Feed it two files, each containing a JSON array of level values. It prints the correlation rounded to 6 decimals; round further to the template's required precision.

When the task requires correlations across many index pairs, save each index's level array to a temp file, then run the script pairwise. Sort pair members alphabetically by index ID when reporting.

### Weighted portfolio metrics

Compute post-trade portfolio metrics by aggregating across all holdings after applying proposed trades:

- **Total market value**: Sum of market values of all holdings.
- **HY allocation percentage**: Sum of market values of HY-rated holdings divided by total market value, times 100.
- **Weighted modified duration**: Sum of (holding market value × its bond's modified duration) divided by total market value.
- **Weighted YTM**: Sum of (holding market value × its bond's YTM) divided by total market value.

Round each to the template's declared precision.

### Constraint checks

For credit and risk tasks, verify each constraint as a boolean:

- **HY cap**: Post-trade HY allocation is at or below the portfolio's HY cap (fetch the cap from the environment's policy or portfolio metadata).
- **Duration band**: Post-trade weighted duration falls within the CIO-approved range (fetch from policy/portfolio metadata).
- **Issuer diversification**: No single issuer exceeds the concentration limit among the selected trades.
- **Subsector diversification**: Selected trades are spread across multiple subsectors; no single subsector dominates.
- **Watchlist avoidance**: No BUY trade targets a watchlisted issuer, and watchlisted SELL candidates are correctly identified.

### Allocation view derivation

When refreshing active allocation views for a new quarter:

1. Read the prior quarter's views from `/api/allocation/prior-views`.
2. Read current macro signal scores from `/api/macro-signals`.
3. For each opportunity set:
   - If the signal score is strongly positive and the prior view was N or UW, consider upgrading to OW (`change: "UP"`).
   - If the signal score is strongly negative and the prior view was N or OW, consider downgrading to UW (`change: "DOWN"`).
   - If the signal is near zero or consistent with the prior view, keep unchanged (`change: "UNCHANGED"`).
4. Assign a rationale code that best explains the driver (e.g., strong positive European signal → `EUROPE_RECOVERY`; weak EM signal with China linkage → `CHINA_DEPENDENCE`).
5. Conviction follows signal strength and consistency: strong, consistent signals → `HIGH`; moderate or mixed → `MEDIUM`; weak or noisy → `LOW`.

## Output discipline

Every Asteria answer is a single JSON object. Follow these rules exactly:

1. **Match the template structure**: Every key, every nesting level, every list length must match. If the template says `"length": 2`, produce exactly 2 items.
2. **Use only enumerated values**: Never invent a new action code, view code, rationale code, segment, or theme. The template's `allowed_values` is exhaustive.
3. **Respect ordering**: When the template says "Sort ascending by instrument_id", sort ascending by instrument_id. Alphabetical means lexicographic (standard string sort). "Sort by action with SELL before BUY" means group SELL items first, then BUY, then sort within each group.
4. **Round precisely**: Never output more decimal places than the template declares. Use standard rounding (half-up).
5. **Fill every required field**: If a required field has no meaningful value, use the appropriate null/empty form from the template's context. But most fields will have concrete values after querying the environment.
6. **Return only JSON**: Do not wrap the JSON in markdown fences, do not add explanatory text, do not include commentary outside the JSON object — unless the prompt explicitly asks for it.

## Environment precedence

Payload files (desk requests, memos, committee packets) often contain data labeled as "stale" or from an earlier worksheet. When a payload field conflicts with the current environment service:

- Use the environment value.
- Set any `data_precedence` field to `"current_environment_over_stale_payload"`.
- If no conflicts exist, use `"no_conflict_found"`.
- The template may provide other precedence enum values; use the one that matches the actual situation.

## Task-specific patterns

### Credit trade construction

For trade-package tasks (e.g., energy credit, fixed-income rotation):
- Start by fetching the portfolio holdings and the full bond catalog in parallel.
- Filter the bond catalog to eligible instruments: correct sector/theme alignment, IG or acceptable carry, not on the current watchlist.
- For BUY tickets, rank candidates by YTM or carry attractiveness while ensuring issuer and subsector diversification across the ticket set.
- For SELL tickets, prioritize watchlisted holdings and HY positions that create the most risk pressure.
- Compute post-trade metrics after simulating the proposed trades against the current holdings.
- The `sales_positioning` fields (target segment, theme) should reflect the strategy's narrative — match the theme to the actual bond exposures selected.

### Correlation review

For equity correlation tasks:
- Read the index universe from the payload (or use all available indices).
- Fetch levels for every index. The payload specifies the date window; use only levels within that range.
- Compute pairwise Pearson correlations across the universe.
- Identify the pair with the highest positive correlation and the pair with the lowest (most negative) correlation.
- For concentration analysis, check whether the China-Asia Pacific ex-Japan correlation exceeds a material threshold (infer the threshold from the environment's policy or index metadata if available).
- Diversification candidates are indices showing low or negative correlation to the dominant risk factor.
- Sleeve actions are directional: `trim` for concentrated sleeves, `add` for diversifiers, `monitor` for borderline cases.

### Risk rebalancing

For fixed-income risk rotation:
- Identify HY holdings and watchlisted holdings from the current portfolio (query holdings + bonds + issuers in parallel).
- The memo's stale exception board may list target instruments, but verify each against the current environment: an instrument that was watchlisted last week may be clear now, or vice versa.
- Select SELL candidates from confirmed HY/watchlist positions. Size them to achieve at least the minimum HY reduction target from the memo.
- Select BUY candidates from the bond catalog: IG-rated, not watchlisted, with adequate duration and yield contribution.
- Match total SELL and BUY notional as closely as practical.
- After simulation, check all exception flags.

### Multi-asset committee files

For committee JSONs that combine correlation and allocation:
- Run the correlation analysis on the specified index subset first.
- Then run the allocation view refresh for the focused opportunity sets.
- Cross-reference: correlation findings should inform sleeve actions, while allocation views should reflect macro signals and prior views.
- The `rebalance_trigger` and `next_step` fields capture the committee's decision posture based on whether any risk limits are breached.

## References

- [references/api.md](references/api.md) — Detailed API endpoint reference with expected response shapes and common field names.
- [scripts/correlation.py](scripts/correlation.py) — Compute Pearson correlation from monthly index level time series.
