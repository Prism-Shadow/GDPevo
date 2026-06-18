import { cp, copyFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const dist = join(root, "dist");

await copyFile(join(root, "blog.html"), join(dist, "blog.html"));
await copyFile(join(root, "styles.css"), join(dist, "styles.css"));
await copyFile(join(root, ".nojekyll"), join(dist, ".nojekyll"));
await cp(join(root, "assets"), join(dist, "assets"), { recursive: true });
