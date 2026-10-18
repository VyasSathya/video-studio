"""Write the HyperFrames compositions for the agent-brain launch film from BUILD/storyboard.json:
BUILD/hf-wide/index.html (1920x1080) and BUILD/hf-tall/index.html (1080x1920).

The only product pixels are the cards: real command output and real files from capture.py, typeset in JetBrains Mono
on agent-brain's own diagram tokens (docs/how-it-works-dark.png: bg #0d0d10, card #141418, hairline #27272d, text
#ececf0, muted #9a9aa4, blue #7d9bff for what you run, orange #fb923c for evidence, highlight #2a1c10). Inter for
type. Everything else is camera, light and type.
"""
import html
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storyboard import BUILD  # noqa: E402

SB = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
M = SB["metrics"]
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}


def grain(path):
    rng = np.random.default_rng(3)
    g = (rng.standard_normal((512, 512)) * 38 + 128).clip(0, 255).astype(np.uint8)
    Image.fromarray(g, "L").save(path)


def accent(text, marks):
    """Escape text and wrap the accent ranges [a, b, cls] (from storyboard.py, exact substrings of the output)."""
    out, pos = [], 0
    for a, b, cls in sorted(marks):
        out.append(html.escape(text[pos:a], quote=False))
        out.append('<span class="%s">%s</span>' % (cls, html.escape(text[a:b], quote=False)))
        pos = b
    out.append(html.escape(text[pos:], quote=False))
    return "".join(out)


def card_html(c, first=False):
    """One window: its rows at their laid-out y. Focus rows are sharp (and carry a tinted band); every other row
    sits out of focus (dimmed and softly blurred: the camera's focus, not an edit)."""
    # Out-of-focus rows are grouped: one blurred layer per run of consecutive soft rows (HyperFrames' capture goes
    # black when a composition carries ~40 blurred elements, so the blur is never per row).
    rows, out, run = [], [], None

    def flush():
        if rows:
            out.append('<div class="softg">%s</div>' % "".join(rows) if run else "".join(rows))
            rows.clear()

    for i, r in enumerate(c["rows"]):
        is_soft = not r["focus"]
        if is_soft != run:
            flush()
            run = is_soft
        soft = ""
        if r.get("band"):
            rows.append('<div class="band %s" style="top:%dpx;height:%dpx"></div>' % (r["band"], r["y"] - 2, M["lh"]))
        if r["kind"] == "cmd":
            pre = '<span class="pr">$</span> ' if r["first"] else "&nbsp;&nbsp;"
            inner = pre + '<span class="cm">%s</span>' % html.escape(r["text"], quote=False)
        elif r["kind"] == "out":
            inner = accent(r["text"], r.get("acc", [])) or "&nbsp;"
        else:
            rows.append('<div class="row gut%s%s" style="top:%dpx;left:%dpx">%s</div>' % (
                (" " + r["band"]) if r.get("band") else "", soft, r["y"], M["pad_x"], r["n"] or ""))
            inner = html.escape(r["text"], quote=False) or "&nbsp;"
        rows.append('<div class="row %s%s" style="top:%dpx;left:%.1fpx">%s</div>' % (
            r["kind"], soft, r["y"], c["x0"], inner))
    flush()
    head =('<div class="bar"><i></i><i></i><i></i><span class="%s">%s</span></div>' %
            ("tn" if c["title"] == "agent-brain" else "fn", html.escape(c["title"])))
    # the first shot's card is visible from the first frame without a timeline set at t=0 (HyperFrames' seek
    # drops zero-duration sets at the very start: the opening card rendered blank)
    return ('<div class="card %s" id="card_%s" data-layout-allow-overflow style="width:%.1fpx;height:%dpx%s">%s%s</div>' %
            (c["kind"], c["id"], c["w"], c["h"], ";display:block" if first else "", head, "".join(out)))


