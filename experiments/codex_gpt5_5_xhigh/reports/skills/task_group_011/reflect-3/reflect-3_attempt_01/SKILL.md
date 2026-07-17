# Credit Office Committee JSON Skill

Use this skill for Credit Office tasks that ask for committee-ready JSON using public branch, loan, application, policy, benchmark, sector-exposure, or credit-union segment data.

## Core Workflow

1. Read the prompt target IDs, review/as-of date, and required JSON shape. If an `answer_template.json` is present in the task input, follow its field names, enum values, and identifiers exactly.
2. Use only the public API surfaces named by the task/environment. Pull the entity record, latest relevant metrics, policies, relevant loans/applications/exposures, and the named benchmark set.
3. Work from the latest quarter unless the prompt names a different period. Preserve requested ordering for applications and use stable IDs exactly as returned by the API.
4. Return one valid JSON object only. Do not add prose outside JSON. Prefer explicit numeric fields over narrative-only conclusions.

## Risk Rating Regrades

- Numeric ratings worsen as the number increases.
- For re-derived loan ratings, apply the policy dominant-factor rule: calculate available DSCR rating, LTV/collateral rating, and delinquency minimum, then use the worst numeric rating among the available factors.
- Do not invent scores for missing DSCR, LTV, collateral, or delinquency factors. If no objective factor is available, flag the loan as insufficient-data or retain/mark current only if the template requires a rating.
- A material downgrade is `rederived_rating - current_rating >= material_downgrade_notches`.
- Count migration categories from objective rederived ratings: downgrades, material downgrades, upgrades, unchanged, and reviewed population.
- For NPA variance, use `nonperforming_loans / total_loans_outstanding` from the latest metrics and compare it to the named FDIC noncurrent benchmark. Report ratio plus percentage-point/basis-point variance when useful.

## Stress And Watch Lists

- Watch-list +200 bp DSCR stress: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Treat a stressed DSCR below the policy coverage threshold as a breach. If DSCR is missing, leave the stressed value null and do not count it as stress-tested.
- For adversely rated populations, use the prompt cutoff exactly, such as current rating `>= 6`.
- Summarize payment status counts by severe rating bucket when requested, for example rating 6, 7, and 8 buckets.

## CDFI-Style Classes

- Score only objective factors available in the loan/application record using the policy CDFI tables: debt-to-asset, FICO, liquidity months, and LTV.
- Sum the factor scores, then classify using the policy class ranges:
  - `Prime`: 0-5
  - `Desirable`: 6-9
  - `Satisfactory`: 10-13
  - `Watch`: 14-18
  - `Doubtful`: >=19
  - `Projected Loss`: >=19 and LTV > 1.0
- If narrative notes indicate loss concern but the factor score does not meet `Projected Loss`, keep the calculated class and queue the loss review as a workout action.

## Allocation And Concentration

- For lending allocation packages, total retained approvals must not exceed `lending_capacity_q1`.
- For sector concentration, use the branch sector-exposure override table when a sector is listed; otherwise use the branch default sector ceiling.
- For post-approval concentration views, compare `(current_exposure + retained_approved_amount)` against the portfolio denominator used by branch metrics, typically latest `total_loans_outstanding + retained_approved_amounts`. Use `lending_capacity_q1` for allocation capacity dollars, not as the sector exposure denominator unless the prompt/template says so.
- Existing over-ceiling exposure may be grandfathered, but a new approval should not worsen that sector or CRE concentration without an allowed mitigation: `participation_required`, `reduced_amount`, or `board_exception`.
- When a selected credit is strong but the branch/sector concentration is already elevated, recommend a mitigated path rather than a clean approval.

## CRE Comparisons

- Apply the policy CRE weighted-score framework with lower scores better:
  - capacity: DSCR and stressed DSCR
  - capital: debt-to-asset/leverage
  - character: delinquencies, relationship depth, guarantor strength
  - collateral_exposure: LTV and collateral support
  - conditions: branch CRE exposure, sector exposure, and benchmark pressure
- Use the policy weights exactly: capacity 0.45, capital 0.03, character 0.05, collateral exposure 0.36, conditions 0.11.
- Classify the weighted result using policy thresholds: `approve_quality` at or below 2.0, `conditional` at or below 3.0, and `weak` above 3.0.
- Prefer the credit that combines stronger weighted score, stress pass, lower LTV/leverage, stronger guarantor/relationship support, and less concentration pressure.
- For the unselected credit, provide reason codes tied to the template enums: stress breach, concentration, high leverage, weak sponsor/guarantor, weaker score, or documentation weakness as applicable.

## Credit-Union Segment Posture

- Pull the target segment, NCUA benchmark set, and policies. Compare the target state to the US row and every peer state named in the segment record.
- Keep benchmark units straight: NCUA delinquency and ROAA are in bps; loan-to-share and positive-net-income fields are percentages.
- Use the segment `minimum_checklist` identifiers verbatim for operating controls.
- Recommend a controlled posture when capacity exists but target/internal delinquency is above national or peer levels, staffing is constrained, or closing controls have failed.
- Escalation triggers should have concrete thresholds and owners, such as delinquency bps, capacity utilization, missing required checklist items, or unresolved staffing constraints. Use template owner IDs if supplied.

## Output Conventions

- Preserve exact API IDs and template enum spelling/casing.
- Do not invent enum labels. If the template provides enums, choose only from them; if not, use clear, stable strings and include the underlying facts.
- Round dollars to two decimals, ratios to 4-6 decimals, percentages to two decimals, and bps to whole numbers unless the template demands another precision.
- Include both the selected conclusion and the supporting calculation fields so the committee can audit the answer from the JSON alone.
