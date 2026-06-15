---
name: credit-office-committee-packets
description: >
  Use this skill for ANY "credit office" / lending-committee packet task that pulls from the shared
  read-only HTTP API at http://127.0.0.1:8003 and asks for a structured JSON answer matching an
  answer_template.json. Triggers include: branch rating-migration / regrade reviews, Q1 lending
  allocation packages, credit-union segment posture pages, watch-list stress & workout queues,
  competing CRE decisions, NPA/FDIC or NCUA benchmark variance, concentration / sector-ceiling
  analysis, CDFI risk classes, and CRE 5-C weighted scoring. Apply this skill even when the prompt
  only names a branch_id/segment_id and an answer template — it encodes the authoritative business
  rules, API usage, rounding/ordering conventions, and the exact error corrections learned from
  graded train tasks. The single source of truth is the live API (especially GET /api/policies);
  never invent thresholds.
---

# Credit Office Committee Packets

You produce committee-ready JSON for a fictional multi-branch credit office. Every task: read a
prompt + `answer_template.json`, pull data from the **live HTTP API**, apply the **policy rules**,
and emit JSON in the exact required shape. All review/as-of dates so far are **2025-03-31**;
policy_version is `credit_policy_v2025Q1`.

The grader compares your JSON field-by-field to an official answer. Wrong rule, wrong rounding,
wrong ordering, wrong enum, or wrong population each cost points. The rules below were validated by
reproducing official train answers exactly — follow them literally and re-derive from the API, do
not hardcode any number from an example.

## Golden workflow

1. `GET /api/health` and `GET /api/manifest` to confirm the service and benchmark versions.
2. `GET /api/policies` FIRST and treat it as authoritative for every threshold, band, weight, and
   formula. Never reuse a remembered number — re-read it each task; thresholds can change.
3. Pull the entities the prompt names (branch / segment) plus everything the template references:
   detail, metrics, loans, sector-exposures, applications, and the relevant FDIC/NCUA benchmark.
4. Compute with **full precision throughout; round only the final field** to the precision the
   template states (see Rounding).
5. Emit JSON in the template's required shape: every required key, correct enums, correct ordering.
   Output JSON only — no prose, no trailing commentary.

## API quick reference

Base URL `http://127.0.0.1:8003`. `branch_id`/`segment_id` are case-insensitive. All money/ratios
are plain numbers.

- `GET /api/policies` — authoritative rules (read first, every task).
- `GET /api/branches/{id}` — `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`,
  `total_assets`, `institution_type`, `fdic_benchmark_set`.
- `GET /api/branches/{id}/metrics?quarter=YYYYQn` — returns a list of quarters; pick the right one
  (Q1 review ⇒ `2025Q1`). Has `total_loans_outstanding`, `nonperforming_loans`,
  `delinquency_30_plus_pct`, etc.
- `GET /api/branches/{id}/loans` (filters `loan_type`, `payment_status`, `min_current_rating`) —
  fields `current_rating`, `dscr`, `ltv`, `payment_status`, `outstanding_balance`, `loan_type`,
  `borrower_name`. **"exposure" = `outstanding_balance`.**
- `GET /api/branches/{id}/sector-exposures` — `sector`, `current_exposure`, `limit_pct`,
  `grandfathered`. Per-sector `limit_pct` OVERRIDES the branch default `sector_ceiling_pct`.
- `GET /api/branches/{id}/applications` — underwriting fields (`dscr`, `ltv`, `fico`, `dti`,
  `years_in_business`, `bankruptcy_months_ago`, `sba_guaranty_pct`, `requested_amount`, `sector`,
  `documentation_complete`, `total_debt`, `total_assets`, `prior_delinquencies_12m`).
- `GET /api/benchmarks/fdic/q4-2024` — `total_loans_noncurrent_pct`, `total_real_estate_30_89_pct`,
  `total_real_estate_noncurrent_pct`, `construction_development_*`.
- `GET /api/benchmarks/ncua/q1-2025?state_code=XX` — state rows for delinquency/loan_to_share/roaa/
  positive_net_income.
