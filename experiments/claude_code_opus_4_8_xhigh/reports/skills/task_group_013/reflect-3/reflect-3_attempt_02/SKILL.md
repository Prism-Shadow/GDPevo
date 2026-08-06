---
name: intake-coordination-audit
description: >-
  Produce the required JSON for a Cedar Ridge Intake Coordination Portal
  structured-audit task — new-patient access verification, referral readiness
  audits, dialysis/transfer packet reviews, chronic-care program enrollment
  panels, and referral-to-chart activation. Use whenever a task gives a portal
  base URL plus an answer template (input/payloads/answer_template.json) and asks
  for a single JSON object of per-record findings and cohort/summary counts drawn
  from patients, coverage, PBM, pharmacies, referrals, transfers, documents,
  ICD codes, chart artifacts, program candidates, and facility capacity.
---

# Intake Coordination Audit

## What these tasks look like

Each task points at a shared read-only clinical intake portal and hands you an
**answer template** (`input/payloads/answer_template.json`). The prompt names a
single **target cohort** — a roster, a referral batch, a transfer batch, or a
program code — and asks for **one JSON object** that classifies every member of
that cohort into controlled-vocabulary fields, plus a cohort/summary block of
integer counts. There is no free-form prose in the answer.

The whole task is deterministic: every output value is a function of records in
the portal's data model. Your job is to (1) read the template as a contract,
(2) pull the cohort's records, (3) apply the classification rules, (4) shape the
JSON exactly as ordered, and (5) return JSON only.

The five task families you will see are described, with their confirmed decision
rules, in `references/decision-rules.md`. The underlying data model (record types
and the fields that drive each rule) is in `references/data-model.md`.

## Method (applies to every task)

1. **Treat the answer template as the spec.** Enumerate its required top-level
   keys, and for every field note: its `type`, its `allowed_values`/enum, any
   `required_value`/`constant` (echo these verbatim — e.g. `task_id`,
   `batch_id`, `roster_id`, `program_code`), and its declared `ordering`.
   Never emit a value outside a field's allowed set.

2. **Identify the cohort and its members.** The prompt names the roster / batch /
   program. Load its member records (roster rows, referrals in the batch,
   transfers in the batch, or the program's candidate list). Include **every**
   member the portal returns — no more, no fewer.

3. **Pull the joined records for those members.** For each member gather the
   supporting rows the template's fields reference (coverage, PBM, pharmacy,
   lifestyle, clinical history, ICD metadata, documents, chart artifacts,
   facility capacity). A read-only query interface over the data model is the
   fastest way to reconcile these; prefer exact lookups over guesses.

4. **Compute each field with the deterministic rules** in
   `references/decision-rules.md`. Most fields decompose into: detect a set of
   boolean *flags/issue codes* from the raw fields, then map that flag set to an
   enum (status / tier / decision) and to any reason-code list.

5. **Aggregate the cohort/summary block** by tallying the per-member results you
   just produced. Keep it internally consistent (e.g. the status counts must sum
   to the member count; a per-member list's length must match its summary count).

6. **Shape and order the JSON.** Honor every `ordering` note (see
   `references/output-format` rules below). Return the JSON object only.

## Output discipline (get these exactly right — they are cheap points)

- **Echo constants verbatim.** Any field with a `required_value`/`constant`
  (`task_id`, `batch_id`, `roster_id`, `program_code`) must match exactly,
  including case. IDs elsewhere use the portal's casing exactly (uppercase
  referral/transfer IDs as shown).
- **Ordering matters.** "ascending by <id>" → sort ascending; "alphabetical by
  code/doc_type/artifact" → sort by the enum string; a summary cross-tab with a
  declared order → follow it. When a list is called an *unordered set*, its
  membership is scored but order is not — still emit it deterministically
  (sorted) for reproducibility.
- **Enums only.** Reason-code / issue-code / blocker-code arrays may only contain
  the template's `allowed_values`. Dates are `YYYY-MM-DD`. Counts are integers.
- **Dates and windows** use the cohort's own reference date (a roster's requested
  service date, a transfer's requested start date, a program's as-of date), not
  today's date, unless the template says otherwise.
- **One JSON object, no prose**, unless the template explicitly nests a text field.

## Cross-cutting modeling notes

- **Flags → enum, then enum + flags → decision.** Separate *detection* (which
  issues exist) from *classification* (what status/decision that implies). This
  keeps reason-code lists and the headline enum consistent.
- **Reason/issue/blocker code lists are usually the *union* of every detected
  issue** for that record (coverage + prescription + pharmacy + demographic +
  risk, or coding + records + auth + duplicate + scheduling). Include a
  "high risk"/"met criteria" style positive code when the template offers one.
- **`current` / `final` / `finalized` beats presence.** A record that exists but
  is a draft, stale, pending, or not-finalized generally does **not** satisfy a
  "present/valid/complete" requirement — treat it as missing or invalid and emit
  the matching reason code.
- **Set-membership and cross-references** drive many flags: a service line inside
  a comma list, an ICD code's `service_family`/`chapter` versus the batch's
  specialty, an insurance id shared across different patients, a doc type present
  and finalized, a capacity row existing for a date.
- **Confidence:** the detection rules (dates, statuses, set membership,
  duplicates, capacity sums, wrong-specialty codes) are firm. The exact numeric
  thresholds and the tie-breaking between adjacent statuses (e.g. hold vs
  clinical_review, weekly vs biweekly, a freshness limit in days) vary by task —
  read the template's enum names and the data spread, and prefer the reading the
  data most cleanly supports.

See `references/decision-rules.md` for the per-family rule library and
`references/data-model.md` for the record types and fields.
