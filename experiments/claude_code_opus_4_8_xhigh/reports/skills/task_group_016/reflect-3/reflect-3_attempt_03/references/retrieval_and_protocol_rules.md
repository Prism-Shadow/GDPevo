# Retrieval & protocol-application rules

Detailed rules behind Steps 4–5 of `SKILL.md`. Read the actual thresholds, codes,
and formulas from the task's protocol body at runtime; the patterns below are what
to look for, not fixed values.

## Endpoint shape (read-only)

The runtime is a FHIR-like synthetic clinic exposed over read-only GET endpoints.
Typical shape (confirm names against the run's environment-access file):

- Collections: patients, cases, observations, medications, allergies, problems,
  imaging, care-registry, sdoh, protocols.
- Detail: `.../api/cases/{case_id}` and `.../api/protocols/{protocol_id}`.
- The **case-detail bundle** is the workhorse — it already joins patient, allergies,
  problems, medications, observations, imaging, `findings`, `care_registry`, `sdoh`
  for that case. Start there; fall back to collection endpoints only if you need
  something the bundle omits.
- Some POST endpoints may require a credential you were not issued and return 401.
  Do not rely on them; the read-only GETs are sufficient.

Never mutate state or "place an order." Read only.

## The four-filter eligibility gate for observations/results

Apply ALL four before an observation can be used for a protocol decision or listed
as a "match":

1. **Status** — keep only statuses the protocol calls authoritative (usually
   `final`). Explicitly drop `preliminary`, `entered-in-error`, `canceled`.
2. **Code** — must equal the target code exactly. Watch for near-miss distractors:
   a different specimen (serum vs whole-blood) or a neighboring analyte is a
   *different* code even if the display name looks similar. Use the protocol's
   `controlled_codes` map to resolve the intended code.
3. **Patient** — `patient_id` must equal the target patient. A record carrying the
   case id but a **different patient id** is a data-quality distractor. It belongs
   to neither the matched list nor the excluded-distractor list — it is simply out
   of the review set.
4. **Window** — if a time window applies, include only records with
   `start <= effective_time < end` (inclusive start, **exclusive** end). Records
   just outside are date-excluded.

"Latest"/"current" = the latest **eligible** record (all four filters passed) by
`effective_time`. Distractors are specifically engineered to be more recent, more
extreme, or same-month — the filters, not recency alone, decide eligibility.

## Matched vs excluded (retrieval-gate tasks)

- **matched** = every record passing all four filters. Sort as the template says
  (commonly `effective_time` ascending, then `observation_id` ascending).
- **excluded distractors** = records that are relevant to *this patient's* review
  but fail on one of the **enumerated** reasons the template names (typically date,
  code, or status). If the template's exclusion reasons are date/code/status, a
  **wrong-patient** record is NOT an "excluded" item — leave it out of both lists.
- `lab_found` / "any qualifying result" booleans key off the matched set only.
- The downstream **gate enum** keys off the latest matched (eligible) value and its
  interpretation (e.g. normal → "satisfies" branch; low → "repletion" branch;
  critical → "urgent" branch; none → "no result in window"). A follow-up/repeat is
  typically **not** recommended when the gate is already satisfied by a normal
  result (recommended=false, scheduled_time=null).

## Protocol branch evaluation

1. **Escalation/urgent branch first.** Collect the protocol's trigger set (vital
   thresholds, a critical value cutoff, high-risk conditions, red-flag symptoms).
   Evaluate each against the filtered data. If any fires → the escalation/urgent
   disposition and its actions. If none fire → the routine/outpatient branch.
2. **Assessment label via support criteria.** If the protocol lists criteria that
   *support* a given assessment and the case satisfies them, pick that assessment
   enum. This categorical is the highest-weighted field — resolve it deliberately
   and let disposition/imaging/tier follow consistently.
3. **Formulas.** Apply exactly as written (e.g. amount per increment below a target,
   then round to the specified step). Feed the eligible latest value in.
4. **Allergy screen.** Only `active` allergies count. Avoid the implicated classes;
   choose a compatible regimen; report avoided classes as a set. Ignore `inactive`
   allergy entries.
5. **Risk/eligibility tiers.** Compare the registry/observed score to the protocol
   cutoff for the tier; count how many complex-care/eligibility triggers are met to
   choose the program/routing enum.

## Consistency invariants to self-check
- Disposition, imaging recommendation, and stabilization/urgent actions all agree
  with which branch fired.
- Safety-check booleans agree with the plan and the imaging/exam findings.
- Any medication fields are internally consistent (strategy ↔ drug ↔ route ↔
  avoided-allergen set) and compatible with active allergies.
- Numeric anchors echo the exact filtered source values at the required precision.
