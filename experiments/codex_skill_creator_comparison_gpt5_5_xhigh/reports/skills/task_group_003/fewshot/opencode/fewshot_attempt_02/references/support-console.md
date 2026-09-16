# Support Console Reference

## Lookup helpers
- Use the exact ID from the payload first.
- If the prompt gives a name or approximate reference, use `/api/search` before guessing.
- Favor the record that matches the task ID over broader search hits.

## Task families

### Ticket batch
- Use the ticket IDs from the CSV as the starting point.
- Pull the ticket, then check diagnostics, troubleshooting, outages, and the account record.
- Treat outage-backed tickets as waiting on service recovery rather than local repair.
- Treat successful troubleshooting or clear diagnostics/remediation as resolved.
- Treat invalid accounts, auth failures, or ineligible accounts as failed.
- Route physical faults, capacity issues, or line work to the escalation team named by the evidence.

### Mobile case queues
- Use the case record to get the customer, line, and device IDs.
- Inspect the line, customer, device, bill, and plan records before choosing an action.
- Check `status`, `suspension_reason`, `roaming_enabled`, and `data_used_gb` on the line.
- Check `mobile_data_enabled`, `data_saver_mode`, `vpn_connected`, `phone_roaming_enabled`, `messaging_permissions`, `network_mode_preference`, `sim_status`, and `mmsc_url_present` on the device.
- If the issue is suspended service or overdue payment, favor billing recovery over self-service.
- If the issue is MMS or photo messaging, inspect storage permission and related messaging flags first.
- If the issue is abroad roaming, roaming controls usually matter more than device resets.
- If the issue is slow data, check data saver, VPN, network mode, and usage limit before escalating.

### Queue-quality review
- Use the same ticket lookup flow, but only populate the fields the template asks for.
- Preserve the template's blocker enum exactly; do not paraphrase it.
- Keep diagnostics-required aligned with whether a diagnostic record or troubleshooting run is needed to support the decision.

### Enterprise response packages
- Resolve the incident with the incident ID, account name, or client name from the complaint.
- Use export runs to identify the failed window and the number of failed days.
- Use the incident record for severity and owner assignments.
- Use messages and SLA records for root-cause wording, alert-route clues, and credit percent.
- Failure window: first failed export date through last failed export date.
- Backfill days: number of failed export days that need replay.
- Follow naming constraints from the prompt exactly for channel, evidence folder, and report title.
- Order share permissions exactly as the requirements list.

## Output discipline
- Keep the response schema exact.
- Preserve array order from the payload.
- Use JSON numbers for numeric fields, not strings.
- If the template asks for a percentage, emit the integer percent value from the evidence or SLA record.
- Use concise root-cause labels. Prefer the shortest category that still reflects the evidence.
- Do not lean on the client narrative when the console record gives a more specific answer.
