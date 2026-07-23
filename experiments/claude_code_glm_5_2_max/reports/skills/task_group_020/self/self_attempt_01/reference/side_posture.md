# Side Posture — Direction of "Out of Policy"

The playbook encodes each side's preferred and fallback positions. These are the
**directional** defaults that tell you which way a draft term must move to be
in-policy for your client. Always read the actual playbook/policy thresholds from
the workbench — do not assume specific numbers; the postures below are direction
only.

## Buyer-side posture (protect the buyer)

- **Indemnity cap:** higher is better — toward the full deal value. Basket:
  lower / tipping-basket preferred (easier to recover).
- **Survival:** longer is better, with longer periods for fundamental reps.
- **Materiality scrape:** full (breach and damages) preferred.
- **Escrow / holdback:** required, sized to indemnity exposure and unresolved
  findings, released on survival expiration.
- **Knowledge qualifiers:** fewer / qualifier-light reps preferred.
- **Working capital:** dollar-for-dollar outside a collar.
- **Consents / regulatory:** require all material consents and HSR clearance as
  closing conditions. Hell-or-high-water is a buyer burden — disfavored unless
  the deal requires it for certainty.
- **Reverse termination fee / financing:** buyer prefers financing flexibility
  and a lower RTF.

A draft that falls short of these (lower cap, shorter survival, no escrow,
missing consents) is `draft_below_playbook` or `missing_required_term` for the
buyer.

## Seller-side posture (protect the seller)

- **Indemnity cap:** lower, capped well below the full deal value. Basket:
  higher / true deductible.
- **Survival:** shorter is better.
- **Escrow:** minimize or eliminate; if required, small and short release.
- **Restrictive covenants:** limit the scope and duration of non-compete /
  non-solicit on the seller's personnel.
- **Tax allocation (carveout):** seller-favorable Section 1060 allocation;
  transfer-tax split favoring the seller.
- **Governing law / forum:** the seller's preferred jurisdiction (commonly
  Delaware).
- **Transition services (carveout):** cap scope, duration, and fees; at-cost or
  cost-plus, not open-ended.
- **Outside date / closing deadline:** seller wants closing-deadline protection
  and extension rights.
- **Reverse break fee / financing:** seller wants financing certainty and an RTF
  that covers reliance/out-of-pocket; no open-ended financing out.

A draft that exceeds these (longer survival, higher cap, uncapped transition
services, open-ended financing out) is `draft_exceeds_playbook` for the seller; a
draft silent on a seller-protective term the seller needs is
`missing_required_term`.

## Direction of out-of-policy classification

- `draft_exceeds_playbook` — the draft metric has moved past the playbook bound
  **against your client**.
- `draft_below_playbook` — the draft metric is short of the playbook bound
  **against your client**.

The same draft term can be `draft_exceeds_playbook` for one side and
`draft_below_playbook` for the other (e.g., a long survival period exceeds the
seller's playbook max but falls below the buyer's preferred min). Always classify
from the side the prompt assigns you, using that side's playbook (e.g.,
`PB_BUYER_A` for buyer-side, `PB_SELLER_A` for seller-side).
