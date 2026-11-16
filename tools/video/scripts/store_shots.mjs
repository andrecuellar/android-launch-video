// Clean film stills for the Google Play store listing: a single seek(t) per frame (no subframes: no motion
// blur) with the real recording frame of that instant.
// Usage:
//   node store_shots.mjs <16x9|9x16> - --evaluate t1 t2 ...          (visible finger, ripple and trail at each t, as JSON)
//   node store_shots.mjs <16x9|9x16> <folder> --render name:t name:t ...   (full resolution PNGs)
// Reads from the film page: elements with class .finger and .ripple, and the opacity attribute of
// the polylines (the trail).
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [format, folder, mode, ...rest] = process.argv.slice(2);
const [W, H] = format === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({
  executablePath: chromiumPath(),
  args: ["--allow-file-access-from-files", "--disable-gpu", "--font-render-hinting=none", "--disable-lcd-text"],
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on("pageerror", (e) => console.error("PAGE ERROR:", e.message));
await page.goto(`file://${ROOT}/film/index.html?f=${format}`);
await page.evaluate(() => window.READY);
const cdp = await page.context().newCDPSession(page);

if (mode === "--evaluate") {
  const out = [];
  for (const t of rest.map(Number)) {
    await page.evaluate((x) => window.seek(x), t);
    const r = await page.evaluate(() => {
      const op = (e) => parseFloat(getComputedStyle(e).opacity || "1");
      const finger = Math.max(0, ...[...document.querySelectorAll(".finger")].map(op));
      const ripple = Math.max(0, ...[...document.querySelectorAll(".ripple")].map(op));
      const trail = Math.max(0, ...[...document.querySelectorAll("polyline")].map((p) => parseFloat(p.getAttribute("opacity") || "0")));
      return { finger, ripple, trail };
    });
    out.push({ t, ...r });
  }
  console.log(JSON.stringify(out));
} else if (mode === "--render") {
  mkdirSync(folder, { recursive: true });
  for (const pair of rest) {
    const [name, ts] = pair.split(":");
    await page.evaluate((x) => window.seek(x), Number(ts));
    const r = await cdp.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(path.join(folder, `${name}.png`), Buffer.from(r.data, "base64"));
  }
  console.log(`${rest.length} frames in ${folder}`);
}
await browser.close();
process.exit(0);
