"""Write the HyperFrames compositions for the crewboard launch film from build/storyboard.json and build/rects.json:
build/hf-wide/index.html (1920x1080) and build/hf-tall/index.html (1080x1920).

The only product pixels are build/page.mp4: crewboard's real page, recorded by ui_render.mjs at 2x. Everything else
is camera, light, type and backdrop. Colours and fonts are read from crewboard's own theme (web/index.html, read
only): the room and type use its neutrals, the room light takes a third of the status colour a shot is about
(doing amber, waiting violet, done green), Geist for type and Geist Mono for the command and the URL.

Cameras: each shot names DOM blocks; their text and controls (from rects.json) give the focus rect, and solve()
moves the framing (and if needed shortens the push) until no frame edge cuts a line of text or a control at any
moment of the push, in every page state the shot shows. The solved cameras go to build/cameras.json, which the
edge gate in checks.py re-checks independently.
"""
import json
import math
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import storyboard as SBM  # noqa: E402

BUILD = SBM.BUILD
ROOT = HERE.parents[1]
THEME = Path(r"C:\Dev\crewboard\crewboard\web\index.html")
SRC = SBM.SCALE                    # page.mp4 px per CSS px
PW, PH = SBM.PAGE
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}


# ------------------------------------------------------------------ tokens from crewboard's theme
def oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    enc = [12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0) ** (1 / 2.4) - 0.055 for c in lin]
    return tuple(int(round(min(max(c, 0), 1) * 255)) for c in enc)


def tokens():
    css = THEME.read_text(encoding="utf-8")

    def block(sel):
        m = re.search(re.escape(sel) + r"([^}]*)\}", css)
        return dict(re.findall(r"--([a-z]+):\s*(oklch\([^)]*\))", m.group(1)))
    light = block(":root{color-scheme:light dark;")
    dark = block(':root[data-theme="dark"]{')
    font = re.search(r"family=([A-Za-z+]+):wght", css).group(1).replace("+", " ")

    def rgb(v):
        n = [float(x.rstrip("%")) / (100 if x.endswith("%") else 1) for x in re.findall(r"[\d.]+%?", v)]
        r = oklch_to_rgb(n[0], n[1], n[2])
        return r + ((n[3],) if len(n) > 3 else ())
    return {"font": font, "mono": font + " Mono", "dark": {k: rgb(v) for k, v in dark.items()},
            "light": {k: rgb(v) for k, v in light.items()}}


def css_rgb(c, a=None):
    if a is None and len(c) == 4:
        a = c[3]
    return "rgba(%d,%d,%d,%g)" % (c[0], c[1], c[2], a) if a is not None else "rgb(%d,%d,%d)" % c[:3]


def mix(c, n, k):
    return tuple(int(round(c[i] * k + n[i] * (1 - k))) for i in range(3))


# ------------------------------------------------------------------ framing
RECTS = json.loads((BUILD / "rects.json").read_text(encoding="utf-8"))


def state_at(t):
    st = RECTS["states"][0]
    for s in RECTS["states"]:
        if s["t"] <= t + 1e-6:
            st = s
    return st


def states_in(t0, t1):
    out = [state_at(t0)]
    out += [s for s in RECTS["states"] if t0 + 1e-6 < s["t"] < t1 - 1e-6]
    return out


def focus_rect(spec, st, clip_w=None):
    """The text lines and controls inside the bounding box of the named blocks (their content, not their full
    width), so everything between the first and the last named block is in focus."""
    if spec == ["page"]:
        return [0, 0, PW, PH]
    blocks = []
    for f in spec:
        sel, idx = (f, None) if isinstance(f, str) else f
        blocks += st["named"][sel] if idx is None else [st["named"][sel][idx]]
    bx0 = min(e[0] for e in blocks)
    by0 = min(e[1] for e in blocks)
    bx1 = max(e[0] + e[2] for e in blocks)
    by1 = max(e[1] + e[3] for e in blocks)
    boxes = [r[:4] for r in st["text"] + st["controls"]
             if r[0] >= bx0 - 1 and r[1] >= by0 - 1 and r[0] + r[2] <= bx1 + 1 and r[1] + r[3] <= by1 + 1
             and (clip_w is None or r[0] + r[2] <= bx0 + clip_w)]
    if not boxes:
        raise SystemExit("empty focus %s" % spec)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def frame_css(cx, cy, z, sx, sy, W, H):
    return cx - sx / z, cy - sy / z, cx + (W - sx) / z, cy + (H - sy) / z


