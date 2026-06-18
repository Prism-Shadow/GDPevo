export const blogIntro = {
  title: {
    en: "Evaluating Agent Self-Evolution on Real Business Tasks",
    zh: "在真实企业任务上评估 Agent 的自进化能力"
  },
  lead: {
    en: "In the AI era, once a task can be evaluated and automated, it is not far from being maxed out.",
    zh: "在 AI 时代，一旦某件事可以被评估并且被自动化，它就离做到极致不远了。"
  },
  paragraphs: [
    {
      key: "gap",
      en: "Self-evolution refers to the process by which an Agent continuously improves task performance by improving its internal state. Related concepts include continual learning (CL) and recursive self-improvement (RSI). In recent months, this topic has attracted intense attention. Startups built around AI self-evolution, such as [NeoCognition](https://neocognition.io/) and [Recursive](https://www.recursive.com/), raised **billions of dollars** in 2026. Only if we can accurately evaluate an Agent's ability to self-evolve will we have the chance to explore better self-evolution strategies. Yet in **real enterprise tasks**, such as invoice auditing, trade show operations, and insurance compliance, there is almost no dedicated benchmark for evaluating an Agent's self-evolution capability, let alone doing so automatically.",
      zh: "自进化（Self-evolution）是指 Agent 通过自我改进内部状态，不断提升任务表现的过程。类似的概念也包括持续学习（Continual learning，CL）和递归自我改进（Recursive self-improvement，RSI）。近几个月这个话题备受关注，围绕 AI 自进化的初创企业（[NeoCognition](https://neocognition.io/)、[Recursive](https://www.recursive.com/) 等），在 2026 年募集了**数十亿美元**的资金。只有当我们能准确评估 Agent 自进化能力时，我们才能有机会探索更优秀的自进化策略。然而在**真实企业任务**领域，例如发票审核、展会事务和保险合规等任务，几乎没有专门的基准能评估 Agent 的自进化能力，更不用说自动化评估。"
    },
    {
      key: "release",
      en: "GDPevo attempts to fill this gap. To the best of our knowledge, it is the first benchmark for evaluating Agent self-evolution on economically valuable (or GDP-related) tasks. It is both an **automated benchmark construction process** and the output of that process: an **out-of-the-box benchmark**. The benchmark contains 120 real enterprise tasks across Customer Relationship Management (CRM), Enterprise Resource Planning (ERP), and Finance. Each task involves multiple complex rules and requires the Agent to improve itself from prior examples before it can reach satisfactory performance.",
      zh: "GDPevo 试图弥补这方面的不足，据我们所知，这是首个在具有经济价值（和 GDP 相关）的任务上评估 Agent 自进化的基准。它既是一套**自动化基准构建流程**，又是这套流程的产物，一份**开箱即用的基准**。这套基准包含 120 个真实企业任务，覆盖客户关系管理（CRM）、企业资源计划（ERP）和金融（Finance）三大场景，每个任务都会涉及多个复杂规则，需要 Agent 通过过往样本改进自身后，才能达到满意的表现。"
    },
    {
      key: "construction",
      en: "In building this benchmark, we mainly address two hard problems. First, we need two non-overlapping sets to truly test an Agent's self-evolution capability; otherwise, the evaluation becomes **training on the test set**. To solve this, we introduce **rule hybridization**, inspired by crossover evolution in genetic algorithms. We decompose complex business logic into multiple atomic rules, hide them in the training set, and then recombine them into different new tasks to form the test set. Only when the Agent has truly learned the rules can it perform well on the test samples, rather than merely memorizing the training set. Second, we want to build a sufficiently difficult evaluation benchmark. To **prevent LLMs from gaming the tasks**, we design multiple independent evaluation Agents to audit each task group end-to-end. Only automatically constructed data that reaches a required difficulty level is accepted as valid samples.",
      zh: "在构建这套基准的过程中，我们主要解决了两大难题。第一，我们需要两套互不重叠的集合才能真正测试出 Agent 自进化能力，否则就会出现**在测试集上训练**的问题。为此，我们提出了**规则杂交**的方法，源自于遗传算法中的交叉进化。我们将复杂的业务逻辑分解成多个元规则，隐藏到训练集中，再重新组合成不同的新任务，构成测试集。仅当 Agent 真正学会了规则，才能做好测试样本，而不仅仅是记住了训练集。第二，我们希望构建足够困难的评估基准，为了**防止大模型投机取巧**，我们设计了若干独立的评估 Agent，端到端地审计每一组任务，只有当自动构建的数据达到一定难度要求，才会采用作为有效样本。"
    },
    {
      key: "evaluation",
      en: "We follow three principles in evaluation. First, we use a **rule-based** grading strategy rather than model-based evaluation (LLM-as-a-judge). The final score is composed of multiple distinct rubrics, ensuring that every score is **reproducible** while also making it possible to identify the specific cause of each result. Second, we treat both **accuracy** and **cost** as first-class citizens. A good self-evolution strategy should not only become more accurate over time, but also become more cost-efficient. Third, we do not design a separate evaluation framework; instead, we use an **end-to-end** natural-language-driven evaluation process. You describe the experiment to run and the chart you want in one sentence, and Claude Code/Codex can generate the evaluation results and charts on the spot, with no manual code adaptation or writing required.",
      zh: "我们在评估过程中遵循三个原则。第一，采用**基于规则**的打分策略，而非使用基于模型的评估（LLM-as-a-judge）。最终分数由多个不同的打分点（rubrics）组成，保证每个分数都是**可复现**的，同时还能定位到具体的原因。第二，我们将**准确率**和**成本**都看作一等公民。一个好的自进化策略不仅要越来越准确，还要越来越省成本。第三，我们不设计评估框架，而是采用**端到端**自然语言驱动的评估流程。你用一句话描述要跑的实验和想要的图表，Claude code/Codex 就能当场生成评估结果和图表，全程无需人工进行任何代码适配和编写。"
    },
    {
      key: "findings",
      en: "We tested the self-evolution capability of three different Agents. Test-set accuracy generally improved by **17-22%**, and two of the Agents also showed significant reductions in token consumption. These results suggest that current Agents already have a degree of self-evolution capability: they can effectively learn from past experience and transfer that knowledge to new tasks. This finding is similar in spirit to conclusions from several existing works ([[1]](https://trinkle23897.github.io/learning-beyond-gradients/) [[2]](https://www.recursive.com/articles/first-steps-toward-automated-ai-research)).",
      zh: "我们测试了三个不同 Agent 的自进化能力，测试集准确率普遍都提升了 **17-22%**，其中两个 Agent 的 Token 消耗也有显著减少。这个结果意味着当前的 Agent 已经具备一定的自进化能力，能有效从过往经验中学习并迁移知识到新的任务上，这个发现和一些已有工作（[[1]](https://trinkle23897.github.io/learning-beyond-gradients/) [[2]](https://www.recursive.com/articles/first-steps-toward-automated-ai-research)）的结论有着相似点。"
    }
  ]
};

