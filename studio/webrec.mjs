// Record a scripted walk through a web page as an mp4, headless, no human step.
//
//   node studio/webrec.mjs shot.json out.mp4
//
// shot.json: { "url": "...", "width": 1600, "height": 1000, "scale": 1, "colorScheme": "dark", "fps": 30,
//              "cursor": true, "steps": [ {"do":"wait","s":1}, {"do":"move","sel":"[data-x]","s":0.7},
//              {"do":"click","sel":"..."}, {"do":"type","sel":"input","text":"hi"}, {"do":"key","key":"Enter"},
//              {"do":"scroll","sel":"#list","dy":400,"s":0.8}, {"do":"eval","js":"..."} ] }
// A move eases the drawn cursor to the element's center; click moves there first if it is not already there.
// Frames come from Chrome's screencast (one per paint, with timestamps) and are laid on a constant-fps clock.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import puppeteer from "puppeteer-core";

const [, , shotPath, outPath] = process.argv;
if (!shotPath || !outPath) { console.error("usage: node studio/webrec.mjs shot.json out.mp4"); process.exit(2); }
const shot = JSON.parse(fs.readFileSync(shotPath, "utf8"));
const W = shot.width || 1600, H = shot.height || 1000, SCALE = shot.scale || 1, FPS = shot.fps || 30;

function findChrome() {
  if (process.env.STUDIO_CHROME) return process.env.STUDIO_CHROME;
  const base = path.join(os.homedir(), ".cache", "puppeteer");
  for (const kind of ["chrome-headless-shell", "chrome"]) {
    const dir = path.join(base, kind);
    if (!fs.existsSync(dir)) continue;
    for (const v of fs.readdirSync(dir).sort().reverse()) {
      for (const exe of ["chrome-headless-shell-win64/chrome-headless-shell.exe", "chrome-win64/chrome.exe",
                         "chrome-headless-shell-linux64/chrome-headless-shell", "chrome-linux64/chrome",
                         "chrome-headless-shell-mac-arm64/chrome-headless-shell", "chrome-headless-shell-mac-x64/chrome-headless-shell"]) {
        const p = path.join(dir, v, exe);
        if (fs.existsSync(p)) return p;
      }
    }
  }
  throw new Error("no Chrome found: set STUDIO_CHROME or run `npx hyperframes browser ensure`");
}

function ffmpeg() {
  if (process.env.STUDIO_FFMPEG) return process.env.STUDIO_FFMPEG;
  const tools = path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..", "tools");
  if (fs.existsSync(tools)) {
    for (const d of fs.readdirSync(tools).filter((d) => d.startsWith("ffmpeg-")).sort().reverse()) {
      const p = path.join(tools, d, "bin", process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg");
      if (fs.existsSync(p)) return p;
    }
  }
  return "ffmpeg";
}

const CURSOR = `(() => {
  const mk = () => {
    if (document.getElementById('__cur')) return;
    const c = document.createElement('div'); c.id = '__cur';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 26 26"><path d="M3 2 L3 21 L8.2 16.4 L11.6 24 L15 22.5 L11.7 15.2 L18.6 15.2 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:2147483647, pointerEvents:'none',
      transform:'translate(-100px,-100px)', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
    const r = document.createElement('div'); r.id = '__ring';
    Object.assign(r.style, {position:'fixed', left:'0', top:'0', width:'36px', height:'36px', margin:'-18px 0 0 -18px',
      borderRadius:'50%', border:'2px solid rgba(120,160,255,.9)', zIndex:2147483646, pointerEvents:'none', opacity:'0'});
    document.documentElement.appendChild(r); document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.transform = 'translate(' + (e.clientX - 3) + 'px,' + (e.clientY - 2) + 'px)'; }, true);
    addEventListener('mousedown', e => {
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      r.animate([{opacity: .9, transform: 'scale(.4)'}, {opacity: 0, transform: 'scale(1.4)'}], {duration: 450, easing: 'ease-out'});
    }, true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', mk); else mk();
})();`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "webrec-"));
const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true,
  args: ["--hide-scrollbars", "--force-color-profile=srgb", "--font-render-hinting=none"] });
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: SCALE });
if (shot.colorScheme) await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: shot.colorScheme }]);
if (shot.cursor !== false) await page.evaluateOnNewDocument(CURSOR);
await page.goto(shot.url, { waitUntil: "networkidle0", timeout: 30000 });
await page.evaluate(() => document.fonts && document.fonts.ready);
await sleep(shot.settle_ms ?? 600);

