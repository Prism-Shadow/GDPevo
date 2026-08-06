# Skill: Investigation Review Hub — Structured Legal Review Deliverable

This skill produces a **single JSON object** that answers a legal/eDiscovery
review request against the shared **Investigation Review Hub** (a grand-jury /
SEC / DOJ subpoena review environment). It applies to any matter in this family:
rolling-production gap analysis, retention & litigation-hold gap review,
cross-system remediation dashboard, or production-readiness review.

These are reusable operating rules. They contain **no task-specific answer
values** — no matter's findings, counts, category assignments, or record IDs.
Apply the rules to whatever matter and schema the task hands you.

---

## 0. When to use

Use this skill when a task asks you to review a matter in the Investigation
Review Hub and return a structured-JSON deliverable (gap analysis, retention
review, remediation dashboard, production-readiness review). The signal phrases:
"Investigation Review Hub", "source of record", "conforms to
`input/payloads/answer_template.json`", and the repeated prohibition on local
env/db/manifest/answer files.

## 1. Contamination guard — run first

Before doing anything, scan the working directory. The only legitimate contents
are:

- `environment_access.md` (network access only)
- the task input directory (`prompt.txt` + a `payloads/` folder containing an
  `answer_template.json` schema and one client-facing context JSON)

If anything else is present — answer files, evaluation/grading files, generated
manifests, database/seed files, setup scripts, hidden notes, or files outside
the expected layout — **stop immediately** and write `contamination_report.txt`
describing the unexpected material. Do **not** produce an answer. Do not read
the contaminating files for evidence.

The `answer_template.json` files are **schemas** (they explicitly state they do
not contain the answer) and are legitimate inputs, not contamination.

## 2. Source rules — what is and isn't allowed

- **Allowed for network access:** `environment_access.md` only. It gives the
  base URL, the `X-API-Key: review-key-017` header, and the allowed endpoint
  list. See `references/hub_schema.md`.
- **Allowed for evidence:** the hub endpoints (GET endpoints + the read-only
  `POST /api/query` SQL endpoint with the API-key header).
- **Allowed for context:** the task-local payload files (the schema
  `answer_template.json` and the client-facing context JSON — they supply the
  `matter_id`, client name, and request category labels only).
- **Forbidden:** local environment source files, database files, generated
  manifests, setup/seed scripts, hidden notes, and any standard-answer or
  evaluation files. Never open them. If a count or ID is not derivable from the
  hub, leave the hub as the gap — do not backfill from forbidden sources.

## 3. Output contract — every time

- Return **exactly one JSON object**. No prose, no markdown fences, no
  commentary outside the JSON.
- Conform to **this task's** `answer_template.json`: its
  `required_top_level_keys`, each section's `item_required_keys`, its `enums`,
  its `field_types`, and its `numeric_precision`.
- Use **only** enum values listed in the template. Never invent enum strings,
  section names, or field names. Different tasks name sections differently
  (`critical_findings` vs `top_risks` vs `issue_ledger`, `metrics` vs `metrics`,
  `priority_actions` vs `action_plan`) — follow the exact key names in the
  template in front of you.
- All counts are **whole integers**. Use `0` when a count is not applicable —
  never null for a count. Use `null` only where the schema explicitly permits
  "or null" (e.g. dates, third_party, policy_section).
- Readiness / production-ready flags are **booleans**.

## 4. Stable IDs and category codes

- Carry hub IDs through **verbatim**: `matter_id`, `source_id`, `event_id`,
  `finding_id`, `doc_id`, `entry_id`, `action_id`, `batch_id`, and
  `category_code`. Never invent or reformat them.
- The authoritative category codes for a matter come from the hub's
  `subpoena_categories` for that `matter_id`. The client-facing context JSON may
  label them, but the codes themselves are confirmed against the hub.
- Anchor each finding/risk/issue object to a stable hub record ID (its
  `finding_id` / `risk_id` / `issue_id` / `correction_id`), and list supporting
  hub record IDs in the `*_refs` fields.

## 5. Sorting rules — always applied

Apply the template's `ordering_rules`, and as a default where the template is
silent:

- Sort each list of objects by its stable ID ascending, **or** by
  `priority_rank` / `rank` ascending where 1 is highest priority (per the
  template).
- Sort every list of category codes **ascending** (uppercase codes, lexical).
- Sort every `*_refs` list of hub record IDs **ascending** (lexical).

## 6. Assembly workflow

