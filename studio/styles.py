"""Speaker-led styles over edited footage: "whiteboard" and "course" (16:9).

    beats = beats.place(beats.parse(prompt, words)["rules"], words, duration)["beats"]
    build(comp_dir, footage, words, beats, style="whiteboard" | "course", credit=..., accent=...)
    overlay.finish(comp_dir, audio, out)          # render, then the edited audio at -14 LUFS

whiteboard: the speaker full frame by default; a "takeover" or "draw" beat turns the whole frame into a paper
board where strokes draw themselves (rough hand-drawn paths generated here) and words are hand-lettered (Caveat,
OFL); "number", "bullets", "card" and "image" beats split the frame: speaker on the left half, board on the right.
course: the speaker full frame, then for each beat the speaker glides into a rounded crop on the left and a big,
short takeaway (number, bullets, card, image) builds on the right on a liquid-glass card; a takeover shrinks the
speaker to a corner. Both: captions at the bottom, the beat's key word lit like a highlighter.
One motion at a time: the layout moves first (0.55 s, ease in-out), then the content draws or builds.
"""
import html
import json
import math
import random
import shutil
from pathlib import Path

from . import launch, media, overlay, stock

INK = "#1d1d22"
PAPER = "#f7f5ef"


def esc(s):
    return html.escape(str(s), quote=True)


# rough strokes ---------------------------------------------------------------------------------------------

def _jit(rng, a):
    return rng.uniform(-a, a)


def rough_line(x1, y1, x2, y2, rng, j=3.0):
    mx, my = (x1 + x2) / 2 + _jit(rng, j * 2), (y1 + y2) / 2 + _jit(rng, j * 2)
    return "M%.1f %.1f Q%.1f %.1f %.1f %.1f" % (x1 + _jit(rng, j), y1 + _jit(rng, j), mx, my,
                                                x2 + _jit(rng, j), y2 + _jit(rng, j))


def rough_circle(cx, cy, r, rng, j=0.06, over=0.18):
    pts, n = [], 28
    a0 = rng.uniform(0, math.pi * 2)
    for i in range(int(n * (1 + over)) + 1):
        a = a0 + i * 2 * math.pi / n
        rr = r * (1 + _jit(rng, j)) * (1 - 0.04 * i / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.96))
    return "M" + " L".join("%.1f %.1f" % p for p in pts)


def rough_arrow(x1, y1, x2, y2, rng):
    a = math.atan2(y2 - y1, x2 - x1)
    h = 26
    p = [rough_line(x1, y1, x2, y2, rng)]
    for d in (2.6, -2.6):
        p.append(rough_line(x2, y2, x2 + h * math.cos(a + d), y2 + h * math.sin(a + d), rng, 1.5))
    return p


def doodle(text, cx, cy, size, rng):
    """A simple drawn picture for the beat's subject: a planet, a clock, or a star burst."""
    t = text.lower()
    r = size / 2
    first = t.split()[0] if t.split() else ""
    if first in ("clock", "time"):
        t = "time"
    if t != "time" and any(k in t for k in ("mars", "planet", "earth", "moon", "orbit", "space")):
        return [rough_circle(cx, cy, r * 0.62, rng),
                "M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" % (cx - r, cy + r * 0.1, cx - r * 0.4, cy - r * 0.42,
                                                              cx + r * 0.6, cy - r * 0.45, cx + r, cy - r * 0.08)]
    if any(k in t for k in ("day", "year", "hour", "time", "month", "long")):
        p = [rough_circle(cx, cy, r * 0.7, rng), rough_line(cx, cy, cx, cy - r * 0.48, rng, 1.5),
             rough_line(cx, cy, cx + r * 0.34, cy + r * 0.12, rng, 1.5)]
        for k in range(12):
            a = k * math.pi / 6
            p.append(rough_line(cx + r * 0.6 * math.cos(a), cy + r * 0.6 * math.sin(a),
                                cx + r * 0.68 * math.cos(a), cy + r * 0.68 * math.sin(a), rng, 0.8))
        return p
    p = []
    for k in range(10):
        a = k * math.pi / 5 + rng.uniform(-0.1, 0.1)
        p.append(rough_line(cx + r * 0.25 * math.cos(a), cy + r * 0.25 * math.sin(a),
                            cx + r * 0.7 * math.cos(a), cy + r * 0.7 * math.sin(a), rng, 2))
    return p


