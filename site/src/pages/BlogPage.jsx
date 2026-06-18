import { useState } from "react";
import { blogConstruction, blogFindings, blogIntro, blogInvite, blogUsage, citation } from "../blogContent.jsx";
import { modes, summaryCards } from "../data.js";
import { Lang, LocalizedParagraph } from "../lib/i18n.jsx";
import { links } from "../lib/links.js";

function metricValue(value) {
  return Number.parseFloat(String(value).replace(/[^\d.-]/g, ""));
}

function BlogBenchmarkFigure() {
  return (
    <figure className="blog-benchmark-figure">
      <figcaption className="blog-benchmark-head">
        <div>
          <span>
            <Lang en="All metrics are avg@3, then averaged over 12 task groups" zh="所有指标均为 avg@3，再跨 12 个 task group 取均值" />
          </span>
        </div>
        <span className="blog-benchmark-legend" aria-label="Chart legend">
          {modes.map((mode) => (
            <i key={mode}>
              <b className={`sw sw-${mode}`} />
              {mode}
            </i>
          ))}
        </span>
      </figcaption>
      <div className="blog-benchmark-cols">
        <span>Harness</span>
        <span>Model</span>
        <span>Mode</span>
        <span>avg@3</span>
        <span>Tokens</span>
        <span>USD</span>
      </div>
      <div className="blog-benchmark-rows">
        {summaryCards.map((card) => {
          const [harness, model] = card.title.split(" · ");
          return (
            <div className="blog-benchmark-group" key={card.title}>
              <div className="blog-benchmark-name">
                <strong>{harness}</strong>
              </div>
              <div className="blog-benchmark-model">
                <strong>{model}</strong>
                <small>{card.thinking}</small>
              </div>
              <div className="blog-benchmark-bars">
                {card.rows.map((row) => (
                  <div className={`blog-benchmark-bar mode-${row.mode}`} key={row.mode}>
                    <code>{row.mode}</code>
                    <div className="blog-benchmark-measure">
                      <div className="blog-benchmark-track">
                        <span style={{ "--w": `${metricValue(row.avg)}%` }} />
                      </div>
                      <b>{row.avg}</b>
                    </div>
                    <span className="blog-benchmark-token">{row.tokens}k</span>
                    <span className="blog-benchmark-usd">${row.usd}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function BlogIntro() {
  return (
    <section className="section blog-head">
      <div className="wrap narrow">
        <h1 className="h2 blog-title">
          <Lang {...blogIntro.title} />
        </h1>
        <p className="lead">
          <Lang {...blogIntro.lead} />
        </p>
        <div className="prose">
          {blogIntro.paragraphs.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
        </div>
      </div>
    </section>
  );
}

function BlogConstruction() {
  return (
    <section className="section" id="construction">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang {...blogConstruction.heading} />
        </h2>
        <p className="lead">
          <Lang {...blogConstruction.lead} />
        </p>

        <h3 className="h3 h3-spaced h3-spaced-sm">
          <Lang {...blogConstruction.agentHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogConstruction.pipeline} />
        </div>
        <figure className="pipeline-figure">
          <img src="assets/gdpevo-pipeline.png" alt="GDPevo data pipeline: seed scenarios to multi-agent task factory to quality review to release." loading="lazy" />
        </figure>

        <h3 className="h3 h3-spaced">
          <Lang {...blogConstruction.hiddenHeading} />
        </h3>
        <div className="prose">
          {blogConstruction.hiddenRules.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
        </div>
      </div>
    </section>
  );
}

function BlogUsage() {
  return (
    <section className="section" id="usage">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang {...blogUsage.heading} />
        </h2>
        <p className="lead">
          <Lang {...blogUsage.lead} />
        </p>

        <h3 className="h3 h3-spaced">
          <Lang {...blogUsage.gradingHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogUsage.grading} />
        </div>

        <h3 className="h3 h3-spaced" id="cost">
          <Lang {...blogUsage.costHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogUsage.cost} />
        </div>
      </div>
    </section>
  );
}

function BlogFindings() {
  return (
    <section className="section" id="findings">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang {...blogFindings.heading} />
        </h2>
        <div className="prose">
          {blogFindings.intro.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
          <ul className="bullets">
            {blogFindings.modes.map((mode) => (
              <li key={mode.key}>
                <Lang en={mode.en} zh={mode.zh} />
              </li>
            ))}
          </ul>
        </div>

        <BlogBenchmarkFigure />
        <p className="note">
          <Lang {...blogFindings.note} />
        </p>
        <p className="prose-link">
          <a href="index.html#results">
            <Lang en="See the per-group breakdown on the homepage →" zh="在首页查看逐组的明细 →" />
          </a>
        </p>
      </div>
    </section>
  );
}

function BlogInvite() {
  const [copied, setCopied] = useState(false);

  const copyCitation = async () => {
    if (!navigator.clipboard) return;
    await navigator.clipboard.writeText(citation);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="section band" id="invite">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang {...blogInvite.heading} />
        </h2>
        <div className="prose">
          <LocalizedParagraph copy={blogInvite.paragraph} />
        </div>
        <div className="btn-row invite-actions">
          <a className="btn btn-dark" href={links.repo} target="_blank" rel="noreferrer">
            <span>GitHub</span>
          </a>
          <a className="btn btn-ghost" href={links.experimentBoard} target="_blank" rel="noreferrer">
            <span>
              <Lang en="Experiment board" zh="实验看板" />
            </span>
          </a>
          <a className="btn btn-ghost" href={links.evalWorkspace} target="_blank" rel="noreferrer">
            <span>
              <Lang en="Eval workspace" zh="评估工作区" />
            </span>
          </a>
        </div>
        <div className="bibtex">
          <button type="button" className={`copy-btn ${copied ? "copied" : ""}`} aria-label="Copy citation" onClick={copyCitation}>
            <Lang en={copied ? "Copied" : "Copy"} zh={copied ? "已复制" : "复制"} />
          </button>
          <pre><code>{citation}</code></pre>
        </div>
      </div>
    </section>
  );
}

export function BlogPage() {
  return (
    <main id="top">
      <BlogIntro />
      <BlogConstruction />
      <BlogUsage />
      <BlogFindings />
      <BlogInvite />
    </main>
  );
}
