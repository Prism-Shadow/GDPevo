# Formatting, Enums & Output Discipline

The output is validated against `answer_template.json`. A structurally correct analysis still fails if a value is the wrong type, wrong precision, or not in the allowed enum. These rules are mechanical — apply them on every field.

## Units & precision

Precision is **task-specific** — always read the template's `units` block. Do not assume a default.

| Quantity | Typical forms seen | Rule |
|---|---|---|
| Currency | `integer USD` | Integer dollars, no decimals, no `$`, no commas. Round half up. |
| Percent points | `2 dp`, `1 dp`, whole | Decimal number at the precision the template states. `18.0`, `18.00`, or `18` — match exactly. |
| Holder / fully-diluted % | `4 dp` | e.g., `0.3820` when the cap table stores fractions. Confirm whether the template wants the fraction or percent-points form. |
| Months | integer | Integer months, no decimals. |
| Dates | `YYYY-MM-DD` | Four-digit year, zero-padded month/day. Use the date as recorded; do not reformat. |
| Counts | integer | Integer. |
| Booleans | `true` / `false` (JSON) | Literal JSON booleans, not strings, unless the template shows string enums. |
| `null` | only where permitted | If the template field says "number or null" / "integer or null", emit `null` when the value does not apply — never `0` to mean "not applicable", and never omit a required field. |

## Enum conformance

- Every enum field has an `allowed_enums` (or inline "one of: …") list in the template. Emit **only** values from that list, with exact spelling and case (`LOW`, not `low` or `Low`; `approve_with_conditions`, not `Approve With Conditions`).
- Common enums and their members (verify against the specific template — members vary):
  - `risk_rating`: `LOW`, `MEDIUM`, `HIGH`
  - `issue_status`: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`
  - `recommended_action`: `delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`
  - `business_outcome`: `closing_certainty`, `escrow_economics`, `indemnity_exposure`, `restrictive_covenants`, `employee_transition`, `tax_allocation`, `governing_law`, `regulatory_efforts`
- Some templates use **string unions** instead of generic enums (e.g., `materiality_scrape_required: "FULL_BREACH_AND_DAMAGES | BREACH_ONLY | NONE"`, `hell_or_high_water_required: "yes | no | limited covenant"`). Copy those literal strings exactly.

## Stable IDs

- Use IDs **verbatim** from the workbench: `term_id`, `consent_id`, `contract_id`, `finding_id`, `estimate_id`, `employee_id`, `note_id`, `benchmark_id`, `holder` name, `security_class`. Do not paraphrase or renumber.
- For issues/redlines the template defines its own **stable IDs** (e.g., `possible_issue_ids`, `stable_issue_ids`, `stable_redline_ids`). Use exactly those strings; do not invent new IDs.
- For a missing required term, `source_term_ids` is `[]` (empty array) — never null, never omitted if the field is required.
- Synthetic IDs (e.g., a regulatory blocker with no consent/contract id) should follow the template's stated convention (e.g., `blocker_type` + related id); only synthesize when the template explicitly allows it.

## Ordering

Follow the template's ordering instructions exactly. Common rules:
- `transition_issues` / `issue_register`: sort by `issue_id` ascending unless a `priority_order` is requested elsewhere.
- `required_redlines`: sort by `redline_id` ascending.
- `priority_order` / `operational_risk.priority_order`: highest negotiation priority first — order is a judgment call driven by risk_rating, dollar exposure, and closing-blocker status, not alphabetical.
- `holder_allocation`: typically by `fully_diluted_pct` descending or by holder name — match the template.
- `negotiation_priority` / `priority_rank`: assign sequential ranks; lowest rank = highest priority unless the template says otherwise.

## JSON-only output

- Return **one** JSON object. No leading/trailing prose, no markdown fences, no explanations, no "Here is the…".
- The object must conform to the template's top-level shape. Include every required top-level field even if some nested arrays are empty.
- Valid JSON only: double-quoted strings, no trailing commas, no comments.
- Do not include fields the template does not define (extra fields risk rejection). If a value is genuinely not applicable and the field allows null, use `null`; if the field is optional and unused, omit it only if the template treats it as optional.
- Numbers that must be integers are integers (`150000000`, not `1.5e8` or `150000000.0`).

## Final self-check before emitting

1. Every enum value is in `allowed_enums` (exact case).
2. Every currency field is an integer; every percent field is at the template's precision; every month is an integer; every date is `YYYY-MM-DD`.
3. Every required field is present; nulls only where permitted.
4. Every ID is copied verbatim from the workbench or from the template's stable-ID list.
5. Arrays are sorted per the template.
6. Output is a single JSON object with no surrounding text.