export const blogConstruction = {
  heading: {
    en: "How we built it",
    zh: "数据构建方法"
  },
  lead: {
    en: "Building a large-scale self-evolution benchmark for enterprise scenarios poses two challenges. First, the construction process should be fully automated end-to-end: humans write the workflow once, and AI handles the rest of running it (similar to [Loop Engineering](https://addyosmani.com/blog/loop-engineering/)). This not only helps our benchmark **outrun data leakage**: as long as the benchmark can generate new tasks faster than models can memorize leaked solutions, it can stay ahead and remain valid. It also makes the benchmark **scalable**: its size is no longer constrained by human labor and can grow on its own. Second, the training and test sets must be related, but not too similar. The Agent should be able to generalize rules from the training set to the test set, rather than memorize the training set.",
    zh: "针对企业场景构建大规模的自进化评估基准有两个挑战：首先，构建过程应能被端到端全自动完成，人只需要写一遍流程，剩下跑流程的工作交给 AI（就像 [Loop Engineering](https://addyosmani.com/blog/loop-engineering/)）。它不仅能帮我们的基准**跑赢数据泄露**，只要基准的生成速度比模型记住已泄露题解的速度快，基准就能一直保持领先和有效。它还能让基准变得**可缩放**（Scalable），基准的大小不再受人力制约，而是可以自己长大。其次，训练集和测试集要有相关性，但不能太过相似。Agent 是可以将训练集的规则泛化到测试集中，而不是记住训练集。"
  },
  agentHeading: {
    en: "Built end-to-end by multiple agents",
    zh: "数据由多个 Agent 端到端全自动构建"
  },
  pipeline: {
    en: "Humans design the workflow, and Agents keep running it continuously, as shown below. We first take seed scenarios from public real-business benchmarks ([GDPval](https://arxiv.org/abs/2510.04374), [SOP-Bench](https://arxiv.org/abs/2506.08119), and [JobBench](https://arxiv.org/abs/2605.26329)), then generate a large number of candidate task groups. Each task group builds a shared environment and generates 5 training samples and 5 test samples, with every sample paired with a rule-based grading script. A new Agent then calibrates the difficulty so that the Agent's performance after evolution clearly exceeds its performance before evolution. This step filters out samples that cannot effectively evaluate Agent evolution capability, keeping the benchmark focused on tasks that truly require cross-task self-evolution. Finally, six independent Reviewer Agents audit the result, and a task group is adopted only if it receives at least 5 passing votes. Reviewers exist to prevent Agents from cutting corners by checking whether the file structure is complete and whether the hidden rules are actually planted. In the end, 120 tasks across 12 task groups pass the filter and form the current benchmark.",
    zh: "人负责设计流程，Agent 负责持续不断运行，如下图所示。先从公开的真实业务基准（[GDPval](https://arxiv.org/abs/2510.04374)、[SOP-Bench](https://arxiv.org/abs/2506.08119)、[JobBench](https://arxiv.org/abs/2605.26329)）里取种子场景，再生成大量候选任务组。每个任务组都搭建一个共享环境，生成 5 个训练样本和 5 个测试样本，每个样本都搭配上基于规则的评分脚本。然后由一个新的 Agent 校准难度，使 Agent 在进化后的表现明显超过进化之前。这一步是为了将没法有效评估 Agent 进化能力的样本筛掉，让基准集中在那些真的需要跨任务自我进化的 Agent 上。最后由 6 个互相独立的 Reviewer Agent 审核，至少拿到 5 个通过票才会采用这组数据。Reviewer 的存在是为了防止 Agent 偷懒，检查文件结构和隐藏规则是否真正埋好。最终有 120 个任务，12 个任务组通过了筛选，形成了当前的这套基准。"
  },
  pipelineImageAlt: "GDPevo data pipeline: seed scenarios to multi-agent task factory to quality review to release.",
  hiddenHeading: {
    en: "Evaluating self-evolution through rule hybridization",
    zh: "通过规则杂交来评估自进化能力"
  },
  hiddenRules: [
    {
      key: "rules",
      en: "We scatter clues and rules throughout the training set of each task group. For example, in customer relationship management (CRM), we hide the priority order for sponsor status and a blacklist policy. In enterprise resource planning (ERP), we hide vendor risk-control rules and the corresponding response measures.",
      zh: "我们会将一些线索和规则分散藏到每个任务组的训练集中。例如在客户关系管理（CRM）中，我们会隐藏赞助商身份的优先级以及黑名单策略。在企业资源规划（ERP）中，我们会隐藏供应商的风控规则和应对措施。"
    },
    {
      key: "recombine",
      en: "We scatter these rules across the 5 training samples, with each sample containing only part of them. The 5 test samples are then designed as **combinations** of these rules, such as triggering both the \"priority\" and \"blacklist\" rules at the same time. An Agent without self-evolution capability can only see the scattered rules, while an Agent with self-evolution capability can generalize them to new tasks.",
      zh: "我们把这些规则分散埋藏到 5 个训练样本里，每个样本只包含一部分。5 个测试样本则被设计成这些规则的**组合**，比如同时触发”优先级“和”黑名单“。不具备自进化能力的 Agent 只能看到分散的规则，而具有自进化能力的 Agent 可以将它们泛化到新的任务上。"
    }
  ]
};

