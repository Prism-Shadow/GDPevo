# train_005 Notes

## English

The solver sees only an English prompt, the answer template, and a small release packet. The packet names the target IDs: `PRG-AX17`, POs `PO-AX17-4481`, `PO-AX17-4519`, `PO-00031`, and `PO-00038`; receipts `RCV-BLUE-14`, `RCV-00017`, and `RCV-00020`; and AP invoices `AP-LUMA-7714`, `AP-VANTIX-2188`, `AP-00027`, and `AP-00032`. Exact PO-73xx IDs are absent from the shared data, so `PO-00031` and `PO-00038` are used as the available generated PO records and are explicitly named in the payload.

The expected work is to query the shared API for purchase orders, receipts, and AP invoices, then combine that state with the local chargeback register excerpt. The release note and PO-73xx alias note are supporting context only. The authoritative sources are ProcureOps PO, receipt, and AP records plus the local chargeback register excerpt because the shared environment does not expose a chargeback endpoint.

Solution basis: `AP-LUMA-7714` is tied to `RCV-BLUE-14`, where 216 units were received against a 240-unit AP bill, producing an approved underage chargeback of `24 * 84.50 = 2028.00`; the later same-PO receipt `RCV-00001` belongs outside this invoice release line. `AP-00032` has accepted receipt `RCV-00020`, but the invoice bills four more units than the accepted receipt, producing an approved AP quantity variance of `4 * 295.94 = 1183.76`. `AP-VANTIX-2188` remains held because `PO-AX17-4519` has no receipt. `AP-00027` is not released because `RCV-00017` is still in inspection hold with a pending underage chargeback of `99 * 84.50 = 8365.50`. Approved chargebacks total `3211.76`, pending chargebacks total `8365.50`, and the net AP release total is `48058.94`.

Evaluation uses eight exact-match scoring points with raw weights `[3, 3, 2, 2, 3, 2, 2, 1]`: target IDs and review date; invoice decisions and reasons; receipt inclusion and exclusion; per-invoice financial amounts; release/hold sets and totals; receiving exception classifications; source precedence; and follow-up actions. Lists are normalized by the evaluator, and currency is rounded to cents.

As a train task, this teaches transferable conventions through answer comparison rather than through the prompt: match AP release to the invoice-linked receipt, treat similar same-PO receipts as exclusions when they belong to another invoice, use approved chargebacks for net release, hold pending quality or missing-receipt cases, and separate authoritative system/register sources from supporting request notes.
