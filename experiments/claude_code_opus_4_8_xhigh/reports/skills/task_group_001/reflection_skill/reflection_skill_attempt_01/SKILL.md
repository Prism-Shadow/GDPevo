---
name: harborcrm-front-of-funnel
description: >-
  Use for HarborCRM front-of-funnel CRM/marketing tasks: post-event sponsor
  reconciliation and CRM handoff, trade-show exhibitor prospecting/qualification,
  raw contact-import hygiene/dedup, sponsor/lead follow-up planning, and CRM
  create/update/no-action decisions. Covers reconciling event orders, finance
  invoices, badge scans, CRM accounts/contacts/campaign-members/opportunities,
  import batches, and tradeshow exhibitor/meeting-interest data into a strict
  JSON answer that conforms to a supplied answer_template.json.
---

# HarborCRM Front-of-Funnel Solver

This skill encodes the SOPs and business rules for solving HarborCRM tasks. Every
task asks you to read the live read-only JSON API, apply domain rules, and emit a
single JSON object that conforms exactly to a provided `answer_template.json`.

## 0. Environment / API usage

- Base URL is given in the prompt or an `environment_access.md` (commonly
  `http://127.0.0.1:8080`; some prompts mention `:8067` — confirm with
  `GET /health`). Use `curl -s`. All responses are JSON.
