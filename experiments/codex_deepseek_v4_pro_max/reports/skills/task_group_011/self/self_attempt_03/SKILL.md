 # Credit Committee API Agent

 Reusable operating rules for completing credit-committee analytical tasks against the shared credit office public API. Follow these instructions for any branch review, segment posture, allocation, watch-list, or competing-credit task that supplies a prompt and an answer template.

 ## Workflow

 ### 1. Read the inputs

 Every task provides two files inside the `input/` directory:

 - `prompt.txt` — describes the task, target entity, reference date, and any special instructions.
 - `payloads/answer_template.json` — declares the exact JSON output shape, required keys, field types, allowed enum values, numeric precision, and sort ordering.

 Read both files completely before making any API calls. The template is the authoritative contract for the answer shape; use its enum choices and precision rules verbatim.

 ### 2. Resolve the base URL

 The prompt contains a placeholder `<TASK_ENV_BASE_URL>`. Substitute this with the actual base URL supplied by the runner. All API calls use this base.

 ### 3. API discovery and context

 Begin every task with these context endpoints to understand available data, rules, and benchmarks:

 | Endpoint | When to use |
 |---|---|
 | `GET /api/manifest` | Always call first. Describes all available API surfaces and data models. |
 | `GET /api/policies` | Always call. Returns credit policy limits, concentration caps, rating definitions, and decision rules that govern answers. |

 Then query the relevant benchmark endpoint:

 | Endpoint | When to use |
 |---|---|
 | `GET /api/benchmarks/fdic/q4-2024` | Branch-centric tasks that reference FDIC benchmarks (NPA, delinquency, CRE). |
 | `GET /api/benchmarks/ncua/q1-2025` | Credit-union segment tasks that reference NCUA benchmarks. |

 ### 4. Query entity-specific data

 Use the entity identifier from the prompt (branch_id or segment_id) to query detail endpoints:

 **Branch tasks** (branch_id provided):

 | Endpoint | Returns |
 |---|---|
 | `GET /api/branches/{branch_id}` | Branch profile, total assets, total loans. |
 | `GET /api/branches/{branch_id}/metrics` | Delinquency, NPA, ROA, concentration ratios. |
 | `GET /api/branches/{branch_id}/loans` | Loan portfolio: loan_id, borrower, exposure, current_rating, DSCR, LTV, FICO, payment_status, sector, maturity. |
 | `GET /api/branches/{branch_id}/sector-exposures` | Exposure by sector with policy limits. |
 | `GET /api/branches/{branch_id}/applications` | Pending applications: application_id, amount, sector, DSCR, LTV, FICO, purpose. |

 **Segment tasks** (segment_id provided):

 | Endpoint | Returns |
 |---|---|
 | `GET /api/credit-union-segments/{segment_id}` | Segment profile, state, metrics, peer data. |

 ### 5. Perform the analysis

 Follow the specific analysis pattern demanded by the prompt (see sections below). Use the policies endpoint to inform all decisions — policy limits, rating-scale definitions, and decision rules are authoritative.

 ### 6. Output the answer

 - Produce a single JSON object that matches the template shape exactly.
 - Use only the enum values defined in the template.
 - Apply numeric precision exactly as specified (e.g., 2 decimal places for currency, 4 for ratios).
 - Sort lists as specified in the template ordering rules.
 - Do not include narrative text, commentary, or markdown outside the JSON object.

 ## Analysis Patterns

 ### Rating Migration Review (e.g., train_1)

 When the prompt asks to re-derive risk ratings and summarize migration:

 1. **Identify the target population**: Filter loans by `current_rating >= target_current_rating_min` (e.g., 3 or worse).
 2. **Re-derive ratings**: Apply the rating methodology from `/api/policies`. Consider objective factors: DSCR, LTV, FICO, payment status, collateral coverage, sector risk. The rating scale is integer-based where lower is better (1 = strongest).
 3. **Build migration table**: Group re-rated loans by `final_rating`. For each group report loan_count, total exposure, and loan_ids sorted ascending.
 4. **Identify material downgrades**: Loans where `final_rating > current_rating`. Calculate downgrade notches as `final_rating - current_rating`.
 5. **Select top problem credit**: The loan with the worst combination of highest final_rating, largest exposure, and most severe payment status. Break ties by exposure size.
 6. **Assign watch-list actions**: For every regraded loan, assign an action based on final_rating:
    - Rating 1-2: `monitor`
    - Rating 3-4: `watchlist`
    - Rating 5: `special_assets`
    - Rating 6: `workout`
    - Rating 7: `partial_chargeoff_review`
    - Rating 8+: `legal_referral`
 7. **NPA benchmark**: Compute `branch_npa_ratio = branch_npa_exposure / branch_total_loans`. Compare against the FDIC benchmark ratio. `variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`. `variance_bps = variance_ratio * 10000`.

 ### Lending Allocation Package (e.g., train_2)

 When the prompt asks for an allocation package with application decisions:

 1. **Determine lending capacity**: From branch metrics and policy, compute `lending_capacity_q1`.
 2. **Score and rank applications**: Evaluate each pending application against policy criteria (DSCR, LTV, FICO, sector, amount). Assign priority — highest quality and strategic fit first.
 3. **Allocate capacity**: Starting from highest priority, approve applications until capacity is exhausted. Use `conditional_approve` for applications that are close but need extra conditions. Use `decline` for applications that fail policy minimums. Use `defer` for borderline cases.
 4. **Check concentration**: After each approval, compute `post_approval_pct = (existing_sector_exposure + approved_amount) / total_loans`. Compare against `limit_pct` from policy. Flag any sector exceeding its limit.
 5. **Assign decline reasons**: Map each declined application to the applicable reason codes from the template enum. Use only codes that apply to the specific rejection rationale.
 6. **Post-approval view**: Recompute all sector concentrations after all approvals are applied.

 ### Segment Posture (e.g., train_3)

 When the prompt asks for a credit-union segment posture recommendation:

 1. **Read segment data**: Query the segment endpoint for state-level metrics.
 2. **Compare against NCUA benchmarks**: Extract the state's delinquency_bps, loan_to_share_pct, roaa_bps, and positive_net_income_pct. Compare against the national and peer-state values from the NCUA benchmark table.
 3. **Determine posture**:
    - `continue_approving` — all metrics stronger than or equal to national/peer medians.
    - `continue_with_tighter_conditions` — mixed picture, state is weaker on 1-2 metrics.
    - `temporarily_pause` — state is weaker on most or all metrics.
 4. **Select controls**: Choose required checklist gates and added operating controls based on the posture and segment risk profile. More conservative posture → more controls.
 5. **Define escalation triggers**: Map each trigger condition to an owner. Use trigger IDs and conditions from the template enum.
 6. **Write interpretation**: Choose the committee message that best matches the capacity and risk picture.

 ### Watch-List Stress Packet (e.g., train_4)

 When the prompt asks for a watch-list stress and workout review:

 1. **Identify adverse population**: Filter loans where `current_rating >= adverse_rating_min` (e.g., 6 or worse).
 2. **Assign CDFI-style risk classes**: Derive a `factor_score` from objective loan attributes (DSCR, LTV, FICO, payment_status, months_on_book, collateral_type). Map factor_score to risk_class:
    - Score 1-2: `Prime`
    - Score 3-4: `Desirable`
    - Score 5-6: `Satisfactory`
    - Score 7-8: `Watch`
    - Score 9-10: `Doubtful`
    - Score 11+: `Projected Loss`
 3. **Set monitoring cadence**: Based on the most common risk class:
    - Predominantly Watch or worse → `monthly`
    - Mixed Satisfactory/Watch → `quarterly`
    - Predominantly Satisfactory or better → `semiannual`
 4. **DSCR stress**: For every adverse loan with a DSCR value, apply the +200bp shock:
    - `stressed_dscr = base_dscr - 0.20` (a 200bp reduction of the DSCR ratio expressed as a decimal adjustment proportionate to the original; apply as `base_dscr * (1 - 0.20 / base_dscr_scale)` if base_dscr is expressed differently, otherwise compute `stressed_dscr = base_dscr - 0.20` for ratios near 1.0x).
    - `breaches_threshold = stressed_dscr < breach_threshold` (commonly 1.00).
 5. **Queue workout actions**: For each adverse loan, assign a recommended_action based on risk_class and payment_status. Sort workout queue by descending exposure, then ascending loan_id.
 6. **Severe bucket counts**: Group adverse loans by `current_rating` and `payment_status`, counting loan_count and summing exposure.

 ### Competing CRE Decision (e.g., train_5)

 When the prompt asks to compare two CRE applications and recommend one:

 1. **Score both applications**: Compute a weighted CDFI score for each. Factors typically include DSCR, LTV, FICO, borrower experience, property type, market conditions. Lower score is better.
 2. **Map score to class**:
    - Weighted score ≤ 3.5: `approve_quality`
    - Weighted score 3.6-5.5: `conditional`
    - Weighted score ≥ 5.6: `weak`
 3. **Stress DSCR**: Apply the CRE dual-stress formula (rate shock + vacancy/income shock) to compute `stressed_dscr`. Mark `breaches_threshold` if stressed_dscr falls below the coverage_breach_threshold (commonly 1.20).
 4. **Check CRE concentration**: Compute `existing_cre_concentration = existing_cre_exposure / total_loans`. Compute `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_amount) / total_loans`. Compare against `cre_policy_limit_pct` from policy. `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
 5. **FDIC delinquency comparison**: Compute `branch_delinquency_ratio` from branch metrics. Compare against `fdic_benchmark_ratio` for the `total_real_estate_30_89_pct` metric. `fdic_variance_ratio = branch_delinquency_ratio - fdic_benchmark_ratio`. `fdic_variance_bps = fdic_variance_ratio * 10000`.
 6. **Recommend**: Select the stronger credit (lower weighted score, stronger stressed DSCR). Assign `approve` or `conditional_approve` based on whether any conditions are needed. For the unselected credit, assign `decline` or `defer` with the applicable reason codes.
 7. **Assign conditions**: Choose from the template's conditions enum based on the risk profile of the selected application.

 ## Enum Reference

 These enums appear across multiple templates. Use exactly as written.

 ### Decision

 `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

 ### Watch-List / Workout Actions

 `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

 ### Payment Status

 `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

 ### CDFI Risk Class

 `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

 ### Decline Reason Codes

 `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

 ### Benchmark Metrics (FDIC)

 `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`

 ### Segment Posture

 `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

 ### Escalation Owners

 `credit_risk_manager`, `operations_control_manager`, `lending_committee_chair`

 ## Numeric Precision Rules

 - **Currency (USD)**: Always round to 2 decimal places.
 - **Ratios / percentages (as decimal)**: Always round to 4 decimal places.
 - **Basis points (bps)**: Always round to 2 decimal places.
 - **Integer fields** (counts, ratings, scores): Whole numbers, no decimals.

 ## Output Discipline

 - Output must be a single valid JSON object.
 - All required_top_level_keys must be present.
 - All nested required_keys must be present.
 - Enum fields must use exactly one of the allowed_values.
 - Lists must be sorted according to the template's ordering rule.
 - No trailing commas.
 - No comments, explanations, or markdown wrapping the JSON.
 - Null values are not allowed; use 0 for numeric fields and empty list `[]` where appropriate.

 ## API Error Handling

 - If any endpoint returns a non-2xx status, retry once after a short delay.
 - If the retry fails, report the failing endpoint and status code in a structured error field at the top level of the JSON.
 - If data needed for a computation is missing from the API response, use 0 for numeric fields and document the gap.

 ## Task Type Detection

 Identify the task type from the prompt to choose the correct analysis pattern:

 - **rating migration** / **regrade**: Use Rating Migration Review pattern.
 - **allocation** / **lending capacity**: Use Lending Allocation Package pattern.
 - **segment** / **posture** / **credit union**: Use Segment Posture pattern.
 - **watch-list** / **stress** / **adverse**: Use Watch-List Stress Packet pattern.
 - **competing** / **compare** / **CRE decision**: Use Competing CRE Decision pattern.
