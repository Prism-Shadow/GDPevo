---
name: cedar-ridge-intake-audit
description: Solve Cedar Ridge Intake Coordination Portal tasks — patient access verification, referral readiness audits, transfer packet reviews, chronic-care enrollment panels, and referral-to-chart activation. Use when a task points at the Cedar Ridge portal and asks for a single JSON object following an answer_template.json. Read BEFORE querying the portal.
---

# Cedar Ridge Intake Coordination — Access / Readiness Audit

## When to use this skill

Use this skill when a task asks you to use the **Cedar Ridge Intake Coordination Portal** to do any of the following and return **one JSON object** that follows a provided `answer_template.json`:

- New-patient **access verification** for an intake roster (insurance, prescription benefit, pharmacy network, risk, registration status, blocked reason codes).
- **Referral readiness / activation** audit for a referral batch (coding discrepancies, duplicates, shared insurance, missing records/imaging/authorization, ready-to-schedule, priority tiers, chart-activation needs).
- **Transfer packet review** for a transfer batch (packet completeness/freshness, chair-capacity feasibility, intake decision, next-contact routing).
- **Chronic-care enrollment panel** for a program code (eligibility, enrollment disposition, reason codes, follow-up cadence, monitoring package, outreach).

If the task names a batch/roster/program ID, lists target patient/referral/transfer IDs, and points at the Cedar Ridge portal, this skill applies.

## What every task looks like

- A **prompt** naming the batch/roster/program and the target record IDs.
- **`environment_access.md`** giving the portal base URL and the allowed endpoints (use only those).
- **`input/payloads/answer_template.json`** — the contract: required top-level keys, per-record required keys, allowed enum values, and list-ordering rules ("ascending by referral_id", "alphabetical by doc_type", "treat as an unordered set").
- The required response is a **single JSON object** using only the template's controlled values. No prose outside the JSON.

## Entry workflow (do these in order)

1. **Read the template first, completely.** It is the contract. For every field note: required?, allowed enum values?, list ordering?, "unordered set"? Build a mental (or scratch) map of every controlled vocabulary before touching the portal. Every value you emit must come from the template.

2. **Read `environment_access.md`** for the base URL and the allowed endpoints. Use only the endpoints listed there. The portal exposes per-resource GET endpoints and a **read-only SQL interface** — prefer SQL for anything that joins tables.

3. **Discover the data model.** Through the SQL interface, run schema introspection to list every table and its `CREATE TABLE` statement (see `reference/portal_schema.md` for the table map and the introspection queries — re-run them to verify, since the schema is the source of truth). Knowing all tables up front prevents missing a relevant table (e.g., `icd_codes`, `facility_capacity`, `chart_artifacts`).

4. **Gather data in bulk with SQL joins.** Write one or two `SELECT ... JOIN` queries that pull the target IDs plus every related table. Pulling all related rows in one pass is faster and less error-prone than many single-record GET calls. Join `icd_codes` to referrals for chapter/service_family/laterality; join `facility_capacity` to transfers for chair counts; join `clinical_history`/`lifestyle`/`chart_artifacts` to patients for risk and chart status.

5. **Apply the business rules** in `reference/business_rules.md` to map raw rows → the template's controlled enum values and reason/blocker-code sets, one record at a time. Work the deterministic fields first (coverage status, PBM, pharmacy network, records/imaging/auth flags, ICD service family, duplicates, shared insurance, capacity) — these objective per-record findings matter most for correctness. Then derive the rollup statuses (readiness/registration/decision) and priority tiers.

6. **Aggregate the cohort summary from your own per-record outputs.** Count the values you already produced (statuses, reason codes, risk levels). Never recompute summary counts independently or they will drift from the per-record answers.

7. **Emit JSON only.** Assemble the object with exactly the template's keys, values from the template's allowed lists, and the specified orderings. Validate: every enum value is allowed; every list is ordered as specified; reason/blocker-code arrays are sets (no duplicates, order not meaningful); IDs are uppercase exactly as the portal shows them.

## Output discipline (non-negotiable)

- **JSON only** in the final response — no surrounding prose, no markdown fences, no commentary.
- **Only controlled values** from the template. Never invent an enum value or a reason code.
- **Honor orderings exactly.** "ascending by referral_id" means sort the list; "unordered set" means the set is compared without order but you should still emit it cleanly.
- **Reason/blocker-code arrays are sets.** Emit each applicable code once; do not order them meaningfully unless the template says to.
- **Identifiers verbatim.** Use patient/referral/transfer/program IDs exactly as the portal returns them (case-sensitive).
- **Self-validate** against the template before finishing: required keys present, all values in allowed lists, list orderings correct, summary counts consistent with per-record outputs.

## Domain map (what each table drives)

- `intake_rosters` → roster-level requested service date + service line (access verification).
- `patients` → demographics, existing chart flag, preferred contact, emergency-contact presence, address (drives contact/address blockers).
- `coverage` → insurance status (active/expired/pending, network, service-line scope, termination vs service date).
- `pbm` → prescription benefit status (active, formulary, approval, policy match vs coverage).
- `pharmacies` + `patient_pharmacy` → pharmacy network status (rank-1 preferred pharmacy).
- `lifestyle` + `clinical_history` → lifestyle risk and overall risk.
- `referrals` + `icd_codes` → referral readiness, clinical-code discrepancies, duplicates, shared insurance, records/imaging/auth blockers, already-scheduled.
- `transfer_requests` + `documents` + `facility_capacity` → packet completeness/freshness, chair-capacity feasibility, intake decision.
- `program_candidates` + `chart_artifacts` + `clinical_history` → enrollment eligibility, monitoring intensity, chart-artifact gaps.
- `chart_artifacts` → chart-action decisions (create vs update vs none) and artifacts to create.

See `reference/business_rules.md` for the field-by-field mapping rules and `reference/portal_schema.md` for the table/column reference.
