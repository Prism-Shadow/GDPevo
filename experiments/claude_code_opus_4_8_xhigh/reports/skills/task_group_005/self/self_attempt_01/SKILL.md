# SKILL: ERP Finance Close & Vendor Compliance (task_group_005)

Executable playbook for answering finance/AP/compliance review tasks against the shared
read-only ERP API. Covers five recurring task families:

1. Reimbursement-to-AP close review (claim vs bill vs payment triage).
2. Vendor onboarding finance-risk release calls (UBO + compliance gating).
3. Prepaid / GL reconciliation close checks (straight-line amortization vs GL).
4. Stale-AP-snapshot batch refresh (CSV/snapshot is context, API is system of record).
5. AP payment-release risk review after vendor account-change events.

The answer for every task is a single JSON object that conforms to the task's
`payloads/answer_template.json`. Read that template FIRST and obey every field name,
enum value set, ordering rule, precision rule, and `additional_properties_allowed` flag.

---

## 0. Golden rules (apply to every task)

- **The live API is the system of record.** Any base URL written inside a prompt
  (e.g. `http://127.0.0.1:8005`) is wrong/stale — always use the runner-provided base URL.
  Any local CSV/JSON "snapshot/export" is CONTEXT ONLY; never trust its statuses, amounts,
  or payment states. Re-fetch every record from the API and overwrite snapshot values.
- **Only the IDs listed in the prompt/payload are in scope.** Do not add or drop IDs.
  `reviewed_count` style fields = number of requested IDs.
- **Output discipline:** return JSON only, no prose. Honor `required_top_level_keys` /
  `top_level_order`. When `additional_properties_allowed: false`, emit exactly the listed
  keys — no extras. Money = USD rounded to 2 decimals (unless a template literally says
  "USD cents" → integer cents). Sort every ID list as instructed (almost always **ascending
  by id**); sort enum-string lists alphabetically when told to.
- **Decide on a 3-way bucket, never just echo the source `status`/`review_status`.** The
  templates always want a release-control decision computed from evidence, not the system's
  current workflow state. A record marked `approved`/`escalated` in the source may still be
  blocked/released by your own rules.
- Build the answer programmatically (fetch JSON, compute, dump JSON). Verify totals add up
  and rounding is applied once at the end.

---

## 1. The API

Base URL is provided by the runner (health responds `{"status":"ok","task_group":"task_group_005"}`).
Every object endpoint exists in two equivalent forms (e.g. `/claims` and `/api/claims`);
prefer the `/api/...` form. Object responses are
`{endpoint, count, total, offset, limit, data:[...]}`.

Filtering: **exact-match query params by field name**, plus `limit` & `offset`. Default
`limit` is small — pass `limit=200` (or page with offset) when scanning a whole table.
There is no range/`>=` filter; pull and filter client-side for numeric thresholds.

| Endpoint | Use it to answer | Key filterable fields |
|---|---|---|
| `/api/health`, `/endpoints` | confirm liveness / list routes | — |
| `/api/claims` (`/api/claims/{id}`) | expense claim facts | `claim_id`, `status`, `department`, `vendor_id` |
| `/api/ap/bills` | AP bills, incl. reimbursement clearing bills | `bill_id`, `claim_id`, `vendor_id`, `status` |
| `/api/ap/payments` | payments against bills | `payment_id`, `bill_id`, `vendor_id`, `status` |
| `/api/ap/aging?as_of=YYYY-MM-DD` | open balance per bill | also `bill_id`, `claim_id`; balance = amount − Σpayments, clamped ≥ 0 |
| `/api/vendors` | vendor master | `vendor_id`, `status` |
| `/api/compliance/objects` | full compliance/KYC record (one call gives everything) | `business_id`, `vendor_id` |
| `/api/compliance/{profile\|ownership\|registry\|screening\|bank\|risk}/{business_id}` | projections of the same object | path param only |
| `/api/prepaids/invoices` | prepaid amortization schedules | `prepaid_invoice_id`, `account`, `vendor_id` |
| `/api/prepaids/gl-balances` | GL ending balances by period | `account`, `period` (YYYY-MM), `entity` |
| `/api/close/logs` | month-end close log entries | `log_id`, `period`, `area`, `related_account`, `status` |