def svg(paths, w, h, color=INK, width=5):
    return ('<svg class="ink" viewBox="0 0 %d %d" width="%d" height="%d">%s</svg>' % (
        w, h, w, h, "".join('<path d="%s" fill="none" stroke="%s" stroke-width="%g" stroke-linecap="round" '
                            'stroke-linejoin="round"/>' % (d, color, width) for d in paths)))


# beat content ----------------------------------------------------------------------------------------------

def _content(style, b, i, comp, rng, accent, used):
    kind = b["show"]
    text = b.get("text") or b["when"]
    if kind == "image":
        hit = stock.find(b.get("query") or text, comp / "stock", avoid=used)
        if hit:
            used.append(hit["title"])
            name = "img/b%d%s" % (i, Path(hit["file"]).suffix)
            shutil.copyfile(hit["file"], comp / name)
            cap = '<div class="pcap">%s</div>' % esc(text)
            if style == "whiteboard":
                return ('<div class="photo"><img src="%s" alt=""><div class="tape"></div>%s</div>' % (name, cap),
                        hit)
            return '<div class="glass imgcard"><img src="%s" alt="">%s</div>' % (name, cap), hit
        kind = "card"
    if style == "whiteboard":
        if kind == "number":
            return ('<div class="hand big">%s</div>%s' % (esc(text), svg([rough_circle(330, 120, 260, rng)], 660,
                                                                          260, accent, 6)), None)
        if kind == "bullets":
            items = [x.strip() for x in text.replace(";", ",").split(",") if x.strip()][:3] or [text]
            rows = "".join('<div class="hrow">%s<span class="hand">%s</span></div>' % (
                svg([rough_line(6, 30, 22, 46, rng, 1), rough_line(22, 46, 50, 8, rng, 1)], 56, 56, accent, 6),
                esc(x)) for x in items)
            return '<div class="hlist">%s</div>' % rows, None
        pic = svg(doodle((b.get("draw") or "") + " " + text + " " + b["when"], 260, 200, 330, rng), 520, 400).replace(
            'width="520" height="400"', 'width="760" height="585"')
        under = svg([rough_line(20, 20, 700, 26, rng, 4)], 720, 46, accent, 7)
        return '<div class="drawn">%s<div class="hand mid">%s</div>%s</div>' % (pic, esc(text), under), None
    if kind == "number":
        return '<div class="glass num"><div class="v">%s</div></div>' % esc(text), None
    if kind == "bullets":
        items = [x.strip() for x in text.replace(";", ",").split(",") if x.strip()][:3] or [text]
        return '<div class="glass list">%s</div>' % "".join('<div class="li"><i></i>%s</div>' % esc(x)
                                                             for x in items), None
    return '<div class="glass take"><div class="k">Key idea</div><div class="v">%s</div></div>' % esc(text), None


