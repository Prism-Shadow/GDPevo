---
name: licensing-review
description: >-
  Produce structured JSON licensing-review decisions against a shared state
  licensing data service. Covers three recurring task families: (A) contractor
  application batch eligibility reviews, (B) restricted liquor-license staff
  packages, and (C) alcohol renewal manual-review queues. Use this whenever a
  prompt asks you to act as a licensing examiner / renewal-unit staffer, points
  you at the licensing environment endpoints (/api/policies, /api/contractor/*,
  /api/liquor/*, /api/alcohol/*, /api/renewal/rules, /api/sql), and asks for a
  JSON answer that must conform to an input/payloads/answer_template.json.
---

# Licensing Review

## What these tasks are

Each task is a licensing-decision problem solved from a shared read-only data
service. The prompt names one or more target entities, the answer template
fixes the exact output schema and enum vocabulary, and `environment_access.md`
gives the base URL, an auth token, and the allowed endpoints. Your job is to
gather the relevant records, apply the governing policy/rule logic, and emit
**only** JSON that conforms to the answer template.

The decision *logic* is stable across tasks. What changes per task is: the
target IDs, the review/boundary date, and — critically — the **exact enum codes
and keys the answer template allows**. Never copy codes from one task into
another; always bind your findings to the vocabulary in the current
`answer_template.json`.

## Three task families — detect first

Read the prompt and the answer template together, then classify:

| Family | Prompt signals | Answer template shape | Playbook |
|---|---|---|---|
| **A. Contractor batch** | "Licensing Examiner", "State Contractors Licensing Board", a batch/list of `C-…` application IDs | `application_decisions[]` (per-app `determination` APPROVE/HOLD/DENY + `deficiency_codes` + `required_actions` + `risk_tier` + `policy_impacted`) plus a `summary` | `references/contractor_playbook.md` |
| **B. Liquor staff package** | "restricted liquor license", one `L-…` application + a `LOC-…` location | single object: `recommended_posture`, `same_premises_basis_applies`, `covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes` | `references/liquor_playbook.md` |
| **C. Alcohol renewal queue** | "Alcohol Renewal Unit", "manual-review queue", `AL-…` license IDs, a **release boundary** date and target queue size | `queue[]` (ranked) plus `summary` | `references/renewal_playbook.md` |

## Standard workflow

1. **Classify** the family (table above).
2. **Parse the prompt** for: target entity IDs, target location (family B),
   review date (family A) or release boundary + queue size (family C), and the
   `<TASK_ENV_BASE_URL>` placeholder.
3. **Read `answer_template.json` fully.** Extract the exact top-level keys,
   per-item schema, the allowed enum values for every coded field, required
   list length, ordering rules, and empty-value handling. This is your output
   contract — see `references/output_contract.md`.
4. **Read `environment_access.md`** for the concrete base URL, the
   `X-Task-Token`, and the allowed endpoint list. Use `/api/sql` only when a
   token is provided and the endpoint is allowed.
5. **Fetch governing rules first.** Always pull `/api/policies` (families A & B)
   or `/api/renewal/rules` (family C) and parse each row's `details_json` —
   the numeric thresholds and boolean toggles that drive decisions live there.
   **Read them at runtime; do not hardcode threshold numbers.**
6. **Fetch and join the records** for each target (see `references/data_model.md`
   for endpoints ↔ SQL tables and join keys).
7. **Apply the family playbook** to reach determinations, reading every
   threshold from the policy/rule `details_json`.
8. **Map findings to the template vocabulary** — translate each underlying fact
   to the specific allowed code in *this* template.
9. **Build the summary** so it is internally consistent with the item-level
   decisions (counts, high-risk lists, etc.).
10. **Emit only the JSON** — correct keys, correct ordering, deduped lists,
    empty arrays where nothing applies, exactly the target entities and length
    required.

## Data access in one place

- Endpoints return JSON arrays. The same data is queryable via `POST /api/sql`
  with body `{"query": "SELECT …"}` and header `X-Task-Token: <token>`.
- SQL is **SELECT-only**; `PRAGMA` and `sqlite_master` are blocked; results
  default to `LIMIT 200` (use explicit `LIMIT`/`COUNT`/`WHERE`, or page).
- Table names are the underscored form of the endpoint path
  (e.g. `/api/contractor/license-history` → `contractor_license_history`).
- A ready generic client is in `scripts/query_env.py` (reads base URL + token
  from `environment_access.md`; exposes `get(path)` and `sql(query)`).

Full endpoint/table/field/join reference: `references/data_model.md`.

## Rules that apply to every family

- **Vocabulary is per-task.** Two tasks in the same family use *different* code
  sets (e.g. contractor deficiency `bond_cancelled` vs `no_active_bond`). Emit
  only codes present in the current template.
- **Thresholds come from the environment**, not memory. Match each entity to its
  governing policy/rule and read `details_json`.
- **Filter by the field the rule names**, not by look-alike labels. E.g. the
  renewal boundary filters on `violation_date`; a `source_name` like
  `post_boundary_feed` is a distractor, not the filter.
- **Applicant/self-reported assertions are not verification.** Only trust a
  correspondence/evidence item when the record marks it agency-verified/current.
- **Output is JSON only** — no prose, markdown, comments, citations, or keys
  outside the template. Dates are `YYYY-MM-DD`.

## Common pitfalls

- Emitting a code that is valid in a sibling task but absent from the current
  template's `allowed_values`.
- Hardcoding a threshold (bond/insurance/experience minimum, boundary date)
  instead of reading it from `details_json` for the *applicable* rule.
- Treating a distractor source/theme (`post_boundary_feed`, `late renewal`) as a
  real signal.
- Summary counts that don't match the per-item determinations, or list fields
  that aren't sorted/deduped as the template demands.
- Wrong list length or missing/extra target entities.
