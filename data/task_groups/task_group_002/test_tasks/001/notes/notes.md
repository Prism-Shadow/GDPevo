# test_001 construction notes

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

## 中文

- 任务类型：带物流比较的报价修订。
- 报价编号：`Q-TE-MAT-7791`；客户：`CUST-MWA`；报价日期：`2026-06-01`。
- 产品：`MAT-EMERG-C`；确认数量：`640`。
- 应使用内部目录中 500-799 件数量档位：单价 `332.00`，交期 `28` 天，保质期 `30` 个月。
- EXW 总额：`640 * 332.00 = 212480.00`。
- 货运选项：
  - `FR-MAT-AIR`：空运，运费 `29750.00`，运输时间 `4-6`，有效期至 `2026-06-20`，低风险，总额 `242230.00`，满足要求的交付窗口。
  - `FR-MAT-SEA`：海运，运费 `7200.00`，运输时间 `32-38`，有效期至 `2026-06-30`，低风险，总额 `219680.00`，不满足要求的交付窗口。
  - `FR-MAT-ROAD`：陆运，运费 `11900.00`，运输时间 `16-23`，有效期至 `2026-06-11`，高边境风险，总额 `224380.00`，满足交付窗口但风险较高。
- 推荐模式是 `AIR`：海运太慢，陆运存在高边境风险。
- 客户及付款政策：老客户 NGO 账户条款为 `NET_30_AFTER_PO`。
- 尽管三条货运报价在报价日均有效，最终下单时仍必须重新确认货运价格。
- 评估包含九个计分点，总权重 22：档位单价/交期/EXW、三条货运总额、路线风险标记、推荐模式、交付窗口可行性、货运有效性提醒、账户条款、来源优先级和日期控制，以及决策控制约定。
