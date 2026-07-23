---
name: northstar-payer-ops-determination
description: Produces a structured JSON determination, disposition, summary, or correction packet for a Northstar Health Plan payer-operations work item. Use whenever a task asks for a UM-nurse prior-authorization determination, pharmacy coverage appeal and/or manufacturer-assistance intake disposition, payment-integrity claim repricing packet, peer-to-peer (P2P) final summary, or UM-finance margin-queue summary — i.e. any task that supplies a prompt plus a task_context.json and an answer_template.json and expects a single JSON object back from the shared Northstar payer-operations environment. Covers reaching the environment only over the network (SQL endpoint + bearer token + open business endpoints), reconciling conflicting evidence via the domain source-precedence rule, evaluating criteria, classifying evidence vs excluded records, and assembling the basis_audit trail.
---

# Northstar Payer-Ops Structured Determination

This skill turns a Northstar Health Plan payer-operations work item into one
correct JSON object that conforms to the supplied `answer_template.json`. It is
domain-generic: the same workflow covers prior-authorization determinations,
pharmacy appeals, claim repricing, peer-to-peer summaries, and finance margin
queues. Apply the process below; do not memorize or reuse values from any
specific prior case.

## What you receive

Each task stages three inputs (paths are relative to the task root):

- `input/prompt.txt` — the business request in plain language.
- `input/payloads/task_context.json` — structured context: the target business
  ID, requester role, reporting date/period, work type, environment pointer
  (`<TASK_ENV_BASE_URL>`), and any task-specific parameters (thresholds, queue
  row IDs, source tables, appeal windows, etc.).
- `input/payloads/answer_template.json` — the binding output contract: required
  top-level keys, per-field types/enums/ordering/precision, the `basis_audit`
  sub-contract, and the additional-fields rule.

The template is the contract. Every required key, enum choice, list ordering,
numeric precision, date format, and null rule in it is binding.

## Environment access — network only

Resolve access from `/work/environment_access.md` (the sole sanctioned source).
Do not invent endpoints, base URLs, or credentials.

- The `<TASK_ENV_BASE_URL>` placeholder in `task_context.json` maps to the base
  URL recorded in `environment_access.md`.
- SQL access: `POST /sql/query` to the base URL with header
  `Authorization: Bearer <token from environment_access.md>`.
- Open business endpoints (no auth), as listed in `environment_access.md`:
  `GET /portal`, `GET /api/tables`, `GET /api/cases`, `GET /api/cases/{case_id}`,
  `GET /api/policies`, `GET /api/policies/{policy_id}`,
  `GET /api/documents/{document_id}`, `GET /api/rate-schedules`,
  `GET /api/appeals`.
- Prefer REST endpoints to traverse the obvious entities; use `POST /sql/query`
  for joins or facts the REST surface does not expose (drug-trial records,
  assistance-screen facts, margin rows, line-level detail, etc.).

**Hard rule:** reach the environment ONLY over its HTTP/SQL interface. Do not
open, `cat`, `sqlite3`, grep, or otherwise inspect environment source files,
generated data files, SQLite/database files, manifests, setup scripts, or
construction files. The environment is a black box. Derive every value from
live network responses, never from local files or memory.

## Workflow

1. **Load inputs.** Read `prompt.txt`, `task_context.json`, and
   `answer_template.json`. Identify the target business ID, reporting date or
   period, requester role, work type, and any task-context parameters
   (thresholds, queue row IDs, source tables, appeal windows).
2. **Internalize the template.** Note required top-level keys, each field's
   type/enum/ordering/precision, the `basis_audit` contract, and whether extra
   fields are allowed. You will emit exactly this shape.
3. **Resolve environment access** from `environment_access.md`.
4. **Discover the schema.** `GET /api/tables` first, so you know what entities
   and tables exist before querying.
5. **Fetch and traverse.** Pull the target record, then related entities:
   member/plan context, requested service/procedure lines, applicable policy
   and criteria, clinical/evidence documents, the authorization record, and any
   work-type-specific facts (drug trials, assistance screen, rate schedules,
   P2P event, margin rows). Use REST where it fits; fall back to SQL for the
   rest.
6. **Reconcile via source-precedence.** Apply the domain's precedence rule to
   resolve conflicts (current vs stale; payer appeal vs manufacturer
   assistance; effective benchmark vs stale schedule; new P2P info vs prior
   record; margin threshold vs charge sensitivity). Decide which records
   *control* the result and which are *exceptions/gaps/excluded*.
7. **Evaluate criteria.** Map each required criterion ID to its review result
   enum from the reconciled evidence.
8. **Classify documents/records.** Evidence relied on vs excluded
   (stale/superseded/inapplicable).
9. **Compute the result.** Determination/disposition, route/owner, next action,
   dates, and numeric outputs per work type, using task-context parameters and
   the template's precision rules.
10. **Assemble `basis_audit`.** Per `references/basis_audit_contract.md`.
11. **Emit.** Exactly one JSON object conforming to the template.

## The basis_audit contract (summary)

Every answer includes a `basis_audit` object with four required keys:

- `source_precedence` — one of six fixed precedence rules (see
  `references/basis_audit_contract.md`). Pick the rule that governs this work
  type.
- `controlling_record_ids` — environment record IDs that directly control the
  result, in operational evidence order (complete list).
- `exception_record_ids` — gap/exception records that explain exclusions,
  denials, missing information, or route priority; criteria/route gaps before
  stale/excluded records (complete list).
- `precedence_record_order` — the controlling and exception records in
  source-precedence order, highest priority first. This is a **curated,
  de-duplicated trail of the records that drive the precedence decision**, not a
  plain union of the two lists above: omit records that are mere operands or
  supporting evidence, and list a record once even if it appears in both roles.

Full semantics, the six rules, and worked ordering logic live in
`references/basis_audit_contract.md`.

## Output contract invariants

- Emit a single JSON object. No markdown, no prose, no comments outside the JSON.
- Enum values must exactly match the template's choices.
- Order every list per its template rule (ascending document_id, ascending CPT,
  claim-line order, alphabetical, the task-context `queue_row_ids` order, the
  template's choices order, operational packet order, etc.).
- Currency in USD rounded to two decimals; ratios to the precision stated
  (typically 4 decimals); service units as integers.
- Dates as `YYYY-MM-DD` ISO calendar dates; periods as `YYYY-MM`. Use `null`
  (not `""`) for absent modifiers and for deadlines that do not apply.
- Do not add fields beyond the template unless it explicitly permits additional
  properties.

## Pitfalls

- Reaching for local env/db files instead of the network — never.
- Copying values from memory or any prior case — derive every value live.
- Treating `precedence_record_order` as a plain union — it is curated and
  reordered by the precedence rule (see references).
- Conflating evidence documents with controlling record IDs — they overlap but
  serve different fields; populate each per its own rule.
- Forgetting to explicitly exclude a stale/superseded source (it belongs in
  excluded/exception, not evidence/controlling).
- Ignoring a task-context parameter (threshold, queue row IDs, appeal window) —
  these drive numeric and date results.

## References

- `references/basis_audit_contract.md` — the four basis_audit keys, the six
  source-precedence rules with semantics and work-type guidance, and the
  ordering / curation / de-duplication logic.
- `references/environment_workflow.md` — the detailed data-gathering workflow,
  the endpoint-to-entity traversal map, per-work-type notes, and formatting
  invariants.
