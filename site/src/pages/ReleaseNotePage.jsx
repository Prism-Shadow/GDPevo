import { Lang } from "../lib/i18n.jsx";

const release = {
  en: {
    title: "GDPevo — The V2 Release",
    subtitle: "Broader · Deeper · Sharper.",
    summary: "We grew GDPevo along three independent axes: more scenarios it covers, more agents it puts under test, and more lenses through which you can read the results.",
    meta: "Version: v2.0 · Date: 2026-07-17",
    agentDefinition: (
      <>
        Throughout this note, an <strong>agent</strong> = a <strong>model</strong> running inside a <strong>harness</strong> (for example Claude Code · Opus 4.8, or Codex · GPT-5.5). Everything GDPevo puts under test is a different agent.
      </>
    ),
    tldrTitle: "TL;DR",
    tldrColumns: ["Axis", "Before", "After"],
    tldrRows: [
      ["① Width — business domains", "3 domains · 12 task groups · 120 tasks", "6 domains · 24 task groups · 240 tasks"],
      ["② Depth — models under test", "3 agents", "more agents, incl. Claude Code × DeepSeek V4 Pro, Kimi K2.6, and GLM-5.2"],
      ["③ Lens — evaluation metrics", "accuracy · tokens · cost", "+ turn count, plus heatmaps, score breakdowns, and radar views"]
    ],
    widthTitle: "① Width — the benchmark got wider",
    widthParagraphs: [
      "We doubled the coverage of the benchmark by adding three new domains on top of the original CRM / ERP / Finance set — each mirrors everyday enterprise work:",
      "This takes GDPevo from 120 tasks across 12 task groups to 240 tasks across 24 task groups."
    ],
    domains: [
      ["Legal", "e.g. reviewing contracts when one company acquires another."],
      ["Medical", "e.g. getting a patient's records ready before a hospital transfer."],
      ["Data processing", "e.g. cleaning up a messy dataset before it can be analyzed."]
    ],
    depthTitle: "② Depth — we tested more models, more thoroughly",
    depthIntro: "Beyond the previous agents (Codex · GPT-5.5, Claude Code · Opus 4.8, Panofy · Opus 4.6), this release evaluates more agents and reports both their overall scores and per-group breakdowns, so readers can compare agents apples-to-apples:",
    newAgents: ["Claude Code × DeepSeek V4 Pro", "Claude Code × Kimi K2.6", "Claude Code × GLM-5.2", "…and more"],
    depthOutro: "Each agent is run in base (no-evolution) mode plus three self-evolution modes — self, fewshot, and reflect-3.",
    leaderboardTitle: "Leaderboard",
    leaderboardIntro: (
      <>
        A <strong>partial</strong> view — just the rows behind the findings below, keeping their original rank. The <strong>full 24-row leaderboard</strong> (all 6 agents × 4 modes, sortable) lives on the <a href="https://prism-shadow.github.io/GDPevo/index.html" target="_blank" rel="noreferrer">project site</a>. <strong>Lift</strong> is the gain over the same agent&apos;s base run.
      </>
    ),
    leaderboardColumns: ["#", "Agent", "Mode", "Method", "avg@3", "Lift (pp)", "Cost (USD)", "Rounds", "Tokens"],
    leaderboardRows: [
      ["1", "Panofy · Opus 4.6", "fewshot", "Agent Training", "71.47%", "+21.07", "$0.81", "13.48", "385.5k"],
      ["2", "Claude Code · Opus 4.8", "fewshot", "Skill Creator", "70.90%", "+21.79", "$0.55", "11.10", "347.3k"],
      ["3", "Claude Code · GLM-5.2", "fewshot", "Skill Creator", "69.55%", "+21.83", "$0.34", "15.49", "606.3k"],
      ["4", "Codex · GPT-5.5", "fewshot", "Skill Creator", "64.91%", "+18.19", "$0.81", "11.58", "451.7k"],
      ["⋮", "", "", "", "", "", "", "", ""],
      ["13", "Claude Code · DeepSeek V4 Pro", "fewshot", "Skill Creator", "54.80%", "+8.74", "$0.032", "11.46", "439.9k"],
      ["16", "Claude Code · Opus 4.8", "base", "—", "49.11%", "—", "$0.61", "14.62", "385.8k"],
      ["19", "Codex · GPT-5.5", "base", "—", "46.72%", "—", "$1.14", "14.91", "735.3k"],
      ["⋮", "", "", "", "", "", "", "", ""],
      ["21", "Claude Code · Kimi K2.6", "reflect-3", "Skill Creator", "32.68%", "+7.54", "$0.28", "31.68", "950.5k"],
      ["24", "Claude Code · Kimi K2.6", "base", "—", "25.14%", "—", "$0.34", "46.24", "1226.7k"]
    ],
    findings: (
      <>
        <strong>Findings.</strong> Self-evolution pays off for every agent — the <strong>fewshot</strong> mode lifts tests avg@3 by <strong>+18 to +22 pp</strong> over <strong>base</strong>. The lever is high enough to leapfrog model tiers: <strong>DeepSeek V4 Pro</strong> with <strong>fewshot</strong> reaches <strong>54.8%</strong>, above the <strong>base</strong> (no-evolution) scores of flagship agents like <strong>Opus 4.8</strong> (49.1%) and <strong>GPT-5.5</strong> (46.7%) — so evolving a cheaper model can beat running a flagship one as-is. At the bottom, <strong>Kimi K2.6</strong> is both the weakest (25–33%) and by far the most interaction-heavy, burning 30–46 rounds and up to 1.2M tokens per task.
      </>
    ),
    lensTitle: "③ Lens — more ways to read the results",
    lensIntro: "On top of the original accuracy / token count / cost metrics, this release adds:",
    lenses: [
      ["Turn count", "how many agent turns each task takes, a direct read on interaction efficiency."],
      ["Heatmaps", "how a learned skill transfers across task groups (source × target)."],
      ["Score breakdown charts", "per-group and per-mode decomposition."],
      ["Radar charts", "one agent's accuracy across all task groups, for comparing modes or models at a glance."]
    ],
    heatmapTitle: "Result 1 — skill-transfer heatmap",
    heatmapIntro: "Each panel applies a skill learned on the row task group to the column target, showing avg@3 and its Δ vs base.",
    heatmapFinding: "The diagonals (reusing a skill on its own domain) of fewshot and reflect-3 are reliably green — it lifts avg@3 by up to +9.6 pp (CRM fewshot). Off the diagonal, cross-domain transfer is riskier: a fewshot skill carried to a different domain can hurt (Finance → ERP −5.0 pp), but reflect-3 skills generalize far more safely, with nearly every cross-domain cell staying positive.",
    radarTitle: "Result 2 — radar views",
    radarIntro: "The radar chart supports two types of comparisons:",
    radarModeTitle: "Usage 1 — one agent, all modes.",
    radarModeText: "Fix an agent and vary the mode to see how far it evolves and how big the lift is. Here Claude Code · Opus 4.8 grows from base (49.1%) out to fewshot (70.9%) across the 12 task groups:",
    radarModelTitle: "Usage 2 — one mode, all models.",
    radarModelText: "Fix the mode and vary the model to see which is strongest per task group. Here every agent under fewshot — Opus 4.6 (71.5%) and Opus 4.8 (70.9%) occupy the outer edge, Kimi K2.6 (30.5%) the inner one:",
    getStartedTitle: "Get started",
    getStartedText: "GDPevo is public and ready to run. Pull the tasks, pick your agent, run it in base / self / fewshot / reflect-3 mode, and compare against the board.",
    links: [
      ["Leaderboard", "https://prism-shadow.github.io/GDPevo/index.html", "overall scores and per-group breakdowns for every agent"],
      ["Project blog", "blog-self-evolution.html", "motivation, construction pipeline, and findings"],
      ["GitHub repo", "https://github.com/Prism-Shadow/GDPevo", "code, data, and issues"]
    ],
    discussionTitle: "Join the discussion",
    discussionText: "Questions, feedback, and results are all welcome — scan to join our WeChat group."
  },
  zh: {
    title: "GDPevo — V2 版本发布",
    subtitle: "更宽 · 更深 · 更清晰。",
    summary: "我们在三个相互独立的维度上扩展了 GDPevo：覆盖更多的业务场景、纳入更多受测 Agent、以及更多解读结果的视角。",
    meta: "版本：v2.0 · 日期：2026-07-17",
    agentDefinition: (
      <>
        在本文中，一个 <strong>Agent</strong> = 一个<strong>模型</strong>（model）运行在一个<strong>框架</strong>（harness）之中（例如 Claude Code · Opus 4.8，或 Codex · GPT-5.5）。GDPevo 所测试的每一个对象，都是一个不同的 Agent。
      </>
    ),
    tldrTitle: "一句话总结",
    tldrColumns: ["维度", "之前", "之后"],
    tldrRows: [
      ["① 宽度 — 业务领域", "3 个领域 · 12 个任务组 · 120 个任务", "6 个领域 · 24 个任务组 · 240 个任务"],
      ["② 深度 — 受测模型", "3 个 Agent", "更多 Agent，包括 Claude Code × DeepSeek V4 Pro、Kimi K2.6、GLM-5.2"],
      ["③ 视角 — 评测指标", "准确率 · token · 成本", "新增 turn 数量，以及热力图、分数 breakdown、雷达图"]
    ],
    widthTitle: "① 宽度 —— Benchmark 变宽了",
    widthParagraphs: [
      "我们在原有的 CRM / ERP / Finance 之上新增了三个领域，每个都对应日常企业工作：",
      "由此 GDPevo 从 12 个任务组、120 个任务扩张到 24 个任务组、240 个任务。"
    ],
    domains: [
      ["法律（Legal）", "比如审查一家公司收购另一家公司时的合同。"],
      ["医疗（Medical）", "比如在病人转院前整理好病历。"],
      ["数据处理（Data processing）", "比如在数据能被分析之前先清洗掉其中的脏数据。"]
    ],
    depthTitle: "② 深度 —— 我们评测了更多模型，也更彻底理解 Agent 的行为",
    depthIntro: "在原有的 Agent（Codex · GPT-5.5、Claude Code · Opus 4.8、Panofy · Opus 4.6）之外，本次更新评测了更多 Agent，并同时给出它们的总体分数与分组 breakdown，方便读者做同口径对比：",
    newAgents: ["Claude Code × DeepSeek V4 Pro", "Claude Code × Kimi K2.6", "Claude Code × GLM-5.2", "……以及更多"],
    depthOutro: "每个 Agent 都在 base（无进化）模式，以及三种自进化模式——self、fewshot、reflect-3——下运行。",
    leaderboardTitle: "榜单",
    leaderboardIntro: (
      <>
        <strong>部分</strong>榜单——只列出下面 findings 涉及的几行，并保留其原始排名。<strong>完整的 24 行榜单</strong>（全部 6 个 Agent × 4 种模式，可排序）在<a href="https://prism-shadow.github.io/GDPevo/index.html" target="_blank" rel="noreferrer">项目站点</a>上查看。<strong>提升</strong>是相对该 Agent 自身 base 运行的增益。
      </>
    ),
    leaderboardColumns: ["#", "Agent", "模式", "方法", "avg@3", "提升（pp）", "费用（USD）", "轮次", "令牌数"],
    leaderboardRows: [
      ["1", "Panofy · Opus 4.6", "fewshot", "Agent Training", "71.47%", "+21.07", "$0.81", "13.48", "385.5k"],
      ["2", "Claude Code · Opus 4.8", "fewshot", "Skill Creator", "70.90%", "+21.79", "$0.55", "11.10", "347.3k"],
      ["3", "Claude Code · GLM-5.2", "fewshot", "Skill Creator", "69.55%", "+21.83", "$0.34", "15.49", "606.3k"],
      ["4", "Codex · GPT-5.5", "fewshot", "Skill Creator", "64.91%", "+18.19", "$0.81", "11.58", "451.7k"],
      ["⋮", "", "", "", "", "", "", "", ""],
      ["13", "Claude Code · DeepSeek V4 Pro", "fewshot", "Skill Creator", "54.80%", "+8.74", "$0.032", "11.46", "439.9k"],
      ["16", "Claude Code · Opus 4.8", "base", "—", "49.11%", "—", "$0.61", "14.62", "385.8k"],
      ["19", "Codex · GPT-5.5", "base", "—", "46.72%", "—", "$1.14", "14.91", "735.3k"],
      ["⋮", "", "", "", "", "", "", "", ""],
      ["21", "Claude Code · Kimi K2.6", "reflect-3", "Skill Creator", "32.68%", "+7.54", "$0.28", "31.68", "950.5k"],
      ["24", "Claude Code · Kimi K2.6", "base", "—", "25.14%", "—", "$0.34", "46.24", "1226.7k"]
    ],
    findings: (
      <>
        <strong>发现。</strong>自进化对每个 Agent 都奏效——<strong>fewshot</strong> 模式相比 <strong>base</strong> 把测试集 avg@3 抬高了 <strong>+18 到 +22 pp</strong>。而这个杠杆高到可以跨越模型档位：<strong>DeepSeek V4 Pro</strong> 配上 <strong>fewshot</strong> 达到 <strong>54.8%</strong>，超过了 <strong>Opus 4.8</strong>（49.1%）、<strong>GPT-5.5</strong>（46.7%）这些旗舰 Agent 在 <strong>base</strong>（无进化）下的分数——也就是说，让一个更便宜的模型自进化，能打过原样跑的旗舰模型。另一端，<strong>Kimi K2.6</strong> 既最弱（25–33%），交互也最重，每个任务要烧掉 30–46 轮、最多 120 万 token。
      </>
    ),
    lensTitle: "③ 视角 —— 更多解读结果的方式",
    lensIntro: "在原有的准确率 / token 数 / 成本之上，本次新增：",
    lenses: [
      ["Turn 数量", "每个任务花了多少个 Agent 回合，直接反映交互效率。"],
      ["热力图（Heatmap）", "一个学到的技能在不同任务组之间如何迁移（源 × 目标）。"],
      ["分数 breakdown 图", "按任务组、按模式的分解。"],
      ["雷达图（Radar）", "单个 Agent 在所有任务组上的准确率，方便一眼对比不同模式或不同模型。"]
    ],
    heatmapTitle: "例子 1 —— 技能迁移热力图",
    heatmapIntro: "每个面板把在行任务组上学到的技能应用到列目标任务组，展示 avg@3 及其相对无技能 base 的 Δ。",
    heatmapFinding: "fewshot 和 reflect-3 的对角线（把技能用回它自己的领域）稳定为绿——最高能把 avg@3 抬升 +9.6 pp（CRM fewshot）。而在对角线之外，跨领域迁移风险更大：fewshot 技能被搬到别的领域可能掉分（Finance → ERP −5.0 pp）；但 reflect-3 技能的泛化要安全得多，几乎每一个跨领域格子都保持为正。",
    radarTitle: "例子 2 —— 雷达图用法",
    radarIntro: "同一张雷达图支持两类对比：",
    radarModeTitle: "用法 1 —— 固定一个 Agent，看所有模式。",
    radarModeText: "固定一个 Agent，变换模式，就能看到它进化了多远、幅度多大。这里 Claude Code · Opus 4.8 在 12 个任务组上从 base（49.1%）一路长到 fewshot（70.9%）：",
    radarModelTitle: "用法 2 —— 固定一种模式，看所有模型。",
    radarModelText: "固定模式、变换模型，就能看出每个任务组上哪个模型更强。这里是 fewshot 下的所有 Agent —— Opus 4.6（71.5%）和 Opus 4.8（70.9%）占据最外圈，Kimi K2.6（30.5%）在最内圈：",
    getStartedTitle: "立即开始",
    getStartedText: "GDPevo 已公开，开箱即用。拉取任务、选定你的 Agent、在 base / self / fewshot / reflect-3 模式下运行，然后与榜单对比。",
    links: [
      ["榜单", "https://prism-shadow.github.io/GDPevo/index.html", "每个 Agent 的总体分数与分组 breakdown"],
      ["项目博客", "blog-self-evolution.html", "动机、构建流程与发现"],
      ["GitHub 仓库", "https://github.com/Prism-Shadow/GDPevo", "代码、数据与 issue"]
    ],
    discussionTitle: "加入讨论",
    discussionText: "欢迎大家一起讨论问题、反馈与结果 —— 扫码加入我们的微信群。"
  }
};

