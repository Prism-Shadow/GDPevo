# Licensing Examiner Skill

Reusable methodology for evaluating licensing applications, building staff review
packages, and constructing manual-review queues against a shared licensing data
environment.  This skill covers contractor eligibility batches, restricted liquor
license transfers, and alcohol renewal screening — any task where you must fetch
records from the licensing API, cross-reference them against business rules, and
produce structured JSON decisions.

---

## Phase 1 — Environment Bootstrapping

Every task begins by locating and reading the environment descriptor.

1. Read `environment_access.md` from the working directory.  It contains:
   - `base_url` — the root of the licensing data service
   - `credentials` — required headers (notably `X-Task-Token` for SQL)
   - `allowed_endpoints` — the full set of available API routes

2. Replace every occurrence of `<TASK_ENV_BASE_URL>` in the prompt with the
   `base_url` from `environment_access.md`.  All GET/POST calls go to routes
   under that base.

3. The SQL endpoint (`POST /api/sql`) requires the header
   `X-Task-Token: licensing-review-019`.  No other endpoints require this header.
   SQL is the escape hatch — use it when the standard GET endpoints cannot
   express a necessary join, filter, or aggregation.  Prefer the purpose-built
   GET endpoints first; they are simpler and less error-prone.

---

## Phase 2 — Task Discovery

Every task provides two input files under `input/`:

| File | Purpose |
|---|---|
| `prompt.txt` | Human-readable task description, target identifiers, applicable endpoints, and any review-date or boundary-date constants. |
| `payloads/answer_template.json` | The exact JSON schema the output must satisfy — top-level keys, field types, allowed enum values, ordering rules, and constraints on list lengths. |

**Procedure:**

1. Read `prompt.txt` fully.  Extract:
   - The **task type** (batch eligibility, staff package, or renewal queue — see
     [task-patterns.md](references/task-patterns.md) for the catalog).
   - The **target identifiers** (application IDs, license numbers, location codes).
   - The **review date** or **boundary date** if one is stated.
   - The **list of suggested API endpoints**.

2. Read `payloads/answer_template.json` fully.  Internalize every constraint:
   - Required top-level keys
   - Enum value sets (every code, action, posture, tier)
   - Ordering rules (ascending by ID, alphabetical, by date)
   - Required lengths and empty-value conventions

3. If any suggested endpoint is absent from `environment_access.md`, skip
   it — only call endpoints listed in the environment descriptor.

---

## Phase 3 — Data Collection

### General Strategy

1. Always start with `GET /api/policies` — it provides the current rule baseline
   that may change how other records are interpreted.

2. Fetch the core entity collection next:
   - Contractor tasks → `GET /api/contractor/applications`
   - Liquor tasks → `GET /api/liquor/applications`
   - Renewal tasks → `GET /api/alcohol/licensees`

3. Then fetch each supporting record collection in parallel.  The full set of
   available GET routes is in the environment descriptor; only call those
   relevant to the task type.

4. Use `POST /api/sql` when you need to:
   - Join entities across collections on a shared key
   - Filter by date ranges (e.g., violations before a boundary date)
   - Aggregate (count, max date, group by)
   - Answer a question the flat GET endpoints cannot answer alone

### Domain-Specific Fetching

**Contractor tasks** (`/api/contractor/*`):
- `applications` — applicant identity, license class, experience summary
- `bonds` — bond amount, status (active/cancelled), effective dates
- `insurance` — coverage amount, expiry date, binding status
- `license-history` — prior licenses, suspensions, revocations
- `violations` — open/closed violations, severity
- `correspondence` — stale or unverified correspondence
- `inspections` — document gaps, safety rechecks

**Liquor tasks** (`/api/liquor/*`):
- `applications` — applicant, premises, license class
- `settlements` — tax holds, board orders
- `privileges` — special operating privileges
- `incidents` — reported incidents at the premises
- `site-evidence` — camera evidence, floor plans, signage, photos, police memos,
  neighbor notices

**Alcohol renewal tasks** (`/api/alcohol/*` + `/api/renewal/*`):
- `licensees` — license identity, facility name, status
- `violations` — violation records with dates and IDs
- `renewal/rules` — renewal criteria and rule parameters

---

## Phase 4 — Decision Logic

The reasoning patterns differ by task type; see
[task-patterns.md](references/task-patterns.md) for per-type decision trees.
Below is the cross-cutting logic shared by all types.

### Cross-Cutting Decision Principles

1. **Policy-first reasoning.**  Every analysis starts from the current policy
   baseline (`GET /api/policies`).  A deficiency that exists only because a
   policy changed is a *policy-impacted* finding.  A deficiency that would have
   existed under the prior baseline is not policy-impacted.

