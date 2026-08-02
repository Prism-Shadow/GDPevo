# Reconciliation, determination, and math reference

Load this when building the packet. It gives the field-level determination rules,
the plea taxonomy, and the exact formulas. Everything here is method/domain
knowledge — always apply the specific numbers, bands, and enum names from the
task's own template, portal, and policy, not fixed values.

## Gathering data efficiently

- Look each target up by its exact identifier (case number / citation number /
  petition id). Record-collection endpoints typically support filtering by that
  identifier; generic page/offset parameters may be ignored, so filter by
  identifier rather than paging.
- For each target also fetch: the jurisdiction row (timezone, policy ref), the
  matching current fee-schedule rows, the payment policy, and the relevant form
  metadata (form id, label, required fields, placeholder instruction).
- Redacted/"clerk note text redacted" docket entries carry no usable content;
  rely on the typed docket entries (filing / hearing / disposition / financial /
  continuance) and their `source` label.

## Conflict resolution — worked patterns

Build, per target, a small table: field -> {each source's value} -> corrected
value -> resolving source. Common patterns:

- Queue/worksheet name or DOB differs from the portal and a memo → correct to the
  portal/memo value; resolution = portal identity record, or the corroborating
  memo if it is what established the correction.
- Queue labels counsel as public defender but a memo/record shows appointed
  private (county pay) → counsel = appointed private; and therefore no
  public-defender user fee.
- Worksheet uses an archived assessment amount → replace with the schedule row
  effective on the disposition date.
- Portal charge shows a departure ("dispositional/durational") but the judge
  called it top-of-range/presumptive → no departure entered.
- Portal charge disposition contradicts the bench outcome (e.g. "dismissed" for
  an adjudicated-guilty matter, or the pre-amendment charge) → the bench outcome
  controls.
- A draft disposition sheet lists a sentence but the docket says the order was
  not signed → hold; post nothing.

## Plea taxonomy (when the enum has no "not guilty")

- Guilty plea → `guilty`.
- No-contest plea → `no_contest` (or the template's spelling, e.g. `no contest`).
- **Bench/jury trial with a guilty verdict** → the plea field is
  `not_applicable` — the conviction came from a verdict, not a plea.
- Matter continued / plea paperwork incomplete / no plea reached →
  `not_entered`.

## Charge-severity → departure status

- Felony conviction, no departure pronounced → the "none/no-departure" value.
- Misdemeanor conviction → the "not evaluated (misdemeanor)" value.
- Held/pending matter → the "not entered / pending" value.
- Count amended from a felony drug count to a misdemeanor → treat as the
  misdemeanor for departure and drop any drug assessment.

## Fees, holds, and register/batch totals

1. Determine each posted case's fee lines from the **current schedule** and the
   conviction facts: mandatory court cost; fine as pronounced (0 if waived);
   assessment only for the matching conviction type; user fee only for the
   matching counsel type.
2. `case_total` / `total_due` = sum of that case's posted lines.
3. Held/pending cases: fee status = hold/do-not-post, all amounts 0, and they are
   **excluded** from disposed counts and money totals.
4. Register/batch totals: counts of posted vs held; per-fee-type totals summed
   across posted cases only; grand/batch total = sum of posted case totals.
5. Verify the grand total equals both the sum of per-case totals and the sum of
   per-fee-type totals.

## Traffic-citation fine tiers

- The absolute-speed tier (e.g. "100 mph or greater") is triggered by the actual
  speed, independent of the over-the-limit amount; other tiers are by mph-over.
- Standard fine = the current schedule row for the violation code; add any
  mandatory county surcharge once per citation. `amount_due` = standard fine +
  surcharge. Reject stale-schedule and statutory-maximum substitutions.

## Installment / payment-plan math (verified)

Let `total_due` = supported balances (restitution + fines/costs), excluding any
account fee the policy excludes. Let `monthly` = the approved monthly amount.

- **Approved monthly**: use the requested amount if it is within the policy band
  `[min_monthly, max_monthly]` and affordable versus disposable income
  (`income − obligations`). Otherwise flag with the schema's classification
  (below minimum / above maximum / unsupported / needs review). Down payment =
  the policy's required down payment (often 0).
- `full = floor(total_due / monthly)`
- `remainder = round(total_due − full × monthly, 2)`
- If `remainder > 0`: `final_payment = remainder`, `total_installments = full + 1`.
- Else: `final_payment = monthly`, `total_installments = full`.
- `first_due_date = submitted_date + policy.first_due_days`
- `final_due_date = first_due_date + (total_installments − 1) months`
  (advance by whole months, keep the day-of-month).
- `return_to_court_date = final_due_date + policy.return_to_court_offset_days`
- `payment_application_order`: `restitution_before_fines_costs` when
  restitution > 0 and the policy prioritizes restitution; `fines_costs_only`
  when there is no restitution.
- `account_fee_treatment`: `excluded_by_policy` (amount 0) when the policy's
  account fee is 0, even if a counter worksheet carried an old fee; included only
  where the policy sets a nonzero account fee.

## Probation referral and license order

- Probation referral: prepare it when supervised probation was ordered; mark
  "not ordered" when no referral order was signed (term 0, report datetime null).
  Report datetime comes from the sentencing/probation note.
- License suspension: **start/effective date = the conviction date** (never the
  release date or petition date). Term = the months the controlling packet
  document states; for a financial/installment order, the packet's financial
  worksheet value governs when it conflicts with the charge. Driver-license
  number is a placeholder when absent. Basis = the conviction type (e.g. DUI).

## Placeholders — completeness rule

- Include a placeholder entry for a field **only if that field is needed for that
  specific case and no source supplies it.** Identity/contact fields (SSN,
  driver-license number, addresses, phone) apply to any case that needs them.
- A case with a probation referral additionally needs the probation officer and
  probation office location — include those placeholders for that case only.
- A case with no probation referral does not carry probation-office placeholders.
- Prefer a concrete standard/derivable value over a placeholder when one exists
  (e.g. a standard court session time is a value, not a "case-file" unknown).
- Sort placeholder lists / missing-field lists as the template instructs
  (usually alphabetical), and list each field once.
