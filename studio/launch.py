"""Product-launch film from real product screens: render(brief, out_mp4, width, height) -> manifest.

    brief = {"product": "crewboard",
             "tokens": {"bg": "#0a0a0a", "fg": "#fafafa", "accent": "#a78bfa", "font": "Inter", "mono": "Geist Mono",
                        "radius": 14},
             "features": [{"title": "Every session, live", "asset": "board.png", "focus": [x, y, w, h],
                           "cursor": [x, y, w, h] or None, "asset_size": [w, h]}],      # pixels of the asset
             "end": {"title": "crewboard", "sub": "python -m crewboard --open"},
             "music": None or path (with "bpm"), "voice": None}
    manifest = {"cuts": [...], "shots": [{"start", "end", "asset"}], "style": "launch", "version": VERSION, ...}

The look (skills/product-launch/SKILL.md has the why): the real app in a plain window on a background made from
the product's own tokens; it settles from a 3D tilt, then each feature is one shot, cut on the beat, the camera
already pushing into the part of the screen that matters (the screen bleeds off frame), a rack focus, a soft
spotlight on that part, then a short title. One motion at a time, every move eased. A cursor and click only where
the brief gives a real target. A strong end card with the name and the install line. No voiceover.
Every value on screen comes from the brief: no invented UI, no stock, no generated people.
"""
import html
import json
import shutil
from pathlib import Path

from . import hf, media, music

VERSION = "3"   # 3: words and end card start hidden (staggered reveal fix)
BPM = 120


def esc(s):
    return html.escape(str(s), quote=True)


def _beats(chars, beat, minimum):
    """Shot length in beats: at least `minimum`, and long enough to read the title (chars / 20 per second)."""
    need = 0.9 + chars / 20.0
    b = minimum
    while b * beat < need:
        b += 1
    return b


def plan(brief, beat):
    """Shot list on the beat grid: establishing, one per feature, end card."""
    shots, t = [], 0.0
    feats = brief["features"]
    est_b = 3
    shots.append({"kind": "establish", "start": 0.0, "beats": est_b, "asset": feats[0]["asset"], "feature": 0})
    t = est_b * beat
    for i, f in enumerate(feats):
        b = _beats(len(f["title"]), beat, 3 if not f.get("cursor") else 4)
        shots.append({"kind": "feature", "start": round(t, 3), "beats": b, "asset": f["asset"], "feature": i})
        t += b * beat
    end = brief.get("end") or {}
    eb = max(5, _beats(len(end.get("title", "")) + len(end.get("sub", "")), beat, 5))
    shots.append({"kind": "end", "start": round(t, 3), "beats": eb, "asset": None})
    t += eb * beat
    for s in shots:
        s["end"] = round(s["start"] + s["beats"] * beat, 3)
    return shots, round(t, 3)


def _pose(feature, size, frame, vertical, win):
    """Camera pose (x, y, scale) that puts the feature's focus rect where the frame wants it."""
    W, H = frame
    Ww, Wh = win
    aw, ah = size
    fx, fy, fw, fh = (feature.get("focus_v") if vertical else None) or feature.get("focus") or [0, 0, aw, ah]
    fw_f, fh_f = fw / aw, fh / ah
    if vertical:
        s = min(0.84 * W / (fw_f * Ww), 0.36 * H / (fh_f * Wh))
        tx, ty = W * 0.5, H * 0.54
    else:
        s = min(0.54 * W / (fw_f * Ww), 0.70 * H / (fh_f * Wh))
        tx, ty = W * 0.68, H * 0.50
    s = max(1.0, min(s, 3.2))
    dx = ((fx + fw / 2) / aw - 0.5) * Ww
    dy = ((fy + fh / 2) / ah - 0.5) * Wh + TITLEBAR / 2.0
    return {"x": round(tx - W / 2 - s * dx, 1), "y": round(ty - H / 2 - s * dy, 1), "scale": round(s, 4)}


TITLEBAR = 34