2. **Financial-coverage checks (bonds & insurance).**  For each application:
   - Is there an active bond?  If no → deficiency (bond not active / cancelled).
   - Does the bond amount meet the required minimum?  If no → bond shortfall.
   - Is insurance current (not expired as of the review date)?  If no →
     insurance not current / expired.
   - Does insurance coverage meet the required minimum?  If no → insurance shortfall.
   - Is insurance still pending (not yet bound)?  If yes → insurance pending.

3. **Endorsement checks.**  For each application:
   - Are all required specialty endorsements verified?  If no → endorsement not
     verified / missing / pending.

4. **Experience checks.**  Does the applicant meet the minimum experience
   threshold for the license class?  If no → experience shortfall.

5. **Compliance-history checks.**  For each application/licensee:
   - Are there open serious violations?  If yes → serious-violation deficiency.
   - Are there open minor violations?  If yes → minor-violation deficiency.
   - Is there an active suspension?  If yes → active-suspension deficiency.
   - Are there unresolved complaints?  If yes → unresolved-complaint deficiency.

6. **Inspection checks (contractor).**  Are there inspection document gaps or
   safety rechecks needed?

7. **Site-evidence checks (liquor).**  Are there missing or conflicting site
   evidence items (cameras, floor plans, signage, photos, police memos, neighbor
   notices)?

8. **Risk-tier assignment.**  Use the severity and count of deficiencies:
   - `high` — active suspension, open serious violations, multiple severe
     financial-coverage failures, or a pattern requiring board review.
   - `medium` — curable deficiencies (bond shortfall, expired insurance, pending
     endorsements, experience shortfall) without a suspension or serious pattern.
   - `low` — no material deficiencies; application is approvable.

9. **Determination.**  Map deficiencies to a posture:
   - `APPROVE` / `issue_restricted` — no deficiencies, or deficiencies already
     resolved.
   - `HOLD` / `request_follow_up` — curable deficiencies; applicant can resolve
     them.
   - `DENY` — uncurable or severe deficiencies (active suspension, serious
     unresolved violations, board-level issues).

### Correspondence Staleness

When correspondence records include dates or status fields, flag any item that
is stale (older than a reasonable review window) or unverified.  Include those
IDs in the summary's `stale_or_unverified_correspondence_ids`.

### Boundary-Date Logic (Renewal Queue)

When a boundary date is given (e.g., "release boundary is 2025-04-10"):
- Violations dated **on or before** the boundary are in scope.
- Violations dated **after** the boundary are excluded and listed in
  `post_boundary_violation_ids_excluded`.
- The `most_recent_violation_date` and `violation_count` only reflect in-scope
  violations.

### Match Confidence (Renewal Queue)

When matching violation records to licensees:
- `exact` — violation's license identifier matches exactly.
- `close_address` — match is on address or facility name, not license number.
- `uncertain` — match relies on partial or inferred linkage.

---

## Phase 5 — Output Construction

1. Build the JSON object top-down, matching the keys and structure in
   `answer_template.json` exactly.

2. **Ordering rules** — obey every ordering constraint in the template:
   - Lists of application/license IDs: ascending lexical order.
   - Code lists: the ordering rule stated in the template (alphabetical,
     ascending, or "any order").
   - Queue entries: by ascending rank with no gaps.
   - Violation IDs: by date ascending, then ID ascending.

3. **Empty values** — use `[]` for empty code/ID lists, `0` for zero counts.
   Never use `null` where the template expects a list or integer.

4. **No extraneous output.**  Return only the JSON object.  No prose, no
   markdown fences, no citations, no commentary, no keys not shown in the
   template.

5. **Summary consistency.**  The summary must be mechanically consistent with
   the item-level decisions:
   - `approve_count` + `hold_count` + `deny_count` = total applications.
   - `high_risk_application_ids` = every application with `risk_tier: "high"`.
   - `policy_impacted_application_ids` = every application with
     `policy_impacted: true`.
   - `stale_or_unverified_correspondence_ids` = every stale or unverified
     correspondence ID found across all applications.

---

## Phase 6 — Verification (Before Returning)

1. Every target identifier from the prompt appears in the output exactly once.
2. Every list length matches its stated constraint.
3. Every enum value is from the template's allowed set.
4. Summary counts sum correctly.
5. Ordering rules are satisfied.
6. No prose, no markdown — pure JSON.

---

## Reference Files

- [task-patterns.md](references/task-patterns.md) — catalog of the three task
  types, their API endpoints, field schemas, and decision trees.
- [domain-concepts.md](references/domain-concepts.md) — glossary of every
  deficiency code, risk code, verification gap code, obligation code, check
  code, escalation trigger code, and action code seen across the training
  distribution, with the conditions that trigger each one.
