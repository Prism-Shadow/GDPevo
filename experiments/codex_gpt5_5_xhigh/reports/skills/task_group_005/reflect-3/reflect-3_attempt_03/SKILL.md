# Reflect-3 Finance Close Skill

Use this skill for task_group_005 finance-control tasks that ask for JSON decisions from the shared ERP/compliance API. The common pattern is to reconcile a small scoped payload against current API records, not to summarize source statuses.

## Core Workflow

1. Read the prompt, the answer template, and any scoped local payloads first. Treat local snapshots and batches as scope/context unless the prompt explicitly makes them authoritative.
2. Use the live API records as the system of record for current claim, AP, payment, vendor, compliance, prepaid, GL, and close-log evidence.
3. Build the answer directly from the template. Keep required top-level keys, enum values, booleans, numeric precision, and list ordering exactly as specified.
4. Sort ID lists ascending by the ID type requested. Preserve scope order only when the template says to preserve it.
5. Return JSON only when requested. Do not include explanatory text outside the object.

## Reimbursement And AP Close

- For claim batches, reconcile each claim across claim status/support, AP bill link, AP bill amount/vendor, bill status, and payment status.
- A claim is settled only when a current AP bill matches the claim amount and has a cleared payment for that amount. Scheduled, processing, or in-flight payments are not settled.
- A valid open payable needs an approved/supportable claim and a current non-void AP bill that matches the claim amount and expected vendor/account evidence. Do not use void, stale, duplicate, amount-mismatched, or vendor-mismatched rows as release evidence.
- Keep reimbursement-case problems separate from AP/payment evidence problems when the schema has separate blocked, cleanup, stale-correction, or paid fields.
- Open-balance totals should include only valid current open AP rows for the claims the relevant field describes. Do not count paid rows, void rows, stale rows, or invalid mismatches as open release balance.
- For stale AP snapshots, compare every snapshot row to current API data. Mark rows as in-flight, replaced by matched paid evidence, excluded for amount/vendor mismatch, ignored because void, or blocked because the claim is not approved/supportable according to the enum set provided.
- Use current nonclosed close logs that are relevant to the AP export/import issue when the answer template asks for close-log IDs. A batch that is otherwise payable but needs a refreshed export is usually a refresh state; a batch with unresolved current claim/AP blockers is blocked.

## Vendor And Compliance Release

- Gather evidence from vendor records plus compliance profile, ownership, registry/license, screening, bank, and risk records. Do not copy a review-status field as the final decision without checking the evidence.
- Release only when the current vendor/compliance evidence is clean for the requested release: active vendor, bank verified, tax evidence valid and consistent, license current as of the review date, screening complete and clear, and no risk override or severe compliance flag.
- Use hold for remediable release blockers such as bank mismatch/closed bank, expired or missing license, missing required documents, incomplete screening, invalid tax evidence, or risk-score override when no severe escalation signal is present.
- Use escalate for severe compliance risk such as confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold, or explicit escalated risk posture combined with release blockers.
- For UBO counts, count unique owner names at or above the reporting threshold; duplicates count once and owners below threshold do not count.
- Treat possible PEP or possible sanctions as review evidence, not the same as confirmed PEP or confirmed sanctions unless the prompt or enum explicitly says otherwise.
- For bank-change batches, compare the requested bank last four to the current vendor bank last four, but populate bank-mismatch lists from the compliance bank-account status when the template defines them that way.
- For invalid-tax lists, include malformed tax IDs and profile/vendor/registry contradictions when the task asks for release-control tax exceptions.
- For expired-license lists, compare license expiry to the task review/as-of date. A license expiring after that date is not expired for the review.
- Risk-score override lists are threshold-based; when the template says `risk_score >= N`, include the threshold value itself.

## Prepaid Close

- Limit the schedule to the scoped invoice IDs and account list from the payload. Do not pull unscoped invoices into totals.
- Use the invoice record's monthly amortization as represented. Count a full monthly amortization when the close month falls within the invoice's service month range; do not prorate mid-month starts or force tiny final-month residuals to zero unless the record or prompt explicitly instructs it.
- Cumulative amortization through the close month is the recorded monthly amount times the count of service months through that close month. Ending balance is original amount minus cumulative amortization, rounded to two decimals.
- Roll account totals from invoice results, then compare schedule ending balance to the GL ending balance for the same entity, account, and period. Variance amount is schedule ending balance minus GL ending balance.
- Set the variance flag using the absolute threshold from the payload. If an account has a variance flag, the account status should require reconciliation; use reconciled only when both variance and data-quality/default-term issues are clear.
- Map missing/default contract-term quality flags to the default/missing-term fields. Treat invoice data-quality flags as invoice exceptions and include exception invoice IDs sorted ascending.

## Output Discipline

- Use two decimals for USD amounts when the schema asks for currency precision. Use integer cents only when the prompt explicitly asks for cents.
- Include all required object keys even when a value is empty; use empty arrays, not omitted fields.
- Keep enum strings exact. Do not invent extra statuses or reason labels.
- Before finalizing, recheck that every ID in the output belongs to the requested scope and that no unrequested API record leaked into the answer.
