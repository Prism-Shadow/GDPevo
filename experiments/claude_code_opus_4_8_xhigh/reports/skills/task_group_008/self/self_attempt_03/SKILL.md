---
name: private-wealth-advisory-planning
description: >
  Solve private wealth advisory structured-output tasks (Roth conversion / RMD tax,
  ILIT Crummey funding, GRAT vs CRAT comparison, and integrated estate-liquidity
  action plans) by querying a read-only advisory HTTP API, resolving conflicting
  source documents by priority, applying the derived business formulas, and emitting
  a single JSON object that conforms to the task's answer_template.json.
  Use this whenever a task asks for a structured planning output for a client
  CLT-#### in the private-wealth domain.
---

# Private Wealth Advisory Planning Skill

You are given, per task: `input/prompt.txt`, `input/payloads/request_memo.md`, and
`input/payloads/answer_template.json`. The prompt names a client (e.g. `CLT-1003`)
and an engagement type. The memo gives engagement context and sometimes an explicit
**planning horizon year**. The answer_template lists the required top-level keys,
the exact field names, the enum value sets, and rounding/date conventions.

Your job: fetch the client's data from the remote API, run the correct analysis,
and return ONE JSON object (no prose) matching the template.

---

## 0. Output discipline (always)

- Return a **single JSON object only**, no prose, no markdown fences.
- Include `task_id` (e.g. `train_003` / `test_003` — derive from the task folder
  name; use the same numeric suffix the harness used) and `client_id` (e.g.
  `CLT-1003`, exactly as given).
- Set `analysis_type` to the single enum the template fixes for that task
  (`roth_conversion_rmd`, `ilit_crummey_implementation`, `trust_comparison`,
  `estate_liquidity_action_plan`).
- **All USD amounts rounded to 2 decimals (cents).** Emit JSON numbers, not strings.
- **All dates ISO `YYYY-MM-DD` strings.**
- Build the object from the template's `required_top_level_keys` and `fields`
  list — produce every key it names, nested exactly as the dotted paths imply
  (e.g. `recommendation.primary_action` → `{"recommendation":{"primary_action":...}}`).
- Only use enum string values that appear in the template for that field. Never
  invent new enum strings.
- Where a field is `list ... sorted alphabetically`, sort the final list with a
  plain ascending string sort.

---

## 1. API usage (read-only, curl via Bash)

Base URL comes from the environment (the harness exposes it; the file
`environment_access.md` gives it explicitly, e.g. `<remote-env-url>`).
All endpoints are GET and return JSON. Use `curl -s --max-time 30`.

| Endpoint | Use |
|---|---|
| `GET /api/health` | liveness check (optional first call) |
| `GET /api/clients/<client_id>` | base client record (age, filing_status, planning_year, estate_value, liquid_assets, marital_status) |
| `GET /api/source-documents?client_id=<id>` | list of conflicting documents; each has `source_type`, `effective_date`, `facts{}` |
| `GET /api/retirement-accounts?client_id=<id>` | IRA export: `traditional_balance`, `roth_balance`, `expected_return`, `rmd_start_age`, `recommended_conversion_years`; `source_type` = `CUSTODIAN_EXPORT` |
| `GET /api/life-insurance?client_id=<id>` | policy: `death_benefit`, `annual_premium`, `planned_contribution_date`, `is_existing_policy_transfer`, `proposed_owner` |
| `GET /api/trust-candidates?client_id=<id>` | `asset_value`, `expected_growth_rate`, `grat_term_years`, `grat_annuity_rate`, `crat_term_years`, `crat_payout_rate` |
| `GET /api/policies/tax` | constants (see below) |
| `GET /api/rmd-factors` | map `age -> divisor` (age 73..99) |

**Always fetch:** the client record, the source-documents, the tax policy, and
the endpoint(s) relevant to the analysis. For any task touching estate tax you
also need `/api/policies/tax`. For RMD you need `/api/rmd-factors`.

Run helper math with `python` (NOT `python3`).

### Tax policy constants (shape observed)

```
annual_gift_exclusion: {"2025":19000, "2026":20000}   # per beneficiary, by year
estate_tax_exemption:  {"2025":13990000, "2026":13610000}  # by year
estate_tax_rate:       0.40
conversion_bracket_targets: {"MFJ":394600, "SINGLE":197300, "HOH":263500}  # top of target bracket
max_crat_term_years:   20
charitable_deduction_rate: 0.35
```

Pick exemption / gift-exclusion **by the client's `planning_year`** (usually 2026).
Pick the bracket target by the client's `filing_status`.

