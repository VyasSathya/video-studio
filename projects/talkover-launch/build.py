"""Write the HyperFrames compositions for the Talkover launch film from build/storyboard.json:
build/hf-wide/index.html (1920x1080) and build/hf-tall/index.html (1080x1920).

The only product pixels are build/panel.webm: Talkover's real floating panel, drawn by its own voice_panel.py
(panel_render.py). Everything else is camera, type and backdrop. Tokens: a neutral near-black with one cool
neutral room light, Talkover's teal as the only accent in type; Inter for type, JetBrains Mono for the URL.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SB = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
SRC = 10                       # panel.webm px per panel logical px (panel_render --scale 10)
PANEL_W, PANEL_H = 424 * SRC, 120 * SRC
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}
# The room light takes a little of the orb's colour (35 % into a neutral), following the panel's state changes.
SPILL = [(0.0, "129,150,213"), (1.0, "124,181,204"), (2.9, "152,153,213"), (4.4, "185,154,156"), (8.5, "124,181,204"),
         (9.1, "152,153,213"), (11.0, "185,154,156")]


def grain(path):
    rng = np.random.default_rng(3)
    g = (rng.standard_normal((512, 512)) * 38 + 128).clip(0, 255).astype(np.uint8)
    Image.fromarray(g, "L").save(path)


def build(fmt):
    W, H = SIZE[fmt]
    out = BUILD / ("hf-" + fmt)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(BUILD / "panel.webm", out / "panel.webm")
    grain(out / "grain.png")
    cams = [{"id": s["id"], "t": s["t"], "end": s["end"], "from": s[fmt]["from"], "to": s[fmt]["to"],
             "dof": bool(s.get("dof")), "hide": bool(s.get("hide_panel")), "hero": bool(s.get("hero")),
             "mask": s.get("mask_" + fmt)} for s in SB["shots"]]
    types = []
    for k, v in SB["type"].items():
        if k == "end":
            continue
        head = v.get("head_" + fmt, v["head"])
        types.append({"id": k, "t": v["t"], "end": v["end"], "head": head, "sub": v.get("sub_" + fmt, v.get("sub")),
                      "place": v["place"][fmt]})
    end = SB["type"]["end"]
    page = (TEMPLATE.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", "%.3f" % SB["duration"])
            .replace("__PW__", str(PANEL_W)).replace("__PH__", str(PANEL_H)).replace("__SRC__", str(SRC))
            .replace("__CAMS__", json.dumps(cams)).replace("__TYPES__", json.dumps(types))
            .replace("__TE__", str(end["t"])).replace("__SPILL__", json.dumps(SPILL)).replace("__FMT__", fmt)
            .replace("__END_HEAD__", end["head"]).replace("__END_SUB__", end.get("sub_" + fmt, end["sub"])).replace("__END_URL__", end["url"]))
    (out / "index.html").write_text(page, encoding="utf-8")
    print("composition:", out / "index.html")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root { --bg: #08080a; --text: #f2f2f5; --muted: #c9c9d1; --accent: #4ddbe6; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: var(--bg); }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden;
          background: radial-gradient(130% 90% at 50% 35%, #1b1c21 0%, #0f0f12 45%, var(--bg) 100%); }
  #stage { position: absolute; inset: 0; opacity: 0; }
  #light { position: absolute; left: -15%; top: -25%; width: 130%; height: 110%; opacity: 0.22;
           background: radial-gradient(50% 45% at 50% 50%, var(--lc) 0%, rgba(0,0,0,0) 70%); }
  #cam { position: absolute; left: 0; top: 0; width: __PW__px; height: __PH__px; transform-origin: 0 0; }
  #dof { position: absolute; inset: 0; transform-origin: 50% 50%; }
  #panelwrap { position: absolute; inset: 0; filter: drop-shadow(0 70px 110px rgba(0,0,0,0.78)); }
  #panelwrap video { position: absolute; left: 0; top: 0; width: __PW__px; height: __PH__px; }
  #vig { position: absolute; inset: 0; pointer-events: none;
         background: radial-gradient(120% 100% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%); }
  #grain { position: absolute; inset: 0; pointer-events: none; opacity: 0.05; mix-blend-mode: overlay;
           background-image: url(grain.png); background-size: 512px 512px; }
  .type { position: absolute; opacity: 0; }
  .type .h { font-weight: 600; letter-spacing: -0.035em; line-height: 1.04; color: var(--text); white-space: pre-line; }
  .wd { display: inline-block; overflow: hidden; vertical-align: top; padding-bottom: 0.12em; margin-bottom: -0.12em; }
  .wd > span { display: inline-block; }
  .type .s { margin-top: 22px; font-weight: 450; white-space: pre-line; letter-spacing: -0.01em; line-height: 1.3; color: var(--muted); }
  .wide .type { width: 1300px; }
  .wide .type .h { font-size: 96px; }
  .wide .type .s { font-size: 50px; }
  .wide .type.bl { left: 128px; bottom: 104px; }
  .wide .type.tl { left: 128px; top: 104px; }
  .wide .type.tr { right: 128px; top: 104px; text-align: right; }
  .wide .type.center { left: 310px; right: 310px; width: auto; top: 560px; text-align: center; }
  .wide .type.center .h { font-size: 132px; }
  .tall .type { left: 72px; right: 72px; text-align: center; }
  .tall .type .h { font-size: 96px; }
  .tall .type .s { font-size: 52px; }
  .tall .type.bottom { bottom: 420px; }
  .tall .type.top { top: 300px; }
  .tall .type.center { top: 1000px; }
  .tall .type.center .h { font-size: 130px; }
  .scrim { position: absolute; left: 0; right: 0; height: 50%; pointer-events: none; opacity: 0; }
  #scrimB { bottom: 0; background: linear-gradient(to bottom, rgba(8,8,10,0) 0%, rgba(8,8,10,0.8) 60%, rgba(8,8,10,0.94) 100%); }
  #scrimT { top: 0; background: linear-gradient(to top, rgba(8,8,10,0) 0%, rgba(8,8,10,0.8) 60%, rgba(8,8,10,0.94) 100%); }
  #endcard { position: absolute; left: 0; right: 0; text-align: center; }
  .wide #endcard { top: 350px; }
  .tall #endcard { top: 720px; }
  #endcard .wm { font-size: 168px; font-weight: 650; letter-spacing: -0.05em; line-height: 1; opacity: 0; }
  #endcard .ln { white-space: pre-line; margin-top: 30px; font-size: 56px; color: var(--muted); letter-spacing: -0.012em; opacity: 0; }
  #endcard .url { margin-top: 34px; font-size: 52px; font-family: "JetBrains Mono", ui-monospace, monospace;
                  color: var(--accent); opacity: 0; }
  .tall #endcard .wm { font-size: 176px; }
  .tall #endcard .ln { font-size: 58px; padding: 0 60px; }
  .tall #endcard .url { font-size: 48px; }
  #mask { position: absolute; left: 0; right: 0; bottom: 0; opacity: 0; pointer-events: none;
          background: linear-gradient(to bottom, rgba(11,11,13,0) 0px, rgba(11,11,13,1) 40px); }
  #black { position: absolute; inset: 0; background: #000; opacity: 0; pointer-events: none; }
</style>
</head>
<body>
<div id="root" class="__FMT__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="stage">
    <div id="light" style="--lc: rgb(129,150,213)"></div>
    <div id="cam">
      <div id="dof">
        <div id="panelwrap">
          <video id="pv" src="panel.webm" data-start="0" data-duration="__DUR__" data-track-index="0" muted playsinline></video>
        </div>
      </div>
    </div>
    <div id="vig"></div>
    <div id="mask"></div>
    <div class="scrim" id="scrimB"></div>
    <div class="scrim" id="scrimT"></div>
    <div id="types"></div>
    <div id="endcard">
      <div class="wm"><span class="wd"><span>__END_HEAD__</span></span></div>
      <div class="ln">__END_SUB__</div>
      <div class="url">__END_URL__</div>
    </div>
  </div>
  <div id="grain"></div>
  <div id="black"></div>
</div>
<script>
  const CAMS = __CAMS__, TYPES = __TYPES__, SRC = __SRC__, DUR = __DUR__, TE = __TE__, SPILL = __SPILL__;
  const holder = document.getElementById("types");
  for (const ty of TYPES) {
    const d = document.createElement("div");
    d.className = "type " + ty.place; d.id = "ty_" + ty.id;
    d.innerHTML = '<div class="h"></div>' + (ty.sub ? '<div class="s"></div>' : "");
    const h = d.querySelector(".h");
    ty.head.split(String.fromCharCode(10)).forEach((line, li) => {
      if (li) h.appendChild(document.createElement("br"));
      line.split(" ").forEach((w, wi) => {
        if (wi) h.appendChild(document.createTextNode(" "));
        const o = document.createElement("span"); o.className = "wd";
        const i = document.createElement("span"); i.textContent = w; o.appendChild(i); h.appendChild(o);
      });
    });
    if (ty.sub) d.querySelector(".s").textContent = ty.sub;
    holder.appendChild(d);
  }
  const tl = gsap.timeline({ paused: true });
  const pos = (p) => ({ x: p[3] - p[2] * p[0], y: p[4] - p[2] * p[1], scale: p[2] / SRC });
  tl.fromTo("#stage", { opacity: 0 }, { opacity: 1, duration: 0.6, ease: "power2.out" }, 0);
  for (const c of CAMS) {
    tl.set("#cam", pos(c.from), c.t);
    tl.to("#cam", { ...pos(c.to), duration: c.end - c.t, ease: c.id === "s1" ? "power2.inOut" : "sine.inOut" }, c.t);
    tl.set("#dof", { filter: c.dof ? "blur(36px)" : "blur(0px)", opacity: c.dof ? 0.42 : 1 }, c.t);
    tl.set("#cam", { opacity: c.hide ? 0 : 1 }, c.t);
    if (c.mask) { tl.set("#mask", { top: c.mask, opacity: 1 }, c.t); tl.set("#mask", { opacity: 0 }, c.end); }
    if (c.hero) tl.fromTo("#dof", { rotationX: 26, rotationY: -22, transformPerspective: 5200 },
                          { rotationX: 0, rotationY: 0, duration: c.end - c.t, ease: "power3.out" }, c.t);
  }
  // kinetic type: one block at a time; head first, sub after it lands; scrim on the side the type sits
  for (const ty of TYPES) {
    const el = "#ty_" + ty.id;
    const scrim = /^(bl|bottom)$/.test(ty.place) ? "#scrimB" : (/^(tl|tr|top)$/.test(ty.place) ? "#scrimT" : null);
    tl.set(el, { opacity: 1 }, ty.t);
    tl.set("#scrimB", { opacity: scrim === "#scrimB" ? 1 : 0 }, ty.t);
    tl.set("#scrimT", { opacity: scrim === "#scrimT" ? 1 : 0 }, ty.t);
    tl.fromTo(el + " .wd > span", { yPercent: 115, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.55, ease: "power3.out", stagger: 0.07 }, ty.t + 0.02);
    if (ty.sub) tl.fromTo(el + " .s", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, ty.t + 0.4);
    tl.set(el, { opacity: 0 }, ty.end);
  }
  tl.set(".scrim", { opacity: 0 }, TE);
  tl.set("#endcard .wm", { opacity: 1 }, TE);
  tl.fromTo("#endcard .wm .wd > span", { yPercent: 115 }, { yPercent: 0, duration: 0.7, ease: "power3.out" }, TE);
  tl.fromTo("#endcard .ln", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out" }, TE + 0.6);
  tl.fromTo("#endcard .url", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out" }, TE + 1.1);
  tl.to("#black", { opacity: 1, duration: 0.6, ease: "power1.in" }, DUR - 0.6);
  for (const [t, c] of SPILL) tl.to("#light", { "--lc": "rgb(" + c + ")", duration: 0.4, ease: "sine.inOut" }, t);
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    for f in (sys.argv[1:] or ["wide", "tall"]):
        build(f)
