# Skill: Asteria Investment Office API Tasks

## When to use

Use this skill when a task requires querying the Asteria Investment Office shared environment (a REST API) to retrieve portfolio, market, policy, or macro data, perform institutional-finance calculations, and return JSON that conforms to a provided answer template.

## Overview

These tasks follow a repeatable pattern:
1. Read the task prompt, request payload, and answer template.
2. Discover and fetch all relevant data from the API.
3. Compute derived quantities (returns, correlations, allocations, policy checks).
4. Assemble and validate JSON output against the template schema.

The API is read-only and stateless; every answer must be built from live endpoint data combined with the static request/template files.

---

## Step 1: Read local inputs before touching the API

Always start by reading all files in the task input directory:

- `prompt.txt` — the high-level instruction.
- `payloads/*.json` — usually a request/memo file and an `answer_template.json`.

The request JSON tells you which portfolio, indices, date windows, and checks are required. The answer template tells you the exact structure, keys, and nesting depth expected in the output.

**Critical:** Do not add commentary outside the JSON. Return only the JSON object.

---

## Step 2: Discover the environment

Read `environment_access.md` in the workspace root to get the base URL (e.g. `GDPEVO_ENV_BASE_URL`).

Hit the API root path (`/`) with `GET` to retrieve the human-readable endpoint catalog. Use it to confirm which paths exist, such as:

- `/api/catalog` — IDs for portfolios, policies, indices, issuers, bonds, opportunity sets.
- `/api/policies` — constraint definitions (correlation thresholds, HY limits, duration bands, allocation mapping rules).
- `/api/portfolios` and `/api/portfolios/<portfolio_id>` — summaries and current holdings.
- `/api/indices` and `/api/index-levels` and `/api/index-levels/<index_id>` — regional equity index metadata and monthly levels.
- `/api/allocation/opportunity-sets`, `/api/allocation/prior-views` — allocation taxonomy and existing views.
- `/api/macro-signals` — scored macro signals by opportunity set and quarter.
- `/api/instruments/bonds` — bond universe with ratings, duration, spreads, energy-linked flags.
- `/api/issuers` — issuer watchlist and research records.
- `/api/market/energy` — current energy market signals.

If a requested `portfolio_id` does not appear in `/api/catalog`, still try `GET /api/portfolios/<portfolio_id>` directly; the catalog may be incomplete.

---

## Step 3: Fetch all referenced data

Based on the request payload, issue parallel `curl` (or equivalent) calls to collect:

1. **Portfolio record** — `GET /api/portfolios/<portfolio_id>`
   - Extract `holdings`, `market_value_usd_m`, `constraints`, `as_of_date`.
2. **Policy record** — `GET /api/policies` (or the specific `policy_id` referenced by the portfolio)
   - Extract thresholds (e.g. `correlation_high_threshold`, `max_hy_allocation_pct`, `duration_band_years`, allocation mapping thresholds).
3. **Index levels** — `GET /api/index-levels/<index_id>` for every index mentioned
   - Returns a list of `{date, level}` objects, typically monthly.
4. **Bond universe** — `GET /api/instruments/bonds` if credit holdings are involved
   - Needed to map `instrument_id` to `rating_bucket`, `modified_duration_years`, `spread_bps`, `energy_linked`, `issuer_id`.
5. **Issuers** — `GET /api/issuers` if concentration or watchlist checks are required.
6. **Macro signals / prior views / opportunity-sets** — if the task asks for allocation views or signal linkage.

Cache responses locally (e.g. as JSON files or shell variables) so you can inspect them while writing calculation logic.

---

## Step 4: Perform calculations precisely

The tasks commonly require one or more of the following calculations. Use the exact formulas described; do not approximate or round prematurely unless the template explicitly asks for a specific precision.

### 4.1 Simple return over a window

```
return_pct = (end_level / start_level - 1) * 100
```

Identify the correct start and end dates from the request payload (e.g. "12-month monthly-level window" means the first and last months in the level series). Use the levels exactly as provided.

### 4.2 Monthly return series

For each consecutive pair of monthly levels:

```
monthly_return_i = (level_i / level_{i-1}) - 1
```

Build an array of these returns. This is the input for correlation and volatility calculations.

### 4.3 Pearson correlation between two indices

Given two same-length arrays of monthly returns (aligned by date):

```
corr = covariance(x, y) / (std_dev(x) * std_dev(y))
```

Use population or sample standard deviation consistently; if the task does not specify, sample standard deviation (N-1 denominator) is conventional for financial time series. The correlation window must match the request (e.g. "current 12-month monthly-level window" means the 12 most recent monthly returns, which requires 13 level observations).

### 4.4 Portfolio allocation percentage

For each holding:

```
allocation_pct = (quantity_usd_m / market_value_usd_m) * 100
```

Sum of all holdings’ `quantity_usd_m` should equal `market_value_usd_m`, but use the stated total as the denominator.

### 4.5 Sector / sleeve aggregation

Group holdings by `sleeve` or `sector` (from the bond/issuer metadata), sum `quantity_usd_m` per group, then divide by total `market_value_usd_m`.

### 4.6 High-yield (HY) allocation

From the bond universe, map each fixed-income holding’s `instrument_id` to its `rating_bucket`. Sum quantities where `rating_bucket == "HY"`, then:

