// Prints the boxes of the overlap check at the requested times: node boxes.mjs <16x9|9x16> t...
import { createRequire } from "node:module";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, ...ts] = process.argv.slice(2);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
for (const t of ts.map(Number)) {
  await page.evaluate((x) => window.seek(x), t);
  const c = await page.evaluate((x) => window.boxes(x), t);
  console.log(`t=${t} screen=${JSON.stringify(c.screen)} bands=${JSON.stringify(c.bands.map((b) => b.box))}`);
  for (const s of c.popouts) console.log(`  P ${s.name} ${JSON.stringify(s.box)} opaque=${s.opaque} flying=${s.flying} op=${s.op}`);
  for (const x of c.texts) console.log(`  T ${x.name} ${JSON.stringify(x.box)} op=${x.op}`);
}
await browser.close(); process.exit(0);