def build(brief, out_dir, width, height, beat):
    out = Path(out_dir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    tok = dict({"bg": "#0b0b0d", "fg": "#f4f4f6", "accent": "#a78bfa", "font": "Inter", "mono": "JetBrains Mono",
                "radius": 14}, **(brief.get("tokens") or {}))
    vertical = height > width
    W, H = width, height
    Ww = int(W * (0.86 if vertical else 0.74))
    feats = brief["features"]
    sizes = []
    imgs = []
    for i, f in enumerate(feats):
        src = Path(f["asset"])
        name = "img/s%d%s" % (i, src.suffix)
        shutil.copyfile(src, out / name)
        sizes.append(f.get("asset_size") or _size(src))
        imgs.append(name)
    aw, ah = sizes[0]
    Wh = int(Ww * ah / aw)
    shots, total = plan(brief, beat)
    screens = "\n".join('<img class="scr" id="scr%d" src="%s" alt="">' % (i, esc(n)) for i, n in enumerate(imgs))
    spots, titles, anim = [], [], []
    for k, s in enumerate(shots):
        if s["kind"] == "establish":
            if vertical:
                # a tall frame cannot show a wide app whole: settle on a wide view of the first feature's region
                p = _pose(feats[0], sizes[0], (W, H), vertical, (Ww, Wh))
                to = {"x": 0, "y": -H * 0.04, "scale": 0.92 * W / Ww}     # the whole window, inside the frame
                frm = {"x": 0, "y": H * 0.02, "scale": to["scale"] * 0.88}
            else:
                to = {"x": 0, "y": H * 0.02, "scale": 1.04}
                frm = {"x": 0, "y": H * 0.08, "scale": 0.92}
            anim.append({"k": "est", "t": s["start"], "e": s["end"], "scr": 0,
                         "from": dict(frm, rx=22, ry=0 if vertical else -16, rz=0),
                         "to": dict(to, rx=0, ry=0, rz=0)})
        elif s["kind"] == "feature":
            f = feats[s["feature"]]
            p = _pose(f, sizes[s["feature"]], (W, H), vertical, (Ww, Wh))
            sp = None
            if f.get("focus"):
                fx, fy, fw, fh = (f.get("focus_v") if vertical else None) or f["focus"]
                sw, sh = sizes[s["feature"]]
                pad = 0.006 * sw                 # the outline sits just clear of the UI it frames
                fx, fy, fw, fh = fx - pad, fy - pad, fw + 2 * pad, fh + 2 * pad
                sp = [fx / sw, fy / sh, fw / sw, fh / sh]
                spots.append('<div class="spot" id="spot%d" style="left:%.3f%%;top:%.3f%%;width:%.3f%%;height:%.3f%%">'
                             '</div>' % (k, sp[0] * 100, sp[1] * 100, sp[2] * 100, sp[3] * 100))
            cur = ring = None
            if f.get("cursor"):
                cx, cy, cw, ch = f["cursor"]
                sw, sh = sizes[s["feature"]]
                cur = [(cx + cw * 1.02) / sw, (cy + ch * 1.0) / sh]   # the tip rests beside the label
                ring = [(cx + cw / 2) / sw, (cy + ch / 2) / sh]        # the click lands on its centre
            words = f["title"].split()
            titles.append('<div class="title" id="ti%d">%s</div>' % (k, " ".join(
                '<span class="w">%s</span>' % esc(w) for w in words)))
            anim.append({"k": "feat", "t": s["start"], "e": s["end"], "scr": s["feature"], "pose": p,
                         "spot": ("#spot%d" % k) if sp else None, "title": "#ti%d" % k, "cursor": cur,
                         "ring": ring})
        else:
            anim.append({"k": "end", "t": s["start"], "e": s["end"]})
    end = brief.get("end") or {}
    page = (TEMPLATE.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", "%.3f" % total)
            .replace("__WW__", str(Ww)).replace("__WH__", str(Wh)).replace("__TB__", str(TITLEBAR))
            .replace("__BG__", tok["bg"]).replace("__FG__", tok["fg"]).replace("__ACCENT__", tok["accent"])
            .replace("__FONT__", tok["font"]).replace("__MONO__", tok["mono"]).replace("__RADIUS__", str(tok["radius"]))
            .replace("__SCREENS__", screens).replace("__SPOTS__", "\n".join(spots))
            .replace("__TITLES__", "\n".join(titles)).replace("__CLASS__", "v" if vertical else "h")
            .replace("__END_TITLE__", esc(end.get("title", brief.get("product", ""))))
            .replace("__END_SUB__", esc(end.get("sub", ""))).replace("__ANIM__", json.dumps(anim))
            .replace("__FONTFACES__", font_faces([tok["font"], tok["mono"]], out))
            .replace("__VERTICAL__", "true" if vertical else "false"))
    (out / "index.html").write_text(page, encoding="utf-8")
    return shots, total


ROOT = Path(__file__).resolve().parents[1]


def font_faces(families, comp):
    """@font-face rules for token fonts that HyperFrames cannot fetch itself, from Fontsource packages in
    node_modules (npm i @fontsource/<name>); the woff2 files are copied next to the composition."""
    rules = []
    for fam in families:
        slug = fam.lower().replace(" ", "-")
        d = ROOT / "node_modules" / "@fontsource" / slug / "files"
        if not d.exists():
            continue
        (comp / "fonts").mkdir(exist_ok=True)
        for wgt in (400, 500, 600, 700):
            f = d / ("%s-latin-%d-normal.woff2" % (slug, wgt))
            if f.exists():
                shutil.copyfile(f, comp / "fonts" / f.name)
                rules.append("@font-face { font-family: '%s'; font-weight: %d; font-style: normal; "
                             "src: url('fonts/%s') format('woff2'); }" % (fam, wgt, f.name))
    return "\n  ".join(rules)


def _size(p):
    from PIL import Image
    with Image.open(p) as im:
        return list(im.size)


def render(brief, out_mp4, width=1920, height=1080, work=None, quality="high"):
    """Compose, render, put the music under it, and return the manifest (content-studio's contract)."""
    out_mp4 = Path(out_mp4)
    work = Path(work) if work else out_mp4.with_suffix("")
    comp = work / ("comp-%dx%d" % (width, height))
    bpm = (brief.get("music_bpm") if brief.get("music") else None) or BPM
    beat = 60.0 / bpm
    shots, total = build(brief, comp, width, height, beat)
    end_t = [s for s in shots if s["kind"] == "end"][0]["start"]
    if brief.get("music"):
        track = {"file": str(brief["music"]), "bpm": bpm, "licence": brief.get("music_licence", "supplied in the brief")}
    else:
        track = music.launch_track(total, work / "track.wav", bpm=bpm, hit_at=end_t)
    silent = comp / "render.mp4"
    hf.render(comp, silent, quality=quality)
    media.mux_loud(silent, track["file"], out_mp4)
    return {"cuts": [s["start"] for s in shots[1:]], "shots": [{"start": s["start"], "end": s["end"],
                                                                "asset": s["asset"], "kind": s["kind"]} for s in shots],
            "style": "launch", "version": VERSION, "duration": total, "bpm": bpm,
            "holds": [[end_t, total]],          # the end card stands still on purpose
            "texts": [f["title"] for f in brief["features"]] + [brief.get("end", {}).get("title", ""),
                                                               brief.get("end", {}).get("sub", "")],
            "music": {"file": Path(track["file"]).name, "licence": track["licence"]}, "voice": None,
            "composition": str(comp / "index.html")}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  __FONTFACES__
  :root { --bg: __BG__; --fg: __FG__; --accent: __ACCENT__; --r: __RADIUS__px; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: var(--bg); }
  body { font-family: "__FONT__", ui-sans-serif, system-ui, sans-serif; color: var(--fg); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden; background: var(--bg); }
  #bgfx { position: absolute; inset: -10%;
          background: radial-gradient(55% 55% at 72% 18%, color-mix(in oklch, var(--accent) 34%, transparent), transparent 72%),
                      radial-gradient(60% 50% at 12% 92%, color-mix(in oklch, var(--accent) 14%, transparent), transparent 70%),
                      radial-gradient(46% 44% at 50% 50%, color-mix(in oklch, var(--fg) 15%, transparent), transparent 78%),
                      linear-gradient(180deg, color-mix(in oklch, var(--bg) 88%, var(--fg)), var(--bg)); }
  #grain { position: absolute; inset: 0; opacity: 0.05; mix-blend-mode: overlay;
           background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
  #stage { position: absolute; inset: 0; perspective: 1800px; perspective-origin: 50% 40%;
           -webkit-mask-image: linear-gradient(to right, transparent 0, #000 7%, #000 93%, transparent 100%),
                               linear-gradient(to bottom, transparent 0, #000 6%, #000 94%, transparent 100%);
           -webkit-mask-composite: source-in; mask-composite: intersect; }
  #win { position: absolute; left: calc(50% - __WW__px / 2); top: calc(50% - (__WH__px + __TB__px) / 2);
         width: __WW__px; border-radius: var(--r); overflow: hidden; transform-origin: 50% 50%;
         background: var(--bg); border: 1px solid color-mix(in oklch, var(--fg) 38%, transparent);
         box-shadow: inset 0 1px 0 color-mix(in oklch, var(--fg) 22%, transparent), 0 0 0 1px color-mix(in oklch, var(--fg) 10%, transparent), 0 2px 6px rgba(0,0,0,.35), 0 40px 90px rgba(0,0,0,.55), 0 90px 180px rgba(0,0,0,.45); }
  #bar { height: __TB__px; display: flex; align-items: center; gap: 8px; padding: 0 14px;
         border-bottom: 1px solid color-mix(in oklch, var(--fg) 12%, transparent);
         background: linear-gradient(to bottom, color-mix(in oklch, var(--bg) 80%, var(--fg)), color-mix(in oklch, var(--bg) 88%, var(--fg))); }
  #glow { position: absolute; left: 50%; top: 50%; width: 104%; height: 96%; transform: translate(-50%, -48%);
          background: radial-gradient(closest-side, color-mix(in oklch, var(--accent) 46%, transparent), transparent 92%);
          filter: blur(40px); pointer-events: none; }
  #bar i { width: 11px; height: 11px; border-radius: 50%; background: color-mix(in oklch, var(--fg) 22%, transparent); }
  #view { position: relative; width: __WW__px; height: __WH__px; }
  .scr { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; }
  .spot { position: absolute; border-radius: calc(var(--r) * 0.8); opacity: 0;
          box-shadow: 0 0 0 4000px color-mix(in oklch, var(--bg) 60%, transparent); }
  #cursor { position: absolute; width: 26px; height: 26px; opacity: 0; transform-origin: 0 0; z-index: 3; }
  #ring { position: absolute; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%; opacity: 0;
          border: 2px solid var(--accent); z-index: 2; }
  #scrim { position: absolute; left: 0; right: 0; opacity: 0; pointer-events: none; }
  .h #scrim { top: 0; bottom: 0; left: 0; width: 52%; background: linear-gradient(to right, var(--bg) 0%, var(--bg) 70%, transparent); }
  #topfade { position: absolute; left: 0; right: 0; top: 0; height: 9%; pointer-events: none; opacity: 0;
             background: linear-gradient(to bottom, var(--bg), transparent); }
  .v #scrim { top: 0; height: 50%; background: linear-gradient(to bottom, var(--bg) 0%, var(--bg) 70%,
              color-mix(in oklch, var(--bg) 60%, transparent) 86%, transparent); }
  .v #topfade { top: auto; bottom: 0; height: 22%; background: linear-gradient(to top, var(--bg) 25%, transparent); }
  .title { position: absolute; font-weight: 650; letter-spacing: -0.035em; line-height: 1.02; opacity: 0; }
  .title .w { display: inline-block; opacity: 0; }
  .h .title { left: 96px; top: 50%; transform: translateY(-50%); font-size: 84px; max-width: 600px; }
  .v .title { left: 72px; right: 72px; top: 19%; font-size: 92px; }
  #end { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
         background: var(--bg); opacity: 0; }
  #end h1 { font-weight: 600; letter-spacing: -0.045em; line-height: 1; opacity: 0; }
  .h #end h1 { font-size: 168px; } .v #end h1 { font-size: 150px; }
  #end .sub { margin-top: 44px; font-family: "__MONO__", ui-monospace, monospace; letter-spacing: -0.01em;
              padding: 16px 26px; border-radius: 12px; border: 1px solid color-mix(in oklch, var(--fg) 16%, transparent);
              color: color-mix(in oklch, var(--fg) 86%, transparent); opacity: 0; }
  .h #end .sub { font-size: 38px; } .v #end .sub { font-size: 34px; }
