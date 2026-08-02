# Output contract — conforming to answer_template.json

The `answer_template.json` in each task's payloads **is the spec**. It is not itself the
answer shape you copy verbatim — it is a description (types, enums, ordering rules,
required keys). Build a JSON object that satisfies it precisely. Checklist:

## Structure
- [ ] Top level has **exactly** the keys listed in `required_top_level_keys` — none
      missing, none extra.
- [ ] Each array item includes every key its `*_item` / `*_required_keys` block lists,
      with nested objects (e.g., `charge_summary`, `payment_schedule`, `sentence_summary`)
      fully populated.
- [ ] Include an item's `task_id`/`schema_version` echo fields when the template shows
      them.

## Enums
- [ ] Every enum field uses one of the **allowed values verbatim** — never a paraphrase,
      never prose in an enum slot.
- [ ] When a value is genuinely unverifiable and the enum offers a
      `verify_before_entry` (or equivalent) option, use it instead of guessing.
- [ ] Reason-code and status enums match the exact strings the template defines.

## Formats
- [ ] Currency: JSON **number**, two decimals (e.g., `150.00`, not `"150"`).
- [ ] Dates: `YYYY-MM-DD`. Date-times: `YYYY-MM-DDTHH:MM:SS`. Times: `HH:MM`.
- [ ] Use `null` where the template says a field may be null (e.g., no disposition date
      for a held matter) — do not substitute `0`, `""`, or a placeholder unless the
      template's placeholder rule applies.
- [ ] Placeholder strings are copied **exactly** as the materials specify (commonly
      `TBD from case file`) and only for genuinely missing required fields.

## Ordering
- [ ] Sort every array per the template's `ordering_rules` — usually ascending by
      `case_number` / `citation_number` / `petition_id`, and for placeholder/exclusion
      lists by field/item name ascending. Sort `missing_fields` alphabetically.
- [ ] Sort by the secondary key when the rule names one (e.g., case_number then
      issue_type).

## Totals & counts
- [ ] Financial totals sum **posted matters only**; held/excluded/pending matters go in
      their own count fields.
- [ ] Category subtotals (fine/court-cost/assessment/user-fee) add up to the grand total.
- [ ] Counts (assessed vs held vs excluded, matter_count, installment counts) are
      internally consistent with the item lists.

## Delivery
- [ ] Return **JSON only** — no markdown fences, no commentary — when the prompt says
      "Return JSON only" / "Do not include markdown". Match the file the template
      indicates (write the result to the task's expected output location).
- [ ] Re-read the template once more and diff your object's keys/enums/formats against it
      before finishing.

## Common template families seen in this task type
Different tasks name the sections differently but they recur:
- **Audit / exceptions** list (conflicted vs corrected value + resolution source).
- **Dispositions / case memo** (identity, counsel_type, plea, charge/sentence summary,
  departure status, closeout action).
- **Fee reconciliation / financial entry** (per-line fee_code + amount, fee_status
  post/exclude/hold, case_total).
- **Docket / register** entries + rolled-up totals.
- **Payment plan / installment order** (schedule math, policy band, support class).
- **Form entries** (form_id/label enums, exact required labels, account_reference).
- **Placeholder list** (field + exact placeholder + reason code).
- **Exclusions** (unsupported item + reason code; held/pending matters kept out of the
  disposed register).
Map the current template's keys onto these roles, then fill each with verified values.
