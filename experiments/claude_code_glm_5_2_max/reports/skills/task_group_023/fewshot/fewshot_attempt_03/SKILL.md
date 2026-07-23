---
name: pho-algorithmic-audit
description: Solve Public Health Observatory (PHO) algorithmic transport/audit tasks. Read the task prompt plus analysis_request.json and answer_template.json from the task's input/payloads/, pull evidence only from the read-only PHO web portal, resolve one effective request, run the registered multi-module audit with exact reproducible numerics, and return exactly one JSON object conforming to answer_template.json. Use when a task names the PHO portal (<TASK_ENV_BASE_URL>), carries a PHO_* protocol_id and a declared set of audit modules in analysis_request.json, and asks for a single JSON answer conforming to an answer_template.json contract.
---

# Public Health Observatory Algorithmic Audit

This skill solves the PHO "algorithmic transport / robustness audit" family of tasks. Every
task in the family has the same shape: a business question, a read-only evidence portal, an
`analysis_request.json` that registers a `protocol_id` plus ordered audit modules, an
`answer_template.json` that fixes the response contract, and a demand for **exactly one JSON
object** with no surrounding narrative.

The method is reusable; only the task-local bindings (entities, measures, years, geography,
sources, seeds, grids, cutoffs, output vocabulary) change per request. **Never carry solved
analytical values from one task into another** — recompute everything from the effective
request and the portal evidence.

## When to use this skill

Activate when **all** are true:

- The task points at a Public Health Observatory portal via `<TASK_ENV_BASE_URL>` (resolved
  from `environment_access.md`).
- `analysis_request.json` declares a `protocol_id` whose string begins with `PHO_` and ends
  with a version tag (e.g. `..._V1`, `..._TRANSPORT_V1`, `..._AUDIT_V1`).
- The request registers a set of `audit_modules` (typically six) plus a `decision_rule` /
  `controlled_conclusion` and a `reporting` block.
- The response must be one JSON object conforming to `answer_template.json`.

Activation is by **exact `protocol_id` match** for any protocol-specific profile, but the
procedure below is common to the whole family. If the `protocol_id` is unfamiliar, still
apply this procedure — bind every parameter from the effective request.

## Inputs (read from the task's `input/payloads/`)

- `prompt.txt` — business framing and the `<TASK_ENV_BASE_URL>` placeholder.
- `analysis_request.json` — the registered protocol: scope, outcome/exposure/mediator,
  evidence specification, ordered `audit_modules` (each with a `method` string, cohort,
  parameters, `required_evidence`), `reporting` (precision), and `decision_rule`.
- `answer_template.json` — the binding output contract: required top-level keys, per-field
  types, array lengths/cardinality, ordering, enum values, and precision.

Treat `answer_template.json` as the single source of truth for the response shape. Where the
template gives an `ordering`, `cardinality`, `allowed_values`, or `required_value`, follow it
exactly.

## Output

Exactly one JSON object. No prose, no code fences, no commentary outside the JSON. The object
must contain every required top-level key and conform to the template's types, ordering,
cardinality, enum values, and precision. A `protocol_registry_record` block is **not** part of
the solver-visible contract — do not emit one unless the effective template requires it.

## Hard rules (apply to every task)

1. **Portal-only evidence.** All data comes from the read-only PHO portal reached through
   `environment_access.md` — the sole authorized network path. See
   [`references/portal.md`](references/portal.md). Do not invent, impute-from-memory, or
   synthesize values not present in the portal.
2. **One effective request.** Resolve a single effective `analysis_request` (override merge)
   **before** any data access, fit, random draw, aggregation, or decision. Every module must
   use the same effective request. See [`references/request_resolution.md`](references/request_resolution.md).
3. **Never zero-fill.** Suppressed, invalid, withdrawn, blank, or null analytic values are
   *unavailable* — they count as publication evidence when counting releases, but are excluded
   from analytic completeness. Never treat a missing/suppressed value as zero.
4. **Preserve declared order.** Every list retains the exact order declared in the effective
   request (entity order, time order, feature order, grid order, checkpoint order, source
   order). Do not sort an aligned result array independently. Ties in selections follow the
   documented tie-break (usually: smaller penalty / smaller grid value / earlier entity code /
   smaller mask / lexicographically smallest permutation).
5. **Round only reported fields; decide on unrounded values.** Evaluate every business
   predicate / gate on full-precision values, then round reported statistics to the request's
   declared decimal places. See [`references/output_contract.md`](references/output_contract.md).
6. **Exact identifiers.** Uppercase two-letter state codes; portal division names spelled
   exactly as the geography reference returns them; uppercase ISO3. FIPS codes are text with
   meaningful leading zeros.
7. **null, never NaN.** Use JSON `null` only when a requested statistic is mathematically
   unavailable. Never emit `NaN` or `Infinity`. Integers and booleans stay natural JSON types.

## Procedure

1. **Read the inputs.** Parse `prompt.txt`, `analysis_request.json`, and
   `answer_template.json`. Note the `protocol_id`, the module list and its declared order,
   the reporting precision, and the decision rule.
2. **Resolve the effective request.** Verify the `protocol_id`; fold direct keys and
   `*_overrides` / `module_overrides` aliases per the override rules; freeze one contract.
   See [`references/request_resolution.md`](references/request_resolution.md).
