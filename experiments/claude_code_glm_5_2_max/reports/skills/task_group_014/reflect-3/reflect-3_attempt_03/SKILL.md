---
name: northstar-payer-determinations
description: Produce a structured JSON determination for a Northstar Health Plan payer-operations task — UM prior-authorization, pharmacy appeal + manufacturer assistance, payment-integrity claim repricing, peer-to-peer summary, or therapy margin queue — by gathering evidence from the shared Northstar environment and mapping it exactly to the task's answer_template.json.
---

# Northstar Payer Operations Determinations

Use this skill when a task asks you to act as a Northstar Health Plan reviewer
(UM nurse, pharmacy appeals coordinator, payment-integrity analyst, peer-to-peer
coordinator, or UM-finance analyst) and return a **single JSON object** matching a
provided `answer_template.json`. The work is always: gather evidence from the
shared Northstar payer-operations environment, evaluate it against the applicable
policy/finance rules, and emit a structured determination with a `basis_audit`
trail.

## Inputs you will receive

- `prompt.txt` — the request narrative and the **target business ID** to review.
- `payloads/task_context.json` — your role, reporting date, target IDs, an
  environment pointer, and any business rules specific to the request (appeal
  windows, margin thresholds, unit limits, queue row IDs, etc.).
- `payloads/answer_template.json` — the **exact** required JSON shape: required
  fields, enum choices, list-ordering rules, and numeric/date precision.
- An environment access file — the base URL, the SQL endpoint path, the SQL
  bearer token, and the list of allowed endpoints. Read it; do not assume
  credentials.

## Workflow

1. **Read the template first.** Before touching the environment, note every
   required top-level field, every enum's allowed choices, every list's
   ordering rule, and every numeric/date precision rule. Most templates set
   `additional_fields_allowed: false`, so extra keys cost points. The output
   must conform exactly.

2. **Discover the schema.** Call the open tables endpoint (`GET /api/tables`)
   to list every table and its columns. This is the source of truth for table
   and column names — never guess. The known Northstar schema is summarized in
   `references/data_model.md`; verify it still matches what the endpoint
   returns.

3. **Gather all related records.** Use the SQL endpoint (`POST /sql/query`,
   bearer token from the environment file; the request body carries the SQL
   string under the `sql` key — not `query`) and/or the open business endpoints
   (`GET /api/cases`, `/api/cases/{id}`, `/api/policies`, `/api/policies/{id}`,
   `/api/documents/{id}`, `/api/rate-schedules`, `/api/appeals`). Pull every
   record linked to the target business ID across the tables that matter for
   the task type (see `references/determination_playbooks.md`):
   - the primary record (case / appeal / claim / p2p event / margin queue rows);
   - member + plan + provider context;
   - request lines (requested CPT/modifier/units/dates);
   - policy + policy_criteria (the rules and `result_if_missing`);
   - case_criteria (the per-criterion review result already recorded);
   - documents + document_facts (the evidence, with `is_current` and
     `supports_criteria`);
   - authorizations, drug_trials, assistance_screen, claim_lines,
     payment_benchmarks — whichever apply.
   - **Use only the HTTP endpoints.** Do not read environment source files,
     SQLite database files, data dumps, manifests, or setup scripts from disk.

4. **Evaluate the determination.** Apply the playbook for the task type
   (`references/determination_playbooks.md`). Cross-cutting rules:
   - **Criteria results** come from `case_criteria.result`. The **meaning** of
     each criterion comes from `policy_criteria` (`criterion_text`,
     `approval_required`, `result_if_missing`). The **supporting evidence**
     comes from `document_facts.supports_criteria` (joined to `documents`).
   - **Prefer current records.** Rely on `documents.is_current = 1`. A stale
     export (`is_current = 0`, typically `source_system` like `LegacyUM`) is
     **excluded** from evidence, not relied upon — and it becomes the
     `exception_record_id` in the basis audit.
   - **Numbers and dates.** Apply unit multipliers before rounding (e.g.
     `allowed_amount * units`). Round currency to 2 decimals, ratios to the
     precision the template states (usually 4). Use `null` (never an empty
     string) for an absent modifier or a non-applicable date.

5. **Build the `basis_audit`.** Every task requires a `basis_audit` object with
   `source_precedence`, `precedence_record_order`, `controlling_record_ids`,
   and `exception_record_ids`. This is the part most likely to be wrong if
   improvised — follow `references/basis_audit.md`.

6. **Emit exactly one JSON object.** No prose, no markdown fences, no comments
   outside the JSON. Confirm every list is in the order the template specifies
   (ascending id, alphabetical, claim-line order, queue-row order, etc.).

## Task types → source-precedence rule

Pick the `source_precedence` enum value that matches the task type. This choice
drives the whole `basis_audit`:

| Task type | `source_precedence` |
|---|---|
| UM prior-authorization (PT/OT/ST) | `current_clinical_records_over_stale_export` |
| Pharmacy coverage-exception appeal + assistance | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity claim repricing | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer final summary | `new_patient_specific_p2p_information` |
| Therapy margin queue | `margin_threshold_then_charge_sensitivity` |
| Appeal routing with competing deadlines | `appeal_deadline_then_clinical_then_payment_integrity` |

## Output discipline checklist

- [ ] Every required top-level field present; no extra fields unless explicitly allowed.
- [ ] Every enum value is exactly one of the listed choices (watch spelling/case).
- [ ] Every list ordered per its template rule.
- [ ] Currency → JSON number rounded to 2 decimals; ratios → precision stated (usually 4); dates → `YYYY-MM-DD`; absent modifier/non-applicable date → `null`.
- [ ] `basis_audit` complete with the correct `source_precedence` and the right controlling/exception record sets (see `references/basis_audit.md`).
- [ ] The response is a single bare JSON object — nothing else.

## References

- `references/data_model.md` — the Northstar tables, key columns, and how they link.
- `references/determination_playbooks.md` — per-task-type determination logic and field mapping.
- `references/basis_audit.md` — how to choose `source_precedence` and assemble the controlling/exception record trail.
