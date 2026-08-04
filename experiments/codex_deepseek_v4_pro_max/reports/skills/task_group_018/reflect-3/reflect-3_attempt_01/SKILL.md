 # Court Clerk Closeout and Financial Reconciliation

 This skill covers reconciling local case materials with a Court Operations Portal to produce structured closeout, sentencing, and financial-plan answers. Use it whenever a task involves comparing hearing notes, audit memos, finance extracts, petitions, or worksheets against live portal data to find and fix conflicts before entry.

 ## Workflow

 ### 1. Gather all inputs

 Read every local payload file in the task's input directory before querying the portal. Common payload types:

 - **Hearing / courtroom notes** — the authoritative record of what the judge said and ordered in open court.
 - **Clerk audit memos** — supervisor-flagged exceptions that must be investigated.
 - **Finance queue extracts / worksheets** — draft or carry-forward ledgers that may contain stale or incorrect figures.
 - **Sentencing intake / probation notes** — structured facts about conviction dates, sentences, probation terms, and license consequences.
 - **Petition summaries / budgets** — payment-plan requests with income, obligations, and candidate dates.
 - **Form field excerpts** — local form labels, placeholder rules, and required fields.
 - **Answer template** — defines the exact JSON shape, required keys, enum values, and ordering rules for the final answer.

 ### 2. Query the portal

 Pull all relevant data from the Court Operations Portal. Match endpoints to the case type:

 - **Criminal sentencing / disposition:** jurisdictions, cases, charges, docket-entries, fee-schedules, payment-policies, forms, search.
 - **Traffic citations:** citations, fee-schedules, payment-policies, forms, search.
 - **Financial petitions:** cases, charges, docket-entries, payment-policies, forms, financial-petitions, search.

 Extract every case number, citation number, or petition ID referenced in the task. Filter portal results to only those identifiers.

 ### 3. Cross-reference and flag conflicts

 Walk through every case or matter and compare the portal record against each local payload. Flag differences in these categories:

 | Conflict type | What to check |
 |---|---|
 | **Identity** | Defendant name spelling, date of birth. Prefer the CMS/AOC-CMS portal value when it is the system of record, unless the hearing notes or a paper jacket correction say otherwise. |
 | **Counsel** | PD / public defender vs. appointed private vs. retained. The judge's on-the-record clarification or a defense cover memo overrides a stale queue label or calendar abbreviation (e.g. "APD" may mean appointed private, not public defender). |
 | **Status** | Disposed vs. deferred vs. pending. If no final order was signed in open court, the matter is not disposed regardless of what a draft worksheet shows. |
 | **Fee schedule** | Queued amounts vs. current portal fee schedules. Replace any amount marked as an older year or "archived" with the current effective schedule. Omitted mandatory fees (e.g. lab assessment on a controlled-substance conviction, PD user fee when counsel is a public defender) must be added. |
 | **Departure** | Portal departure type and reason vs. the judge's stated finding. If the judge expressly said "top of range, no departure," override any departure label from a legacy charge screen or draft worksheet. |
 | **Charge amendment** | The original charge on a worksheet vs. the amended charge the state moved to and the court accepted. The conviction is on the amended count, not the original. |

 ### 4. Resolve conflicts

 Apply this resolution order (earlier wins):

 1. **Judge's oral pronouncement in hearing notes** — what the judge said in open court.
 2. **Signed sentencing / disposition order** — controls entry when available.
 3. **Corroborating memo / cover sheet** — used for counsel-type corrections when the judge noted it on the record.
 4. **Current portal fee schedule** — for all dollar amounts (ignore older/archived schedule rows).
 5. **CMS/AOC-CMS portal identity values** — for DOB and name when no courtroom correction exists.
 6. **Local worksheet / queue** — used only when it matches the above sources.

 ### 5. Build financial entries

 - Use only fee codes and amounts supported by the current portal fee schedule for the jurisdiction and disposition date.
 - Do not carry forward stale amounts from older schedule rows.
 - Do not add account-management, collection, late, DMV, restitution, copy, certification, or traffic-school fees unless the hearing order or current policy explicitly supports them.
 - PD user fees apply only when counsel type is `public_defender`, never `appointed_private` or `retained`.
 - Lab / drug assessment fees apply only to controlled-substance convictions, per the current schedule.

 ### 6. Compute payment plans

 When a payment plan is approved:

 1. Start with `total_due` = fines/costs balance + restitution balance. Do not add account fees unless the active payment policy supports them.
 2. Divide `total_due` by the `monthly_payment` amount. The integer quotient is the number of full installments. If there is a remainder, add one final installment.
 3. `first_due_date` comes from the petition candidate date or policy `first_due_days` offset from the petition submission date.
 4. Compute `final_due_date` by adding `(total_installments - 1)` months to `first_due_date`.
 5. `return_to_court_date` comes from the petition candidate date; if absent, add the policy `return_to_court_offset_days` to the final due date.
 6. Check that the `monthly_payment` falls within the policy's `min_monthly`–`max_monthly` band.
 7. Classify support: compare disposable income (income − obligations) to the requested monthly amount. If disposable ≥ requested and within policy band, mark `supported_by_budget`.

 ### 7. Handle placeholders

 - When a form field is required but the value is genuinely absent from all case materials (SSN, driver license number, address, phone, probation officer, probation office location), use the exact placeholder value specified by the answer template (usually `"TBD from case file"`).
 - Never invent identifiers or contact details.
 - Group placeholder fields by case number. Sort missing field names alphabetically.

 ### 8. Handle exclusions

 - Cases where no final order was signed must be excluded from the disposed register. Mark them with `hold_unsigned_order` / `exclude_pending` and set `financial_posting_allowed: false`.
 - Financial items not supported by the current policy or hearing order must be listed as excluded with a reason code (`no_order_or_policy_support`, `not_part_of_balance`, `no_triggering_event`, `stale_schedule`, `not_in_hearing_order`, `not_current_policy`).

 ### 9. Format the answer

 - All currency values: numbers rounded to two decimal places.
 - All dates: ISO 8601 `YYYY-MM-DD`.
 - All datetimes: ISO 8601 `YYYY-MM-DDTHH:MM:SS`.
 - Sort arrays by the key specified in the answer template (typically `case_number`, `citation_number`, or `petition_id` ascending).
 - Use only the enum values provided in the answer template. Do not substitute prose descriptions for enum values.
 - Do not include extra commentary, markdown, or text outside the JSON structure.

 ## Portal data interpretation

 When reading portal records, be aware of these patterns:

 - **`attorney_label_raw`** may be a carry-forward or calendar abbreviation (e.g. "APD", "PD conflict label", "UNK"). Cross-check with `counsel_type` and hearing notes.
 - **`counsel_type`** is the authoritative counsel classification from the CMS, but may still be stale. The judge's on-the-record statement controls.
 - **`status`** values: `disposed` = final order entered; `deferred` = no final order; `pending` = awaiting action; `continued` = carried to a future date.
 - **Charge `disposition`** in the portal may reflect the original filing rather than the amended conviction. When the hearing notes document an amendment, the conviction is on the amended count.
 - **`departure_type`** and **`departure_reason`** in the portal may reflect a draft worksheet, not the judge's final ruling.
 - **Fee schedule `effective_date`** and **`end_date`** determine currency. Use only rows where the disposition date falls within the effective range and `end_date` is null or after the disposition date.
 - **`jurisdiction_code`** matches the answer template's jurisdiction field.

 ## Common error patterns to avoid

 - Do not carry a PD user fee onto a case where counsel was determined to be appointed private.
 - Do not apply a drug assessment / lab fee to a non-controlled-substance conviction.
 - Do not post financial entries for a case whose status is `deferred` or `pending` with no signed order.
 - Do not use an older year's fee amount when a current schedule row exists.
 - Do not add a payment-plan account-management fee when the active policy sets `account_fee: 0.00`.
 - Do not compute `amount_due` as the sum of every fee line — only include fees that are "post" status; excluded fees contribute zero.
 - Do not invent driver license numbers, SSNs, addresses, phone numbers, probation officer names, or office locations.