const assets = {
  iconTable: "assets/release/fig-icon-table.svg",
  heatmap: "assets/release/heatmap.png",
  acrossModes: "assets/release/across_modes.jpg",
  acrossModels: "assets/release/across_models.jpg",
  wechat: "assets/release/wechat.jpg"
};

function ReleaseTable({ columns, rows, compact = false }) {
  return (
    <div className={compact ? "release-table release-table-compact" : "release-table"}>
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr className={row[0] === "⋮" ? "release-table-gap" : undefined} key={`${row[0]}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReleaseFigure({ src, alt, width = 760 }) {
  return (
    <figure className="release-figure">
      <img src={src} alt={alt} style={{ "--release-img-width": `${width}px` }} loading="lazy" />
    </figure>
  );
}

export function ReleaseNotePage({ lang = "en" }) {
  const copy = release[lang] ?? release.en;

  return (
    <main id="top" className="blog-page release-note-page">
      <section className="section release-hero">
        <div className="wrap narrow">
          <a className="blog-back-link" href="blog.html">
            <Lang en="← Back to blog" zh="← 返回博客列表" />
          </a>
          <p className="blog-meta release-meta">{copy.meta}</p>
          <h1 className="h2 blog-title">{copy.title}</h1>
          <blockquote className="lead blog-quote">
            <strong>{copy.subtitle}</strong> {copy.summary}
          </blockquote>
          <p className="release-agent-definition">{copy.agentDefinition}</p>
        </div>
      </section>

      <article className="section release-body">
        <div className="wrap narrow release-prose">
          <h2>{copy.tldrTitle}</h2>
          <ReleaseTable columns={copy.tldrColumns} rows={copy.tldrRows} compact />
          <ReleaseFigure
            src={assets.iconTable}
            alt="Three dimensions point by point: domains, models, and metrics with their icons"
            width={880}
          />

          <h2>{copy.widthTitle}</h2>
          <p>{copy.widthParagraphs[0]}</p>
          <ul>
            {copy.domains.map(([name, text]) => (
              <li key={name}>
                <strong>{name}</strong> — {text}
              </li>
            ))}
          </ul>
          <p>{copy.widthParagraphs[1]}</p>

          <h2>{copy.depthTitle}</h2>
          <p>{copy.depthIntro}</p>
          <ul>
            {copy.newAgents.map((agent) => (
              <li key={agent}>{agent}</li>
            ))}
          </ul>
          <p>{copy.depthOutro}</p>

          <h3 id="leaderboard">{copy.leaderboardTitle}</h3>
          <p>{copy.leaderboardIntro}</p>
          <ReleaseTable columns={copy.leaderboardColumns} rows={copy.leaderboardRows} />
          <p>{copy.findings}</p>

          <h2>{copy.lensTitle}</h2>
          <p>{copy.lensIntro}</p>
          <ul>
            {copy.lenses.map(([name, text]) => (
              <li key={name}>
                <strong>{name}</strong> — {text}
              </li>
            ))}
          </ul>

          <h4>{copy.heatmapTitle}</h4>
          <p>{copy.heatmapIntro}</p>
          <ReleaseFigure
            src={assets.heatmap}
            alt="Codex · GPT-5.5 skill-transfer heatmaps for base, fewshot, and reflect-3, with avg@3 and delta-vs-base per cell"
            width={960}
          />
          <p>{copy.heatmapFinding}</p>

          <h4>{copy.radarTitle}</h4>
          <p>{copy.radarIntro}</p>
          <p>
            <strong>{copy.radarModeTitle}</strong> {copy.radarModeText}
          </p>
          <ReleaseFigure
            src={assets.acrossModes}
            alt="Radar chart of Claude Code · Opus 4.8 across base, self, fewshot, and reflect-3 modes over task groups TG001–TG012"
          />
          <p>
            <strong>{copy.radarModelTitle}</strong> {copy.radarModelText}
          </p>
          <ReleaseFigure
            src={assets.acrossModels}
            alt="Radar chart of all six models under the fewshot mode over task groups TG001–TG012"
          />

          <h2>{copy.getStartedTitle}</h2>
          <p>{copy.getStartedText}</p>
          <ul>
            {copy.links.map(([label, href, text]) => {
              const external = /^https?:\/\//.test(href);
              return (
                <li key={label}>
                  <strong>
                    <a href={href} {...(external ? { target: "_blank", rel: "noreferrer" } : {})}>{label}</a>
                  </strong>{" "}
                  — {text}
                </li>
              );
            })}
          </ul>

          <h2>{copy.discussionTitle}</h2>
          <p>{copy.discussionText}</p>
          <ReleaseFigure
            src={assets.wechat}
            alt="WeChat QR code to join the GDPevo discussion group"
            width={320}
          />
        </div>
      </article>
    </main>
  );
}
