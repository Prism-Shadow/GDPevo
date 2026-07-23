# Output contract & pre-submission checklist

The answer is **one JSON object** conforming to `answer_template.json`. The template is the
source of truth for every formatting decision. These rules are the common, stable form across
all PHO audits; defer to the specific template when it says otherwise.

## Formatting rules

### Top-level shape
- Emit exactly the `required_top_level_keys`, in that order, nothing else. No wrapper object,
  no `template_instructions`, no metadata envelope unless a key is explicitly required.
- One JSON object only. No markdown fences, no prose before or after, no trailing commas.

### Keys & cardinality
- Include every key in each module's `required_keys` / `required_keys` list.
- Honor `array_lengths` (a scalar = exact length; a 2-element list = `[rows, cols]`) and
  `cardinality_rules` / `cardinality` text constraints (e.g., "every universe state code
  absent from the cohort, and no others").
- Where a key has `required_value` (a fixed string/enum), emit exactly that value.

### Ordering (the most common failure mode)
- Preserve the declared order for every list: `state_order`, `feature_order`,
  `coefficient_order`, `lambda_grid` / `alpha` / `l1_ratio_grid`, `division_order`,
  `checkpoint_replicates`, `subset_order`, `ordered_source_groups`, `leave_year_out_order` /
  stability omission order, `target_order` (mediation equations).
- Do **not** re-sort an array that is **positionally aligned** to another. Examples:
  `delete_obesity_coefficients` aligns to `state_order`; `pc1_scores`/`pc2_scores`/
  `cluster_labels` align to `state_order`; `delete_state_diagnostics` aligns to state order;
  inner-grid RMSE arrays align to `lambda_grid`; Shapley effects align to
  `ordered_rollup_state_codes`.
- Where the template **does** demand sorting, sort exactly as specified: "ascending ASCII",
  "state ascending", "ISO3 sorted ascending", "descending absolute loading (indicator_id
  ascending breaks ties)", "NEGATIVE then POSITIVE", "replacement_count ascending from 0
  through M", "registered division order", "registered replicate order".
- Set-like identifier lists must be **unique** when the template says so.

### Cross-module alignment
- `state_order` must be byte-identical across the modules the template says must match
  (commonly: delete_cluster_fixed_effects == wild_cluster_bootstrap == trajectory_pca_clustering).
- `division_order` / `lambda_grid` / `feature_order` must be the identical object across
  modules that share them.
- A module's `state_assignments` / `cluster_labels` must cover each and only each state code
  in the cohort it is built on (e.g., `release_and_cohort.balanced_state_codes`), in the same
  order.

### Precision & types
- **Default:** round every non-integer reported statistic to **4 decimal places**, encoded as
  a JSON number. Trailing zeros need not be preserved.
- **Where declared:** some tasks require **6 decimal places** for *computed real-valued*
  fields and **4 decimal places** for *literal grid/threshold* fields (e.g., alpha,
  l1_ratio, nominal_coverage, declared thresholds). Apply the per-field rule, not a global one.
- **Integers** are JSON integers (no `.0`): counts, ranks, fold numbers, seeds, PRNG states,
  replicate numbers, revision numbers, years, jurisdiction counts, `k`, update counts.
- **Booleans** are JSON `true`/`false` (gate flags), never `"PASS"`/`"FAIL"` unless the
  template's `gate_values` says otherwise (some templates use `"PASS"`/`"FAIL"` strings —
  match the template).
- **Enums** use only the `allowed_values` / `classification_values` / `controlled_values`
  declared. Decision classifications and `first_failed_module` are enums.

### Identifiers
- State codes: uppercase two-letter (`CA`, not `ca`).
- Division / region names: **verbatim** as the portal returns them
  (`Pacific`, `East South Central`, `New England`, …).
- ISO3: uppercase (`QAA`, not `qaa`).
- `request_id` / `protocol_id` / `briefing_id`: copy the declared value exactly.

### Missing values
- Use JSON `null` **only** when a requested statistic is mathematically undefined/unavailable
  (e.g., a quantile of an empty set, a degenerate fit). Never for missing source data — those
  are handled by cohort construction.
- Never emit `NaN`, `Infinity`, `-Infinity`, or the strings `"NaN"`/`"Infinity"`. If a value
  would be `NaN`, emit `null` and ensure the cohort/math genuinely makes it unavailable.

### Decision block
- Evaluate each gate against its **declared** threshold (from `robustness_gates` /
  `decision_rule.flags` / `controlled_conclusion`). Do not invent or round thresholds.
- Report per-gate PASS/FAIL or boolean, the `passed_gate_count` / `supported_module_count`,
  `first_failed_module` (use `NONE` when all pass), and the `classification` /
  `conclusion` / `decision` per the declared precedence:
  - all gates pass → top tier;
  - a declared partial threshold (e.g., ≥4, or 4–5) → middle tier;
  - else → bottom tier.
- Match the exact enum strings the template lists (e.g.,
  `PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL`, `ROBUST_ACROSS_REGISTERED_MODULES`,
  `DEPLOY_DIABETES_DYNAMICS`, `PRIORITIZE_HIGH_BURDEN_CLUSTER`).

## Pre-submission checklist

Run this before emitting the final JSON. Each item is a frequent failure.

- [ ] Exactly the required top-level keys, in order; no extra keys; no `template_instructions`.
- [ ] Every required sub-key present in every module.
- [ ] Every `array_lengths` / `cardinality_rules` satisfied (count them).
- [ ] Shared `state_order` is identical across the modules the template says must match.
- [ ] Every positionally-aligned array aligns to its anchor (coefficients↔state_order,
      scores↔state_order, inner grids↔lambda_grid, Shapley↔rollup order, checkpoints↔replicate order).
- [ ] Every "sorted" list sorted exactly as specified; every declared-order list preserved.
- [ ] Precision: 4 dp default; 6 dp for computed reals where declared; literal grids/thresholds
      at the declared precision. Integers are integers; booleans are booleans; enums match.
- [ ] No `NaN`/`Infinity`; `null` only for mathematically undefined statistics.
- [ ] Identifiers: uppercase state codes; portal division/region names verbatim; ISO3 uppercase;
      request/protocol ids copied exactly.
- [ ] RNG: declared seed/stream/replicate count; checkpoint PRNG states + t-stats at the
      declared replicates; terminal PRNG state recorded; plus-one p-value used.
- [ ] Cohort exclusion sets are complete (every universe jurisdiction absent, and no others).
- [ ] Decision: gates evaluated against declared thresholds; count correct; classification and
      first_failed_module match the precedence rule and allowed enum values.
- [ ] Output is a single JSON object with no narrative, no markdown fences, no trailing text.

## Final formatting

Serialize with standard JSON. Do not wrap in code fences. Do not prepend commentary like
"Here is the answer:". The entire submission is the JSON object.
