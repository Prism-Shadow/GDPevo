---
name: investigation-review-gap-analysis
description: >-
  Produce a structured-JSON e-discovery gap / remediation dashboard for a legal-investigation
  matter by reading evidence from a running "Investigation Review Hub" API. Use when a task asks
  for a production gap analysis, retention/litigation-hold gap review, cross-system remediation
  dashboard, or production-readiness review for a subpoena/grand-jury/SEC/DOJ matter, and the
  answer must be a single JSON object conforming to a provided answer_template.json. Triggers:
  "Investigation Review Hub", "gap analysis", "remediation dashboard", "production readiness",
  "retention/litigation-hold gap", "privilege log gap", "custodian sources", matter IDs like
  MTR-*-GJ / MTR-*-SEC.
---

# Investigation Review Hub — gap / remediation dashboard

This skill turns raw records in a running **Investigation Review Hub** into the exact JSON
dashboard a task asks for. Every task in this family follows the same shape:

> Read the matter's evidence from the hub over the network → separate material issues from
> planted decoys → classify each issue with a fixed legal-review playbook → compute numeric
> metrics → emit **one** JSON object that conforms to the task's `answer_template.json`.

The output schema, enum names, category codes, and metric names **change per task**, so the
contract is always the `answer_template.json` shipped in that task's `input/payloads/`. The
*method* below is constant. Read the three reference files for depth:

- `references/hub_api.md` — endpoints, auth, the SQL endpoint, and every table's columns.
- `references/domain_playbook.md` — how each kind of evidence maps to issue type / severity /
  status / production impact / action / owner / priority, plus metric-derivation rules.
- `references/output_contract.md` — how to conform to any `answer_template.json` exactly.

## Procedure

### 1. Read the task, not just the prompt
Read `prompt.txt` and **every** file in the task's `input/payloads/`. From them extract:
- **`matter_id`** (e.g. `MTR-<NAME>-GJ` / `MTR-<NAME>-SEC`) — the filter for everything.
- **`answer_template.json`** — the output contract (required keys, enums, ordering, precision).
  Treat it as authoritative; never guess enum values or keys.
- Any `*context*.json` / `review_scope.json` — client-facing category labels, credentials,
  cutoff dates. These give *labels only*; the evidence must come from the hub.

### 2. Reach the hub (network only)
Read `environment_access.md` for the base URL (`GDPEVO_ENV_BASE_URL`) and the `X-API-Key`
credential, and send that header on every call. **Evidence comes only from the hub API.**
Do **not** read the hub's database/source/seed/manifest files, and never read
`train_answers/` or any evaluation/answer file. Sanity-check with `GET /` and `GET /api/schema`.

### 3. Pull all matter-scoped records
For the matter, pull rows from every table (filter by `matter_id`): `matters`,
`subpoena_categories`, `production_stats`, `custodian_sources`, `review_documents`,
`privilege_entries`, `qc_findings`, `retention_events`, `remediation_actions`. Prefer
`POST /api/query` with `{"sql": "..."}` for precise pulls; the REST `GET /api/*?matter_id=…`
endpoints also work. See `references/hub_api.md`.

### 4. Separate material issues from decoys — the key step
The hub seeds each matter with a **handful of genuinely material records** plus **many
plausible decoys**. Build your candidate set this way:

- **ID convention (primary signal).** Material/planted records use the matter's **short
  abbreviation** with a *descriptive* suffix (schematically `RET-<TOK>-<DESCRIPTOR>`,
  `SRC-<TOK>-<CUSTODIAN>-<DEVICE>`, `QC-<TOK>-<DEFECT>`, `PRIV-<TOK>-<DESCRIPTOR>`,
  `DOC-<TOK>-<DESCRIPTOR>` — descriptors are words, and may include a year or version like
  `…-2019` or `…-V3`, not a bare sequence number). **Decoys embed the FULL matter name + a
  zero-padded sequence number**
  (e.g. `PRIV-<FULLNAME>-001`, `RET-<FULLNAME>-007`) and carry routine/benign notes. Start from
  the short-token records as your material candidates.
- **Attribute corroboration.** Confirm materiality with the record's own fields, not the ID
  alone: retention `status` (`post_hold_loss`, `should_exist_missing`, `system_loss`,
  `auto_purged`, `post_hold_partial_recovery` are material; `available` and pre-hold
  policy-compliant destruction are not); custodian `status`/`issue_tags`
  (`lost`, `not_collected`, `available`+`archive_available` are material; `routine` is not);
  qc `issue_type` (`miscoded_*`, `zero_claim*` are material; `family_break`,
  `date_normalization`, `near_duplicate` are noise); privilege `issue_type`
  (`incomplete_log` with a real `withheld − logged` gap, `third_party_waiver`,
  `over_designated`); `production_stats.status` (`zero_claim_contradicted` is material); and doc
  `produced_status` (`not_produced`/`unrecovered`/miscoded-`withheld` are gaps — already
  `produced` docs are **not** a gap even if responsive/interesting).
- **Ignore the hub's own remediation_actions attributes.** `remediation_actions.target_ref`
  can point at material records, but its `owner` / `priority` / `action_type` are deliberately
  wrong and its `*-NOISE-*` / bare-category rows are decoys. Re-derive everything in step 5.
- **Fallback.** If a needed dimension has *no* short-token record (a matter can carry its
  privilege story in numbered entries), select analytically: within the flagged category, take
  the entries with a genuine defect, one representative per `(category, issue_type)` (lowest id).

### 5. Classify each material issue with the playbook
For every material record, derive its `issue_type`, `severity`, `status`, `source_status`,
`production_impact`, affected categories, `recommended_action`, `owner`, and priority using
`references/domain_playbook.md`. Map only to enum values present in *this* task's template.
Anchor each finding on a stable hub record ID; list all supporting IDs in `source_refs`
sorted ascending; sort category-code lists ascending.

### 6. Compute metrics and category coverage
- Derive counts from the material records: `unlogged = withheld − logged`; sum boxes/volumes,
  split pre- vs post-hold where the template asks; count each issue class and affected sources.
- Fill **every** metric key the template lists — use `0` / `[]` / `false` when the matter has
  no such fact. Read each metric's own description for its exact scope (some are "selected
  blockers only"). Any material gap ⇒ `production_ready` / `rolling_production_ready` = `false`.
- Category coverage: for each affected category, union the supporting material record IDs
  (sorted), pick a representative status / production_impact / recommended_action, and count
  open issues.

### 7. Prioritize the action plan
Order actions by the playbook's ladder (disclosure/preservation → privilege exposure →
recode → collect source → supplement log → search archive → over-designation → no-action) and
number ranks per the template's ordering rule (1 = highest). Assign `P0–P3` and `owner` from
the playbook, targeting stable hub IDs.

### 8. Emit exactly one JSON object
Conform to the template precisely (see `references/output_contract.md`): only the required
top-level keys, only template enum values, all lists sorted per `ordering_rules`, whole-integer
counts, hub IDs verbatim, **no prose outside the JSON**.

## Guardrails
- Evidence only from the hub API; connection details only from `environment_access.md`.
- Never read database/seed/source/manifest files or any answer/evaluation file.
- Do not invent record IDs, categories, or enum values — use the hub's and the template's.
- Prefer under-reporting a doubtful decoy to inflating the dashboard with noise.
