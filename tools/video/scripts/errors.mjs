// Loads the film and steps through time looking for page errors: node errors.mjs <16x9|9x16> [step=0.25]
import { createRequire } from "node:module";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, stepS] = process.argv.slice(2); const step = Number(stepS || 0.25);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message)); page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("requestfailed", (r) => errors.push("failed to load: " + r.url()));
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
const dur = await page.evaluate(() => window.DUR);
for (let t = 0; t <= dur; t += step) { await page.evaluate((x) => window.seek(x), t); }
console.log(f, "errors:", errors.length ? [...new Set(errors)].slice(0, 10).join(" | ") : "none");
await browser.close(); process.exit(0);
