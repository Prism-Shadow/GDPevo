# test_002 Notes

## English

This task creates a June 2026 month-end AP supplier release package using ProcureOps invoices, payments, receipts, POs, and supplier records. The solver-facing prompt and payloads are English-only and do not reveal scoring weights or SOP.

Train anchors: `train_003` teaches AP invoice/payment reconciliation, supplier balances, program totals, and release/hold queues. `train_005` teaches receipt scoping, excluding same-PO receipts that are not the invoice-linked receipt, and treating local request notes as supporting context rather than authority.

Gold basis: only `AP-HEXEL-3309` releases. `AP-00007` has a matched receipt but blocked payment, so it stays held. `AP-00008` and `AP-00038` have scheduled payments but no receipt as of `2026-06-30`. `AP-00004` references `RCV-00003`, but that receipt is dated `2026-07-03` and is in inspection hold, so it is excluded by cutoff. Release total is `28909.24`; hold and exception payment totals are `159239.67`.

Scoring uses eight exact-match points with weights `[3, 3, 2, 2, 3, 2, 2, 1]`: package identity and targets; invoice supplier/program/PO/AP fields; receipt cutoff and quantities; payment linkage and bank actions; release/hold decisions, queues, and totals; supplier summary; program summary; payment buckets and source precedence.

## 中文

本任务要求基于 ProcureOps 的发票、付款、收货、采购订单和供应商记录，生成 2026 年 6 月月结 AP 供应商释放包。求解者可见的 prompt 和 payload 均为英文，不暴露评分权重或 SOP。

训练锚点：`train_003` 对应 AP 发票/付款核对、供应商汇总、项目汇总和 release/hold 队列；`train_005` 对应 receipt 范围判定、排除不属于当前发票的同 PO receipt，以及把本地请求备注作为辅助信息而非权威来源。

标准答案依据：只有 `AP-HEXEL-3309` 可以释放。`AP-00007` 有匹配收货但付款为 blocked，因此继续 hold。`AP-00008` 和 `AP-00038` 有计划付款但截至 `2026-06-30` 没有收货。`AP-00004` 指向的 `RCV-00003` 日期为 `2026-07-03` 且处于 inspection hold，因此被 cutoff 排除。释放总额为 `28909.24`；hold 总额和异常付款总额均为 `159239.67`。

评估使用 8 个 exact-match 评分点，权重为 `[3, 3, 2, 2, 3, 2, 2, 1]`：包标识与目标发票、发票供应商/项目/PO/AP 字段、receipt cutoff 与数量、payment 关联和银行动作、release/hold 决策及队列和总额、供应商汇总、项目汇总、payment 分桶和来源优先级。
