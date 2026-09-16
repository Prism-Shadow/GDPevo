## Correction Transaction Protocol

When a task requires a controlled data correction, follow this exact sequence.

### Step 1: Identify the target

Run a read-only query (POST /api/sql) to locate the row and column that needs
changing. Confirm the current (old) value matches the request's description of
the contradiction. The request will specify exactly one canonical field to
correct.

### Step 2: Build the transaction

Submit to POST /api/sql/transaction. The body is a JSON object with a
 array and metadata fields.

Required metadata:
- : always the value from the request (e.g. )
- : the stable key from the request
- : the actor identifier from the request

The  array contains SQL strings:

1. An UPDATE statement that sets the target column to the new value, scoped to
   the exact row by its primary/source key.
2. An INSERT statement into the audit table (see schema for the exact table
   name) with all required audit columns: audit_id, correction_key, entity_type,
   entity_id, source_row_id, field_name, old_value, new_value, reason_code,
   corrected_at, actor.

Example transaction body shape:



### Step 3: Verify the mutation

After the transaction, verify both:

1. Re-query the changed row with POST /api/sql and confirm the value now matches
   the requested new value.
2. Query GET /api/correction-audit with the  or  to
   confirm exactly one audit row was committed.

### Step 4: Report the result

Report  only when exactly one business row was updated, exactly one
audit row was committed, and the post-change query confirms the new value.
Otherwise report .

Do not re-apply a correction that already succeeded. If a correction fails,
report the observed state and do not retry unless the request explicitly
instructs otherwise.

### Important constraints

- Never modify raw source values, source identity fields, or unrelated business
  rows.
- Use only the approved reason_code from the request.
- The transaction is atomic: all statements succeed or none do.