---

## 2. Source-document conflict resolution (applies to EVERY task)

Each client has three source documents that **disagree**. Resolve by source-type
priority, which also matches recency:

**Priority (highest → lowest):**
`SIGNED_PROFILE` (newest, e.g. 2026-02-06) **>** `ATTORNEY_MEMO` (e.g. 2026-01-18)
**>** `CRM_NOTE` (oldest, e.g. 2025-11-20, this is the "stale" import).

Rules:
- For **profile / goal / beneficiary / income** fields (`beneficiary_count`,
  `marginal_tax_rate`, `annual_non_ira_income`, `family_transfer_priority`,
  `philanthropic_intent`, `filing_status`, `liquid_assets`, `estate_value`,
  `age`, `planning_year`): **use `SIGNED_PROFILE`.** The base client record
  matches the SIGNED_PROFILE for overlapping fields, so they corroborate.
  → `source_resolution.controlling_profile_source = SIGNED_PROFILE`
  → `source_resolution.controlling_goal_source = SIGNED_PROFILE`
  → `source_resolution.controlling_beneficiary_source = SIGNED_PROFILE`
- For **retirement-account numbers** (balances, return, rmd_start_age,
  recommended_conversion_years): the only/authoritative source is the custodian
  export. → `source_resolution.controlling_account_source = CUSTODIAN_EXPORT`.
- For **life-insurance / policy numbers** (death_benefit, premium, dates):
  authoritative source is the policy/custodian record.
  → `source_resolution.controlling_policy_source = CUSTODIAN_EXPORT`.
- For **asset/estate figures in trust comparison** (`controlling_asset_source`):
  the `ATTORNEY_MEMO` is the controlling authority for estate/asset values in a
  trust-planning context (it carries `estate_value` and is the legal-planning
  document). → `source_resolution.controlling_asset_source = ATTORNEY_MEMO`.

General tiebreak if you ever see a new field: prefer the document whose
`source_type` is highest priority above; among same type, prefer the latest
`effective_date`. The enum value sets for each `controlling_*` field are fixed by
the template — pick from that list only. `STALE_MARKETING_INTAKE` corresponds to
a stale CRM-type import and is essentially never the controlling source.

---

## 3. Analysis: `roth_conversion_rmd` (e.g. Mercer, Patel)

Inputs: SIGNED_PROFILE (`annual_non_ira_income`, `marginal_tax_rate`,
`filing_status`), retirement account (`traditional_balance`, `roth_balance`,
`expected_return` = ret, `rmd_start_age`, `recommended_conversion_years`), RMD
factors, tax policy (`conversion_bracket_targets`), and the **horizon year** from
the memo.

Derived quantities:

- `first_conversion_year = planning_year` (conversions start now).
- `first_rmd_year = planning_year + (rmd_start_age - age)`.
- `conversion_window = max(0, first_rmd_year - first_conversion_year)` (years
  before RMDs begin).
- `bracket_headroom = conversion_bracket_targets[filing_status] - annual_non_ira_income`.
- `annual_conversion_amount = min(bracket_headroom, traditional_balance / recommended_conversion_years)`
  — stage conversions to stay within the target bracket.
- `conversion_years` = `recommended_conversion_years` (the planned count).
- `conversion_years_positive = min(recommended_conversion_years, conversion_window)`
  — the years actually executed before RMDs start. (For a near-RMD client this is
  small or 0; for a client years away from RMD it equals the planned count.)
- `horizon_year` = the memo's horizon; `first_rmd_year` as above.

Two-scenario projection from `planning_year` through `horizon_year` inclusive
(simulate year by year; keep the order consistent in both scenarios):

For each year, in this order:
1. **Conversion** (conversion scenario only), if the year is within the
   `conversion_years_positive` window starting at `first_conversion_year`:
   move `amt = min(annual_conversion_amount, traditional_balance)` from
   traditional to Roth; accumulate `total_converted += amt` and
   `total_conversion_tax += amt * marginal_tax_rate` (tax paid from outside funds).
2. **RMD**, if `age >= rmd_start_age`: `rmd = traditional_balance / rmd_factor[age]`;
   accumulate `rmd_tax += rmd * marginal_tax_rate`; subtract `rmd` from traditional.
3. **Growth**: multiply both traditional and Roth balances by `(1 + ret)`.

