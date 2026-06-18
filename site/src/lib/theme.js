export const themeChoices = ["light", "dark", "system"];

export function initialThemeChoice() {
  try {
    const saved = localStorage.getItem("gdpevo-theme");
    if (themeChoices.includes(saved)) return saved;
  } catch (e) {
    // Ignore storage access errors in restricted browser contexts.
  }
  return "system";
}

export function resolveTheme(choice) {
  if (choice !== "system") return choice;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
