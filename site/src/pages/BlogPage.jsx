import { useEffect, useState } from "react";
import { BenchmarkFigure } from "../components/BenchmarkFigure.jsx";
import { blogBenchmark, blogConstruction, blogFindings, blogIntro, blogInvite, blogToc, blogUsage, citation } from "../content/blog.js";
import { Lang, LocalizedMarkdown, LocalizedParagraph } from "../lib/i18n.jsx";
import { links } from "../content/links.js";

function BlogIntro() {
  const [copied, setCopied] = useState(false);
  const { meta, share } = blogIntro;

  const copyBlogLink = async () => {
    const url = `${window.location.origin}${window.location.pathname}`;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
      } else {
        const input = document.createElement("textarea");
        input.value = url;
        input.setAttribute("readonly", "");
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      setCopied(false);
    }
  };

  return (
    <section className="section blog-head" id="intro">
      <div className="wrap narrow">
        <h1 className="h2 blog-title">
          <Lang {...blogIntro.title} />
        </h1>
        <div className="blog-meta">
          <span className="blog-meta-date">
            <Lang {...meta.date} />
          </span>
          <span className="blog-meta-author">{meta.author}</span>
          <button type="button" className={`blog-share-btn ${copied ? "copied" : ""}`} aria-label={share.ariaLabel} onClick={copyBlogLink}>
            <Lang {...(copied ? share.copiedLabel : share.label)} />
          </button>
        </div>
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

        <h3 className="h3 h3-spaced h3-spaced-sm" id="agent-pipeline">
          <Lang {...blogConstruction.agentHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogConstruction.pipeline} />
        </div>
        <figure className="pipeline-figure">
          <img src="assets/gdpevo-pipeline.png" alt={blogConstruction.pipelineImageAlt} loading="lazy" />
        </figure>

        <h3 className="h3 h3-spaced" id="rule-hybridization">
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

        <h3 className="h3 h3-spaced" id="rule-based-grading">
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

        <BenchmarkFigure modeLabels={{ demo: "fewshot" }} />
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
    <section className="section" id="invite">
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

function BlogToc({ activeHref }) {
  return (
    <aside className="blog-toc" aria-label="On this page">
      <strong className="blog-toc-title">
        <Lang {...blogToc.title} />
      </strong>
      <ol>
        {blogToc.items.map((item) => (
          <li className={[item.level === 2 ? "is-child" : "", activeHref === item.href ? "is-active" : ""].filter(Boolean).join(" ")} key={item.href}>
            <a href={item.href}>
              <Lang {...item.label} />
            </a>
          </li>
        ))}
      </ol>
    </aside>
  );
}

export function BlogPage() {
  const [activeHref, setActiveHref] = useState(blogToc.items[0]?.href ?? "#intro");

  useEffect(() => {
    const targets = blogToc.items
      .map((item) => [item.href, document.querySelector(item.href)])
      .filter(([, element]) => element);

    if (!targets.length) return undefined;

    let frame = 0;
    const updateActiveHref = () => {
      const offset = 120;
      const current = targets.reduce((active, [href, element]) => {
        return element.getBoundingClientRect().top <= offset ? href : active;
      }, targets[0][0]);
      setActiveHref(current);
    };
    const scheduleUpdate = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(updateActiveHref);
    };

    updateActiveHref();
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    document.addEventListener("scroll", scheduleUpdate, { capture: true, passive: true });
    window.addEventListener("resize", scheduleUpdate);
    window.addEventListener("hashchange", scheduleUpdate);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", scheduleUpdate);
      document.removeEventListener("scroll", scheduleUpdate, { capture: true });
      window.removeEventListener("resize", scheduleUpdate);
      window.removeEventListener("hashchange", scheduleUpdate);
    };
  }, []);

  return (
    <main id="top" className="blog-page">
      <BlogToc activeHref={activeHref} />
      <BlogIntro />
      <BlogConstruction />
      <BlogUsage />
      <BlogFindings />
      <BlogInvite />
    </main>
  );
}
