# Output Conventions

The deliverable is **exactly one JSON object** conforming to
`answer_template.json`.

## Format

- Return a single JSON object only. **No** markdown fences, **no** comments,
  **no** prose or narrative outside the JSON.
- Include every required top-level key and every required nested key listed in
  the template.
- Respect `additional_fields_allowed`: when false (the default), include **no**
  keys beyond those defined; when allowed, extra keys are permitted but not
  evaluated.
- Every enum value must exactly match one of the template's allowed choices
  (case and spelling). Never invent enum values.

## List ordering

Follow each field's `ordering` rule precisely. Common patterns observed across
templates:

- **Documents** (`evidence_documents`, `excluded_documents`): ascending by
  `document_id`.
- **CPT lists** (e.g. `approved_cpt`): ascending CPT code.
- **Claim lines** (`lines`): claim-line order (ascending `line_number`).
- **Margin rows** (`rows`): the same order as
  `task_context`'s queue row IDs list.
- **Segment / medication lists** (`below_threshold_segments`,
  `documented_failures`, etc.): alphabetical.
- **Packet item lists**: "operational packet order" (payer appeal items before
  assistance items) for `required_packet_items`; "case-specific gap order"
  (appeal evidence gaps before assistance information gaps) for
  `missing_packet_items`.
- **`unresolved_criteria`**: ascending criterion ID.
- **`basis_audit` lists**: see `basis_audit.md` (evidence order; gap/exception
  order; precedence order).

## Numeric precision

- **Currency:** JSON numbers in USD, rounded to **two decimals** (cents). Apply
  per-unit amounts before summing (e.g. line allowed = benchmark rate × units,
  rounded; totals are the sum of rounded lines).
- **Ratios:** precision per template (commonly **4 decimals**).
- **Integers:** service/claim-line **units** as integers.
- **`recovery_amount`:** signed by direction — the underpayment amount
  (corrected − paid) when the corrected allowed total exceeds the paid total;
  follow the template's direction for overpayments.

## Dates, modifiers, and nulls

- **Dates:** ISO 8601 `YYYY-MM-DD` (calendar day precision).
- **Periods:** `YYYY-MM`.
- **Modifiers:** use **`null`** (not `""`) when a claim/request line has no
  modifier.
- **Computed deadlines** (e.g. internal appeal deadline): calendar days from the
  determination date using the window given in `task_context` (e.g. 180 days).
  Use `null` only when the template says no deadline applies.
- **Booleans:** use JSON `true`/`false`, not strings.

## Final self-check

Before returning, verify against the template: all required keys present; enum
values valid; list orderings correct; numeric precision and currency rounding
correct; `null` used where required; no extra keys when disallowed; and the
`basis_audit` follows the ordering rules in `basis_audit.md`.
