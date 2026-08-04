++---
++name: portal-api-reference
++description: Reference for querying the Court Operations Portal REST API during court closeout tasks.
++---
+
+# Court Operations Portal — API Query Reference
+
+Base URL is provided via the `<TASK_ENV_BASE_URL>` placeholder in the prompt (typically `http://task-env:9018/`). All endpoints are read-only `GET`. Append query parameters as URL query strings.
+
+## Endpoint query patterns
+
+### `/api/cases` — Case records
+
+Query by case number to retrieve the court's current case record (defendant identity, status, counsel, flags).
+
+```
+GET {BASE_URL}/api/cases?case_number={CASE_NUMBER}
+```
+
+Key fields in response: `case_number`, `defendant_name`, `dob`, `counsel_type`, `attorney_name`, `case_status`, `jurisdiction_code`.
+
+### `/api/charges` — Charge details
+
+Query by case number to retrieve charge records, offense codes, and plea/finding history.
+
+```
+GET {BASE_URL}/api/charges?case_number={CASE_NUMBER}
+```
+
+Key fields: `count_no`, `offense_code`, `statute`, `plea`, `charge_disposition`, `offense_date`.
+
+### `/api/citations` — Traffic citations
+
+Query by citation number for traffic docket tasks.
+
+```
+GET {BASE_URL}/api/citations?citation_number={CITATION_NUMBER}
+```
+
+Key fields: `citation_number`, `defendant_name`, `violation_code`, `alleged_speed`, `posted_speed`, `officer`, `event_date`.
+
+### `/api/docket-entries` — Docket text and register actions
+
+Query by case number to see prior docket entries, register codes, and disposition text.
+
+```
+GET {BASE_URL}/api/docket-entries?case_number={CASE_NUMBER}
+```
+
+Key fields: `entry_date`, `docket_entry_type`, `summary_code`, `financial_total`, `entry_text`.
+
+### `/api/jurisdictions` — Court metadata
+
+Query to confirm jurisdiction code and court name.
+
+```
+GET {BASE_URL}/api/jurisdictions?code={JURISDICTION_CODE}
+```
+
+Key fields: `jurisdiction_code`, `court_name`, `state`, `county`.
+
+### `/api/fee-schedules` — Current fee amounts
+
+Query by jurisdiction and fee type to get the active fee schedule. Use this to resolve stale local amounts.
+
+```
+GET {BASE_URL}/api/fee-schedules?jurisdiction_code={CODE}
+GET {BASE_URL}/api/fee-schedules?jurisdiction_code={CODE}&fee_type={TYPE}
+```
+
+Key fields: `schedule_id`, `jurisdiction_code`, `fee_type`, `fee_code`, `amount`, `effective_date`, `status`.
+
+Common fee codes: `court_cost`, `fine`, `drug_assessment`, `crime_lab_fee`, `public_defender_user_fee`, `county_surcharge`.
+
+### `/api/payment-policies` — Installment and payment rules
+
+Query by jurisdiction to get active payment policy (minimum/maximum installment, down-payment rules, return-to-court triggers).
+
+```
+GET {BASE_URL}/api/payment-policies?jurisdiction_code={CODE}
+```
+
+Key fields: `policy_id`, `jurisdiction_code`, `minimum_monthly`, `maximum_monthly`, `down_payment_required`, `return_to_court_trigger`, `account_fee_policy`.
+
+### `/api/forms` — Form metadata
+
+Query by jurisdiction or form family to get form IDs, labels, field groups, and revision dates.
+
+```
+GET {BASE_URL}/api/forms?jurisdiction_code={CODE}
+GET {BASE_URL}/api/forms?form_family={FAMILY}
+```
+
+Key fields: `form_id`, `form_label`, `form_family`, `revision_date`, `jurisdiction_code`, `field_groups`.
+
+Common form families: `CC-1375` (probation referral), `CC-1379` (license/installment order), local payment plan forms.
+
+### `/api/financial-petitions` — Payment petitions
+
+Query by petition ID or case number for installment agreement details.
+
+```
+GET {BASE_URL}/api/financial-petitions?petition_id={PETITION_ID}
+GET {BASE_URL}/api/financial-petitions?case_number={CASE_NUMBER}
+```
+
+Key fields: `petition_id`, `case_number`, `petitioner_name`, `sequence`, `requested_amount`, `balances`, `budget`, `status`.
+
+### `/api/search` — Entity search
+
+Search for cases, defendants, or citations by partial match.
+
+```
+GET {BASE_URL}/api/search?q={QUERY_STRING}&type={case|defendant|citation}
+```
+
+Use this to find records when identifiers are ambiguous or to verify that a defendant does not have other open matters.
+
+## Cross-checking strategy
+
+For every target case or citation:
+1. Fetch the case/citation record from `/api/cases` or `/api/citations`.
+2. Fetch charges from `/api/charges`.
+3. Fetch docket entries from `/api/docket-entries`.
+4. Fetch the fee schedule from `/api/fee-schedules` for the relevant jurisdiction.
+5. Fetch payment policy from `/api/payment-policies` if payment plans are involved.
+6. Fetch form metadata from `/api/forms` if form entries are needed.
+7. Fetch petition data from `/api/financial-petitions` if petitions are in scope.
+
+Always use portal data to override stale or conflicting local data. Local hearing notes and audit memos are authoritative for courtroom events (what the judge said on the record), while portal data is authoritative for system-of-record values (identity, fee schedules, form revisions).
