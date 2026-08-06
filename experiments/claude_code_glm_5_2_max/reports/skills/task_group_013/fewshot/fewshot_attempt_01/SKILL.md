---
name: cedar-ridge-intake-verification
description: Complete a Cedar Ridge Intake Coordination Portal intake/audit task. Query the live portal for a roster, batch, or program; reconcile the records against the task's answer_template.json; and return one JSON object built only from the template's controlled values. Use when a task points at the Cedar Ridge portal and supplies an answer_template.json.
---

# Cedar Ridge Intake Verification

## When to use this skill

A task asks you to use the **Cedar Ridge Intake Coordination Portal** (reachable over the
network) to verify, audit, review, or activate a **roster**, **referral batch**, **transfer
batch**, or **program**, and to return **a single JSON object** that follows a provided
`answer_template.json`. The portal holds the intake data: patients, referrals, transfers,
documents, charts, ICD metadata, pharmacies, program candidates, and facility capacity.

If the task does not name the Cedar Ridge portal, or does not supply an `answer_template.json`,
this skill does not apply.

## The one rule

`answer_template.json` is the **single source of truth** for the output shape, required keys,
allowed enum values, and list ordering.

- Emit only values that appear in the template's `allowed_values` / `allowed` lists.
- Never invent codes, statuses, or fields.
- Never carry values over from memory or from any other task — **derive every value from the
  live portal data for the current task's scope**.
- The template defines the vocabulary; the portal provides the facts; your job is to map one
  onto the other.

## Network access

Reach the environment **only** through the endpoints listed in `environment_access.md`
(the base URL is given there). Do not call `/health` or any reset/reseed endpoint. No
authentication is required.

A read-only SQL endpoint is available: `POST /query` with a JSON body `{"sql": "..."}` returns
`{columns, row_count, rows, truncated}`. Use it for joins, grouping, and counts across tables
when the per-record endpoints would be slower or lossy.

For the full endpoint → response-shape → field map, see
[`references/portal_endpoints.md`](references/portal_endpoints.md).

## Workflow

1. **Parse the prompt.** Identify the target scope identifier — a `roster_id`, `batch_id`, or
   `program_code` — and which records it implies. Note every output section the office asks for
   (e.g. per-patient results, referral reviews, discrepancy lists, duplicate groups, blocker
   sets, action plans, correspondence queue, cohort summary).

2. **Read the template.** From `answer_template.json` extract, for every level:
   - required top-level keys (and the order they are listed);
   - per-item required keys;
   - every `allowed_values` / `allowed` enum (these are the only values you may emit);
   - every list `ordering` rule (ascending by id, unordered set, urgency-then-status,
     highest-priority-first, alphabetical, etc.);
   - the summary count-key buckets (`count_keys`, `required_keys`, `integer_keys`).
   These define exactly what to compute and how to order it.

3. **Gather portal data for the scope.** Pull the relevant collection, filter to the target
   identifier, then fetch per-record detail. Pull supporting metadata for every record in scope:
   `/icd/{code}`, `/documents`, `/chart/{patient_id}`, `/pharmacies`, and (for transfers) the
   capacity rows. Use `POST /query` when you need to join or count across tables. Do not pull
   records outside the scope — distractor records exist in every collection.

4. **Reconcile each record** against the template's vocabularies using the reusable primitives
   in [`references/reconciliation_rules.md`](references/reconciliation_rules.md). Assign only
   codes/statuses that exist in the template. The rule families are:
   - clinical-code discrepancy (ICD chapter / service-family / narrative / laterality);
   - duplicate referrals and shared-insurance anomalies;
   - missing records / imaging and authorization blockers;
   - already-scheduled appointments;
   - transfer packet completeness and document freshness;
   - chair-capacity feasibility for a requested start date;
   - coverage / PBM / pharmacy / lifestyle risk for access verification;
   - program eligibility, enrollment disposition, and monitoring package selection;
   - chart-activation gaps for ready referrals.

5. **Assemble the JSON object** section by section, in the order the template lists the
   top-level keys. Order every list exactly as the template specifies; treat every
   code/reason array as an **unordered set**.

6. **Compute the cohort / batch summary** by re-deriving integer counts from the per-record
   list you just built — do not count by eye. Include every bucket the template lists under
   `required_keys` / `count_keys`, **even when the count is 0**.

7. **Validate** against [`references/output_discipline.md`](references/output_discipline.md)
   before returning.

8. **Return JSON only.** A single object — no prose, no markdown fences, no trailing commentary.

## Scope is everything

Every collection in the portal contains records that belong to **other** batches, rosters, or
programs (and explicit distractors). Always filter to the target identifier first. A common
failure mode is reconciling records that are not in scope and letting them pollute the summary
counts. After you build the per-record list, confirm its length matches the scope (e.g. the
roster's patient count, the batch's referral count, the program's candidate count) before
computing the summary.

## Supporting references

- [`references/portal_endpoints.md`](references/portal_endpoints.md) — every documented endpoint,
  its response shape, and the fields that drive each reconciliation.
- [`references/reconciliation_rules.md`](references/reconciliation_rules.md) — generic, reusable
  detection rules for the issue / code classes the templates use.
- [`references/output_discipline.md`](references/output_discipline.md) — ordering, enum, count,
  and JSON-only rules, plus a pre-return checklist.
