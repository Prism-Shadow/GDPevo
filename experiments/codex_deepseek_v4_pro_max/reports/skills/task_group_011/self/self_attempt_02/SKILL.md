This skill provides reusable operating rules for a **Credit Risk Committee analyst agent** that prepares committee-ready JSON packets by interacting with a shared credit office public API.

## Preconditions

Before executing any task:

1.  Read the task `prompt.txt` to identify the task type, target identifier(s), review date, and any special parameters.
2.  Read `input/payloads/answer_template.json` to learn the exact output shape, required keys, allowed enum values, numeric precision rules, and list ordering rules.
3.  Read `environment_access.md` to confirm the API base URL and the list of allowed endpoints. Do not use any endpoint not listed.

## API Usage

- The base URL is always supplied by the runner as `<TASK_ENV_BASE_URL>`.
- No credentials are required.
- Replace path placeholders (`{branch_id}`, `{segment_id}`) with the identifier from the task prompt.
- Never call `/api/health`, reset/reseed endpoints, evaluator paths, task source answers, or the judge API.

### Available Endpoints

| Endpoint | Use when |
|---|---|
| `GET /api/manifest` | Task mentions "manifest" or needs an overview of available data. |
| `GET /api/policies` | Task needs credit policy limits, sector caps, or policy thresholds. |
| `GET /api/benchmarks/fdic/q4-2024` | Task references FDIC Q4 2024 benchmarks. |
| `GET /api/benchmarks/ncua/q1-2025` | Task references NCUA Q1 2025 benchmarks. |
| `GET /api/branches` | Task needs to list or discover branches. |
| `GET /api/branches/{branch_id}` | Task targets a specific branch by branch_id. |
| `GET /api/branches/{branch_id}/metrics` | Task needs branch-level financial/risk metrics. |
| `GET /api/branches/{branch_id}/loans` | Task needs the branch loan portfolio (ratings, exposure, payment status). |
| `GET /api/branches/{branch_id}/sector-exposures` | Task needs sector concentration or CRE exposure data. |
| `GET /api/branches/{branch_id}/applications` | Task needs pending credit applications for a branch. |
| `GET /api/credit-union-segments/{segment_id}` | Task targets a credit-union segment by segment_id. |

### Data Gathering Workflow

Fetch data in this order to ensure downstream fields have the context they need:

1.  **Branch or segment details** — `GET /api/branches/{branch_id}` or `GET /api/credit-union-segments/{segment_id}`, and `GET /api/manifest` if the task references it.
2.  **Policies** — `GET /api/policies` for limits, concentration caps, and policy thresholds.
3.  **Portfolio / applications** — `GET /api/branches/{branch_id}/loans` and/or `GET /api/branches/{branch_id}/applications`.
4.  **Metrics** — `GET /api/branches/{branch_id}/metrics` and/or `GET /api/branches/{branch_id}/sector-exposures`.
5.  **Benchmarks** — `GET /api/benchmarks/fdic/q4-2024` or `GET /api/benchmarks/ncua/q1-2025` as indicated by the task.

## Task Types and Analysis Patterns

### 1. Rating Migration Review (branch-level)

**Trigger indicators in prompt**: "rating migration", "regrade", "risk ratings", "downgrades", "NPA benchmark", "problem credit", "watch-list action coverage".

**Analysis sequence**:
- Identify the regrade population: loans with `current_rating` at or above a threshold (named in the prompt, e.g., 3 or worse).
- Re-derive final risk ratings for each loan using objective factors available in the loan data (DSCR, LTV, FICO, payment status, collateral coverage, sector risk).
- Compute rating migration: for each `current_rating`, count loans and exposure that moved to each `final_rating`.
- Identify material downgrades: loans whose rating worsened by a meaningful number of notches (typically 2+).
- Compute NPA variance: sum nonperforming exposure, compute branch NPA ratio, compare to the FDIC benchmark ratio, and compute variance in bps.
- Select the top problem credit: the loan with the worst combination of rating, payment status, and exposure.
- Assign watch-list actions from the allowed action enum based on severity.

### 2. Lending-Committee Allocation Package (branch-level)

**Trigger indicators in prompt**: "allocation package", "lending-committee", "pending applications", "capacity", "concentration", "decline reasons".

