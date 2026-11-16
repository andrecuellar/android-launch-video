// Tests delivery/downloads/index.html with a stand-in for the "downloads" capability.
// Serve the page and its parts first, e.g.:  (cd <published folder> && python3 -m http.server 8799)
// Usage: node test-downloads.mjs
import { chromium } from "playwright-core";
import { chromiumPath } from "/PATH/TO/WORKDIR/kitconfig.mjs";
const b = await chromium.launch({ executablePath: chromiumPath() });
const p = await b.newPage();
await p.addInitScript(() => {
  window.__saved = null;
  window.claude = { use: async (n) => n === "downloads" ? { save: async ({ filename, data }) => { window.__saved = { filename, size: data.size }; return { status: "saved" }; } } : null };
});
await p.goto("http://127.0.0.1:8799/index.html");
await p.waitForTimeout(500);
const buttons = p.locator("button");
await buttons.nth(0).click();
await p.waitForFunction(() => document.querySelectorAll(".status")[0].textContent.includes("Ready") || document.querySelectorAll(".status")[0].classList.contains("error"), null, { timeout: 120000 });
console.log("status:", await p.locator(".status").nth(0).textContent());
await buttons.nth(0).click();
await p.waitForFunction(() => window.__saved !== null, null, { timeout: 10000 });
console.log("saved:", JSON.stringify(await p.evaluate(() => window.__saved)));
await b.close();
