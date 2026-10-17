"""HyperFrames composition for footage: captions word by word, a lower third, keyword callouts, a progress bar.

    build(out_dir, video="cut.mp4", words=..., size=(1080, 1920), name="Scott Kelly", role="NASA astronaut",
          callouts=[{"t": 12.0, "text": "340 days"}], credit="Footage: NASA (public domain)")

The footage plays muted (the edited audio is muxed afterwards by `finish()`, loudness-normalised). Captions are
the transcript's own words, never rewritten; the word being said is lit in the accent colour.
"""
import html
import json
import shutil
from pathlib import Path

from . import edit, hf, media

ACCENT = "#ffd84d"


def groups(words, max_words=3, max_chars=18, max_gap=0.45):
    """Split words into caption groups: break at sentence ends, pauses and size limits."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap or
                    len(" ".join(x["text"] for x in cur + [w])) > max_chars):
            out.append(cur)
            cur = []
        cur.append(w)
        if w["text"].rstrip().endswith((".", "?", "!")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def esc(s):
    return html.escape(s, quote=True)


def build(out_dir, video, words, size=(1080, 1920), name=None, role=None, callouts=(), credit=None, title=None):
    W, H = size
    vertical = H > W
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "footage.mp4"
    if Path(video).resolve() != dst.resolve():
        shutil.copyfile(video, dst)
    dur = media.duration(dst)
    gs = groups(words, *((3, 18) if vertical else (6, 44)))
    caps, anim = [], []
    for gi, g in enumerate(gs):
        gid = "g%d" % gi
        spans = "".join('<span class="w" id="%s_%d">%s</span> ' % (gid, k, esc(w["text"].strip())) for k, w in
                        enumerate(g))
        caps.append('<div class="cap" id="%s"><span class="in">%s</span></div>' % (gid, spans))
        nxt = gs[gi + 1][0]["start"] - 0.06 if gi + 1 < len(gs) else dur   # when the next group appears
        anim.append(["cap", gid, max(0, g[0]["start"] - 0.06), min(nxt, g[-1]["end"] + 0.5)])
        for k, w in enumerate(g):
            anim.append(["word", "%s_%d" % (gid, k), w["start"]])
    calls = []
    for ci, c in enumerate(callouts):
        calls.append('<div class="call" id="c%d"><span class="tick"></span>%s</div>' % (ci, esc(c["text"])))
        anim.append(["call", "c%d" % ci, c["t"], c["t"] + c.get("dur", 2.8)])
    lower = ""
    if name:
        lower = '<div id="lower"><div class="bar"></div><div><b>%s</b>%s</div></div>' % (
            esc(name), ("<span>%s</span>" % esc(role)) if role else "")
    page = (TEMPLATE.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", "%.3f" % dur)
            .replace("__CLASS__", "v" if vertical else "h").replace("__CAPS__", "\n".join(caps))
            .replace("__CALLS__", "\n".join(calls)).replace("__LOWER__", lower)
            .replace("__CREDIT__", '<div id="credit">%s</div>' % esc(credit) if credit else "")
            .replace("__TITLE__", '<div id="title"><span>%s</span></div>' % esc(title) if title else "")
            .replace("__ANIM__", json.dumps(anim)).replace("__ACCENT__", ACCENT))
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir / "index.html"


def finish(comp_dir, audio_src, out, quality="high", reuse=False):
    """Render the composition (reuse=True keeps an existing render), then mux the edited audio,
    loudness-normalised to -14 LUFS (social platforms)."""
    comp_dir = Path(comp_dir)
    silent = comp_dir / "render.mp4"
    if not (reuse and silent.exists()):
        hf.render(comp_dir, silent, quality=quality)
    return media.mux_loud(silent, audio_src, out)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root { --accent: __ACCENT__; --ink: #0b0b0d; --text: #ffffff; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: #000; }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: __W__px; height: __H__px; overflow: hidden; }
  #bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .cap { position: absolute; left: 0; right: 0; display: flex; justify-content: center; opacity: 0; }
  .cap .w { opacity: 0.55; }
  .v .cap { top: 66%; padding: 0 70px; }
  .v .cap .in { font-weight: 800; font-size: 82px; line-height: 1.08; letter-spacing: -0.02em; text-align: center;
                text-shadow: 0 0 2px #000, 0 3px 0 #000, 0 -2px 0 #000, 3px 0 0 #000, -3px 0 0 #000, 0 8px 28px rgba(0,0,0,.65); }
  .h .cap { bottom: 64px; }
  .h .cap .in { font-weight: 600; font-size: 44px; line-height: 1.3; padding: 12px 26px; border-radius: 14px;
                background: rgba(11,11,13,0.78); max-width: 1500px; text-align: center; }
  #lower { position: absolute; display: flex; gap: 18px; align-items: stretch; opacity: 0; }
  #lower .bar { width: 6px; border-radius: 3px; background: var(--accent); }
  #lower b { display: block; font-weight: 700; letter-spacing: -0.01em; }
  #lower span { display: block; color: #e2e2e8; font-weight: 500; margin-top: 4px; }
  .v #lower { left: 64px; top: 150px; } .v #lower b { font-size: 48px; } .v #lower span { font-size: 32px; }
  .h #lower { left: 72px; bottom: 170px; } .h #lower b { font-size: 40px; } .h #lower span { font-size: 26px; }
  #lower > div:last-child { background: rgba(11,11,13,0.72); padding: 14px 22px; border-radius: 12px; }
  .call { position: absolute; display: flex; align-items: center; gap: 16px; opacity: 0; font-weight: 700;
          letter-spacing: -0.01em; background: #f7f7f9; color: var(--ink); border-radius: 18px;
          box-shadow: 0 18px 50px rgba(0,0,0,.35); }
  .call .tick { width: 14px; height: 14px; border-radius: 50%; background: #e0a800; flex: none; }
  .v .call { left: 50%; top: 300px; transform: translateX(-50%); font-size: 54px; padding: 22px 34px; white-space: nowrap; }
  .h .call { right: 72px; top: 64px; font-size: 40px; padding: 18px 28px; }
  #prog { position: absolute; left: 0; top: 0; height: 8px; width: 0; background: var(--accent); }
  .h #prog { display: none; }
  #credit { position: absolute; right: 28px; bottom: 20px; font-size: 20px; color: rgba(255,255,255,.82);
            text-shadow: 0 1px 4px rgba(0,0,0,.8); }
  .v #credit { right: 0; left: 0; text-align: center; bottom: 46px; font-size: 26px; }
  #title { position: absolute; left: 0; right: 0; display: flex; justify-content: center; opacity: 0; }
  #title span { background: var(--accent); color: var(--ink); font-weight: 800; letter-spacing: -0.02em; border-radius: 16px; }
  .v #title { top: 200px; padding: 0 60px; } .v #title span { font-size: 64px; padding: 18px 30px; text-align: center; }
  .h #title { top: 70px; } .h #title span { font-size: 52px; padding: 14px 28px; }
</style>
</head>
<body>
<div id="root" class="__CLASS__" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <video id="bg" src="footage.mp4" data-start="0" data-duration="__DUR__" data-track-index="0" data-media-start="0" muted playsinline></video>
  <div id="prog"></div>
  __TITLE__
  __LOWER__
__CALLS__
__CAPS__
  __CREDIT__
</div>
<script>
  const A = __ANIM__;
  const D = __DUR__;
  const tl = gsap.timeline({ paused: true });
  tl.to("#prog", { width: "100%", duration: D, ease: "none" }, 0);
  const hasTitle = !!document.querySelector("#title");
  if (hasTitle) {
    tl.fromTo("#title", { opacity: 0, y: -20 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.1);
    tl.to("#title", { opacity: 0, duration: 0.35, ease: "power1.in" }, Math.min(3.0, D - 0.5));
  }
  if (document.querySelector("#lower")) {
    const t0 = hasTitle ? 3.4 : 0.8;
    tl.fromTo("#lower", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.5, ease: "power3.out" }, t0);
    tl.to("#lower", { opacity: 0, x: -20, duration: 0.4, ease: "power1.in" }, Math.min(t0 + 4.6, D - 0.6));
  }
  for (const a of A) {
    if (a[0] === "cap") {
      tl.set("#" + a[1], { opacity: 1 }, a[2]);
      tl.fromTo("#" + a[1] + " .in", { scale: 0.92 }, { scale: 1, duration: 0.18, ease: "back.out(2)" }, a[2]);
      tl.set("#" + a[1], { opacity: 0 }, a[3]);
    } else if (a[0] === "word") {
      tl.to("#" + a[1], { opacity: 1, color: "var(--accent)", duration: 0.06, ease: "none" }, a[2]);
      tl.to("#" + a[1], { color: "#ffffff", duration: 0.2, ease: "none" }, a[2] + 0.32);
    } else if (a[0] === "call") {
      tl.fromTo("#" + a[1], { opacity: 0, scale: 0.85, y: 20 }, { opacity: 1, scale: 1, y: 0, duration: 0.4, ease: "back.out(1.8)" }, a[2]);
      tl.to("#" + a[1], { opacity: 0, y: -12, duration: 0.3, ease: "power1.in" }, a[3]);
    }
  }
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""
