# Atlas Commerce Ops — Safe vs Rejected SQL Patterns

The read endpoint `POST /api/sql` (JSON `{sql, params}`) and the transaction endpoint `POST /api/sql/transaction` (`{statements:[{sql,params}], expected_total_changes}`) enforce two rules that silently corrupt or reject queries. Auth: `Authorization: Bearer <token>` (runtime-provided); `Content-Type: application/json`.

## Rule 1 — 5000-row hard cap

Every `POST /api/sql` result is capped at 5000 rows **regardless of `LIMIT`**. The response includes:
```json
{"columns":[...], "rows":[...], "row_count": 5000, "truncated": true}
```
When `truncated` is true, the rows are an incomplete prefix — any count/sum over them is wrong. `LIMIT 10000` does **not** raise the cap.

**Mitigations (in order of preference):**
1. **Aggregate in SQL** so the result is inherently small: `GROUP BY` + `COUNT/SUM/MIN/MAX`. E.g. per-shipment delivered timestamp: `SELECT shipment_id, MIN(canonical_event_at) … GROUP BY shipment_id`.
2. **Restrict to the in-scope cohort** with a single-level `IN (subquery)` so the scanned set is small:
   ```sql
   SELECT cs.shipment_id, MIN(cs.canonical_event_at) AS delivered_at
   FROM carrier_scans cs
   WHERE cs.canonical_status = ? AND cs.canonical_event_at <= ?
     AND cs.shipment_id IN (
       SELECT s.shipment_id FROM shipments s
       JOIN orders o ON o.order_id = s.order_id
       JOIN accounts a ON a.account_id = o.account_id
       WHERE a.is_test = 0 AND a.is_internal = 0 /* + other scope */
     )
   GROUP BY cs.shipment_id
   ```
3. If you need per-row detail for a bounded cohort (e.g. all scans for ~500 cohort shipments), fetch the **cohort keys first** (small), then query the child table restricted to `WHERE key IN (that same single-level subquery)` — verifiably below the cap — and reduce in your own code.
4. Always **check `truncated`** before trusting any result; treat `truncated:true` as a hard error and refine the query.

## Rule 2 — nested-subquery rejection

`{"error":"query rejected"}` (HTTP 400) is returned for several shapes. Empirically:
- ✓ Single-level `WHERE col IN (SELECT … FROM …)` — allowed (this is the workhorse).
- ✓ Single-level FROM-subquery with no inner subquery: `SELECT … FROM (SELECT … FROM t GROUP BY …) x`.
- ✗ FROM-subquery that itself contains a subquery or self-join, then aggregated again at an outer level — rejected.
- ✗ Wrapping a self-join dedup in another SELECT/GROUP BY — rejected.
- ✗ `SELECT alias.*` (star with alias) inside a CTE/FROM-subquery — rejected; enumerate columns explicitly.
- ✓ Plain `COUNT(DISTINCT col)`, `GROUP BY … HAVING count(*)>1`, correlated `WHERE col IN (SELECT …)` — fine.

**When a dedup-by-latest-ingested pattern is rejected as a nested construct**, move the dedup into your own code: fetch the cohort's rows in a flat query (restricted by scope so it's under 5000), then keep the latest `ingested_at` per `(source_system, external_event_id)` locally.

## Transaction endpoint (corrections only)

`POST /api/sql/transaction` commits atomically; returns `{total_changes, statements:[{type, changes}]}`.
- Allowed statements: `SELECT`/`WITH`; **guarded** `UPDATE` on `carrier_scans` or `inventory_movements` (the `WHERE` must pin the target row, typically `WHERE scan_row_id = ? AND canonical_<field> = ?`); `INSERT INTO correction_audit` with all columns.
- Set `expected_total_changes` to the expected sum of `changes` (e.g. 2 for one UPDATE + one INSERT).
- A guarded UPDATE that matches exactly one row reports `changes: 1`. Match the old value in the `WHERE` so a no-op or multi-row update is caught.

## General query hygiene

- Use `params` (positional `?`) for all literals — strings, numbers, booleans, nulls. Timestamps stay as ISO-8601 `…Z` text; dates as `YYYY-MM-DD`.
- Comparisons on timestamp text work lexicographically because everything is UTC `…Z` and zero-padded.
- Validate small result sets in your own code (dedup, effective-final-status, active-time pauses) rather than fighting the nested-subquery limit in SQL.
