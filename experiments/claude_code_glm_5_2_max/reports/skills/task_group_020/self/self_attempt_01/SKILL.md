---
name: ma-deal-workbench
description: Prepare a structured M&A deliverable from a running deal workbench. Use when a task positions you as buyer- or seller-side counsel for a specific deal (deal_id like PRJ_<NAME>), points you at a deal workbench API plus an answer_template.json, and asks for a JSON-only structured review that compares current draft terms against a playbook or committee policy. Covers issue registers, deviation/position matrices, closing & economics packages, committee escalation memos, and carveout transition/separation reviews.
---

# M&A Deal Workbench — Structured Review

This skill produces a single JSON object that conforms to the task's
`input/payloads/answer_template.json`. It is reusable across any deal, side,
and deliverable shape that follows the workbench convention below.

## When to use

Use this skill when the task has all of these markers:

- You are cast as **buyer-side or seller-side counsel** for one named deal
  (deal_id follows a `PRJ_<NAME>` pattern).
- A **deal workbench** is available at `<TASK_ENV_BASE_URL>` with documented REST
  routes and a read-only SQL endpoint.
- An **answer template** exists at `input/payloads/answer_template.json` and the
  task says to return only JSON conforming to it.
- The work is to **compare current draft terms against a playbook or committee
  policy**, classify issues, quantify exposure, and aggregate a summary.

Do not use this skill for tasks that have no workbench, no answer template, or
that ask for prose/narrative advice rather than a structured JSON artifact.

## What you produce

Exactly one JSON object. No prose, no markdown fences, no commentary outside the
JSON. Every field, enum value, ID, unit, and ordering rule comes from the
template — the template is the contract, not these instructions.

## Operating rules (apply to every task, in order)

1. **Parse the prompt.** Extract: client side (buyer/seller), `deal_id`, the
   governing playbook or policy id, the deliverable type, the template path, and
   any per-task unit/precision rules the prompt states explicitly.

2. **Load the answer template first.** Read `input/payloads/answer_template.json`
   before touching the workbench. It defines: required top-level fields, allowed
   enums (`risk_rating`, `issue_status`, `recommended_action`, business outcomes,
   etc.), the stable issue/redline IDs you may use, units, and ordering. Never
   invent an enum value, issue id, or field the template does not permit.

3. **Resolve network access from `environment_access.md`.** Read
   `environment_access.md` in the task working directory. It is the **only**
   source for the workbench base URL, the read-only SQL token, and the allow-list
   of endpoints. Use only the endpoints it lists; do not invent routes or
   hardcode the URL/token into your work. The prompt's `<TASK_ENV_BASE_URL>`
   placeholder resolves to the base URL found there. See
   `reference/workbench.md`.

4. **Pin to the exact `deal_id`.** Filter every request by the deal_id from the
   prompt. Never assume records from a similarly named project apply to your
   deal_id. When a route takes `<deal_id>`, substitute the prompt's value.

5. **Gather the full record set.** Pull deal record, current draft terms, the
   applicable playbook rules (or policy thresholds), risk estimates, employees,
   consents, material contracts, regulatory, diligence findings, benchmarks, cap
   table, notes, and documents — whichever the deliverable requires. See
   `reference/workbench.md` for what each route returns.

6. **Cross-check with read-only SQL.** Use `POST /api/query` (token from
   `environment_access.md`) to reconcile across tables — verify a term exists,
   sum PTO across employees, confirm holder allocation sums to 100%, join
   consents to material contracts. Use it to verify, not as the primary read path.

7. **Classify each draft term against the playbook/policy.** For every term the
   deliverable covers, assign an `issue_status` by comparing the draft metric to
   the playbook's preferred and fallback positions (or the policy threshold).
   Treat draft silence as `missing_required_term` when the side's position
   requires an affirmative provision. For escalation tasks, include only
   out-of-policy / restricted terms and exclude stale, in-policy, and distractor
   terms. See `reference/classification.md` and `reference/side_posture.md`.

