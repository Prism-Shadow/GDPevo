# basis_audit Construction

Every Northstar output carries a `basis_audit` object with the same four keys. It is the auditable trail of *why* the result is what it is: which precedence rule governed, which records directly controlled the result, and which records explain the gaps/exclusions.

## Required keys

```json
"basis_audit": {
  "source_precedence": "<one of six enum values>",
  "precedence_record_order": ["<record_id>", "..."],
  "controlling_record_ids": ["<record_id>", "..."],
  "exception_record_ids": ["<record_id>", "..."]
}
```

- **`source_precedence`** — the rule that governed how competing records were weighed. One enum value (see table below). Choose the one that best characterizes the *controlling* logic for the task.
- **`controlling_record_ids`** — environment record IDs that **directly control** the result (the records the answer actually depends on). Order: **operational evidence order** — the order in which the records bear on the determination (typically the order you would cite them in a reviewer narrative: target record first, then the evidence that decides each criterion/line/row).
- **`exception_record_ids`** — record IDs that **explain a gap, exclusion, denial, missing information, or route priority** — i.e., records that shape the result by their absence, staleness, or exception status rather than by affirmatively controlling it. Order: **business gap/exception order** — criteria or route gaps **before** stale or excluded records when both appear.
- **`precedence_record_order`** — the union of controlling and exception record IDs, ordered by the `source_precedence` rule, **highest priority first**. This is the single ordered trail a reviewer can read top-to-bottom.

## Controlling vs exception — how to decide

A record is **controlling** if removing it would change the substantive answer (a criterion result, a line correction, a queue classification, a route). A record is an **exception** if it explains *why something is excluded, denied, pended, or routed differently* — its role is to justify a non-default outcome or a gap. Stale exports, non-applicable documents, missing packet items, and unresolved/`unclear` criteria typically land in `exception_record_ids`.

Worked intuition:
- UM determination: the current clinical documents that satisfy `PT-*` criteria are controlling; the stale export (`is_current=false`) that you excluded is an exception.
- Pharmacy appeal: the appeal record, denial, and documented failures that decide the path are controlling; the assistance-screen gap / missing income proof is an exception.
- Claim repricing: the effective benchmark row (matching modifier + date) is controlling; the rejected `Legacy Imaging Export` is an exception.
- P2P: the `p2p_events` record with new information (and the criteria it resolves) is controlling; criteria left `unclear` after P2P are exceptions.
- Margin queue: the below-threshold `service_margin` row(s) are controlling; charge-sensitive-but-not-below rows are exceptions only when they explain a monitor classification rather than the top issue.

## Ordering rules (recap)

- `controlling_record_ids`: operational evidence order (target → deciding evidence).
- `exception_record_ids`: criteria/route gaps first, then stale/excluded records.
- `precedence_record_order`: highest-precedence record first, down to lowest, across both controlling and exception sets.

## The six `source_precedence` rules

| `source_precedence` | Governs | When to choose |
|---|---|---|
| `current_clinical_records_over_stale_export` | Document freshness | UM nurse determination: current (`is_current=true`) clinical records control; stale exports are excluded. |
| `payer_appeal_before_manufacturer_assistance` | Appeal vs assistance ordering | Pharmacy appeal + assistance: the payer appeal path/packet/deadline controls; manufacturer assistance is secondary and denial-conditional. |
| `effective_benchmark_by_plan_modifier_and_date` | Rate schedule selection | Payment-integrity repricing: the benchmark effective for the service date and matching the plan modifier controls; stale sources are rejected. |
| `new_patient_specific_p2p_information` | P2P overturn/uphold | P2P final summary: new patient-specific information from the P2P controls the outcome; pre-P2P gaps that remain are exceptions. |
| `margin_threshold_then_charge_sensitivity` | Queue classification | Finance margin queue: the ratio-vs-threshold test controls; charge-sensitivity is a secondary monitor classification. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Routing/owner precedence | General tie-breaker when competing deadlines drive owner/route priority: appeal deadline first, then clinical, then payment-integrity. Use only when this best characterizes the controlling logic. |

## Selection guidance

The five archetypes map one-to-one to the first five rules (see `SKILL.md`'s quick table). Choose the rule that matches the archetype's controlling logic. If a task blends concerns (e.g., an appeal whose routing is dominated by its deadline rather than the assistance screen), pick the rule that characterizes what *most directly* drives the recorded result — and make sure the controlling/exception record lists reflect that same logic. The `source_precedence` string and the record lists must tell the same story.
