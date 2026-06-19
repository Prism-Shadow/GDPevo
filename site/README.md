# GDPevo Site

This directory contains the React/Vite GitHub Pages site for GDPevo.

The landing page is rendered by React and built into `dist/` before deployment.
`blog.html` remains a static article file and is copied into the build output.

## Contents

| Path | Purpose |
| --- | --- |
| `src/` | React components and page data for the landing page. |
| `styles.css` | Shared site styling. |
| `blog.html` | Static blog article copied into `dist/` during build. |
| `scripts/postbuild.mjs` | Copies the static blog, assets, and `.nojekyll` into `dist/`. |