Run the loop once with conversions off (baseline) and once on (conversion):
- `rmd_projection.baseline_rmd_tax_through_horizon` = baseline rmd_tax total.
- `rmd_projection.conversion_rmd_tax_through_horizon` = conversion rmd_tax total.
- `rmd_projection.rmd_tax_savings_through_horizon` = baseline − conversion.
- `conversion_plan.total_converted`, `conversion_plan.total_conversion_tax` from
  the conversion run.
- `legacy_projection.projected_roth_balance_horizon` = ending Roth (conversion run).
- `legacy_projection.projected_traditional_balance_horizon` = ending traditional
  (conversion run).

(Modeling note: the exact intra-year ordering and whether growth precedes RMD is a
judgement call; pick one convention and apply it identically to both scenarios so
the *savings difference* is consistent. The simulation above — convert, then RMD,
then grow — is internally consistent and recommended.)

Enums:
- `recommendation.primary_action`: `STAGED_ROTH_CONVERSION` when there is a usable
  conversion window (`conversion_years_positive >= 1`) with positive savings;
  `DEFER` when the window is effectively gone but a later look is warranted;
  `NO_CONVERSION` when conversion adds no value.
- `recommendation.suitability`: `SUITABLE` when the window is healthy (multiple
  positive years and meaningful savings); `BORDERLINE` when only 1 positive year /
  thin savings; `DEFER` when no window.
- `recommendation.risk_flag`: `RMD_NEAR_TERM` when `conversion_window <= 1` /
  client at or just under `rmd_start_age`; `LIQUIDITY_CONSTRAINT` when
  `total_conversion_tax` is large relative to `liquid_assets`;
  `TAX_BRACKET_MANAGEMENT` otherwise (ample headroom, staging is the main lever).
- `legacy_projection.heir_tax_profile` from Roth share of horizon balances
  `f = roth/(roth+traditional)`: `MOSTLY_TAX_FREE` if `f >= ~0.66`,
  `MIXED_TAXABLE_AND_TAX_FREE` if `~0.34 <= f < ~0.66`, `MOSTLY_TAXABLE` if
  `f < ~0.34`.

---

## 4. Analysis: `ilit_crummey_implementation` (e.g. Keating)

Inputs: SIGNED_PROFILE `beneficiary_count`; life-insurance policy
(`annual_premium`, `death_benefit`, `planned_contribution_date`,
`is_existing_policy_transfer`); tax policy (`annual_gift_exclusion[planning_year]`,
exemption, rate).

- `annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]` (e.g.
  $20,000 in 2026).
- `beneficiary_count` from SIGNED_PROFILE.
- `annual_exclusion_capacity = exclusion_per_beneficiary * beneficiary_count`.
- `annual_premium` from the policy.
- `premium_gap = max(0, annual_premium - annual_exclusion_capacity)` — the
  shortfall not covered by annual-exclusion gifts. (If capacity ≥ premium, gap = 0
  and there is no shortfall.)
- `administration.notices_required = beneficiary_count` (one Crummey notice each).
- `administration.dedicated_bank_account_required = true` (an ILIT should pay
  premiums from its own account after the withdrawal window).

Dates (ISO):
- `administration.contribution_date = planned_contribution_date`.
- `administration.notice_due_date` = the contribution date (notices go out
  promptly upon contribution; same day is the defensible due date).
- `administration.withdrawal_window_end = contribution_date + 30 days` (standard
  Crummey withdrawal window).
- `administration.earliest_premium_payment_date = withdrawal_window_end` (pay the
  premium only after the withdrawal window closes).

Estate result:
- `estate_result.death_benefit = death_benefit`.
- `estate_result.projected_outside_estate_if_implemented = death_benefit` for a
  **new** policy (`is_existing_policy_transfer == false`); for a transfer of an
  existing policy still inside the 3-year lookback, treat the proceeds as not yet
  reliably outside the estate (→ 0 or flag the lookback).
- `estate_result.tax_liquidity_support = min(death_benefit, estate_tax_exposure)`
  where `estate_tax_exposure = max(0, estate_value - exemption[planning_year]) * estate_tax_rate`.

Risk flag (`recommendation.risk_flag` and `estate_result.estate_inclusion_risk`,
same enum):
- new policy + no shortfall → `LOW_IF_FORMALITIES_MET`
- new policy + `premium_gap > 0` → `EXCLUSION_SHORTFALL`
- existing-policy transfer + no shortfall → `THREE_YEAR_LOOKBACK`
- existing-policy transfer + `premium_gap > 0` → `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL`

