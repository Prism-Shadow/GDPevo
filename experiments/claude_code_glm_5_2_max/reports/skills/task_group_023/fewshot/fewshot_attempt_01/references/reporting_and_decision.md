# Reproducibility, Reporting, and the Controlled Decision

These rules are cross-cutting. They apply to every module and to the final JSON.
Violating any of them typically breaks the evaluator even when the statistics are
right.

## Reproducibility

The deliverable is a **deterministic** computation. Floating-point and ordering
choices are part of the answer.

- **PRNG.** Use the exact declared generator (PCG32-Webb or xorshift32-Rademacher —
  see [`module_methods.md`](module_methods.md) §E2), with the declared seed and
  stream. Maintain **one continuous stream** per bootstrap; record checkpoints
  only after the listed replicate completes; **never reset** between replicates or
  checkpoints. Report the terminal generator state when required.
- **Draw order.** Draw once per cluster in **entity-code order** per replicate.
  Reuse the same cluster sign across paired equations when paired.
- **Ordering.** Preserve every declared order: entity (state/county/ISO3 code),
  time (year), feature, group (division/region/RUCC), coefficient, penalty grid,
  checkpoint, source group, and subset. **Never independently re-sort an aligned
  result array** (e.g. delete coefficients, scores, labels, per-subset vectors) —
  they align positionally with a declared order.
- **Tie-breaks.** Apply declared tie-breaks exactly: ASCII-first / smallest entity
  id; lower working cluster id; lower row then column (Jacobi pivot); farthest
  point then entity code (k-means seeding); lower id on assignment equality;
  lexicographically smallest permutation on label alignment; smaller penalty, then
  smaller `α`, then smaller `l1_ratio` on RMSE ties; smaller mask on shift ties;
  earlier cluster/subset on influence/shift ties.
- **Cold starts.** Ridge/elastic-net refits cold-start coefficients at zero (and
  the intercept at the training outcome mean) for every penalty and fold — never
  warm-start. Source-group perturbation reuses full-model hyperparameters **without
  retuning**.
- **Refit from scratch.** Cluster/substring deletions recompute all dependent
  means, moments, and fits from scratch in entity order; do not approximate with
  update formulas.

## Reporting precision and types

- **Decimal places.** Round every reported non-integer to the declared places
  (commonly **4**). Some protocols split precision: **6** for computed reals and
  **4** for literal grid/threshold values; others use 4 throughout. Honor the
  request's `reporting` / `precision` block.
- **Round only reported fields.** Evaluate gates, select extrema, and pick
  penalties/quantiles on **unrounded** values; round only when emitting. Keep an
  unrounded working copy throughout.
- **Integer and boolean fields** keep natural JSON types (counts, ranks, fold
  numbers, seed, PRNG states, replicate numbers are integers; gate flags are
  booleans).
- **Identifiers.** Use uppercase two-letter state codes, exact portal
  division/region names, ISO3 in the declared case, and enum values **exactly** as
  the template lists them.
- **Missing.** Use JSON `null` **only** when a requested statistic is
  mathematically unavailable (e.g. a singleton cluster, a zero-denominator shift, a
  degenerate fit). **Never** emit `NaN` or `Infinity`. Suppressed/invalid/blank/
  null analytic values are unavailable and are **never zero-filled** — neither in
  data nor in reported statistics.
- **Counts.** Report requested counts exactly as defined (selected rows by year,
  yearly complete counts, cohort sizes, cluster/group counts, observation counts,
  fold sizes). Compute them for the invocation; do not copy.

## The output object

- Return **exactly one JSON object** conforming to `answer_template.json`.
- Include every required key at every level; honor declared array lengths and
  orderings; honor `global_rules` / `template_instructions` (e.g. "lists must use
  the specified order", "compact ridge arrays aligned positionally to
  `lambda_grid`").
- **No narrative outside the JSON.** No prose, no markdown fences around the
  object, no commentary.
- The optional `protocol_registry_record` provenance (when included) is
  method-only and evaluator-ignored; it must not carry task-local solved values.

## Controlled decision

1. **Complete every evidence module first.** Do not short-circuit on an early
   failure unless the request's precedence is explicitly "first failed module."
2. **Evaluate every business predicate on unrounded values.** Predicates and
   thresholds are declared in the request (e.g. coefficient sign + p ≤ threshold,
   pooled R²/Q² ≥ cutoff, bootstrap p ≤ threshold, coverage ≥ cutoff, width ≤
   cutoff, min/median ARI ≥ cutoff, same-sign fraction ≥ cutoff, median shift ≤
   cutoff, deterioration ≥ cutoff). The thresholds are task-local — read them.
3. **Preserve the declared gate/module order** for reporting gate values (typically
   `PASS`/`FAIL` or booleans) and the supported count.
4. **Count satisfied predicates.**
5. **Apply only the request's classification mapping and precedence/tie rules.**
   Common shapes:
   - All gates pass → primary classification; `≥ N` gates pass → intermediate;
     otherwise → none.
   - First-failed-module: return `ROBUST_...` if all pass, else
     `NOT_ROBUST_AT_<FIRST_FAILED_MODULE>` in precedence order.
   - Tiered deploy/review/retain by pass count.
6. **Report gate values, the supported count, and the final classification** in the
   template's declared keys and enum values.

The decision is the last module — but its inputs are the unrounded outputs of all
the modules above, so getting the method and ordering right upstream is what makes
the classification correct.
