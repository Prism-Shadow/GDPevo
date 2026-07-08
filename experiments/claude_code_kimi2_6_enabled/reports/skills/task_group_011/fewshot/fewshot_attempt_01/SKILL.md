# Credit Committee JSON Packet Generation

Generate committee-ready JSON packets by querying a shared credit-office public API and strictly following a provided answer template.

## Setup

1. Run `env/setup.sh` to initialize the environment and capture the API `base_url` printed to stdout.
2. Read `input/payloads/answer_template.json` before any data fetching to know exact required top-level keys, nested shapes, enum values, ordering rules, and numeric precision.
3. Use only the public API surfaces; do not read local environment files for business data.

## API Workflow

1. **Discover endpoints** via the manifest/root endpoint.
2. **Fetch all relevant data** before computing:
   - Target branch/segment details and metrics
   - Portfolio or pending applications
   - Policies (limits, floors, concentration caps)
   - Benchmark data (FDIC, NCUA, peer comparisons)
3. **Cross-reference** identifiers (branch_id, segment_id, application_id, loan_id) between endpoints exactly as strings.

## Output Rules

- Emit **only** the JSON object. No markdown, no narrative, no code fences.
- Include **every** required top-level key and every nested required key from the template.
- Use **exact enum values** from the template; never invent alternatives.

## Numeric Precision

| Field Type | Precision | Example |
|---|---|---|
| Currency / USD | 2 decimals | `1234567.89` |
| Percentage as ratio | 4 decimals | `0.2950` |
| Basis points (bps) | 2 decimals or integer | `2449.15` |
| DSCR / coverage ratios | 2 decimals | `1.25` |
| Scores | 1 or 2 decimals per template | `2.6`, `4.40` |
| Counts | integer | `7` |

Always use standard rounding (`round(value, N)`).

## List Ordering

Follow the template's explicit `ordering` directive. Common patterns:
- **Ascending by ID**: `application_id`, `loan_id`, `sector`, `state_code`, `trigger_id`
- **Descending by exposure, then ascending by ID**: workout queues, severity-ranked items
- **Alphabetical**: reason codes, enum lists, conditions
- **Ascending by rating, then payment status**: bucket summaries

When the template specifies a sort key, apply it before serializing.

## Enum Reference (Common Values)

- **Decisions**: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`
- **Reason codes**: `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`
- **Conditions**: `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`
- **Risk classes**: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`
- **Payment status**: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`
- **Actions**: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`
- **Monitoring cadence**: `monthly`, `quarterly`, `semiannual`

## Business Logic Patterns

- **Capacity**: `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`; sum approved amounts to compute `gross_approved_amount` and `bank_capacity_used`.
- **Concentration**: `post_approval_pct = (existing_exposure + approved_amount) / total_portfolio_or_assets`. Compare against `limit_pct`; flag when over limit.
- **Policy variance**: in basis points or percentage points: `post_approval_pct - limit_pct`.
- **Priority ranking**: include only approved and conditionally approved applications, ordered by priority (e.g., higher CDFI score first, lower risk first, or larger facility first depending on prompt).
- **DSCR stress**: apply the formula given in the prompt (e.g., `dscr * 0.85 / 1.18`), compare to `breach_threshold`, emit boolean `breaches_threshold`.
- **Decline reasons**: map each declined application to a sorted list of reason codes drawn from the enum.
- **Concentration flags**: include entries for any sector where post-approval exceeds or is near limit; sort by sector then application_id.
- **Post-approval concentrations**: one entry per sector, sorted ascending by sector.

## Common Pitfalls

1. **Wrong precision**: Do not truncate; round to the exact decimal count specified.
2. **Missing keys**: The template's `required_keys` and `item_required_keys` are mandatory even if a list is empty.
3. **Wrong sort order**: Verify whether the template wants ascending or descending.
4. **Narrative leakage**: The final output must be parseable JSON only.
5. **Stale identifiers**: Use the exact branch/segment/application IDs from the prompt, not inferred names.
6. **Empty lists vs omission**: If a template section allows empty lists, still include the key with `[]`.