Recommendation `primary_action`:
- no shortfall, new policy → `FUND_WITH_CRUMMEY_NOTICES`
- shortfall, new policy → `USE_LIFETIME_EXEMPTION_FOR_SHORTFALL`
- existing-policy transfer (lookback) → `USE_NEW_POLICY_OR_ACCEPT_LOOKBACK`
  (or `DISCLOSE_LOOKBACK_AND_USE_EXEMPTION` when there is ALSO a shortfall).

`recommendation.suitability`: `SUITABLE_WITH_ADMINISTRATION` when formalities (notices,
dedicated account, window) cleanly cover the premium; `BORDERLINE` with a modest
shortfall; `NOT_SUITABLE` only in severe lookback+shortfall cases.

---

## 5. Analysis: `trust_comparison` — GRAT vs CRAT (e.g. Alvarez)

Inputs: trust-candidate params; tax policy (`estate_tax_rate`,
`charitable_deduction_rate`, `max_crat_term_years`); SIGNED_PROFILE goal fields
(`family_transfer_priority`, `philanthropic_intent`); exemption + estate_value.

Estate context:
- `estate_context.taxable_estate = max(0, estate_value - exemption[planning_year])`.
- `estate_context.estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `estate_context.liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

GRAT (term = `grat_term_years`, annuity rate = `grat_annuity_rate`, growth =
`expected_growth_rate`):
- `annuity = asset_value * grat_annuity_rate` (level annuity each year).
- `fv_asset = asset_value * (1 + growth) ** term`.
- `fv_annuity = sum over t=1..term of annuity * (1 + growth) ** (term - t)`
  (annuity payments reinvested/grown at the growth rate to end of term).
- `grat.projected_remainder_to_heirs = fv_asset - fv_annuity`.
- `grat.estimated_estate_tax_reduction = projected_remainder_to_heirs * estate_tax_rate`
  (value moved out of the taxable estate × rate).
- `grat.mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED` (fixed enum: grantor
  must outlive the term).
- `grat.term_years = grat_term_years`.

CRAT (term = `crat_term_years`, capped at `max_crat_term_years`=20; payout =
`crat_payout_rate`):
- `crat.term_years = min(crat_term_years, max_crat_term_years)`.
- `payout = asset_value * crat_payout_rate`.
- `fv_asset = asset_value * (1 + growth) ** term`.
- `fv_payout = sum over t=1..term of payout * (1 + growth) ** (term - t)`.
- `crat.projected_charitable_remainder = fv_asset - fv_payout`.
- `crat.estimated_income_tax_deduction = asset_value * charitable_deduction_rate`
  (charitable deduction approximated as the funded value × deduction rate).
- `crat.family_transfer_fit`: `LOW` (a CRAT sends the remainder to charity, not
  family) — use `LOW` unless the goal data clearly elevates family use of the CRAT.

Recommendation (goal-driven; goal source = SIGNED_PROFILE):
- `family_transfer_priority == high` and `philanthropic_intent != high`
  → `preferred_strategy = GRAT`, `rationale_code = CHILDREN_TRANSFER_PRIORITY`,
  `alternate_role = SECONDARY_CHARITABLE_TOOL`.
- `philanthropic_intent == high` (and family not higher)
  → `preferred_strategy = CRAT`, `rationale_code = PHILANTHROPIC_PRIORITY`,
  `alternate_role = SECONDARY_FAMILY_TRANSFER_TOOL`.
- Otherwise default to the family-transfer (GRAT) branch, since these clients are
  large taxable estates whose primary motive is moving appreciation to heirs.

---

## 6. Analysis: `estate_liquidity_action_plan` — integrated (e.g. Chen)

Combines the ILIT and trust-transfer analyses into a coordinated plan. Reuse §4
and §5 computations.

Estate context (same formulas as §5):
- `taxable_estate = max(0, estate_value - exemption[planning_year])`.
- `estate_tax_exposure = taxable_estate * estate_tax_rate`.
- `liquidity_gap_before_planning = max(0, estate_tax_exposure - liquid_assets)`.

`ilit` block:
- `annual_exclusion_capacity`, `premium_gap` as in §4.
- `estate_inclusion_risk` as in §4 (new policy + no shortfall →
  `LOW_IF_FORMALITIES_MET`, etc.).
- `projected_outside_estate_if_implemented = death_benefit` for a new policy.

`trust_transfer` block (pick GRAT vs CRAT by goal as in §5):
- `preferred_strategy`, `projected_remainder_to_heirs` (GRAT remainder),
  `estimated_estate_tax_reduction` (GRAT reduction),
  `projected_charitable_remainder` (CRAT remainder). Provide all of these so the
  attorney sees both branches.