```
hy_allocation_pct = (hy_quantity_sum / total_market_value) * 100
```

### 4.7 Duration band check

For each bond holding, look up `modified_duration_years`. Count how many unique holdings fall into each policy duration band. The policy’s `duration_band_years` array defines the band boundaries (commonly `[3.0, 5.0]`, yielding bands: `<3`, `3-5`, `>5`).

### 4.8 Issuer concentration

Map each bond holding to its `issuer_id` (via the bond universe). Sum `quantity_usd_m` per issuer, then:

```
issuer_concentration_pct = (issuer_quantity / total_market_value) * 100
```

### 4.9 Allocation view mapping from macro signals

The policy object `allocation_mapping` contains thresholds:

- `OW_min` (e.g. 0.35) → view "OW" if signal score >= this.
- `UW_max` (e.g. -0.35) → view "UW" if signal score <= this.
- Otherwise view "N" (neutral).

Match each `opportunity_set` in the request to its `macro-signals` record for the requested quarter, read the `score`, and apply the thresholds.

### 4.10 Correlation concentration vs diversification classification

Using the policy correlation thresholds:

- If correlation >= `correlation_high_threshold` (commonly 0.8), the pair represents **concentration risk**.
- If correlation <= `correlation_low_threshold` (commonly 0.2), the pair supports **diversification**.

### 4.11 Policy exception / check logic

Many answer templates require boolean or enumerated checks. Common patterns:

- **Risk policy breached?** — compare computed metric (e.g. `hy_allocation_pct`) against the policy limit; return `true` only if strictly above the limit.
- **Within tolerance?** — check if metric is inside an inclusive band.
- **Duration band counts** — return counts per band as integers.
- **Watchlist / rating flags** — read issuer records and bond records for `watchlist`, `rating`, or `energy_linked` booleans.

---

## Step 5: Assemble the answer JSON

1. **Start from the template.** Copy the structure of `answer_template.json` exactly.
2. **Fill scalar fields** (e.g. `portfolio_id`, `as_of_date`, `review_date`) from the request payload or the API portfolio record.
3. **Insert computed objects/arrays** using the calculations above.
4. **Preserve key names.** Do not rename template keys, omit optional keys that are present in the template, or add extra top-level keys unless explicitly instructed.
5. **Use correct JSON types:** numbers (not strings), booleans (`true`/`false`, not strings), and arrays/objects exactly as templated.

If the template contains a placeholder like `"TBD"` or an empty array `[]`, replace it with the actual computed value.

---

## Step 6: Validate before returning

Run a quick sanity check:

- Is the top-level object valid JSON? (Use `python3 -m json.tool` or `jq`.)
- Do all required template fields have non-placeholder values?
- Are percentages roughly sensible (e.g. between 0 and 100 for allocations)?
- Do dates match the format used in the template?
- If the task mentions overriding stale local notes with current API records, verify that you used the latest API `as_of_date` and levels rather than any date embedded in the request payload.

---

## Common pitfalls

| Pitfall | Mitigation |
|---------|------------|
| Using stale dates from the request JSON instead of the API’s current `as_of_date`. | Always prefer the API portfolio record’s `as_of_date` or the latest index level date. |
| Off-by-one in correlation windows. | 12 monthly returns require 13 level observations; ensure the date range matches the policy/request. |
| Omitting `candidate=true` bonds when the task asks for the full universe. | Read `/api/instruments/bonds` and filter by the request’s criteria. |
| Wrong denominator for allocation percentages. | Use the portfolio’s `market_value_usd_m`, not a subtotal or stale number. |
| Including narrative outside JSON. | Return **only** the JSON object. |
| Confusing `rating_bucket` ("IG" vs "HY") with the letter rating. | Policy checks almost always use the bucket, not the fine rating. |
| Missing energy-linked or watchlist linkage. | Cross-reference issuer records and bond flags when the task mentions energy themes or watchlists. |

---

## Example workflow (illustrative, not an answer)

```bash
# 1. Read inputs
cat input/prompt.txt
jq . input/payloads/request.json
jq . input/payloads/answer_template.json

# 2. Explore API
BASE="http://<host>:<port>"
curl -s "$BASE/" | grep -oE '/api/[^<]+'

# 3. Fetch data
curl -s "$BASE/api/portfolios/PF-EXAMPLE" > portfolio.json
curl -s "$BASE/api/policies" > policies.json
curl -s "$BASE/api/index-levels/IDX_EXAMPLE" > levels.json
curl -s "$BASE/api/instruments/bonds" > bonds.json
curl -s "$BASE/api/macro-signals" > signals.json

# 4. Compute (typically done in Python or jq)
python3 << 'PY'
import json
portfolio = json.load(open("portfolio.json"))
# ... perform calculations ...
PY

# 5. Validate
python3 -m json.tool answer.json > /dev/null
```

---

## Summary checklist

- [ ] Read `prompt.txt`, request payload, and `answer_template.json`.
- [ ] Read `environment_access.md` for the base URL.
- [ ] Fetch portfolio, policy, index levels, bonds, issuers, signals as required.
- [ ] Compute returns, correlations, allocations, and policy checks using exact formulas.
- [ ] Populate the answer template without renaming keys or adding external commentary.
- [ ] Validate JSON syntax and sanity-check numerical outputs.
- [ ] Return **only** the JSON.
