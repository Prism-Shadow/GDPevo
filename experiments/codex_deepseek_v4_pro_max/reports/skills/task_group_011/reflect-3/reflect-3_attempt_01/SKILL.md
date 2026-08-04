## Credit Office Task Solver

### Overview
Solve credit-office committee tasks by querying a shared public API, applying credit policy rules, and producing JSON answers that conform to task-specific templates.

### Core Workflow

1. **Read the task prompt** (`prompt.txt`) to identify the target entity (branch_id, segment_id, or application_ids), the as-of date, and the committee's request.

2. **Locate the answer template** (`answer_template.json`) alongside the prompt. Every key, enum value, numeric precision, and list ordering rule in the final answer must match the template exactly. Study `required_top_level_keys`, field types, enum choices, and sort orders before building the answer.

3. **Query the public API** for all relevant data. The API base URL is supplied externally (e.g., `<TASK_ENV_BASE_URL>`). Available endpoints are listed in `/api/manifest`. Common endpoints:
   - `/api/branches/{branch_id}` — branch details (lending capacity, policy limits, state)
   - `/api/branches/{branch_id}/metrics` — quarterly financial and delinquency metrics
   - `/api/branches/{branch_id}/loans` — loan portfolio with risk ratings, DSCR, LTV, payment status
   - `/api/branches/{branch_id}/sector-exposures` — per-sector exposure, limits, grandfathered flags
   - `/api/branches/{branch_id}/applications` — pending applications with credit metrics
   - `/api/policies` — credit policy rules (risk rating, CDFI scoring, stress formulas, concentration rules)
   - `/api/benchmarks/fdic/q4-2024` — FDIC benchmark ratios
   - `/api/benchmarks/ncua/q1-2025` — NCUA state-level benchmark data
   - `/api/credit-union-segments/{segment_id}` — credit union segment profiles

4. **Apply policy rules** from `/api/policies` to derive required values. Key rule sets:

   **Risk Rating Derivation** (`risk_rating`): The final re-derived rating is the worst (highest numeric) rating from available DSCR, LTV, and delinquency factors. DSCR and LTV thresholds map ranges to ratings; delinquency minimums assign ratings by payment status. When no factors are available, retain the current rating.

   **CDFI Factor Scores** (`cdfi_factor_scores`): Score each loan on debt-to-asset, FICO, liquidity months, and LTV using the bracketed score tables. Sum available scores to get a factor score, then classify into Prime (0–5), Desirable (6–9), Satisfactory (10–13), Watch (14–18), Doubtful (≥19), or Projected Loss (≥19 and LTV > 1.0).

   **Stress Formulas** (`stress`): The watch-list parallel shock applies `stressed_dscr = dscr / (1 + 0.18)`. The CRE dual-stress formula applies `stressed_dscr = dscr * 0.85 / (1 + 0.18)`. The coverage breach threshold is 1.0.

   **Capacity and Concentration** (`capacity_concentration`): Lending capacity comes from `branches.lending_capacity_q1`. Sector ceilings come from `branches.sector_ceiling_pct` (default) or per-sector overrides in the `sector_exposures` table. Existing over-ceiling exposure may be grandfathered, but new approvals must not worsen the breach without mitigation (participation_required, reduced_amount, or board_exception).

   **Material Downgrades** (`risk_rating.material_downgrade_notches`): A downgrade is material when the final rating exceeds the current rating by at least this number of notches.

5. **Construct the JSON answer** following the template's field rules with exact precision:
   - Currency amounts: round to 2 decimal places
   - Percentages and ratios: round to 4 decimal places
   - Basis points: round to 2 decimal places
   - Sort lists as specified (ascending by ID, rating, sector, etc.)
   - Use only allowed enum values for all categorical fields

### Common Pitfalls

- **Enum violations**: Every categorical field (decision, action, reason_code, payment_status, condition, etc.) must use exactly the values listed in the template. Check the template's enum lists before writing any value.

- **Precision drift**: Always round before building the JSON. Currency → 2 decimals, ratios → 4 decimals, basis points → 2 decimals. Use `round(value, N)` consistently.

- **Sort order**: Lists of objects must be sorted as specified (ascending loan_id, ascending final_rating, descending exposure, etc.). Sort the raw data before constructing list items.

- **Missing factors**: When policy factors (DSCR, LTV) are null for a loan, skip that factor rather than assigning a default. If no factors are available, retain the current rating.

- **Grandfathered exposure**: Sector exposures with `grandfathered: 1` are allowed to exceed the limit. New approvals in grandfathered sectors still require scrutiny.

- **Benchmark selection**: Match the benchmark version to the task context. FDIC benchmarks are used for bank branches; NCUA benchmarks are used for credit union segments.

- **Capacity allocation**: When allocating lending capacity across applications, prioritize by credit quality. Approved amounts consume capacity; declined applications do not. Only "approve" and "conditional_approve" decisions appear in priority rankings.

### Task-Type Patterns

**Rating Migration Review** (branch-level): Re-derive risk ratings for all loans meeting a rating threshold, compute rating migration, identify material downgrades (2+ notches), compare NPA to FDIC benchmarks, and flag the top problem credit. Assign watch-list actions based on final rating severity.

**Lending Allocation Package** (branch-level): Evaluate pending applications against lending capacity and sector concentration limits. Make approve/decline/conditional decisions, flag sector breaches, and summarize post-approval concentrations.

**Segment Posture Review** (credit-union segment): Compare state-level NCUA metrics against national and peer-state medians. Recommend a posture (continue/continue_with_tighter_conditions/pause), define controls and escalation triggers, and provide a committee interpretation.

**Watch-List Stress Packet** (branch-level): Isolate adversely rated loans, assign CDFI risk classes, apply the +200bp DSCR stress, queue workout actions ordered by exposure, and count severe payment-status buckets.

**Competing Credit Decision** (branch-level): Compare two applications using CRE weighted scoring, apply the dual-stress formula, assess CRE concentration against policy limits and FDIC benchmarks, select the stronger credit, and recommend conditions.