3. **Pull and resolve evidence; build cohorts.** Fetch each needed dataset from the portal
   (CSV via `/download`); filter by the effective status/source/value_type/validity/geography
   bindings; select one record per entity-time-measure key using the declared release
   priority; build the primary / balanced / broad / strict cohorts from the effective
   completeness predicates. See [`references/portal.md`](references/portal.md) and
   [`references/request_resolution.md`](references/request_resolution.md).
4. **Run the audit modules in declared order.** Each module's `method` string names the exact
   algorithm; bind all parameters (cohort, feature order, grid, seed/stream, replicates,
   quantile probabilities, checkpoints) from the effective request. The reusable numerics are
   in [`references/methods.md`](references/methods.md). Run modules in the order the request
   lists them; later modules reuse earlier fits where the method says so (e.g. conformal
   reuses nested-CV outer predictions).
5. **Evaluate the controlled decision.** On unrounded values, evaluate every gate predicate,
   count satisfied gates, and apply the request's precedence + controlled-conclusion mapping.
6. **Emit one JSON object.** Assemble exactly the template's top-level keys, in the template's
   order, at the declared precision, with every aligned array preserving its declared order.

## Module families (generic; parameters come from the effective request)

The family shares a common core of audit modules. The exact subset and naming vary by
protocol; bind from the request. Full reusable numerics live in
[`references/methods.md`](references/methods.md).

- **Release & cohort resolution** — publication filtering, ordered release priority,
  completeness cohorts.
- **Delete-cluster fixed effects / cluster jackknife** — two-way FE OLS (or weighted OLS),
  delete-one-cluster refits, jackknife bias correction and inference, influence summary.
- **Nested ridge / elastic-net cross-validation** — leave-one-group-out outer and inner folds,
  training-only standardization, cyclic coordinate descent, smallest-RMSE-then-smaller-penalty
  selection, pooled OOF metrics.
- **Wild cluster bootstrap** — restricted-null refit, registered PRNG (pcg32 with stream, or
  xorshift32), one continuous stream drawing once per cluster in order, plus-one p-value,
  nearest-rank or type-7 quantiles, checkpoints recorded after the completed replicate.
- **Grouped split conformal** — per-group calibration, nearest-rank threshold, symmetric
  inclusive intervals, coverage/width aggregation by held-out counts.
- **Trajectory PCA + deterministic k-means** — covariance PCA (symmetric Jacobi), sign
  orientation, farthest-first initialization, Lloyd updates, leave-year-out / delete-state
  adjusted-Rand-index stability.
- **Source perturbation** — exhaustive source-year / source-group / direct-vs-rollup subsets
  or bitmasks, refit, percent-shift summaries, exact Shapley attribution where declared.
- **Protocol-specific modules** (when the request declares them): difference-GMM mediation,
  partial-R² sensitivity surface, two-step linear GMM, region-adjusted panel model, etc.
- **Controlled decision** — gate evaluation on unrounded values, count + precedence mapping.

## Reproducibility essentials (these make or break an exact match)

- **PRNG is fully specified by the module `method` string.** `PCG32_*` uses 64-bit pcg32 with
  `increment = 2*stream + 1`, zero-init, advance, add the init value mod 2^64, advance; each
  advance is the standard pcg32 output; map output modulo six to the six Rademacher-ish
  weights `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`. `*XORSHIFT32*` uses
  `x ^= x<<13; x ^= x>>17; x ^= x<<5` with 32-bit masking after every xor; map odd state to
  `+1`, even to `-1`. Maintain **one continuous stream**; draw once per cluster in registered
  order per replicate; checkpoints are recorded **after** their completed replicate without
  resetting the stream.
- **Standardize from training moments only.** Training mean and (population or sample SD per
  the method) computed on the training rows; apply those moments to validation/test rows. Zero
  variance uses a unit divisor. Outcome is centered, not scaled, for ridge/elastic-net.
- **Cold-start solvers.** Coefficients initialize to zero (intercept to training outcome
  mean); no warm-start across penalties. Stop after a full sweep when the max coefficient
  change is below the effective tolerance or at the sweep/cycle cap.
- **Selection tie-breaks.** Smallest unrounded RMSE, then smaller penalty (ridge) / smaller
  alpha then smaller l1_ratio (elastic-net).
- **PCA orientation.** Order eigenpairs by descending eigenvalue then original diagonal index;
  flip each retained eigenvector so its **earliest maximum-absolute loading is positive**;
  scores are Z times oriented loadings.
- **k-means initialization.** First center is the ASCII-first entity; each next is the entity
  maximizing distance to its nearest center (tie → entity code); assign ties to lower cluster
  id; update by member means; stop when labels are unchanged or at the cap. Canonicalize final
  ids by centroid coordinates then working id.
- **Stability via adjusted Rand index.** For each omitted time block / deleted state, rebuild
  the full pipeline from scratch and compare labels with ARI; align refit ids by the
  permutation with maximum matches (tie → lexicographically smallest mapped-id vector).
- **Gates and decisions use unrounded values**; only reported fields are rounded.

## See also

- [`references/portal.md`](references/portal.md) — portal access, dataset schemas, CSV
  download filters, methodology library.
- [`references/request_resolution.md`](references/request_resolution.md) — effective-request
  override resolution, release priority, cohort construction, ordering.
- [`references/methods.md`](references/methods.md) — reusable statistical method for each
  module family.
- [`references/output_contract.md`](references/output_contract.md) — precision, ordering,
  identifiers, null rules, controlled-decision evaluation.
