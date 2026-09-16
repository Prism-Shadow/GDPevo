# Committee Escalation Memo Reference

Use this reference when the prompt asks for an **M&A Committee escalation package** comparing draft terms against policy thresholds with benchmark support.

## Data Sources

1. `/api/deals/<id>` — headline value, signing date, parties
2. `/api/deals/<id>/terms` — all draft terms
3. `/api/policies/<policy_id>/thresholds` — committee policy thresholds
4. `/api/deals/<id>/benchmarks` — market data with sample_size, median, upper_quartile
5. `/api/deals/<id>/risk-estimates` — quantified exposure estimates
6. `/api/deals/<id>/notes` — negotiation history

## Filtering Logic

The task asks for **only out-of-policy or restricted-for-approval terms**. Exclude:

- Terms whose draft values fall within policy thresholds.
- Stale terms not part of the current draft.
- Terms not on the committee's approval scope (non-committee distractor terms).

Compare each draft term against its policy threshold. A term is escalated when:

- A numeric draft value exceeds a policy cap.
- A draft provision removes a required trigger (e.g., intervening event in fiduciary out).
- A draft adds restricted carveouts beyond the approved list.

## Escalation Term Structure

For each escalated term:

- **term_id**: stable ID from the terms endpoint.
- **category**: `reverse_termination_fee`, `fiduciary_out`, `rw_survival`, or `mae_carveouts` (template enum).
- **clause_ref**: article or section reference from the term.
- **issue_status**: `out_of_policy`.
- **risk_rating**: HIGH when the delta is large or a fundamental trigger is missing; MEDIUM for smaller deviations.

### draft_metric vs. policy_metric

**For percent-point terms (reverse termination fees):**

- `draft_metric.value` = draft percentage
- `draft_metric.unit` = `"percent_points"`
- `draft_metric.basis` = `"equity value"`
- `draft_metric.amount` = `round(headline_value * draft_metric.value / 100)`
- `policy_metric.threshold_value` = policy cap percentage
- `policy_metric.threshold_amount` = `round(headline_value * policy_metric.threshold_value / 100)`
- `delta.percent_points` = `draft_metric.value - policy_metric.threshold_value`
- `delta.amount` = `draft_metric.amount - policy_metric.threshold_amount`

**For fiduciary-out (binary/trigger terms):**

- `draft_metric.value` = `1` (counting the restricted change)
- `draft_metric.unit` = `"restricted_change"`
- `draft_metric.missing_intervening_event_trigger` = `true/false`
- `draft_metric.match_right_business_days` = days from draft
- `policy_metric.required_triggers` = `["superior_proposal", "intervening_event"]`
- `delta.removed_triggers` = triggers present in policy but missing in draft

**For survival terms (month-based):**

- `draft_metric.value` = max survival months
- `draft_metric.unit` = `"months"`
- `draft_metric.fundamental_months` = fundamental rep survival
- `draft_metric.general_months` = general rep survival
- `draft_metric.max_survival_months` = `max(fundamental_months, general_months)`
- `policy_metric.threshold_value` = policy max months
- `delta.fundamental_months` = `draft_metric.fundamental_months - policy_metric.threshold_value`
- `delta.general_months` = `draft_metric.general_months - policy_metric.threshold_value`

**For MAE carveouts:**

- `draft_metric.value` = count of added carveouts
- `draft_metric.unit` = `"additional_carveouts"`
- `draft_metric.added_count` = count of restricted carveouts
- `draft_metric.restricted_carveouts` = list of carveout IDs
- `policy_metric.threshold_value` = max approved carveouts
- `policy_metric.approved_carveout_groups` = approved list
- `delta.excess_count` = `draft_metric.added_count - policy_metric.threshold_value`

## Benchmark Integration

Pull from `/api/deals/<id>/benchmarks`. Match the benchmark metric to the term category. Populate:

- **metric**: the benchmark metric name.
- **sample_size**: from the benchmark record.
- **median / upper_quartile**: from the benchmark record.
- **position**: compare the draft value to median and upper quartile:
  - `at_or_below_median`
  - `between_median_and_upper_quartile`
  - `at_upper_quartile`
  - `above_upper_quartile`
  - `not_applicable` when no benchmark exists for this category.

## Exposure

Pull from risk estimates (`/api/deals/<id>/risk-estimates`). Match estimates by category:

- **type**: `closing_certainty` (RTF, fiduciary out), `indemnity_leakage` (survival), or `not_quantified` (MAE carveouts).
- **low / high**: from the risk estimate record.
- **source_estimate_id**: the risk estimate ID.

## Recommendations

- **approve**: draft is within committee tolerance.
- **approve_with_conditions**: committee can approve if specific conditions are met (e.g., cap the fee at policy threshold, add a carveout exception).
- **reject**: committee should reject (e.g., missing fiduciary trigger that is non-negotiable).

Each recommendation with conditions must list the `required_conditions` as an array of short descriptive strings.

## Aggregate Summary

- **escalated_term_count**: number of terms in the escalation array.
- **excluded_in_policy_terms**: list of term IDs that were checked but found in-policy.
- **excluded_in_policy_categories**: categories that were checked but had no escalated terms.
- **risk_counts**: count of HIGH, MEDIUM, LOW.
- **aggregate_quantified_exposure_low / _high**: sum of low/high across escalated terms.
- **rtf_excess_amount**: `delta.amount` for the reverse termination fee, if escalated.
- **overall_recommendation**: the highest-severity recommendation across all terms.
- **committee_action**: one-sentence summary of what the committee should do.
- **negotiation_priority**: category IDs ordered from most to least critical.