1. **Read access + schema.** Read `environment_access.md` for the base URL, API
   key, and allowed endpoints. Read the task payload: `answer_template.json`
   (the schema you must conform to) and the context JSON (for the `matter_id`,
   client, and category labels).
2. **Confirm the matter and its categories.** `GET /api/matters` (or query the
   `matters` table) for the matter; note `hold_date` (the preservation dividing
   line). `GET /api/subpoena-categories` for the matter → the authoritative
   category code set.
3. **Pull all evidence for the matter** across the evidence tables:
   productions, custodian-sources, review documents, privilege-log, qc-findings,
   retention-events, remediation-actions. Use `POST /api/query` for filtered and
   aggregate rollups (e.g. counts by category, post-hold loss events, withheld
   vs. logged sums, unlogged = withheld − logged).
4. **Classify each category** against the template's `category_status` (or
   `readiness_status`) enum from the assembled evidence. One status object per
   category that has a material non-complete / non-ready status.
5. **Build the findings/risks/issues ledger.** One object per material gap or
   defect, anchored to a stable hub record ID. Map each hub record's issue to
   the template's `issue_type` enum faithfully — do not relabel. Recurring
   archetypes and their typical hub signals:
   - **preservation_failure / post_hold_loss** — source/retention loss with
     `post_hold=1` or event after `hold_date`.
   - **policy-compliant retention loss** — loss dated **before** `hold_date`
     under a stated `policy_section` (lower risk; may warrant `no_action`).
   - **collection_gap / uncollected_source** — source `status` not collected or
     partial.
   - **responsiveness_miscode** — document `responsiveness` conflicts with
     category production or a zero-claim assertion (`zero_claim_reason`).
   - **privilege_log_gap** — `withheld_count` exceeds `logged_count` (unlogged >
     0).
   - **third_party_waiver / privilege_waiver** — `third_party=1` or
     commingled/forwarded privileged material.
   - **miscoded_privilege / over_designation** — privilege status coding defect
     (per qc-findings / privilege issue_type).
   - **missing_required_record** — a record that should exist is absent.
6. **Identify retained/available remediation sources** (when the template has a
   `retained_or_available_sources` / `available_archives` section): sources still
   available that limit irretrievable loss for specific categories. Record which
   categories each source limits.
7. **Compute metrics** as whole integers from the hub, scoped to the matter and
   to the exact subset the template names. Watch for scope qualifiers in the
   schema (e.g. "from selected incomplete-log blockers only",
   "destroyed source named in the task") — count only that subset. Derive
   dependent counts arithmetically: `unlogged = withheld − logged`.
8. **Build the prioritized action plan.** Rank 1 = highest priority. Assign
   `action_type` and `owner` from the template's enums. Point `target_refs` at
   the hub records the action remediates (sorted ascending). Map each action to
   the categories it affects (sorted ascending). Map severity/risk and priority
   consistently with the findings.
9. **Validate before emitting:**
   - all `required_top_level_keys` present;
   - every object has all its `item_required_keys`;
   - every enum value is in the template's allowed list;
   - every list sorted per §5;
   - all counts are integers, `0` where not applicable;
   - readiness flags are booleans;
   - output is exactly one JSON object, no surrounding prose.

## 7. Common pitfalls to avoid

- **Accepting a zero-claim at face value.** A category marked "nothing
  responsive" (`zero_claim_reason`) must be cross-checked against documents and
  custodian sources before you mark it complete — contradictions are a material
  finding.
- **Treating pre-hold and post-hold losses the same.** Pre-hold policy
  destruction may be compliant (low risk / `no_action`); post-hold loss is a
  preservation failure. Always compare event dates to `hold_date`.
- **Mixing the privilege log scope.** Withheld vs. logged counts and the
  unlogged delta must come from the same privilege-log rows the template scopes
  to — don't aggregate across all entries when the schema says "selected
  incomplete-log blockers only."
- **Inventing IDs or category codes.** If the hub doesn't expose a record, you
  cannot fabricate a stable ID for it. Anchor findings only to real hub records.
- **Forgetting source_refs.** Every finding/category/action that the schema asks
  to be backed must cite hub record IDs — unsupported claims fail the schema.
- **Outputting prose.** The deliverable is one JSON object. No narrative, no
  fences, no trailing explanation.

## 8. Reference

- `references/hub_schema.md` — hub endpoint list, API-key header, and the full
  table/column map with which table backs which deliverable section.
