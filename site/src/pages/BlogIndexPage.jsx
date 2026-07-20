import { blogIntro } from "../content/blog.js";
import { Lang, LocalizedMarkdown } from "../lib/i18n.jsx";

const posts = [
  {
    key: "self-evolution",
    href: "blog-self-evolution.html",
    pinned: true,
    title: blogIntro.title,
    date: blogIntro.meta.date,
    eyebrow: {
      en: "Pinned article",
      zh: "置顶文章"
    },
    summary: {
      en: "Why GDPevo evaluates agent self-evolution, how the benchmark is constructed, and what the first released evaluations show.",
      zh: "介绍 GDPevo 为什么评估 Agent 自进化、数据如何构造，以及首批公开评测结果说明了什么。"
    },
    tags: ["benchmark", "self-evolution", "business tasks"]
  },
  {
    key: "release-v2",
    href: "release-v2.html",
    title: {
      en: "GDPevo — The V2 Release",
      zh: "GDPevo — V2 版本发布"
    },
    date: {
      en: "July 17, 2026",
      zh: "2026 年 7 月 17 日"
    },
    eyebrow: {
      en: "Release note",
      zh: "版本发布说明"
    },
    summary: {
      en: "The v2 release expands GDPevo along domains, evaluated agents, and result-reading lenses including turns, heatmaps, breakdowns, and radar views.",
      zh: "V2 版本从覆盖领域、受测 Agent、结果解读视角三个方向扩展 GDPevo，并新增轮次、热力图、分数拆解和雷达图。"
    },
    tags: ["v2.0", "release", "leaderboard"]
  }
];

export function BlogIndexPage() {
  return (
    <main id="top" className="blog-page blog-index-page">
      <section className="section blog-index-hero">
        <div className="wrap narrow">
          <p className="blog-index-kicker">
            <Lang en="GDPevo Blog" zh="GDPevo 博客" />
          </p>
          <h1 className="h2 blog-title">
            <Lang en="Research notes and release updates" zh="研究笔记与版本更新" />
          </h1>
          <p className="lead">
            <Lang
              en="Read the benchmark story first, then follow new releases as GDPevo expands."
              zh="先阅读基准构建与评测故事，再查看 GDPevo 后续版本扩展。"
            />
          </p>
        </div>
      </section>

      <section className="section blog-index-list">
        <div className="wrap narrow">
          <div className="blog-post-list">
            {posts.map((post) => (
              <a className={post.pinned ? "blog-post-card is-pinned" : "blog-post-card"} href={post.href} key={post.key}>
                <div className="blog-post-meta">
                  <span>
                    <Lang {...post.eyebrow} />
                  </span>
                  <time>
                    <Lang {...post.date} />
                  </time>
                </div>
                <h2>
                  <Lang {...post.title} />
                </h2>
                <p>
                  <LocalizedMarkdown copy={post.summary} />
                </p>
                <div className="blog-post-tags" aria-label="Post tags">
                  {post.tags.map((tag) => (
                    <code key={tag}>{tag}</code>
                  ))}
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