def build(fmt):
    W, H = SIZE[fmt]
    out = BUILD / ("hf-" + fmt)
    out.mkdir(parents=True, exist_ok=True)
    grain(out / "grain.png")
    cards = SB["cards"][fmt]
    cams = []
    for s in SB["shots"]:
        c = cards.get(s["card"]) if s["card"] else None
        cams.append({"id": s["id"], "t": s["t"], "end": s["end"], "card": s["card"], "from": s[fmt]["from"],
                     "to": s[fmt]["to"], "hero": bool(s.get("hero")), "angle": s.get("angle", [0, 0]),
                     "cw": c["w"] if c else 0, "ch": c["h"] if c else 0, "light": SB["light"][s["id"]]})
    types = []
    for k, v in SB["type"].items():
        if k == "end":
            continue
        types.append({"id": k, "t": v["t"], "end": v["end"], "head": v.get("head_" + fmt, v["head"]),
                      "sub": v.get("sub_" + fmt, v.get("sub")), "place": v["place"][fmt]})
    end = SB["type"]["end"]
    page = (TEMPLATE.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", "%.3f" % SB["duration"])
            .replace("__CARDS__", "\n".join(card_html(c, c["id"] == SB["shots"][0]["card"]) for c in cards.values()))
            .replace("__FS__", str(M["fs"])).replace("__LH__", str(M["lh"]))
            .replace("__CAMS__", json.dumps(cams)).replace("__TYPES__", json.dumps(types))
            .replace("__TE__", str(end["t"])).replace("__FMT__", fmt)
            .replace("__END_HEAD__", end["head"]).replace("__END_SUB__", end.get("sub_" + fmt, end["sub"]))
            .replace("__END_URL__", end["url"]))
    (out / "index.html").write_text(page, encoding="utf-8")
    print("composition:", out / "index.html")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root { --bg: #0d0d10; --card: #141418; --line: #27272d; --text: #ececf0; --muted: #9a9aa4; --faint: #63636c;
          --in: #7d9bff; --ev: #fb923c; --hl: #2a1c10; --out: #c4c4cc; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: var(--bg); }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden;
          background: radial-gradient(120% 85% at 50% 42%, #24242c 0%, #15151a 46%, var(--bg) 100%); }
  #stage { position: absolute; inset: 0; opacity: 0; }
  #light { position: absolute; left: -15%; top: -20%; width: 130%; height: 110%; opacity: 0.32;
           background: radial-gradient(48% 44% at 50% 52%, var(--lc) 0%, rgba(0,0,0,0) 70%); }
  #lens { position: absolute; inset: 0;
          -webkit-mask-image: linear-gradient(to right, transparent 0, #000 6%, #000 93%, transparent 100%),
                              linear-gradient(to bottom, transparent 0, #000 7%, #000 92%, transparent 100%);
          -webkit-mask-composite: source-in; mask-composite: intersect; }
  #cam { position: absolute; left: 0; top: 0; width: 1400px; height: 1400px; transform-origin: 0 0; }
  #dof { position: absolute; inset: 0; transform-origin: 50% 50%; }
  .card { position: absolute; left: 0; top: 0; display: none; border-radius: 16px; overflow: hidden;
          background: linear-gradient(to bottom, #23232a 0%, #1b1b21 18%, #17171c 60%, #131317 100%);
          border: 1px solid rgba(255,255,255,0.085);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.16), inset 0 0 0 1px rgba(255,255,255,0.02),
                      0 60px 120px rgba(0,0,0,0.8), 0 14px 34px rgba(0,0,0,0.55); }
  .card::after { content: ""; position: absolute; left: 8%; right: 8%; top: 0; height: 1px;
                 background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.32), rgba(255,255,255,0)); }
  #glow { position: absolute; opacity: 0.22; pointer-events: none;
          background: radial-gradient(closest-side, var(--lc) 0%, rgba(0,0,0,0) 100%); }
  .bar { position: absolute; left: 0; right: 0; top: 0; height: 54px; border-bottom: 1px solid var(--line);
         display: flex; align-items: center; padding-left: 22px; gap: 9px; }
  .bar i { width: 12px; height: 12px; border-radius: 50%; background: #2e2e35; display: block; }
  .bar span { margin-left: 16px; font-size: 16px; color: var(--muted); letter-spacing: -0.005em; }
  .bar span.fn { font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 15px; color: var(--muted); }
  .row { position: absolute; white-space: pre; font-family: "JetBrains Mono", ui-monospace, monospace;
         font-size: __FS__px; line-height: __LH__px; color: var(--out); }
  .row.cmd { color: var(--in); }
  .row .pr { color: var(--muted); }
  .row.out { color: var(--text); }
  .row.gut { color: #85858e; }
  .row.gut.ev { color: var(--ev); }
  .row.gut.in { color: var(--in); }
  .row.file { color: var(--text); }
  .band { position: absolute; left: 0; right: 0; }
  .band.ev { background: var(--hl); box-shadow: inset 3px 0 0 var(--ev); }
  .band.in { background: rgba(125,155,255,0.10); box-shadow: inset 3px 0 0 var(--in); }
  .softg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; opacity: 0.5; filter: blur(1px); }
  .ev { color: var(--ev); }
  .in { color: var(--in); }
  #vig { position: absolute; inset: 0; pointer-events: none;
         background: radial-gradient(120% 100% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%); }
  #grain { position: absolute; inset: 0; pointer-events: none; opacity: 0.05; mix-blend-mode: overlay;
           background-image: url(grain.png); background-size: 512px 512px; }
  .type { position: absolute; opacity: 0; }
  .type .h { font-weight: 600; letter-spacing: -0.035em; line-height: 1.04; color: var(--text); white-space: pre-line; }
  .wd { display: inline-block; overflow: hidden; vertical-align: top; padding-bottom: 0.12em; margin-bottom: -0.12em; }
  .wd > span { display: inline-block; opacity: 0; }
  .type .s { margin-top: 22px; font-weight: 450; white-space: pre-line; letter-spacing: -0.01em; line-height: 1.3; color: var(--muted); opacity: 0; }
  .wide .type { width: 1500px; }
  .wide .type .h { font-size: 92px; }
  .wide .type .s { font-size: 48px; }
  .wide .type.bl { left: 128px; bottom: 104px; }
  .wide .type.tl { left: 128px; top: 96px; }
  .tall .type { left: 72px; right: 72px; text-align: center; }
  .tall .type .h { font-size: 92px; }
  .tall .type .s { font-size: 50px; }
  .tall .type.top { top: 260px; }
  .scrim { position: absolute; left: 0; right: 0; pointer-events: none; opacity: 0; }
  #scrimB { bottom: 0; height: 36%; background: linear-gradient(to bottom, rgba(13,13,16,0) 0%, rgba(13,13,16,0.97) 42%, rgba(13,13,16,1) 100%); }
  #scrimT { top: 0; height: 300px; background: linear-gradient(to top, rgba(13,13,16,0) 0%, rgba(13,13,16,0.97) 26%, rgba(13,13,16,1) 100%); }
  .tall #scrimT { height: 610px; }
  #endcard { position: absolute; left: 0; right: 0; text-align: center; }
  .wide #endcard { top: 352px; }
  .tall #endcard { top: 720px; }
  #endcard .wm { font-size: 168px; font-weight: 650; letter-spacing: -0.05em; line-height: 1; opacity: 0; }
  #endcard .wm .wd > span { opacity: 1; }
  #endcard .ln { white-space: pre-line; margin-top: 30px; font-size: 54px; color: var(--muted); letter-spacing: -0.012em; opacity: 0; }
  #endcard .url { margin-top: 36px; font-size: 52px; font-family: "JetBrains Mono", ui-monospace, monospace;
                  color: var(--in); opacity: 0; }
  .tall #endcard .wm { font-size: 160px; }
  .tall #endcard .ln { font-size: 56px; padding: 0 60px; }
  .tall #endcard .url { font-size: 44px; }
  #black { position: absolute; inset: 0; background: #000; opacity: 0; pointer-events: none; }
