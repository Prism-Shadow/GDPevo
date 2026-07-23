# Answer-Template Patterns

Recurring constructs in `answer_template.json` files and how to satisfy each.
These describe the *shape* of the contract; the actual allowed values come from
the template in front of you, never from memory or from training examples.

## Fixed-value fields (`expected_constant` / `required_value`)
Some fields pin a literal value — typically `task_id` (from the task directory
name) and `case_id` (from the prompt). Copy the value exactly; do not "derive"
it.

## Enum fields (`type: "enum"` + `allowed_values`)
- Use a token from `allowed_values` verbatim. Case and underscores matter.
- Never invent a token. If the chart/protocol doesn't justify any allowed token,
  pick the closest "pending"/"not_eligible"/"defer…" token the template offers,
  or use `null` only if the field is explicitly `enum_or_null`.

## Null-permitted fields
Templates declare forms like `string_or_null`, `integer_or_null`,
`enum_or_null`, or JSON-Schema `["string","null"]`. Rules:
- Emit `null` only for fields whose spec explicitly permits it.
- When a plan defers action (e.g. `defer_antibiotic_selection_to_ed`,
  `supportive_care_no_antibiotic`, `urgent_escalation`,
  `hold_due_to_contraindication`), the dependent detail fields (medication,
  dose, route, frequency, duration, oral_dose_mEq, scheduled_time) are typically
  `null` — and conversely must be populated when an active plan applies.
- A `nullable: true` object field (e.g. `latest_final`) is `null` when its
  precondition is false (e.g. `lab_found` false → `latest_final` null), and
  required otherwise (`required_when`).

## Numeric precision
Templates state per-field precision: "one decimal place", "two decimal places",
"whole hours", "integer days". Round the chart value to that precision in the
output. A potassium of 3.24 → `3.2`; a risk score of 0.837 → `0.84`; a follow-up
of 1.5 days → use the unit the field demands (hours vs days) and round to whole.

## List ordering — three flavors
1. **Set-normalized** ("No semantic ordering; evaluators normalize as a set" /
   "Order is not meaningful") — emit each selected value once; order is free but
   deduplication is required.
2. **Sort by time then id** ("Sort … by effective_time ascending, then
   observation_id ascending") — sort explicitly on those keys.
3. **Semantic order** ("case identifier first, then clinical source identifiers",
   "descending relevance", "Sort by clinical action sequence") — apply that
   specific ordering. For "descending relevance," lead with the most decisive
   evidence (the observation driving the decision, then supporting labs, then
   case/registry IDs).

## Red flags present vs absent
Some templates carry both `red_flags` (present) and `absent_red_flags`. The
absent list enumerates protocol-defined red flags that the chart does **not**
support — assert absence only for flags the protocol defines and the chart
screened for. Do not list a flag as absent if the chart never assessed it.
Safety-check booleans (e.g. `no_false_loc`, `no_false_vomiting`,
`no_false_photophobia`) back this up: set `true` when you did not falsely assert
that finding.

## Safety-check booleans (absence-of-unsupported-claim)
Booleans named `no_<claim>` assert your response avoids a specific unsupported
claim (`no_normal_cxr_claim`, `no_clear_lungs_claim`, `no_false_loc`,
`no_penicillin_or_sulfa`). Set `true` when your reasoning genuinely avoids it;
`false` (or reconsider your reasoning) if your output would imply the claim
without chart support. "All `true`" is not automatically correct — it is correct
only when each claim is genuinely absent from your reasoning.

## Allergy / contraindication screens
- Map chart allergens to the template's `avoid_allergens` classes via the
  protocol's allergy rule. Active status only; ignore inactive allergens.
- Contraindication objects (dialysis dependence, arrhythmia symptoms, eGFR,
  etc.) gate plans: a positive contraindication often flips the plan to
  `hold_due_to_contraindication` or `urgent_escalation` and nulls the routine
  medication fields.

## Evidence IDs
- Only stable identifiers that exist in the runtime.
- Respect the ordering rule (set-normalized, case-id-first, or descending
  relevance).
- Include the identifiers your decision actually rested on (the decisive
  observation, relevant labs/imaging/registry, the case, sometimes the
  protocol). Don't pad with unrelated IDs.

## Output hygiene
- Exactly one JSON object. No markdown fences, no comments (`//` or `/* */`),
  no trailing prose, no extra top-level keys.
- Match the template's `required_top_level_keys` exactly. If the template says
  "additional properties ignored unless they conflict," still omit extras —
  cleaner and avoids conflicts.
