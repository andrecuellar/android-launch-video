// Exports, frame by frame, where the phone screen is and which frame of which recording it shows.
// Usage: node screens.mjs <16x9|9x16> <fps> <out.json>
// Needs from the film: window.screenAt() -> the 4 screen corners [[x,y] x4] or null, and
// window.sourceAt(t) -> {clip, tc, shot, fade, hidden} (read by jumps.py and stutter.py).
import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, fpsS, out] = process.argv.slice(2);
const fps = Number(fpsS);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
const dur = await page.evaluate(() => window.DUR);
const frames = await page.evaluate(async ([dur, fps]) => {
  const r = [];
  for (let i = 0; i < Math.round(dur * fps); i++) { const t = i / fps; await window.seek(t); r.push({ q: window.screenAt(), ...window.sourceAt(t) }); }
  return r;
}, [dur, fps]);
writeFileSync(out, JSON.stringify({ fps, W, H, frames }));
console.log("frames:", frames.length);
await browser.close(); process.exit(0);
