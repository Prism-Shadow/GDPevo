# Field conventions & distractor patterns

Companion to `SKILL.md`. Generic conventions observed across EHR quality-governance packet tasks.
No task-specific values — apply the patterns to whatever records the environment returns.

## Distractor patterns (recognize and handle by field purpose)

| Pattern | What it looks like | Handling |
|---|---|---|
| **Name collision** | Two patients share a display name but differ in DOB / insurance / address | Different people. Not a duplicate and not an insurance anomaly. |
| **Placeholder normalized_key** | A real drug/allergy carries a generic key (e.g. `baseline_med`, `baseline_allergy`), sometimes with an implausible route | Keep it in a *comprehensive active* list; drop it from a *relevance-filtered* list. |
| **Routine document** | `chart_summary` / `ehr_export` docs | Excluded from identity/continuity evidence → distractor bucket; name the excluded type. |
| **Inactive record** | `status` = `inactive` / `entered-in-error` | Never in an active union; belongs in the excluded/distractor bucket. |
| **Foreign / test audit log** | audit entry for another patient, an unrelated merge, or a test-tagged event | Not case evidence → distractor bucket. |
| **Soft coordination note** | "confirm sulfa allergy before letter" while the record is already complete | Does not make a complete record incomplete; do not add follow-up/blockers for it. |
| **Trivial demographic conflict** | address abbreviation ("St" vs "Street"), name nickname/variant | Record as a conflict signal, but it does not downgrade a merge disposition. |
| **Symptom-vs-diagnosis narrative** | narrative "knee pain" against a specific knee OA/meniscus code, same region + side | Not a mismatch; only flag when region or side actually differs, or condition is genuinely different. |
| **Comorbidity in a referral** | an active hypertension/diabetes condition on a cardiology/ortho referral | `referral_relevant = false` (only the referral reason + presenting symptom are relevant), even if a related medication is highlighted. |
| **Latest-but-irrelevant encounter** | the most recent visit is for an unrelated problem | Handoff/recent-encounter selection is by relevance to the packet's reason, not pure recency. |

## Cross-cutting conventions

- **Enums are closed sets.** Only emit values listed in the template's `allowed_values`/enum. When a
  business signal has no matching enum member (e.g. "same family name"), it isn't reportable.
- **`required_value` fields** (like a fixed `task_id`) must be set exactly.
- **Nullable types** (`["string","null"]`) — emit `null` when there is genuinely no value (e.g. no
  merge target on a hold), not an empty string.
- **Ordering keywords**: "sorted alphabetically" / "ascending" / "by code" / "by id" → literal string
  sort on that key. "newest → oldest" → descending by date. `set_semantics: true` → order is ignored,
  but membership must be exact.
- **Derived counts** (audit `summary_counts`, mismatch/queue counts) must be computed from the arrays
  you actually emit — keep them internally consistent.

## Evidence-linking conventions

- Link each derived flag/finding to the record(s) that justify it (condition/medication
  `normalized_key`s, encounter ids). Prefer the direct source of the finding:
  - condition/med/allergy-derived flags → their condition/medication keys;
  - note-derived requirements → the specific encounter carrying the note.
- Validate identity/coding claims against primary records (demographics, the ICD reference, the
  service-code reference, the provider directory) rather than trusting a preview/summary blindly;
  when a preview and the live endpoints disagree, the live patient endpoints are authoritative.

## Disposition / readiness mental model

Think of two independent axes and let the template's enums express them:

1. **Substance of conflicts/blockers**: none → trivial/normalizable → substantive → disqualifying.
2. **Presence of non-blocking flags/notes**: clean → flagged-but-ready → held-for-review → blocked.

Trivial/normalizable differences and soft notes keep you on the "clean/ready" side; substantive
conflicts (opposite laterality, different identity fields) or missing required artifacts move you to
"review/hold" or "blocked". Only genuinely disqualifying evidence reaches "do-not-merge" / "not-ready".
