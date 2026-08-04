This skill provides reusable instructions for working with a shared credit-office REST API to produce committee-ready JSON work products. Apply it when a task references the credit-office API or asks for credit-risk analysis in the shapes described below.

## Prerequisites

The runner supplies the API base URL as `<TASK_ENV_BASE_URL>`. All endpoints use HTTP GET; no authentication is required. Do not call `/api/health`, reset/reseed endpoints, evaluator paths, task source answers, or the judge API.

## Available endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/manifest` | Lists available branches, benchmark versions, and segment identifiers (use before retrieving specific resources). |
| `GET /api/policies` | Returns institution-wide credit policies including sector concentration limits, CRE policy limits, credit floors, and rating definitions. |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC quarterly banking profile: industry NPA ratios, delinquency rates by loan type, and peer-group statistics. |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA quarterly credit-union data: state-level metrics (delinquency bps, loan-to-share, ROAA, positive net income) and national aggregates. |
| `GET /api/branches` | Lists all branch identifiers. |
| `GET /api/branches/{branch_id}` | Branch metadata (name, total assets, total loans, etc.). |
| `GET /api/branches/{branch_id}/metrics` | Branch-level performance metrics (NPA exposure, delinquencies by aging bucket, DSCR coverage, CRE concentration). |
| `GET /api/branches/{branch_id}/loans` | Loan portfolio: each loan includes `loan_id`, `borrower_name`, `exposure`, `current_rating` (1-8, where 1 is best), `payment_status`, `sector`, `dscr`, `ltv`, `fico`, and other origination fields. |
| `GET /api/branches/{branch_id}/sector-exposures` | Outstanding exposure grouped by sector for the branch. |
| `GET /api/branches/{branch_id}/applications` | Pending credit applications with `application_id`, `requested_amount`, `sector`, `dscr`, `ltv`, `fico`, `collateral_type`, and other underwriting fields. |
| `GET /api/credit-union-segments/{segment_id}` | Credit-union segment data including state affiliation, capacity, and segment-level delinquency/loss history. |

## General workflow

Every task supplies an `answer_template.json` that defines the exact output schema. Start by reading the template thoroughly — it specifies required keys, enum choices, numeric precision, sort order, and allowed values. The template is the authoritative contract; every value in the final JSON must conform to its constraints.

### Step 1 — Gather all relevant data

Determine which endpoints are needed from the task prompt and the template's required fields:
- For **branch-level** tasks: fetch the branch detail, its metrics, its loans, its sector exposures, and its applications.
- For **segment-level** tasks: fetch the credit-union segment.
- For **benchmark** tasks: fetch the relevant FDIC or NCUA benchmark data.
- Always fetch `/api/policies` when the template references policy limits, concentration caps, or credit floors.
- Always fetch `/api/manifest` when you need to discover available identifiers or benchmark versions.

Make all independent GET requests in parallel to minimise latency.

### Step 2 — Filter and classify the target population

Each task defines a target population for analysis. Common filters:
- **By rating**: e.g., "loans currently rated 3 or worse", "adversely rated (rating 6+)". Use `current_rating >= N`.
- **By payment status**: Nonaccrual, 90+ Days Past Due, 60 Days Past Due, 30 Days Past Due, Current.
- **By sector**: e.g., CRE, C&I, consumer.
- **By application status**: pending, or a specific subset of application IDs named in the prompt.

### Step 3 — Re-derive ratings or assign risk classes where required

When the template requires you to re-derive ratings (regrade) or assign risk classes:

**Rating re-derivation (1-8 scale):** Use the loan's objective factors (payment status, DSCR, LTV, FICO, collateral coverage, days past due) against the policy-defined rating thresholds. Downgrade by at least one notch for each material adverse factor; upgrade only when every factor supports it. The policy endpoint provides the rating definitions. A loan on nonaccrual or with collateral shortfall generally floors at rating 7 or 8.

**CDFI-style risk classes:** Assign each loan a `factor_score` (integer) derived from available objective factors — payment delinquency, DSCR coverage, collateral position, borrower credit. Map scores to risk classes: Prime (lowest score), Desirable, Satisfactory, Watch, Doubtful, Projected Loss (highest). The mapping is monotonic; higher scores mean worse credit quality.

### Step 4 — Compute benchmark variances

When comparing branch metrics against FDIC or NCUA benchmarks:
- Identify the correct benchmark metric from the template's enum (e.g., `total_loans_noncurrent_pct`, `total_real_estate_30_89_pct`).
- Extract the benchmark value from the benchmark endpoint response.
- Compute `variance_ratio = branch_ratio - benchmark_ratio`.
- Compute `variance_bps = variance_ratio * 10000` (1 bp = 0.0001).
- For NCUA peer comparisons, evaluate North Carolina's metrics against the US national aggregate and against named peer states. Determine direction (higher/lower/equal) for each metric.

### Step 5 — Apply stress tests where specified

**DSCR stress:** Apply the specified shock (e.g., +200bp) to each loan's base DSCR. The formula is typically `base_dscr * (1 - shock_fraction)` or a dual-stress formula provided in the template (e.g., `dscr * 0.85 / 1.18` for combined rate + vacancy stress). Compare the stressed DSCR against the coverage breach threshold (usually 1.0 or 1.25). A loan breaches when `stressed_dscr < threshold`.