Notes:
- `/api/compliance/objects?business_id=X` returns ALL fields you need (bank, screening,
  ownership, risk, missing_fields). The per-aspect detail endpoints are just subsets — use
  `objects` for efficiency.
- `aging` recomputes balance live from payments; use it instead of trusting a bill's
  `status` to know how much is still open. `paid_amount` and `balance` are in the response.

### Object field reference (observed shapes)

- **claim**: `claim_id, amount, currency(USD), status, receipt_status, policy_flags[],
  department, employee_name, vendor_id(may be null), submitted_date, approved_date(may be null), category, notes`.
- **bill**: `bill_id, claim_id(may be null), amount, status, account, vendor_id,
  bill_date, due_date, invoice_number, currency, memo`.
- **payment**: `payment_id, bill_id, amount, status, vendor_id, payment_date, method, bank_reference`.
- **compliance object**: `business_id, vendor_id, business_name, jurisdiction,
  registration_number, tax_id, license_expiry, missing_fields[], ownership_layer_count,
  shell_company_suspected(bool), ubo_list:[{name,ownership_pct}], pep_status,
  sanctions_check_status, bank_account_status, review_status, risk_score(int)`.
- **prepaid invoice**: `prepaid_invoice_id, account, original_amount, monthly_amortization,
  recognition_method(straight_line), service_start, service_end, data_quality_flags[],
  invoice_date, invoice_number, vendor_id`.
- **gl balance**: `account, account_name, period(YYYY-MM), ending_balance, entity, source, loaded_at`.

### Enum value sets actually present in the data (use for validation)

- claim.status: `submitted, approved, paid, rejected, needs_receipt`
- claim.receipt_status: `attached, partial, missing`
- claim.policy_flags: `weekend_spend, late_receipt, manual_rate, over_limit, duplicate_amount`
- bill.status: `draft, approved, scheduled, paid, void`
- payment.status: `scheduled, processing, cleared`
- vendor.status: `active, inactive, on_hold`
- compliance.bank_account_status: `verified, not_verified, name_mismatch, closed`
- compliance.pep_status: `none, possible_pep, confirmed_pep, not_run`
- compliance.sanctions_check_status: `clear, possible_match, confirmed_match, not_run`
- compliance.review_status: `not_started, in_review, awaiting_information, escalated, approved`
- compliance.missing_fields: `license, website, bank_statement, beneficial_owner_id, address`
- prepaid.data_quality_flags: `rounded_amount, missing_contract_dates, manual_override, duplicate_invoice_number`

---

## 2. Family A — Reimbursement-to-AP close (claims triage)

Tasks of this family give a list of claim IDs and an answer template with buckets like
`payable / blocked / paid` (or `eligible / not_ready`), plus a money total, a remediation
list, and an overall `batch_status` enum.

### Per-claim evidence to gather
For each claim ID: fetch the claim; fetch its bill(s) via `/api/ap/bills?claim_id=...`;
for each bill fetch payments via `/api/ap/payments?bill_id=...`. (Optionally confirm open
balance via `/api/ap/aging?as_of=...&claim_id=...`.)

### Matching rule (a "matched" reimbursement link requires ALL of):
- a bill linked to that `claim_id` exists, AND
- bill amount **equals the claim amount** (to the cent), AND
- bill `vendor_id` is consistent with the claim (when the claim carries a vendor_id).
A bill whose amount is wildly different from the claim (e.g. claim 2,129.69 vs bill 44,348.61)
is an AP-link/amount mismatch — treat the claim as NOT validly linked.

