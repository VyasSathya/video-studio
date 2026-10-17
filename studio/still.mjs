// Render an HTML file (or URL) to PNG in headless Chrome: one image per color scheme.
//
//   node studio/still.mjs page.html out.png [--width 1600] [--height 900] [--scale 2] [--scheme light,dark] [--sel #frame]
//
// With several schemes, out.png becomes out-light.png, out-dark.png. --sel crops to one element.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const [src, out] = args;
if (!src || !out) { console.error("usage: node studio/still.mjs page.html out.png [--scheme light,dark]"); process.exit(2); }
const W = +opt("width", 1600), H = +opt("height", 900), S = +opt("scale", 2);
const schemes = opt("scheme", "light").split(",");
const sel = opt("sel", null);

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

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const url = /^https?:/.test(src) ? src : pathToFileURL(path.resolve(src)).href;
const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ["--force-color-profile=srgb"] });
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: S });
for (const sc of schemes) {
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: sc }]);
  await page.goto(url, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const file = schemes.length > 1 ? out.replace(/\.png$/i, `-${sc}.png`) : out;
  if (sel) await (await page.$(sel)).screenshot({ path: file, omitBackground: false });
  else await page.screenshot({ path: file });
  console.log("still:", file);
}
await browser.close();