### Step 6 — Queue watch-list and workout actions

Assign follow-up actions from the allowed enum: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

Mapping guidance:
- **Nonaccrual + rating 8**: `partial_chargeoff_review` (or `legal_referral` if collateral is severely impaired).
- **90+ Days Past Due**: `special_assets`.
- **Rating 7, Current**: `special_assets` or `watchlist` depending on exposure size and stress breach.
- **Rating 6, Current or 30-60 DPD**: `watchlist`.
- **Stress breach without delinquency**: `watchlist`.
- **Projected Loss risk class**: `partial_chargeoff_review`.

### Step 7 — Make committee-level decisions

For **allocation decisions**: rank applications by credit quality (higher DSCR, lower LTV, stronger FICO, policy compliance). Approve until capacity is exhausted. Apply `conditional_approve` when a credit is strong but needs a structural condition. Apply `decline` with reason codes from the template's enum. `defer` when information is missing but the credit could be viable.

For **competing-credit decisions**: score each application on objective factors, compute weighted CRE credit scores, evaluate stressed DSCR for both, compare concentration impact, and select the stronger one. The weaker application gets a disposition (`decline` or `defer`) with reason codes.

### Step 8 — Assemble the JSON answer

- Populate every required top-level key from the template.
- Use exact enum values from the template; never invent values.
- Round numeric values to the precision declared in the template (usually 2 decimals for currency, 4 decimals for ratios).
- Sort lists exactly as the template specifies (ascending by the named field; for `loan_ids`, ascending alphabetically).
- For string identifiers, use the exact values returned by the API; do not transform or abbreviate.
- Output only valid JSON with no narrative text outside it.

## Common credit-risk calculations

| Concept | Formula |
|---------|---------|
| NPA ratio | `nonaccrual_exposure / total_loans` |
| Delinquency ratio | `(30dpd + 60dpd + 90dpd + nonaccrual) / total_loans` |
| CRE concentration | `cre_exposure / total_loans` |
| Policy variance (bps) | `(actual_pct - limit_pct) * 10000` |
| Stressed DSCR (+200bp) | `base_dscr * (1 - 0.02 * duration_factor)` or as directed by the template |
| Sector post-approval exposure | `existing_sector_exposure + approved_amount` |
| Sector post-approval concentration | `post_approval_exposure / (total_loans + approved_amount)` |

## Enum reference

**Risk ratings:** 1 (best) through 8 (worst). Rating 4+ is typically considered adverse; rating 7 indicates substandard; rating 8 is loss/doubtful.

**Payment statuses:** `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`.

**Workout actions (ascending severity):** `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

**Credit decision paths:** `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`.

**CDFI risk classes (ascending quality):** `Projected Loss`, `Doubtful`, `Watch`, `Satisfactory`, `Desirable`, `Prime`.

**Segment posture:** `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`.

**Benchmark versions:** `fdic_q4_2024`, `ncua_q1_2025`.

**FDIC benchmark metrics:** `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`.

## Task-type specific guidance

### Rating migration review
Fetch branch loans, metrics, policies, and FDIC benchmark. Filter loans meeting the rating threshold. Re-derive each loan's rating. Build `final_rating_exposure_totals` grouped by final rating. Track migration specifically for loans that were originally at the stated current rating. Identify material downgrades (3+ notch moves). Pick the top problem credit as the highest-exposure loan on nonaccrual or with the worst final rating. Assign watch-list actions and compute action coverage.

### Lending-committee allocation
Fetch branch detail, pending applications, sector exposures, and policies. Determine total lending capacity for the period. Score and rank applications. Allocate capacity to the strongest applications first. For each application, record decision, approved amount, capacity consumed, and conditions (or "none"). Flag sector concentrations that exceed policy limits post-approval. Map declined applications to reason codes. Compute post-approval sector concentrations.

### Credit-union segment posture
Fetch the segment by ID and the NCUA benchmark. Determine the segment's state. Compare the state's metrics against national aggregates and named peer states. Choose a posture based on whether state metrics and segment history support continued approval. List required checklist gates and any added operating controls needed for the posture. Define escalation triggers with condition descriptions and named owners. Write a concise committee interpretation covering capacity, external risk, risk tolerance, and a committee message.

### Watch-list stress and workout
Fetch branch loans and metrics. Filter to adversely rated loans (rating 6+). Assign CDFI risk classes and factor scores. For loans with DSCR available, apply the stress formula and identify breaches. Build the workout queue ordered by exposure, assigning recommended actions based on risk class, payment status, and stress results. Summarise severe risk-rating buckets (rating 6+) grouped by current rating and payment status.

### Competing CRE decision
Fetch branch detail, branch metrics, the two named applications, branch loans, sector exposures, policies, and FDIC benchmark. Score each application on weighted CRE factors. Apply the CRE dual-stress formula. Compute existing and post-approval CRE concentration. Compare CRE delinquency against FDIC benchmark. Select the stronger credit and give the unselected one a disposition with reason codes. List committee conditions for the selected path.

## Output quality rules

- Do not include narrative text outside the JSON object.
- Use only the enum values defined in the answer template.
- Sort every list exactly as the template specifies.
- Round all numbers to the precision stated in the template.
- Verify every required key is present before delivering the answer.
- If a field is inapplicable (e.g., no loans breach the stress threshold), use an empty list `[]`, not `null` or omitted keys.
