# train_004 Notes / train_004 说明

## English

This hidden note documents construction for `train_004`, assigned to `task-builder-train-004` in `task_group_020`. The source scenario is `SCN_020_ma_transaction_contract_review_and_negotiation`, with scenario examples `E001`, `E002`, and `E003` informing the recurring M&A review workflows. The task brief requires a seller-side carveout APA transition review for `PRJ_ORION`, with output sections `transition_issues`, `required_redlines`, and `operational_risk`.

The solver-visible input consists only of `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt directs solvers to the shared M&A deal workbench at `<TASK_ENV_BASE_URL>` and to the read-only APIs/SQL service. It does not copy the SQLite database, generator, manifests, or environment source. The template declares stable issue IDs, redline IDs, controlled enums, integer-dollar precision, and list ordering rules.

The construction evidence comes from the generated environment data for `PRJ_ORION`: the deal record, current draft terms, `PB_SELLER_A` transition-services rule, employees, consents, material contracts, regulatory row, risk estimates, documents, diligence findings, and deal notes. `PRJ_ORION` is a seller-side carveout asset purchase agreement for Orion GridWorks Inc. selling the Orion Grid Services Division to Palisade Infrastructure Partners. The transaction has a headline value of `$198,000,000`, upfront cash of `$178,000,000`, milestone value of `$20,000,000`, and HSR is required.

Key environment facts used in the standard answer:

- `TERM_PRJ_ORION_01`: buyer asks for 15 months of billing, dispatch, and HR transition services at cost.
- `TERM_PRJ_ORION_02`: at-cost TSA fees exclude `$3,800,000` of stranded overhead.
- `PB_SELLER_A` transition-services rule: preferred maximum 6 months; fallback 9 months only if monthly fees cover stranded cost.
- `TERM_PRJ_ORION_03`: buyer may terminate if any top five utility customer consent is missing.
- Required closing consents in `consents`: `CNS_PRJ_ORION_01` and `CNS_PRJ_ORION_03`, totaling `$11,740,000` amount at risk.
- Material consent-bearing contracts: `MAT_PRJ_ORION_01` and `MAT_PRJ_ORION_03`; top customer annual revenue at risk is `$16,830,000`.
- `TERM_PRJ_ORION_04` and `EMP_PRJ_ORION_03`: buyer may cherry-pick field and operations employees; 124 employees; accrued PTO exposure is `$1,240,000`; service credit is required.
- `RSK_PRJ_ORION_03`: transition disruption exposure high is `$3,563,999`.
- Draft silence is treated as an issue for IP/domain transition, Section 1060 allocation, transfer taxes, outside date/regulatory extension, and governing law/forum because these are affirmative carveout APA protections in the task brief and source scenario lineage.

The standard answer uses eight issue IDs: `CUSTOMER_CONSENT_TERMINATION_RIGHT`, `FIELD_EMPLOYEE_CONTINUITY_PTO`, `GOVERNING_LAW_FORUM_FIX`, `IP_DOMAIN_TRANSITION_MISSING`, `OUTSIDE_DATE_EXTENSION_MISSING`, `SECTION_1060_ALLOCATION_MISSING`, `TRANSFER_TAX_SPLIT_MISSING`, and `TSA_SCOPE_DURATION_FEES`. The redlines mirror those issues using eight stable redline IDs. The answer intentionally distinguishes business outcomes: separation cost recovery, IP/domain continuity, customer consent closing certainty, workforce continuity, tax reporting consistency, deadline/regulatory protection, law/forum predictability, and overall operational-risk posture.

Evaluation uses `eval/evaluate.py` and `eval/eval.sh`. It defines eight deterministic all-or-nothing scoring points with raw weights `[2, 2, 3, 2, 2, 1, 1, 3]`:

1. Correct issue and redline identifier sets.
2. Correct trademark license and domain redirect protections.
3. Correct TSA duration, scope, fee model, and stranded-cost treatment.
4. Correct Section 1060 and transfer-tax allocation.
5. Correct employee continuity and accrued PTO treatment.
6. Correct outside date and seller regulatory extension.
7. Correct Delaware governing law/forum fix.
8. Correct operational risk summary, priority order, and quantified exposures.

Each point passes only when all required normalized fields for that business result match exactly. Numeric checks are integer-dollar or integer-day/month checks. Set checks normalize order where the business result is a set; `operational_risk.priority_order` is checked as an exact ordered list. The evaluator does not score free-form prose or evidence wording.

Likely solver pitfalls include using a similarly named distractor deal, relying only on draft terms and missing silent required provisions, using the 12-month TSA convention from the source playbook instead of the generated `PB_SELLER_A` 6/9-month seller rule for `PRJ_ORION`, treating all top-five consents as automatic termination rights, omitting PTO liability, missing HSR-driven deadline protection, or failing to quantify the operational-risk summary.

For transfer design, this train task teaches that seller-side carveout transition reviews require cross-record synthesis rather than single-term extraction. Solvers should learn to compare draft terms to the active playbook, treat missing carveout mechanics as deviations, carry stable IDs into JSON output, compute exposure aggregates from consent and employee records, and separate must-have protections from lower-risk cleanup terms.

Construction record: author `task-builder-train-004`; created `2026-07-18`; updated `2026-07-18`; major changes: created the complete `train_tasks/004` artifact set, standard answer, and deterministic evaluator.

## 中文

本隐藏说明记录 `task_group_020` 中 `train_004` 的构建过程，负责人是 `task-builder-train-004`。来源场景是 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例 `E001`、`E002`、`E003` 提供了并购交易文件审阅、谈判和升级的业务模式。本任务简报要求针对 `PRJ_ORION` 构建卖方视角的剥离式资产购买协议过渡条款审阅，输出为 `transition_issues`、`required_redlines` 和 `operational_risk`。

解题者可见输入只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示要求使用 `<TASK_ENV_BASE_URL>` 上的共享并购工作台，以及只读 API/SQL 服务。任务目录没有复制 SQLite 数据库、生成器、manifest 或环境源码。模板定义了稳定 issue ID、redline ID、受控枚举、美元整数精度和列表排序规则。

构建依据来自环境中 `PRJ_ORION` 的生成数据：交易记录、当前草案条款、`PB_SELLER_A` 过渡服务规则、员工记录、同意事项、重大合同、监管记录、风险估算、文件记录、尽调发现和交易笔记。`PRJ_ORION` 是 Orion GridWorks Inc. 作为卖方，将 Orion Grid Services Division 出售给 Palisade Infrastructure Partners 的剥离式资产购买协议。交易 headline value 为 `$198,000,000`，upfront cash 为 `$178,000,000`，milestone value 为 `$20,000,000`，且需要 HSR。

标准答案使用的关键事实包括：买方要求 15 个月 billing、dispatch、HR 过渡服务且按成本收费；费用排除 `$3,800,000` 滞留 overhead；`PB_SELLER_A` 要求过渡服务首选不超过 6 个月，只有在费用覆盖滞留成本时才可退让到 9 个月；买方要求任何前五大公用事业客户同意未取得即可终止；真正 required for closing 的同意是 `CNS_PRJ_ORION_01` 和 `CNS_PRJ_ORION_03`，风险金额合计 `$11,740,000`；重大需同意合同是 `MAT_PRJ_ORION_01` 和 `MAT_PRJ_ORION_03`；field and operations 员工共 124 人，PTO 风险为 `$1,240,000`；过渡中断高端风险为 `$3,563,999`。对于 IP/domain、Section 1060、transfer tax、outside date、governing law/forum，草案没有明确条款，因此按任务简报和来源场景的卖方剥离交易惯例视为缺失必备条款。

标准答案包含八个 issue ID：`CUSTOMER_CONSENT_TERMINATION_RIGHT`、`FIELD_EMPLOYEE_CONTINUITY_PTO`、`GOVERNING_LAW_FORUM_FIX`、`IP_DOMAIN_TRANSITION_MISSING`、`OUTSIDE_DATE_EXTENSION_MISSING`、`SECTION_1060_ALLOCATION_MISSING`、`TRANSFER_TAX_SPLIT_MISSING`、`TSA_SCOPE_DURATION_FEES`。redline ID 与这些 issue 一一对应。答案覆盖的业务结果包括卖方分离成本回收、IP/domain 连续性、客户同意与交割确定性、员工连续性、税务申报一致性、监管期限保护、法律/管辖地确定性和整体运营风险判断。

评估入口为 `eval/eval.sh`，核心逻辑在 `eval/evaluate.py`。评估包含八个确定性的全有或全无评分点，原始权重为 `[2, 2, 3, 2, 2, 1, 1, 3]`：issue/redline 集合、商标许可与域名跳转、TSA 范围和费用、Section 1060 与 transfer tax、员工连续性和 PTO、outside date 与卖方监管延期、Delaware 法律和论坛、运营风险摘要。每个评分点只有在该业务结果的全部规范化字段完全匹配时才通过；数值按整数美元、整数天数或月数检查；集合字段会按集合比较，优先级顺序字段必须完全按顺序匹配。

常见错误包括使用相似项目的干扰数据，只看 draft terms 而漏掉草案沉默导致的必备条款缺失，误用来源 playbook 中 12 个月 TSA 规则而不是 `PRJ_ORION` 环境里的 `PB_SELLER_A` 6/9 个月规则，把前五大客户同意全部作为自动终止权，漏算 PTO liability，忽略 HSR 导致的 deadline 保护，或没有汇总量化运营风险。

迁移设计方面，本训练任务让解题者学习卖方剥离交易过渡审阅需要跨记录综合，而不是单条款摘录。可迁移能力包括：根据活跃 playbook 审阅当前草案；将缺失的剥离机制作为偏离项；在 JSON 中使用稳定 ID；从同意事项和员工记录计算风险金额；区分必须修改的保护条款与较低风险的清理项。

构建记录：作者 `task-builder-train-004`；创建日期 `2026-07-18`；更新日期 `2026-07-18`；主要变更为创建完整的 `train_tasks/004` 文件集、标准答案和确定性评估器。
