---
name: investigation-review-gap-dashboard
description: >-
  Produce a schema-conforming JSON e-discovery / litigation-hold gap and remediation
  dashboard for a legal matter by querying a read-only "Investigation Review Hub" API.
  Use when a task gives you a matter context payload plus an answer_template.json and
  asks for a structured JSON gap analysis, production-readiness review, retention/hold
  gap review, or cross-system remediation dashboard sourced from a review hub over the
  network (grand jury / SEC / DOJ subpoena response work). Triggers: "Investigation
  Review Hub", "production gap analysis", "remediation dashboard", "retention gap
  review", "production readiness", answer_template.json with matter_id + findings/risks
  + category coverage + metrics + prioritized actions.
---

# Investigation Review Hub — Gap & Remediation Dashboard

## What this task is

You are given a legal matter (a grand jury / SEC / DOJ subpoena response) and must return
**exactly one JSON object** that summarizes the *material* production gaps, preservation
failures, privilege problems, and QC defects for that matter, plus rollup metrics and a
prioritized remediation action plan. All business facts come from a running **Investigation
Review Hub** you reach over the network — never from local files.

Every run varies (different matter, different output schema), but the shape is always:

- **Findings list** — one row per material gap/defect (may be called `critical_findings`,
  `top_risks`, `issue_ledger`, `retention_events`+`communication_gaps`, …).
- **Category coverage** — one row per subpoena/request category with a non-complete status.
- **Available/retained sources** — archives or sources that still limit the loss (may be empty).
- **Metrics** — a fixed object of integer counters + a readiness boolean.
- **Action plan** — prioritized, owner-assigned remediation steps.

The hub deliberately buries a handful of **material "story" records** inside **many realistic
distractors**. The entire difficulty of the task is *separating signal from noise*, then
*normalizing* the signal into the exact enums/keys the answer template demands. Read
`reference/materiality_and_mapping.md` before you start classifying records.

## Inputs you will have

- `input/prompt.txt` — the client ask (which matter, what deliverable).
- `input/payloads/<context>.json` — matter context: the `matter_id`, category labels, and often
  the base URL placeholder + API key header. (Filename varies: `request_context.json`,
  `review_scope.json`, `matter_context.json`, …) Use it for the matter id, category codes/titles,
  and credentials **only** — it never contains the hub evidence.
- `input/payloads/answer_template.json` — **the contract for your output**: required top-level
  keys, per-item required keys, ordering rules, numeric precision, and the exact **enum choices**
  for every field. This file (not this skill, and not any example) is the source of truth for
  field names and allowed values. Re-read it for every run; keys and enums change per matter.
- `environment_access.md` (repo root) — how to reach the running hub over the network: the
  `GDPEVO_ENV_BASE_URL`, the required `X-API-Key`, and the allowed endpoints.

## Guardrails (do this, not that)

- **Only source of business evidence = the hub over the network.** Do NOT read local
  environment source files, database/seed files, generated manifests, hidden notes, other tasks'
  inputs, or any answer/evaluation files. Use `environment_access.md` *only* to obtain the base URL
  and credentials.
- Read the base URL + API key from `environment_access.md` / the matter context payload for the
  current run; do not assume. (In the environment observed while building this skill the base URL
  was `http://task-env:9017/` and the header was `X-API-Key: review-key-017`.)
- The hub is read-only; the SQL endpoint permits `SELECT` only.
- Output **one JSON object and nothing else** — no prose, no code fences, no trailing commentary.
- Use **stable hub record IDs exactly as they appear** (source_id, event_id, entry_id, finding_id,
  doc_id, action_id, category_code). Never invent IDs for evidence; the only IDs you may synthesize
  are action_ids in the action plan when the template shows synthetic keys (e.g. `ACT-<M>-001`).

## Workflow

1. **Read the three inputs.** From the prompt + context payload get the `matter_id` and the
   category code family. From `answer_template.json` extract: `required_top_level_keys`, each
   list's `item_required_keys`, the `ordering_rules`, `numeric_precision`, and every `enums` block.
   Keep the enum lists open in front of you — every field value you emit must be one of them.

2. **Reach the hub.** Get base URL + key from `environment_access.md`. Confirm the matter exists:
   `GET /api/matters?matter_id=<M>` (note `hold_date`, `agency`, `investigation_type`). The
   endpoints and the SQL data model are in `reference/hub_api.md`. `scripts/pull_matter.sh` dumps
   every table for one matter and pre-flags material candidates — run it first.

