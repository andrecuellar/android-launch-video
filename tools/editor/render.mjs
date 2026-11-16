// Simple renderer: renders scene.html (next to this file, not bundled: write your own) frame by
// frame with the given plan and encodes the MP4. The production render is video/scripts/final2.sh.
// Usage: node render.mjs plan.json out.mp4            (full video)
//        node render.mjs plan.json sample.png 3.5 9 14 (single frames, in seconds)
// scene.html must expose window.loadPlan(plan) and window.seek(t); plan.json has "duration" and
// an optional "audio" path.
import { chromium } from "playwright-core";
import { readFileSync, mkdirSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";

const DIR = path.dirname(new URL(import.meta.url).pathname);
const [planPath, output, ...singles] = process.argv.slice(2);
const plan = JSON.parse(readFileSync(planPath, "utf8"));
const FPS = 30;
const total = plan.duration;

const browser = await chromium.launch({
  executablePath: chromiumPath(),
  args: ["--allow-file-access-from-files"],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(`file://${DIR}/scene.html`);
await page.evaluate((p) => window.loadPlan(p), plan);

if (singles.length) {
  for (const [i, s] of singles.entries()) {
    await page.evaluate((t) => window.seek(t), Number(s));
    await page.screenshot({ path: output.replace(/\.png$/, `-${i}.png`) });
  }
} else {
  const frames = path.join(DIR, "frames");
  rmSync(frames, { recursive: true, force: true });
  mkdirSync(frames);
  const n = Math.round(total * FPS);
  for (let f = 0; f < n; f++) {
    await page.evaluate((t) => window.seek(t), f / FPS);
    await page.screenshot({ path: path.join(frames, `${String(f).padStart(5, "0")}.jpg`), type: "jpeg", quality: 95 });
    if (f % 60 === 0) process.stdout.write(`${f}/${n}\n`);
  }
  const input = ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(frames, "%05d.jpg")];
  const audio = plan.audio ? ["-i", plan.audio, "-shortest", "-c:a", "aac", "-b:a", "192k"] : [];
  execFileSync("ffmpeg", [...input, ...audio, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", output], { stdio: "inherit" });
}
await browser.close();
