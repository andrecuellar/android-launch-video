// Reading windows computed with seek(t): node reading.mjs <16x9|9x16> <out.json>
// Needs from the film: window.measureReading(dt) -> [{name, best, from, to}] (best in seconds).
import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, out] = process.argv.slice(2);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on("pageerror", (e) => console.error("ERROR:", e.message));
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
const res = await page.evaluate(() => window.measureReading(1 / 60));
writeFileSync(out, JSON.stringify(res, null, 1));
for (const r of res) console.log(`${r.best.toFixed(2).padStart(5)} s  ${r.name}  [${r.from ?? "-"} to ${r.to ?? "-"}]`);
await browser.close(); process.exit(0);