3. **Find the material anchor records** (the core step — see `reference/materiality_and_mapping.md`):
   - Start from `remediation_actions` for the matter, **excluding NOISE rows** (action_id contains
     `NOISE`, description == "Routine action included as realistic operational noise.", or
     `target_ref` is a bare category code). The remaining `target_ref`s are the authoritative
     material anchors (retention events, custodian sources, privilege entries, QC findings).
   - This set is *necessary but not complete.* Also sweep every table for records that (a) carry a
     **descriptive slug ID** (not a sequential `TYPE-MATTERTOKEN-NNN` id) **and** (b) have a note/
     summary stating a **concrete, quantified defect**, **and** (c) a material issue type/tag.
     In particular, `documents/search` responsiveness-miscodes (`issue_tags` contains
     `miscoded_nonresponsive`, coded nonresponsive but responsive) are material even when no
     remediation action or QC finding points at them.
   - **Discard distractors:** sequential ids with boilerplate hedge notes ("ordinary review
     variance", "not immediately remediated", "not one of the stable exception records", "realistic
     operational noise", "included to create similar labels", "remediated by archive collection", …).
     Distractors reuse the same `issue_type` values as real records — issue_type alone never proves
     materiality; the slug-id + concrete-note + cross-reference test does.
   - Pull the **linked records** for each anchor: a QC finding's `source_ref` → its review document;
     a privilege `incomplete_log` entry → its withheld/logged counts; a retention note may name
     specific unrecovered volumes or linked docs. Read note text to extract the *material* count
     (e.g. a "X of Y withheld docs logged" note → Y withheld / X logged / (Y−X) unlogged; a
     "N deleted, R recovered, K unrecovered" note → material volume = K unrecovered).

4. **Classify & normalize** each material record into the template's enums (issue_type, severity/
   risk_level, status, source_status, production_impact, category_status, action_type, owner,
   priority). Use the mapping tables in `reference/materiality_and_mapping.md`. When the template
   lists an enum, pick the closest allowed value — never emit a value outside the enum.

5. **Build category coverage.** For each request category touched by ≥1 material finding, emit its
   status (preservation loss / collection gap / privilege log gap / responsiveness gap / archive
   available / …), production impact, the sorted list of supporting record IDs, a recommended
   action, and (if required) an open-issue count. Sort category code lists ascending.

6. **Compute metrics.** The `metrics` object's required keys differ per template — compute each one
   literally from your material set (e.g. unlogged = withheld − logged; box counts split pre-hold vs
   post-hold; counts of lost personal devices, uncollected sources, available archives, miscoded
   docs, affected categories; the `*_ready` / `production_ready` boolean is `false` whenever any
   open material gap remains). Every count is a whole integer; use 0 (not null) when not applicable.

7. **Build the prioritized action plan.** Synthesize one action per material finding (or per
   related group). Rank by legal exposure and irreversibility, then map action→owner→priority from
   the template enums (rubric in `reference/materiality_and_mapping.md`). Roughly: spoliation /
   post-hold destruction / lost sources requiring disclosure to the government come first (P0),
   then privilege waivers, privilege-log supplementation and privilege recodes, confirmed
   responsiveness recodes, personal-source collection, and archive search (P1), then over-
   designation downgrades and routine cleanup (P2/P3). Do **not** copy the hub's own
   `remediation_actions` owners/action_types verbatim — re-map them to the template's enums.

8. **Order, validate, emit.** Apply every `ordering_rules` entry (sort findings/categories/actions
   by the specified key; sort every category-code list ascending; sort every `source_refs`/
   `record_refs`/`issue_refs`/`target_refs` list ascending). Then run the checklist below and print
   the single JSON object.

## Output validation checklist

- Top-level keys == `required_top_level_keys` exactly (no extras, none missing). `matter_id` matches
  the hub.
- Every list item has all of its `item_required_keys`; every enum field holds an allowed value.
- All counts are integers (0, not null, when N/A); booleans are real booleans.
- All ordering rules applied; every id-list sorted ascending.
- Evidence IDs are verbatim hub IDs. No distractor records leaked into findings.
- Output is one JSON object, no prose, no code fence.

See `reference/hub_api.md` for endpoints + SQL schema and `reference/materiality_and_mapping.md`
for the signal/noise heuristics and the field→enum mapping and priority rubric.
