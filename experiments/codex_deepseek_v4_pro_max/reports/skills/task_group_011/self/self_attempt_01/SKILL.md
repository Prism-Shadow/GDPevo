## Credit Risk Committee Skill

### Purpose

Prepare committee-ready JSON analyses for lending committees using the shared credit office public API. This skill covers loan portfolio regrades, allocation packages, credit-union segment posture reviews, watch-list stress packets, and competing credit decisions. Do not include narrative text outside the JSON response.

### API Reference

The API base URL is always supplied by the runner as `<TASK_ENV_BASE_URL>`. No credentials are required. Replace path placeholders (`{branch_id}`, `{segment_id}`) with the identifiers named in the task input.

| Method | Endpoint | Use |
|--------|----------|-----|
| GET | `/api/manifest` | Discover available data surfaces |
| GET | `/api/policies` | Retrieve credit policies (limits, rating floors, sector caps) |
| GET | `/api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 industry benchmarks |
| GET | `/api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 credit-union benchmarks |
| GET | `/api/branches` | List all branches |
| GET | `/api/branches/{branch_id}` | Branch detail (name, region, capacity) |
| GET | `/api/branches/{branch_id}/metrics` | Branch-level financial and risk metrics |
| GET | `/api/branches/{branch_id}/loans` | Loan portfolio (ratings, exposure, payment status, DSCR, LTV, FICO, borrower, sector) |
| GET | `/api/branches/{branch_id}/sector-exposures` | Sector-level exposure breakdowns |
| GET | `/api/branches/{branch_id}/applications` | Pending credit applications |
| GET | `/api/credit-union-segments/{segment_id}` | Credit-union segment detail and metrics |

### Universal Operating Rules

1. **Read the answer template first.** Every task includes `input/payloads/answer_template.json`. Study it before making any API calls. It specifies required top-level keys, field types, enum choices, ordering rules, and numeric precision. Conform exactly.

2. **Enum discipline.** Never invent values. Use only the allowed values listed in the template for each field. If a template lists `["monitor", "watchlist", "special_assets"]`, do not substitute "enhanced_monitoring" or any other string.

3. **Ordering discipline.** Every list field declares an ordering rule (e.g., "ascending by loan_id", "descending by exposure"). Sort results accordingly.

4. **Precision discipline.** Respect declared precision: currency fields round to 2 decimals, ratios to 4 decimals, integers where specified.

5. **Start with manifest and policies.** Fetch `/api/manifest` to confirm available endpoints, then `/api/policies` to load rating criteria, concentration limits, and decision rules. Cross-reference every decision against policy.

6. **JSON only.** Return a single valid JSON object. Do not wrap in markdown fences, add commentary, or include narrative text outside the JSON.

7. **All-caps identifiers.** Branch IDs, segment IDs, and application IDs are uppercase strings (e.g., `REDWOOD`, `CIVIC_NC_FIRE_EMS`, `HAR-APP-901`). Loan IDs may follow branch-specific patterns.

### Analysis Patterns

#### Pattern A: Rating Migration Review

Used when the task asks to re-derive risk ratings and summarize migration.

1. Fetch the target branch, its metrics, and its loan portfolio.
2. Filter loans to the regrade population: `current_rating >= target_current_rating_min` (typically 3 or worse as specified in the task).
3. Re-derive final ratings for each loan using objective factors available from the loan data (payment status, DSCR, LTV, FICO, sector). Apply policy rating floors from `/api/policies`.
4. Build `final_rating_exposure_totals`: group regraded loans by final rating, count loans, sum exposure.
5. Build `migration_from_current_rating_X`: for loans currently at the specified rating floor, show where they migrate (by final rating) with loan_count, exposure, and loan_ids.
6. Assign watch-list actions based on final rating severity:
   - Ratings 1-3: `monitor`
   - Ratings 4-5: `watchlist`
   - Ratings 6-7: `special_assets`
   - Ratings 8-9: `workout`
   - Rating 10+ with payment issues: `partial_chargeoff_review` or `legal_referral`
7. Compute NPA benchmark variance using FDIC Q4 2024 data:
   - `branch_npa_ratio = branch_npa_exposure / branch_total_loans`
   - `variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`
   - `variance_bps = variance_ratio * 10000`
8. Identify material downgrades: loans whose `final_rating - current_rating >= 2` notches.
9. Select the top problem credit: the loan with the worst final rating; break ties with highest exposure and worst payment status.

#### Pattern B: Lending Allocation Package

Used when the task asks to allocate lending capacity across pending applications.

1. Fetch the branch, its metrics, sector exposures, and pending applications.
2. Determine `lending_capacity_q1` from branch metrics or policy.
3. Score each application against policy criteria (DSCR, LTV, FICO, sector limits).
4. Rank applications by priority (credit quality, policy compliance, exposure impact).
5. Allocate capacity to the highest-priority applications, marking remaining as declined or deferred.
6. For each decision, determine `approved_amount`, `bank_capacity_used`, and any `conditions`.
7. Compute `concentration_flags`: for each sector with a post-approval exposure exceeding its policy limit, flag it with a handling decision.
8. Build `decline_reasons`: map each declined application to its reason codes from the controlled enum.
9. Build `post_approval_concentrations`: recalculate each sector's exposure and concentration after approvals.