# Screen regions (x0, x1, y0, y1) where the type scrim (16:9: the left type column; 9:16: the top band) or the
# 9:16 bottom fade is at least ~90 % opaque: a line wholly inside one cannot be seen, so an edge may cross it.
INF = 1e9
OPAQUE = {"wide": [(-INF, 715, -INF, INF)], "tall": [(-INF, INF, -INF, 455), (-INF, INF, 1690, INF)]}
# The out-of-focus surround: everything outside the focus rect padded by SPOT_PAD + SPOT_SOFT CSS px is dimmed and
# blurred (the #spot layer), so a side edge crossing a line that sits wholly in it is a soft bleed, not a cut. Top and
# bottom edges get no such pass: a row sliced by them reads as a bad crop even when it is out of focus.
SPOT_PAD, SPOT_SOFT = 14, 17


def _arr(sts):
    rows = []
    for st in sts:
        for r in st["text"] + st["controls"]:
            rows.append(r[:4])
    return np.array(rows, dtype=float)


def edge_cuts(cam, fmt, sts, labels=False):
    """Lines of text / controls that a frame edge cuts at any of 13 moments of the push, unless the line sits wholly
    under an opaque type region, or (left and right edges only) wholly in the out-of-focus surround."""
    W, H = SIZE[fmt]
    cx, cy, z0, sx, sy = cam["from"]
    z1 = cam["to"][2]
    A = _arr(sts)
    x0, y0, x1, y1 = A[:, 0], A[:, 1], A[:, 0] + A[:, 2], A[:, 1] + A[:, 3]
    bad = np.zeros(len(A), bool)
    for k in range(13):
        z = z0 + (z1 - z0) * k / 12
        L, T, R, B = frame_css(cx, cy, z, sx, sy, W, H)
        vis = ~((x1 < L) | (x0 > R) | (y1 < T) | (y0 > B))
        cut_lr = (x0 < L - 0.5) & (L - 0.5 < x1) | (x0 < R + 0.5) & (R + 0.5 < x1)
        cut_tb = (y0 < T - 0.5) & (T - 0.5 < y1) | (y0 < B + 0.5) & (B + 0.5 < y1)
        sx0, sx1, sy0, sy1 = (x0 - L) * z, (x1 - L) * z, (y0 - T) * z, (y1 - T) * z
        opaque = np.zeros(len(A), bool)
        for a, b, c, d in OPAQUE[fmt]:
            opaque |= (sx0 >= a) & (sx1 <= b) & (sy0 >= c) & (sy1 <= d)
        soft = np.zeros(len(A), bool)
        if cam.get("spot"):
            fx, fy, fw, fh = cam["focus"]
            m = SPOT_PAD + SPOT_SOFT
            soft = (x1 < fx - m) | (x0 > fx + fw + m) | (y1 < fy - m) | (y0 > fy + fh + m)
        bad |= vis & ((cut_lr & ~(opaque | soft)) | (cut_tb & ~opaque))
    if not labels:
        return int(bad.sum())
    names = [r[4] if len(r) > 4 else "control" for st in sts for r in st["text"] + st["controls"]]
    return [names[i] for i in np.nonzero(bad)[0]]


