---
name: northstar-payer-ops
description: Northstar Health Plan payer-operations structured determinations. Use when a task asks for a JSON determination, disposition, correction packet, P2P summary, or margin-queue summary for a Northstar case/appeal/claim/P2P/queue against a shared read-only payer environment (base URL http://task-env:9014/, SQL POST /sql/query with bearer pa-review-token-014, open GET business endpoints). Covers five archetypes — UM nurse prior-auth determination (physical therapy), pharmacy coverage appeal + manufacturer assistance intake, payment-integrity claim repricing (cardiac imaging), peer-to-peer final summary (PET MPI), and UM-finance therapy margin queue. Reads prompt.txt + task_context.json + answer_template.json, gathers evidence via allowed endpoints only, and emits exactly one JSON object matching the template's required keys, enums, ordering, precision, and basis_audit rules. Do not inspect environment DB/setup files directly; do not call any judge endpoint.
---

# Northstar Payer Operations Determinations

Produces one structured JSON object for Northstar Health Plan payer-operations work items: utilization-management (UM) prior-auth determinations, pharmacy coverage appeals with manufacturer assistance intake, payment-integrity claim repricing, peer-to-peer (P2P) final summaries, and UM-finance margin-queue summaries.

Each work item is self-describing: the task directory tells you the intent, the target identifiers, and the exact output contract. Your job is to gather evidence from the shared read-only environment, apply the domain rules, and return one JSON object that conforms to the contract.

## When to use

A task matches this skill when it references the **Northstar** payer-operations environment and asks for a structured JSON result for one of these work items:

- **UM nurse determination** — prior authorization case, typically physical therapy (`CASE-…`).
- **Pharmacy appeal + assistance** — coverage exception appeal with a manufacturer assistance screen (`APPEAL-…` / `APL-…`).
- **Payment-integrity claim repricing** — a paid claim repriced against a benchmark schedule, typically cardiac imaging (`CLAIM-…`).
- **Peer-to-peer summary** — final P2P determination after a completed discussion, typically cardiac imaging PET MPI (`P2P-…`).
- **Finance margin queue** — a service-margin queue summarized for a reporting period (`QUEUE-…`).

## Inputs (read all three before touching the environment)

Every task directory has the same shape. Read all three files; each carries different authority:

1. `prompt.txt` — human-readable intent and which record classes to review.
2. `payloads/task_context.json` — machine-readable context: `target_business_id` / `case_id` / `appeal_id` / `claim_id` / queue business id, `requester_role`, `reporting_date` / `reporting_period`, environment access, and a `local_memo` / `finance_memo` with operational definitions (thresholds, due-date windows, queue row ids, cost definitions).
3. `payloads/answer_template.json` — **the authoritative output contract.** Required top-level keys, per-field enums, list ordering rules, numeric precision, date format, and whether extra fields are allowed. Conform to this exactly.

The template is the contract, not a suggestion. If the template and your intuition disagree, the template wins.

## Environment access

Resolve access from `environment_access.md` (or the `environment` block in `task_context.json`):

- **Base URL:** `http://task-env:9014/`
- **SQL:** `POST /sql/query` with header `Authorization: Bearer pa-review-token-014`. Body is a SQL query over the relational tables. This is the flexible path for joins.
- **Business GET endpoints:** open (no auth) — `/portal`, `/api/tables`, `/api/cases`, `/api/cases/{case_id}`, `/api/policies`, `/api/policies/{policy_id}`, `/api/documents/{document_id}`, `/api/rate-schedules`, `/api/appeals`.

**Prohibited:** do not inspect environment source files, generated data files, SQLite files, manifests, or setup scripts directly. Do not call any judge endpoint (none is available). Use only the allowed HTTP endpoints above.

Full endpoint rules and the 19-table schema are in `references/environment_and_schema.md`.

## Workflow

1. **Parse the contract.** Read all three input files. Extract target identifiers, role, dates/period, and any operational definitions from the memo (thresholds, due-date windows, queue row ids, cost definitions). Note every required key, enum, ordering rule, and precision rule in the template.
2. **Classify the archetype.** Map the task to one of the five archetypes (see quick table below). The archetype selects the criteria keys, decision logic, and the `source_precedence` rule.
3. **Gather evidence** via the allowed endpoints / SQL. Pull the target record plus its dependent records (member/plan, request lines, policy + criteria, case criteria, documents + document facts, authorization/appeal/P2P/claim/rate-schedule/service-margin rows as applicable). Use `GET /api/tables` only if you need to re-discover the schema.
4. **Apply domain rules.** For each criterion/line/queue row, compute the result per the archetype playbook (`references/domain_playbooks.md`). Resolve stale-vs-current, deadline, threshold, and modifier questions explicitly.
5. **Build the `basis_audit`.** Every output carries the same audit object. Pick `source_precedence`, then list `controlling_record_ids` (records that directly drive the result, operational evidence order), `exception_record_ids` (gaps/exclusions/denials/missing-info/route-priority; criteria/route gaps before stale/excluded), and `precedence_record_order` (controlling ∪ exception, highest precedence first). See `references/basis_audit.md`.
6. **Emit exactly one JSON object** matching the template. No markdown, prose, or comments outside the JSON. Respect enums, list ordering, numeric precision, date format, and `null`-for-absent rules.

## Universal output contract (distilled from all five templates)

- **One JSON object only.** No extra top-level fields unless the template explicitly allows them.
- **Currency:** USD dollars rounded to two decimals (cents). **Ratios:** precision per template (commonly 4 decimals). **Dates:** ISO 8601 `YYYY-MM-DD`. **Periods:** `YYYY-MM`.
- **Absent values:** use `null` (not `""`) for an absent modifier and for a deadline that does not apply. Use booleans for flags.
- **List ordering** is scored — follow each field's stated rule: ascending `document_id`; ascending CPT code; alphabetical; claim-line order; the order in `task_context.…queue_row_ids`; "payer appeal items before assistance items"; "appeal evidence gaps before assistance information gaps"; "criteria/route gaps before stale/excluded records".
- **`basis_audit`** is required in every output with keys `source_precedence`, `precedence_record_order`, `controlling_record_ids`, `exception_record_ids`.

## Archetype → source_precedence (quick map)

| Archetype | Target | Criteria / focus keys | `source_precedence` |
|---|---|---|---|
| UM nurse determination (PT) | `CASE-…` | `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, `PT-UNITS` | `current_clinical_records_over_stale_export` |
| Pharmacy appeal + assistance | `APPEAL-…` / `APL-…` | `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES` | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity repricing | `CLAIM-…` | line corrections, benchmark selection | `effective_benchmark_by_plan_modifier_and_date` |
| P2P final summary (PET MPI) | `P2P-…` | `PET-IND`, `PET-FACTOR` | `new_patient_specific_p2p_information` |
| Finance margin queue | `QUEUE-…` | per-row ratio vs 1.2 threshold, charge-sensitivity | `margin_threshold_then_charge_sensitivity` |

A sixth enum value, `appeal_deadline_then_clinical_then_payment_integrity`, is a general routing-precedence tie-breaker (deadline → clinical → payment-integrity) for tasks where competing deadlines drive owner/route priority; use it only when it best characterizes the controlling logic. Detail and selection guidance: `references/basis_audit.md`.

## References (load on demand)

- `references/environment_and_schema.md` — allowed endpoints, auth rules, the 19-table catalog, table→archetype map, prohibited actions.
- `references/domain_playbooks.md` — per-archetype trigger, evidence to gather, decision logic, criteria keys, special rules (deadlines, thresholds, normalization), and `source_precedence`.
- `references/basis_audit.md` — the four audit keys, controlling-vs-exception selection, ordering rules, and the six `source_precedence` rules with archetype mapping.