### Three-way classification
- **PAID**: claim is settled — there is a matched bill with status `paid` AND a payment for
  the full claim amount with status `cleared`. (claim.status `paid` corroborates.)
- **PAYABLE / open payable / eligible**: claim is `approved`, receipt support is adequate,
  there is a valid matched bill that is NOT yet fully cleared (bill `approved`/`scheduled`,
  or payment still `scheduled`/`processing` = in-flight). These stay in the AP batch.
- **BLOCKED / not_ready / needs cleanup** (any one triggers it):
  - claim.status is not a releasable state (`needs_receipt`, `submitted`, `rejected`, draft);
  - no bill linked to the claim (AP-link missing);
  - bill amount ≠ claim amount, or vendor mismatch (amount/vendor mismatch);
  - bill.status is `void`/`draft` (void/invalid AP evidence);
  - receipt support is `partial`/`missing` when the workflow needs full support.
  These go to the remediation/`crm_required`/`stale_snapshot_corrections` list.

Preserve the prompt's distinction between **reimbursement-case issues** (claim-side: not
approved, missing receipt) and **AP/payment-evidence issues** (bill-side: void, missing,
amount mismatch) when populating reason/remediation fields.

### Money totals
- `ap_open_balance_total` (or similar): sum the OPEN AP balance for **payable claims only**
  (exclude paid and blocked). Open balance = bill amount − Σ cleared/applied payments
  (use the aging `balance`). Round to 2 decimals (or cents if the template says cents).
- `ap_balance_by_claim`: per requested claim, open balance after cleared payments, ignoring
  stale/void rows. Paid claims → 0.00. Blocked-because-no-valid-bill → 0.00.

### batch_status (overall)
- If ANY in-scope item is blocked → `blocked`.
- Else if valid unpaid payable bills remain → `open_payables` / `needs_ap_refresh`.
- Else (all paid, nothing open) → `ready_to_close` / `ready_to_send`.
(Use the exact enum spelling from the template; sets differ per task.)

### Stale-snapshot variant (Family A + CSV)
The CSV is pre-cleanup. Compare each snapshot row to live API and pick the correction enum,
e.g.: live payment now cleared but snapshot showed scheduled → `mark_in_flight_payment` /
`replace_with_matched_paid_bill`; snapshot bill is `void` in API → `ignore_void_bill`;
amount/vendor differs → `exclude_amount_or_vendor_mismatch`; claim not approved in API →
`block_unapproved_claim`; everything matches live → `current_snapshot_ok`. Map to whatever
allowed_values the template lists.

### close_log_required
When a template asks for close logs, query `/api/close/logs?period=...` (and/or by
`related_account`/`area`) for the relevant period; set `required=true` with the matching
`log_id`s sorted ascending only when the scenario actually depends on a close-log action;
otherwise `required=false`, `ids:[]`.

---

## 3. Family B — Vendor onboarding finance-risk release

Template typically wants: `per_business` (each `{business_id, decision}`),
`reportable_ubo_counts`, `hard_stop_flags` (per business, a list of enum flags),
`follow_up_business_ids`, `overall_release_ready`.

Pull `/api/compliance/objects?business_id=X` for each business; also fetch the vendor via
`/api/vendors?vendor_id=<obj.vendor_id>` when a `vendor_on_hold` style flag is in scope.

### Reportable UBO count
"Unique beneficial-owner **names** at or above the reporting threshold." Reporting
threshold = **25%**. Algorithm: aggregate `ubo_list` by `name` (the list can contain
duplicate names / split stakes), then count distinct names whose ownership is ≥ 25%.
(In observed data, summing duplicate stakes by name and "any single stake ≥ 25%" give the
same count, but dedupe-by-name is the rule the wording asks for.) Whole-number ≥ 0.

