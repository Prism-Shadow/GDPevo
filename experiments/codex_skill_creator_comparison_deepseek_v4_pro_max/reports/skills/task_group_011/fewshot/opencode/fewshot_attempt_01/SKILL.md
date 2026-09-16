---
name: credit-risk-committee
description: Bank credit risk committee analysis using a shared credit office REST API. Use this skill whenever the user mentions credit risk committee, branch loan review, rating migration, lending committee allocation, credit union segment posture, watch-list stress testing, CRE competing decision, or any task that references a shared credit office API, FDIC benchmarks, NCUA benchmarks, bank branch metrics, or CDFI-style risk scoring. Activate for any prompt about loan portfolio reviews, committee-ready JSON outputs for bank branches, adverse-rated loan workouts, sector concentration analysis, DSCR stress testing, NPA benchmark comparisons, or risk rating regrades. Even when the user does not use the exact phrase "credit risk," if they mention branch-level loan analysis with an API base URL placeholder like <TASK_ENV_BASE_URL>, proceed with this skill.
compatibility: Requires curl and a JSON processor (jq or Python json module).
---

# Credit Risk Committee Analysis

Produce committee-ready JSON work products for bank credit risk reviews using a shared credit office public REST API. The API exposes branch data, loan portfolios, pending applications, sector exposures, credit policies, and FDIC/NCUA benchmark datasets. This skill guides the agent through data gathering, credit-policy application, metric computation, stress testing, and structured JSON output.

## Core Workflow

Every credit committee task follows the same five-stage pipeline. Do not skip stages or reorder them.

1. **Parse** the task prompt and answer template
2. **Collect** all relevant data from the API
3. **Apply** credit policy rules to the data
4. **Compute** required metrics, scores, and stress results
5. **Produce** the final JSON answer matching the template exactly

---

## Stage 1: Parse the Task Prompt

Read the prompt and the answer template file (always under `input/payloads/answer_template.json`). Extract:

- **branch_id** or **segment_id**: the target entity
- **review_date**: the as-of date for the analysis (format YYYY-MM-DD)
- **Population definition**: which loans or applications to include. Common definitions:
  - "currently rated 3 or worse" -> filter loans where `current_rating >= 3`
  - "currently rated 6 or worse" -> filter loans where `current_rating >= 6`
  - "adversely rated" -> same as 6 or worse
  - Specific application IDs listed in the prompt
- **Analysis type**: what the committee needs (rating migration, allocation, posture, stress, competing decision)
- **Template requirements**: every required key, enum constraint, ordering rule, and numeric precision from the template

Identify which of these product types you are building. The prompt language always makes it clear:

| Product | Prompt keywords |
|---------|----------------|
| Rating migration review | "rating migration", "re-derive risk ratings", "regrade", "downgrades" |
| Lending allocation package | "allocation", "lending-committee allocation", "pending applications" |
| Segment posture | "posture", "credit-union segment", "state metrics" |
| Watch-list stress | "watch-list", "stress packet", "adversely rated", "CDFI", "workout" |
| Competing CRE decision | "competing", "CRE", "compare", "two pending" |

---

## Stage 2: Collect API Data

The API base URL is provided as `<TASK_ENV_BASE_URL>` in the prompt. Replace it with the actual URL before making requests. Use `curl -s` and pipe through `jq` or Python for parsing.

### Required Endpoints (fetch in parallel where possible)

1. **Manifest** -- always first: `GET /api/manifest`
   - Discover available endpoints and response shapes
   - Use it to confirm field names before writing extraction logic

2. **Policies** -- always second: `GET /api/policies`
   - Contains credit rules: rating thresholds, concentration limits, capacity formulas, DSCR/LTV/FICO floors, benchmark selection guidance
   - All threshold values in later stages come from policies unless policies are silent, in which case apply the standard conventions in `references/formulas.md`

3. **Branch/segment core data:**
   - `GET /api/branches/{branch_id}` -- branch metadata
   - `GET /api/branches/{branch_id}/metrics` -- total loans, lending capacity, NPA figures, delinquency ratios
   - `GET /api/branches/{branch_id}/loans` -- the loan portfolio
   - `GET /api/branches/{branch_id}/sector-exposures` -- per-sector exposure and limit percentages
   - `GET /api/branches/{branch_id}/applications` -- pending applications (for allocation and CRE tasks)
   - `GET /api/credit-union-segments/{segment_id}` -- segment details, state metrics, peer states

4. **Benchmarks:**
   - `GET /api/benchmarks/fdic/q4-2024` -- FDIC quarterly bank benchmarks
   - `GET /api/benchmarks/ncua/q1-2025` -- NCUA credit union benchmarks
   - Use FDIC for bank branch tasks, NCUA for credit union segment tasks

For detailed field descriptions and response shapes, see `references/api-guide.md`.

### Parallelism

Fetch independent endpoints concurrently. A typical branch review fetches manifest, policies, branch detail, branch metrics, branch loans, sector exposures, and benchmarks -- all seven can run in parallel after the manifest confirms the endpoints.

---

## Stage 3: Apply Credit Policy Rules

### Risk Rating Framework

