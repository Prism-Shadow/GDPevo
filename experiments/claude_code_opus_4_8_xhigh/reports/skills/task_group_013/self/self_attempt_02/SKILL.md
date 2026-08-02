---
name: cedar-ridge-intake-coordination
description: >-
  Produce the strict-JSON deliverable for any Cedar Ridge Intake Coordination
  Portal task — primary-care access verification, referral readiness/activation
  audits, dialysis transfer packet review, and chronic-care program enrollment
  panels. Use whenever a prompt points at the Cedar Ridge Intake Coordination
  Portal (a base URL) plus an input/payloads/answer_template.json and asks for a
  single JSON object keyed by a roster_id, batch_id, or program_code. Covers how
  to reach the read-only REST + SQL endpoints, the shared data model, per-item
  classification rules, cohort/summary rollups, and the output contract.
---

# Cedar Ridge Intake Coordination — reusable operating guide

Every task in this family has the same shape:

1. A short prompt names **one work unit** — a roster (`NPI-…`), a referral
   batch (`ORTHO-…`, `PULM-…`, `CARD-…`, …), a transfer batch (`DIAL-…`), or a
   program (`DMHTN-…`, `RENAL-…`, `COPD-…`, `CAD-…`) — and points at the **Cedar
   Ridge Intake Coordination Portal** at `<TASK_ENV_BASE_URL>`.
2. `input/payloads/answer_template.json` defines the **exact output shape** and
   the **controlled vocabulary** (allowed enum values, required keys, ordering).
3. You must read portal data, classify each item, roll up cohort counts, and
   return **one JSON object, JSON only, no prose**, that conforms to the template.

The template is the contract. The portal is the source of truth. Your job is to
join the right tables, apply the classification rules, and reconcile the counts.

## 1. Golden rules (do these every time)

- **Re-read the task's `answer_template.json` first.** Treat its
  `required_*_keys`, `allowed_values`/`allowed`, `required_value`/`constant`,
  and `ordering` as authoritative. Never emit a key or enum value not listed
  there. The controlled vocabulary is self-describing — a code named
  `coverage_expired`, `missing_imaging`, or `consent_missing` tells you exactly
  the condition it represents.
- **Parameterize by the id in the prompt/template.** The work-unit id
  (`roster_id`/`batch_id`/`program_code`) and any constant `task_id` come from
  the prompt and the template's `required_value`/`constant`/`expected_value`
  fields — copy those verbatim. Do not hardcode ids or dates from prior runs;
  a held-out task will use a different id (e.g. `NPI-JUL-02`, `ORTHO-JUL-04`,
  `DIAL-FALL-03`, `RENAL-DM-2026B`).
- **Cover exactly the roster's members.** Include a row for every member the
  portal returns for that work unit, and no others. For rosters, the member
  list and the `requested_service_date` + `service_line` come from the
  `intake_rosters` rows for that `roster_id` (not from the prompt text).
- **Ordering matters.** Sort every list exactly as the template says (usually
  ascending by `patient_id` / `referral_id` / `transfer_id` / `group_id`).
  Where the template says "unordered set" for a code array, order is not graded
  but stay consistent; where it says alphabetical (e.g. dialysis
  `missing_required_documents`, activation `artifacts_to_create`), sort the
  strings.
- **Reconcile counts.** Every summary/cohort count must equal what you can
  recompute from the item list (per status, per risk, per urgency, totals). A
  mismatch between the detail rows and the summary is the most common failure.
  Cross-tab lists (e.g. `counts_by_urgency_and_status`) should enumerate the
  template's key order and may include explicit zero rows if the template's
  key set is fixed.
- **Emit JSON only.** No markdown, no commentary, no trailing text. IDs keep the
  portal's exact casing (uppercase `REF0001`, `P001`, etc.).
- **Dates are `YYYY-MM-DD` strings.** Compare dates as calendar dates. Use the
  work unit's own reference date (roster `requested_service_date`, transfer
  `requested_start_date`, program `candidate_date`/as-of) — see each playbook.

## 2. Reaching the portal

Base URL is provided per task (`environment_access.md` →
`GDPEVO_ENV_BASE_URL`, shown in prompts as `<TASK_ENV_BASE_URL>`).
**Credentials: none.** Everything is **read-only**.

Two equivalent ways to read; prefer whichever makes the join cleanest. The SQL
endpoint is usually fastest for batch joins and exact reconciliation.

