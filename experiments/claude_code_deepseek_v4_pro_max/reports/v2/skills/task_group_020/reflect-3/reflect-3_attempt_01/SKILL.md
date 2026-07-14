# Aster Legal Deal Desk — Skill Guide

## 1. Environment

Single entry point for all deal data:

```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:9020
```

All deal, document, policy, benchmark, and clause data lives at this origin. Do not start
local env processes, read env/ source files, or use `localhost`/`127.0.0.1`.

### Key pages and API surfaces

| Resource | Path | Description |
|---|---|---|
| Home / search | `GET /` | Deal index, search bar |
| Deal page | `GET /deals/D-XXXX-NNN` | Full deal profile with embedded JSON |
| Deal API | `GET /api/deals/D-XXXX-NNN` | Structured JSON for the deal (includes benchmarks array) |
| Policy page | `GET /policies/P-XXXX` | Policy rules, thresholds, escalation triggers |
| Document page | `GET /documents/DOC-XXXX` | Document sections, version status |
| Benchmarks | `GET /benchmarks?industry=…` | Industry-specific benchmark data |
| Clause compare | `GET /clauses/compare?deal_id=D-XXXX-NNN` | Draft-vs-playbook clause comparison |
| API health | `GET /api/health` | Seed, counts, status |

**Preferred data extraction pattern:**
1. Fetch the deal page (`/deals/D-XXXX-NNN`) and locate the `<details class="raw"><summary>Raw Deal JSON</summary>` block — this contains the authoritative structured record for the deal.
2. Fetch the deal API (`/api/deals/D-XXXX-NNN`) for the benchmarks array attached to that deal.
3. Fetch the policy page for the deal's `policy_id`.
4. Fetch referenced documents if their `<details class="raw">` block contains info not already in the deal page's embedded JSON.

The deal page embeds **multiple** raw JSON blocks — Economics, Parties, Schedules, Client Positions / Negotiation Context, Draft Terms, and the aggregated Raw Deal JSON. The aggregated Raw Deal JSON is the single source of truth; the others are rendered views of the same data.

---

## 2. Source Precedence and Authority

### Document status hierarchy (strongest to weakest)

1. **ACTIVE** — current, authoritative document. Always preferred.
2. **STALE** — superseded; use only as context, never as a primary source.
3. **TEMPLATE** — generic drafting-system placeholder; disregard for deal-specific answers.

### Source-type priority for deal-specific values

1. **Active cap table** — governs seller names, ownership percentages, roles, as-of date, and allocation source.
2. **Active client instruction email** (`DOC-XXXX-EMAIL-03`) — the latest written client instructions supersede generic playbook positions where they conflict. Look for `Instruction summary`, `Fallbacks`, and `Escalations` sections.
3. **Active draft agreement** (`DOC-XXXX-DRAFT-02`) — current draft terms and negotiation posture.
4. **Applicable policy/playbook** — policy rules provide thresholds, escalation triggers, and fallback positions. Rule IDs map to specific `check_id` / `term_id` / `issue_id` values.
5. **Industry benchmarks** — provide market-context data (sample size, mean, median, count-above-threshold). Use only the benchmark set matching the deal's industry and topic.

### Stale / template distractors

Every deal room includes stale cap tables and generic template documents. These are **intentional distractors**.
- **Stale cap tables** have earlier as-of dates and notes explaining why they were superseded (e.g., "Pre-option-exercise summary; superseded by June cap table").
- **Template documents** carry a generic effective date (often `2026-01-15`) and contain placeholder values.
- In clause comparison tables, stale/template rows have `Status: STALE` or `Status: TEMPLATE` badges.

**Rule**: always verify the **Status** badge before using a clause comparison row, document, or schedule. ACTIVE only.

---

## 3. Numeric and Unit Conventions

### Currency
- All USD amounts are **integers** (whole dollars). No commas, no decimal points, no `$` sign.
- Compute amounts as `rate × base_value` and round to the nearest integer.

