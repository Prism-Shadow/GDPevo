## Skill: Asteria Investment Office — Institutional Portfolio Workflow

### Overview
Use this skill whenever a task references the **Asteria Investment Office** shared environment, an institutional portfolio (IDs like `PF-*`), or output templates that demand strict JSON contracts with precision, ordering, and codebook constraints. The skill encodes reusable operating rules distilled from the Asteria credit, equity, allocation, fixed-income, and multi-asset workflows.

---

### Rule 1 — Environment Is the Book of Record
The shared Asteria environment service is the **current official source** for portfolio holdings, instrument master data, issuer records, index levels, policies, prior views, macro signals, and opportunity-set taxonomies. Always prefer environment data over any local payload when the two disagree.

**Access pattern:**
- Read the environment base URL from `environment_access.md` (or the analogous project README).
- Use **HTTP GET** against `{base_url}{endpoint}` for every allowed endpoint.
- For endpoints containing `{placeholder}` (e.g., `/api/portfolios/{portfolio_id}/holdings`), replace the placeholder with the relevant id from the task input or from a preceding catalog-list call.
- All endpoints are read-only; no authentication is required.

---

### Rule 2 — Local Payloads Are Intake Context, Not Source of Truth
Every task ships with one or more local JSON payloads (e.g., `desk_request.json`, `review_request.json`, `risk_meeting_memo.json`). Treat these as:
- **Intake context**: portfolio ID, review window, requested opportunity sets, desk preferences, candidate shortlists.
- **Potentially stale**: any marks, quantities, holdings snapshots, or as-of dates in the payload may predate the current environment.

**When the two conflict**, the current environment wins. If the template includes a `data_precedence` field, report `"current_environment_over_stale_payload"` when a conflict is detected and resolved in favour of the environment, or `"no_conflict_found"` otherwise.

---

### Rule 3 — Answer Template Is the Strict Output Contract
Every task includes an `answer_template.json` (or equivalent schema file). Produce output that conforms **exactly** to that template. In particular:

1. **Required keys**: every key listed under `required`, `required_top_level_keys`, or `required_keys` must be present.
2. **Required values**: when a field specifies `required_value`, set it to that exact string.
3. **Enum constraints**: never emit a value outside the `allowed_values` list for an `enum` field.
4. **Type constraints**: use the declared JSON type (`string`, `number`, `boolean`, `list`, `object`).
5. **Length constraints**: lists with a declared `length` must contain exactly that many items.
6. **Ordering constraints**: follow `ordering` rules (e.g., "ascending alphabetical by index id", "Sort by action with SELL before BUY, then by instrument_id ascending", "Sort by the request payload's focus_opportunity_sets order").

---

### Rule 4 — Numeric Precision
Round every numeric field to the precision declared in the template (`"precision": N` means N decimal places). Examples:
- `"precision": 1` → one decimal place (e.g., `4.0`).
- `"precision": 2` → two decimal places (e.g., `3.10`).
- `"precision": 3` → three decimal places (e.g., `0.847`).

Do not add extra digits beyond the declared precision. For whole-number representations of a precision-N value, include trailing zeros to match the declared precision (e.g., `4.0`, not `4`, when precision is 1).

---

### Rule 5 — Correlation Calculations
When a task requires correlation values:
- Compute **Pearson correlation** of **monthly simple returns** derived from consecutive index levels.
- Use the level window specified in the request payload (e.g., a 12-month monthly-level window spanning a start and end date).
- Round to the precision declared in the template (typically three decimals).
- Order index ids within a pair alphabetically.

---

### Rule 6 — Portfolio Constraint Validation
When constraint checks are required, validate against the current environment data:
- **HY cap**: compare post-trade high-yield allocation against the policy cap.
- **Duration band**: confirm post-trade weighted modified duration falls within the CIO range.
- **Issuer/subsector diversification**: ensure selected instruments do not create excessive concentration.
- **Watchlist avoidance**: BUY actions must avoid watchlisted issuers or instruments.

Report each check as a boolean (`true` = pass, `false` = fail) in the constraint_checks or exception_flags block.

---

### Rule 7 — Watchlist Handling
- SELL actions targeting watchlisted instruments are permitted and expected when reducing risk.
- BUY actions must **avoid** any instrument whose issuer or instrument id appears on the current watchlist.
- If the template includes a `watchlist_handling` block, list the watchlist instruments being sold and confirm buys avoid the watchlist.

---

### Rule 8 — Risk Overlay Selection
When a risk overlay is requested:
- Select an `overlay_code` from the allowed set that best matches the macro-signal and portfolio-risk picture.
- Provide a `primary_action` from the allowed action set.
- Supply `rationale_codes` as an ordered list, highest business priority first, using only the allowed rationale code set.

---

### Rule 9 — JSON-Only Output
Unless the prompt explicitly permits narrative commentary, return **only** the JSON object — no markdown fences, no explanatory text before or after. The output must parse as valid JSON.

---

### Rule 10 — General Workflow Sequence
For any Asteria task, follow this order:
1. **Read local payloads** — extract portfolio id, review window, opportunity sets, preferences, and any stale hints.
2. **Read the answer template** — understand the output contract before querying data.
3. **Query the environment** — fetch current portfolio holdings, instrument details, issuer records, index levels, policies, macro signals, prior views, and opportunity sets as needed.
4. **Resolve data conflicts** — prefer environment data over stale local payload data.
5. **Compute derived values** — correlations, post-trade metrics, HY reductions, constraint flags.
6. **Assemble the JSON** — build the output object strictly following the template, applying precision, ordering, and enum constraints.
7. **Validate** — confirm every required key is present, every enum value is allowed, every numeric field has correct precision, and every list follows its ordering rule.

---

### Rule 11 — Rationale Code Selection
When rationale codes are required, choose only from the template's allowed set. Map the code to the substantive signal:
- `GROWTH_IMPROVES` — improving growth outlook.
- `RATE_CUT_SUPPORT` — expected rate cuts support the asset.
- `CREDIT_SPREAD_RISK` — credit spread widening risk.
- `DOLLAR_DEFENSIVE` — USD strength as a defensive factor.
- `CHINA_DEPENDENCE` — exposure reliant on China dynamics.
- `LATAM_DIVERSIFIER` — Latin America as a diversifying allocation.
- `INDIA_OFFSET` — India used as an offset or diversifier.
- `DURATION_SUPPORT` — duration tailwind.
- `HY_VALUATION_RISK` — high-yield valuations stretched.
- `EUROPE_RECOVERY` — European recovery narrative.
- `JAPAN_POLICY_RISK` — Japan policy uncertainty.
- `NEUTRAL_BALANCE` — no strong directional signal; neutral positioning.

---

### Rule 12 — Endpoint Discovery
The environment access file lists all allowed endpoints. Use the catalog endpoints to discover available ids:
- `/api/portfolios` → list all portfolios.
- `/api/instruments/bonds` → list all bonds.
- `/api/issuers` → list all issuers.
- `/api/indices` → list all indices.
- `/api/index-levels` → list available index-level series.
- `/api/allocation/opportunity-sets` → list opportunity sets.
- `/api/allocation/prior-views` → list prior-quarter views.
- `/api/macro-signals` → list macro signal scores.
- `/api/market/energy` → list energy market data.

When a detail endpoint requires an id, first fetch the catalog, then use the returned id to call the detail endpoint.
