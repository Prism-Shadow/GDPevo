import { useEffect, useState } from "react";
import { Header, Footer } from "./components/Layout.jsx";
import { homeContent } from "./content/home.js";
import { BlogPage } from "./pages/BlogPage.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { initialLang, localize } from "./lib/i18n.jsx";
import { initialThemeChoice, resolveTheme } from "./lib/theme.js";

function currentPage() {
  return window.location.pathname.endsWith("/blog.html") ? "blog" : "home";
}

export default function App() {
  const [lang, setLang] = useState(initialLang);
  const [themeChoice, setThemeChoice] = useState(initialThemeChoice);
  const page = currentPage();

  useEffect(() => {
    if (!window.location.hash) return;
    requestAnimationFrame(() => {
      const id = window.location.hash.slice(1);
      document.getElementById(id)?.scrollIntoView();
    });
  }, [page]);

  useEffect(() => {
    document.body.classList.toggle("blog", page === "blog");
    document.title = localize(homeContent.documentTitle[page], lang);
  }, [page, lang]);

  useEffect(() => {
    document.documentElement.setAttribute("data-lang", lang);
    document.documentElement.setAttribute("lang", lang === "zh" ? "zh-Hans" : "en");
    try {
      localStorage.setItem("gdpevo-lang", lang);
    } catch (e) {
      // Ignore storage access errors in restricted browser contexts.
    }
  }, [lang]);

  useEffect(() => {
    const apply = () => {
      document.documentElement.setAttribute("data-theme", resolveTheme(themeChoice));
      document.documentElement.setAttribute("data-theme-choice", themeChoice);
    };
    apply();
    try {
      localStorage.setItem("gdpevo-theme", themeChoice);
    } catch (e) {
      // Ignore storage access errors in restricted browser contexts.
    }
    const mq = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
    if (!mq || themeChoice !== "system") return undefined;
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [themeChoice]);

  return (
    <>
      <Header page={page} lang={lang} setLang={setLang} themeChoice={themeChoice} setThemeChoice={setThemeChoice} />
      {page === "blog" ? <BlogPage /> : <HomePage lang={lang} />}
      <Footer />
    </>
  );
}
