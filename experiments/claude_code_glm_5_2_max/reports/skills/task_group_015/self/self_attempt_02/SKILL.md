---
name: ehr-quality-governance-packets
description: Produce normalized JSON packets from a read-only EHR quality-governance / referral API — duplicate-chart merge readiness, care-transition handoffs, referral coordination, duplicate + ServiceRequest quality review, and batch referral audits. Use when a task gives an EHR/referral prompt plus an answer_template.json (or equivalent schema) that names entity IDs and asks for normalized JSON conforming to that template.
---

# EHR Quality-Governance Packet Generation

## When to use
Use this skill when a task:
- gives a prompt about an EHR / referral / quality-governance scenario,
- provides an `answer_template.json` (or equivalent schema) describing the required output shape,
- names specific entity IDs (patients, duplicate candidates, referrals, service requests, providers, batches), and
- asks you to return **normalized JSON conforming to the template**.

The environment is a read-only HTTP API described in `environment_access.md`. **The network API is the only source of truth for environment data — never read local source files for it.**

## Hard invariants (do not violate)
1. **Only the documented API.** Read the base URL and the allowed `GET` endpoints from `environment_access.md` at the start. Hit no other host and no endpoint not listed there. Access is unauthenticated.
2. **No server-side filtering.** List endpoints ignore query parameters (e.g. `?batch_id=` returns the full set). Always fetch the full list, then filter / sort / group client-side.
3. **List vs detail shapes.** List endpoints return `{ "<plural_resource>": [ ... ] }` — one wrapper key around an array. Detail endpoints return a bare object. Unwrap accordingly; do not assume a top-level array.
4. **404 = "not found" signal.** Unknown patient / ICD-10 code / service-code / duplicate-candidate / provider / referral returns HTTP 404 with `{ "error": ..., "status": 404 }`. Use 404 as the validity signal (invalid/unknown code, `service_code_valid=false`, `unknown_code`, etc.).
5. **Output purity.** Return only the JSON object conforming to the template — no markdown fences, no prose, no narrative SOP text. Use stable IDs, not explanations. Prompts in this family explicitly forbid procedural notes and narrative.
6. **Dates** are `YYYY-MM-DD` throughout. **Enums** must take a value from the template's allowed set; when reality does not fit, use the template's `other` / `unknown` bucket — never invent values.

## The operating loop (run for every task)
1. **Parse prompt + template.** Identify the task archetype (see `reference/task_archetypes.md`), the named input IDs, and read `answer_template.json` as the contract: required top-level keys, per-field enums/allowed-values, `ordering` rules, and `set_semantics`.
2. **Resolve base URL** from `environment_access.md`; fetch the endpoints the archetype needs (see `reference/api_contract.md` for exact wrapper keys and field shapes).
3. **Reconcile and derive.** Most template fields are not present verbatim in the API — derive them by cross-referencing endpoints (see `reference/derivation_rules.md`). Use `normalized_key` as the canonical element for any clinical-list set.
4. **Filter to active + relevant.** Keep `status == "active"` clinical records by default; exclude stale / out-of-window / unrelated distractors; report exclusions where the template has an `excluded_distractors` (or equivalent) section.
5. **Normalize sets & order.** Sort arrays marked as sets alphabetically ascending, unless the template's `ordering` field says otherwise (e.g. newest-to-oldest by date, or by `referral_id` / `group_id` / `risk_flag` / `code`).
6. **Emit.** Produce one JSON object matching the template exactly. Set `task_id` to the task's own identifier when the template requires a specific value for it.

## Core reusable rules (quick reference)
- **Canonical merge target / source** = `duplicate.merge_preview.preferred_target_patient_id` / `source_patient_id`. The patient's own `/conditions`, `/medications`, `/allergies` endpoints are **authoritative over the `merge_preview`** — reconcile and report keys the preview missed (`active_list_reconciliation`).
- **Disposition by signal strength**: reconcilable/soft signals (address abbreviation, name variant) lean merge-ready; hard identity conflicts (different DOB, different given name, different phone, opposite laterality) lean needs-review / do-not-merge. Defer to the candidate `status` and the template's disposition enum.
- **`normalized_key`** is the set element for condition / medication / allergy unions and diffs. Sort these alphabetically.
- **Derived provider / service fields need a lookup**: `performer_service_line` ← `/providers/{performer_id}`; receiving/specialist contact ← `/providers/{receiving_provider_id}`; `service_code_valid` ← `/service-codes/{code}` returns 200 **and** `active == true`.
- **ICD-10 validation**: 404 → invalid / `unknown_code`; chapter ≠ expected (e.g. `Musculoskeletal` for an orthopedic batch) → out-of-range / wrong-service-chapter; `requires_laterality == true` compared against the referral `diagnosis_narrative` via `expected_terms` → `laterality_mismatch` / `missing_laterality` / `narrative_mismatch`.
- **`reason_code_validation`**: for each reason code, `valid` = (lookup returned 200), `chapter` = looked-up chapter, `matches_patient_evidence` = code appears in the patient's active condition `code` values.
- **Evidence IDs**: include only documents / audit logs tied to the subject's patient_id(s) and the relevant event type (identity review, external import, merge). Everything else goes to `excluded_distractors`.

## Supporting references (inside this skill)
- `reference/api_contract.md` — every endpoint, its wrapper key, item field shapes, and 404 behavior. Consult before fetching so you unwrap correctly.
- `reference/derivation_rules.md` — cross-endpoint derivation, validation, normalization, sorting, and exclusion rules.
- `reference/task_archetypes.md` — the five task archetypes with a generic fetch → derive → emit plan each (procedures only; no task-specific answer values).

## Scope note
This skill encodes **reusable operating rules**, not answers. Apply the rules to the specific IDs and evidence each new task names; derive every output value fresh from the API. Do not copy final values from any prior task.
