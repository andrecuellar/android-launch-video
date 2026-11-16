// Purity check: seek(t) must not depend on the order in which frames were requested (every render
// worker starts on a different segment). Captures the same times in ascending and in reverse order,
// in fresh pages, and compares the PNGs byte by byte.
// Usage: node purity.mjs <16x9|9x16> <folder_for_differences> [step=0.5]
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, folder, stepS] = process.argv.slice(2);
const step = Number(stepS || 0.5);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
mkdirSync(folder, { recursive: true });
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files", "--disable-gpu", "--disable-lcd-text", "--font-render-hinting=none"] });
async function capture(times) {
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
  await page.evaluate(() => window.READY);
  const r = new Map();
  for (const t of times) { await page.evaluate((x) => window.seek(x), t); r.set(t, await page.screenshot({ type: "png" })); }
  await page.close();
  return r;
}
const dur = await (async () => { const p = await browser.newPage(); await p.goto(`file://${ROOT}/film/index.html?f=${f}`); await p.evaluate(() => window.READY); const d = await p.evaluate(() => window.DUR); await p.close(); return d; })();
const times = []; for (let t = 0.12; t < dur; t += step) times.push(+t.toFixed(3));
const A = await capture(times), B = await capture([...times].reverse());
let bad = 0;
for (const t of times) {
  if (!A.get(t).equals(B.get(t))) {
    bad++;
    writeFileSync(path.join(folder, `${f}-t${t.toFixed(3)}-ascending.png`), A.get(t));
    writeFileSync(path.join(folder, `${f}-t${t.toFixed(3)}-reverse.png`), B.get(t));
  }
}
console.log(`${f}: ${times.length} times; different depending on the order: ${bad}`);
await browser.close(); process.exit(0);