`recommendation`:
- `primary_action`: `COMBINE_ILIT_AND_GRAT` when family-transfer priority is high
  and the estate needs both liquidity (ILIT) and transfer (GRAT);
  `CRAT_WITH_LIQUIDITY_REVIEW` when philanthropic priority dominates;
  `ILIT_WITH_EXEMPTION_REVIEW` when the ILIT premium creates an exclusion shortfall
  needing lifetime-exemption allocation.
- `sequencing`: `ILIT_FIRST_THEN_GRAT` for the combine case;
  `TRUST_DECISION_FIRST` when the trust choice (GRAT vs CRAT) is unresolved;
  `ILIT_FIRST_THEN_ATTORNEY_REVIEW` when documents must be drafted before the trust.
- `risk_flag`: the ILIT estate-inclusion risk flag (§4 enum).

`action_set` — a list of enums **sorted alphabetically ascending**, drawn only
from: `ATTORNEY_DRAFT_REVIEW`, `CRAT_FOR_CHARITABLE_REMAINDER`,
`GRAT_FOR_APPRECIATING_SHARES`, `ILIT_CRUMMEY_NOTICE_CYCLE`,
`LIFETIME_EXEMPTION_ALLOCATION`. Build it by including:
- `ILIT_CRUMMEY_NOTICE_CYCLE` whenever an ILIT/policy is in play.
- `GRAT_FOR_APPRECIATING_SHARES` when preferred trust = GRAT (family priority),
  else `CRAT_FOR_CHARITABLE_REMAINDER` when preferred = CRAT (philanthropic).
- `LIFETIME_EXEMPTION_ALLOCATION` when `premium_gap > 0` (shortfall) or the estate
  needs exemption allocation.
- `ATTORNEY_DRAFT_REVIEW` essentially always (these need legal drafting).
Then `sorted(set(actions))`.

---

## 7. Common pitfalls / checklist

- **Do not** read the client record's possibly-stale fields directly when a
  SIGNED_PROFILE fact disagrees — SIGNED_PROFILE wins. (In practice the client
  record already matches SIGNED_PROFILE, but always cross-check the documents.)
- **Beneficiary count drives** Crummey notices and exclusion capacity — take it
  from SIGNED_PROFILE (CRM count is usually different and stale).
- **Bracket target is per filing_status**; use SINGLE vs MFJ vs HOH correctly.
- **Exemption / gift exclusion are per planning_year** — read the right year key.
- **CRAT term is capped** at `max_crat_term_years` (20).
- **premium_gap / liquidity_gap are non-negative** (`max(0, …)`): a "gap"/"shortfall"
  of zero means fully covered; never report a negative gap.
- **estate_tax_exposure uses `estate_value - exemption`, then × 0.40** — not the
  full estate value.
- **Roth two-scenario consistency**: apply the identical intra-year ordering in
  baseline and conversion runs; savings = baseline − conversion must be ≥ 0.
- **conversion_years_positive ≤ conversion_window**: a near-RMD client gets few or
  zero positive conversion years; reflect that in suitability/risk enums.
- **Rounding**: round every USD figure to 2 decimals at output time (not midway,
  to avoid compounding rounding error).
- **Dates**: emit ISO `YYYY-MM-DD`; compute the 30-day Crummey window by real date
  arithmetic (use python `datetime.date` + `timedelta(days=30)`).
- **Enums**: copy enum spellings verbatim from the template; any typo fails.
- **task_id**: match the harness's numbering (`train_00X` for train, `test_00X`
  for test) using the numeric suffix of the task.

## 8. Quick procedure

1. Read prompt, memo (note horizon year if any), and answer_template (note required
   keys, enums, `analysis_type`).
2. `curl` health, `/clients/<id>`, `/source-documents?client_id=<id>`,
   `/policies/tax`, plus the analysis-specific endpoint(s) and `/rmd-factors` if
   Roth.
3. Resolve conflicts via §2 (SIGNED_PROFILE > ATTORNEY_MEMO > CRM_NOTE; accounts =
   CUSTODIAN_EXPORT; assets in trust comparison = ATTORNEY_MEMO).
4. Run the matching analysis (§3–§6) in a `python` helper; keep formulas
   internally consistent and self-check sign/order.
5. Assemble the JSON per the template, set `source_resolution.*` enums, round USD,
   ISO dates, sort any list fields.
6. Output the single JSON object only.