- `GET /api/credit-union-segments/{id}` — `minimum_checklist`, `peer_states`, `quarterly_capacity`,
  `risk_tolerance`, `internal_context` (control_issue, staffing_constraint, recent_delinquency_bps).

## Core business rules (from /api/policies — verify against the live doc each run)

**Risk rating (re-derive ratings).** Map each available factor to a rating, then the final rating is
the **worst (max numeric)** of the available factors (`dominant_factor_rule`):
- DSCR: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7.
- LTV: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7.
- Delinquency minimum by `payment_status`: Current→none, 30DPD→4, 60DPD→5, 90+DPD→7, Nonaccrual→8.
- If a loan has **no objective factor** (DSCR/LTV null AND Current), **retain its current_rating**
  (do not drop it, do not force a default).
- Material downgrade = `final − current ≥ material_downgrade_notches` (2).

**CDFI factor scoring.** Sum the banded scores for the factors present (fico, ltv, debt_to_asset,
liquidity_months); a missing factor contributes 0. Class by total: Prime 0–5, Desirable 6–9,
Satisfactory 10–13, Watch 14–18, Doubtful ≥19. **Projected Loss overrides Watch/Doubtful whenever
`ltv > 1.0` (even if the score is < 19).** This ltv>1.0 override is the single most-missed rule.

**Stress.** Watch-list +200bp: `stressed_dscr = dscr / 1.18`. CRE dual stress:
`stressed_dscr = dscr * 0.85 / 1.18`. Breach threshold = 1.0 (`stressed_dscr < 1.0` breaches; round
stressed_dscr to 2 dp for display but decide the breach on the value you report).

**CRE 5-C weighted score** (lower = better). Weights capacity 0.45, collateral_exposure 0.36,
conditions 0.11, character 0.05, capital 0.03. Class: ≤2.0 approve_quality, ≤3.0 conditional, >3.0
weak. The per-component score *scale* is NOT published — see the pitfalls note; anchor on the
relative ranking, the class cutoffs, and the decision, not on a fabricated exact component scale.

**Capacity & concentration.** Capacity = `branches.lending_capacity_q1`. New approvals may not worsen
an over-ceiling sector without an allowed mitigation (`participation_required`, `reduced_amount`,
`board_exception`). Existing over-ceiling exposure is grandfathered. **Concentration denominator =
post-approval book = `total_loans_outstanding` + sum of ALL approved/conditionally-approved amounts**
(not the bare current book). Per-sector `limit_pct` overrides the branch default.

**Derived mappings NOT in the policy doc** (validated against official answers; reuse exactly):

- `recommended_action` for an adverse/regraded loan, by severity:
  Nonaccrual → `partial_chargeoff_review`; final_rating ≥ 7 OR 90+ Days Past Due → `special_assets`;
  final_rating 5–6 (or a Current adverse loan) → `watchlist`; otherwise → `monitor`.
  The enums `workout` and `legal_referral` are NOT used by this family — do not pick them.
- Watch-list **coverage population = final_rating ≥ 6** (5 is below the line and not "covered").
- `projected_loss` boolean = `risk_class == "Projected Loss"`.

For the full worked rule tables (application decline floors, action mapping, concentration math,
segment trigger selection) read `references/rules.md`.

## Rounding & precision (a top source of lost points)

- **Compute on full-precision intermediates; round once, at the final field only.** Do NOT round a
  ratio to 4 dp and then multiply by 10000 — that drops cents of basis points.
  `variance_bps = (full_ratio − benchmark_ratio) * 10000`, rounded to the field precision. Example
  of the failure mode: 1037.49 (correct) vs 1037.0 (wrong, from a pre-rounded 0.1135 ratio); and
  2449.15 (correct) vs 2449.0 (wrong).
- Currency (USD) → 2 dp. Ratios/percentages-as-ratios → 4 dp (or whatever the template says).
  `weighted_cdfi_score` → 1 dp. bps fields → 2 dp.
- State NCUA metrics are integers reported exactly as the benchmark table gives them — do not scale.

