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
      zh: "自进化（Self-evolution）是指 Agent 通过自我改进内部状态，不断提升任务表现的过程。类似的概念也包括持续学习（Continual learning，CL）和递归自我改进（Recursive self-improvement，RSI）。近几个月这个话题备受关注，围绕 AI 自进化的初创企业（[NeoCognition](https://neocognition.io/)、[Recursive](https://www.recursive.com/) 等），在 2026 年募集了**数十亿美元**的资金。只有当我们能给准确评估 Agent 自进化能力时，我们才能有机会探索更优秀的自进化策略。然而在**真实企业任务**领域，例如发票审核、展会事务和保险合规等任务，几乎没有专门的基准能评估 Agent 的自进化能力，更不用说自动化评估。"
    },
    {
      key: "release",
      en: "GDPevo attempts to fill this gap. To the best of our knowledge, it is the first benchmark for evaluating Agent self-evolution on economically valuable (GDP) tasks. It is both an **automated benchmark construction process** and the output of that process: an **out-of-the-box benchmark**. The benchmark contains 120 real enterprise tasks across CRM, ERP, and Finance. Each task involves multiple complex rules and requires the Agent to improve itself from prior examples before it can reach satisfactory performance.",
      zh: "GDPevo 试图弥补这方面的不足，据我们所知，这是首个在具有经济价值（GDP）的任务上评估 Agent 自进化的基准。它既是一套**自动化基准构建流程**，又是这套流程的产物，一份**开箱即用的基准**。这套基准包含 120 个真实企业任务，覆盖 CRM、ERP、Finance 三大场景，每个任务都会涉及多个复杂规则，需要 Agent 通过过往样本改进自身后，才能达到满意的表现。"
    },
    {
      key: "construction",
      en: "In building this benchmark, we mainly addressed two hard problems. First, we need two non-overlapping sets to truly test an Agent's self-evolution capability; otherwise, the evaluation becomes **training on the test set**. To solve this, we introduce **rule hybridization**, inspired by crossover evolution in genetic algorithms. We decompose complex business logic into multiple atomic rules, hide them in the training set, and then recombine them into different new business scenarios to form the test set. Only when the Agent has truly learned the rules can it perform well on the test samples, rather than merely memorizing the training set. Second, we want to build a sufficiently difficult evaluation benchmark. To **prevent large models from gaming the tasks**, we design multiple independent evaluation Agents to audit each task group end-to-end. Only automatically constructed data that reaches a required difficulty level is accepted as valid samples.",
      zh: "在构建这套基准的过程中，我们主要解决了两大难题。第一，我们需要两套互不重叠的集合才能真正测试出 Agent 自进化能力，否则就会出现**在测试集上训练**的问题。为此，我们提出了**规则杂交**的方法，源自于遗传算法中的交叉进化。我们将复杂的业务逻辑分解成多个元规则，隐藏到训练集中，再重新组合成不同的新业务，构成测试集。仅当 Agent 真正学会了规则，才能做好测试样本，而不仅仅是记住了训练集。第二，我们希望构建足够困难的评估基准，为了**防止大模型投机取巧**，我们设计了若干独立的评估 Agent，端到端地审计每一组任务，只有当自动构建的数据达到一定难度要求，才会采用作为有效样本。"
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
    en: "How we built it.",
    zh: "我们怎么构建。"
  },
  lead: {
    en: "Building a self-evolution benchmark for real business work poses two challenges. **First**, the construction should be agent-driven end-to-end: humans write the procedure once, agents do the rest. This matters for two reasons. It helps the benchmark *outrun data leakage*: as long as agents can spawn fresh tasks faster than models absorb the leaked ones, the benchmark stays ahead. It also lets the benchmark *scale*: when agents both build and evaluate, the loop is closed, with no human bottleneck, and the benchmark can keep growing on its own. **Second**, train and test have to be related but not redundant: the train tasks must teach a real, hidden lesson that pays off only when the lesson is extracted, not memorized.",
    zh: "为真实业务工作构建一个 self-evolution benchmark，有两个 challenge。**第一**，构建过程应该是 agent 端到端跑出来的：人只把流程写一次，剩下交给 agent。这件事之所以重要有两个原因。它能帮 benchmark *跑赢数据泄露*：只要 agent 生成新题的速度比模型吸收已泄露题的速度快，benchmark 就一直保持领先。它也让 benchmark 能*真正 scale*：当 agent 既负责构造、又负责评测，整个回路就闭合了，没有人力瓶颈，benchmark 可以自己长大。**第二**，train 和 test 要相关、但不能冗余：train 必须真的\"教\"一个隐藏的规则，这个规则只有被抽象出来才会在 test 上派上用场，而不是被死记下来。"
  },
  agentHeading: {
    en: "Built end-to-end by agents.",
    zh: "从头到尾，全部由 agent 完成。"
  },
  pipeline: {
    en: "Humans wrote the pipeline once. After that, agents do everything (illustrated below). They pull seed scenarios from public real-job benchmarks (GDPval, SOP-Bench, JobBench) and spawn many candidate task groups from those seeds. For each group, they build a shared environment and author 5 train + 5 test tasks with rule-based evaluators. A calibrator then tunes difficulty so that an `evolution` setup clearly beats a `no-evolution` setup. This filters out tasks where evolution wouldn't change the answer, keeping the benchmark focused on agents that actually have to evolve across related work. Finally, six independent reviewer agents audit the result, and a group ships only when 5 of 6 pass. These reviewers exist because agents have a habit of declaring victory while quietly skipping work, so completeness, file presence, and planted hidden rules are exactly what gets checked. Twelve task groups make it through this filter and form the public release.",
    zh: "人只写一次 pipeline，之后全靠 agent（如下图所示）。先从公开的真实业务 benchmark（GDPval、SOP-Bench、JobBench）里取种子场景，再据此 spawn 出大量候选 task group。每组里搭一个共享 env，写 5 个 train + 5 个 test 任务并配上基于规则的 evaluator。然后 calibrator 调难度，让 `evolution` 设定明显超过 `no-evolution` 设定。这一步是为了把那些\"是否进化都不影响答案\"的题筛掉，让 benchmark 集中在那些真的需要跨相关任务自我进化的 agent 上。最后由 6 个互相独立的 reviewer agent 审核，6 个里 5 个通过这一组才放行。之所以要 reviewer，是因为 agent 经常嘴上说\"做完了\"、实际偷懒，所以审核的就是结构、完整性、文件是否齐全、隐藏规则是否真的埋了进去。最终通过这层筛选活下来、进入公开发布的，是 12 组 task group。"
  },
  pipelineImageAlt: "GDPevo data pipeline: seed scenarios to multi-agent task factory to quality review to release.",
  hiddenHeading: {
    en: "Hidden rules, spread across the train tasks.",
    zh: "隐藏规则，分散到各个 train task 里。"
  },
  hiddenRules: [
    {
      key: "rules",
      en: "For every task group we plant a small set of hidden operational rules. A CRM lead-capture group might encode a *sponsor-status precedence rule* (finance invoices outrank badge scans) and a *suppression-list policy* (don't contact certain segments). A procurement-readiness group enforces that *open vendor-risk events and AP holds force a \"held\" line*, regardless of how clean the PO looks.",
      zh: "每个 task group 我们都会埋一小组隐藏的业务规则。CRM 销售线索组可能埋了两条：*赞助商身份的优先级*（财务发票优先于胸卡扫描），以及 *suppression list 政策*（某些细分人群禁止联系）。采购就绪组则要求：*只要供应商有 open 的 risk event 或 AP hold，对应行就必须 held*，不管 PO 看起来多干净。"
    },
    {
      key: "recombine",
      en: "We *spread* these rules across the 5 train tasks, so each train task only exercises a subset. The 5 test tasks are deliberately built as **combinations**, say, the precedence rule together with the suppression policy. An agent that solves each train in isolation only sees rule fragments. An agent that turns them into an evolution update has them all in one place; when the test asks for two at once, it doesn't need to rediscover them. That's why a higher test score is real evidence of evolution, not luck.",
      zh: "我们把这些规则*分散*到 5 个 train 里，每个 train 只触发一部分。5 个 test 故意被设计成这些规则的**组合**，比如同时触发\"优先级 + suppression\"。只盯着单个 train 做的 agent 看到的是碎片；能把这些规则转成一次 evolution update 的 agent，则把它们放在一处。test 同时问两条时，它不需要重新发现。这就是 test 分数变高的原因，是真的发生了进化，而不是运气。"
    }
  ]
};

export const blogUsage = {
  heading: {
    en: "How to evaluate with it.",
    zh: "怎么用它做评估。"
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
