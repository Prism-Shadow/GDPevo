# Court Operations Portal — endpoint & field reference

The portal is a read-only JSON API. Base URL comes from `environment_access.md`
as `GDPEVO_ENV_BASE_URL` (it is the value that replaces `<TASK_ENV_BASE_URL>`
in the prompt). **No credentials.** Each prompt lists the subset of endpoints it
needs, but they all behave the same way.

## Calling convention

- `GET {BASE}/api/<resource>` returns `{"count": N, "results": [ ... ]}`.
- Every collection supports server-side filtering by exact field match, e.g.
  `?case_number=RC-25-0412`, `?citation_number=OR26-TR-1188`,
  `?petition_id=VA-PET-716A`, `?jurisdiction_code=AR-RC`. **Always filter** —
  the unfiltered lists are capped (100 rows) and contain many decoys.
- `GET {BASE}/api/search?q=<text>` is a fuzzy cross-type search. Each row carries
  `result_type` (`cases`, `charges`, `docket_entries`, …) and `result_id`. Handy
  to discover the `jurisdiction_code` and related rows for one target id, but it
  returns near-name matches — **confirm the exact id before trusting a row.**

## Resolution order for a matter

1. Read the prompt: note the court/county and every target id
   (case / citation / petition).
2. `GET /api/jurisdictions` → map the county + court level to its
   `jurisdiction_code` (e.g. Redwood Circuit → `AR-RC`, 22nd JD Jefferson →
   `OR22-JEFF`, Gloucester Circuit → `VA-GLO`, Union Circuit → `AR-UC`). Some
   payloads already state the code.
3. Pull each target row by exact id from `cases` / `citations` /
   `financial-petitions`.
4. Using that row's `jurisdiction_code`, pull `fee-schedules`,
   `payment-policies`, and `forms` for the jurisdiction.
5. Pull `charges` (by `case_number`) and `docket-entries` as needed.

## Resource fields you actually use

### /api/jurisdictions
`jurisdiction_code`, `county`, `court_name`, `court_level`, `state`,
`policy_ref`, `timezone`, `active`.

### /api/cases  (criminal CMS — authoritative for identity & counsel)
`case_number`, `defendant_first` / `defendant_last`, `defendant_dob`,
`counsel_type` (`public_defender` | `appointed_private` | `retained`),
`attorney_name`, `attorney_label_raw` (**noisy — see decoys**), `status`
(`disposed` | `deferred` | `continued` | `closed` | …), `disposition_date`,
`jurisdiction_code`, `judge`, `source_system`.

### /api/charges  (authoritative for offense id & structured sentence numbers)
`case_number`, `count_no`, `offense_code`, `statute`, `description`,
`severity` (e.g. "Class D felony", "Class A misdemeanor"), `fine_amount`,
`jail_days_imposed`, `jail_days_suspended`, `probation_months`,
`license_suspension_months`, `assessment_code` (e.g. `DRUG_ASSESSMENT` marks a
lab/drug-assessment-eligible count), `departure_type`
(`none` | `durational` | `dispositional`), `departure_reason`, `plea`,
`disposition` (**may be stale draft text — see decoys**), `verdict`.

### /api/docket-entries
`case_number`, `entry_date`, `entry_type` (`filing` | `hearing` | `disposition`
| `financial` | `clerk_note`), `text`, `source`. Public clerk-note text is
often redacted; use it for entry summaries, not for hidden facts.

### /api/citations  (traffic — authoritative record for a citation)
`citation_number`, `defendant_name`, `defendant_dob`, `jurisdiction_code`,
`statute`, `violation_code` (e.g. `ORS_811_109_100PLUS`, `..._31_40`,
`..._21_30`), `speed_mph`, `zone_mph`, `plea`, `disposition`, `hearing_date`,
`plan_approved`, `monthly_payment`, `first_due_date`, `status`.

### /api/fee-schedules  (authoritative for AMOUNTS)
`fee_id`, `jurisdiction_code`, `fee_type` (`court_cost`, `assessment`,
`user_fee`, `standard_fine`, `county_surcharge`, …), `label`, `amount`,
`mandatory`, `violation_code` (for traffic tiers), `effective_date`,
`end_date`, `priority`, `notes`. **Pick the row whose date window covers the
disposition date** (`effective_date <= disposition_date` and `end_date` is null
or `>= disposition_date`). Rows with a past `end_date` are stale/archived —
never use their amount.

### /api/payment-policies  (authoritative for installment terms)
`policy_id`, `jurisdiction_code`, `min_monthly`, `max_monthly`, `account_fee`,
`down_payment_required`, `first_due_days`, `return_to_court_offset_days`,
`restitution_priority`, `subsequent_petition_rule`, `notes`.

### /api/forms
`form_id`, `form_name`, `jurisdiction_code`, `label`, `required_fields`,
`placeholder_instruction`, `revision_date`. Use `form_id`/`label` and the
`placeholder_instruction` verbatim; corroborate a local form excerpt against it.

### /api/financial-petitions
`petition_id`, `case_number`, `petitioner_name`, `petition_sequence`,
`default_status`, `submitted_date`, `income_monthly`, `obligations_monthly`,
`household_size`, `public_assistance`, `fines_costs_balance`,
`restitution_balance`, `requested_monthly`, `license_suspension_months`,
`probation_report_datetime`.

## Decoys the portal deliberately plants (do not get caught)

- **`attorney_label_raw` lies.** It carries legacy/miskeyed strings like `"RET"`,
  `"APD"`, `"PD conflict label on intake"`. Trust the structured `counsel_type`
  field, and let the signed court record override even that when it explicitly
  reclassifies counsel (e.g. "APD" clarified on the record as appointed-private).
- **`charges.disposition` can be stale draft text** (`nolle prosequi`,
  `dismissed`, `pending`) that contradicts the actual conviction in the hearing
  record. The **court record wins for the disposition**; the portal's numeric
  sentence fields (jail/fine/probation/`departure_type`) still fill fields the
  record leaves unstated.
- **Near-name / similar-defendant rows.** Never borrow a DOB or identifier from a
  different row just because the name is similar — if the target's own record is
  blank, keep the placeholder.
- **Stale fee rows** carry a real-looking `amount` but an expired `end_date`, and
  local worksheets carry old-year amounts and statutory-maximum notes. Use only
  the current scheduled amount.
