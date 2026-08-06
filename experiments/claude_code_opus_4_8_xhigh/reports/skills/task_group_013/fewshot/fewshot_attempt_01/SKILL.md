---
name: cedar-ridge-intake
description: >-
  Answer Cedar Ridge Intake Coordination Portal tasks: read a task prompt plus its
  input/payloads/answer_template.json, query the read-only portal (REST + POST /query SQL) at
  the base URL in environment_access.md, apply the intake decision rules, and return ONE JSON
  object that exactly matches the template. Covers patient access verification, referral
  readiness audits, dialysis transfer reviews, program enrollment panels, and referral-to-chart
  activation. Use whenever a prompt points at the "Cedar Ridge Intake Coordination Portal" or a
  roster/batch/program id (e.g. NPI-*, ORTHO-*, PULM-*, DIAL-*, a program code) with an
  answer_template.json to fill.
---

# Cedar Ridge Intake Coordination tasks

Each task gives you a prompt, an `input/payloads/answer_template.json`, and network access to a
read-only clinical-intake portal. Your job: gather the relevant records, apply the intake
business rules, and emit a **single JSON object** that conforms exactly to the template. The
grader compares your JSON to a gold answer — controlled values, keys, ordering, and summary
counts all matter, and no prose is allowed outside the JSON.

## Workflow

1. **Read the inputs.** Read the prompt and `input/payloads/answer_template.json` in full. Note
   the target id (roster/batch/program), the required top-level keys, every controlled-value
   (enum) list, ordering directives, and any pinned constants (`task_id`, ids). Some tasks add
   an extra payload (e.g. `target_roster.json`) — read it too.

2. **Connect to the portal.** Get the base URL from `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`) and use only the endpoints listed there. Prefer `POST /query`
   (read-only SQL) for reconciliation; use the REST views for convenience. The helper
   `scripts/portal.py` wraps both:
   ```bash
   python3 scripts/portal.py --env <path>/environment_access.md tables
   python3 scripts/portal.py --env <path>/environment_access.md schema referrals
   python3 scripts/portal.py --env <path>/environment_access.md sql "SELECT ... ORDER BY ..."
   python3 scripts/portal.py --env <path>/environment_access.md get /programs/<code>/candidates
   ```
   `GET /health` shows per-table row counts as a sanity check. See
   `references/data_model.md` for the full schema, endpoints, and the service-line↔ICD-chapter
   reference.

3. **Identify the family and pull the roster/batch/program.** Match the template to one of the
   five families in `references/task_families.md`. Fetch the exact working set (every patient,
   referral, transfer, or candidate the prompt scopes) and all the tables that family needs.
   Include **every** member the portal returns — don't sample.

4. **Apply the decision rules** from `references/task_families.md` per row. Those rubrics
   (coverage/PBM/pharmacy status, risk scoring, readiness/blocker logic, coding discrepancies,
   duplicates, packet completeness/freshness, capacity feasibility, program eligibility &
   monitoring packages, chart activation, correspondence, priority tiers) reproduce every
   worked example. When a rubric offers a threshold as a heuristic, apply it consistently and
   sanity-check against the cohort.

5. **Assemble the JSON to the template.** Use the template's keys, in the item ordering it
   specifies (usually ascending id). Use **only** the template's controlled values in each
   field. Compute every summary/cohort count from your own rows so they reconcile exactly.
   Surface the template's constraints with:
   ```bash
   python3 scripts/template_constraints.py <path>/input/payloads/answer_template.json
   ```

6. **Self-check before returning** (see checklist below), then output the JSON object and
   nothing else.

## Output discipline

- Return exactly one JSON object; **no** commentary, markdown fences, or trailing text.
- Echo pinned constants verbatim (`task_id`, `roster_id`/`batch_id`/`program_code`).
- Every enum-typed field must hold a value from that field's template list — never invent
  codes or reuse a code from a different field.
- Lists follow the template's ordering rule (ascending id, alphabetical, "urgency then status",
  etc.); lists marked "unordered set" still must contain the right members with no duplicates.
- Integer counts are integers; keep the full set of count keys even when a count is 0.
- Ids stay in the portal's exact casing (referral/patient ids uppercase as returned).

## Self-check

- [ ] Top-level keys == the template's required set; constants echoed verbatim.
- [ ] Row count == number of scoped patients/referrals/transfers/candidates; ordered correctly.
- [ ] Every enum value is a member of its field's allowed list.
- [ ] Each row's reason/issue/blocker/action codes are internally consistent with its status.
- [ ] Every summary/cohort count equals the recomputed tally from the rows (totals add up).
- [ ] Date fields come from the data (roster service date, transfer start, received dates).
- [ ] Output is a single JSON object, no prose.

## Notes & judgment calls

- Some rules are semantic (narrative / clinical-reason mismatch, clinical-vs-administrative
  document severity). Use the ICD description and service-line context; `references/` records
  the observed conventions.
- Freshness for **documents** (family C) is computed from `received_date` vs the transfer's
  `requested_start_date`; freshness for **chart artifacts** (families D/E) is pre-computed in
  `chart_artifacts.status` — read it, don't recompute.
- The reference rubrics were derived from a handful of examples. If the live data contradicts a
  stated threshold, trust the data and the template's controlled vocabulary over the heuristic.
