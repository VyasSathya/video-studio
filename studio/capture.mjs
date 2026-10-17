// Capture real product states as stills, with where each feature sits on screen, headless, no human step.
//
//   node studio/capture.mjs capture.json out_dir
//
// capture.json: { "url": "...", "width": 1440, "height": 900, "scale": 2, "colorScheme": "dark",
//   "shots": [ { "name": "board", "steps": [ {"click": "[data-x]"}, {"wait": 0.6}, {"eval": "..."} ],
//                "focus": "#tasks", "cursor": "[data-x]" } ] }
// Steps run in order on one page, so a shot starts from the state the last one left. Each shot writes
// <name>.png (the full viewport at `scale`) and an entry in shots.json with "focus" and "cursor" as
// [x, y, w, h] in image pixels, read from the live DOM (never guessed).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import puppeteer from "puppeteer-core";

const [, , cfgPath, outDir] = process.argv;
if (!cfgPath || !outDir) { console.error("usage: node studio/capture.mjs capture.json out_dir"); process.exit(2); }
const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
const W = cfg.width || 1440, H = cfg.height || 900, S = cfg.scale || 2;

function findChrome() {
  if (process.env.STUDIO_CHROME) return process.env.STUDIO_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer");
  for (const kind of ["chrome-headless-shell", "chrome"]) {
    const dir = path.join(base, kind);
    if (!fs.existsSync(dir)) continue;
    for (const v of fs.readdirSync(dir).sort().reverse())
      for (const exe of ["chrome-headless-shell-win64/chrome-headless-shell.exe", "chrome-win64/chrome.exe",
                         "chrome-headless-shell-linux64/chrome-headless-shell", "chrome-headless-shell-mac-arm64/chrome-headless-shell"]) {
        const p = path.join(dir, v, exe);
        if (fs.existsSync(p)) return p;
      }
  }
  throw new Error("no Chrome found: set STUDIO_CHROME");
}

const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ["--force-color-profile=srgb"] });
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: S });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: cfg.colorScheme || "light" }]);
await page.goto(cfg.url, { waitUntil: "networkidle0", timeout: 60000 });
await sleep(cfg.settle || 1.0);

async function rect(sel) {
  if (!sel) return null;
  const r = await page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return [b.x, b.y, b.width, b.height];
  }, sel);
  return r ? r.map((v) => Math.round(v * S)) : null;
}

const out = { width: W * S, height: H * S, scale: S, shots: [] };
for (const shot of cfg.shots) {
  for (const st of shot.steps || []) {
    if (st.click) { await page.waitForSelector(st.click, { timeout: 15000 }); await page.click(st.click); await sleep(st.after ?? 0.6); }
    if (st.wait) await sleep(st.wait);
    if (st.eval) { await page.evaluate(st.eval); await sleep(st.after ?? 0.3); }
  }
  const file = path.join(outDir, shot.name + ".png");
  await page.screenshot({ path: file });
  const f = await rect(shot.focus);
  if (shot.focus && !f) throw new Error("focus selector not found: " + shot.focus);
  out.shots.push({ name: shot.name, file: path.resolve(file), focus: f, cursor: await rect(shot.cursor) });
  console.log("captured", shot.name, f ? f.join(",") : "");
}
fs.writeFileSync(path.join(outDir, "shots.json"), JSON.stringify(out, null, 1));
await browser.close();
