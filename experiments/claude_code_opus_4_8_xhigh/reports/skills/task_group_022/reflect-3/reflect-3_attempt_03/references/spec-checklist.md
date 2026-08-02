# Per-request checklist

Run this against any new operations request + answer_template of this family.
It is domain-agnostic: it names the *kinds* of clauses to look for, not any
specific task's values.

## 1. Parse the contract
- [ ] Read prompt, request payload, and `answer_template.json` fully.
- [ ] List every `required` output key and its type/enum/pattern/decimal rule.
- [ ] Note `additionalProperties: false` → no extra keys allowed.
- [ ] Consult the schema and data dictionary; map each business term to a real
      column. Note raw vs. canonical/effective columns and status vocabularies.

## 2. Build the eligible cohort (do this first)
- [ ] Production/non-test flag applied.
- [ ] All scope filters applied (segment, tier, region, warehouse, campaign, …).
- [ ] Window applied with correct inclusivity on both ends (exact UTC).
- [ ] "Eligible" = attribution AND creation/opening inside the active window.
- [ ] Distinct entity granularity (distinct orders/cases, not rows).

## 3. Metrics
- [ ] Numerator uses the precise definition (effective / net-of-reversals /
      canonical / on-time / completed-by-cutoff).
- [ ] Denominator keeps incomplete/unresolved/breached items unless told otherwise.
- [ ] Cutoff respected: only events at/before the cutoff count; open items use
      elapsed-at-cutoff.
- [ ] SLA/threshold comparisons use the per-priority value and the stated clock basis.
- [ ] Money converted with the correct daily FX rate (row's service_date + currency).
- [ ] Full precision kept; rounding applied ONCE at the end to stated decimals.

## 4. Lists and rankings
- [ ] Sort key = named metric on the UNROUNDED value.
- [ ] Direction correct (asc/desc); tie-break applied (usually id/region/code asc).
- [ ] Exactly N items returned.
- [ ] ID lists sorted ascending and matching the required regex.

## 5. Composite definitions
- [ ] Each branch of a severe/exception/leakage definition encoded separately.
- [ ] Every explicit carve-out honored (e.g. "no promise → first branch not met").

## 6. Classification
- [ ] Status/risk rules evaluated top-to-bottom, first fully-satisfied tier wins.
- [ ] ALL sub-thresholds of the chosen tier are satisfied.
- [ ] "otherwise" used only as the final fallback.
- [ ] Compared against unrounded rates.

## 7. Correction/mutation tasks only
- [ ] Exactly one canonical field corrected; raw/source/identity + unrelated rows
      untouched.
- [ ] One business-row update + one audit-row insert, atomic.
- [ ] Audit row carries the approved reason_code/actor/id/key/corrected_at.
- [ ] Post-change read confirms the new canonical value.
- [ ] `APPLIED` only if committed AND verified; else `NOT_APPLIED` with observed
      figures.
- [ ] Pre/post figures and their delta reconcile.

## 8. Final validation
- [ ] Counts cross-foot (parts sum to whole; subsets ⊆ supersets).
- [ ] Each rate re-derived from numerator/denominator.
- [ ] Object validates against every template constraint.
- [ ] `answer.json` holds only the JSON object — no commentary.
