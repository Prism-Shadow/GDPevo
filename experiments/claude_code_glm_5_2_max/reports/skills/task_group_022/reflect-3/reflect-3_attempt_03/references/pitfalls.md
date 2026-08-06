# Atlas Commerce Ops — Recurring Pitfalls

Each trap below silently corrupts one or more output fields. The fix is the resolution column.

| Trap | Symptom | Resolution |
|---|---|---|
| **Truncated result set** | A `GROUP BY`/detail query returns exactly 5000 rows; counts are short or wrong with no error. | Check `truncated` on every response. Aggregate in SQL and restrict by the in-scope cohort via single-level `IN (subquery)`. See `query-patterns.md`. |
| **Missing production filter** | Cohort includes sandbox/internal rows → counts too high; rates skewed. | Every production scope = `is_test=0 AND is_internal=0`, propagated through `account_id`. Confirm via account names. |
| **Trusting `current_status` snapshots** | "At cutoff" counts disagree with event history; resolved cases still show OPEN. | Replay append-only events ≤ cutoff. Snapshots lag by design. |
| **Earliest-delivered vs effective-final-status** | Completeness/on-time wrong; "delivered by cutoff" over- or under-counted. | Use the **final** scan's `canonical_status` at/before cutoff (max `canonical_event_at`, tiebreak `ingested_at`, `scan_row_id`), not "any DELIVERED scan exists". |
| **Skip retry dedup** | Duplicate re-ingested rows double-count events/scans. | Keep latest `ingested_at` per `(source_system, external_event_id)` before any effective aggregation. |
| **USD FX hardcoded to 1.0** | Net refund / gross USD slightly off. | Use the **daily** `fx_rates.usd_per_unit` for the row's currency AND service_date — the USD rate itself varies by date. Sum full precision, round last. |
| **Reversals ignored or under-counted** | `effective_linked_reversal_count` and `net_refund_amount` wrong. | Count in-scope REVERSED refunds that have a `linked_refund_id` (even if their target isn't SETTLED), and **subtract** their USD from net. |
| **Support clock starts at OPENED event** | SLA breach counts wrong; boundary cases land exactly on thresholds. | Start the active clock at the case's `opened_at` **header field**, not the `OPENED` event timestamp (they differ by minutes; data is seeded so `opened_at` puts cases just over thresholds). |
| **Active time not pausing on WAITING_CUSTOMER** | Resolution active-time / first-response active-time too large. | Subtract `WAITING_CUSTOMER`→next-agent-event intervals from elapsed time. |
| **`>=` instead of `>` for "EXCEEDS"** | Cases exactly at the SLA threshold flip breach status. | "EXCEEDS the threshold" is strictly `>`. (Boundary cases at 8.0/16.0/24.0h are seeded on purpose.) |
| **Ranking on rounded values** | Worst regions/accounts or top-N order wrong on near-ties. | Sort/rank on **unrounded** rates, then round for output. Tie-break by the stated secondary key (usually id ascending). |
| **Rounding intermediate sums** | Net amount off by cents. | Sum full-precision values, round only the final reported number to the stated decimals. |
| **Extra fields / wrong types in output** | Schema rejection / 0 score on the object. | Match `answer_template.json` exactly: `additionalProperties:false`, enums, array bounds, ID patterns. Validate before writing `answer.json`. |
| **Correction changes raw or unrelated rows** | APPLIED rule fails; data integrity broken. | Minimal canonical correction only: one `UPDATE` on the one canonical field of the one scan row (WHERE pinned to row + old value), plus one `correction_audit` INSERT, in one transaction with `expected_total_changes=2`. |
| **Cohort for backlog not production-restricted** | Pre/post backlog counts wrong. | Backlog is over **production** shipments in the named batch with an effective scan ≤ cutoff. |
| **State cutoff vs created/opened window conflated** | "completed by cutoff" / "delayed" wrong. | Distinguish the **opened/created window** (eligibility) from the **state cutoff** (later; used for completion/rework/resolution/delayed predicates). |
