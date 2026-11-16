// Renders a contiguous segment of film frames (one browser per process).
// Usage: node segment.mjs <16x9|9x16> <scale> <fps> <subframes> <start_frame> <end_frame> <folder>
// With subframes = 4: subT(i) = floor(i/4)/fps + ((i%4) - 1.5)/(4*fps)  (centered on the frame).
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [format, scaleS, fpsS, subS, startS, endS, folder] = process.argv.slice(2);
const scale = Number(scaleS), fps = Number(fpsS), sub = Number(subS), start = Number(startS), end = Number(endS);
const [W, H] = format === "9x16" ? [1080, 1920] : [1920, 1080];
mkdirSync(folder, { recursive: true });

async function open() {
  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: ["--allow-file-access-from-files", "--disable-gpu", "--disable-lcd-text", "--font-render-hinting=none"],
  });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
  page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));
  await page.goto(`file://${ROOT}/film/index.html?f=${format}`);
  await page.evaluate(() => window.READY);
  const cdp = await page.context().newCDPSession(page);
  return { browser, page, cdp };
}
let s = await open();
const total = (end - start) * sub;
for (let k = 0; k < total; k++) {
  const i = start * sub + k;
  const name = path.join(folder, `s${String(i).padStart(6, "0")}.jpg`);
  if (existsSync(name)) continue;
  const t = sub === 1 ? i / fps : Math.floor(i / sub) / fps + ((i % sub) - (sub - 1) / 2) / (sub * fps);
  for (let attempt = 0; ; attempt++) {
    try {
      await s.page.evaluate((x) => window.seek(Math.max(0, x)), t);
      const r = await s.cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 95, optimizeForSpeed: true });
      writeFileSync(name, Buffer.from(r.data, "base64"));
      break;
    } catch (e) {
      console.error(`retry ${attempt + 1} at t=${t}: ${e.message}`);
      if (attempt >= 3) throw e;
      try { await s.browser.close(); } catch {}
      s = await open();
    }
  }
}
await s.browser.close().catch(() => {});
process.exit(0);
