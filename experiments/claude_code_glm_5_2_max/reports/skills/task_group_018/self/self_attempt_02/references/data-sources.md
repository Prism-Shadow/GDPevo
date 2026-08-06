# Data sources and trust ranking

This reference describes the recurring payload types seen across court closeout batches and how to treat each. It is generic — the exact filenames vary, but the roles repeat.

## Payload types and what they mean

- **prompt.txt** — the task framing: jurisdiction, docket/citation/petition targets, which endpoints to use, and the list of artifacts the final object must contain. Names the answer template to match.
- **answer_template.json** — the deliverable contract: required top-level keys, per-item required keys, enum vocabularies, sort orders, date/currency rules, and placeholder tokens. Authoritative over prompt prose.
- **hearing notes / courtroom disposition notes / closeout note** — first-person bench transcription from the hearing. Carries the bench shorthand, party nicknames, and carry-forward morning-sheet values, plus the judge's actual pronouncements (plea accepted, sentence pronounced, top-of-range vs. departure, order signed or not). Highest authority for what happened in court.
- **clerk audit memo / corroborating memo / review reminder** — a supervisor/audit layer telling you which queue values are stale, drafted, or miscopied and which source to trust instead. Use it to direct corroboration.
- **finance queue extract / worksheet CSV / worksheet JSON / petition summary** — the financial intake data, always partially stale: carry-forward DOBs, archived fee amounts, draft plea lines, "PD" labels that may really be appointed-private, old account-fee rows. Lowest base trust; verify each line.
- **local form excerpt / form field excerpt** — the field groups and labels of the local forms (e.g. CC-1375 probation referral, CC-1379 license/installment order, extended payment plan agreement). Defines which fields are required, what the placeholder rule is, and the precise labels the answer must reference.
- **sentencing intake facts / probation desk notes** — the conviction/sentence posture (conviction date, offense/statute, jail months imposed/suspended, fine, costs, probation term, license suspension months, release date) and probation reporting details. Controls the case-memo and form fields.
- **environment_access.md** — the only network authority: portal base URL and the allowed GET endpoints. No credentials. HTTP-only; no server-side file reads.

## Trust ranking (highest to lowest)

1. Signed sentencing order / hearing closeout minute / bench pronouncement on the record.
2. Clerk audit memo / corroborating memo / courtroom audio clerk statement / review reminder.
3. Current portal record (CMS case, charge, current-year fee schedule, current payment policy, current form metadata) — used to confirm, not to override a signed order.
4. Sentencing intake / probation desk notes (the controlled posture of the case).
5. Finance queue / worksheet / petition counter note (stale/draft by default).

When two sources conflict, pick per this ranking and record the resolution (corrected value + which source you trusted) in the audit section.

## Mapping a payload type onto the schema

- hearing/closeout notes → disposition, plea, primary outcome, sentencing terms, "order signed?" → drives `entry_status` / `register_action` / `closeout_action`.
- audit/corroboration memo → `audit_findings` / `case_audit` conflict rows and `resolution_source`.
- finance queue / worksheet → candidate fee lines and totals that you then **reconcile** (post, hold, or exclude) into `fee_reconciliation` / `fee_entries` / `financial_entry`.
- local/form excerpt → `form_entry` / `cc1375` / `cc1379` / `license_orders` / `probation_referrals` field values and the placeholder rule.
- petition budget → `budget_review` / `payment_plan` / `petitions` math and support classification.
- portal (cases/charges/fee-schedules/payment-policies/forms/financial-petitions) → corroborating identity, offense code, current fee amount, policy band, form id/label.

## What "corroborate via the portal" means concretely

For each target (case / citation / petition), call the endpoints the prompt lists against the `environment_access.md` base URL to confirm: DOB and defendant name spelling, offense/statute code, the fee-schedule amount in effect for the disposition year, the payment-policy band, and the form id/label in current revision. A portal refusal or empty result means hold/verify that field per the rules — never backfill it from the stale worksheet.
