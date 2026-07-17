import { Fragment, useMemo, useState } from "react";
import { BenchmarkFigure } from "../components/BenchmarkFigure.jsx";
import { TaskGroupRadar } from "../components/TaskGroupRadar.jsx";
import { GitHubIcon, NavIcon } from "../components/icons.jsx";
import { homeContent } from "../content/home.js";
import { Lang, LocalizedMarkdown } from "../lib/i18n.jsx";
import { links } from "../content/links.js";
import { taskGroups, taskTopics } from "../content/benchmark.js";

function Hero() {
  const { title, subtitle, meta, actions, stats } = homeContent.hero;

  return (
    <section className="hero">
      <div className="hero-glow" aria-hidden="true" />
      <div className="wrap hero-inner">
        <h1 className="hero-title">
          <span className="lang-en">
            <span className="accent">{title.brand}</span>: {title.en[0]}
            <br className="hero-break" />
            {" "}{title.en[1]}
          </span>
          <span className="lang-zh">
            <span className="accent">{title.brand}</span>：{title.zh[0]}
            <br className="hero-break" />
            {title.zh[1]}
          </span>
        </h1>
        <p className="hero-sub">
          <LocalizedMarkdown copy={subtitle} />
        </p>
        <p className="hero-meta">
          <Lang {...meta} />
        </p>
        <div className="btn-row">
          <a className="btn btn-dark" href={links.repo} target="_blank" rel="noreferrer">
            <GitHubIcon size={17} />
            <span>{actions.github}</span>
          </a>
          <a className="btn btn-ghost" href="#results">
            <NavIcon name="chart" />
            <span>
              <Lang {...actions.results} />
            </span>
          </a>
          <a className="btn btn-ghost" href="blog.html">
            <NavIcon name="blog" />
            <span>
              <Lang {...actions.blog} />
            </span>
          </a>
          <a className="btn btn-ghost" href={links.experimentBoard} target="_blank" rel="noreferrer">
            <NavIcon name="code" />
            <span>
              <Lang {...actions.experimentBoard} />
            </span>
          </a>
        </div>
        <div className="stat-band">
          {stats.map((stat) => (
            <div className={`stat ${stat.positive ? "stat-pos" : ""}`} key={stat.key}>
              <span className="stat-num">
                {stat.value}{stat.unit ? <i>{stat.unit}</i> : null}
              </span>
              <span className="stat-label">
                <Lang {...stat.label} />
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ResultsSection({ lang }) {
  const { results } = homeContent;

  return (
    <section className="section" id="results">
      <div className="wrap results-wrap">
        <h2 className="h2">
          <LocalizedMarkdown copy={results.heading} />
        </h2>
        <p className="lead">
          <LocalizedMarkdown copy={results.lead} />
        </p>
        <BenchmarkFigure className="results-benchmark-figure" variant="leaderboard" />
        <TaskGroupRadar lang={lang} />
        {results.notes.map((note) => (
          <p className="note" key={note.key}>
            <LocalizedMarkdown copy={note} />
          </p>
        ))}
        <p className="note">
          <a href="blog-self-evolution.html#cost">
            <Lang {...results.blogLink} />
          </a>
        </p>
      </div>
    </section>
  );
}

function TaskDetail({ groupId }) {
  const { detail } = homeContent.tasks;
  const tasks = taskTopics[groupId] ?? [];
  const sections = useMemo(
    () => detail.sets.map((section) => [
      section.label,
      section.count,
      tasks.filter((task) => task.kind === section.kind)
    ]),
    [detail.sets, tasks]
  );

  return (
    <div className="tg-detail" id={`task-detail-${groupId}`}>
      <div className="tg-detail-head">
        <strong>
          <Lang {...detail.heading} />
        </strong>
        <span>
          <Lang {...detail.count} />
        </span>
      </div>
      <div className="task-sets">
        {sections.map(([label, count, items]) => (
          <section className={`task-set task-set-${label}`} key={label}>
            <div className="task-set-head">
              <strong>{label}</strong>
              <span>{count}</span>
            </div>
            <div className="task-list">
              {items.map(({ id: taskId, title, desc }) => {
                const taskNo = String(Number(taskId.split("_")[1])).padStart(2, "0");
                return (
                  <div className="task-item" key={taskId}>
                    <span className="task-id">{detail.taskPrefix} {taskNo}</span>
                    <span className="task-title">
                      <Lang {...title} />
                    </span>
                    <span className="task-desc">
                      <Lang {...desc} />
                    </span>
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
  const { tasks } = homeContent;

  return (
    <section className="section band" id="tasks">
      <div className="wrap">
        <h2 className="h2">
          <LocalizedMarkdown copy={tasks.heading} />
        </h2>
        <p className="lead">
          <LocalizedMarkdown copy={tasks.lead} />
        </p>
        <div className="tg-table">
          <div className="tg-row tg-head">
            <span>
              <Lang {...tasks.tableColumns.group} />
            </span>
            <span>
              <Lang {...tasks.tableColumns.domain} />
            </span>
            <span>
              <Lang {...tasks.tableColumns.focus} />
            </span>
          </div>
          {taskGroups.map((group) => {
            const open = openGroup === group.id;
            const chip = group.domainKey ?? (group.domain === "Finance" ? "fin" : group.domain.toLowerCase());
            const domainLabel = group.domainLabel ?? { en: group.domain, zh: group.domain };
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
                    <i className={`chip ${chip}`}>
                      <Lang {...domainLabel} />
                    </i>
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
          <LocalizedMarkdown copy={tasks.note} />
        </p>
      </div>
    </section>
  );
}

export function HomePage({ lang = "en" }) {
  return (
    <main id="top">
      <Hero />
      <ResultsSection lang={lang} />
      <TasksSection />
    </main>
  );
}
