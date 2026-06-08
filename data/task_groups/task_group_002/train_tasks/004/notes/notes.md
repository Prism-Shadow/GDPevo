# train_004 Notes

## English

This task asks the solver to prepare a quote revision and logistics comparison for `Q-TR-LD-5521`, customer `CUST-GHL`, product `LD-REAGENT-44`, confirmed quantity `1000`, quote date `2026-06-01`.

Expected facts:
- Internal catalog tier: `900-1199`, unit price `76.00` USD, lead time `14` days, shelf life `18` months.
- EXW total: `76000.00` USD.
- Freight `FR-LD-AIR`: mode `AIR`, freight `21400.00`, transit `3-5`, valid until `2026-06-21`, risk `LOW`, grand total `97400.00`.
- Freight `FR-LD-SEA`: mode `SEA`, freight `5200.00`, transit `26-31`, valid until `2026-06-28`, risk `LOW`, grand total `81200.00`.
- Freight `FR-LD-ROAD`: mode `ROAD`, freight `4800.00`, transit `10-14`, valid until `2026-05-25`, stale/invalid on quote date, customs or border risk `HIGH`, grand total `80800.00`.
- Recommended mode: `SEA`.
- Freight reconfirmation required: `true`.
- Payment terms: `NET_30_AFTER_PO`.

The road quote is cheaper than sea, but it is expired before the quote date and carries high customs/border risk, so it must not drive the recommendation.