### Percentages
- Expressed as **percentage points** (e.g., 7.50 means 7.50%, not 0.075).
- **Two decimal places** unless the template specifies otherwise.
- When computing a percentage: `(numerator / denominator) × 100`, then round to two decimal places.

### Months
- Always **integers**. Convert "two years" → 24, "five years" → 60, etc.

### Null handling
- Use `null` (JSON null, not the string `"null"`) for numeric fields that do not apply.
- Use `[]` (empty array) for list fields with no items.

---

## 4. Field-Population Rules

### Party names
- Use the **exact** name as displayed in the deal page. Do not shorten, expand, or normalize.
- For **employee names**, include the full display string including title/role suffix: `"Mina Calder, founder/CTO"` not `"Mina Calder"`.
- For **buyer**, use the primary buyer entity from `parties.buyers[0]`.
- For **seller_group**, use the `seller` field from the Raw Deal JSON.

### Sort ordering
- **Seller allocations**: sort by `seller_name` ascending (lexicographic).
- **Material consents / contracts**: sort by `contract_name` ascending.
- **Employment employees**: sort by displayed employee name ascending.
- **Issue lists / escalation terms**: sort by `issue_id` or `term_id` ascending (lexicographic on the enum value).
- **Code lists** (e.g., mae_omitted_carveouts, committee_members, service codes): sort alphabetically.

### Allocations
- `gross_proceeds_usd` / per-seller proceeds = `headline_value × ownership_percent / 100`.
- Proceeds should be integers (whole dollars).
- Seller allocation list must include every seller from the **active** cap table.

### Material contracts in consent lists
- Include **all** material contracts from the active material contracts schedule.
- Sort by contract name ascending.
- Use exact contract names as displayed.

---

## 5. Enum Mapping Conventions

### Deal structure
Map the `structure` field from the deal page exactly:
- `STOCK_PURCHASE` → STOCK_PURCHASE
- `ASSET_PURCHASE` → ASSET_PURCHASE
- `MERGER` → MERGER
- `CARVE_OUT` → CARVE_OUT (use STOCK_PURCHASE or ASSET_PURCHASE as the underlying structure when the template requires one)

### NWC adjustment mechanic
Map descriptive text to enum:
- "Dollar-for-dollar adjustment outside collar" → `DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`
- "Dollar-for-dollar from first dollar" → `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR`
- Text indicating no adjustment → `NO_POST_CLOSING_ADJUSTMENT`

### Basket type
- `deductible` → `DEDUCTIBLE`
- `tipping` → `TIPPING`
- `none` or 0% → `NONE`

### HSR condition
- `hsr_required: false` with size-of-person basis → `NO_HSR_CONDITION_COOPERATION_ONLY`
- `hsr_required: true` → `HSR_CLOSING_CONDITION`
- `hsr_basis_code` maps to the specific regulatory reasoning:
  - "size-of-person test is not met" → `SIZE_OF_PERSON_TEST_NOT_MET`
  - "reportable thresholds are not met after debt adjustments" → `REPORTABLE_THRESHOLDS_MET` / `THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS`
  - "counsel memo missing" → `COUNSEL_MEMO_MISSING`

### Consent condition status
- If any material contract has `condition_type: "closing"` and `consent_required: true` → `MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`
- If all are post-closing covenants only → `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS`
- If no material consents exist → `NO_MATERIAL_CONSENTS_REQUIRED`

### Per-share price
- If the *active* cap table reports ownership percentages but **no share count** → `per_share_price_usd: null`, `per_share_price_basis: "NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE"`
- If share count is available → compute `equity_value / total_shares`, round to two decimal places, `per_share_price_basis: "CALCULATED_FROM_ACTIVE_CAP_TABLE"`

### Price per percent point
- `price_per_as_converted_percent_point_usd = equity_value / 100` (integer)

---

## 6. Issue Identification (Review / Escalation Tasks)

