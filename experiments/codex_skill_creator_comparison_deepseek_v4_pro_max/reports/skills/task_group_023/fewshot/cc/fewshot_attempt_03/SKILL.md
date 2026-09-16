---
name: pho-audit
description: >
  Execute registered Public Health Observatory algorithmic audits using only
  the PHO REST API. Use this skill whenever the user needs to resolve PHO
  publication releases, construct study cohorts from health and socioeconomic
  data, or run any registered multi-module audit (transportability, mediation,
  burden stratification, robustness, or county dynamics) that requires
  clustering, ridge or elastic net, wild bootstrap, conformal prediction,
  PCA trajectory clustering, source perturbation, or Shapley attribution.
  The skill covers all PHO algorithmic audit families including state-level,
  county-level, and country-level protocols.
compatibility: curl, Python 3, numpy
---

# PHO Algorithmic Audit Skill

This skill enables a Codex solver to complete any registered PHO audit by
providing reusable methodology for API interaction, release resolution,
cohort construction, and every algorithmic module used by the PHO protocol
families.

Use and only use the authorised evidence source whose base URL is supplied as
`<TASK_ENV_BASE_URL>` in the task prompt. Never guess URLs.

---

## Core Workflow

1. Read the task prompt, `analysis_request.json`, and `answer_template.json`.
2. Resolve releases and build every declared cohort against the PHO API.
3. Execute audit modules exactly as declared in the request, using the
   methods in `references/methods.md`.
4. Run the controlled decision module from the computed evidence.
5. Return one JSON object conforming to `answer_template.json`.

If an `answer_template.json` references `protocol_registry_record`, note
that it is an **output provenance field only**; it is never solver input
and is not required for computation. However, if the template includes it
as a required top-level key, populate it with the method profile from the
matching answer structure.

---

## Rule Zero: The Effective Request

Before any data access or computation, resolve one effective request from
`analysis_request.json`. Apply these override rules:

- A direct root key binds to the identically named canonical key.
- A root key `<section>_overrides` targets canonical `<section>`, stripping
  the `_overrides` suffix. Inside a named section or module, a direct child
  key targets only that identical child path. Similarly,
  `module_overrides.<module>` targets that exact top-level module,
  `reporting_overrides` targets the `reporting` section.
- Merge in request document order: objects merge by exact key recursively;
  arrays replace whole arrays (never concatenate or patch positionally);
  explicit scalars, strings, booleans, and null replace only at their exact
  path; absent paths inherit unchanged.
- Task-local direct bindings take precedence over inherited defaults at the
  same path. Reject unknown targets and incompatible types.
- Use the same effective request consistently in every module.

---

## Precision and Ordering

- Round every computed **non-integer** statistic to the precision declared
  in the answer template (commonly 4 or 6 decimal places) and encode as a
  JSON number. Integers and booleans keep their natural JSON types.
- Never use `NaN` or `Infinity`; use JSON `null` only when a requested
  statistic is mathematically unavailable.
- Preserve every declared order exactly. State, feature, cluster, division,
  and grid orders come from the effective request or the natural entity-code
  order from the API. Never sort an aligned result array independently.
- When ascending identifier order is required, use ASCII ordering.

---

## PHO API

All endpoints are at `<TASK_ENV_BASE_URL>`. See `references/api.md` for the
full endpoint catalog and query parameters.

### Release Selection

The universal rule: filter each publication key by the effective status,
source, value type, and entity bindings. Then select **one record per
entity-time-measure key** using these criteria in order:
1. greatest `revision` number
2. latest `released_at` timestamp
3. lowest `observation_id` or `record_id` (depending on dataset)

**Suppressed, invalid, withdrawn, blank, or null analytic values remain
unavailable publication evidence.** They are never zero-filled, never
imputed, and never treated as zero.

### Cohort Construction

Construct each cohort from the independently resolved series after release
selection. Join by stable entity and time keys. Apply the effective
completeness predicates. Preserve entity-code then time order everywhere.