## Ordering & enums (read the template every time)

- Default list ordering is whatever the template's `ordering` clause says. Common ones:
  ascending `loan_id`/`application_id`; ascending by `final_rating`/`current_rating`;
  workout queues "descending exposure, then ascending loan_id".
- For a secondary `payment_status` sort, sort by the **literal string** ascending. Note
  `"90+ Days Past Due"` sorts **before** `"Current"` ('9' < 'C'). Do not reorder by clinical severity.
- `enum`/`set` fields that come from a source list (e.g. a segment's `minimum_checklist`) keep the
  **source order**, not alphabetical — unless the template explicitly says "ascending".
- Boolean flag fields are booleans (`true`/`false`), not strings like `"over_limit"`. Check the
  template's declared type for every flag.
- Only ever emit values from the template's allowed enum lists.

## Common pitfalls / error reflections (from blind-vs-official diffs)

1. **Pre-rounding before a bps/variance calc.** Always carry full precision and round last.
   (Caused 1037.0 vs 1037.49 and 2449.0 vs 2449.15.)
2. **Inventing the `recommended_action` map.** It is severity-driven and uses only
   partial_chargeoff_review / special_assets / watchlist / monitor (Nonaccrual →
   partial_chargeoff_review, NOT legal_referral; Current adverse → watchlist, NOT workout).
3. **Wrong coverage cutoff.** Watch-list coverage is final_rating ≥ 6, not ≥ 5.
4. **Missing the Projected-Loss ltv>1.0 override.** A loan with ltv>1.0 is Projected Loss even when
   its CDFI score is < 19.
5. **Wrong concentration denominator.** Use the post-approval book (`total_loans_outstanding` +
   all approved amounts), not the bare current book. Using the bare book inflates ratios and
   produces false over_limit flags. Also: `post_approval_concentrations` typically lists only the
   sectors actually touched by approvals (follow the official scope the template implies, not all
   branch sectors), and `concentration_flags.flag` is a boolean.
6. **Re-sorting source-ordered sets** (checklist gates) alphabetically. Preserve source order.
7. **Including unevidenced escalation triggers.** Emit only triggers whose condition is actually
   supported by the segment's metrics/`internal_context`. A gap-based trigger like
   "state_delinquency_gap_widens_25_bps" only fires if the current gap meets the threshold (e.g.
   NC−US delinquency gap of 21 bps does NOT arm a 25-bps trigger). `trigger_id` is zero-padded
   `ET001`, `ET002`, … in ascending order.
8. **CRE component-score over-fitting.** The 5-C per-component scale isn't published. Don't claim a
   precise component score you can't derive; rank the two credits, apply the class cutoffs and the
   decision/path rules, and let the relative ordering drive the answer.
9. **Wrong CRE decision path / disposition.** When the selected CRE credit sits far over the CRE
   concentration limit, the path is `participation_required` (sector breach forces a mitigation),
   not a plain `conditional_approve`. In a *competing* CRE comparison the loser's disposition is
   `defer` (it lost the competition but is viable), not `decline`. Both credits over the CRE limit
   carry a `sector_breach` reason code; add `fdic_adverse_variance` when branch delinquency is far
   above the FDIC benchmark, and `weak_dscr` when the stressed DSCR breaches 1.0.
10. **Branch delinquency for CRE/benchmark variance.** Use the branch metric
    `delinquency_30_plus_pct` directly as `branch_delinquency_ratio` — do not recompute a bespoke
    RE-type 30–89 ratio.

## Exclusion rules

- Regrade / adverse populations are defined by the prompt's rating floor (e.g. current_rating ≥ 3,
  or ≥ 6 for "adverse"); include exactly that population and no others.
- Declined applications get `approved_amount`/`bank_capacity_used` = 0 and `conditions` = `["none"]`,
  and they are excluded from `priority_ranking` and from the concentration denominator.
- Grandfathered over-ceiling exposure is excluded from new-breach blocking (but still counts in the
  exposure base).
- A loan/applicant with no objective factor is not silently dropped — retain its current rating.
