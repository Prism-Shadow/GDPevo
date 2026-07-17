# Credit Office Committee JSON Skill

Use this skill for credit-office evaluation tasks that ask for a committee-ready JSON answer from the public credit office API. The highest-risk failure mode is a structurally plausible answer that does not match the requested template. Treat the template, enum strings, and identifier spelling as controlling whenever they are present.

## Core Workflow

1. Read the prompt and any provided answer template before calculating. Preserve the template's top-level keys, nested object names, enum values, reason-code identifiers, owner identifiers, and required ordering.
2. Use only public API surfaces named in the prompt or manifest. Fetch the policy endpoint for calculation rules and the relevant benchmark endpoint before making recommendations.
3. Filter the population exactly as stated. Phrases such as "rated 3 or worse" and "rating 6 or worse" mean numeric ratings greater than or equal to that cutoff.
4. Keep calculations and presentation separate: first derive objective values, then map them into the template's allowed decision, posture, class, action, and reason-code fields.
5. Return one valid JSON object only. Do not add explanatory text outside JSON, and do not invent enum strings when the template gives a controlled vocabulary.

## Risk Rating Regrades

- Convert each available objective factor into its policy rating, then use the worst numeric rating among available DSCR, LTV/collateral, and delinquency factors.
- For DSCR thresholds, use the policy order exactly: stronger DSCR maps to lower numeric risk; DSCR below the lowest threshold maps to the weakest listed rating.
- For LTV thresholds, use the policy order exactly: lower LTV maps to lower numeric risk; LTV above the highest threshold maps to the weakest listed rating.
- Delinquency minimums are numeric floors. Nonaccrual should dominate when the policy maps it to the worst rating.
- If a loan lacks all objective regrade factors, do not manufacture a rating from unrelated fields. Retain the current rating unless the template explicitly allows a null factor-only result.
- A material downgrade is a numeric worsening of at least the policy's `material_downgrade_notches`. Count only positive worsening, not upgrades or unchanged ratings.
- For NPA benchmark variance, use `nonperforming_loans / total_loans_outstanding` and compare it with the matching FDIC noncurrent-loan benchmark. Report both decimal ratios and percentage-point variance if the template has room.

## Watch-List And CDFI Scoring

- For adversely rated watch-list tasks, build the population from the prompt's cutoff before scoring.
- CDFI factor scores come from the policy tables for debt-to-asset, FICO, liquidity months, and LTV. Sum only factors with available values unless the template explicitly says to penalize missing data.
- Apply CDFI class breakpoints after summing: Prime `0-5`, Desirable `6-9`, Satisfactory `10-13`, Watch `14-18`, Doubtful `>=19`; Projected Loss requires the score condition plus the policy's LTV condition.
- Keep payment status, nonaccrual, days past due, and internal workout severity separate from the CDFI class unless the template provides an override field.
- For watch-list DSCR stress, use the policy formula `stressed_dscr = dscr / (1 + 0.18)`. Mark coverage breaches when stressed DSCR is below the policy threshold, commonly `1.0`.
- For CRE dual stress, use `stressed_dscr = dscr * 0.85 / (1 + 0.18)`. This is distinct from the watch-list-only formula.

## Allocation And Concentration

- `lending_capacity_q1` caps retained approvals for branch allocation packages. Sum approved or retained amounts, not requested amounts for declined or participated portions.
- Sector limits come from the sector exposure table when present; otherwise use the branch default sector ceiling. CRE policy limits are separate from single-sector limits.
- Post-approval sector exposure is current exposure plus the retained approved amount for that sector. If a sector is already over ceiling, new exposure should use an allowed mitigation such as reduced amount, participation, or board exception, or be declined.
- For a post-approval view, calculate exposure percentages consistently with the template's denominator. If the template is silent, include current exposure amount, approved addition, post exposure amount, limit percent, and over-limit flag.
- Decline reason codes should describe the binding reasons only: capacity, sector concentration, missing documentation, credit weakness, stress breach, recent bankruptcy, delinquency, high leverage, or weak guarantor support as allowed by the template.

## CRE Comparison

- Use the policy CRE weights without reversing them: capacity is usually the largest component, collateral exposure next, then conditions, character, and capital.
- Build component scores from the natural credit drivers unless a template-specific rubric is supplied: DSCR for capacity, debt-to-asset for capital, guarantor/relationship/delinquency for character, LTV for collateral exposure, and sector/benchmark/concentration for conditions.
- Lower weighted CRE scores are stronger. Apply the policy class thresholds after calculating the weighted score.
- A stronger CRE request can still need a mitigated path when branch CRE exposure, sector exposure, or FDIC benchmark underperformance is elevated.
- When comparing two requests, the selected credit should have the better combined profile across weighted score, stressed DSCR, LTV/collateral, sponsor support, relationship depth, and concentration impact. The unselected credit still needs template-valid reason-code treatment.

## Credit-Union Segment Posture

- Use the credit-union segment endpoint plus the NCUA benchmark table, not bank-branch FDIC data.
- Compare the target state with the national row and each named peer state from the segment record. Preserve the peer-state identifiers exactly.
- A controlled posture is appropriate when capacity remains available but state or internal delinquency, control issues, or staffing constraints argue against unrestricted growth.
- Operating controls should start with the segment's minimum checklist and add controls that directly address internal issues, such as pre-close insurance proof, lien/UCC/title confirmation, public contract or tax-support verification, and senior-underwriter review.
- Escalation triggers should have concrete owners and measurable events: missing required checklist items, delinquency thresholds, capacity exceptions, insurance/lien exceptions, or benchmark deterioration.

## Output Discipline

- Prefer exact IDs from source records: branch IDs, segment IDs, loan IDs, application IDs, state codes, benchmark versions, policy versions, and sector names.
- Round only at the presentation edge. Keep internal ratios precise, and output decimals versus percentages according to the template labels.
- Do not let narrative phrasing replace structured fields. If a concise interpretation is required, keep it short and tie it to objective metrics and controls.
- When uncertain between a good calculation and a template enum, choose the template enum and place supporting detail in a permitted notes, rationale, or evidence field.