**Analysis sequence**:
- Compute branch lending capacity from metrics and policy limits.
- Score each pending application against credit policy (DSCR, LTV, FICO, sector limits, collateral).
- Assign a decision from the decision enum to each application.
- Rank approved/conditionally-approved applications by priority (credit quality, strategic fit, capacity efficiency).
- Check sector concentration limits: compare post-approval concentration against policy limits; flag any sector that would exceed its cap.
- For declined applications, assign controlled reason codes from the reason-code enum.
- Compute post-approval sector concentrations for all sectors.

### 3. Credit-Union Segment Posture (segment-level)

**Trigger indicators in prompt**: "credit-union segment", "posture", "NCUA", "state benchmarks", "peer comparison", "escalation triggers", "operating controls".

**Analysis sequence**:
- Fetch the segment details and NCUA Q1 2025 benchmark data.
- Extract state-level metrics for the segment's state: delinquency bps, loan-to-share pct, ROAA bps, positive net income pct.
- Identify peer states from the benchmark data and compare NC values to peer median and US national values.
- Determine posture: compare state metrics against escalation thresholds to decide among `continue_approving`, `continue_with_tighter_conditions`, or `temporarily_pause`.
- Select required checklist gates and added operating controls from the allowed control enums.
- Define escalation triggers with conditions from the allowed condition choices and owners from the allowed owner choices.
- Write a controlled interpretation with capacity status, external risk status, risk tolerance, and committee message — all from the allowed enum choices.

### 4. Watch-List Stress & Workout (branch-level)

**Trigger indicators in prompt**: "watch-list stress", "adversely rated", "CDFI", "risk classes", "DSCR stress", "workout", "severe buckets".

**Analysis sequence**:
- Identify the adverse-rated population: loans with `current_rating` at or above the threshold named in the prompt (e.g., 6 or worse).
- Assign CDFI-style risk classes (Prime through Projected Loss) to each adverse loan based on objective factors (payment status, DSCR, LTV, collateral position).
- Compute a factor score (integer) for each loan derived from available objective data.
- Run a +200bp DSCR stress: for each adverse loan with a DSCR value, compute `stressed_dscr = base_dscr / (1 + shock_bps / 10000)`; flag loans that breach the coverage threshold (1.00).
- Queue workout actions ordered by descending exposure: assign recommended actions from the action enum based on risk class and payment status; mark projected_loss boolean.
- Summarize severe-bucket counts: group loans by `current_rating` and `payment_status`, counting loan count and total exposure per bucket.
- Set monitoring cadence from the allowed values based on the severity of the portfolio.

### 5. Competing CRE Decision (branch-level, dual-application)

**Trigger indicators in prompt**: "competing", "CRE decision", "two applications", "selected/unselected", "weighted score", "dual-stress".

**Analysis sequence**:
- Fetch both CRE applications and branch exposure data.
- Compute a weighted CDFI score for each application (lower is better). Factors include DSCR, LTV, FICO, loan purpose/sector risk, borrower strength.
- Assign score classes (`approve_quality`, `conditional`, `weak`) based on score thresholds.
- Compute a CRE dual-stress DSCR for both applications using the stress formula (rate shock + vacancy/income shock). Identify which applications breach the coverage threshold.
- Compare existing CRE concentration against the policy limit; compute post-approval concentration for the selected application and policy variance in bps.
- Compare branch delinquency metrics against the FDIC benchmark; compute variance ratio and bps.
- Select the stronger application; assign the unselected application a disposition (`decline` or `defer`) with reason codes from the unselected reason-code enum.
- Attach conditions from the allowed conditions enum as appropriate.

## Output Rules

### JSON Discipline
- Return exactly one JSON object matching the answer template shape.
- Do not include any narrative text, markdown fences, or commentary outside the JSON.
- Every top-level key listed as `required_top_level_keys` in the template must appear in the output.
- Every nested `required_keys` object must be fully populated.

### Enum Compliance
- Every field with an `allowed_values` or `choices` list must only use values from that list.
- Reason codes, decision values, action types, posture choices, risk classes, payment statuses, monitoring cadences, conditions — all must match the template enums exactly, including case and underscores.