- Endpoints you will use:
  - `GET /api/events/{event_id}` — has `start_date`, `end_date`,
    `followup_days_after_end`, `sponsor_followup_days_after_end`,
    `lead_opportunity_amount`, `campaign_code`, `status`.
  - `GET /api/events/{event_id}/orders` and `/sponsor_packages` — sponsor orders
    with `order_status`, `amount`, `account_id`, `ticket_contacts`.
  - `GET /api/events/{event_id}/badges` — badge scans with `badge_type`,
    `company_name`, `contact_name`, `email`, `phone`, `scan_score`.
  - `GET /api/finance/invoices?event_id=` (also `account_id=`) — `status`,
    `amount`, `paid_amount`, `deferred_amount`, `due_date`.
  - `GET /api/crm/accounts` (`status=`, `owner_region=`) — `status`
    (customer/prospect/disqualified), `disqualified_reason`, `name`, `domain`.
  - `GET /api/crm/contacts` (`account_id=`) — `name`, `email`, `phone`,
    `opted_out`, `account_id`, `contact_id`.
  - `GET /api/crm/opportunities` (`event_id=`, `account_id=`) — `amount`, `stage`.
  - `GET /api/crm/campaign_members?event_id=` (`account_id=`) — existing event
    campaign members with `account_id`, `contact_id`, `status`.
  - `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
    `/api/tradeshows/{show_id}/meeting_interest`.
  - `GET /api/import_batches`, `/{batch_id}/raw_contacts`, `/{batch_id}/suppression`.
  - `GET /api/policies` — controlled enums and qualification notes.
- The API has NO answer endpoints; you must compute everything.

## 1. Output discipline (applies to every task)

- Return ONE JSON object and nothing else. No prose, no markdown fences in the
  final answer file.
- Match `answer_template.json` EXACTLY: same top-level keys, same nested keys,
  same enum spellings. Do not add fields not declared in the template. Some
  templates are literal answer skeletons (build the same shape); some are schema
  descriptors (build the shape they describe).
- Use the EXACT controlled enum values from the template / `/api/policies`.
  Never invent enum values or reasons.
- Currency is integer USD. Counts are integers. Never emit floats for money/counts.
- Apply the stated sort to every list (usually by name/id ascending). Sorting is
  graded — always sort, and remember strings sort lexicographically (e.g.
  `acct_...` sorts before `badge:...`).
- `null` vs empty string: use `null` only where the template/field-type says
  "string or null" (e.g. `existing_account_id`, `invoice_id`, `crm_account_id`).
  Use `""` where it says "empty string allowed" (e.g. missing email/phone).

## 2. Normalization rules (exact)

- **Email**: trim leading/trailing whitespace, then lowercase. Nothing else.
  An email that is blank or only whitespace normalizes to `""` (no contact email).
- **Phone**: strip ALL non-digit characters; keep the remaining digits exactly as
  they appear. KEEP a leading country-code digit if it is present in the source
  (`+1 415 555 0188` -> `14155550188`); do NOT add a country code if the source
  has none (`415-555-0188` -> `4155550188`, `212-555-0166` -> `2125550166`).
  A blank phone normalizes to `""`.
- Because two records of the same person can normalize to different phones
  (one with country code, one without), do NOT use phone as the primary dedup
  key — use normalized email (see dedup).

## 3. Sponsor status classification (post-event reconciliation)

Decide each sponsor account's status by reconciling its ORDER status and its
INVOICE status. Controlled values: `paid_deferred`, `open_invoice`,
`proposal_only`, plus `not_sponsor` (only when the template lists it).

- An order/package is an **active sponsor record** only if its `order_status` is
  `confirmed` or `proposal_sent`. An order with `order_status = canceled` (or
  inactive) is NOT an active sponsor — exclude it from `sponsor_statuses` and
  treat its attendees as `inactive_sponsor_record` (see exclusions).
- For active sponsors:
  - `proposal_only`: order `proposal_sent` and NO invoice yet (set `invoice_id`
    null, `paid_amount` 0, `open_balance` 0, package_amount = order amount).
  - `paid_deferred`: invoice `status = paid_deferred` / fully paid
    (`paid_amount == amount`, `open_balance == 0`).
  - `open_invoice`: invoice `status = open` and not fully paid. Set
    `open_balance = amount - paid_amount`. Report `paid_amount` as paid so far.
- Revenue rollups by status use the package/order `amount` (integer). For
  open invoices, also report the open balance separately
  (`open_invoice_balance` / `unpaid_sponsor_total_usd`).
- "Unpaid"/finance-follow-up sponsors = active sponsors that are NOT fully paid:
  i.e. `open_invoice` AND `proposal_only` accounts. Sum their amounts for the
  unpaid total. (A `paid_deferred` sponsor is fully paid and is NOT followed up.)

## 4. Badge -> lead classification & exclusions (post-event)

Work from the BADGE/lead population for the event (the `badges` endpoint and any
import rows), NOT from the sponsor roster or campaign-member list. Each badge maps
to exactly one classification.

Classify each badge:
1. **Non-business badge** (`non_business_badge`): `badge_type` is `student`,
   `press`, `media`, academic, etc. -> excluded.
2. **Inactive-sponsor attendee** (`inactive_sponsor_record`): the attendee's
   company has a sponsor order that is `canceled`/inactive. This reason takes
   PRECEDENCE over `existing_disqualified` even if the account is also
   disqualified.
3. **Sponsor attendee** (`sponsor_attendee`): the company is an ACTIVE sponsor
   (confirmed or proposal_sent order). These are not new leads. Note a
   proposal-stage sponsor still counts as a sponsor attendee.
4. **Existing disqualified** (`existing_disqualified`): the company maps to a CRM
   account whose `status = disqualified` (and it is not an inactive-sponsor case).
5. **Qualified non-sponsor lead**: a business attendee whose company is none of
   the above. This is the sales-handoff population.

Exclusion-reason precedence (apply top-down): non_business_badge ->
inactive_sponsor_record -> sponsor_attendee -> existing_disqualified.
(`missing_contact` applies in import-hygiene contexts when a row has no usable
contact identity.)

Important: only records that actually appear as badges/leads belong in
`excluded_records`/`badge_decisions`. Do NOT manufacture excluded attendees from
sponsor packages or existing campaign members who have no badge. A sponsor's
existing campaign member with no badge scan is handled in
`campaign_member_actions` as `no_action`, not as an exclusion.

## 5. CRM create / update / no-action decisions

Resolve each lead/contact against existing CRM accounts (match by company
name/domain) and contacts (match by normalized email, then name within account):

- **Account action**: account exists in CRM -> `update_existing`; not found ->
  `create_account`.
- **Contact action**: contact already exists under that account -> `update_existing`;
  otherwise -> `create_contact`. NOTE: an existing account often does NOT contain
  the badge contact (e.g. only an old/opted-out contact exists), so the common
  case is `update_existing` account + `create_contact` contact.
- **Campaign member action**: already a campaign member for the event ->
  `no_action` (or `update_*` if the template models updates); needs creating ->
  `create`/`add_campaign_member`; excluded/non-business badge -> dropped or
  `no_import`.

For combined badge `crm_action` enums (e.g. task family 004), decision tree:
  - non-business badge -> `no_import`
  - account missing -> `create_account_contact_campaign_member`
  - account exists, contact missing -> `create_contact_campaign_member`
  - account+contact exist, already a campaign member -> `no_action`
  - account+contact exist, not yet a member -> `add_campaign_member`

`campaign_member_actions` list:
  - Include existing event campaign members (preserve their current `status` as
    `target_status`, action `no_action`), AND new members derived from qualifying
    badges (action `create`).
  - EXCLUDE non-business/excluded badges entirely (they get no campaign-member row).
  - `target_status`: sponsor accounts -> `attended_sponsor` (if attended) or keep
    existing `registered_sponsor`; non-sponsor qualified leads -> `attended`.
  - `subject_key` format when the schema uses keyed subjects: existing CRM
    contacts use `acct_<id>:cont_<id>`; badge-derived new members use
    `badge:<badge_id>`. (Do NOT invent a snake_cased company-name key unless the
    template's examples actually show that.)

`badge_only_contacts` (normalized contact facts): include every badge that
results in a NEW contact being created — this includes sponsor attendees whose
contact must still be created (e.g. a proposal-stage sponsor's new attendee), not
only the non-sponsor leads. Exclude badges whose contact already exists and
excluded/non-business badges. Provide normalized email and phone per Section 2.

## 6. Opportunities & pipeline totals

- A new lead/handoff opportunity is sized at the event's `lead_opportunity_amount`
  for EACH qualified non-sponsor lead account.
- "lead_pipeline_total" / "open_opportunity_total" = (number of qualified
  non-sponsor lead accounts) x `lead_opportunity_amount`. The corresponding count
  = number of qualified non-sponsor lead accounts. Do NOT confuse this with
  existing CRM opportunity records — when the task says "open"/"lead" opportunity
  for the handoff, it means the prospective opportunities to be opened, computed
  from lead count x the event lead amount.

## 7. Follow-up due dates

- `lead_followup_due_date` = event `end_date` + `followup_days_after_end` days.
- `sponsor_followup_due_date` = event `end_date` + `sponsor_followup_days_after_end`
  days.
- Format `YYYY-MM-DD`. Add calendar days to end_date (not start_date).
- Task counts usually equal the number of accounts in that follow-up group
  (e.g. lead_task_count = number of qualified lead accounts; sponsor finance task
  count = number of unpaid sponsor accounts).

## 8. Import-batch hygiene & dedup (raw contact import)

Process `raw_contacts` for the batch. Every raw row ends in exactly ONE import
action so the action totals sum to the raw row count.

Pipeline order (apply in this sequence):
1. **Normalize** email (trim+lowercase) and phone (digits only) on every row.
2. **Missing-contact check**: a row with no usable contact identity (blank email
   AND no usable phone/identity) -> removal reason `missing_contact`, import
   action `no_import`. (A row missing only phone but with a valid email is still
   usable.)
3. **Dedup** on the normalized-email key. Group rows sharing the same normalized
   email. Pick ONE winner per group:
   - Winner is chosen by SOURCE PRECEDENCE, not by earliest timestamp and not by
     lowest row_id. Authoritative/enriched sources beat self-service web sources
     (observed: `partner_upload` beats `webinar_form`). When precedence ties,
     fall back to a deterministic tiebreak (later/most-complete record), but
     source precedence is the primary rule.
   - Losers -> removal reason `duplicate`, import action `no_import`.
   - The winner carries that winning row's own field values (its company_name,
     email, phone, source_name, captured_at, row_id).
   - `duplicate_keys` entries: `key` is prefixed when the template shows a prefix
     (e.g. `email:<normalized_email>`). Record `winner_row_id` and
     `removed_row_ids`.
4. **Suppression**: match each surviving row against the batch `suppression` list
   (by email and/or normalized phone) and against CRM contacts flagged
   `opted_out`. Match -> removal reason `suppressed`, import action `suppress`.
5. **Surviving importable rows**: decide `create_account` vs `update_existing`
   against CRM accounts (Section 5).

`clean_contacts` contains ONLY the surviving importable rows
(`create_account`/`update_existing`). Do NOT put duplicate-losers, suppressed, or
missing-contact rows into `clean_contacts`; they live only in `removed_rows`.

`import_action_totals` count EVERY raw row by action:
  - `create_account`, `update_existing`: surviving importable rows.
  - `suppress`: suppressed rows.
  - `no_import`: missing-contact rows PLUS all duplicate-loser rows. (Duplicate
    losers count as `no_import`, not as their own category.)
  Totals must sum to the raw row count.

`campaign_member_import_count` = number of surviving importable clean contacts
(those that will be added as members of the batch campaign).

## 9. Trade-show exhibitor prospecting / qualification

- **Qualified** = exhibitor that MANUFACTURES or OEM-builds a target platform
  covered by the campaign's prospecting policy (read the description for verbs
  like "manufactures", "builds", "OEM"). Classify platforms from the description
  using the policy's controlled platform enums (e.g. `AUV`, `ROV`,
  `Underwater Camera`); list platforms in the enum order given by the template.
- **Excluded near-misses** = adjacent companies that do not build the target
  platform: distributors/resellers (`distributor_only`), pure service/analytics
  with no hardware (`service_only`), sensor-only vendors
  (`sensor_vendor_only`/`sensor_only`), research/academic (`research_only`),
  off-target (`not_target_market`). Use the EXACT reason enum from THAT task's
  template (the spellings differ between tasks, e.g. `sensor_vendor_only` vs
  `sensor_only`). Excluded -> `crm_action: no_import`.
- **CRM overlap**: exhibitor with a non-null `crm_account_id` -> `update_existing`
  and counts toward existing CRM overlap; null -> `create_account`.
- **Ranking** (when requested, e.g. task family 005): sort qualified leads by
  (1) `requested_demo` desc (true first), (2) `interest_score` desc,
  (3) broader platform coverage (more platforms first), (4) `company_name` asc.
  Assign 1-based contiguous `rank`.
- **Priority tiers & sizing** (per the prompt; values can change per task):
  typically A = demo + score >= 90, B = demo + score >= 80, C = all other
  qualified. Default sizing A=120000, B=90000, C=50000 — but ALWAYS use the
  amounts the prompt states. `total_estimated_opportunity_usd` = sum of tier
  amounts over qualified leads.
- Meeting-interest data joins to exhibitors by `company_name`; treat a missing
  meeting-interest record as `requested_demo=false` / no score for tier purposes.

## 10. Common pitfalls / mistakes to avoid (distilled from reflection)

- **Do not invent excluded attendees.** Build the badge/lead population only from
  actual badge scans (and import rows). Sponsor packages and existing campaign
  members are NOT badges; do not add their contacts to `excluded_records` unless
  they actually appear as a badge scan.
- **inactive_sponsor_record beats existing_disqualified.** A canceled sponsor
  order makes the attendee `inactive_sponsor_record` even when the CRM account is
  also `disqualified`. Apply the exclusion-reason precedence ladder.
- **Canceled sponsor orders are not sponsors.** Exclude them from
  `sponsor_statuses` entirely; only `confirmed`/`proposal_sent` orders are active
  sponsor records.
- **Dedup winner is by source precedence, not earliest timestamp or lowest
  row_id.** Authoritative/partner sources beat self-service web forms. Choosing
  the chronologically-first or numerically-first row is a frequent error.
- **Duplicate-loser rows count as `no_import` in import action totals** (and
  appear in removed_rows with reason `duplicate`). They do not get their own
  totals bucket, and they never appear in `clean_contacts`.
- **`clean_contacts` is only importable survivors** — never include suppressed,
  no_import, or duplicate-loser rows there.
- **Duplicate-key string format matters** — prefix it (`email:<value>`) when the
  template's example shows a prefix; emit the bare value only when that's what the
  template shows.
- **"Open"/"lead" opportunity totals are derived from lead count x the event
  lead_opportunity_amount**, not from existing CRM open-stage opportunity records.
  Returning 0 because no CRM opportunity row exists is wrong.
- **An existing account usually still needs `create_contact`.** Don't assume the
  badge person is already a CRM contact just because the account exists; check
  contacts and default to `create_contact` when the specific person is absent.
- **A sponsor attendee can still require `create_contact_campaign_member`** (and
  belongs in `badge_only_contacts`) when its account exists but the attendee
  contact does not. Don't downgrade it to a bare `add_campaign_member`, and don't
  omit it from badge_only_contacts.
- **subject_key / member keys follow the template's keying scheme**
  (`acct_<id>:cont_<id>` for existing contacts, `badge:<badge_id>` for new
  badge-derived members) — not a snake_cased company name. Then sort by the key
  string ascending (so `acct_*` precedes `badge:*`).
- **Excluded/non-business badges drop out of campaign_member_actions** — they are
  not members.
- **Follow-up dates add days to end_date**, and lead vs sponsor use different
  `*_days_after_end` fields. Don't swap them or use start_date.
- **Use each task's own enum spellings.** Reason/status enums differ slightly
  across tasks (`sensor_vendor_only` vs `sensor_only`, presence of `not_sponsor`,
  etc.). Read the template/`/api/policies` every time.
- **Phone normalization keeps source country-code digits and strips everything
  else; it never adds or removes a country code.** Email normalization is just
  trim + lowercase.

## 11. Suggested solving procedure

1. Read the prompt and `answer_template.json`; list the exact top-level keys,
   nested keys, enums, and sort orders required.
2. `GET /health` to confirm the base URL; `GET /api/policies` for enums.
3. Fetch all data the task references (event, orders, badges, invoices, accounts,
   contacts, opportunities, campaign_members, exhibitors, meeting_interest,
   raw_contacts, suppression) for the relevant id.
4. Apply the relevant SOP section(s) above to compute each field.
5. Normalize emails/phones; classify statuses/leads/exclusions with the
   precedence ladders; compute totals so per-row/per-account categories reconcile
   (every input row maps to exactly one bucket).
6. Sort every list as specified; verify enum spellings; verify integer types.
7. Emit one JSON object matching the template exactly — no extra fields, no prose.
