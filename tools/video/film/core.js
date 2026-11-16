// Pure core: everything is a function of time. No state between frames except DOM caches.
"use strict";

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, p) => a + (b - a) * p;
const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const easeOut = (x) => 1 - Math.pow(1 - clamp(x), 3);
const easeIn = (x) => Math.pow(clamp(x), 3);
const easeInOut = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };

// Step response of a damped spring, from 0 to 1, in closed form.
function stepR(tau, sp) {
  if (tau <= 0) return 0;
  const { w, z } = sp;
  if (z >= 1) { const x = w * tau; return 1 - Math.exp(-x) * (1 + x); }
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * tau) * (Math.cos(wd * tau) + (z * w / wd) * Math.sin(wd * tau));
}
// Named springs. w in rad/s; z = damping ratio (1 = critical).
const R = {
  camera: { w: 9, z: 1 },
  cameraFast: { w: 15, z: 1 },
  whip: { w: 22, z: 1 },
  text: { w: 24, z: 1 },
  soft: { w: 13, z: 1 },
  firm: { w: 20, z: 1 },
  pop: { w: 19, z: 0.82 },
  popFirm: { w: 26, z: 0.84 },
  slow: { w: 7, z: 1 },
  hit: { w: 30, z: 0.72 },
  edge: { w: 34, z: 0.9 },     // leading edge
  edgeSoft: { w: 17, z: 0.9 }, // trailing edge
  app: { w: 2 * Math.PI / 0.35, z: 1 }, // the app's own firm spring (example value: match your app)
};

// A value that changes target many times: the sum of one spring per change.
class Track {
  constructor(v0) { this.v0 = v0; this.cur = v0; this.ev = []; }
  to(t, v, sp = R.soft) { if (v !== this.cur) { this.ev.push([t, v - this.cur, sp]); this.cur = v; } return this; }
  at(t) { let v = this.v0; for (const [ti, d, sp] of this.ev) v += d * stepR(t - ti, sp); return v; }
  vel(t) { const h = 1 / 480; return (this.at(t + h) - this.at(t - h)) / (2 * h); }
}

// Spring entrance and a short, early exit, with blur.
function vis(t, tin, tout, dOut = 0.13, sp = R.text) {
  const e = stepR(t - tin, sp);
  const x = tout == null ? 0 : clamp((t - tout) / dOut);
  const xo = x * x;
  return { o: e * (1 - xo), b: (1 - e) * 10 + xo * 12, dy: (1 - e) * 18 - xo * 12, e, x };
}
function applyVis(el, v, extra = "") {
  el.style.opacity = v.o.toFixed(4);
  el.style.filter = v.b > 0.05 ? `blur(${v.b.toFixed(2)}px)` : "none";
  el.style.transform = `translateY(${v.dy.toFixed(2)}px) ${extra}`;
}

// ---------- Sound effect registry (single source of truth) ----------
// The film exports it as window.CUES; audio.py reads it through `snap.mjs ... --cues out.json`.
const CUES = [];
function cue(t, type, extra = {}) { CUES.push({ t: +t.toFixed(4), type, ...extra }); }

// ---------- DOM utilities ----------
const $ = (s, r = document) => r.querySelector(s);
function el(tag, cls, parent, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  if (parent) parent.appendChild(e);
  return e;
}
function setStyle(e, props) { for (const k in props) e.style[k] = props[k]; }

// ---------- Locale number format (decimal comma, thousands dot) ----------
function fmt(v, dec) {
  const s = v.toFixed(dec);
  let [whole, frac] = s.split(".");
  whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return frac ? `${whole},${frac}` : whole;
}

// ---------- Odometer: one strip per digit, clipped only vertically ----------
// Template: final text with digits (e.g. "1.250" or "12,50"). Digits move only while the one
// below carries; separators stay fixed.
class Odometer {
  constructor(parent, { cls = "", dec = 0, maxDig = 5, width = null } = {}) {
    this.dec = dec;
    this.root = el("span", "odo " + cls, parent);
    this.slots = [];
    this.maxDig = maxDig;
    this.cache = "";
  }
  // Builds the slots for a given number of integer digits.
  build(intDig) {
    const key = String(intDig);
    if (this.cache === key) return;
    this.cache = key;
    this.root.innerHTML = "";
    this.slots = [];
    const total = intDig + this.dec;
    for (let i = 0; i < total; i++) {
      const pos = total - 1 - i; // power of 10 (decimals included)
      const intPos = pos - this.dec;
      if (i > 0 && intPos >= 0 && (intPos + 1) % 3 === 0) el("span", "odo-sep", this.root, ".");
      if (this.dec > 0 && pos === this.dec - 1) el("span", "odo-sep", this.root, ",");
      const s = el("span", "odo-slot", this.root);
      const strip = el("span", "odo-strip", s, "0<br>1<br>2<br>3<br>4<br>5<br>6<br>7<br>8<br>9<br>0");
      this.slots.push({ s, strip, pos });
    }
  }
  // v: real value (e.g. 12.5). Scaled to an integer according to the decimals.
  set(v, intDig) {
    this.build(intDig);
    const n = v * Math.pow(10, this.dec);
    for (const { strip, pos } of this.slots) {
      const p10 = Math.pow(10, pos);
      const base = Math.floor(n / p10) % 10;
      const rest = n % p10;
      const carry = pos === 0 ? (n - Math.floor(n)) : Math.max(0, rest - (p10 - 1));
      const d = base + clamp(carry);
      strip.style.transform = `translateY(${(-d * 10).toFixed(3)}%)`;
    }
  }
}

// ---------- Path interpolation (polylines of the same length) ----------
function mixPoints(a, b, p) { return a.map((q, i) => [lerp(q[0], b[i][0], p), lerp(q[1], b[i][1], p)]); }
// Smooth curve through the points (Catmull-Rom to Bezier).
function curve(pts) {
  if (pts.length < 2) return "";
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}
