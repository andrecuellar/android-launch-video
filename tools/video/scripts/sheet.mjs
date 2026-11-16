// Contact sheet: node sheet.mjs <folder> <out.png> <columns> <thumbnail_width> [title]
// Takes the images of the folder in order and writes the time (from the file name) under each one.
import { createRequire } from "node:module";
import { readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const [folder, out, colS, widthS, ...title] = process.argv.slice(2);
const cols = Number(colS), width = Number(widthS);
const imgs = readdirSync(folder).filter((f) => /\.(png|jpg)$/.test(f)).sort();
const cells = imgs.map((f) => {
  const m = f.match(/t(\d+\.\d+)/); const t = m ? Number(m[1]).toFixed(2) : f;
  const extra = f.includes("-") && !m ? "" : "";
  return `<figure><img src="file://${path.resolve(folder, f)}"><figcaption>${t} s${extra}</figcaption></figure>`;
}).join("");
const html = `<!doctype html><meta charset="utf-8"><style>
body{margin:0;background:#1b1f1d;color:#e6ede8;font:600 15px/1.2 sans-serif;padding:14px;width:${cols * (width + 10) + 18}px}
h1{font-size:18px;margin:0 0 10px}
.g{display:grid;grid-template-columns:repeat(${cols},${width}px);gap:10px}
figure{margin:0}img{width:${width}px;display:block;border:1px solid #333}
figcaption{padding:3px 0 0}</style><h1>${title.join(" ")}</h1><div class="g">${cells}</div>`;
const tmp = path.join(path.dirname(out), "." + path.basename(out) + ".html");
writeFileSync(tmp, html);
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: cols * (width + 10) + 18, height: 400 } });
await page.goto(`file://${tmp}`);
await page.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); });
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log(`sheet: ${out} (${imgs.length} frames)`);
process.exit(0);
