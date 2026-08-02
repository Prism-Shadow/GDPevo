# Field checklist & distractor catalog

Run this before emitting the JSON. It encodes the mistakes these tasks are built to
catch. None of it substitutes for the run's own template/protocol/record — those win
on any conflict.

## Pre-submission checklist

**Structure**
- [ ] Exactly the template's required top-level keys — no extras, none missing.
- [ ] One JSON object only; no markdown/comments/prose.
- [ ] Every constant field (task id, case id, any `expected_constant` /
      `required_value`) copied verbatim; patient id taken from the record.

**Types & values**
- [ ] Every enum value is spelled exactly as an allowed value (no paraphrases).
- [ ] Numbers honor stated precision (decimal places / integer-only).
- [ ] `null` used only where the field permits it; required-when conditions met
      (e.g. a "latest/current" object populated only when the corresponding
      "found/needed" flag is true).
- [ ] Booleans reflect the record, not an assumption.

**Timestamps**
- [ ] ISO-8601 UTC with trailing `Z`.
- [ ] Window boundaries applied with the stated inclusivity (often inclusive start,
      exclusive end).
- [ ] Relative times resolved concretely and exactly (e.g. "next morning" → next
      calendar day, clinic morning hour).

**Lists / sets**
- [ ] Each member is clearly supported by the record *now*; no plausible-but-unstated
      extras.
- [ ] No supported member omitted.
- [ ] Ordering rule applied where the field states one; duplicates removed.

**Evidence / provenance fields**
- [ ] Only ids/keys actually used as evidence; ordering rule honored (e.g. case id
      first, or descending relevance).
- [ ] "Chart facts" vs "member-disclosed / needs-disclosure" split correctly:
      objective, documented values are chart facts; self-reported barriers/goals are
      disclosure-dependent. A value that is *absent from the record* is not a chart
      fact.

**Safety checks**
- [ ] Each safety boolean is `true` only if your answer genuinely honors the guard
      (no contraindicated class prescribed; no "normal/clear" claim contradicted by
      the record; no assertion about something never assessed).

## Filtering order (apply in this sequence)

1. **Patient** — drop records whose patient id ≠ the target patient. These are
   out-of-scope, not in-scope distractors.
2. **Status** — keep only protocol-authoritative statuses (usually `final`).
3. **Code** — keep only the exact controlled code(s) for the target concept.
4. **Time window** — keep only records inside the window (mind boundary
   inclusivity).
5. **Select** — "latest" = max `effective_time` among survivors; tie-break per the
   ordering rule.

When a field asks for the distractors you *excluded*, include only the in-scope
records that failed a filter for the reason(s) that field names (commonly date,
code, or status). Do not list out-of-scope (wrong-patient) records there unless the
field explicitly says to.

## Common distractor catalog

- **Wrong patient:** a target-code, final record attached to the case but under a
  different patient id.
- **Wrong status:** a preliminary/entered-in-error/canceled result that looks like
  the value you want.
- **Wrong code / look-alike:** whole-blood vs serum form of the same analyte; a
  neighboring analyte from the same panel; the same test in a different specimen.
- **Out-of-window:** a valid result dated just before/after the window.
- **Superseded / distractor cases:** other cases of the same type; always resolve
  the exact target case id from the prompt.
- **Over-specific vs generic enum pairs:** when two enum values both seem to fit
  (e.g. a generic condition code and a more specific variant that also encodes the
  precipitating event), pick the one the data most precisely supports and do not
  list both.
- **Absent modality treated as present:** a stat/anchor the template lists but that
  the record never contains — leave it out (or null where permitted); do not fill it
  from assumption.
- **Presenting symptom vs red flag:** a symptom that is the reason for the visit is
  not automatically a current "red flag"; place it where the template's semantics
  put it (often a return-precaution / monitoring list).
