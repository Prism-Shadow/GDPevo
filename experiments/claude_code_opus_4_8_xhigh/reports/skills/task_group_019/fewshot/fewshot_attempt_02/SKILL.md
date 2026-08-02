---
name: licensing-review
description: >-
  Produce the strict JSON answer for a GDPEVO "licensing review" task — a
  regulatory decision (contractor eligibility, restricted liquor package, or
  alcohol renewal queue) computed from a live licensing data service. Use when a
  prompt casts you as a licensing examiner/reviewer, points at a task
  environment (an environment_access.md with a base URL, GET endpoints under
  /api/{contractor,liquor,alcohol,renewal,policies}, and POST /api/sql), and
  asks for JSON matching an answer_template.json. Triggers: "licensing
  examiner/board", "eligibility batch", "restricted liquor license", "renewal
  manual-review queue", "answer_template.json", "contractor applications",
  "X-Task-Token".
---

# Licensing review

Tasks in this family give you: (1) a role + a set of **target entities**
(application ids / license numbers / a location), (2) a running **data service**
described by `environment_access.md`, and (3) an **`answer_template.json`** that
is the exact output contract. Your job is to fetch the records, apply the
regulatory decision logic encoded in `/api/policies` (and `/api/renewal/rules`),
and emit JSON that conforms to the template — nothing more.

The three families and their full decision rules are in
[`references/decision-models.md`](references/decision-models.md):
- **Contractor batch eligibility** — per-application APPROVE/HOLD/DENY with
  deficiency/action codes, risk tier, policy_impacted, and a batch summary.
- **Restricted liquor staff package** — issuance posture, same-premises basis,
  covered risks / verification gaps, standard vs location-specific controls, a
  90-day plan, and escalation triggers.
- **Alcohol renewal queue** — a ranked manual-review queue with match
  confidence, risk tier, next-step label, and a release-staff summary.

## Workflow

**1. Read the answer_template first — it is the contract.** Open
`input/payloads/answer_template.json`. Note the exact top-level keys, each
field's type, every `allowed_values` (enum) list, required lengths, ordering
rules, and how to represent "none" (empty array). The output must contain
*exactly* these keys and only values from these enums. **Code vocabularies vary
between tasks** — the same underlying fact maps to different code strings in
different templates, so always map facts to *this* template's enum.

**2. Read the prompt for parameters.** Identify: the family (contractor / liquor
/ renewal), the target ids (and the required count/order), any **review date**
or **release boundary**, the target location, and which endpoints are offered.

**3. Connect using `environment_access.md`.** It holds the base URL, the auth
header for `POST /api/sql` (e.g. `X-Task-Token: ...`), and the allowed
endpoints. Do not hardcode these — they change per task.
`scripts/licensing_client.py` parses this file and gives you `get(path)` and
`sql(query)` helpers:

```bash
python3 skill/scripts/licensing_client.py sql \
  "SELECT * FROM contractor_bonds WHERE application_id IN ('C-...','C-...')"
```

**4. Pull data with SQL, not bare GETs.** The GET list endpoints **silently cap
at 200 rows**, so records for your targets can be missing (e.g. contractor
bonds/insurance have 222 rows). `POST /api/sql` runs read-only SQLite over
tables that mirror the endpoint names (`contractor_bonds`, `liquor_settlements`,
`alcohol_violations`, `policies`, …). Filter by your target ids
(`WHERE ... IN (...)`) so results stay small and complete. `sqlite_master` and
quoted identifiers are blocked; plain `SELECT / WHERE / LIKE / IN / ORDER BY`
work. Always also fetch `/api/policies` (and `/api/renewal/rules` for renewal) —
these carry the thresholds and boundary dates; read them at runtime rather than
assuming values.

**5. Apply the family decision model.** Follow the matching table in
`references/decision-models.md`: for each target, join its records, compare
against the applicable policy standard, derive the underlying **facts**
(deficiencies / risks / gaps / violations), then map each fact to the code that
exists in this template's enum. Determine the aggregate outcome (determination /
posture / rank) and risk tier from those facts.

**6. Build the summary consistently.** Summary counts and id-lists must agree
with the per-item decisions you produced (e.g. `deny_count` equals the DENY
rows; `high_risk_application_ids` equals the high-risk items). Recompute them
from your own output, don't hand-write them.

**7. Enforce output discipline.**
- Output *only* the JSON object with exactly the template's keys — no prose,
  markdown, comments, citations, or extra keys.
- Respect every ordering rule (target ids in the required order; code arrays
  sorted as the template says — usually ascending lexical) and **dedupe** arrays.
- Use `[]` for "none applies". Include the exact required list lengths.
- Dates as `YYYY-MM-DD`. Booleans/enums exactly as spelled in the template.
- Before returning, validate: keys match; every enum value is allowed; lengths
  and ordering hold; summary is consistent.

## Notes
- Only report facts for which the template has a code. If a template lacks
  inspection codes (or a given severity), that fact is simply not emitted.
- Distinguish current/active records from expired/cancelled/dismissed
  distractors (and post-boundary `-LATE` rows) — distractors are deliberately
  included in the data.
- `verified_by_agency`/status flags are authoritative over free-text notes.
