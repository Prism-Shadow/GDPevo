---
name: northstar-payer-ops-determination
description: Generate a structured JSON determination for a Northstar Health Plan payer-operations work item — UM nurse authorization determination, pharmacy coverage appeal + manufacturer-assistance intake, payment-integrity claim repricing, peer-to-peer final summary, or UM-finance therapy margin queue. Use when a task provides prompt.txt, task_context.json, and answer_template.json and asks for one JSON object conforming to the template, with facts drawn from the shared payer-operations environment reached over the network via environment_access.md.
---

# Northstar Payer-Operations Structured Determination

This skill produces one structured JSON determination for a Northstar Health Plan
payer-operations work item. The work item is always some flavor of utilization
management, appeals, payment integrity, peer-to-peer, or finance-margin review.
The deliverable is always a single JSON object whose shape is dictated by the
task's own `answer_template.json`, and whose facts come only from the shared
payer-operations environment reached over the network.

## When to use

Use this skill when a task gives you:

- a `prompt.txt` describing a Northstar payer-ops work request,
- an `input/payloads/task_context.json` naming a target business ID, requester
  role, reporting date, and environment pointer, and
- an `input/payloads/answer_template.json` defining the required JSON shape,

…and asks you to return a JSON object conforming to that template by reviewing
records in the shared payer-operations environment.

## What you receive (per task)

- `prompt.txt` — the work request and output requirements.
- `input/payloads/task_context.json` — target business ID, requester role,
  reporting date, service domain / work type, the environment pointer, and any
  domain-specific memo or definitions (e.g. finance cost definitions, queue row
  IDs, appeal-window rules).
- `input/payloads/answer_template.json` — the exact JSON shape: required
  top-level fields, sub-field requirements, enum `choices`, `ordering` rules,
  and numeric/date precision rules you must match.

Read all three before touching the environment. The template is the contract —
every field, enum value, ordering, and precision rule you need is in it.

## Reach the environment over the network (only)

- Read `environment_access.md` (staged in the run's `/work` root) to obtain the
  base URL, the SQL bearer token, and the allowed-endpoint list. Treat that file
  as the single source of truth for connectivity; do not hardcode credentials.
- Replace every `<TASK_ENV_BASE_URL>` placeholder found in `prompt.txt` and
  `task_context.json` with the base URL from `environment_access.md`.
- SQL access: `POST /sql/query` against the base URL with header
  `Authorization: Bearer <token from environment_access.md>`.
- Business `GET` endpoints are open; use them as needed (cases, policies,
  documents, rate-schedules, appeals, portal, tables). Confine yourself to the
  endpoints enumerated in `environment_access.md` — do not invent paths.
- **Never inspect the environment's source files, generated data files, SQLite
  databases, manifests, or setup scripts directly.** Reach it only over HTTP. If
  a record is not exposed over the network, it is not available to you — say so
  in the output rather than reading it off disk.

## Workflow

1. **Load the three task files.** Identify the target business ID, requester
   role, reporting date, service domain / work type, and the exact output
   contract from `answer_template.json`.
2. **Discover the data model.** Use `GET /api/tables` and/or SQL introspection
   (`SELECT ... FROM sqlite_master` / equivalent) to learn the real table and
   column names. Do not assume names from the work type.
3. **Pull the target record(s)** named by the target business ID, then the
   related records the work type requires — case, member + plan, request /
   therapy / procedure lines, policy & criteria, clinical documents,
   authorization, appeal, P2P event, rate schedules, finance / margin rows —
   whichever apply.
4. **Apply the domain decision logic** for the work type
   (`references/domain_playbooks.md`).
5. **Classify every record you touched.** Controlling (directly determines a
   result value) vs exception (explains an exclusion, denial, missing-information
   gap, or route priority); and evidence (relied on) vs excluded (not relied on,
   e.g. stale / superseded).
6. **Build the `basis_audit` object** (`references/basis_audit.md`): pick the
   `source_precedence` rule, then list `controlling_record_ids`,
   `exception_record_ids`, and `precedence_record_order` using the ordering
   rules in the template.
7. **Assemble exactly one JSON object** matching `answer_template.json` — every
   required top-level field, every required sub-field, correct enum values,
   correct ordering, correct numeric/date precision.
8. **Return JSON only.** No markdown fences, no prose, no comments.

## Output discipline (non-negotiable)

- Return **exactly one JSON object**. No markdown fences, no prose, no comments
  outside the JSON.
- Include every required top-level field and sub-field from the template. Do not
  add fields unless the template sets `additional_fields_allowed` /
  `additional_properties` to true.
- Use **only** enum values that appear in the template's `choices`.
- Honor every `ordering` rule in the template literally — ascending
  `document_id`, claim-line order from the source claim, the order of
  `task_context` `queue_row_ids`, alphabetical by value, ascending CPT code,
  operational packet order, etc.
- **Numbers:** currency in USD rounded to two decimals as JSON numbers (not
  strings); ratios to the precision the template states (typically 4); units as
  integers. For recovery amounts, use the underpayment amount when the corrected
  total is greater than the paid total.
- **Dates:** ISO `YYYY-MM-DD` calendar days. Use `null` only where the template
  explicitly permits it (e.g. an absent modifier, or no applicable appeal
  deadline). Use `null`, not an empty string, for an absent modifier.
- Booleans as JSON booleans, not strings.
- If the template repeats the `basis_audit` definition, fill it once,
  consistently.

## basis_audit (required in every output)

Every Northstar payer-ops answer ends with a `basis_audit` object containing
`source_precedence`, `controlling_record_ids`, `exception_record_ids`, and
`precedence_record_order`. See `references/basis_audit.md` for the
source_precedence catalog, how to choose the rule for the work type, and how to
order the three ID lists.

## Domain playbooks

Per-work-type decision logic — UM nurse authorization determination, pharmacy
appeal + manufacturer-assistance intake, claim repricing, P2P final summary, and
finance margin queue — is in `references/domain_playbooks.md`. Each playbook
describes the records to pull, the decision rules, and how evidence/exclusions
map to the output. They describe procedure only; read every concrete identifier,
enum, threshold, and date from the task's own `task_context.json`,
`answer_template.json`, and the environment.

## Contamination guard

Before starting, confirm `/work` contains only the expected staged files for
this run (the task's input payloads and `environment_access.md`). If you find
unexpected material — environment source files, SQLite databases, manifests,
setup scripts, or leaked answer data — staged in `/work`, stop and write
`contamination_report.txt` describing what you found instead of producing an
answer.