export const blogUsage = {
  heading: {
    en: "How to evaluate with it.",
    zh: "评估方法"
  },
  lead: {
    en: "Two things we want from an evaluation harness: it should grade in a way you can audit; and it should treat *cost* as a first-class citizen alongside accuracy. Each one motivated a specific design.",
    zh: "我们对评估 harness 有两个要求：评分必须可被人审计；*cost* 要和 accuracy 同等重要。下面两块就是为了满足这两个要求。"
  },
  gradingHeading: {
    en: "Rule-based grading, not \"ask another LLM\".",
    zh: "基于规则的评分，而不是\"再叫一个 LLM 来判\"。"
  },
  grading: {
    en: "GDPevo grades with deterministic, rule-based checkers. For example, was the right set of records returned, did the amount round to the right precision. Two things follow. First, the score is **reproducible**: the same answer always gets the same grade, regardless of who runs it or when. Second, every failure is **traceable**: instead of a vague verdict, you see exactly which rule was violated and by how much. That trace is what makes the benchmark useful for diagnosis: you can read it back to find weak spots in your agent and feed those weak spots into the next round of memory or procedure updates.",
    zh: "GDPevo 用确定性的 rule-based checker 打分，比如返回的记录集对不对、金额是否遵守了要求的精度。这带来两个好处。第一，评分是**可复现**的：同一份答案，谁跑、什么时候跑，得到的分都一样。第二，每一次失败都是**可追溯**的：你看到的不是一个含糊的整体结论，而是具体哪一条规则被违反、扣了多少分。这种可追溯性让 benchmark 成为诊断工具：你可以反过来读这些 trace，找到你的 agent 短板在哪儿，再把这些短板喂回下一轮 memory 或 procedure 更新。"
  },
  costHeading: {
    en: "Cost and accuracy, both first-class.",
    zh: "cost 和 accuracy 都是一等公民。"
  },
  cost: {
    en: "A useful agent isn't just one that gets the right answer. It is one that *stops redoing* the same legwork every time a similar task comes in. Self-evolution should look like a human getting fluent: more accurate *and* faster, with fewer tokens, fewer steps, and cleaner moves. So we instrument every run end-to-end: per-agent total token spend, plus a breakdown by reasoning, tool calls, and stage. That observability isn't only for our analysis; those traces also become raw material for the agent's next evolution update.",
    zh: "一个有用的 agent 不仅要答得对，还得*不再每次都把同样的活儿重做一遍*。Self-evolution 应该像人变熟练：更准、*更快*，用更少的 token、更少的步数、更干净的做法。所以我们对每一次运行都做端到端打点：每个 agent 的总 token 消耗，以及按 reasoning、工具调用、不同阶段的 breakdown。这套 observability 不只服务我们自己的分析，这些 trace 本身也是 agent 下一次 self-evolve 的材料。"
  }
};

