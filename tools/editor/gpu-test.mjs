// Which Chromium mode renders the film fastest on this machine: CPU, or GPU through ANGLE/GL or EGL.
// Usage: node gpu-test.mjs   (prints the WebGL renderer and the ms per screenshot of each mode)
import { chromium } from "playwright-core";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const exe = chromiumPath();
for (const [name, args] of [
  ["cpu", []],
  ["gpu-angle-gl", ["--enable-gpu", "--ignore-gpu-blocklist", "--use-gl=angle", "--use-angle=gl", "--enable-gpu-rasterization"]],
  ["gpu-egl", ["--enable-gpu", "--ignore-gpu-blocklist", "--use-gl=egl", "--enable-gpu-rasterization"]],
]) {
  try {
    const b = await chromium.launch({ executablePath: exe, args });
    const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
    await p.setContent(`<body style="margin:0"><div id=x style="width:1920px;height:1080px;background:linear-gradient(45deg,#1E5693,#2EAE6E);filter:blur(0px)"></div></body>`);
    const r = await p.evaluate(() => { const c = document.createElement("canvas").getContext("webgl"); if (!c) return "no webgl"; const e = c.getExtension("WEBGL_debug_renderer_info"); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : "no info"; });
    const t0 = Date.now();
    for (let i = 0; i < 40; i++) { await p.evaluate((i) => { document.getElementById("x").style.filter = `blur(${i % 8}px)`; document.getElementById("x").style.transform = `rotate(${i}deg) scale(1.1)`; }, i); await p.screenshot({ type: "png" }); }
    console.log(name, "|", r, "|", ((Date.now() - t0) / 40).toFixed(0), "ms per screenshot");
    await b.close();
  } catch (e) { console.log(name, "failed:", String(e).slice(0, 160)); }
}