#### Pattern C: Credit-Union Segment Posture

Used when the task asks for a segment posture page with benchmark comparisons.

1. Fetch the segment from `/api/credit-union-segments/{segment_id}`.
2. Fetch NCUA Q1 2025 benchmarks.
3. Build `state_metrics` from the NCUA benchmark table for the relevant state.
4. Build `peer_comparison`: compare the segment's state metrics to national and peer-state medians. Use "higher", "lower", or "equal" for direction.
5. Determine `posture`: `continue_approving` if metrics are strong, `continue_with_tighter_conditions` if mixed, `temporarily_pause` if weak.
6. Select `controls` (checklist gates and added operating controls) from the template enums based on risk posture.
7. Define `escalation_triggers` with trigger IDs, conditions, and owners from the template enums.
8. Build `interpretation` with capacity, external risk, risk tolerance, and committee message from the template enums.

#### Pattern D: Watch-List Stress Packet

Used when the task asks for a watch-list stress review of adversely rated loans.

1. Fetch the branch and its loan portfolio.
2. Filter to the adverse population: `current_rating >= adverse_rating_min` (typically 6 or worse as specified in the task).
3. Assign CDFI-style risk classes from available objective factors (payment status, DSCR, LTV, FICO):
   - `Prime`: strong metrics across all factors
   - `Desirable`: good metrics, minor weakness
   - `Satisfactory`: adequate metrics, moderate risk
   - `Watch`: elevated risk, requires monitoring
   - `Doubtful`: high risk, probable loss
   - `Projected Loss`: severe distress, loss expected
   - Compute a `factor_score` (integer) reflecting cumulative risk factors.
4. Determine `monitoring_cadence` from the worst risk class present: `monthly` for Doubtful/Projected Loss, `quarterly` for Watch, `semiannual` for Satisfactory and better.
5. Apply the +200bp DSCR stress for loans with DSCR available:
   - `stressed_dscr = base_dscr * (1 - 0.02)` (approximation) or use formula from policy
   - `breaches_threshold = stressed_dscr < breach_threshold`
6. Build `workout_queue` ordered by descending exposure. Assign `recommended_action` from risk class severity and payment status. Mark `projected_loss` true for Doubtful and Projected Loss classes.
7. Build `severe_bucket_counts`: group loans by `current_rating` and `payment_status`, count loans, sum exposure.

#### Pattern E: Competing CRE Decision

Used when the task asks to compare two CRE applications and recommend one.

1. Fetch the branch, its metrics, loans, sector exposures, and the two target applications.
2. Score both applications using weighted CDFI criteria (lower score is better). Derive `score_class`: `approve_quality` (score ≤ threshold), `conditional` (moderate), `weak` (elevated). Determine initial `decision` per application.
3. Apply the CRE dual-stress formula: compute `stressed_dscr` for each application's base DSCR and record whether it breaches the coverage threshold.
4. Compute concentration metrics:
   - `existing_cre_exposure` from branch loans and sector exposures
   - `existing_cre_concentration = existing_cre_exposure / branch_total_loans`
   - `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_approved_amount) / (branch_total_loans + selected_approved_amount)`
   - `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`
5. Compare to FDIC benchmark for `total_real_estate_30_89_pct`: compute branch delinquency ratio, benchmark ratio, variance.
6. Select the stronger application as the recommended path. The unselected application gets `decline` or `defer` with reason codes from the restricted enum.
7. Build `conditions` list from the template enum based on the risk profile of the selected credit.

### Common Computations

| Computation | Formula |
|-------------|---------|
| NPA ratio | `branch_npa_exposure / branch_total_loans` |
| Variance ratio | `branch_ratio - benchmark_ratio` |
| Variance bps | `variance_ratio * 10000` |
| Concentration ratio | `sector_exposure / total_loans` |
| Post-approval concentration | `(current_exposure + approval_amount) / (total_loans + approval_amount)` |
| Policy variance bps | `(post_approval_pct - limit_pct) * 10000` |
| DSCR stress (+200bp) | `stressed_dscr = base_dscr * (1 - shock)` where shock = 0.02, or use formula from policy |
| Downgrade notches | `final_rating - current_rating` (positive = downgrade) |
| Material downgrade | `downgrade_notches >= 2` |

### Decision Enum Reference

Common across multiple templates:

- **Path / Decision**: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`
- **Watch-List Actions**: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`
- **Risk Classes (CDFI)**: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`
- **Payment Status**: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`
- **Reason Codes**: `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`
- **Posture**: `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

### Error Handling

- If an API endpoint returns an error or empty response, do not fabricate data. Report what is available.
- If a loan lacks DSCR, exclude it from stress results rather than guessing.
- If a benchmark metric is missing, note the gap explicitly rather than substituting.
- If an application's data is incomplete for scoring, mark it with `documentation_gap` as a reason code.