8. **Quantify from the correct base.** Compute dollar amounts from the headline
   purchase price unless a source (memo `value_basis`, policy, finding) states a
   different basis (equity value, upfront cash, identified findings, annual
   revenue). Compute deltas/shortfalls to preferred and fallback; sum PTO,
   consent amounts at risk, and material-contract revenue requiring consent; pull
   exposure low/high from risk estimates by `source_estimate_id`.

9. **Apply units and precision exactly as the template states.** Defaults: integer
   USD; percent points to two decimals; months as integers; dates as
   `YYYY-MM-DD`. But the template overrides — some tasks want one decimal, whole
   percent points, or holder percentages to four decimals. Read the template's
   `units`/`instructions` and follow it, not these defaults. See
   `reference/classification.md`.

10. **Use stable IDs only.** Reuse the workbench's own IDs verbatim
    (`term_id`, consent/`source_id`, `contract_id`, `finding_id`, `employee_id`,
    `estimate_id`, holder name, security class). For issue/redline IDs, use only
    the stable IDs enumerated in the template. Use an empty array `[]` for
    `source_term_ids` when a required term is missing from the draft. Use `null`
    for fields with no value; never omit a required field.

11. **Order per the template.** Sort issue registers by `issue_id` or counsel
    workflow as the template directs; put `priority_order` /
    `negotiation_priority` from highest to lowest negotiation priority; sort
    redlines by `redline_id` ascending; assign `priority_rank` per the template's
    convention.

12. **Aggregate / summarize.** Produce the template's summary object: issue
    counts, risk counts, quantified exposure low and high (aggregated separately,
    excluding components the template says to exclude), negotiation deltas,
    consent amounts at risk, employee/PTO totals, and a final closing-readiness /
    blocker classification or overall recommendation.

13. **Emit one JSON object and stop.** Output only the JSON conforming to the
    template. No narrative. No extra keys outside the template except where it
    explicitly allows free-form objects (e.g., `must_have_terms`,
    `draft_value_normalized`, `covenant_limits`).

## Recurring deliverable shapes

The template tells you which shape applies. Recognize them so you gather the
right records:

- **Issue register + priority order + summary metrics** — term-by-term draft vs
  playbook review (seller or buyer), with quantified impact and a priority list.
- **Deviation / position matrix** — each issue with draft/preferred/fallback
  metrics, a `final_position`, priority rank, and closing blockers + risk totals.
- **Closing & economics package** — holder-level consideration allocation,
  indemnity/escrow/survival/working-capital mechanics, required consents,
  regulatory/HSR status, employee/PTO/covenant treatment, D&O tail and expense
  allocation, and a final closing-readiness / blocker classification.
- **Committee escalation memo** — only out-of-policy or restricted terms, each
  with policy comparison, quantified exposure, benchmark support, recommendation,
  and required conditions, plus an aggregate committee summary with routing
  fields.
- **Transition / separation review** (carveout APA) — IP/domain transition,
  transition-services scope/fees, Section 1060 allocation, transfer-tax split,
  employee continuity, outside-date protection, governing law/forum, with
  required redlines and an operational-risk summary.

## Side posture (direction of "out of policy")

Buyer-side work protects the buyer (higher indemnity caps, lower baskets, longer
survival, full materiality scrape, escrow, all consents as closing conditions);
seller-side work protects the seller (lower caps, higher baskets, shorter
survival, minimal escrow, capped restrictive covenants, seller-favorable tax and
governing law, capped transition services). The same draft term can be
`draft_exceeds_playbook` for one side and `draft_below_playbook` for the other —
classify from your client's side as stated in the prompt. See
`reference/side_posture.md`.

## References

- `reference/workbench.md` — resolving access from `environment_access.md`,
  endpoint purposes, deal_id pinning, read-only SQL cross-checks, stable IDs.
- `reference/classification.md` — `issue_status` taxonomy, classification
  procedure, quantification rules, units/precision, ordering, output discipline.
- `reference/side_posture.md` — buyer vs seller default protective positions and
  the direction of out-of-policy classification.