def build(comp, footage, words, beats, style="whiteboard", credit=None, accent="#e8590c", size=(1920, 1080),
          key_times=(), seed=7):
    comp = Path(comp)
    (comp / "img").mkdir(parents=True, exist_ok=True)
    W, H = size
    shutil.copyfile(footage, comp / "footage.mp4")
    dur = media.duration(comp / "footage.mp4")
    rng = random.Random(seed)
    used, credits, blocks, anim = [], [], [], []
    for i, b in enumerate(beats):
        inner, hit = _content(style, b, i, comp, rng, accent, used)
        if hit:
            credits.append(hit)
        full = b["show"] in ("takeover", "draw")
        layout = ("board" if style == "whiteboard" else "pip") if full else ("half" if style == "whiteboard" else "crop")
        blocks.append('<div class="bt %s" id="bt%d">%s</div>' % ("full" if full else "side", i, inner))
        anim.append({"i": i, "t": b["t"], "e": b["end"], "layout": layout})
    gs = overlay.groups(words, 6, 44)
    caps, cap_anim = [], []
    keyset = {round(t, 3) for t in key_times}
    for gi, g in enumerate(gs):
        gid = "g%d" % gi
        spans = "".join('<span class="w%s" id="%s_%d">%s</span> ' % (
            " kw" if round(w["start"], 3) in keyset else "", gid, k, esc(w["text"])) for k, w in enumerate(g))
        caps.append('<div class="cap" id="%s"><span class="in">%s</span></div>' % (gid, spans))
        nxt = gs[gi + 1][0]["start"] - 0.06 if gi + 1 < len(gs) else dur
        cap_anim.append(["cap", gid, max(0, g[0]["start"] - 0.06), min(nxt, g[-1]["end"] + 0.5)])
        for k, w in enumerate(g):
            cap_anim.append(["word", "%s_%d" % (gid, k), w["start"]])
    crd = credit or ""
    if credits:
        crd += ("; " if crd else "") + "Images: " + "; ".join(sorted({c["credit"] for c in credits}))
    faces = launch.font_faces(["Caveat", "Inter"], comp)
    page = (TEMPLATE.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", "%.3f" % dur)
            .replace("__STYLE__", style).replace("__ACCENT__", accent).replace("__BLOCKS__", "\n".join(blocks))
            .replace("__CAPS__", "\n".join(caps)).replace("__ANIM__", json.dumps(anim))
            .replace("__CAPANIM__", json.dumps(cap_anim)).replace("__CREDIT__", esc(crd))
            .replace("__FONTFACES__", faces).replace("__PAPER__", PAPER).replace("__INK__", INK))
    (comp / "index.html").write_text(page, encoding="utf-8")
    return {"duration": dur, "beats": anim, "credits": credits}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  __FONTFACES__
  :root { --accent: __ACCENT__; --paper: __PAPER__; --ink: __INK__; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: #0b0b0d; }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden; }
  .whiteboard #ground { position: absolute; inset: 0; background-color: var(--paper);
     background-image: radial-gradient(circle, rgba(29,29,34,.10) 1.2px, transparent 1.4px); background-size: 34px 34px; }
  .course #ground { position: absolute; inset: 0;
     background: radial-gradient(70% 70% at 75% 30%, color-mix(in oklch, var(--accent) 22%, #101014), #0c0c0f 75%); }
  #spk { position: absolute; left: 0; top: 0; width: __W__px; height: __H__px; overflow: hidden; z-index: 2; }
  #spk video { width: 100%; height: 100%; object-fit: cover; object-position: 50% 35%; }
  .course #spk { box-shadow: 0 30px 80px rgba(0,0,0,.45); }
  .bt { position: absolute; z-index: 3; opacity: 0; display: flex; flex-direction: column; align-items: center;
        justify-content: center; }
  .whiteboard .bt.full { inset: 0 0 120px 0; }
  .whiteboard .bt.side { left: 50%; right: 0; top: 0; bottom: 120px; }
  .course .bt.side { left: 52%; right: 70px; top: 120px; bottom: 170px; }
  .course .bt.full { left: 110px; right: 560px; top: 200px; bottom: 260px; }
  .hand { font-family: Caveat, cursive; color: var(--ink); line-height: 1; clip-path: inset(0 100% 0 0); }
  .hand.big { font-size: 190px; font-weight: 700; margin-bottom: -170px; position: relative; z-index: 1; }
  .hand.mid { font-size: 128px; font-weight: 700; text-align: center; max-width: 1100px; margin-top: -10px; }
  .drawn { display: flex; flex-direction: column; align-items: center; }
  .hlist { display: flex; flex-direction: column; gap: 26px; }
  .hrow { display: flex; align-items: center; gap: 20px; } .hrow .hand { font-size: 84px; font-weight: 600; }
  .photo { opacity: 0; position: relative; background: #fff; padding: 18px 18px 64px; box-shadow: 0 18px 40px rgba(0,0,0,.18);
           transform: rotate(-2.5deg); }
  .photo img { width: 620px; height: 420px; object-fit: cover; display: block; }
  .photo .tape { position: absolute; left: 50%; top: -18px; width: 150px; height: 38px; margin-left: -75px;
                 background: rgba(255, 236, 170, .75); transform: rotate(3deg); }
  .photo .pcap { position: absolute; left: 0; right: 0; bottom: 12px; text-align: center; font-family: Caveat, cursive;
                 font-size: 42px; color: var(--ink); }
  .glass { opacity: 0; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22); border-radius: 28px;
           backdrop-filter: blur(22px) saturate(1.4); box-shadow: inset 0 1px 0 rgba(255,255,255,.35), 0 30px 70px rgba(0,0,0,.35);
           color: #f6f6f8; padding: 44px 52px; width: 100%; }
  .glass.num .v { font-size: 200px; font-weight: 700; letter-spacing: -0.05em; line-height: 1; text-align: center; }
  .glass.take .k { font-size: 26px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }
  .glass.take .v { margin-top: 16px; font-size: 84px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.05; }
  .glass.list { display: flex; flex-direction: column; gap: 30px; }
  .glass.list .li { opacity: 0; display: flex; align-items: center; gap: 24px; font-size: 60px; font-weight: 650; letter-spacing: -0.02em; }
  .glass.list .li i { width: 18px; height: 18px; border-radius: 50%; background: var(--accent); flex: none; }
  .glass.imgcard { padding: 18px; } .glass.imgcard img { width: 100%; height: 420px; object-fit: cover; border-radius: 16px; display: block; }
  .glass.imgcard .pcap { font-size: 40px; font-weight: 650; padding: 18px 10px 4px; }
  .cap { position: absolute; left: 0; right: 0; bottom: 38px; display: flex; justify-content: center; opacity: 0; z-index: 5; }
  .cap .in { font-weight: 600; font-size: 42px; line-height: 1.3; padding: 10px 24px; border-radius: 14px;
             background: rgba(14,14,17,.80); color: #fff; backdrop-filter: blur(10px); }
  .cap .w { opacity: .6; } .cap .w.kw { background: linear-gradient(transparent 58%, color-mix(in oklch, var(--accent) 80%, transparent) 58%); padding: 0 4px; }
  #credit { position: absolute; right: 26px; top: 18px; font-size: 18px; color: rgba(255,255,255,.85); z-index: 6;
            text-shadow: 0 1px 4px rgba(0,0,0,.8); max-width: 1100px; text-align: right; }
</style>
</head>
<body>
<div id="root" class="__STYLE__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="ground"></div>
  <div id="spk" data-layout-allow-overflow><video id="v" src="footage.mp4" data-start="0" data-duration="__DUR__" data-track-index="0" data-media-start="0" muted playsinline></video></div>
__BLOCKS__
__CAPS__
  <div id="credit">__CREDIT__</div>
</div>
<script>
  const A = __ANIM__, C = __CAPANIM__, D = __DUR__, W = __W__, H = __H__;
  const STYLE = "__STYLE__";
  const L = {
    full: { left: 0, top: 0, width: W, height: H, borderRadius: 0, opacity: 1 },
    half: { left: 0, top: 0, width: W / 2, height: H, borderRadius: 0, opacity: 1 },
    board: { left: 0, top: 0, width: W, height: H, borderRadius: 0, opacity: 0 },
    crop: { left: 70, top: 120, width: W * 0.44, height: H * 0.64, borderRadius: 28, opacity: 1 },
    pip: { left: W - 470, top: H - 470, width: 400, height: 300, borderRadius: 22, opacity: 1 },
  };
  const tl = gsap.timeline({ paused: true });
  gsap.set("#spk", L.full);
  for (let k = 0; k < A.length; k++) {
    const a = A[k], id = "#bt" + a.i, next = A[k + 1];
    tl.to("#spk", Object.assign({ duration: 0.55, ease: "power2.inOut" }, L[a.layout]), a.t);
    tl.set(id, { opacity: 1 }, a.t + 0.5);
    const ink = document.querySelectorAll(id + " .ink path");
    ink.forEach((p, j) => {
      const len = p.getTotalLength();
      gsap.set(p, { strokeDasharray: len, strokeDashoffset: len });
      tl.to(p, { strokeDashoffset: 0, duration: Math.min(0.7, 0.25 + len / 1600), ease: "power1.inOut" }, a.t + 0.55 + j * 0.12);
    });
    tl.fromTo(id + " .hand", { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.6, stagger: 0.25, ease: "power1.inOut", immediateRender: false }, a.t + 0.6);
    tl.fromTo(id + " .glass, " + id + " .photo", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", immediateRender: false }, a.t + 0.55);
    tl.fromTo(id + " .li", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.35, stagger: 0.35, ease: "power2.out", immediateRender: false }, a.t + 0.85);
    tl.to(id, { opacity: 0, duration: 0.3, ease: "power1.in" }, a.e - 0.3);
    const gapToNext = next ? next.t - a.e : 99;
    // the content is gone before the speaker moves back: one motion at a time
    if (gapToNext > 0.8) tl.to("#spk", Object.assign({ duration: 0.55, ease: "power2.inOut" }, L.full), a.e);
  }
  for (const c of C) {
    if (c[0] === "cap") { tl.set("#" + c[1], { opacity: 1 }, c[2]); tl.set("#" + c[1], { opacity: 0 }, c[3]); }
    else tl.to("#" + c[1], { opacity: 1, duration: 0.06, ease: "none" }, c[2]);
  }
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""