The cohort types used across protocols:

| Cohort | Definition |
|--------|-----------|
| **Primary** | Complete cases in the reference year for all required fields |
| **Balanced** | Intersection of complete cases across every study year |
| **Broad** | Reference-year complete for outcome and all ordered features |
| **Strict dual-source** | Complete for outcome, primary exposure, parallel exposure, and adjustments in every study year |
| **Machine-learning** | Primary-cohort members also complete for additional declared fields |

When a reliability weight is bound (e.g., `sample_size` from a health
measure), keep the selected direct-record value as a fixed positive weight
across all fits, including source-perturbation refits. Never standardize,
rescale, or normalize the weight.

---

## Method Reference

All reusable computational methods are described in `references/methods.md`.
Read that file before executing any module. The modules are:

1. **Release resolution and cohorts**
2. **Common linear algebra** (WLS, HC3, CR1, double-demeaning)
3. **Fixed-effects / GMM regression** with cluster-robust inference
4. **Delete-one-cluster jackknife**
5. **Nested ridge** with training-only standardization
6. **Nested elastic net** with coordinate descent
7. **Wild cluster bootstrap** (PCG32 or xorshift32 PRNG)
8. **Grouped split / cross-fold conformal prediction**
9. **PCA** with Jacobi eigendecomposition
10. **Deterministic k-means clustering** with farthest-first init
11. **Source perturbation** with Shapley attribution
12. **Partial-R2 mediation sensitivity**

---

## PRNG Implementations

### PCG32 (state-level protocols)

Unsigned 64-bit state with wraparound, 32-bit output.
- `increment = 2 * stream + 1`
- Initialize state to zero, advance once, add the effective seed modulo 2^64, advance again
- Each advance: `old = state; state = old * 6364136223846793005 + increment mod 2^64`
- `xorshifted = ((old >> 18) xor old) >> 27` (low 32 bits)
- `rot = old >> 59`
- Output: rotate `xorshifted` right by `rot` bits (32-bit rotation)

Map output modulo 6 to weights: `[-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)]`

### xorshift32 (county/state protocols)

Unsigned 32-bit state with wraparound.
Initialize from the effective seed. Each call:
```
x ^= x << 13
x ^= x >> 17
x ^= x << 5
```
Truncate to unsigned 32 bits after every xor.
Map: odd state -> +1, even state -> -1 (or low bit 1 -> +1, 0 -> -1).

Maintain one continuous PRNG stream per module. Never reset mid-simulation.
Draw per cluster (not per observation) in registered cluster order.

### Bootstrap quantiles

- **Nearest-rank** (used in most PHO protocols): for sorted `x`, `p in (0,1]`,
  index `min(B, ceil(p * B)) - 1` (one-based rank).
- **Type-seven** (used when declared): `h = (B - 1) * p`, `j = floor(h)`,
  `gamma = h - j`, result = `(1 - gamma) * x[j] + gamma * x[j + 1]`
  (zero-based indexing).

---

## Controlled Decision

Complete every evidence module before evaluating gates. Evaluate each
gate on **unrounded** values. Apply the effective request's decision
precedence and mapping exactly. Count passing gates and select the first
applicable classification in the declared precedence order.

---

## Output Structure

The answer template declares every required key, array length, ordering rule,
and field type. Follow it exactly. Key sections typically include:

- `protocol_registry_record` -- optional provenance; include only if the
  template requires it as a top-level key
- `publication_cohort` / `release_and_cohort` / `cohort_audit` -- cohort counts
  and exclusion lists
- Module results -- one key per audit module, with complete ordered evidence
- `robustness_decision` / `controlled_conclusion` / `decision_audit` /
  `decision` -- gate booleans and final classification
- `advisory` -- for protocols with narrative recommendations

Keep array cardinalities exactly as specified; use the declared numeric
precision; preserve every declared list order.
