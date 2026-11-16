// Which elements are at a point of the frame at a time: node point.mjs <16x9|9x16> <t> <x> <y>
import { createRequire } from "node:module";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, tS, xS, yS] = process.argv.slice(2);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
await page.evaluate((x) => window.seek(x), Number(tS));
const r = await page.evaluate(([x, y]) => document.elementsFromPoint(x, y).map((e) => { const cs = getComputedStyle(e); return `${e.tagName}#${e.id}.${e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className} op=${cs.opacity} bg=${cs.backgroundColor} fill=${e.getAttribute && e.getAttribute("fill")}`; }), [Number(xS), Number(yS)]);
console.log(r.join("\n"));
await browser.close(); process.exit(0);
