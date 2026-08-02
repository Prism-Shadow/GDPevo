---
name: investigation-hub-production-gap-analysis
description: >-
  Produce a structured-JSON litigation e-discovery gap / production-readiness /
  remediation analysis for an investigation matter whose evidence lives in a
  read-only "Investigation Review Hub". Use when a task gives a matter_id, points
  at a review hub as the source of record, and asks for a JSON object conforming
  to a provided answer_template.json (critical findings, category statuses,
  retention/communication gaps, privilege corrections, top risks, metrics,
  prioritized actions, etc.). Covers subpoena/grand-jury/SEC/DOJ production
  reviews across custodian collection, preservation/retention loss, privilege
  logging, third-party waiver, and QC/responsiveness coding.
---

# Investigation Review Hub — production gap analysis

These tasks share one shape: a legal team wants a normalized JSON assessment of
what is wrong with a rolling production for one matter. The prose, the client
name, and the output field names change; the underlying data model and the
reasoning do not. Solve it by pulling the matter's records from the hub,
separating the few **material** records from a large field of look‑alike
**distractors**, deriving exact counts, classifying each with domain rules, and
emitting JSON that conforms exactly to the task's `answer_template.json`.

## What the task hands you

- A **prompt** naming a `matter_id` and the deliverable.
- `input/payloads/answer_template.json` — the output contract: required top‑level
  keys, per‑item required keys, the allowed **enum** values for every field,
  **ordering rules**, and numeric precision. This defines the answer; it does not
  contain it.
- `input/payloads/<context>.json` (e.g. `request_context` / `review_scope` /
  `matter_context`) — client‑facing labels and category titles **only**. Never a
  source of evidence facts; use it just for the matter_id and category codes.
- An **environment access file** describing a read‑only hub (per‑record read
  endpoints plus a read‑only SQL query endpoint) and the credentials to send.
  Read that file at task time to learn the base location and credential to use —
  do not assume any particular address or key.

## Hard rules

- **The hub is the only source of business evidence.** Do not read local env
  files, database files, seeds, generated data, manifests, setup/source code, or
  any answer/evaluation file — the prompts forbid it and those are traps.
- **Filter every query by your `matter_id`.** The hub holds many matters; issue
  labels and record shapes repeat across them, so unfiltered data is misleading.
- **Return only the JSON object** the template specifies — no prose around it.

## Procedure

### 1. Load the schema and pull the matter
Learn the hub's data model, then pull every relevant table filtered to your
matter. See `references/hub-data-model.md` for the tables and the columns that
matter. Prefer the SQL query endpoint for one bulk pull per table; save the raw
rows and work from them. Always also pull the matter row itself to get the
`hold_date` — several classifications depend on comparing dates to it.

### 2. Identify the MATERIAL set — the crux of the task
Most rows are realistic noise. The escalated, material records are few. Find them
with three mutually‑reinforcing signals (see
`references/material-vs-distractor.md`):

1. **`remediation_actions` is authoritative.** Keep only the *non‑noise* actions
   (drop any whose id/description marks it as operational noise, and any whose
   target is a bare category code rather than a record id). Each remaining
   action's `target_ref` is a material **anchor record**.
2. **Distinctive IDs.** Material records use a short, human token in the id
   (e.g. `SRC-<TOKEN>-<NAME>`, `PRIV-<TOKEN>-<TAG>`, `QC-<TOKEN>-<TAG>`,
   `RET-<TOKEN>-<TAG>`). Distractors use long sequential ids
   (`…-<MATTERSLUG>-0NN`) and carry give‑away notes (see the reference).
3. **Cross‑check.** The set of non‑noise action targets should equal the set of
   distinctive‑id records. If they agree, that is your material set. Everything
   else is out — even rows whose `status` looks alarming (their notes will say
   "no production‑impacting issue escalated", "remediated by archive collection",
   "ordinary review variance", etc.).

### 3. Derive per‑record facts and counts
Counts come straight from the anchor records — never estimate:
- privilege entries → `withheld_count`, `logged_count`, and
  `unlogged = withheld − logged`.
- qc findings → `doc_count`; note the coding issue (miscoded responsive vs
  miscoded privileged vs zero‑claim contradiction) and its `affected_category`.
- retention events → `volume_count`/`volume_unit`; split destroyed volume by
  pre‑hold vs post‑hold using `event_date` vs the matter `hold_date`.
- custodian sources → count lost / not‑collected sources, keyed by source type
  (personal device/email/messaging, board site, archive, …).
- Roll these up into the template's named metric fields exactly. Booleans like
  `production_ready` / `rolling_production_ready` are **false** whenever any open
  gap remains.

### 4. Classify with domain rules
See `references/classification-and-enum-mapping.md`. Highlights that generalize:
- **Severity/risk is domain‑driven, not copied from the action's severity:**
  a policy‑compliant destruction *before* the hold is **low**; a loss *after* the
  hold (spoliation) is **high**; a large unlogged‑privilege or zero‑claim
  contradiction is **high/critical**.
- **Route each record to the right output section by its nature:** records/box
  retention losses vs messaging‑system losses; privilege corrections vs QC/coding
  issues; sources that are *gaps* (lost / not collected) go in the risk/finding
  lists, while sources that are *available archives or retained systems* go in the
  "available/retained sources" list and are a remediation path, not a risk.
- A category's status/impact summarizes all material records touching it; when the
  template offers a "multiple blockers"/"mixed" value and a category has more than
  one kind of issue, prefer it, otherwise use the single dominant issue.

### 5. Normalize to the template's enums
The hub's raw vocabulary is not the template's. For every enum field, map the raw
value to the closest allowed enum member *by meaning* (e.g. a system‑loss becomes
an active‑system‑loss; an incomplete log becomes a log‑gap / supplement‑log;
an over‑designation becomes a downgrade/recode; a forward to an outsider becomes a
third‑party waiver / waiver‑assessment). Derive `action_type` from the underlying
**issue**, not from the hub action's verb. For `owner`, normalize the hub action's
owner string to snake_case and use it if an enum member matches, otherwise map to
the nearest enum member. The reference lists the recurring mappings.

### 6. Assemble and order the JSON
- Include exactly the `required_top_level_keys`; give every list item exactly its
  `item_required_keys`.
- Apply every **ordering rule** (sort findings/events by id, categories by code,
  actions by priority/rank; sort category‑code lists ascending and uppercase).
- Use whole integers for all counts; use the template's null/`not_applicable`
  conventions when a field does not apply.
- Anchor list items on the hub's own stable record ids.
- Emit the single JSON object and nothing else.

## Checklist before finishing
- [ ] Every query filtered to the matter_id; no local/DB/source files touched.
- [ ] Material set = non‑noise remediation targets = distinctive‑id records; all
      sequential‑id / "noise‑note" distractors excluded.
- [ ] Counts taken verbatim from anchor records; `unlogged = withheld − logged`;
      box volumes split pre/post hold.
- [ ] Pre‑hold loss = low risk, post‑hold loss = high risk applied.
- [ ] Each record routed to the correct output section (gap lists vs
      available/retained‑source list; retention vs communication; privilege vs QC).
- [ ] Every field value is a member of that field's template enum.
- [ ] Ordering, required keys, integer precision, uppercase‑sorted category codes.
- [ ] Output is only the JSON object conforming to `answer_template.json`.