</style>
</head>
<body>
<div id="root" class="__CLASS__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="bgfx"></div>
  <div id="glow"></div>
  <div id="stage">
    <div id="win" data-layout-allow-overflow>
      <div id="bar" data-layout-allow-overflow><i></i><i></i><i></i></div>
      <div id="view" data-layout-allow-overflow>
__SCREENS__
__SPOTS__
        <div id="ring"></div>
        <svg id="cursor" viewBox="0 0 26 26"><path d="M3 2 L3 21 L8 16 L11.5 24 L15 22.5 L11.6 14.8 L18.5 14.8 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>
      </div>
    </div>
  </div>
  <div id="topfade"></div>
  <div id="scrim"></div>
__TITLES__
  <div id="end"><h1>__END_TITLE__</h1><div class="sub">__END_SUB__</div></div>
  <div id="grain"></div>
</div>
<script>
  const A = __ANIM__;
  const VERTICAL = __VERTICAL__;
  const tl = gsap.timeline({ paused: true });
  const win = "#win";
  gsap.set(win, { transformPerspective: 1800 });
  for (const a of A) {
    if (a.k === "est") {
      tl.set("#scr" + a.scr, { opacity: 1 }, a.t);
      tl.fromTo(win, { x: a.from.x, y: a.from.y, scale: a.from.scale, rotationX: a.from.rx, rotationY: a.from.ry },
                { x: a.to.x, y: a.to.y, scale: a.to.scale, rotationX: 0, rotationY: 0, duration: (a.e - a.t) * 0.92,
                  ease: "power3.inOut" }, a.t);
    } else if (a.k === "feat") {
      const d = a.e - a.t;
      tl.set(".scr", { opacity: 0 }, a.t);
      tl.set("#glow", { opacity: 0 }, a.t);
      tl.set("#scr" + a.scr, { opacity: 1 }, a.t);
      tl.set(".spot", { opacity: 0 }, a.t);
      tl.set(".title", { opacity: 0 }, a.t);
      tl.set("#cursor, #ring", { opacity: 0 }, a.t);
      // the camera is already moving when the cut lands, and settles: one move, eased out
      tl.fromTo(win, { x: a.pose.x * 0.9, y: a.pose.y * 0.9 + 18, scale: a.pose.scale * 0.9, rotationX: 0, rotationY: 0 },
                { x: a.pose.x, y: a.pose.y, scale: a.pose.scale, duration: d * 0.95, ease: "expo.out", immediateRender: false }, a.t);
      tl.fromTo("#view", { filter: "blur(6px)" }, { filter: "blur(0px)", duration: 0.18, ease: "power2.out", immediateRender: false }, a.t);
      if (a.spot) tl.to(a.spot, { opacity: 1, duration: 0.3, ease: "power2.out" }, a.t + 0.28);
      tl.to("#scrim", { opacity: 1, duration: VERTICAL ? 0.12 : 0.25, ease: "power1.out" }, a.t + (VERTICAL ? 0 : 0.22));
      tl.set("#topfade", { opacity: 1 }, a.t);
      const tIn = VERTICAL ? 0.12 : 0.36;
      tl.set(a.title, { opacity: 1 }, a.t + tIn);
      tl.fromTo(a.title + " .w", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.42, stagger: 0.06, ease: "power3.out", immediateRender: false }, a.t + tIn);
      if (a.cursor) {
        const cx = a.cursor[0] * 100 + "%", cy = a.cursor[1] * 100 + "%";
        const cs = 34 / (26 * a.pose.scale);   // about 34 px on screen whatever the camera does
        tl.set("#cursor", { left: cx, top: cy, x: 40 / a.pose.scale, y: 26 / a.pose.scale, scale: cs, opacity: 1 }, a.t + 0.9);
        tl.to("#cursor", { x: 0, y: 0, duration: 0.4, ease: "power2.inOut" }, a.t + 0.9);
        tl.to("#cursor", { scale: cs * 0.86, duration: 0.08, yoyo: true, repeat: 1, ease: "power1.inOut" }, a.t + 1.38);
        tl.set("#ring", { left: a.ring[0] * 100 + "%", top: a.ring[1] * 100 + "%" }, a.t + 1.38);
        tl.fromTo("#ring", { opacity: 0.9, scale: 0.4 }, { opacity: 0, scale: 1.4, duration: 0.45, ease: "power2.out", immediateRender: false }, a.t + 1.38);
      }
    } else if (a.k === "end") {
      tl.set("#scrim, #topfade, .title, .spot, #cursor, #ring", { opacity: 0 }, a.t);
      tl.set("#end", { opacity: 1 }, a.t);
      tl.fromTo("#end h1", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, a.t + 0.12);
      tl.fromTo("#end .sub", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", immediateRender: false }, a.t + 0.45);
    }
  }
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""
