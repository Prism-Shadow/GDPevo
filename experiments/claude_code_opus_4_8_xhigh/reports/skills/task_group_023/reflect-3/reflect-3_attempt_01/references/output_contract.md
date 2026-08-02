# Output contract & self-check

The `answer_template.json` is a strict contract. The grader is a **partial-credit**
field scorer: every leaf value that matches earns weight, so a structurally complete
answer with correct cohort counts and a correctly derived decision already scores well
even if some interior module numbers drift. Maximize matched leaves.

## Formatting rules (read them off the template every time)

- **Submit exactly one JSON object**, with exactly the required top-level keys, and **no
  narrative** outside it. Drop any `template_instructions` / descriptor scaffolding — emit
  values, not the schema.
- **Precision.** Round every reported non-integer to the declared decimals (commonly 4;
  some tasks say 6 for computed reals and 4 for literal grids/thresholds). Keep counts,
  ranks, fold numbers, seeds, PRNG states, replicate numbers as **integers**; keep
  booleans as JSON booleans. Trailing zeros need not be preserved.
- **Identifiers.** Uppercase two-letter state codes; uppercase ISO3; portal **division /
  region names exactly** as the portal spells them. Set-like id lists are unique and
  sorted as told (usually ascending ASCII); aligned result arrays are **not** re-sorted.
- **Ordering.** Preserve every declared order (feature order, division order, coefficient
  order, grid order, checkpoint order, source-group order). An array that is "aligned to"
  another (e.g. delete-one coefficients aligned to `state_order`) must match it positionally
  and in length.
- **Missing.** Use JSON `null` only when a statistic is *mathematically* unavailable — never
  `NaN`/`Infinity`, never zero-fill a suppressed/absent input.

## The gated decision

Each task ends with a decision block: compute each module's **gate boolean** from the
declared threshold, count how many pass, and map to the classification by the declared
**precedence** (e.g. all gates → strongest label; ≥4 → intermediate; else weakest; or
"robust across modules" vs. "not robust at <first failed module>"). Get the gate
inequalities and the precedence order exactly right — the decision/classification is a
high-value, self-contained field you can often derive even when some module internals are
approximate. Report the boolean flags, the passed-count, and the enum together.

## Self-check before submitting

Run this checklist against the template:

1. **Top-level keys** — present, exactly named, nothing extra.
2. **Array lengths** — every `array_lengths` / `length` / `cardinality` rule satisfied
   (e.g. 5 years, 9 divisions, 13 features, 16 subsets, N checkpoints). Nested matrices
   (`[9,5]`, `[3,2]`) have the right shape.
3. **Alignment** — each "must match X" / "aligned to X" array equals X's length and order.
4. **Complement sets** — excluded-code lists are exactly universe − cohort.
5. **Types** — integers vs numbers vs booleans vs enums per field; enums use only allowed
   values; required literal fields (`request_id`, seeds, `alpha`, `nominal_coverage`) echo
   the request.
6. **Precision** — non-integers rounded to the declared places.
7. **Decision consistency** — gate booleans, passed-count and classification are mutually
   consistent under the precedence rule.
8. Parse the final string with a JSON parser; confirm it is one object with no trailing
   prose.

A programmatic validator that walks the template's `required_keys` / `array_lengths` /
`cardinality` rules and asserts each on your answer object catches most lost points.
