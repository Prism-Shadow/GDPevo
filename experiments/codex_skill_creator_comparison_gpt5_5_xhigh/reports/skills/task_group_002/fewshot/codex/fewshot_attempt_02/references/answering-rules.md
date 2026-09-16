# MedBridge Answering Rules

## Record Discovery

- Start from the IDs and names in the prompt, then expand through linked records.
- Fetch full records for all evidence used in the answer. Search snippets are only leads.
- If a collection endpoint must be listed, filter by explicit links such as customer ID, quote/RFQ ID, opportunity ID, product code, invoice ID, milestone ID, event ID, or voucher code.
- Resolve conflicts by preferring records whose stable IDs and relationship fields agree with the prompt over records that only share a display name.

## Quote and RFQ Packages

- Use the requested quote or RFQ record as the commercial source of truth, then verify the customer and catalog product records.
- Price only the product or module level requested in the prompt. Do not decompose kit or module component details unless the template explicitly asks for component lines.
- For tiered catalog pricing, choose the tier whose inclusive minimum and maximum quantity bounds contain the confirmed/requested quantity. Treat a missing maximum as open-ended.
- Compute each line total as `quantity * unit_price`. Compute EXW totals as the sum of applicable line totals before freight.
- Use customer or policy records for payment terms, quote basis, offer validity, documentation requirements, and freight controls. Do not infer account terms from the customer name alone.
- Retrieve freight options linked to the quote/RFQ, customer, product, or route requested in the prompt. Include the modes requested by the template or prompt.
- Compute freight grand totals as `exw_total + freight_cost` for each included option.
- Evaluate freight validity against the quote date or stated business date. A freight option is stale or invalid when its validity date is before that date or an API status/source flag marks it stale.
- Flag customs, border, source-validity, or route-risk concerns from freight and policy records.
- Recommend the policy-preferred mode when it is valid and appropriate. Otherwise choose the lowest-cost valid option that does not carry a disqualifying risk. Do not recommend an expired or stale option without an explicit prompt requirement.
- Require freight reconfirmation when policy requires it, when any included option is stale/expired, or when route/source risk requires recheck.

## Opportunity Reconciliations

- Fetch the opportunity, customer, invoices, payments, revenue journals, related event, and voucher.
- Match invoices to the opportunity/customer and to milestone or phase identifiers. Match payments to invoices before assigning paid and unpaid amounts to milestones.
- Sort milestones by their business phase or stable milestone ID when the template requires ordered milestones.
- Compare the won opportunity amount with the sum of invoice or phase milestone totals, rounded to cents.
- Derive payment state from paid amount versus invoice total: fully paid, partially paid, unpaid, or unknown when records are insufficient.
- Outstanding balance is total invoice or phase amount minus total paid amount, rounded to cents.
- Paid milestones require revenue journal coverage unless the API or policy says otherwise. Mark unpaid milestones as not requiring recognition yet.
- Recognition amount is the sum of recognized journal amounts for covered paid milestones, not the full opportunity total unless every paid milestone is covered for that amount.

## Action Routing

- When a paid milestone is missing required revenue recognition, choose the template's accounting action for recording or correcting revenue, link it to that milestone, and use accounting ownership values from the template.
- When an unpaid milestone is not yet due, choose the template's monitoring action. When it is due or overdue, choose the template's collection action. When there is no unpaid balance, choose the template's no-action value.
- Event and voucher tasks should use the event/voucher records explicitly requested or linked to the account. Send the invite when the event is active or scheduled, the voucher is usable, and the prompt asks for invite routing.
- Use the named contact from the prompt only after confirming the contact belongs to the customer or opportunity. If the API carries a more precise linked contact record, use that linked identity.
- Keep task titles short, operational, and tied to the relevant milestone, event, or customer. Do not add explanatory prose outside fields.

## Final Checks

- Ensure every computed total reconciles with its components.
- Ensure every enum value comes from the current template or API records; do not invent synonyms.
- Ensure each ID in the output can be traced to the prompt or a fetched API record.
- Ensure the JSON contains no training example values unless those exact values also appear in the current task records.
