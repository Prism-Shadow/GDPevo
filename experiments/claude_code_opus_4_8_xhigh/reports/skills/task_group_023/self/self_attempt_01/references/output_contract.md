# Output contract, gates & decision logic

The `answer_template.json` is a strict contract. A response that computes every number correctly but
violates the shape, order, precision, or identifier rules still fails. Treat the template as the spec of
record and validate against it before submitting.

## Read the template as a schema

- **`required_top_level_keys`** — your object must contain exactly these keys (usually one cohort/census
  section, one section per module, and one decision section). Match the key spelling exactly.
- **Per-section `required_keys`** — every listed key must be present in that section.
- **`array_lengths`** — arrays must have exactly the stated length (scalars like `9` for the 9 Census
  divisions, `5` for years, or matrices like `[9, 5]` for a division×lambda inner grid). A wrong length
  is an immediate failure; it usually means a cohort or fold set was built wrong upstream.
- **`cardinality_rules`** — e.g. "length must equal the reported `state_n`", "must exactly match
  `<other_section>.state_order`", "one item for each and only each balanced state code". Cross-section
  alignment is required: reuse the *same* ordered unit list across modules where the template says so.
- **`ordering`** — either an explicit order ("year ascending", "registered division order",
  "TOTAL_POVERTY, PATH_A_POVERTY, PATH_B_INACTIVITY"), or "same order as <declared list>". Aligned
  arrays are positional; do not sort them. Only sort where it explicitly says sorted/ascending.

## Precision

- Default: round every **non-integer reported statistic to 4 decimal places**, encoded as a JSON number
  (not a string). Some tasks differ — e.g. one reports **computed reals to 6 dp** but literal grid /
  threshold / coverage / alpha / l1_ratio fields to **4 dp**. Read the task's numeric rule and apply the
  right precision per field class.
- Compute everything **unrounded**; round only at emission. Never round intermediate values used in
  later steps.
- JSON numbers need not preserve trailing zeros. Counts, ranks, fold numbers, seeds, PRNG states, and
  replicate numbers are **integers** (natural JSON ints, not floats).

## Identifiers & missing values

- State codes: uppercase two-letter (`CA`, `DC`). Division/region names: the exact portal strings.
  ISO3: uppercase. County FIPS: text with leading zeros.
- Set-like / complement / excluded lists: **unique and sorted ascending (ASCII)**.
- Aligned lists (scores, coefficients, per-unit assignments): **preserve the reference order**, not sorted.
- Use JSON `null` only when a statistic is mathematically unavailable. Never emit `NaN`, `Infinity`, or a
  string sentinel, and never zero-fill a missing input to avoid a null.

## Gate evaluation

Each module maps to one gate boolean. The task states the gate condition (in `robustness_gates`,
`controlled_conclusion`, or a `decision_rule.flags` list), e.g. "focal coefficient negative and jackknife
p ≤ 0.05", "pooled Q² ≥ 0.85 and pooled RMSE ≤ 0.75", "bootstrap p ≤ 0.05", "aggregate coverage ≥ 0.80
and mean width ≤ 3.25", "minimum leave-year-out ARI ≥ 0.75", "same-sign fraction ≥ 0.75 and median abs
percent shift ≤ 50". Evaluate each strictly from your module outputs and the declared numeric threshold —
mind `≤` vs `<` and `≥` vs `>`, and compound "and" conditions. Emit gate results as the template's type
(`PASS`/`FAIL` strings, or booleans).

## Decision / classification

Count passed gates and apply the declared **precedence**. Two recurring shapes:

- **Threshold tiers**: all N gates → strongest class (e.g. PRIMARY / CONSISTENT / ROBUST /
  DEPLOY_...); ≥ some count → an intermediate class (ASSOCIATED / PARTIAL / REVIEW_...); fewer → the
  null class (NO_... / RETAIN_...). Use the exact counts the task gives.
- **First-failed-module**: evaluate gates in the declared module precedence; if all pass →
  `ROBUST_ACROSS_...` with `first_failed_module = NONE`; otherwise the conclusion is
  `NOT_ROBUST_AT_<first failed module>` and `first_failed_module` = that module's enum token. Order
  matters — report the *first* failure in precedence order, not any failure.

Use only the template's allowed enum values verbatim. Also emit any required scalar like
`passed_gate_count` / `supported_module_count`.

## Pre-submission checklist

1. Top-level keys == `required_top_level_keys` (no extras, none missing; drop any `template_instructions`).
2. Every section has all `required_keys`.
3. Every array length matches `array_lengths`; every matrix has the right shape.
4. Every `cardinality_rules` alignment holds (cross-section unit orders identical where required).
5. Orders correct: aligned arrays positional; only explicitly-sorted lists sorted; complement sets complete.
6. Precision applied per field class; integers are ints; no `NaN`/`Inf`; `null` only where truly undefined.
7. Identifiers in the exact required case/format.
8. Gate booleans/enums legal; decision follows precedence; gate count consistent with the gate values.
9. Output is exactly one JSON object with **no narrative** around it.
