# Exemplar Matter Catalog

The five train matters that define this skill. Each is a deputy-clerk closeout/reconciliation packet; the variation is jurisdiction + which payloads attach. Listed only by shape and which rules each exercises — no final answer values.

## train_001 — Redwood County (AR-RC) criminal sentencing closeout
- **Targets:** four criminal cases on a single docket.
- **Payloads:** hearing notes, clerk audit memo, finance queue extract, answer template.
- **Rules exercised:** identity conflict (name/DOB) resolved to CMS (Rule 3); counsel label "PD C. Hill?" actually appointed-private → not PD-user-fee-eligible (Rule 4); stale 2023 drug assessment → current 2025 schedule row (Rule 5); draft "dispositional departure" label → judge's "top of the range, no departure" finding (Rule 7); unsigned/deferred disposition ("order not signed") → hold financial entry, exclude from register (Rule 6); register totals sum posted lines only.

## train_002 — Oregon 22nd JD / Jefferson County traffic violation closeout + payment plans
- **Targets:** two traffic citations; extended payment plans approved after disposition.
- **Payloads:** hearing closeout note, local form excerpt, answer template.
- **Rules exercised:** post-disposition plan sequence (Rule 8); stale SOF table ($1,000) vs current fee schedule vs "up to $2,000" statutory-max note → pick current schedule, exclude the stale/max substitution (Rule 5); exclude every unchecked sticky-note fee (late, collection, DMV, returned-check, account-mgmt, traffic-school) — no triggering event (Rule 5); account reference = citation number when no case/account number opened (Rule 9); plan schedule math with final remainder installment; required form labels from the local excerpt; obsolete $25 service-charge footer is not current policy.

## train_003 — Gloucester County (VA) single post-sentencing field packet
- **Targets:** one case + one payment petition.
- **Payloads:** sentencing intake facts, payment petition + budget, form field excerpt, answer template.
- **Rules exercised:** conviction/release date distinction — release date is memo context, conviction date drives license suspension (Rule 9); budget support classification (income − obligations vs policy band) (Rule 8); CC-1375 probation referral + CC-1379 license/installment order form mapping (Rule 9); placeholder discipline for null SSN/license/addresses/phone/probation-office → `TBD from case file` with reason codes (Rule 9); exclude restitution/account-mgmt/late/DMV/attorney/court-reporter fees per intake `do_not_add` list when no order/policy supports them (Rule 5).

## train_004 — Union County (AR) criminal disposition batch register
- **Targets:** five criminal cases, one afternoon docket.
- **Payloads:** finance memo/worksheet CSV, hearing notes, answer template.
- **Rules exercised:** amended-away count (controlled-substance → misdemeanor theft) is not the conviction, so no drug/lab fee on that one; *retained* lab assessment on a *different* still-controlled-substance conviction must post even though worksheet omitted it (Rule 7); blank DOB → `TBD from case file` + `verify_before_entry`, never borrowed (Rule 3); "APD" calendar label → judge clarified appointed-private, not PD (Rule 4); draft/continued matter (no plea accepted, no order signed) → exclude from register, next-status-check date, `financial_posting_allowed: false` (Rule 6); batch totals reconcile to posted lines only.

## train_005 — Gloucester County (VA) two-petition post-disposition packet
- **Targets:** two cases + two payment petitions.
- **Payloads:** petition summaries (with budget + counter notes), sentencing/probation notes, answer template.
- **Rules exercised:** petition classification (initial installment vs subsequent review vs deferred) (Rule 8); support classification against policy band (Rule 8); account-fee carried on old counter worksheet → excluded by current Gloucester policy (Rule 5/8); payment application order from policy (restitution-before vs fines-costs-only), not from petitioner question (Rule 8); CC-1375 `not_ordered` when no probation referral order signed (Rule 9); license suspension start basis = conviction date, with months from the record (Rule 9); missing identifiers → `TBD from case file` (Rule 9).

## Common thread
All five: read every payload → spot the conflicts → resolve via the bench/CMS/schedule/policy ladder → hold unsigned matters → drop unsupported fees → never invent identifiers → emit one schema-exact, ordered, two-decimal JSON object with reconciled totals.
