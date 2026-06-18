import { useState } from "react";
import { BenchmarkFigure } from "../components/BenchmarkFigure.jsx";
import { blogBenchmark, blogConstruction, blogFindings, blogIntro, blogInvite, blogUsage, citation } from "../content/blog.js";
import { Lang, LocalizedMarkdown, LocalizedParagraph } from "../lib/i18n.jsx";
import { links } from "../content/links.js";

function BlogIntro() {
  return (
    <section className="section blog-head">
      <div className="wrap narrow">
        <h1 className="h2 blog-title">
          <Lang {...blogIntro.title} />
        </h1>
        <blockquote className="lead blog-quote">
          <LocalizedMarkdown copy={blogIntro.lead} />
        </blockquote>
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
          <LocalizedMarkdown copy={blogConstruction.lead} />
        </p>

        <h3 className="h3 h3-spaced h3-spaced-sm">
          <Lang {...blogConstruction.agentHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogConstruction.pipeline} />
        </div>
        <figure className="pipeline-figure">
          <img src="assets/gdpevo-pipeline.png" alt={blogConstruction.pipelineImageAlt} loading="lazy" />
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
          <LocalizedMarkdown copy={blogUsage.lead} />
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
                <LocalizedMarkdown copy={mode} />
              </li>
            ))}
          </ul>
        </div>

        <BenchmarkFigure />
        <p className="note">
          <LocalizedMarkdown copy={blogFindings.note} />
        </p>
        <p className="prose-link">
          <a href="index.html#results">
            <Lang {...blogBenchmark.breakdownLink} />
          </a>
        </p>
      </div>
    </section>
  );
}

function BlogInvite() {
  const [copied, setCopied] = useState(false);
  const { actions, copy } = blogInvite;

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
            <span>{actions.github}</span>
          </a>
          <a className="btn btn-ghost" href={links.experimentBoard} target="_blank" rel="noreferrer">
            <span>
              <Lang {...actions.experimentBoard} />
            </span>
          </a>
          <a className="btn btn-ghost" href={links.evalWorkspace} target="_blank" rel="noreferrer">
            <span>
              <Lang {...actions.evalWorkspace} />
            </span>
          </a>
        </div>
        <div className="bibtex">
          <button type="button" className={`copy-btn ${copied ? "copied" : ""}`} aria-label={copy.ariaLabel} onClick={copyCitation}>
            <Lang {...(copied ? copy.copiedLabel : copy.label)} />
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
