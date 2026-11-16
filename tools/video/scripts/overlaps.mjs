// Overlap check: at every beat and at +-0.1 s, crosses the boxes of what pops out of the screen, the
// phone screen and the texts. Flags: everything that pops out without its own opaque surface (whether
// it covers something or not); an element without an opaque background that covers something; a card
// standing still over the screen or touching the phone; a card over another card; a card or a text
// over another text; a text over the screen (except where the solid 9:16 header separates them).
// Usage: node overlaps.mjs <16x9|9x16> [out.json] [extra_step]   (OVERLAPS_TIMES="t1,t2" checks only those instants)
import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const require = createRequire("/PATH/TO/WORKDIR/editor/");
const { chromium } = require("playwright-core");
const ROOT = "/PATH/TO/WORKDIR/video";
const [f, out, extraS] = process.argv.slice(2);
const [W, H] = f === "9x16" ? [1080, 1920] : [1920, 1080];
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${ROOT}/film/index.html?f=${f}`);
await page.evaluate(() => window.READY);
const dur = await page.evaluate(() => window.DUR);
const times = new Set();
for (let k = 0; k * 0.5 <= dur + 1e-9; k++) for (const d of [-0.1, 0, 0.1]) { const t = +(k * 0.5 + d).toFixed(3); if (t >= 0 && t <= dur) times.add(t); }
if (extraS) for (let t = 0; t <= dur; t += Number(extraS)) times.add(+t.toFixed(3));
// OVERLAPS_TIMES="t1,t2,..." checks only those instants (e.g. the store listing screenshots)
if (process.env.OVERLAPS_TIMES) { times.clear(); for (const x of process.env.OVERLAPS_TIMES.split(",")) times.add(+Number(x).toFixed(4)); }
const list = [...times].sort((a, b) => a - b);
const inter = (a, b) => (!a || !b) ? 0 : Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) * Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
const grow = (c, m) => [c[0] - m, c[1] - m, c[2] + m, c[3] + m];
const outside = (a, b) => { // area of a outside b (b is a band: a rectangle)
  const i = inter(a, b); return (a[2] - a[0]) * (a[3] - a[1]) - i;
};
const group = (n) => n.replace(/ (line|word) \d+$/, "").replace(/, word \d+$/, "");
const marks = [], wanted = [], centered = [];
// point inside a polygon (horizontal ray)
const inside = (x, y, poly) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const [xi, yi] = poly[i], [xj, yj] = poly[j]; if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c; } return c; };
const coversRibbon = (box, ribbons) => { for (let a = 0; a <= 12; a++) for (let b = 0; b <= 5; b++) { const x = box[0] + ((box[2] - box[0]) * a) / 12, y = box[1] + ((box[3] - box[1]) * b) / 5; for (const c of ribbons) if (inside(x, y, c.poly)) return c.k; } return null; };
// Wanted overlaps: the ones the script asks for (for example, a figure that flies from one place to another).
// Each one: { kind, who: /regex over the box name/, reason }. Everything else is flagged.
const WANTED = [];
for (const t of list) {
  await page.evaluate((x) => window.seek(x), t);
  const c = await page.evaluate((x) => window.boxes(x), t);
  const P = c.screen, Pm = P && grow(P, 14);
  const M = (kind, who, detail = "") => { const z = WANTED.find((x) => x.kind === kind && x.who.test(who)); (z ? wanted : marks).push({ t, kind, who, detail: z ? z.reason : detail }); };
  for (const s of c.popouts) {
    if (!s.box) continue;
    if (!s.opaque) M("pops out of the screen without an opaque surface", s.name); // rule 1: even if it covers nothing
    if (P) {
      const ip = inter(s.box, P), im = inter(s.box, Pm);
      if (!s.opaque && im > 200) M("no background over the phone", s.name);
      else if (s.opaque && ip > 200 && !s.flying) M("card standing still over the screen", s.name, `${Math.round(ip)} px²`);
      else if (s.opaque && im > 0 && !s.flying) M("card touching the phone", s.name);
    }
  }
  for (let i = 0; i < c.popouts.length; i++) for (let j = i + 1; j < c.popouts.length; j++) {
    const a = c.popouts[i], b = c.popouts[j]; if (a.name === b.name) continue; const ii = inter(a.box, b.box);
    if (ii <= 200) continue;
    if (!a.opaque || !b.opaque) M("no background over another card", `${a.name} / ${b.name}`);
    else if (!a.flying && !b.flying) M("card over card", `${a.name} / ${b.name}`, `${Math.round(ii)} px²`);
  }
  for (const x of c.texts) {
    for (const s of c.popouts) if (inter(x.box, s.box) > 40) M("card over text", `${s.name} / ${x.name}`, s.flying ? "flying" : "still");
    if (P && inter(x.box, Pm) > 100) {
      const covered = c.bands.some((b) => outside(x.box, b.box) < 1);
      if (!covered) M("text over the phone", x.name);
    }
  }
  // opening: no text without its own surface over a ribbon
  if (c.ribbons && c.ribbons.length) for (const x of c.texts) { const k = coversRibbon(x.box, c.ribbons); if (k) M("text over a ribbon", `${x.name} / ribbon ${k}`); }
  // opening: centered on the axis (only on still frames: the box does not move in the next frame)
  if (c.center && t <= 4.0) {
    await page.evaluate((x) => window.seek(x), t + 1 / 60);
    const d = await page.evaluate((x) => window.boxes(x), t + 1 / 60);
    for (const e of c.center.elements) {
      const e2 = d.center && d.center.elements.find((q) => q.name === e.name);
      if (!e2 || e.box.some((v, i) => Math.abs(v - e2.box[i]) > 0.5)) continue; // it is moving
      const cx = (e.box[0] + e.box[2]) / 2;
      if (Math.abs(cx - c.center.axis) > 4) M("off the axis", e.name, `center ${cx.toFixed(1)} (axis ${c.center.axis})`);
      else centered.push({ t, name: e.name, dx: +(cx - c.center.axis).toFixed(1) });
    }
  }
  for (let i = 0; i < c.texts.length; i++) for (let j = i + 1; j < c.texts.length; j++) {
    const a = c.texts[i], b = c.texts[j];
    if (group(a.name) === group(b.name)) continue;
    if (inter(a.box, b.box) > 20) M("text over text", `${a.name} / ${b.name}`);
  }
}
// group by kind and elements, with the times
const g = new Map();
for (const m of marks) { const k = m.kind + " | " + m.who; if (!g.has(k)) g.set(k, { kind: m.kind, who: m.who, t: [], detail: m.detail }); g.get(k).t.push(m.t); }
console.log(`${f}: ${list.length} times checked; flags: ${marks.length} in ${g.size} groups; wanted overlaps: ${wanted.length}`);
const gb = new Map(); for (const m of wanted) { const k = m.kind + " | " + m.who; if (!gb.has(k)) gb.set(k, { ...m, t: [] }); gb.get(k).t.push(m.t); }
for (const v of gb.values()) console.log(`  (wanted) ${v.kind}: ${v.who}  [${v.t.map((x) => x.toFixed(2)).join(", ")}]  ${v.detail}`);
for (const v of g.values()) console.log(`  ${v.kind}: ${v.who}  [${v.t.slice(0, 12).map((x) => x.toFixed(2)).join(", ")}${v.t.length > 12 ? ", …" : ""}]${v.detail ? "  " + v.detail : ""}`);
if (centered.length) {
  const by = {}; for (const q of centered) (by[q.name] = by[q.name] || []).push(q.dx);
  console.log("  centering (still frames from 0 to 4 s): " + Object.entries(by).map(([n, v]) => `${n}: ${v.length} frames, max offset ${Math.max(...v.map(Math.abs)).toFixed(1)} px`).join("; "));
}
if (out) writeFileSync(out, JSON.stringify([...g.values()], null, 1));
await browser.close(); process.exit(0);
