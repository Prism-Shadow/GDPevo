# Court Operations Portal — API Reference

## Connection

| Setting | Value |
|---|---|
| Base URL | Provided by the task environment (replace `<TASK_ENV_BASE_URL>` token, or read `environment_access.md`) |
| Auth | None (open access) |

## Endpoints

All endpoints are read-only `GET` requests. The portal returns JSON.

### Jurisdictions

```
GET /api/jurisdictions
```

Returns court jurisdiction metadata — jurisdiction codes, court names, and associated fee-schedule references. Use to confirm the correct jurisdiction code for a case and to look up which fee schedule applies.

### Cases

```
GET /api/cases
```

Returns case records. Query by case number to retrieve the authoritative CMS entry for a case — defendant identity, current status, charge links, docket links, and counsel of record. This is the **source of truth** for case status.

### Citations

```
GET /api/citations
```

Returns traffic citation records. Equivalent to `/api/cases` for traffic-violation matters. Returns citation number, defendant, alleged violation, officer, and current status.

### Charges

```
GET /api/charges
```

Returns charge records linked to a case. Each charge includes the statute, offense description, count number, plea, disposition, and any amendments. Use to confirm what was actually convicted (versus what was originally filed or amended away).

### Docket Entries

```
GET /api/docket-entries
```

Returns the docket sheet for a case — every entry with date, type, and text. Use to confirm whether a final sentencing order was signed and entered, and on what date.

### Citations

```
GET /api/citations
```

(Already listed above. See Citations.)

### Fee Schedules

```
GET /api/fee-schedules
```

Returns current fee schedules by jurisdiction. Each schedule lists fee codes and current amounts. Always use this **instead of** stale amounts from local worksheets or archived intake sheets.

### Payment Policies

```
GET /api/payment-policies
```

Returns the current payment policy for a jurisdiction — minimum monthly installment, maximum term, account-fee treatment, and default due-date rules. Use when constructing payment plans or installment orders.

### Forms

```
GET /api/forms
```

Returns form metadata — form IDs, labels, revision dates, and field groups. Use to confirm the current form version and label before filling form-reference fields in the output.

### Financial Petitions

```
GET /api/financial-petitions
```

Returns financial petition records by petition ID. Includes submitted date, requested terms, balances stated by the counter, and intake classification. Use to cross-reference petition details against case records.

### Search

```
GET /api/search
```

General search endpoint. Use as a fallback for verifying defendant identity, DOB, or counsel when direct case/petition lookups return ambiguous results. Also useful for confirming that similarly named defendants are distinct individuals.