export const blogFindings = {
  heading: {
    en: "Evaluations and findings.",
    zh: "实测与结果。"
  },
  intro: [
    {
      key: "workflow",
      en: "Every run below was driven by natural language: we pointed a coding agent (Codex or Claude Code) at the evaluation workspace, a folder of plain Markdown guides, prompts, and directory conventions, typed one sentence describing the experiment and the chart we wanted, and the agent generated the analysis code, called the graders, and wrote the report. No hand-written harness, no SDK to learn.",
      zh: "下面这些实验都是用自然语言驱动跑出来的：我们把一个 coding agent（Codex 或 Claude Code）指向评估工作区，也就是一个装满纯 Markdown 指南、prompt 和目录约定的文件夹；用一句话说清要跑什么实验、想要什么样的图，agent 就会自己生成分析代码、调 grader、写 report。没有手写的 harness，也没有要学的 SDK。"
    },
    {
      key: "settings",
      en: "We ran the same 12 task groups under three settings, on three different agent harnesses:",
      zh: "我们在同样的 12 组 task group 上跑了三种设定，跨三套不同的 agent harness："
    }
  ],
  modes: [
    {
      key: "base",
      en: "`base`: the agent solves the 5 test tasks cold, with no prior exposure to the 5 train tasks.",
      zh: "`base`：agent 直接做 5 个 test，没接触过 5 个 train。"
    },
    {
      key: "demo",
      en: "`demo`: the agent reads the 5 train tasks *with their gold answers* first, turns them into an evolution update, and then takes the test. (Analogous to SFT.)",
      zh: "`demo`：agent 先读 5 个 train 的题目和*标准答案*，把它们转成一次 evolution update，再去做 test。（类似 SFT。）"
    },
    {
      key: "reflect",
      en: "`reflect`: the agent attempts the 5 train tasks *without* seeing answers, gets back graded reward and feedback, updates its memory or procedure from what it got wrong, then takes the test. (Analogous to RL.)",
      zh: "`reflect`：agent *看不到答案*，自己做 5 个 train，事后拿到 reward 和反馈，更新自己的 memory 或 procedure，再去做 test。（类似 RL。）"
    }
  ],
  note: {
    en: "The shape is the same on all three harnesses: self-evolution lifts held-out accuracy by **~17–22 points**, and on the GPT-5.5 / Opus 4.8 setups tokens go *down*, not up. This is the fluency story, not just a higher score. On one task group (operational financial modeling), Codex went from **42.76% to 92.47%** with fewer tokens than the baseline; on the same group, Claude Code's `demo` reached **100%, up from 51.76%**, and Panofy's `reflect` reached **92.47%, up from 62.39%**.",
    zh: "三套 harness 形状一致：self-evolution 让 held-out 准确率提升 **约 17–22 个百分点**，且在 GPT-5.5 / Opus 4.8 这两套上，*花的 token 反而更少*。这正是\"变熟练\"，而不仅仅是分数更高。在 operational financial modeling 这一组上，Codex 从 **42.76% 升到 92.47%**，token 比基线还少；同一组上，Claude Code 的 `demo` 直接到了 **100%，起点是 51.76%**，Panofy 的 `reflect` 达到 **92.47%，起点是 62.39%**。"
  }
};

