---
name: northstar-payer-determinations
description: Produces a correct structured-JSON determination for Northstar Health Plan payer-operations tasks — UM nurse authorization, pharmacy coverage appeal + manufacturer assistance, payment-integrity claim repricing, peer-to-peer (P2P) summary, and UM-finance margin-queue analysis — backed by records in the shared payer-operations environment. Use whenever a task gives a target business ID, a payer-operations role, a reporting date, and an answer_template.json, and asks you to return one JSON object conforming to that template.
---

# Northstar Payer Operations Determinations

## What these tasks are
Each task gives you:
- `prompt.txt` — the request (your role, the target business ID, the reporting date, what to return).
- `payloads/task_context.json` — target IDs, role, dates, and any domain definitions (finance thresholds, packet items, appeal windows, etc.).
- `payloads/answer_template.json` — the **exact** JSON contract: required fields, types, enum choices, list-ordering rules, numeric precision, and null-handling rules.

The shared payer-operations environment holds the source records (cases, members, plans, providers, clinical documents, policies, criteria, authorizations, appeals, drug trials, assistance screens, claims, claim lines, rate schedules, P2P events, margin rows). Your job is to read the right records, apply the determination logic, and return **one JSON object** matching the template. Output JSON only — no prose, no markdown fence, no comments.

Produce the correct answer in a single pass: read the inputs carefully, derive each field exactly from environment records, and validate every field against the template before emitting JSON.

## Entry workflow (every task)
1. **Read all three inputs fully.** The template is the contract — note every required field, enum choice, list-ordering rule, numeric precision, and null rule before touching the environment.
2. **Identify the task type** from the role/target (see `references/determination_patterns.md`). Identify the target business ID(s) and any row/segment lists named in `task_context.json`.
3. **Discover the live schema** via the environment's tables-listing endpoint, then query the records that feed the answer. Use the environment's SQL query endpoint for precise joins and the business GET endpoints for quick lookups. Use only the endpoints and credentials supplied in the task's own `environment_access` — do not assume URLs or tokens.
4. **Derive every field from environment records.** Never fabricate a value. Apply the cross-cutting rules below.
5. **Assemble one JSON object** matching the template. Re-check every ordering rule, precision rule, enum, and null rule. Output JSON only.

## Cross-cutting rules (these cause silent field failures — follow exactly)
- **Match the template exactly.** Field names, types, enums, and list orderings are strict. A field is correct only when *all* of its sub-values match — partial credit per field is not reliable, so be exact on every sub-field.
- **Lists must match exactly, including the right *item*.** When a category is only partially supported, name the **specific** missing/supported record item, not the broad category. Example: if a packet requires "formulary-failure evidence" and one prior failure is documented while a second is only referenced without a fill record, the missing item is the *specific fill record* for that second medication — not the general "formulary-failure evidence" category (which is partly present).
- **Ordering is part of correctness.** Re-derive order from each rule: ascending IDs/CPT codes, alphabetical by enum value, "the order shown in choices," "operational evidence order," "payer appeal items before assistance items," "appeal-evidence gaps before assistance-info gaps," "criteria/route gaps before stale/excluded records." Do not improvise.
- **Precision.** Currency → dollars rounded to cents (JSON numbers). Ratios → 4 decimals unless told otherwise. Units → integers. Dates → `YYYY-MM-DD` calendar day. Rounding happens *after* applying units (e.g., `allowed_amount × units`, then round).
- **Null vs empty.** Use JSON `null` (not `""`) for an absent modifier or any field the template says may be null. Use `null` for a deadline field *only* when no deadline applies.
- **Enums.** Map the environment record's status/outcome/path to the closest enum value (e.g., `pending_missing_income_proof` → `eligible_missing_information`; `recommended_approval` → approve). When the record's free text does not match an enum exactly, choose the enum that captures the operational state.
- **`basis_audit` is required on every task.** It carries `source_precedence`, `precedence_record_order`, `controlling_record_ids`, `exception_record_ids`. Choose `source_precedence` by task type (table below). Fill:
  - `controlling_record_ids` — records that directly drive the result, in operational evidence order.
  - `exception_record_ids` — gap/stale/excluded records; order criteria/route gaps before stale or excluded records.
  - `precedence_record_order` — controlling + exception records in source-precedence order, highest priority first.
  Keep it sensible and complete; do not leave required keys out.
- **`source_precedence` by task type:**

  | Task type | source_precedence |
  |---|---|
  | Clinical UM determination that excludes a stale/non-current export | `current_clinical_records_over_stale_export` |
  | Pharmacy coverage appeal + manufacturer assistance | `payer_appeal_before_manufacturer_assistance` |
  | Payment-integrity claim repricing vs rate schedule | `effective_benchmark_by_plan_modifier_and_date` |
  | Peer-to-peer (P2P) review | `new_patient_specific_p2p_information` |
  | Therapy/service margin queue | `margin_threshold_then_charge_sensitivity` |
  | Appeal deadline / route-priority tie-break | `appeal_deadline_then_clinical_then_payment_integrity` |

## Determination patterns
See `references/determination_patterns.md` for the field-by-field derivation logic for each task type. See `references/data_model.md` for the environment tables, key columns, and the joins that feed each pattern. Always confirm the live schema via the tables-listing endpoint before relying on column names.

## Pitfalls to avoid (single-pass correctness)
- **Don't echo a broad category when a specific item is required** (packet gaps, evidence lists). Prefer the precise record-level item.
- **Don't use a stale/expired source as the answer's source.** For repricing, the controlling rate is the one *effective on the service date*; anything expired before the service date is the rejected stale source, even if it matches the paid amount.
- **Exclude non-current documents from evidence.** A document with `is_current = 0` (e.g., a stale export) goes in `excluded_documents`, not `evidence_documents`.
- **Report only the template's required criteria keys** in `criteria_results` — do not add extra criterion IDs the template does not list.
- **Date arithmetic for appeal deadlines:** start from the *final adverse determination date* (the date the denial was finalized, e.g., the P2P/final-review date), then add the plan's internal-appeal window (e.g., 180 days). Compute with calendar-day addition and verify.
- **Beware duplicate/distractor benchmark rows.** Multiple rows may share CPT+modifier+source; pick by effective date and plan_type, and ignore schedules whose CPT is not on the claim (distractors).
- **Sign of recovery.** When corrected allowed > paid, recovery is a positive underpayment amount (provider is owed more). Per-line disposition follows the per-line sign.
- **Output discipline.** Exactly one JSON object, no surrounding text, no markdown fence. Numbers as JSON numbers (not strings). Lists sorted per the template's rule.
