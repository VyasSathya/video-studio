// Record crewboard's real page frame by frame on a virtual clock, headless, at 2x, no human step.
//
//   node ui_render.mjs config.json out_dir [--rects-only]
//
// config.json: { url, width, height, scale, fps, t_end, repo, python, data,
//                events: [ {t, do: "click"|"theme"|"cli"|"call", sel, theme, args, js} ] }
// The page is crewboard's own web/index.html + app.js served by `python -m crewboard serve --demo`. Nothing in the
// page is changed; the harness only (1) freezes the page clock and its polling timers so relative times ("now",
// "25m") and the pulse do not drift during a capture that takes minutes of real time, and (2) sets every CSS
// animation's time to the film time before each screenshot. Events are applied on the frame they fall on: a click
// is a real click (puppeteer), "theme" sets the theme the way ?theme= does, "cli" runs crewboard's own command line
// against the demo task list (what an agent does), then the page's own poll(true) re-reads it.
// Writes f00000.png ... (the viewport at `scale`) and rects.json: per state, the rect of every named selector and
// every line of text and control, in CSS px (what the camera solver and the edge gate read).
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.join("C:/Dev/video-studio", "package.json"));
const puppeteer = require("puppeteer-core");

const [, , cfgPath, outDir, flag] = process.argv;
const RECTS_ONLY = flag === "--rects-only";
const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
const W = cfg.width, H = cfg.height, S = cfg.scale, FPS = cfg.fps;

function findChrome() {
  if (process.env.STUDIO_CHROME) return process.env.STUDIO_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer");
  for (const kind of ["chrome-headless-shell", "chrome"]) {
    const dir = path.join(base, kind);
    if (!fs.existsSync(dir)) continue;
    for (const v of fs.readdirSync(dir).sort().reverse())
      for (const exe of ["chrome-headless-shell-win64/chrome-headless-shell.exe", "chrome-win64/chrome.exe"]) {
        const p = path.join(dir, v, exe);
        if (fs.existsSync(p)) return p;
      }
  }
  throw new Error("no Chrome found: set STUDIO_CHROME");
}

const FREEZE = `(() => {
  const R = Date, T0 = R.now();
  function D(...a) { if (!(this instanceof D)) return new R(T0).toString(); return a.length ? new R(...a) : new R(T0); }
  D.prototype = R.prototype; D.now = () => T0; D.parse = R.parse; D.UTC = R.UTC;
  window.Date = D; window.setInterval = () => 0;
})();`;

const NAMED = ["#live", ".hubkids", "#list", ".brand", "#main", "#now", ".modebar", ".hs .thead", ".hs .tmeta",
  ".hs .ptabs", ".hs .nowline", ".hs .plan", ".hs .ags", ".now .nowtask", ".now h3", ".now .q", ".now .pgfoot",
  "#live .hubrow", "#list .gh", "#list .rrow"];

const RECTS = `(() => {
  const named = {};
  for (const s of ${JSON.stringify(NAMED)}) {
    const els = [...document.querySelectorAll(s)].filter((e) => e.getClientRects().length);
    named[s] = els.map((e) => { const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height, (e.innerText || "").slice(0, 40)]; });
  }
  const text = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode, t = n.textContent.trim();
    if (!t) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    for (const b of r.getClientRects()) if (b.width > 0 && b.height > 0) text.push([b.x, b.y, b.width, b.height, t.slice(0, 30)]);
  }
  // controls a viewer can see as a shape: an icon, or a box with a visible border or fill (not bare text buttons)
  const alpha = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return c === "transparent" ? 0 : 1;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const controls = [...document.querySelectorAll("button, .check, .sdot, .seg, .ck, input, svg, .pdot, .live")]
    .filter((e) => e.getClientRects().length)
    .filter((e) => { if (e.tagName.toLowerCase() === "svg") return true; const cs = getComputedStyle(e);
      return (parseFloat(cs.borderTopWidth) > 0 && alpha(cs.borderTopColor) > 0.02) || alpha(cs.backgroundColor) > 0.02; })
    .map((e) => { const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }).filter((b) => b[2] > 0 && b[2] < 400);
  return { theme: document.documentElement.dataset.theme || "dark", named, text, controls };
})()`;

const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true,
  args: ["--force-color-profile=srgb", "--hide-scrollbars"] });
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: S });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "dark" }]);
await page.evaluateOnNewDocument(FREEZE);
await page.goto(cfg.url, { waitUntil: "networkidle0", timeout: 60000 });
await page.evaluate(() => document.fonts.ready);
await sleep(1.0);
await page.mouse.move(W - 4, H - 4);

async function apply(ev) {
  if (ev.do === "click") {
    await page.waitForSelector(ev.sel, { timeout: 15000 });
    await page.click(ev.sel);
    await sleep(0.9);
    await page.mouse.move(W - 4, H - 4);
  } else if (ev.do === "theme") {
    await page.evaluate((th) => { document.documentElement.dataset.theme = th; }, ev.theme);
  } else if (ev.do === "cli") {
    const r = spawnSync(cfg.python, ["-m", "crewboard", ...ev.args, "--data", cfg.data], { cwd: cfg.repo, encoding: "utf8" });
    if (r.status !== 0) throw new Error("crewboard cli failed: " + r.stderr);
    console.log("cli:", ev.args.join(" "), "->", r.stdout.trim());
    await page.evaluate("poll(true)");
  } else if (ev.do === "call") {
    await page.evaluate(ev.js);
  }
  await sleep(0.5);
  await page.evaluate(() => document.fonts.ready);
}

const states = [];
async function dump(t, label) { states.push({ t, label, ...(await page.evaluate(RECTS)) }); }

const events = cfg.events.slice().sort((a, b) => a.t - b.t);
await dump(0, "start");
const n = Math.round(cfg.t_end * FPS);
let k = 0;
const t0 = Date.now();
for (let i = 0; i < n; i++) {
  const t = i / FPS;
  while (k < events.length && events[k].t <= t + 1e-6) {
    await apply(events[k]);
    await dump(events[k].t, events[k].label || events[k].do);
    k++;
  }
  if (RECTS_ONLY) continue;
  await page.evaluate((ms) => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; } }, t * 1000);
  await page.screenshot({ path: path.join(outDir, "f" + String(i).padStart(5, "0") + ".png"), type: "png", optimizeForSpeed: true });
  if (i % 60 === 0) console.log("frame", i, "/", n, ((Date.now() - t0) / 1000).toFixed(0) + "s");
}
fs.writeFileSync(path.join(outDir, "rects.json"), JSON.stringify({ width: W, height: H, scale: S, states }, null, 0));
await browser.close();
console.log(RECTS_ONLY ? "rects only" : "frames " + n, "states " + states.length);