export const blogBenchmark = {
  caption: {
    en: "Each metric averages 3 attempts, then 12 task groups",
    zh: "每个指标先跨 3 次 attempt 取均值，再跨 12 个 task group 取均值"
  },
  columns: {
    harness: "Harness",
    model: "Model",
    mode: "Mode"
  },
  breakdownLink: {
    en: "See the per-group breakdown on the homepage →",
    zh: "在首页查看逐组的明细 →"
  }
};

export const blogInvite = {
  heading: {
    en: "GDPevo is a seed, not a finished product.",
    zh: "GDPevo 是一颗种子，不是一件成品。"
  },
  paragraph: {
    en: "The tasks, environments, graders, generated updates, and full reports are open. Bring your own agents and scenarios. Submit harder hidden rules. The goal is not a leaderboard, but a public interface where agents that actually do productive work can be trained, with evidence of that improvement open to inspection.",
    zh: "任务、环境、grader、生成的更新、完整 report 都是开放的。欢迎带上你自己的 agent、你自己的业务场景，欢迎来挑战、欢迎提交更难的隐藏规则。我们的目标不是一张 leaderboard，而是一个公共接口：让真正能干生产力工作的 agent 在这里被训练出来，并且这种\"它真的变好了\"的证据可以被任何人审计。"
  },
  actions: {
    github: "GitHub",
    experimentBoard: {
      en: "Experiment board",
      zh: "实验看板"
    },
    evalWorkspace: {
      en: "Eval workspace",
      zh: "评估工作区"
    }
  },
  copy: {
    label: {
      en: "Copy",
      zh: "复制"
    },
    copiedLabel: {
      en: "Copied",
      zh: "已复制"
    },
    ariaLabel: "Copy citation"
  }
};

export const citation = `@misc{gdpevo2026,
  title  = {GDPevo: Measuring Agent Self-Evolution on Real Business Work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}`;
