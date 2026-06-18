import { Fragment, useMemo, useState } from "react";
import { GitHubIcon, NavIcon } from "../components/icons.jsx";
import { Lang } from "../lib/i18n.jsx";
import { links } from "../lib/links.js";
import { harnesses, modes, resultGroups, summaryCards, taskGroups, taskTopics } from "../data.js";

function Hero() {
  return (
    <section className="hero">
      <div className="hero-glow" aria-hidden="true" />
      <div className="wrap hero-inner">
        <h1 className="hero-title">
          <span className="lang-en">
            <span className="accent">GDPevo</span>: Measuring Agent
            <br className="hero-break" />
            {" "}Self-Evolution on Real Business Work
          </span>
          <span className="lang-zh">
            <span className="accent">GDPevo</span>：在真实业务工作上
            <br className="hero-break" />
            衡量 Agent 的自我进化
          </span>
        </h1>
        <p className="hero-sub">
          <span className="lang-en">
            Not <em>can the agent solve this task?</em>
            <br />
            — but <strong>can it evolve across related tasks to get better?</strong>
          </span>
          <span className="lang-zh">
            不是问<em>这个 agent 能不能解决这个任务</em>，
            <br />
            而是问<strong>它能不能借由相关任务完成自我进化，越来越擅长这一类任务</strong>。
          </span>
        </p>
        <p className="hero-meta">
          <Lang en="PrismShadow Team · 2026" zh="PrismShadow Team · 2026" />
        </p>
        <div className="btn-row">
          <a className="btn btn-dark" href={links.repo} target="_blank" rel="noreferrer">
            <GitHubIcon size={17} />
            <span>GitHub</span>
          </a>
          <a className="btn btn-ghost" href="#results">
            <NavIcon name="chart" />
            <span>
              <Lang en="Results" zh="结果" />
            </span>
          </a>
          <a className="btn btn-ghost" href="blog.html">
            <NavIcon name="blog" />
            <span>
              <Lang en="Read the blog" zh="阅读博客" />
            </span>
          </a>
          <a className="btn btn-ghost" href={links.experimentBoard} target="_blank" rel="noreferrer">
            <NavIcon name="code" />
            <span>
              <Lang en="Experiment board" zh="实验看板" />
            </span>
          </a>
        </div>
        <div className="stat-band">
          <div className="stat">
            <span className="stat-num">120</span>
            <span className="stat-label">
              <Lang en="GDP-worthy tasks" zh="真实业务任务" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num">12</span>
            <span className="stat-label">
              <Lang en="Task groups · CRM · ERP · Finance" zh="任务组 · CRM · ERP · Finance" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num stat-tba">
              <Lang en="TBD" zh="暂定" />
            </span>
            <span className="stat-label">
              <Lang en="Held-out accuracy lift from self-evolution" zh="自我进化带来的 held-out 准确率提升" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num stat-tba">
              <Lang en="TBD" zh="暂定" />
            </span>
            <span className="stat-label">
              <Lang en="Token cost — fewer, not more" zh="token 成本 —— 更少，而非更多" />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SummaryCard({ card }) {
  return (
    <div className="htable">
      <div className="ht-cap">
        <span>{card.title}</span>
        <small>
          <span className="lang-en">{card.thinking} · avg@3 over 12 task groups</span>
          <span className="lang-zh">{card.thinking} · 12 个 task group 的 avg@3</span>
        </small>
      </div>
      <div className="ht-row ht-head">
        <span>
          <Lang en="Mode" zh="模式" />
        </span>
        <span className="num">avg@3</span>
        <span className="num">
          <Lang en="Tokens (k)" zh="Tokens (k)" />
        </span>
        <span className="num">USD</span>
      </div>
      {card.rows.map((row) => (
        <div key={row.mode} className={`ht-row ${row.best ? "best" : ""}`}>
          <code>{row.mode}</code>
          <span className="num">{row.avg}</span>
          <span className="num">{row.tokens}</span>
          <span className="num">{row.usd}</span>
        </div>
      ))}
    </div>
  );
}

function Meter({ value, mode }) {
  return (
    <div className={`ob-meter mode-${mode}`}>
      <div className="ob-track">
        <span className={`fl ${mode}`} style={{ "--w": `${value.toFixed(2)}%` }} />
      </div>
      <b>{value.toFixed(1)}</b>
    </div>
  );
}

function HarnessRows({ harness, group }) {
  return (
    <div className="ob-harness-block">
      <span className="ob-harness">{harness.harness}</span>
      <span className="ob-model">{harness.model}</span>
      <span className="ob-thinking">{harness.thinking}</span>
      <div className="ob-condition-rows">
        {modes.map((mode, index) => (
          <div className="ob-row" key={mode}>
            <code>{mode}</code>
            <Meter value={group[harness.key][index]} mode={mode} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultsChart() {
  return (
    <figure className="panel chart merged-chart shown" id="chart">
      <figcaption className="panel-head">
        <span className="panel-title">
          <Lang en="Held-out accuracy by task group (avg@3, %)" zh="各 task group 的 held-out 准确率 (avg@3, %)" />
        </span>
        <span className="legend">
          <span className="leg">
            <i className="sw sw-base" />
            base
          </span>
          <span className="leg">
            <i className="sw sw-demo" />
            demo
          </span>
          <span className="leg">
            <i className="sw sw-reflect" />
            reflect
          </span>
        </span>
      </figcaption>
      <div className="combined-bars">
        <div className="ob-head">
          <span>
            <Lang en="Task group" zh="Task group" />
          </span>
          <span>Harness</span>
          <span>Model</span>
          <span>Thinking level</span>
          <span>
            <Lang en="Setting" zh="设定" />
          </span>
          <span>Accuracy</span>
        </div>
        {resultGroups.map((group) => {
          const chip = group.domain === "Finance" ? "fin" : group.domain.toLowerCase();
          return (
            <div className="ob-group" key={group.id}>
              <div className="ob-name">
                <strong>{group.id}</strong>
                <i className={`chip ${chip}`}>{group.domain}</i>
                <span>
                  <Lang en={group.en} zh={group.zh} />
                </span>
              </div>
              <div className="ob-rows">
                {harnesses.map((harness) => (
                  <HarnessRows key={harness.key} harness={harness} group={group} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function ResultsSection() {
  return (
    <section className="section" id="results">
      <div className="wrap results-wrap">
        <h2 className="h2">
          <span className="lang-en">
            Self-evolution makes agents more accurate while spending <span className="accent">fewer</span> tokens.
          </span>
          <span className="lang-zh">
            自我进化让 agent 更准,同时花<span className="accent">更少</span>的 token。
          </span>
        </h2>
        <p className="lead">
          <span className="lang-en">
            Each group has 5 train and 5 held-out test tasks. We compare a baseline (<code>base</code>) against two evolution modes: <code>demo</code> evolves from worked examples, while <code>reflect</code> evolves from its own mistakes. The score measures lift on tasks the agent never saw.
          </span>
          <span className="lang-zh">
            每组有 5 个 train、5 个 held-out test。我们用基线（<code>base</code>）对比两种进化模式：<code>demo</code> 基于样例进化，<code>reflect</code> 基于自己的错误进化；分数衡量的是 agent 在没见过的任务上的提升。
          </span>
        </p>
        <div className="htables">
          {summaryCards.map((card) => (
            <SummaryCard key={card.title} card={card} />
          ))}
        </div>
        <ResultsChart />
        <p className="note">
          <span className="lang-en">
            <strong>avg@3</strong> = mean held-out accuracy over 3 attempts per task. The task-group chart below keeps Codex, Claude Code, and Panofy side by side under the same base, demo, and reflect settings.
          </span>
          <span className="lang-zh">
            <strong>avg@3</strong> = 每个任务 3 次尝试的 held-out 准确率均值。下面的 task-group 图并排展示 Codex、Claude Code 与 Panofy 在 base、demo、reflect 下的结果。
          </span>
        </p>
        <p className="note">
          <span className="lang-en">
            Accuracy lift / cost change: <strong>+20.31 pp / −8.69%</strong> (Claude Code) · <strong>+18.21 pp / −25.75%</strong> (Codex) · <strong>+17.94 pp / +11.82%</strong> (Panofy).
          </span>
          <span className="lang-zh">
            准确率提升 / Cost 变化：<strong>+20.31 pp / −8.69%</strong>（Claude Code）· <strong>+18.21 pp / −25.75%</strong>（Codex）· <strong>+17.94 pp / +11.82%</strong>（Panofy）。
          </span>
        </p>
        <p className="note">
          <span className="lang-en">
            Full per-task reports under <code>experiments/codex_gpt5_5_xhigh/</code>, <code>experiments/claude_code_opus_4_8_xhigh/</code>, and <code>experiments/panofy_claude_opus_4_6_high/</code>.
          </span>
          <span className="lang-zh">
            完整逐任务报告见 <code>experiments/codex_gpt5_5_xhigh/</code>、<code>experiments/claude_code_opus_4_8_xhigh/</code> 与 <code>experiments/panofy_claude_opus_4_6_high/</code>。
          </span>
        </p>
        <p className="note">
          <a href="blog.html#cost">
            <Lang en="Why can self-evolution cost less? Read the blog →" zh="为什么自我进化反而更省？阅读博客 →" />
          </a>
        </p>
      </div>
    </section>
  );
}

function TaskDetail({ groupId }) {
  const tasks = taskTopics[groupId] ?? [];
  const sections = useMemo(
    () => [
      ["Train", "train", "5 examples", tasks.filter((task) => task[1] === "Train")],
      ["Test", "test", "5 held-out", tasks.filter((task) => task[1] === "Test")]
    ],
    [tasks]
  );

  return (
    <div className="tg-detail" id={`task-detail-${groupId}`}>
      <div className="tg-detail-head">
        <strong>
          <Lang en="Task themes" zh="Task 主题" />
        </strong>
        <span>
          <Lang en="5 train · 5 test" zh="5 个 train · 5 个 test" />
        </span>
      </div>
      <div className="task-sets">
        {sections.map(([kind, label, count, items]) => (
          <section className={`task-set task-set-${label}`} key={kind}>
            <div className="task-set-head">
              <strong>{label}</strong>
              <span>{count}</span>
            </div>
            <div className="task-list">
              {items.map(([taskId, , title, desc]) => {
                const taskNo = String(Number(taskId.split("_")[1])).padStart(2, "0");
                return (
                  <div className="task-item" key={taskId}>
                    <span className="task-id">task {taskNo}</span>
                    <span className="task-title">{title}</span>
                    <span className="task-desc">{desc}</span>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function TasksSection() {
  const [openGroup, setOpenGroup] = useState(null);

  return (
    <section className="section band" id="tasks">
      <div className="wrap">
        <h2 className="h2">
          <Lang en="Real company interfaces — CRM, ERP, Finance." zh="真实的公司业务接口 —— CRM、ERP、Finance。" />
        </h2>
        <p className="lead">
          <span className="lang-en">
            Each group is one shared business world with lookalike records mixed in, seeded from real-job sources such as <a href={links.gdpval} target="_blank" rel="noopener noreferrer">GDPval</a> and <a href={links.sopBench} target="_blank" rel="noopener noreferrer">SOP-Bench</a>.
          </span>
          <span className="lang-zh">
            每组都是一个共享的业务世界,混入了大量"长得很像"的干扰记录;场景来自像 <a href={links.gdpval} target="_blank" rel="noopener noreferrer">GDPval</a> 和 <a href={links.sopBench} target="_blank" rel="noopener noreferrer">SOP-Bench</a> 这样的真实工作任务源。
          </span>
        </p>
        <div className="tg-table">
          <div className="tg-row tg-head">
            <span>
              <Lang en="Group" zh="编号" />
            </span>
            <span>
              <Lang en="Domain" zh="领域" />
            </span>
            <span>
              <Lang en="Business focus" zh="业务场景" />
            </span>
          </div>
          {taskGroups.map((group) => {
            const open = openGroup === group.id;
            const chip = group.domain === "Finance" ? "fin" : group.domain.toLowerCase();
            return (
              <Fragment key={group.id}>
                <button
                  type="button"
                  className={`tg-row ${open ? "is-open" : ""}`}
                  data-task-group={group.id}
                  aria-expanded={open}
                  aria-controls={`task-detail-${group.id}`}
                  onClick={() => setOpenGroup(open ? null : group.id)}
                >
                  <span className="tg-id">{group.label}</span>
                  <span>
                    <i className={`chip ${chip}`}>{group.domain}</i>
                  </span>
                  <span>
                    <Lang en={group.en} zh={group.zh} />
                  </span>
                </button>
                {open ? <TaskDetail groupId={group.id} /> : null}
              </Fragment>
            );
          })}
        </div>
        <p className="note">
          <span className="lang-en">
            How the hidden rules are planted, how the data is built and graded by agents, and why cost goes down — <a href="blog.html"><strong>read the blog →</strong></a>
          </span>
          <span className="lang-zh">
            隐藏规则怎么埋、数据怎么由 agent 构造与评分、成本为什么会下降 —— <a href="blog.html"><strong>阅读博客 →</strong></a>
          </span>
        </p>
      </div>
    </section>
  );
}

export function HomePage() {
  return (
    <main id="top">
      <Hero />
      <ResultsSection />
      <TasksSection />
    </main>
  );
}