The shared credit office uses an **8-point rating scale** where 1 is the strongest and 8 is loss. See `references/rating-guide.md` for the full scale and regrade methodology.

When the task asks to **re-derive** or **regrade** risk ratings, evaluate each loan in the target population against its objective factors:

- **Payment status** is the strongest signal. Nonaccrual or 90+ Days Past Due forces a severe rating.
- **DSCR**: below 1.0 indicates inability to service debt from cash flow.
- **LTV**: above 100% means the collateral is worth less than the loan.
- **FICO/credit score**: low borrower credit quality.
- **Sector risk**: some sectors carry higher inherent risk.

Always **read the policies endpoint first** for the institution's specific rating rules. When policies provide explicit thresholds, use them. When policies are silent, apply the standard conventions in the rating guide.

Regraded loans that drop by **2 or more notches** are **material downgrades**. Include them in the material_downgrades list.

### Concentration Rules

Policy sets per-sector concentration limits as percentages (ratios, e.g. 0.19 = 19%). Compare each sector's exposure share against its limit. A sector is over-limit when `post_approval_pct > limit_pct`. Over-limit sectors require handling: decline the application, require participation, or grant a board exception.

### Capacity Rules

Lending capacity comes from branch metrics. Compute committed capacity as the sum of `bank_capacity_used` for approved and conditionally-approved applications. Remaining capacity = lending_capacity - committed_capacity. For participation-required applications, only the bank-retained portion counts against capacity.

Applications ranked by priority should order by some combination of credit score quality, strategic importance, and exposure size. When the template requires a priority ranking, rank highest first using a reasonable compound criterion rather than any single field.

---

## Stage 4: Compute Metrics

All formulas and computation rules are documented in `references/formulas.md`. Key computations:

| Computation | When needed |
|-------------|-------------|
| DSCR stress (+200bp) | Stress testing; divide base DSCR by 1.18 |
| CRE dual-stress | CRE competing decisions; `dscr * 0.85 / 1.18` |
| NPA ratio | Branch NPA exposure / total branch loans |
| Benchmark variance | Branch ratio minus benchmark ratio; report both as decimal and bps (x10000) |
| CDFI factor scoring | Sum weighted objective factors per loan; lower is better |
| Sector concentration | Sector exposure / total loans; compare to policy limit |

Never fabricate DSCR values. Only include loans in stress results when the API returns a DSCR field. Mark `breaches_threshold: true` when stressed DSCR falls below the breach threshold (default 1.0 unless policy specifies otherwise).

### CDFI Risk Class Mapping

Standard CDFI risk classes from lowest to highest risk: **Prime, Desirable, Satisfactory, Watch, Doubtful, Projected Loss**. Map factor scores to classes using policy thresholds, or apply a reasonable monotonic mapping from `references/formulas.md` when policies are silent.

### Watch-List Actions

Assign actions based on the combination of risk rating and payment status. See `references/formulas.md` for the mapping table. The controlled action vocabulary is:

`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

### Reason Codes

Use only the controlled vocabulary from the answer template. Common codes:

`capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

A declined application typically carries multiple reason codes. List them sorted alphabetically unless the template specifies otherwise.

---

## Stage 5: Produce JSON Output

### Template Fidelity

The answer template defines the **exact required shape**. Follow it absolutely:

- **Required keys**: every key listed as required must be present, even if the value is an empty list or zero
- **Enums**: use only the allowed values; never invent new ones
- **Ordering**: sort lists exactly as specified (ascending by loan_id, ascending by application_id, ascending by sector, etc.)
- **Numeric precision**: currency values to 2 decimal places, ratios to 4 decimal places, basis points to 2 decimal places
- **Type matching**: strings stay strings, integers stay integers (no `1.0` where `1` is required), booleans are `true`/`false` not strings

### Common Pitfalls

- **`exposure` in migration lists**: some loans stay at the same rating after regrade. Do not include them in the migration list -- migration only covers loans whose rating actually changed.
- **`loan_ids` ordering**: within each migration bucket or action group, sort loan_ids ascending.
- **`conditions`**: when the template enumerates them, use exactly the allowed strings. `"none"` means no conditions (for declined applications where no conditions apply, use `["none"]`).
- **`over_limit`**: this is a boolean, not a string.
- **`capacity` precision**: round to 2 decimal places for dollar amounts.
- **Empty populations**: when no loans match the target criteria, return zero-count summaries with empty lists, not null or missing keys.

### Validation Before Output

Before writing the final JSON:

1. Check every `required_top_level_keys` is present
2. Check every nested `required_keys` is present
3. Verify all enum values are from the allowed set
4. Verify list orderings match the template spec
5. Run `python3 -c "import json; json.load(open('output.json'))"` to confirm valid JSON
6. Compare against the template field-by-field for shape congruence

---

## Reference Files

- `references/formulas.md` -- every computation formula, action mapping, and reason code assignment rule
- `references/rating-guide.md` -- 8-point rating scale, regrade methodology, and factor weighting
- `references/api-guide.md` -- endpoint catalog, response field inference, and parsing patterns

Read the reference file that matches the computation or rule you need. Do not load all references upfront; consult them as each stage demands.