</style>
</head>
<body>
<div id="root" class="__FMT__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="stage">
    <div id="light" style="--lc: rgb(120,128,170)"></div>
    <div id="lens">
      <div id="cam" data-layout-allow-overflow>
        <div id="dof" data-layout-allow-overflow>
          <div id="glow" style="--lc: rgb(120,128,170)"></div>
__CARDS__
        </div>
      </div>
    </div>
    <div id="vig"></div>
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
  const CAMS = __CAMS__, TYPES = __TYPES__, DUR = __DUR__, TE = __TE__;
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
  const pos = (p) => ({ x: p[3] - p[2] * p[0], y: p[4] - p[2] * p[1], scale: p[2] });
  tl.fromTo("#stage", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power2.out" }, 0);
  for (const c of CAMS) {
    if (c.t > 0) tl.set(".card", { display: "none" }, c.t);
    if (!c.card) continue;
    const card = "#card_" + c.card;
    if (c.t > 0) tl.set(card, { display: "block" }, c.t);
    const org = c.from[0] + "px " + c.from[1] + "px";
    const glow = { left: -c.cw * 0.45, top: -c.ch * 0.55, width: c.cw * 1.9, height: c.ch * 2.1 };
    tl.fromTo("#cam", pos(c.from), { ...pos(c.to), duration: c.end - c.t, ease: c.hero ? "power2.inOut" : "sine.inOut",
              immediateRender: c.t === 0 }, c.t);
    if (c.hero) {
      tl.fromTo("#dof", { rotationX: c.angle[0], rotationY: c.angle[1], transformPerspective: 2600, transformOrigin: org },
                { rotationX: 0, rotationY: 0, duration: c.end - c.t, ease: "power3.out" }, c.t);
      tl.fromTo("#glow", glow, { ...glow, duration: 0.01 }, c.t);
    } else {
      tl.set("#dof", { rotationX: c.angle[0], rotationY: c.angle[1], transformPerspective: 2600, transformOrigin: org }, c.t);
      tl.set("#glow", glow, c.t);
    }
    tl.set("#light, #glow", { "--lc": "rgb(" + c.light + ")" }, c.t);
  }
  for (const ty of TYPES) {
    const el = "#ty_" + ty.id;
    const scrim = ty.place === "bl" ? "#scrimB" : "#scrimT";
    tl.set(el, { opacity: 1 }, ty.t);
    tl.set("#scrimB", { opacity: scrim === "#scrimB" ? 1 : 0 }, ty.t);
    tl.set("#scrimT", { opacity: scrim === "#scrimT" ? 1 : 0 }, ty.t);
    tl.fromTo(el + " .wd > span", { yPercent: 115, opacity: 0 },
              { yPercent: 0, opacity: 1, duration: 0.5, ease: "power3.out", stagger: 0.06, immediateRender: false }, ty.t + 0.02);
    if (ty.sub) tl.fromTo(el + " .s", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", immediateRender: false }, ty.t + 0.45);
    tl.set(el, { opacity: 0 }, ty.end);
  }
  tl.set(".scrim", { opacity: 0 }, TE);
  tl.set("#endcard .wm", { opacity: 1 }, TE);
  tl.fromTo("#endcard .wm .wd > span", { yPercent: 115 }, { yPercent: 0, duration: 0.7, ease: "power3.out", immediateRender: false }, TE);
  tl.fromTo("#endcard .ln", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, TE + 0.6);
  tl.fromTo("#endcard .url", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, TE + 1.1);
  tl.to("#black", { opacity: 1, duration: 0.6, ease: "power1.in" }, DUR - 0.6);
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
