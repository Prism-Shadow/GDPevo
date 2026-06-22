# Evolution Modes

本评估对比三种条件。三种都用同一个 task group、同一批 test tasks、同一个模型和同一套 evaluators。它们之间唯一不同的是 **Panofy 训练配置**——上传的材料和训练 instruction。instruction 让 agent **根据这些 train task 进行 evolve**:从它们身上学习、在这一类任务上变得更强。**不导出任何东西**——进化烤进训练好的 agent 里,测试时的调用就是 `predict()`。

每个条件训练 3 个独立 agent(`attempt_01..03`)。

三种条件共用同一套输入/输出契约,写在你 staging 的 `function_definition.md` 训练材料里:

- `FUNC_INPUT` = `{ task_id, prompt, api_base_url, answer_template }`
- `FUNC_OUTPUT` = 一个严格匹配 `answer_template` 的 JSON 对象。

agent 读 `prompt`,对 `api_base_url` 上 prompt 点名的端点发起实时 GET,应用规则,返回答案 JSON。

## base(基线)

不进化。**只用契约**训练 agent:`function_definition.md` 加一个仅含 schema 的示例,其 `FUNC_OUTPUT` 就是 `answer_template` 的形状(空串、0、枚举拼写)——不暴露任何真实 train task。instruction 说明要直接从输入作答、没有任何已解示例。这是算提升时的分母。

solver(这个训练好的 agent)可以看到:

- 当前 test task 的 `FUNC_INPUT`(`prompt`、`api_base_url`、`answer_template`)。
- 允许的远程 env URL。

solver 不能看到:

- train tasks、test 标准答案、test notes、evaluator 细节。

## fewshot（少样本进化）

用**5 个已解 train task**作为示例对训练 3 个独立 agent(`FUNC_INPUT.json` / `FUNC_OUTPUT.json` 加 `train_example_02..05_{INPUT,OUTPUT}.json`),其中每个 `OUTPUT` 是该 train task 的标准 `answer.json`。训练 instruction 让 agent **根据这些 train task 进行 evolve**:研究这些已解示例、内化**可迁移**流程——SOP、字段定义、纳入/排除规则、取整、排序、常见陷阱——并把它应用到新输入上。目标是掌握可复用、能迁移的流程。

训练(进化)可以看到:

- 5 个 train task 的官方 `FUNC_INPUT`。
- 5 个 train task 的标准 `output/answer.json`。
- 允许的远程 env URL。

训练不能看到:

- test 标准答案、test notes、evaluator 细节。

solver 可见的与 `base` 相同(test `FUNC_INPUT` + env URL);区别在于由哪个训练好的 agent 作答。

## reflect（反思进化）

训练 3 个独立 agent。材料是**同样的 5 个已解 train task**;只有 instruction 不同。它要求 agent **通过反思根据这些 train task 进行 evolve**:

1. 对每个 train 输入,先自己从 prompt 和 API 规则推出答案。
2. 与提供的标准答案对比。
3. 找出究竟在哪里、为什么出现偏差(看错规则、过滤错、取整、排序、枚举)。
4. 把这些纠正提炼成带明确陷阱的可迁移流程。
5. 把这套纠正后的流程应用到新输入。

盲做 / 对比 / 反思的循环在**训练 instruction** 里被要求、在训练中执行。

## 进化质量

好的进化产出的是可执行、可迁移的经验。训练 instruction 应驱动 agent 内化:

- 能复用到 test tasks 的可迁移业务规则和 SOP。
- 如何使用暴露的 env API 端点。
- 输出字段定义和确切枚举拼写。
- 常见误判与排除规则。

训练不得引入:

- 任何来自 test task、test 答案、note 或 evaluator 的东西。
- 对特定 train 数值的死记硬背。