def solve(shot, fmt):
    spec = shot[fmt]
    sts = states_in(shot["t"], shot["end"])
    fx, fy, fw, fh = focus_rect(spec["focus"], sts[0], spec.get("clip_w"))
    anchor = spec.get("anchor", "center")    # which point of the focus the camera holds still during the push
    cx = {"left": fx, "right": fx + fw}.get(anchor, fx + fw / 2)
    if "hold_x" in spec:                     # a page x (CSS px) held at screen x `at[0]` for the whole push
        cx = spec["hold_x"]
    cy = fy + fh / 2
    z0, z1 = spec["z"]
    sx, sy = spec["at"]
    spot = not (shot.get("hero") or shot.get("dof") or shot.get("hide_page") or shot.get("whole"))
    cam = {"from": [cx, cy, z0, sx, sy], "to": [cx, cy, z1, sx, sy], "focus": [fx, fy, fw, fh], "spot": spot}
    if shot.get("hero") or shot.get("dof") or shot.get("hide_page") or shot.get("whole"):
        return cam, 0
    offs = sorted(((dx, dy) for dx in range(-200, 201, 4) for dy in range(-90, 91, 3)),
                  key=lambda d: 2 * abs(d[0]) + abs(d[1]))
    for shrink in range(0, 11):
        zz0, zz1 = z0 * (1 - 0.02 * shrink), z1 * (1 - 0.02 * shrink)
        for dx, dy in offs:
            c = {"from": [cx + dx, cy + dy, zz0, sx, sy], "to": [cx + dx, cy + dy, zz1, sx, sy],
                 "focus": [fx, fy, fw, fh], "spot": spot}
            if not edge_cuts(c, fmt, sts):
                return c, (dx, dy, shrink)
    raise SystemExit("no clean framing for %s %s: %s" % (shot["id"], fmt, edge_cuts(cam, fmt, sts, True)[:8]))


# ------------------------------------------------------------------ composition
def grain(path):
    rng = np.random.default_rng(3)
    g = (rng.standard_normal((512, 512)) * 38 + 128).clip(0, 255).astype(np.uint8)
    Image.fromarray(g, "L").save(path)


