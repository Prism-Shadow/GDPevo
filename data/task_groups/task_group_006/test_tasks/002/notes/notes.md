# test_002 Notes

## English

This task creates a June 2026 month-end AP supplier release package using ProcureOps invoices, payments, receipts, POs, and supplier records. The solver-facing prompt and payloads are English-only and do not reveal scoring weights or SOP.

Train anchors: `train_003` teaches AP invoice/payment reconciliation, supplier balances, program totals, and release/hold queues. `train_005` teaches receipt scoping, excluding same-PO receipts that are not the invoice-linked receipt, and treating local request notes as supporting context rather than authority.

Gold basis: only `AP-HEXEL-3309` releases. `AP-00007` has a matched receipt but blocked payment, so it stays held. `AP-00008` and `AP-00038` have scheduled payments but no receipt as of `2026-06-30`. `AP-00004` references `RCV-00003`, but that receipt is dated `2026-07-03` and is in inspection hold, so it is excluded by cutoff. Release total is `28909.24`; hold and exception payment totals are `159239.67`.

Scoring uses eight exact-match points with weights `[3, 3, 2, 2, 3, 2, 2, 1]`: package identity and targets; invoice supplier/program/PO/AP fields; receipt cutoff and quantities; payment linkage and bank actions; release/hold decisions, queues, and totals; supplier summary; program summary; payment buckets and source precedence.

