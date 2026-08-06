# Output Contract and Verification

The deliverable is a single JSON object conforming to `answer_template.json`. This file captures the cross-cutting output discipline and a pre-submission verification checklist. All schema details (keys, lengths, enums, precision) are read from the per-task template; this file describes the rules that hold across tasks.

## Single object, no narrative

- Return **exactly one JSON object**. No prose, headings, code fences, trailing commentary, or partial outputs. If the task says "do not include narrative outside the JSON," that is literal.
- The object's top-level keys are exactly the template's `required_top_level_keys` (or `required_output` keys). No extra top-level keys, none missing.
- Every nested object has exactly its declared `required_keys`; every list has its declared length and item keys.

## Numeric discipline

- **Precision:** use the request's `reporting`/`precision` block. Default is 4 decimal places for non-integers. Some tasks split precision: computed real-valued statistics to 6 decimals, while literal grids/thresholds (alpha, l1_ratio, nominal_coverage, declared grid values) to 4. Apply the split only if the request declares it.
- **Rounding:** round each reported non-integer to the declared places. JSON numbers need not preserve trailing zeros (e.g. `0.5` not `0.5000`).
- **Integers and booleans:** natural JSON types — counts, ranks, fold numbers, seeds, PRNG states, replicate numbers, years, and revision numbers are integers; gate/support flags are booleans. Do not encode them as strings.
- **No NaN or Infinity.** These are not valid JSON.
- **Null only when mathematically unavailable.** Use JSON `null` exclusively for a requested statistic that cannot be computed (e.g. a coefficient in a singular design, a quantile with too few replicates). Never use `null` for missing source data — missing source data means the cohort/record is excluded, not that a `null` is reported.

## Ordering discipline

- **Preserve declared orders.** Any array the request or template assigns an order to (state/county/ISO3 order, coefficient order, feature order, division order, lambda/alpha grid, checkpoint replicate list, source-group order, cluster order, year order, omitted-state/year order) must appear in **that exact order**.
- **Do not re-sort aligned arrays.** A result vector aligned positionally to a declared order (e.g. delete-one-cluster coefficients aligned to `state_order`) keeps the order's positions. Sorting it independently breaks alignment.
- **Set lists are sorted only when the template says so.** Identifier *sets* — e.g. resolved ISO3, excluded state codes, high-burden membership — are sorted ascending (often "ascending ASCII") **only** when the template explicitly states that ordering. Otherwise keep declared order.
- **No maps/substitutions where a list is required.** If the template specifies a list with an ordering, emit a list, not an object/set.

## Identifier formatting

- **State codes:** uppercase two-letter (e.g. `CA`, `DC`).
- **ISO3:** uppercase.
- **FIPS:** text strings, leading zeros preserved.
- **Division/region names:** portal strings verbatim (exact case and spelling as returned by `/geographies/states`).
- **Measure/indicator ids:** exact strings from the catalog/measure dictionary.
- **Revision event ids / observation ids / record ids:** exact portal strings.

## Enum values

- Use **only** the controlled values the template declares for each enum field (e.g. classification tiers, conclusion values, first-failed-module values, method-name strings, cluster-definition strings).
- Where a field has a `required_value` (a single allowed value), emit exactly that value.
- Boolean gate fields are `true`/`false`, not the gate labels.

## Decision precedence

- Evaluate every module's gate to its boolean/PASS-FAIL per the request's thresholds.
- Apply the request's precedence rule to map the gate pattern to the controlled classification/conclusion enum (see `audit_modules.md` → "Gate evaluation and decision").
- For "first failed module" conclusions, scan gates in the declared precedence order; the first failing module determines the conclusion; `NONE` / `ROBUST` when all pass.
- Count the supported/passed modules and report it where the template requires a count.

## Pre-submission verification checklist

Run this before returning the JSON. Each item must hold.

1. **Shape:** exactly the template's top-level keys; every nested object has its declared keys; no extra keys anywhere.
2. **Lengths:** every list matches its declared length (or cardinality rule, e.g. "length equals `state_n`", "one row per balanced state code and no others").
3. **Ordering:** every ordered list is in the declared order; aligned vectors are positionally consistent with their anchor order; identifier sets are sorted only where required.
4. **Alignment cross-checks:** arrays the template says must match (e.g. `wild_cluster_bootstrap.state_order` exactly equals `delete_cluster_fixed_effects.state_order`; `pc1_scores`/`pc2_scores`/`cluster_labels` length equals `state_order` length) do match.
5. **Precision:** non-integers at the declared places; integers/booleans as natural types; no trailing-zero requirement violated; no strings where numbers are required.
6. **No NaN/Infinity; nulls justified:** every `null` corresponds to a genuinely unavailable statistic; no `null` stands in for missing source data.
7. **Enums:** every enum/required_value field is one of the declared allowed values.
8. **Identifiers:** correct casing/format for state codes, ISO3, FIPS, division/region names, measure ids.
9. **Decision consistency:** the reported classification/conclusion matches the gate booleans under the request's precedence rule; the supported-module count matches the gate pattern; first-failed-module (if reported) is the first failing gate in precedence order.
10. **Evidence traceability:** every reported number traces to portal records resolved under the declared release/revision/quality rules — no assumed, external, or zero-filled values.
11. **Single object:** the final output is one JSON object with no surrounding narrative.