def build(fmt):
    sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
    tok = tokens()
    W, H = SIZE[fmt]
    out = BUILD / ("hf-" + fmt)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(BUILD / "page.mp4", out / "page.mp4")
    grain(out / "grain.png")
    fonts = out / "fonts"
    fonts.mkdir(exist_ok=True)
    faces = []
    for fam, slug, wgts in ((tok["font"], "geist", (400, 500, 600)), (tok["mono"], "geist-mono", (400, 500))):
        for w in wgts:
            name = "%s-latin-%d-normal.woff2" % (slug, w)
            shutil.copyfile(ROOT / "node_modules" / "@fontsource" / slug / "files" / name, fonts / name)
            faces.append("@font-face { font-family: '%s'; font-weight: %d; font-style: normal; "
                         "src: url('fonts/%s') format('woff2'); }" % (fam, w, name))
    D, Lt = tok["dark"], tok["light"]
    neutral = (138, 140, 146)
    lights = {"neutral": neutral, "neutral-light": (196, 196, 200),
              "doing": mix(D["doing"], neutral, 0.38), "waiting": mix(D["waiting"], neutral, 0.38),
              "done": mix(D["done"], neutral, 0.38)}
    cams, solved = [], {}
    for s in sb["shots"]:
        c, moved = solve(s, fmt)
        solved[s["id"]] = {"cam": c, "moved": moved}
        if moved:
            print("  %s %s: framing moved %s" % (fmt, s["id"], moved))
        st = state_at(s["t"])
        cams.append({"id": s["id"], "t": s["t"], "end": s["end"], "from": c["from"], "to": c["to"],
                     "focus": c["focus"], "hero": bool(s.get("hero")), "dof": bool(s.get("dof")),
                     "hide": bool(s.get("hide_page")), "light": "%d,%d,%d" % lights[s["light"]],
                     "theme": st["theme"], "spot": c.get("spot", False), "tilt": s[fmt].get("tilt")})
    cfile = BUILD / "cameras.json"
    allc = json.loads(cfile.read_text(encoding="utf-8")) if cfile.exists() else {}
    allc[fmt] = solved
    cfile.write_text(json.dumps(allc, indent=1), encoding="utf-8")
    types = []
    for k, v in sb["type"].items():
        if k == "end":
            continue
        types.append({"id": k, "t": v["t"], "end": v["end"], "head": (v.get("head_" + fmt) or v.get("head_two") or v.get("head_tall")
                                                               or v["head"]),
                      "term": v.get("term"), "dot": "%d,%d,%d" % D[v["dot"]][:3] if v.get("dot") else None,
                      "pulse": v.get("dot") == "doing"})
    end = sb["type"]["end"]
    rep = {"__W__": W, "__H__": H, "__DUR__": "%.3f" % sb["duration"], "__UIEND__": "%.3f" % sb["ui_end"],
           "__PW__": PW * SRC, "__PH__": PH * SRC, "__SRC__": SRC, "__FMT__": fmt,
           "__CAMS__": json.dumps(cams), "__TYPES__": json.dumps(types), "__TE__": end["t"],
           "__FONTFACES__": "\n  ".join(faces), "__FONT__": tok["font"], "__MONO__": tok["mono"],
           "__BG__": css_rgb(D["bg"]), "__CARD__": css_rgb(D["card"]), "__FG__": css_rgb(D["fg"]),
           "__MFG__": css_rgb(D["mfg"]), "__BORDER__": css_rgb(D["border"]), "__BORDERL__": css_rgb(Lt["border"]),
           "__MUTED__": css_rgb(D["muted"]), "__RING__": "%d,%d,%d" % D["ring"][:3], "__DOING__": "%d,%d,%d" % D["doing"][:3],
           "__END_HEAD__": end["head"], "__END_SUB__": end.get("sub_" + fmt, end["sub"]), "__END_URL__": end["url"]}
    page = TEMPLATE
    for k, v in rep.items():
        page = page.replace(k, str(v))
    (out / "index.html").write_text(page, encoding="utf-8")
    print("composition:", out / "index.html")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  __FONTFACES__
  :root { --bg: __BG__; --card: __CARD__; --fg: __FG__; --mfg: __MFG__; --border: __BORDER__; --muted: __MUTED__; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: var(--bg); }
  body { font-family: "__FONT__", ui-sans-serif, system-ui, sans-serif; color: var(--fg); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden;
          background: radial-gradient(75% 62% at 50% 40%, rgba(__RING__,0.58) 0%, rgba(__RING__,0.26) 42%, rgba(0,0,0,0) 80%),
                      radial-gradient(120% 95% at 50% 30%, var(--muted) 0%, var(--card) 38%, var(--bg) 100%); }
  #root.tall { background: radial-gradient(85% 42% at 50% 50%, rgba(__RING__,0.55) 0%, rgba(__RING__,0.22) 45%, rgba(0,0,0,0) 82%),
                            radial-gradient(120% 70% at 50% 45%, var(--muted) 0%, var(--card) 40%, var(--bg) 100%); }
  #stage { position: absolute; inset: 0; opacity: 0; }
  #roomdim { position: absolute; inset: 0; background: rgba(10,10,10,0.45); opacity: 0; pointer-events: none; }
  #light { position: absolute; left: -20%; top: -30%; width: 140%; height: 120%; opacity: 0.08;
           background: radial-gradient(48% 42% at 50% 46%, rgb(var(--lc)) 0%, rgba(0,0,0,0) 72%); }
  #frame { position: absolute; inset: 0;
           -webkit-mask-image: linear-gradient(to right, transparent 0, #000 2.5%, #000 97.5%, transparent 100%),
                               linear-gradient(to bottom, transparent 0, #000 2%, #000 98%, transparent 100%);
           -webkit-mask-composite: source-in; mask-composite: intersect; }
  #cam { position: absolute; left: 0; top: 0; width: __PW__px; height: __PH__px; transform-origin: 0 0; }
  #dof { position: absolute; inset: 0; transform-origin: 50% 50%; }
  #glow { position: absolute; left: -50px; top: -50px; right: -50px; bottom: -50px; border-radius: 80px; pointer-events: none;
          background: rgb(var(--lc)); filter: blur(160px); opacity: 0; }
  #slab { position: absolute; left: 0; top: 0; width: __PW__px; height: __PH__px; border-radius: 24px; overflow: hidden;
          box-shadow: 0 100px 200px rgba(0,0,0,0.80), 0 34px 70px rgba(0,0,0,0.55), 0 0 0 2px rgba(255,255,255,0.15); }
  #slab.light { box-shadow: 0 90px 180px rgba(0,0,0,0.62), 0 30px 60px rgba(0,0,0,0.38), 0 0 0 2px __BORDERL__; }
  #slab video { position: absolute; left: 0; top: 0; width: __PW__px; height: __PH__px; }
  #rim { position: absolute; inset: 0; border-radius: 24px; pointer-events: none;
         box-shadow: inset 0 3px 0 rgba(255,255,255,0.42), inset 0 0 0 2px rgba(255,255,255,0.10); }
  #sheen { position: absolute; left: -60%; top: 0; width: 220%; height: 100%; pointer-events: none; opacity: 0;
           background: linear-gradient(105deg, rgba(255,255,255,0) 35%, rgba(255,255,255,0.10) 47%, rgba(255,255,255,0) 60%); }
  #spot { position: absolute; inset: 0; pointer-events: none; opacity: 0; background: rgba(10,10,10,0.64);
          -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
  #key { position: absolute; inset: 0; pointer-events: none; border-radius: 24px;
         background: linear-gradient(to bottom, rgba(255,255,255,0.085) 0%, rgba(255,255,255,0.025) 40%, rgba(255,255,255,0) 70%); }
  #vig { position: absolute; inset: 0; pointer-events: none;
         background: radial-gradient(120% 100% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%); }
  #grain { position: absolute; inset: 0; pointer-events: none; opacity: 0.045; mix-blend-mode: overlay;
           background-image: url(grain.png); background-size: 512px 512px; }
  .scrim { position: absolute; left: 0; right: 0; pointer-events: none; opacity: 0; }
  .wide #scrim { left: 0; right: auto; top: 0; bottom: 0; width: 1080px;
                 background: linear-gradient(to right, rgba(10,10,10,1) 0%, rgba(10,10,10,0.97) 66%, rgba(10,10,10,0.6) 84%, rgba(10,10,10,0) 100%); }
  .tall #scrim { top: 0; height: 40%;
                 background: linear-gradient(to top, rgba(10,10,10,0) 0%, rgba(10,10,10,0.92) 40%, rgba(10,10,10,1) 62%); }
  .tall #fadeB { position: absolute; left: 0; right: 0; bottom: 0; height: 30%; pointer-events: none;
                 background: linear-gradient(to bottom, rgba(10,10,10,0) 0%, rgba(10,10,10,0.9) 60%, rgba(10,10,10,1) 100%); }
  .type { position: absolute; opacity: 0; }
  .type .h { font-weight: 600; letter-spacing: -0.035em; line-height: 1.04; color: var(--fg); white-space: pre-line; }
  .wd { display: inline-block; overflow: hidden; vertical-align: top; padding-bottom: 0.12em; margin-bottom: -0.12em; }
  .wd > span { display: inline-block; opacity: 0; }
  .dot { position: relative; display: inline-block; width: 0.40em; height: 0.40em; border-radius: 50%; margin-right: 0.30em;
         vertical-align: 0.14em; opacity: 0; }
  .dot i { position: absolute; inset: 0; border-radius: 50%; background: inherit; opacity: 0; }
  .wide .type { left: 128px; top: 540px; width: 800px; transform: translateY(-50%); }
  .wide .type .h { font-size: 84px; }
  .tall .type { left: 72px; right: 72px; top: 250px; text-align: center; }
  .tall .type .h { font-size: 100px; }
  .term { position: absolute; white-space: nowrap; opacity: 0; transform-origin: 50% 50%; transform-style: preserve-3d;
          font-family: "__MONO__", ui-monospace, monospace; font-weight: 400; color: var(--fg); letter-spacing: -0.01em;
          border: 2px solid rgba(255,255,255,0.13); border-radius: 24px; background: rgba(19,19,19,0.88);
          box-shadow: 0 60px 120px rgba(0,0,0,0.6), 0 20px 40px rgba(0,0,0,0.4), inset 0 2px 0 rgba(255,255,255,0.08); }
  .term .l { display: block; } .term .l + .l { color: var(--mfg); opacity: 0; }
  .wide .term { left: 960px; top: 400px; font-size: 38px; line-height: 1.7; padding: 48px 56px; }
  .tall .term { left: 0; right: 0; margin: 0 auto; width: max-content; top: 900px; font-size: 33px; line-height: 1.7; padding: 40px 44px; }
  #endcard { position: absolute; left: 0; right: 0; text-align: center; }
  .wide #endcard { top: 360px; }
  .tall #endcard { top: 720px; }
  #endcard .wm { font-size: 176px; font-weight: 600; letter-spacing: -0.05em; line-height: 1; opacity: 0; }
  #endcard .wm .wd > span { opacity: 1; }
  #endcard .ln { white-space: pre-line; margin-top: 34px; font-size: 56px; color: var(--mfg); letter-spacing: -0.015em; opacity: 0; }
  #endcard .url { display: inline-block; margin-top: 40px; font-size: 44px; font-family: "__MONO__", ui-monospace, monospace;
                  color: rgb(__DOING__); opacity: 0; border: 2px solid rgba(255,255,255,0.14); border-radius: 999px; padding: 16px 40px; }
  .tall #endcard .wm { font-size: 170px; }
  .tall #endcard .ln { font-size: 60px; padding: 0 60px; line-height: 1.25; }
  .tall #endcard .url { font-size: 42px; }
  #black { position: absolute; inset: 0; background: #000; opacity: 0; pointer-events: none; }
