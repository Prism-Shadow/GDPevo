export function initialLang() {
  try {
    const saved = localStorage.getItem("gdpevo-lang");
    if (saved === "en" || saved === "zh") return saved;
  } catch (e) {
    // Ignore storage access errors in restricted browser contexts.
  }
  return navigator.language && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

export function Lang({ en, zh }) {
  return (
    <>
      <span className="lang-en">{en}</span>
      <span className="lang-zh">{zh}</span>
    </>
  );
}

export function LocalizedParagraph({ copy }) {
  return (
    <p>
      <Lang en={copy.en} zh={copy.zh} />
    </p>
  );
}
