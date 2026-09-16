# Prepaid-GL Reconciliation Patterns

Reconcile prepaid invoice amortization schedules against general ledger
ending balances for a specified close period and set of accounts.

## Workflow

1. Read the close scope payload to get entity, period, accounts, and
   selected invoice IDs.
2. Fetch /prepaids/invoices or /api/prepaids/invoices.
3. Fetch /gl/balances or /api/prepaids/gl-balances.
4. Filter invoices to the selected invoice IDs in the scope.
5. Filter GL balances to the target accounts and close period.

## Straight-Line Amortization

Each prepaid invoice has a start_date, term_months, original_amount, and
monthly_amortization. The amortization_schedule records cumulative
amortization through each period.

For a given close period (YYYY-MM):

- **Monthly amortization**: the monthly_amortization from the invoice, or
  compute as original_amount / term_months rounded to two decimals.
- **Cumulative amortization through period**: sum of all amortization
  amounts for periods up to and including the close period. Read from the
  amortization_schedule array when available; otherwise compute from
  start_date and term_months.
- **Ending balance**: original_amount minus cumulative amortization through
  period. Clamp to zero (do not report negative ending balances; use 0.00).
  Small positive residuals (e.g., 0.01) from rounding are valid.

Use the script at scripts/amortization.py for deterministic computation
when schedule arrays are incomplete or absent.

## Invoice-Level Fields

For each selected invoice, populate:

- `prepaid_invoice_id`: as given.
- `account`: the account code from the invoice.
- The period amortization field: monthly amortization for the close period.
- The cumulative amortization field: sum of amortization from start
  through the close period.
- `ending_balance`: original_amount minus cumulative amortization, clamped
  to 0.00.
- `default_missing_term_flag`: true when the invoice has no term_months or
  term_months is 0, or when monthly_amortization is missing/underivable.
- `exception_flag`: true when ANY of:
  - Ending balance is 0.00 while cumulative amortization does not equal
    original_amount (rounding tolerance 0.02).
  - Ending balance is negative (treat as clamped to 0.00, but still flag).
  - Monthly amortization for the period does not match expected
    straight-line value.
  - Start date is after the close period (no amortization should have
    occurred, but schedule shows amortization).
  - Any other data-quality anomaly in the invoice record.

## Account-Level Rollup

For each account:

- `account_name`: from the GL balance record for that account.
- `selected_invoice_count`: number of selected invoices in this account.
- `original_amount_total`: sum of original_amount for all selected
  invoices in this account.
- Period amortization total: sum of monthly amortization for the close
  period across invoices.
- Cumulative amortization total: sum of cumulative amortization through
  the close period.
- `schedule_ending_balance`: original_amount_total minus cumulative
  amortization total.
- `gl_ending_balance`: the GL ending balance for this account and period.
- `variance_amount`: schedule_ending_balance minus gl_ending_balance.
- `variance_flag`: true when |variance_amount| > variance_threshold_abs
  (from scope, typically 100.00).
- `has_default_missing_term_flag`: true when any invoice in this account
  has default_missing_term_flag: true.
- `account_status`:
  - `reconciled`: variance_flag is false.
  - `variance_review`: variance_flag is true but variance is explained by
    known items.
  - `requires_reconciliation`: variance_flag is true and unexplained.

## Default/Missing Term Invoices

Collect all invoice IDs with default_missing_term_flag: true, sorted
ascending.

## Exception Invoices

Collect all invoice IDs with exception_flag: true, sorted ascending.