</style>
</head>
<body>
<div id="root" class="__FMT__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="stage" style="--lc: 138,140,146">
    <div id="roomdim"></div>
    <div id="light"></div>
    <div id="frame">
      <div id="cam" data-layout-allow-overflow>
        <div id="dof">
          <div id="glow"></div>
          <div id="slab">
            <video id="pv" src="page.mp4" data-start="0" data-duration="__UIEND__" data-track-index="0" muted playsinline></video>
            <div id="spot"></div>
            <div id="key"></div>
            <div id="sheen"></div>
            <div id="rim"></div>
          </div>
        </div>
      </div>
    </div>
    <div id="vig"></div>
    <div id="fadeB"></div>
    <div class="scrim" id="scrim"></div>
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
  const CAMS = __CAMS__, TYPES = __TYPES__, SRC = __SRC__, DUR = __DUR__, TE = __TE__;
  const holder = document.getElementById("types");
  for (const ty of TYPES) {
    const d = document.createElement("div");
    d.className = "type"; d.id = "ty_" + ty.id;
    d.innerHTML = '<div class="h"></div>';
    const h = d.querySelector(".h");
    if (ty.dot) {
      const dt = document.createElement("span"); dt.className = "dot"; dt.style.background = "rgb(" + ty.dot + ")";
      dt.appendChild(document.createElement("i")); h.appendChild(dt);
    }
    ty.head.split(String.fromCharCode(10)).forEach((line, li) => {
      if (li) h.appendChild(document.createElement("br"));
      line.split(" ").forEach((w, wi) => {
        if (wi) h.appendChild(document.createTextNode(" "));
        const o = document.createElement("span"); o.className = "wd";
        const i = document.createElement("span"); i.textContent = w; o.appendChild(i); h.appendChild(o);
      });
    });
    holder.appendChild(d);
    if (ty.term) {
      const p = document.createElement("div"); p.className = "term"; p.id = "term_" + ty.id;
      ty.term.forEach((line, li) => {
        const l = document.createElement("span"); l.className = "l";
        for (const ch of line) { const c = document.createElement("span"); c.className = li ? "o" : "c"; c.textContent = ch; l.appendChild(c); }
        p.appendChild(l);
      });
      document.getElementById("stage").appendChild(p);
    }
  }
  // the dimmed surround: everything outside the focus rect (padded, soft edges), as a mask on the spot layer
  function spotMask(f) {
    const pad = 14, soft = 34;
    const L = (f[0] - pad) * SRC, T = (f[1] - pad) * SRC, R = (f[0] + f[2] + pad) * SRC, B = (f[1] + f[3] + pad) * SRC;
    const gx = "linear-gradient(to right, #000 0px, #000 " + (L - soft) + "px, transparent " + L + "px, transparent " + R + "px, #000 " + (R + soft) + "px, #000 100%)";
    const gy = "linear-gradient(to bottom, #000 0px, #000 " + (T - soft) + "px, transparent " + T + "px, transparent " + B + "px, #000 " + (B + soft) + "px, #000 100%)";
    return gx + ", " + gy;
  }
  const tl = gsap.timeline({ paused: true });
  const pos = (p) => ({ x: p[3] - p[2] * p[0], y: p[4] - p[2] * p[1], scale: p[2] / SRC });
  tl.fromTo("#stage", { opacity: 0 }, { opacity: 1, duration: 0.6, ease: "power2.out" }, 0);
  // the studio backdrop is brightest for the opening object shot, then settles lower under the feature shots
  tl.to("#roomdim", { opacity: 1, duration: 0.5, ease: "sine.inOut", immediateRender: false }, CAMS[1].t);
  for (const c of CAMS) {
    tl.set("#cam", pos(c.from), c.t);
    tl.to("#cam", { ...pos(c.to), duration: c.end - c.t, ease: c.hero ? "power2.inOut" : "power2.out" }, c.t);
    tl.set("#dof", { filter: c.dof ? "blur(30px)" : "blur(0px)", opacity: c.dof ? 0.45 : 1 }, c.t);
    tl.set("#cam", { opacity: c.hide ? 0 : 1 }, c.t);
    tl.set("#slab", { attr: { class: c.theme === "light" ? "light" : "dark" } }, c.t);
    tl.set("#spot", { opacity: c.spot ? 1 : 0, webkitMaskImage: spotMask(c.focus), maskImage: spotMask(c.focus) }, c.t);
    tl.to("#stage", { "--lc": c.light, duration: 0.45, ease: "sine.inOut", immediateRender: false }, c.t);
    if (c.hero) {
      const k = c.tilt || [18, -12, 0, 0];   // the page turns toward the camera as it settles
      tl.fromTo("#dof", { rotationX: k[0], rotationY: k[1], transformPerspective: 6000 },
                { rotationX: k[2], rotationY: k[3], duration: c.end - c.t, ease: "power3.out" }, c.t);
      tl.set("#dof", { rotationX: 0, rotationY: 0 }, c.end);
      tl.fromTo("#sheen", { opacity: 1, xPercent: -18 }, { xPercent: 22, opacity: 0, duration: c.end - c.t, ease: "power2.out" }, c.t);
    }
  }
  // type: one block per shot; the words rise in after the camera has started and the surround has dimmed
  for (const ty of TYPES) {
    const el = "#ty_" + ty.id;
    tl.set(el, { opacity: 1 }, ty.t);
    if (ty.dot) {
      tl.fromTo(el + " .dot", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.4, ease: "power3.out", immediateRender: false }, ty.t + 0.12);
      if (ty.pulse) {   // crewboard's own live pulse: scale 1 -> 2.6, fade out, 1.8 s, ease-out
        const n = Math.max(0, Math.floor((ty.end - ty.t - 0.5) / 1.8));
        tl.fromTo(el + " .dot i", { scale: 1, opacity: 0.6 }, { scale: 2.6, opacity: 0, duration: 1.8, ease: "power2.out", repeat: n, immediateRender: false }, ty.t + 0.5);
      }
    }
    tl.set("#scrim", { opacity: 1 }, ty.t);
    tl.fromTo(el + " .wd > span", { yPercent: 110, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.55, ease: "power3.out", stagger: 0.06, immediateRender: false }, ty.t + 0.12);
    if (ty.term) {
      // the card rises in with the command on it, then the line the command prints appears
      const card = "#term_" + ty.id, t0 = ty.t;
      tl.fromTo(card, { opacity: 0.25, y: 24, rotationX: 14, rotationY: -12, transformPerspective: 2400 },
                { opacity: 1, y: 0, rotationX: 0, rotationY: 0, duration: 1.2, ease: "power3.out", immediateRender: false }, t0);
      tl.fromTo(card + " .l + .l", { opacity: 0 }, { opacity: 1, duration: 0.35, ease: "power2.out", immediateRender: false }, t0 + 0.75);
      tl.fromTo(card, { scale: 1 }, { scale: 1.04, duration: ty.end - t0, ease: "sine.inOut", immediateRender: false }, t0);
      tl.set(card, { opacity: 0 }, ty.end);
    }
    tl.set(el, { opacity: 0 }, ty.end);
  }
  tl.set("#scrim", { opacity: 0 }, TE);
  tl.set("#endcard .wm", { opacity: 1 }, TE);
  tl.fromTo("#endcard .wm .wd > span", { yPercent: 110 }, { yPercent: 0, duration: 0.7, ease: "power3.out", immediateRender: false }, TE);
  tl.fromTo("#endcard .ln", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, TE + 0.55);
  tl.fromTo("#endcard .url", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, TE + 1.05);
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
