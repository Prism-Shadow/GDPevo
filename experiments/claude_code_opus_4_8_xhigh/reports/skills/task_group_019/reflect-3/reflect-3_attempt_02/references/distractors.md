# Distractor catalog

These datasets plant misleading records. Each row below is a trap and the rule
that defeats it. When a coded/structured field disagrees with free-text, the
coded field and the dates win.

| Trap | Looks like | Correct handling |
|---|---|---|
| Stale bulk listing | A list endpoint returns "everything" | It may be **row-capped**, silently dropping later target ids. Query per target id and confirm every target + related row is present. |
| "active" but expired coverage | Insurance `status` = active | Compare `expiration_date` to the **review date**; past expiry ⇒ expired, regardless of status. |
| Cancelled/old bond still listed | A bond row exists for the app | Only a bond that is active, effective by the review date, and not cancelled by it is *current*. Superseded `-OLD` rows are history. |
| Inspection `result`/`notes` | "No adverse field finding" vs "incomplete signage" | Ignore `result` and `notes`; the coded `finding_code` is authoritative (and only some finding codes map to a deficiency). |
| Resolved / dismissed violations | A violation row exists | Only `status` = open counts. Resolved/dismissed severity is irrelevant. |
| Verified "registry corrected" letter | Correspondence says the issue was fixed | Correspondence does **not** clear a records-derived deficiency; it only feeds the stale/unverified-correspondence summary. |
| `verified_by_agency` vs notes | Note says "Verified by specialist" but field = 0 (or field = 1 but note says "no agency confirmation") | Treat `verified_by_agency` as the primary signal; the free-text note is often the opposite on purpose. |
| Same address, different license | Violations at the target's address under another `license_no` | Match on **exact license_no** (stable identifier), not address. Different-license rows are another facility. |
| Predecessor / `successor_to` | An old license id linked to the target | A successor match is **uncertain** confidence, not exact. |
| `-LATE` / late-suffixed ids | A violation id ending in a late marker | Explicit distractor per the renewal rule — drop it. |
| Post-boundary violations | A recent violation after the release boundary | Excluded from matching; list it in the post-boundary-excluded summary. |
| Inactive/expired settlement controls | A settlement lists controls | Location-specific controls come only from settlements whose `controls_json.active` is true. |
| Same-premises history | The same-premises settlement is inactive | The same-premises **basis still applies** if any such settlement exists (history matters) — but its controls only count if that settlement is active. |
| `-DIS-####` "distractor" rows | Extra records mixed into a target's related rows | Evaluate them by the same rules (verified? open? current?); they are usually noise but a `-DIS` row genuinely related to a target still follows the normal rule. |
| Cross-task id prefixes | Records under a different task's id prefix at a shared address | Belong to another task; never fold them into this target's findings. |

General rule of thumb: **structured coded fields + dates are truth; prose is
decoration.** Compute findings from the records, then map them onto the exact
enum vocabulary of the current `answer_template.json`.
