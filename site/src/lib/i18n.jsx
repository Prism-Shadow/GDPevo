import { Fragment } from "react";
import ReactMarkdown from "react-markdown";

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

const markdownComponents = {
  a({ href = "", children }) {
    const isExternal = /^https?:\/\//.test(href);
    return (
      <a href={href} {...(isExternal ? { target: "_blank", rel: "noreferrer" } : {})}>
        {children}
      </a>
    );
  },
  p({ children }) {
    return <Fragment>{children}</Fragment>;
  }
};

export function MarkdownText({ children }) {
  return (
    <ReactMarkdown components={markdownComponents}>
      {children}
    </ReactMarkdown>
  );
}

export function LocalizedMarkdown({ copy }) {
  return (
    <Lang
      en={<MarkdownText>{copy.en}</MarkdownText>}
      zh={<MarkdownText>{copy.zh}</MarkdownText>}
    />
  );
}

export function LocalizedParagraph({ copy }) {
  return (
    <p>
      <LocalizedMarkdown copy={copy} />
    </p>
  );
}
