# Pre-submission checklist

Run through this before returning the JSON. Every "no" is a likely lost point.

## Schema conformance
- [ ] Output is a single JSON object — no markdown fences, comments, or prose.
- [ ] Exactly the template's required top-level keys are present; no extra
      top-level keys.
- [ ] Every enum value is drawn from that field's `allowed_values` (exact
      spelling); no invented values.
- [ ] Types match: string vs number vs integer vs boolean; `*_or_null` fields
      use `null` only where permitted; lists are lists, objects are objects.
- [ ] Pinned constants (task id, case id) match what the template requires.
- [ ] Nested objects include all their required sub-keys.

## Numbers & formats
- [ ] Numeric precision honored (e.g. one decimal where specified); units as
      requested.
- [ ] Timestamps are ISO-8601 UTC with trailing `Z`.
- [ ] Composite strings match the specified format (e.g. `systolic/diastolic`).
- [ ] Derived times follow the protocol's timing rule, anchored on the case's
      current/clock time.

## Filtering discipline (distractor defense)
- [ ] Every observation/record used belongs to the **target patient id**.
      Wrong-patient rows appear nowhere in the answer.
- [ ] Only authoritative-status (final) records were used for gated decisions.
- [ ] Codes match the exact controlled code for the concept (right analyte /
      specimen), not a look-alike code.
- [ ] Window bounds applied precisely (inclusive start / exclusive end unless
      the template says otherwise).
- [ ] "Latest / most recent" was taken from the fully-filtered set, not the raw
      list.

## Clinical mapping
- [ ] Urgent/override branch checked before the routine branch.
- [ ] Medication choice avoids the patient's **active** allergen classes and is
      protocol-consistent; avoided classes are listed.
- [ ] Dose/threshold math applied per the protocol's formula and rounding rule,
      using the filtered latest eligible value.

## Conservative assertion
- [ ] Danger signs marked present only with positive evidence; marked absent
      only when explicitly documented/assessed as absent; unmentioned signs are
      in neither list.
- [ ] No unsupported "normal"/"negative"/"clear" claim; safety booleans reflect
      that such claims were avoided.
- [ ] List fields contain only well-supported members — no speculative padding.

## Evidence & provenance
- [ ] Evidence identifiers actually support the stated decisions and follow the
      required ordering (e.g. case id first).
- [ ] No identifier cited for data that is absent/never measured.
- [ ] Where provenance is split, chart-measured facts and member/patient-
      reported facts are in the correct groups.
