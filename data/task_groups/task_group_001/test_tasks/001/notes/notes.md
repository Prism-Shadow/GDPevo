# test_001 Notes
## English

This task is `test_001` for `task_group_001`, derived from source scenario `SCN_001_crm_marketing_lead_capture` and source examples `E001`, `E002`, and `E003`. Its design brief is the event-to-CRM operation family: audit `Predictive Ops Summit 2027` (`event_id: predictive_ops_2027`) after the event and produce a finance and sales handoff from the shared HarborCRM environment.

Solver-visible inputs are only `input/prompt.txt`, `input/payloads/answer_template.json`, and the public HarborCRM API. The relevant public data comes from event metadata, sponsor packages, event badges, finance invoices, CRM accounts, CRM contacts, opportunities, campaign members, and policies. The solver should not inspect generated data files or these notes.

The task fits the group because it combines the same business objects as the train event tasks: sponsor packages, invoices, badge scans, CRM state, campaign membership, lead opportunity sizing, and follow-up dates. It is not a tutorial version of a train task. The Predictive Ops event introduces task-specific exploration through a split Lumina Manufacturing invoice, an inactive Keystone AGV sponsor package, a pre-existing Riverbend lead with stale contact data, and a stale campaign-member mismatch for Fathom Ops.

Material map:

- `/api/events/predictive_ops_2027` supplies the event end date, lead opportunity amount, and follow-up offsets.
- `/api/events/predictive_ops_2027/sponsor_packages` and `/orders` identify Fathom Ops, Lumina Manufacturing, OrbitRail Systems, and the inactive Keystone AGV package.
- `/api/finance/invoices?event_id=predictive_ops_2027` supplies the paid/deferred Fathom invoice, the split Lumina paid/open invoices, and the absence of an OrbitRail delivered invoice.
- `/api/events/predictive_ops_2027/badges` supplies sponsor attendees and non-sponsor attendees.
- `/api/crm/accounts` and `/api/crm/contacts` distinguish existing accounts, disqualified accounts, stale contact data, and new accounts.
- `/api/crm/campaign_members?event_id=predictive_ops_2027` shows Riverbend Chemical already registered and a stale Fathom Ops campaign-member mismatch using `cont_sofia_meyer`.
- `/api/policies` records the public conventions for sponsor status, follow-up date offsets, contact normalization, and lead amount field names.

Solution basis:

- Active sponsors are Fathom Ops (`paid_deferred`), Lumina Manufacturing (`open_invoice` because one split invoice remains open), and OrbitRail Systems (`proposal_only`). Keystone AGV is a no-show sponsor package and is not active.
- Sponsor finance totals are invoice/proposal segment totals: paid/deferred invoiced value is `72000 + 26000 = 98000`, open delivered invoice value is `16000`, proposal-only value is `22000`, and open balance is `16000`.
- Qualified non-sponsor lead accounts are Cascadia Steel and Riverbend Chemical. Each uses the event lead opportunity amount `51000`, so `lead_pipeline_total` is `102000` and `average_deal_size` is `51000.00`.
- Riverbend Chemical maps to existing account `acct_riverbend_chem` and contact `cont_hana_park`; the badge has the fresher email `hana.park@riverbendchem.example`, so the contact and campaign member should be updated rather than duplicated. Cascadia Steel is a new account/contact/campaign-member create.
- Excluded records are sponsor badge attendees Cole Ivers and Nadia Volk, inactive sponsor package contact Anika Shah, disqualified Old Quarry Logistics contact Rhea Moon, non-business press attendee Dev Singh, and the stale Fathom Ops campaign-member mismatch for Sofia Meyer.
- Follow-up dates are event end date `2027-03-24` plus the event offsets: lead follow-up `2027-04-01` and sponsor finance follow-up `2027-03-28`. Lead task count is `2`; sponsor finance task count is `2` for Lumina Manufacturing and OrbitRail Systems.

Evaluation uses seven exact-match scoring points with raw weights:

- SP001, weight 3: exact active sponsor status set, including Lumina's split-invoice status and invoice IDs.
- SP002, weight 2: exact sponsor revenue totals by paid/deferred, open invoice, proposal-only, and open balance.
- SP003, weight 3: exact qualified non-sponsor lead account set and CRM actions.
- SP004, weight 2: exact exclusion set, including sponsor attendees, inactive sponsor record, disqualified badge, non-business badge, and stale CRM duplicate.
- SP005, weight 2: exact lead pipeline total and average deal size.
- SP006, weight 3: exact follow-up due dates, counts, and sponsor finance account set.
- SP007, weight 1: exact CRM create/update counts.

Transfer design:

- `train_001` anchors sponsor/attendee separation, sponsor finance status reconstruction from packages plus invoices, non-sponsor lead inclusion, CRM action counts, and due-date offsets.
- `train_004` anchors event badge classification, campaign member create/update decisions, sponsor attendee exclusion, and how existing CRM state affects handoff actions.
- The high-value transfer-dependent points are SP001, SP002, SP003, SP004, and SP006. SP005 and SP007 require more task-local exploration because the split invoice, stale contact/campaign-member state, and lead count are specific to this event.
- The prompt exposes the public endpoints and output schema but does not restate the complete step-by-step operating method. Solvers must infer the reconciliation pattern from the train tasks and apply it to the Predictive Ops records.

Likely model pitfalls include counting Lumina's full package only as open invoice revenue, missing the paid/deferred part of the split invoice, including Keystone AGV as an active sponsor, treating Riverbend as a new lead because the badge email differs from stale CRM, counting sponsor attendees as sales leads, missing the stale Fathom campaign-member mismatch, or anchoring follow-up dates to the audit date instead of the event end date.
