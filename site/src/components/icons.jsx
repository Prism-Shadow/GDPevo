import { brandLogoIcon, githubIcon, navIcons, themeIcons } from "../content/icons.js";

function SvgIcon({ icon, size }) {
  const { viewBox, width, height, fill, stroke, strokeWidth, elements } = icon;

  return (
    <svg
      viewBox={viewBox}
      width={size ?? width}
      height={size ?? height}
      fill={fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
      aria-hidden="true"
    >
      {elements.map(({ tag: Element, attrs }, index) => (
        <Element key={index} {...attrs} />
      ))}
    </svg>
  );
}

export function BrandLogo() {
  return (
    <span className="brand-logo" aria-hidden="true">
      <SvgIcon icon={brandLogoIcon} />
    </span>
  );
}

export function GitHubIcon({ size = 20 }) {
  return <SvgIcon icon={githubIcon} size={size} />;
}

export function NavIcon({ name }) {
  return <SvgIcon icon={navIcons[name] ?? navIcons.code} />;
}

export function ThemeIcon({ choice }) {
  return <SvgIcon icon={themeIcons[choice] ?? themeIcons.system} />;
}
