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

## 中文

本任务要求求解器为 `Q-TR-LD-5521` 制作报价修订和物流方案对比。客户是 `CUST-GHL`，产品是 `LD-REAGENT-44`，确认数量为 `1000`，报价日期为 `2026-06-01`。

预期事实：
- 内部目录阶梯价：`900-1199`，单价 `76.00` 美元，交期 `14` 天，保质期 `18` 个月。
- EXW 总价：`76000.00` 美元。
- 运费 `FR-LD-AIR`：方式 `AIR`，运费 `21400.00`，运输时间 `3-5`，有效期至 `2026-06-21`，风险 `LOW`，总价 `97400.00`。
- 运费 `FR-LD-SEA`：方式 `SEA`，运费 `5200.00`，运输时间 `26-31`，有效期至 `2026-06-28`，风险 `LOW`，总价 `81200.00`。
- 运费 `FR-LD-ROAD`：方式 `ROAD`，运费 `4800.00`，运输时间 `10-14`，有效期至 `2026-05-25`，在报价日期已经过期/无效，海关或边境风险 `HIGH`，总价 `80800.00`。
- 推荐运输方式：`SEA`。
- 需要重新确认运费：`true`。
- 付款条款：`NET_30_AFTER_PO`。

公路报价虽然比海运便宜，但它在报价日期之前已经过期，并且有高海关/边境风险，因此不能作为推荐方案。