const frames = [];
const cdp = await page.createCDPSession();
cdp.on("Page.screencastFrame", async (f) => {
  const file = path.join(tmp, `f${String(frames.length).padStart(5, "0")}.png`);
  frames.push({ file, t: f.metadata.timestamp });
  fs.writeFileSync(file, Buffer.from(f.data, "base64"));
  cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
});
let mouse = { x: W * 0.62, y: H * 0.72 };
await page.mouse.move(mouse.x, mouse.y);
const t0 = Date.now() / 1000;
await cdp.send("Page.startScreencast", { format: "png", everyNthFrame: 1, maxWidth: W * SCALE, maxHeight: H * SCALE });

async function center(sel) {
  const el = await page.waitForSelector(sel, { visible: true, timeout: 5000 });
  await el.evaluate((e) => e.scrollIntoView({ block: "nearest" }));
  const b = await el.boundingBox();
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
}
async function glide(to, s) {
  const n = Math.max(2, Math.round(s * 60)), from = { ...mouse };
  for (let i = 1; i <= n; i++) {
    const k = ease(i / n);
    await page.mouse.move(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k);
    await sleep((s * 1000) / n);
  }
  mouse = { ...to };
}

for (const st of shot.steps) {
  const s = st.s ?? 0.7;
  if (st.do === "wait") await sleep(s * 1000);
  else if (st.do === "move") await glide(st.sel ? await center(st.sel) : { x: st.x, y: st.y }, s);
  else if (st.do === "click") {
    const p = st.sel ? await center(st.sel) : { x: st.x, y: st.y };
    if (Math.hypot(p.x - mouse.x, p.y - mouse.y) > 4) await glide(p, s);
    await page.mouse.down(); await sleep(70); await page.mouse.up();
    await sleep((st.after ?? 0.6) * 1000);
  } else if (st.do === "type") {
    if (st.sel) await page.focus(st.sel);
    await page.keyboard.type(st.text, { delay: st.delay ?? 55 });
  } else if (st.do === "key") await page.keyboard.press(st.key);
  else if (st.do === "scroll") {
    const n = Math.max(2, Math.round(s * 60));
    for (let i = 0; i < n; i++) {
      await page.evaluate((sel, dy) => { const e = sel ? document.querySelector(sel) : document.scrollingElement; e.scrollBy(0, dy); }, st.sel || null, st.dy / n);
      await sleep((s * 1000) / n);
    }
  } else if (st.do === "eval") await page.evaluate(st.js);
  else throw new Error("unknown step " + st.do);
}
await sleep(400);
await cdp.send("Page.stopScreencast");
const tEnd = Date.now() / 1000;
await browser.close();

// Lay the frames on a constant clock: each frame shows until the next one painted.
if (!frames.length) throw new Error("no frames captured");
const list = frames.map((f, i) => {
  const next = i + 1 < frames.length ? frames[i + 1].t : Math.max(f.t + 1 / FPS, tEnd - t0 + frames[0].t);
  return `file '${f.file.replace(/\\/g, "/")}'\nduration ${Math.max(1 / FPS, next - f.t).toFixed(4)}`;
}).join("\n") + `\nfile '${frames[frames.length - 1].file.replace(/\\/g, "/")}'\n`;
fs.writeFileSync(path.join(tmp, "list.txt"), list);
const r = spawnSync(ffmpeg(), ["-hide_banner", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", path.join(tmp, "list.txt"),
  "-vf", `fps=${FPS},scale=${W * SCALE}:${H * SCALE}:flags=lanczos,format=yuv420p`, "-c:v", "libx264", "-crf", "16",
  "-preset", "slow", "-tune", "animation", "-movflags", "+faststart", outPath], { stdio: "inherit" });
fs.rmSync(tmp, { recursive: true, force: true });
if (r.status) process.exit(r.status);
console.log(`webrec: ${frames.length} paints, ${(tEnd - t0).toFixed(1)} s -> ${outPath}`);