### Which issues to include
- Only include issues where the **active draft** deviates from the **applicable policy/playbook threshold**.
- An issue is **material** if it exceeds a stated escalation trigger in the policy or client instructions.
- **Do not** include an issue just because the draft and playbook use different wording; there must be a quantifiable gap or a policy-escalation trigger breached.
- When uncertain whether an issue is material, check: does the client instruction email list it as an escalation? Does the policy have an explicit `escalation_triggers` entry for it?

### Matching issues to policy rules
- Each issue should reference the policy `rule_id` that governs it.
- If a draft term has no corresponding policy rule, it is likely **not** a priority/material issue.
- Use the policy `approval_category` to determine `approval_owner` / `committee_route`.

### Severity guidelines
- **CRITICAL**: draft term exceeds a policy escalation trigger AND client instructions demand removal/change.
- **HIGH**: draft term exceeds playbook preferred range but has a stated fallback.
- **MEDIUM**: draft term is at the boundary of policy range or has minor deviations.
- **LOW**: draft term is within policy but warrants notation.

---

## 7. Common Pitfalls

1. **Using stale cap tables.** The stale cap table has earlier ownership data and omits later transactions (option exercises, rollover elections). Always use `source_doc_id` from the active cap table.

2. **Truncating display names.** Employee names in the deal data often include titles (e.g., `"Mina Calder, founder/CTO"`). These full display strings are the expected values, not just the person's name.

3. **Precision mismatches.** NWC collar as percent of equity value requires `(collar / equity_value) × 100` computed to two decimal places. Integer division or rounding to zero decimal places will produce wrong values.

4. **Including non-issues.** Adding borderline issues (e.g., NWC mechanics that are disclosed but not escalated by policy) reduces the score. Be conservative: only include issues where the policy explicitly triggers escalation.

5. **Template/stale clause rows.** Clause comparison tables mix ACTIVE, STALE, and TEMPLATE rows. Filter to ACTIVE only before making comparisons.

6. **Policy-client instruction conflict.** Where the client instruction email specifies a stricter or different position than the general playbook, the client instruction controls. The email's `Instruction summary` section is the primary directive.

7. **Sort order violations.** Every list field in the output templates has a specified sort order. Lexicographic sort on the displayed value, not an internal ID.

8. **Seller allocation computation.** Gross proceeds for each seller = `headline_value × ownership_percent / 100`. The sum of all seller gross proceeds should equal `headline_value` (for all-cash deals) or `total_consideration`.

9. **MAE carve-out enumeration.** When listing omitted MAE carve-outs, compare the draft's included carve-outs against the full set expected by the playbook. List only the codes that are **missing** from the draft.

10. **Benchmark memo flag.** When the committee charter or client instructions mention a benchmark memo requirement (e.g., "RTF is outside the stated policy range"), set `benchmark_memo_required: true` in the strategic context.

---

## 8. Workflow Pattern

For each task:

1. **Read the prompt** to identify the deal ID, client side, and output schema.
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand required keys, enums, sort orders, and field types.
3. **Fetch the deal page** and extract the Raw Deal JSON block.
4. **Fetch the deal API** (`/api/deals/D-XXXX-NNN`) for deal-attached benchmarks.
5. **Fetch the policy page** for the deal's `policy_id` to get rule thresholds, escalation triggers, and rule IDs.
6. **Fetch the client email document** (`DOC-XXXX-EMAIL-03`) for latest written instructions.
7. **Construct the answer** following these rules:
   - Populate known fields from the Raw Deal JSON (deal_id, dates, parties, economics).
   - Map descriptive text to controlled enum values.
   - Compute derived values (percentages, per-seller proceeds).
   - Apply sort ordering to every list.
   - For review/escalation tasks: include only issues with clear policy breaches.
   - For term-population tasks: populate every field in the template.
8. **Validate**: check sort orders, enum spellings, integer vs float types, null vs empty-array usage.
