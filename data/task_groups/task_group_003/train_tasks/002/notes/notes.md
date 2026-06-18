# train_002 Notes

## English

Data lineage: This task is derived from `SCN_003_crm_service_ticket_resolution`, especially source example `E002`. The visible queue is `input/payloads/case_queue.json`; the support-console API provides customer, line, bill, plan, and device records.

Task definition: The solver acts as a contact-center lead and chooses the next support operation plus any follow-up operation for five mobile support cases. The output is controlled by enums to avoid free-form action wording.

Scenario fit: The task models CRM technical support triage where the agent must identify the right layer: SIM, billing suspension, roaming, app permissions, or VPN.

Material map: `/api/cases/<id>` maps cases to customer, line, and device IDs. `/api/lines/<id>`, `/api/devices/<id>`, `/api/bills?customer_id=...`, and `/api/plans/<id>` contain the evidence for action selection.

Solution and evaluation basis: The correct actions are `RESEAT_SIM`, `SEND_PAYMENT_REQUEST` plus `RESUME_LINE_REBOOT`, `TOGGLE_ROAMING`, `GRANT_MESSAGING_PERMISSION` for storage, and `DISCONNECT_VPN`. There are 8 exact-match scoring points.

Transfer design: As a train task, it exposes the distinction between phone-state fixes, billing recovery, and transfer/carrier routes. It reinforces that mobile-data and MMS issues depend on lower-layer connectivity and device state.
