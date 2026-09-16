# Source and Year Perturbation

## Time Subset Perturbation

When the perturbation enumerates time subsets (e.g. year_subset_sizes [3, 4, 5]):

1. For each declared subset size, enumerate all combinations of that many years from the analysis years, in lexicographic ascending order.
2. Concatenate subsets across sizes in declared order to produce the full subset_order (16 subsets for 5 years with sizes 3,4,5).
3. For each subset, using the same strict analytic set:
   - Keep only rows whose year is in the subset.
   - Refit the full model (double-demeaned OLS with CR1 inference) from scratch.
   - Record the target coefficient and CR1 p-value for both primary and parallel series.
4. Compute absolute_percent_shift = abs(b_subset - b_full) / abs(b_full) * 100. If b_full == 0, use an alternative denominator or treat as undefined (null).
5. same_sign_subset_n: count of subsets where both primary and parallel coefficients have the same sign as their full-model counterparts (nonzero and same sign).
6. same_sign_subset_fraction = same_sign_subset_n / total_subsets.
7. median_absolute_percent_shift: ordinary median of ordered shifts.
8. maximum_absolute_percent_shift: maximum shift.
9. worst_shift_subset: the subset name with greatest unrounded shift, tie-broken by earlier subset order.

## Exhaustive Source Perturbation

When replacing an outcome source (e.g. DIRECT_SURVEY -> COUNTY_ROLLUP):

1. Resolve the alternate outcome records using the module's effective filters (e.g. value_type=CRUDE, source_type=COUNTY_ROLLUP).
2. For each entity, compare the baseline and alternate outcome values.
3. Order entities by descending absolute difference (|alternate - baseline|), tie-broken by entity code ascending. These are the ordered_rollup_state_codes.
4. Let m = number of such entities. Total scenarios = 2^m (each entity either uses baseline or replacement).
5. For each bitmask from 0 to 2^m - 1 (in increasing integer order):
   - Entity j uses replacement iff bit j of mask is 1.
   - Keep the same fixed reliability weights and design matrix.
   - Refit WLS with HC3 inference.
   - Record the target coefficient and HC3 p-value.

### Stratum Aggregation
Group scenarios by replacement_count (popcount of the bitmask). For each stratum:
- scenario_count: number of masks with that popcount
- minimum_coefficient, maximum_coefficient
- minimum_hc3_p_value, maximum_hc3_p_value
- mean_absolute_percent_shift: mean over scenarios of 100 * |(b_mask - b_zero) / b_zero|

### Stability
A scenario is "stable" if it satisfies the declared predicate (e.g. the coefficient remains statistically significant at a threshold). stable_scenario_count counts all scenarios satisfying the predicate.

### Maximum Shift
Select the scenario with greatest unrounded absolute percent shift. Tie: smaller bitmask integer.
- maximum_shift_bitmask: the integer mask
- maximum_shift_replaced_state_codes: entities with bit=1 for that mask, in declared order
- maximum_shift_coefficient, maximum_shift_hc3_p_value

### Shapley Attribution
For ordered entity j:
- phi_j = sum_{S subset of {1..m} excluding j} |S|! * (m - |S| - 1)! / m! * [b(S U {j}) - b(S)]
- Compute phi_j in declared entity order.
- shapley_sum = sum_j phi_j
- all_rollup_minus_all_direct_coefficient = b(all replaced) - b(none replaced)

Verify: shapley_sum should equal all_rollup_minus_all_direct_coefficient within numerical tolerance.

### Source Group Perturbation (for prediction models)
When removing groups of features from a prediction model:
1. For each declared source group, remove its terms from the model.
2. For each outer fold, reuse the full model's selected hyperparameters without retuning.
3. Apply the same preprocessing and solver to the reduced model.
4. Record per-fold RMSE, then pool squared errors across folds.
5. rmse_deterioration = pooled_rmse_reduced - full_model_pooled_rmse.
6. worse_fold_count: number of folds where reduced RMSE > corresponding full-model fold RMSE.
7. Rank groups: decreasing unrounded deterioration, then declared group order.