- **REST (GET):** `/patients`, `/patients/{id}`, `/referrals` (filter
  `?batch_id=&service_line=&limit=`), `/referrals/{id}`, `/transfers`
  (`?batch_id=`), `/transfers/{id}`, `/documents`, `/chart/{patient_id}`
  (bundles patient + chart_artifacts + clinical_history), `/icd/{code}`,
  `/pharmacies`, `/programs/{program_code}/candidates`. `GET /health` returns
  table row counts — a useful sanity check.
- **Read-only SQL:** `POST /query` with body `{"sql": "SELECT …"}`. Only
  `SELECT` / read-only `PRAGMA` are allowed (writes are rejected). Returns
  `{columns, rows, row_count, truncated}`. Use `LIMIT` and paginate if
  `truncated` is true.

Example:

```bash
curl -s -X POST "$BASE/query" -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT * FROM referrals WHERE batch_id = ?BATCH? ORDER BY referral_id"}'
```

The full table schemas, column enums, and per-archetype join recipes are in
**`references/data_model.md`**. The step-by-step classification logic for each
of the four archetypes is in **`references/task_playbooks.md`**. Read both
before writing output.

## 3. Identify the archetype, then follow its playbook

Match the prompt/template to one of four archetypes and apply the matching
section of `references/task_playbooks.md`:

| Signal in prompt / template top keys | Archetype | Key tables |
|---|---|---|
| `roster_id`, `service_line`, `patient_results`, insurance/prescription/pharmacy/risk | **A. Primary-care access verification** | `intake_rosters`, `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle`, `patients` |
| `batch_id`, `referral_reviews`/`readiness_by_referral`, icd/duplicate/auth/imaging | **B. Referral readiness / chart activation** | `referrals`, `icd_codes`, (`documents`) |
| `batch_id` `DIAL-…`, `packet_completeness`, `stale_documents`, `requested_start`, chairs | **C. Dialysis transfer packet review** | `transfer_requests`, `documents`, `facility_capacity` |
| `program_code`, `patients[].enrollment_status`, `reason_codes`, monitoring package | **D. Chronic-care program enrollment** | `program_candidates`, `chart_artifacts`, `clinical_history`, `patients` |

Archetype B has two closely related variants — a **batch audit** (duplicate
groups, shared-insurance anomalies, action plan, urgency×status summary) and a
**referral-to-chart activation** file (readiness, chart needs, correspondence
queue, priority order). Both read the same `referrals`/`icd_codes` data; let the
template's top-level keys tell you which outputs to produce.

## 4. General decision scaffolding (applies across archetypes)

These structural patterns recur; the playbook gives the field-level specifics.

- **Readiness / registration / decision status** is the worst-severity outcome
  across that item's blockers. Something with a hard blocker is
  `blocked`/`rejected`/`hold`; something clean is `ready`/`approved`/`accept`;
  items needing human judgement are `under_review`/`clinical_review`; purely
  clerical items are `admin_followup`. Map to the exact enum the template lists.
- **A code array is the set of every condition that is true** for that item,
  drawn only from the template's allowed list. Empty list when nothing applies.
- **Priority tiers:** clinical/urgent + blocked → `tier_1_immediate`; substantive
  but non-urgent follow-up → `tier_2_short_term`; clerical/administrative →
  `tier_3_administrative`. Some templates allow `null` tier for already-ready
  items — check `enum_or_null`.
- **Missing vs. invalid vs. stale:** *missing* = the row/record does not exist;
  *invalid* = it exists but fails its rule; *stale* = it exists and is otherwise
  valid but older than its freshness window relative to the reference date.
- **Contact routing / outreach channel** follows the member's stated preference
  (`patients.preferred_contact` or `program_candidates.preferred_outreach`), and
  falls back / becomes `none` when the preferred channel's contact value is
  absent.

Always finish by recomputing the summary from your own item rows and confirming
every template-required count key is present (including zeros).

## 5. Self-check before returning

- [ ] Output is a single JSON object; nothing outside it.
- [ ] Top-level constant fields (`task_id`, `batch_id`/`roster_id`/
      `program_code`, etc.) equal the template's required/constant values.
- [ ] One item per work-unit member; ids in the template-specified order.
- [ ] Every enum/code value appears in the template's allowed list.
- [ ] Code/reason arrays contain no duplicates; alphabetized where required.
- [ ] Every summary count reconciles with the detail rows; all required count
      keys present (zeros included).
- [ ] Dates are `YYYY-MM-DD`; comparisons used the correct reference date.
