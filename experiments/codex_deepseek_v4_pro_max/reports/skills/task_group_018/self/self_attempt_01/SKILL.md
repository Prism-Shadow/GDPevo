 # Court Clerk Closeout & Financial Packet Skill

 Complete court-clerk post-hearing tasks — sentencing closeouts, traffic-violation dispositions, post-sentencing field packets, and criminal-disposition register reconciliation — by cross-referencing local case materials against a Court Operations Portal API.

 ## When to Use

 Use this skill for clerk tasks that combine local payloads (hearing notes, finance extracts, petition summaries, intake sheets, form excerpts) with a court portal API. Indicators include:

 - Criminal or traffic disposition closeouts
 - Post-sentencing field-packet preparation
 - Financial register or batch reconciliation
 - Payment-plan setup with budget analysis
 - Audit findings and multi-source conflict resolution

 ## Default Data Formats

 - **Currency**: numeric values in USD rounded to two decimal places.
 - **Dates**: ISO 8601 `YYYY-MM-DD`.
 - **Date-times**: ISO 8601 local `YYYY-MM-DDTHH:MM:SS`.
 - **Null/empty fields**: use `null` (JSON) or `"TBD from case file"` when an output schema requires the placeholder.
 - **List ordering**: unless the output schema specifies a different sort key, sort top-level result lists by `case_number` or `citation_number` ascending; sort sub-lists alphabetically by their identifying field.

 ## Workflow

 ### 1. Inventory Materials

 Read every local payload file and the task prompt. Identify:
 - The target cases, citations, or petitions.
 - The output schema (from `answer_template.json`).
 - Which portal endpoints are available.
 - Which local documents are present (hearing notes, finance extracts, audit memos, form excerpts, worksheets, budget summaries, petition intakes).

 ### 2. Query the Portal

 Use the Court Operations Portal at `<TASK_ENV_BASE_URL>`. Common endpoints:

 | Endpoint | Used for |
 |---|---|
 | `GET /api/cases` | Case records, identity, status |
 | `GET /api/charges` | Charge details, statutes |
 | `GET /api/docket-entries` | Prior docket history |
 | `GET /api/citations` | Traffic citation records |
 | `GET /api/jurisdictions` | Court jurisdiction metadata |
 | `GET /api/fee-schedules` | Current fee amounts |
 | `GET /api/payment-policies` | Payment policy rules, account-fee treatment |
 | `GET /api/forms` | Form IDs, labels, required fields |
 | `GET /api/financial-petitions` | Filed petitions and balances |
 | `GET /api/search` | Cross-reference lookups |

 Always fetch current records — do not rely solely on local extracts, which may contain stale or carry-forward values.

 ### 3. Resolve Conflicts (Audit)

 When local sources disagree or conflict with portal records, apply this hierarchy:

 1. **Courtroom hearing notes / bench statements** — what the judge actually said in open court.
 2. **Signed final orders** — the executed disposition document.
 3. **Portal/CMS records** — the authoritative digital identity and status record.
 4. **Clerk audit or corroborating memos** — secondary evidence for context.
 5. **Finance queue / worksheet extracts** — lowest priority; often contain draft, stale, or imported carry-forward values.

 Specific conflict rules:

 - **Defendant name**: reconcile spelling variants (e.g., "Simons" vs "Simmons"). Prefer hearing notes for the correct spelling; the portal may confirm it.
 - **Date of birth**: trust portal/CMS record. If a local worksheet has a different DOB, flag it. If DOB is blank everywhere, use `"TBD from case file"`. Do not borrow a DOB from a similarly named defendant in prior search results.
 - **Counsel classification**: hearing notes override intake abbreviations. An "APD" calendar label or "PD" queue label does not make counsel a public defender if the hearing record says "appointed private counsel, county pay." The practical consequence: if counsel is appointed private (not PD office), the public-defender user fee does not apply.
 - **Disposition status**: a queued "disposed" label does not make a case disposed. If no final signed order exists, the case is `pending`, `continued`, or `deferred` — do not enter a disposition or post financials.
 - **Departure findings**: a worksheet departure label (e.g., "dispositional departure") is overridden by the judge's explicit statement. A "top of range" sentence is not a departure. Default to `"none"` or `"not_applicable"` unless the judge stated a departure on the record.
 - **Fee schedule version**: a queued fee amount may be from an archived schedule. Verify the current schedule for the disposition year before posting. If a local worksheet shows an outdated amount (e.g., 2023 drug assessment for a 2025 case), use the current portal fee schedule instead.

 ### 4. Determine Case / Matter Status

 For each target case:

 - **Disposed / enter**: a signed sentencing or disposition order exists. Post the disposition, financial entries, and docket actions.
 - **Hold / exclude**: no final signed order (continued, deferred, pending status check). Do not enter a disposition or post financials. Record as an exclusion or hold with the next status check date.
 - **Deferred with draft worksheet**: ignore draft values. No register entry until the signed order is available.

 ### 5. Build Charge & Sentence Summaries

 For each disposed case with a conviction:

 - Map the plea (`guilty`, `no contest`, `not guilty`) from the hearing record.
 - Map the charge disposition (`guilty`, `nolle prosequi`, `deferred`, `pending`, `dismissed`).
 - Record: offense code, statute citation, jail days imposed/suspended, probation months, fine amount.
 - **Amended charges**: if the state amended a charge before plea (e.g., felony controlled substance → misdemeanor theft), the conviction is on the amended count, not the original filing.
 - **Departure status**: `"no_departure"` unless the judge expressly found one on the record.
 - **Lab fees**: required for controlled-substance convictions (even if the local worksheet omitted them). Include when the conviction is for a controlled-substance offense.

 ### 6. Reconcile Fees & Financials

 Fee types to consider (when supported by the disposition and current fee schedule):

 | Fee code | When applicable |
 |---|---|
 | `fine` | Announced by the court at sentencing. |
 | `court_cost` | Standard circuit/district criminal or traffic court cost per the current schedule. |
 | `drug_assessment` / `assessment` | Controlled-substance convictions; use current schedule amount. |
 | `public_defender_user_fee` | Only when counsel is a public-defender-office attorney. |
 | `crime_lab_fee` | Controlled-substance convictions where the schedule mandates it. |

 **Fees to exclude** (do not add unless the portal record, current fee schedule, or court order explicitly supports them):

 - Account-management / account-maintenance fees
 - Collection referral fees
 - Late-payment fees
 - DMV notice / reinstatement fees
 - Returned-check fees
 - Restitution (unless ordered in the sentencing record)
 - Copy / certification fees
 - Court-appointed-attorney fees
 - Court-reporter fees
 - Traffic-school program fees
 - Stale schedule amounts
 - Payment-plan service charges (unless current policy mandates them)

 **Fee posting rule**: only post fees for cases with a signed final order. For held/deferred cases, set `fee_status` to `"do_not_post_pending"` or `"hold"`.

 ### 7. Create Docket / Register Entries

 For each disposed case:
 - Entry date: the disposition date (date of signed order or hearing).
 - Docket entry type: `"sentencing_order"` or the schema's disposition entry type.
 - Summary code per the schema.
 - Financial total: sum of all posted fees for that case.

 For held cases: use `"disposition_hold"`, `"CONTINUED_NO_DISPOSITION"`, or the schema's hold code. Do not post a financial total.

 ### 8. Compute Register / Batch Totals

 Across all cases in the batch:

 - Count disposed cases and held/excluded cases separately.
 - Sum each fee category (fines, court costs, assessments, user fees, lab fees) across disposed cases only.
 - Compute a grand total from all posted fee lines.
 - Do not include draft or held-case amounts in totals.

 ### 9. Handle Payment Plans (when applicable)

 When a payment petition or installment plan is part of the task:

 **Budget analysis**:
 - Compute monthly disposable income: `monthly_income - total_monthly_obligations`.
 - Compare the requested monthly payment to the disposable income and to any policy minimum/maximum bands.
 - Classify: `supported_by_budget` (or `supportable`), `below_policy_minimum`, `above_policy_maximum`, `unsupported_by_budget`.

 **Payment application order**:
 - If restitution is ordered and has a balance: `restitution_before_fines_costs`.
 - If no restitution: `fines_costs_only`.

 **Account-fee treatment**:
 - Check the current payment policy for account-fee rules.
 - Unless the policy explicitly includes an account-maintenance fee, exclude it (`excluded_by_policy`).
 - A counter worksheet mention of an account fee is not sufficient — verify against the portal policy.

 **Installment schedule**:
 - `first_due_date`: from the petition or hearing note.
 - `regular_installment_amount`: the approved monthly (or interval) payment.
 - `total_installments`: `ceil(total_due / regular_installment_amount)`.
 - `final_payment_amount`: the remainder when `total_due` is not evenly divisible by the installment amount.
 - `final_due_date`: `first_due_date + (total_installments - 1) * interval_months`.
 - `return_to_court_date`: from the petition candidate date; include a return-to-court trigger (`nonpayment`, `default_review`, or `none`).

 **Special note for traffic violations**: if no separate case/account number exists, the citation number serves as the account reference.

 ### 10. Handle Form Requirements (CC-1375, CC-1379, etc.)

 When the output schema requires form-specific sections:

 - **CC-1375 (probation referral)**: required only when supervised probation was ordered. If the sentencing record shows no supervised probation or no signed referral order, set status to `"not_ordered"`.
 - **CC-1379 (license suspension + installment order)**: license start basis is `"conviction_date"` (the release date is context only and does not replace the conviction date for suspension computation).
 - **Missing identifiers**: when a form requires a field (SSN, driver license number, address, phone, probation officer name, probation office location) but the case materials lack it, use `"TBD from case file"`. Never invent identifiers or contact details.

 ### 11. Handle Placeholders

 Use `"TBD from case file"` for:
 - Missing SSN
 - Missing driver license number
 - Missing mailing or residence address
 - Missing phone number
 - Missing probation officer name / office location
 - Missing attorney, judge, or party contact details
 - A blank DOB when no source can verify it

 Do not use placeholders for computable values (totals, dates derivable from known facts, installment counts).

 ### 12. Excluded / Held Items Summary

 Output a section listing each item excluded from the register or balance:
 - Held cases (continued, no final order) with next status check date and `financial_posting_allowed: false`.
 - Unsupported fees with the reason code (`unsupported_post_disposition`, `not_current_policy`, `no_triggering_event`, `stale_schedule`, `not_in_hearing_order`, `no_order_or_policy_support`, `not_part_of_balance`).
 - Stale or inapplicable charges.

 ## Portal Query Strategy

 1. Fetch all target cases/citations from the portal to verify identity, status, and charges.
 2. Fetch the current fee schedule for the relevant jurisdiction and disposition year.
 3. Fetch the current payment policy for account-fee treatment and installment rules.
 4. Fetch form metadata when form IDs or labels are needed.
 5. Use `/api/search` to cross-reference names, case numbers, or statutes when local materials are ambiguous.
 6. Fetch docket entries when prior history (e.g., prior defaults, prior payment plans) is relevant.

 ## Output Construction

 - Build the answer strictly to the schema in `answer_template.json`.
 - Populate every required key; use `null` for genuinely absent values and `"TBD from case file"` only where the schema prescribes that placeholder.
 - Use the exact enum values from the schema — do not substitute prose.
 - Apply the sort rules declared in the schema or the default sort rules above.
 - Return only the JSON object; no surrounding markdown unless the prompt specifically requests it.

 ## Common Pitfalls

 - **Trusting the finance queue**: extracts often contain draft, stale, or carry-forward values. Always cross-check against hearing notes and portal fee schedules.
 - **Assuming PD fee applies**: check whether counsel is actually a public-defender-office attorney. Appointed private counsel paid by the county is not PD.
 - **Posting financials for held cases**: never post a financial register entry for a case without a signed final order, even if a draft worksheet exists.
 - **Using old fee amounts**: always verify the current schedule for the disposition year.
 - **Inventing identifiers**: if a contact detail, ID number, or name is missing from all sources, use the placeholder — do not guess.
 - **Treating "disposed" labels at face value**: a queue or worksheet status of "disposed" does not override the fact that no order was signed.
 - **Overlooking lab fees**: controlled-substance convictions require lab-assessment fees even when the local worksheet omitted them.
 - **Applying a departure without a judicial statement**: a worksheet checkbox is not enough. The judge must have stated it on the record.
 - **Borrowing a DOB from a similar name**: never copy a DOB from a similarly-named search result.
