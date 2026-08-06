# Pre-submission checklist

Run through this before finalizing the JSON.

- [ ] **Schema match.** Every required top-level key from the template is
      present; no extra top-level keys. Field names and nesting match exactly.
- [ ] **Enums.** Every enum-typed field holds one of the template's allowed
      values, spelled exactly. Any `required_value` is emitted verbatim.
- [ ] **Types.** Booleans are booleans, integers are integers, `null` is used
      only where the schema permits it, dates are `YYYY-MM-DD`.
- [ ] **Active lists.** Built from `status == "active"` records only, keyed by
      `normalized_key`, unioned across in-scope patients, deduped, sorted.
- [ ] **Distractors excluded.** Inactive/legacy records, namesake patients,
      generic chart_summary/ehr_export docs, other patients' audit rows, and
      off-topic/stale encounters are excluded (and placed in the excluded lists
      when the template has them).
- [ ] **Structured-over-prose.** Any "confirm/verify" note or preview was
      overridden by the actual structured record when the record is
      complete/valid.
- [ ] **Codes validated.** Each ICD-10/service code was looked up; chapter,
      laterality, expected terms, and patient-evidence match were computed from
      the directory, not guessed.
- [ ] **Providers filled.** Specialist/recipient chosen by service line; full
      contact block copied from the provider directory; PCP from the patient
      record.
- [ ] **Ordering.** Every list obeys its stated order (ascending id/code,
      newest→oldest, alphabetical). Set-semantics lists have exact membership.
- [ ] **Counts consistent.** Any summary counts equal the lengths/derivations of
      the arrays they summarize.
- [ ] **Output is JSON only** — no surrounding prose, no comments.
