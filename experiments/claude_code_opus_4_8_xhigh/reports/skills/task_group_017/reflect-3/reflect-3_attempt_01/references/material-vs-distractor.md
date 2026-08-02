# Separating material records from distractors

Each matter contains a handful of genuinely escalated defects surrounded by many
realistic look‑alikes. Getting the **set** right matters more than any single
enum: an answer built on the wrong records cannot match. Use all three signals
and require them to agree.

## Signal 1 — `remediation_actions` (authoritative)
The escalated, material work is exactly the set of **non‑noise** remediation
actions. Drop an action when:
- its `action_id` (or `description`) marks it as operational noise
  (ids ending in a `NOISE` segment; descriptions like "Routine action included as
  realistic operational noise"), **or**
- its `target_ref` is a bare category code or generic label rather than a
  specific record id.

Every remaining action targets one material **anchor record** by its `target_ref`,
and it also supplies that item's `priority`, `owner`, and `due_days`.

## Signal 2 — distinctive record ids
Material anchor records carry a short, human token in the id — a person, a
system, or a defect name — e.g. `SRC-<TOKEN>-<NAME>`, `PRIV-<TOKEN>-<TAG>`,
`QC-<TOKEN>-<TAG>`, `RET-<TOKEN>-<TAG>`.

Distractors use a long, sequential, slug‑based form, e.g.
`SRC-<MATTERSLUG>-0NN`, `PRIV-<MATTERSLUG>-00N`, `RET-<MATTERSLUG>-00N`.

## Signal 3 — give‑away notes on distractors
Distractor rows almost always explain, in their `notes`, why they are not
material. Treat any of these as "exclude" (a row can *look* alarming by status
yet still be noise):
- "included to create similar labels across matters"
- "no production‑impacting issue has been escalated yet"
- "review team marked this item for follow‑up but not immediate remediation"
- "privilege sample has ordinary review variance"
- "review manager requested re‑sampling before escalation"
- "potential issue was remediated by archive collection"
- "retention entry is relevant only after comparing hold date and policy period"
  (i.e. it turns out compliant)
- "entry creates a similar label but has no unresolved production impact"
- "source map entry has minor metadata normalization issues"
- "collection status differs between custodian tracker and vendor load report"
- "requires matter‑level filtering because similar issue labels appear across
  matters"

## The rule
Material set = { non‑noise remediation targets } = { distinctive‑id records }.
When those two sets agree, use them and exclude everything else. If a distinctive
record has no remediation action (or vice‑versa), re‑examine it, but the default
is that both signals hold together.

## Watch‑outs
- Look‑alike incomplete‑log / not‑collected / should‑exist‑missing rows exist with
  sequential ids purely as noise; the metric fields that say "from selected
  … blockers only" mean *the material anchor only*, not the whole table.
- The same `issue_tags` (collection_gap, scope_exception, personal_device) appear
  on both material and noise rows — tags alone do not make a row material.
