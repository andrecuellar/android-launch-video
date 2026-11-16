// Single film frames. Usage:
//   node snap.mjs <16x9|9x16> <folder> <scale> <png|jpg> t1 t2 ...
//   node snap.mjs <16x9|9x16> <folder> <scale> <png|jpg> --beats          (t = k*0.5 + 0.12)
//   node snap.mjs <16x9|9x16> <folder> <scale> <png|jpg> --list file      (one time per line)
//   node snap.mjs 16x9 - 1 png --cues out.json                            (exports the sound cues)
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");

const ROOT = "/PATH/TO/WORKDIR/video";
const [format, folder, scaleS, kind, ...rest] = process.argv.slice(2);
const scale = Number(scaleS);
const [W, H] = format === "9x16" ? [1080, 1920] : [1920, 1080];

const browser = await chromium.launch({
  executablePath: chromiumPath(),
  args: ["--allow-file-access-from-files", "--disable-gpu", "--font-render-hinting=none", "--disable-lcd-text"],
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));
await page.goto(`file://${ROOT}/film/index.html?f=${format}`);
await page.evaluate(() => window.READY);
const cdp = await page.context().newCDPSession(page);

if (rest[0] === "--cues") {
  const cues = await page.evaluate(() => window.CUES);
  writeFileSync(rest[1], JSON.stringify(cues, null, 1));
  console.log("cues:", cues.length);
  await browser.close(); process.exit(0);
}

let times;
if (rest[0] === "--beats") { const dur = await page.evaluate(() => window.DUR); times = []; for (let k = 0; k * 0.5 + 0.12 < dur; k++) times.push(+(k * 0.5 + 0.12).toFixed(3)); }
else if (rest[0] === "--list") times = readFileSync(rest[1], "utf8").split(/\s+/).filter(Boolean).map(Number);
else times = rest.map(Number);

mkdirSync(folder, { recursive: true });
for (const t of times) {
  await page.evaluate((x) => window.seek(x), t);
  const r = await cdp.send("Page.captureScreenshot", kind === "png" ? { format: "png" } : { format: "jpeg", quality: 95, optimizeForSpeed: true });
  const name = `${format}-t${t.toFixed(3).padStart(7, "0")}.${kind === "png" ? "png" : "jpg"}`;
  writeFileSync(path.join(folder, name), Buffer.from(r.data, "base64"));
}
console.log(`${times.length} frames in ${folder}`);
await browser.close();
process.exit(0);
