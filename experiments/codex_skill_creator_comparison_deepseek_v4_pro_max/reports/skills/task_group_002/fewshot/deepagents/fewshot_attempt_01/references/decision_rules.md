
## Decision Rules

### Quote + freight: Recommended mode

| Conditions | Recommendation |
|---|---|
| SEA valid and low risk | `SEA` |
| SEA medium/high risk, AIR valid and low risk | `AIR` |
| Both SEA and AIR have issues, ROAD valid and low risk | `ROAD` |
| Only one option valid and low risk | That option |
| All options risky | Prefer lowest-risk, fastest valid option |

Never recommend a stale freight option as the primary recommendation.

### Quote + freight: Payment terms mapping

| Customer payment_profile / segment | Payment terms |
|---|---|
| `NEW_CLIENT_REVIEW` / `new_ngo` | `PREPAY_100` |
| `NET_30_AFTER_PO` / `recurring_ngo` | `NET_30_AFTER_PO` |
| `NET_30_AFTER_PO` / `recurring_commercial` | `NET_30_AFTER_PO` |
| `MILESTONE_BILLING` | Check opportunity record |

### Quote + freight: Customer policy label

Derive from customer `segment`:

| Segment | Policy label |
|---|---|
| `recurring_ngo` | `RECURRING_NGO` |
| `recurring_commercial` | `RECURRING_COMMERCIAL` |
| `new_ngo` | `NEW_NGO` |
| `implementation_services` | `IMPLEMENTATION_SERVICES` |

### Quote + freight: Freight risk mapping

| route_risk | risk_level | risk_flag |
|---|---|---|
| `low` | `LOW` | `NONE` |
| `medium` | `MEDIUM` | `MEDIUM_BORDER_RISK` |
| `high` | `HIGH` | `HIGH_CUSTOMS_RISK` (or `HIGH_BORDER_RISK` based on risk_notes) |

### Quote + freight: Freight validity

| Condition | validity_status | source_is_stale |
|---|---|---|
| `valid_until >= quote_date` | `VALID` | `false` |
| `valid_until < quote_date` | `STALE` | `true` |

### Module quote: Payment terms

| Customer segment | Payment terms |
|---|---|
| `new_ngo` | `PREPAY_100` |
| Other segments with `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| Regular recurring | Check customer `payment_profile` |

### Reconciliation: Revenue recognition status

| Invoice status | Payment exists | Revenue journal exists | Status |
|---|---|---|---|
| `paid` | posted payment | journal found | `RECOGNIZED` |
| `paid` | posted payment | no journal | `MISSING_REVENUE_JOURNAL` |
| `unpaid` | no payment | -- | `NOT_REQUIRED_UNPAID` |
| `partial` | partial payment | partial/no journal | `MISSING_REVENUE_JOURNAL` (if any paid portion unjournaled) |

### Reconciliation: Accounting action

| Condition | Action | Debit | Credit | Owner |
|---|---|---|---|---|
| Any paid milestone missing revenue journal | `RECORD_REVENUE_MS{N}` | `DEFERRED_REVENUE` | `IMPLEMENTATION_SERVICES_REVENUE` | `ACCOUNTING` |
| All paid milestones have journals | `NO_ACCOUNTING_ACTION` / `VERIFY_REVENUE_ONLY` | `NONE` | `NONE` | `NONE` |

### Reconciliation: Collection action

| Condition | Action | Owner |
|---|---|---|
| Unpaid milestone, due date past current date | `SEND_COLLECTION_NOTICE` | `COLLECTIONS` or `ACCOUNT_MANAGEMENT` |
| Unpaid milestone, due date in future | `MONITOR_UNPAID_NOT_DUE` | `ACCOUNT_MANAGEMENT` |
| All milestones paid | `NO_COLLECTION_ACTION` | `NONE` |

### Reconciliation: Event invite action

| Event status | Action |
|---|---|
| `scheduled` | `SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`) |
| `confirmed` | `VERIFY_INVITE_SENT` or `SEND_EVENT_INVITATION` |
| `live` / `completed` | `NO_INVITE_ACTION` or `VERIFY_INVITE_SENT` |

Check the specific template enum values and use whichever matches.

### Reconciliation: Revenue recognition summary

| Condition | recognition_status |
|---|---|
| All paid milestones recognized, no unpaid ones with missing journals | `COMPLETE_FOR_PAID_MILESTONES` |
| At least one paid milestone missing a journal | `MISSING_FOR_PAID_MILESTONES` |
| No paid milestones at all | `NOT_REQUIRED` |

### Reconciliation: Event status mapping

| API event status | Template-friendly status |
|---|---|
| `scheduled` | `SCHEDULED` |
| `confirmed` | `ACTIVE` or `SCHEDULED` |
| `live` | `ACTIVE` |
| `completed` | `COMPLETED` |
| `tentative` | `SCHEDULED` |

### Reconciliation: Voucher status mapping

| API voucher status | Template-friendly status |
|---|---|
| `active` | `ACTIVE` |
| `draft` | `DRAFT` |
| `expired` | `EXPIRED` |
| `disabled` | `DISABLED` |