### Numeric Precision
- **Currency fields** (USD exposure, balance, amounts): round to 2 decimal places.
- **Ratios and percentages** (concentration pct, NPA ratio, variance ratio): round to 4 decimal places.
- **Basis points** (variance_bps, delinquency_bps): round to 2 decimal places.
- **Integer fields** (loan counts, ratings, scores, notches): output as integers with no decimal point.
- **Weighted CDFI scores**: round to 1 decimal place.

### List Ordering
- Follow the `ordering` directive on every list field in the template.
- Common orderings:
  - `ascending by <field>` — sort numerically or alphabetically by the named field.
  - `descending exposure, then ascending loan_id` — primary sort descending by exposure, secondary sort ascending by loan_id.
  - `ascending alphabetically` — sort string values alphabetically.
- Loan IDs and application IDs should be sorted as strings (lexicographic order) unless the template specifies otherwise.

### Field Population
- Derive all values from API responses — do not hardcode or guess.
- If a computed value (e.g., variance, concentration) is derived from multiple API fields, show the arithmetic explicitly in your reasoning but only output the final JSON.
- For fields where the API provides a direct value, use that value as-is (applying the stated precision).

## Watch-List Action Escalation Ladder

When assigning `recommended_action`, escalate based on severity:

| Condition | Recommended Action |
|---|---|
| Rating improved or stable, payment current | `monitor` |
| Rating downgraded 1-2 notches, payment ≤30 days | `watchlist` |
| Rating downgraded 3+ notches or payment 60+ days | `special_assets` |
| Payment 90+ days or Nonaccrual, DSCR < 1.0 | `workout` |
| Nonaccrual with projected loss | `partial_chargeoff_review` |
| Evidence of fraud, bankruptcy, or legal action | `legal_referral` |

## CDFI Risk Class Assignment

Assign risk classes from objective loan factors using this hierarchy:

| Risk Class | Typical Indicators |
|---|---|
| `Prime` | DSCR ≥ 1.50, LTV ≤ 65%, FICO ≥ 720, payment current |
| `Desirable` | DSCR ≥ 1.25, LTV ≤ 75%, FICO ≥ 680, payment current |
| `Satisfactory` | DSCR ≥ 1.10, LTV ≤ 85%, FICO ≥ 640, payment ≤30 days |
| `Watch` | DSCR 1.00–1.10, LTV 85–95%, FICO 600–640, or payment 30–60 days |
| `Doubtful` | DSCR < 1.00, LTV > 95%, FICO < 600, or payment 60–90+ days |
| `Projected Loss` | Nonaccrual, collateral underwater, or bankruptcy/legal action |

## Score Class Thresholds (Competing CRE)

| Score Class | Weighted CDFI Score Range |
|---|---|
| `approve_quality` | ≤ 2.5 |
| `conditional` | 2.6 – 4.0 |
| `weak` | > 4.0 |

## CRE Dual-Stress Formula

When a task requires CRE stress testing, apply both shocks simultaneously:

```
stressed_dscr = base_dscr × (1 - rate_shock) × (1 - vacancy_penalty)
```

Where `rate_shock` represents a +200bp interest rate increase effect on debt service and `vacancy_penalty` represents a 5-10% reduction in effective gross income. The formula name used in the `formula` field should be `"cre_dual_stress_rate_vacancy"`.

The coverage breach threshold for CRE stress is `1.00`.

## General Watch-List DSCR Stress

For non-CRE watch-list stress (train_004 pattern):

```
stressed_dscr = base_dscr / (1 + shock_bps / 10000)
```

With `shock_bps = 200`. The shock label is `"+200bp_watchlist_shock"` and the breach threshold is `1.00`.

## Revision Notes

- This skill is distilled from five credit-risk committee task patterns observed in training data.
- Task-specific final values (branch IDs, loan IDs, exact exposure amounts, application IDs, segment IDs) are never hardcoded in this skill — they are always read from the task prompt and API responses at runtime.
- If a new task type appears that does not match any of the five patterns above, fall back to the general output rules (template-first, enum discipline, numeric precision) and the data-gathering workflow, and adapt the analysis using the closest-matching pattern as a guide.
