import { BrandLogo, GitHubIcon, ThemeIcon } from "./icons.jsx";
import { Lang } from "../lib/i18n.jsx";
import { links } from "../lib/links.js";
import { themeChoices } from "../lib/theme.js";

const languageChoices = ["en", "zh"];

export function Header({ page, lang, setLang, themeChoice, setThemeChoice }) {
  const homeHref = page === "home" ? "#top" : "index.html";

  return (
    <header className="nav">
      <div className="nav-inner">
        <a className="brand" href={homeHref} aria-label="GDPevo home">
          <BrandLogo />
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </a>
        <div className="nav-right">
          <nav className="page-nav" aria-label="Primary">
            <a className={page === "home" ? "is-active" : undefined} href={homeHref}>
              <Lang en="Home" zh="首页" />
            </a>
            <a className={page === "blog" ? "is-active" : undefined} href="blog.html">
              <Lang en="Blog" zh="博客" />
            </a>
          </nav>
          <div className="theme-segment" role="group" aria-label="Color theme">
            {themeChoices.map((choice) => (
              <button
                key={choice}
                type="button"
                className={`theme-choice ${themeChoice === choice ? "is-active" : ""}`}
                data-theme-choice={choice}
                aria-label={`${choice} theme`}
                aria-pressed={themeChoice === choice}
                onClick={() => setThemeChoice(choice)}
              >
                <ThemeIcon choice={choice} />
              </button>
            ))}
          </div>
          <div className="lang-segment" role="group" aria-label="Language">
            {languageChoices.map((choice) => (
              <button
                key={choice}
                type="button"
                className={`lang-choice ${lang === choice ? "is-active" : ""}`}
                data-lang-choice={choice}
                aria-label={choice === "en" ? "English" : "Chinese"}
                aria-pressed={lang === choice}
                onClick={() => setLang(choice)}
              >
                {choice.toUpperCase()}
              </button>
            ))}
          </div>
          <a className="icon-link" href={links.repo} target="_blank" rel="noreferrer" aria-label="GitHub repository">
            <GitHubIcon />
          </a>
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <div className="brand">
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </div>
        <p className="footer-tag">
          <Lang en="Measuring agent self-evolution on GDP-worthy work." zh="在真实业务工作上衡量 Agent 的自我进化。" />
        </p>
        <a className="footer-link" href={links.repo} target="_blank" rel="noreferrer">github.com/Prism-Shadow/GDPevo</a>
      </div>
    </footer>
  );
}