### hard_stop_flags — map evidence to the template's allowed enum values
Emit a flag when the corresponding condition holds (use only values the template lists;
order alphabetically; empty list when none):
- `sanctions_confirmed` ← `sanctions_check_status == confirmed_match`
- `screening_not_run` ← `sanctions_check_status == not_run` (and/or `pep_status == not_run`)
- `confirmed_pep` ← `pep_status == confirmed_pep`
- `bank_closed` ← `bank_account_status == closed`
- `bank_name_mismatch` ← `bank_account_status == name_mismatch`
- `expired_license` ← `license_expiry < as_of_date` (date compare)
- `missing_required_documents` ← `missing_fields` non-empty (esp. `license`,
  `beneficial_owner_id`, `bank_statement`)
- `shell_company_suspected` ← `shell_company_suspected == true`
- `vendor_on_hold` ← linked vendor `status == on_hold`

### decision (per business)
- `approve` / `release`: no hard-stop flags and risk acceptable.
- `escalate`: a genuine hard stop (confirmed sanctions match, confirmed PEP, suspected shell
  company, closed bank, high risk) — cannot be cleared by simply collecting a document.
- `awaiting_information` / `hold`: a remediable gap (missing documents, name mismatch,
  screening not run, expired license) — release pending more info.
`follow_up_business_ids` = every business not cleanly approved (escalate ∪ awaiting_information).
`overall_release_ready` = true only if EVERY in-scope business is approved/releasable.

---

## 4. Family C — AP payment-release risk review (account-change)

Template wants `decisions{business_id→release|hold|escalate}` plus categorized ID lists:
`bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`,
`risk_score_override_flags`, and echoes of `task_id/batch_id/as_of_date/target_business_ids`.
`additional_properties_allowed` is often **false** — emit exactly the listed keys.

Echo literal required values (`task_id`, `batch_id`, `as_of_date`) from the template/payload.
For each target business pull `/api/compliance/objects?business_id=X`.

Per-list rules (all lists ascending by business_id):
- `bank_mismatch_ids` ← `bank_account_status == name_mismatch`. (`closed` is a stronger
  hard stop → escalate, not "mismatch".)
- `invalid_tax_ids` ← `tax_id` is malformed vs the normal pattern. Valid pattern is
  `TIN` + 6 digits (e.g. `TIN608869`); a value containing a non-digit like `TIN12X899` is
  invalid.
- `expired_license_ids` ← `license_expiry < as_of_date`.
- `risk_score_override_flags` ← `risk_score >= 70`.
- `review_queue_ids` ← any business needing compliance/AP review before release
  (remediable issue: bank mismatch, invalid tax id, expired license, missing docs,
  screening not run, in_review/awaiting/not_started review_status).

decisions:
- `escalate`: hard stop — `bank_account_status == closed`, sanctions `confirmed_match`,
  `confirmed_pep`, or suspected shell company.
- `hold`: remediable gap — bank `name_mismatch`, invalid tax id, expired license, missing
  required docs, screening `not_run`, or `risk_score >= 70`.
- `release`: clean — bank `verified`, screening clear/run, valid tax id, license current,
  no missing docs, risk below override threshold.

---

## 5. Family D — Prepaid / GL reconciliation close

Scope is given by `selected_prepaid_invoice_ids`, target `accounts`, `close_period`
(YYYY-MM), `entity`, and a `variance_threshold_abs`. Template wants `account_rollup` per
account, `invoice_results` per invoice (same order as the scope file), plus
`default_missing_term_invoice_ids` and `exception_invoice_ids`.

Fetch each invoice by `prepaid_invoice_id`; fetch GL via
`/api/prepaids/gl-balances?account=A&period=close_period` (match the entity).

