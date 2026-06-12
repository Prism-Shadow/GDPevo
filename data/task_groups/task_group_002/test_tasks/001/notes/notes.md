# test_001 Notes
## English

- Task family: quote revision with logistics comparison.
- Quote ID: `Q-TE-MAT-7791`; customer: `CUST-MWA`; quote date: `2026-06-01`.
- Product: `MAT-EMERG-C`; confirmed quantity: `640`.
- Internal catalog tier for 500-799 units controls the quote: unit price `332.00`, lead time `28` days, shelf life `30` months.
- EXW total: `640 * 332.00 = 212480.00`.
- Freight options:
  - `FR-MAT-AIR`: AIR, freight `29750.00`, transit `4-6`, valid until `2026-06-20`, low risk, grand total `242230.00`, feasible for the requested delivery window.
  - `FR-MAT-SEA`: SEA, freight `7200.00`, transit `32-38`, valid until `2026-06-30`, low risk, grand total `219680.00`, not feasible for the requested delivery window.
  - `FR-MAT-ROAD`: ROAD, freight `11900.00`, transit `16-23`, valid until `2026-06-11`, high border risk, grand total `224380.00`, feasible for the requested delivery window but risk is high.
- Recommended mode is `AIR`: sea is too slow for the requested window, and road has high border risk.
- Customer/payment policy: recurring NGO account terms `NET_30_AFTER_PO`.
- Freight reconfirmation is required at final order even though all three freight quotes are valid on the quote date.
- Evaluation uses nine scoring points with total weight 22: tier price/lead time/EXW, freight totals, risk flags, recommendation, delivery-window feasibility, freight warning, account terms, source precedence/date control, and decision-control conventions.
