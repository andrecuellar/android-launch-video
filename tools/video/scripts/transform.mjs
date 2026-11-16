// Transform of the phone and of the camera over a range of frames: node transform.mjs <16x9|9x16> <start_frame> <end_frame>
// Reads the inline transform of #world (camera) and #phone in the film page.
import { createRequire } from "node:module";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, a, b] = process.argv.slice(2);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
for (let n = Number(a); n <= Number(b); n++) {
  await page.evaluate((x) => window.seek(x), n / 60);
  const r = await page.evaluate(() => [document.querySelector("#world").style.transform, document.querySelector("#phone").style.transform]);
  console.log(n, r[0].replace(/translate\(/g, "T(").slice(0, 70), "|", r[1].replace(/translate\(/g, "T(").slice(0, 110));
}
await browser.close(); process.exit(0);
