# Recognizing the task family

Identify the family from the prompt language and the template's top-level keys,
then follow the matching decision table in `business_rules.md`. Templates vary in
exact key names across tasks — always re-read the actual template; this is a map,
not a substitute.

| Family | Prompt cues | Template signature keys | Rules |
|---|---|---|---|
| **Nomination readiness** | "sourcing nomination", "readiness packet", "committee" | `package_line_skus`, `nomination_lines`, `committee_action` | §A + budget headroom §2, risk §5 |
| **Receiving / AP reconciliation** | "receiving closeout", "received-vs-ordered", "AP hold position", batch id | `inspection_summary`, `line_reconciliation`, `invoice_review`, `financials`, `decision` | §B + qty reconciliation §4 |
| **AP close** | "AP close", "payment-hold", "vendor-balance", "hold/release queues" | `invoice_decisions`, `vendor_balances`, `program_summary`, `payment_hold_queue`, `payment_release_queue` | §C + payments §7 |
| **Change-control decision** | "change-control", "amendment", "contract and program-budget impact" | `contract_check`, `program_budget_check`, `approval_check`, `supplier_risk_check`, `decision` | §D + §2,§3,§5,§6 |
| **AP release / chargeback** | "release file", "chargeback", "release/hold", "netting" | `release_decisions`, `receiving_exceptions`, `summary` with chargeback totals | §E + §8 |

## Per-family notes

**Nomination readiness** — one `nomination_lines` entry per package SKU. The
`selected_supplier_id` is the PO/contract supplier for that SKU. `commercial_basis_id`
= contract id or null. Evidence id lists (`receipt_evidence_ids`,
`invoice_exception_ids`, `risk_event_ids`) are scoped "as of as_of_date" and
sorted. Roll up suppliers into the committee buckets by worst line decision.

**Receiving / AP reconciliation** — `evidence.endpoint_record_ids` is the set of
every API id you actually used (PO, receipt, invoice, supplier, contract, item,
risk event), sorted; `task_payloads_reviewed` lists the local files you read
(e.g. `input/payloads/receiving_memo.md`). One `line_reconciliation` row per PO
line, sorted by `po_line_id`.

**AP close** — answer only the invoices the memo names, sorted by invoice_id.
Honor the memo's stated opening balance (often 0.00) and its payment cutoff.
`vendor_balances` is one row per distinct supplier in the slice; `program_summary`
one row per distinct program. `total_close_balance` = Σ held balances.

**Change-control** — single object. The memo carries the business controls
(tax_rate_percent, "exclude cancelled POs", `approval_good_actions`,
"supplier_watch_rating: context only unless an open severe event"). `blocker_count`
counts failed gates; `decision` and `required_actions` follow §D deterministically.

**AP release / chargeback** — the local packet carries the chargeback register
(authoritative for chargebacks — the API has none) plus request notes and a
stale alias note (supporting-only). Net only **approved** chargebacks; pending
ones hold. A PO with multiple receipts: scope the named one, exclude the rest.
A PO with no receipt → hold, synthetic `receipt_id = "MISSING:<po_id>"`. Classify
sources into authoritative vs supporting-only as the summary requires.
