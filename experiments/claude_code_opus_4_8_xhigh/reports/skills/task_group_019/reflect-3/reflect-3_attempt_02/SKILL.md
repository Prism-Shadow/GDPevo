---
name: licensing-review-decisions
description: >-
  Produce a strictly template-conformant JSON decision for a state
  licensing-review task (contractor application-batch eligibility, restricted
  liquor-license staff package, or alcohol renewal manual-review queue) driven
  by records in a shared licensing data environment. Use when a prompt casts you
  as a licensing/renewal examiner reviewing target ids and points you at a
  policy/rules table plus per-domain record tables, and asks for JSON matching
  an answer_template. Covers how to read the template, gather complete data,
  apply the governing policies, separate signal from distractors, and roll up a
  consistent summary.
---

# Licensing-review decisions

These tasks give you a role (licensing examiner / renewal unit), a set of
**target ids**, a policy/rules table, several record tables, and an
`answer_template.json`. Your job is to return **only** JSON that conforms to the
template. The domains differ but the working method is the same.

## 0. Orient before you compute

1. **Read `answer_template.json` first.** It is the contract. Extract for every
   field: exact key names, `allowed_values` (the enum vocabulary), list
   `ordering`, `required_length`, how to represent "none" (usually an empty
   list), and any date format. Output **only** those keys — no prose, markdown,
   citations, or extra keys.
2. **Enum vocabularies are per-task.** Two tasks in the same domain often use
   different code spellings/sets (e.g. `bond_cancelled` vs `no_active_bond`;
   `POLICE_MEMO_CONFLICTING` vs `police_memo_identity_note`). Always map your
   findings onto *this* template's `allowed_values`; never carry codes over from
   another task.
3. **Pull the target list and any review/boundary date** out of the prompt.
4. **Identify the domain** from the prompt + template (contractor eligibility /
   restricted liquor package / renewal review queue) and follow the matching
   checklist in `references/families.md`.

## 1. Gather complete, correct data

- Use the data services named in your environment-access notes. Query **filtered
  to the target ids** (and to any predecessor/related ids you need).
- **Bulk/list responses can be capped** (e.g. truncated at a row limit), which
  silently drops records for later target ids. Do not trust a raw list dump for
  completeness — retrieve per target id (or otherwise confirm every target and
  every one of its related rows is present) before deciding anything.
- Load the **policy/rules table** and index it by domain + class/family. It
  holds the numeric thresholds and the flags you reason with, plus a **prior /
  legacy baseline** row used for "did the current standard change the outcome"
  comparisons.

## 2. Signal vs. distractor (applies to every domain)

These datasets are deliberately salted with distractors. Trust structured
fields and dates; treat contradictory free text as noise.

- **Dates over status text.** Currency of coverage (bonds, insurance) is decided
  by comparing effective / expiration / cancel dates to the **review/boundary
  date**, not by a `status` string that may say "active" on an expired policy.
- **Authoritative code fields over notes.** Where a record has a coded field
  (e.g. an inspection `finding_code`, an evidence `status`, `verified_by_agency`,
  `severity`), that field decides; human-readable `notes`/`result` text is
  frequently inconsistent on purpose.
- **Only "open" items count.** Resolved/dismissed violations, closed incidents,
  expired/cancelled old bonds, and superseded rows are history, not findings.
- **Correspondence never resolves a structured deficiency.** A verified
  "registry corrected" letter does *not* clear a shortfall/suspension/violation
  computed from the records; it only feeds the "stale/unverified correspondence"
  summary. Do not let a letter override a records-based finding.
- **Reused identifiers are traps.** The same address string, or a "successor"
  license, or ids with a `-LATE`/late suffix, or rows under a *different* license
  number, are planted to lure a wrong match. Match on the **stable identifier**
  (exact license/application id) first.

## 3. Decision skeleton (contractor & liquor share this shape)

1. Look up the governing policy row for the item's class/type → thresholds &
   required attributes.
2. Compute each **finding/deficiency** from structured records + the review date.
3. Map each finding to its **remedy/action** code and to a **risk** contribution
   using this template's vocabulary.
4. Choose the **top-level determination/posture** from a fixed precedence
   (a hard block → deny; any open fixable issue → hold / request-follow-up;
   otherwise approve / issue).
5. Compute **policy-impact / same-premises / basis** flags by comparing against
   the *prior baseline* policy, not just the current one.
6. Build the **summary** as pure roll-ups of the per-item decisions (counts and
   id lists), and make it internally consistent (counts must equal the decisions
   you made). Sort every list exactly as the template dictates.

See `references/families.md` for the concrete per-field derivation of each
domain, and `references/distractors.md` for the full trap catalog.

## 4. Before returning

- Every target id present exactly once; list lengths match `required_length`.
- Each list sorted/deduped per the template; empty lists (not nulls) for "none".
- Summary counts and id lists are consistent with the per-item decisions.
- JSON only — the exact keys of the template, nothing else.