### Straight-line amortization (per invoice, recognition_method=straight_line)
Use the invoice's own `monthly_amortization` as the per-month figure.
Let `n` = number of monthly periods recognized from `service_start`'s month through the
close-period month, inclusive: `n = (close_year - start_year)*12 + (close_month - start_month) + 1`.
- `cumulative_amortization_through_<period>` = min(monthly × n, original_amount) (never amortize past the full original).
- `month_amortization` = cumulative(n) − cumulative(n−1) (equals monthly while within the
  schedule; the final month is the remainder; 0 after the schedule has fully ended).
- `ending_balance` = original_amount − cumulative (≥ 0; ≈ 0 once `service_end` ≤ period end).
Round each money figure to 2 decimals.

### Account rollup
Per account: `selected_invoice_count`, and sums of `original_amount`, month amortization,
cumulative, and schedule `ending_balance` across the in-scope invoices for that account.
`schedule_ending_balance` = Σ invoice ending balances. `gl_ending_balance` = GL ending
balance for that account+period. `variance_amount = schedule_ending_balance − gl_ending_balance`
(2 decimals). `variance_flag = |variance_amount| > variance_threshold_abs` (default 100.0).

### Flags & status
- `default_missing_term_flag` (invoice) ← `data_quality_flags` contains a term/date defect,
  primarily `missing_contract_dates` (also treat `manual_override` defaulting terms as
  applicable when relevant). `has_default_missing_term_flag` (account) = any such invoice.
- `exception_flag` (invoice) ← invoice has any data-quality defect or its own schedule
  doesn't reconcile (bad term/dates, duplicate invoice number, etc.). Collect into
  `exception_invoice_ids` (ascending).
- `account_status`:
  - `requires_reconciliation` if the account has default/missing-term invoices or otherwise
    can't be reconciled;
  - else `variance_review` if `variance_flag` is true;
  - else `reconciled`.

Lists `selected_invoice_ids` and `invoice_results` follow the **scope file order**;
`default_missing_term_invoice_ids` and `exception_invoice_ids` are **ascending by id**.

---

## 6. Common misjudgments to avoid

- Trusting a snapshot/CSV/prompt status instead of re-querying the live API.
- Echoing source `status`/`review_status` as the decision rather than computing a
  release-control bucket from evidence.
- Treating a linked bill as valid without checking amount-equals-claim and vendor match —
  a large amount mismatch means the claim is NOT validly linked (blocked).
- Counting an in-flight payment (`scheduled`/`processing`) as settled — only `cleared`
  pays a claim off; in-flight = still an open payable.
- Counting duplicate UBO names twice, or using the wrong reporting threshold (it is 25%).
- Confusing `bank closed` (hard stop → escalate) with `name_mismatch` (remediable → hold).
- Forgetting to clamp amortization/aging at 0 (no negative ending balances).
- Summing blocked or paid claims into the open-payable total (it is payable-bucket only).
- Emitting extra keys when `additional_properties_allowed: false`, or wrong list ordering
  (ascending-by-id vs scope-file order vs alphabetical-by-enum), or wrong money precision
  (2 decimals vs integer cents).
- Using a base URL from the prompt instead of the runner-provided one.

---

## 7. Generic SOP

1. Read `prompt.txt` + every file under `input/payloads/`, especially the answer template;
   note required keys, enums, orderings, precision, `additional_properties_allowed`, and
   any literal required values to echo.
2. Identify the family (claims close / vendor onboarding / payment-release / prepaid recon /
   stale-snapshot) and the exact in-scope ID list.
3. Hit `/api/health` + `/endpoints`; fetch each in-scope entity and its linked records from
   the live API (claims→bills→payments, or compliance objects, or prepaid invoices + GL).
4. Apply the family rules above to compute decisions, buckets, counts, totals, flags.
5. Assemble the JSON exactly to the template (key set, ordering, sorting, rounding); drop
   extras when additionalProperties is false; JSON only, no prose.
6. Self-check: every requested ID appears exactly where required; lists sorted correctly;
   money rounded once; totals only include the intended bucket; enum values are spelled
   exactly as the template allows.
