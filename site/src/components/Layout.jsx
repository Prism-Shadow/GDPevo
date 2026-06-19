import { BrandLogo, GitHubIcon, ThemeIcon } from "./icons.jsx";
import { homeContent } from "../content/home.js";
import { links } from "../content/links.js";
import { Lang } from "../lib/i18n.jsx";
import { themeChoices } from "../lib/theme.js";

const languageChoices = ["en", "zh"];

export function Header({ page, lang, setLang, themeChoice, setThemeChoice }) {
  const homeHref = page === "home" ? "#top" : "index.html";
  const { header } = homeContent;
  const nextThemeChoice = themeChoices[(themeChoices.indexOf(themeChoice) + 1) % themeChoices.length] ?? themeChoices[0];
  const nextLanguage = lang === "en" ? "zh" : "en";

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
              <Lang {...header.home} />
            </a>
            <a className={page === "blog" ? "is-active" : undefined} href="blog.html">
              <Lang {...header.blog} />
            </a>
          </nav>
          <div className="nav-tools">
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
            <button
              type="button"
              className="compact-toggle compact-theme-toggle"
              aria-label={`Switch to ${nextThemeChoice} theme`}
              onClick={() => setThemeChoice(nextThemeChoice)}
            >
              <ThemeIcon choice={themeChoice} />
            </button>
            <button
              type="button"
              className="compact-toggle compact-lang-toggle"
              aria-label={nextLanguage === "en" ? "Switch to English" : "Switch to Chinese"}
              onClick={() => setLang(nextLanguage)}
            >
              {lang.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  const { footer } = homeContent;

  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <div className="brand">
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </div>
        <p className="footer-tag">
          <Lang {...footer.tagline} />
        </p>
        <div className="footer-links">
          <a className="footer-link" href={links.repo} target="_blank" rel="noreferrer">{footer.repoLabel}</a>
          <p className="footer-notice">{footer.trainingNotice}</p>
        </div>
      </div>
    </footer>
  );
}
