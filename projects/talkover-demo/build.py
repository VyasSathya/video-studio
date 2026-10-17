"""Write the HyperFrames composition (build/hf/index.html) for the Talkover demo from build/timeline.json.

The composition draws everything except the panel: title card, the Claude Code chat (messages appear when Talkover
would have typed them; Claude's words light up as they are read aloud, so a cut-in leaves the unheard rest dim),
tool rows and the real diff, a subtitle for what "you" say, and the end card. The real panel is laid over it
afterwards by render.py (it is rendered by Talkover's own code, see panel_render.py).
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
W, H = 1920, 1080
PANEL_SCALE = 0.8                  # panel frames are rendered at 2x; shown at 1.6x the panel's logical size
PANEL_Y = 26


def word_times(text, start, dur, whisper):
    """Start time of every word of `text` as spoken: Whisper's word timings when the counts match, else spread by
    character position over the clip."""
    words = text.split()
    if len(whisper) == len(words):
        return [round(start + w["s"], 3) for w in whisper]
    total = sum(len(w) + 1 for w in words)
    out, acc = [], 0
    for w in words:
        out.append(round(start + dur * acc / total, 3))
        acc += len(w) + 1
    return out


def esc(s):
    return html.escape(s, quote=True)


def main():
    tl = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
    pm = json.loads((BUILD / "panel.json").read_text(encoding="utf-8"))
    ev = tl["events"]
    dur = tl["duration"]
    scene0, scene1 = tl["scene"]
    msgs, anim, subs = [], [], []
    mid = 0

    def add(kind, t, inner, cls=""):
        nonlocal mid
        mid += 1
        i = "m%d" % mid
        msgs.append('<div class="msg %s %s" id="%s">%s</div>' % (kind, cls, i, inner))
        anim.append(["show", i, t])
        return i

    chunks = [e for e in ev if e["kind"] == "chunk"]
    for e in ev:
        if e["kind"] == "you":
            words = e["heard"].split()
            times = word_times(e["heard"], e["t"], e["dur"], e["words"])
            sid = "s%d" % e["turn"]
            spans = "".join('<span class="w" id="%s_%d">%s </span>' % (sid, k, esc(w)) for k, w in enumerate(words))
            subs.append('<div class="sub" id="%s"><span class="who">You <i>synthetic voice</i></span>'
                        '<span class="said">%s</span></div>' % (sid, spans))
            anim.append(["sub", sid, e["t"] - 0.15, e["t"] + e["dur"] + 0.5])
            for k, t in enumerate(times):
                anim.append(["word", "%s_%d" % (sid, k), t])
        elif e["kind"] == "typed":
            m = re.match(r"^(.*?)\s*(\[voice:.*\])?$", e["text"])
            words, note = m.group(1), m.group(2)
            inner = '<div class="said">%s</div>' % esc(words)
            if note:
                inner += '<div class="note">%s</div>' % esc(note)
            add("you", e["t"], inner)
        elif e["kind"] == "tool":
            verb, _, name = e["text"].partition(" ")
            inner = '<div class="tool"><span class="dot"></span><b>%s</b> %s</div>' % (esc(verb), esc(name))
            if e.get("diff"):
                lines = "".join('<div class="dl %s">%s</div>' % (
                    "add" if l.startswith("+") else ("gap" if l.strip() == "..." else ""), esc(l))
                    for l in e["diff"])
                inner += '<div class="diff">%s</div>' % lines
            add("toolrow", e["t"], inner)
        elif e["kind"] == "reply":
            mine = [c for c in chunks if c["turn"] == e["turn"]]
            rid = "r%d" % e["turn"]
            spans, k = [], 0
            for c in mine:
                times = word_times(c["text"], c["t"], c["full"], c["words"])
                for w, t in zip(c["text"].split(), times):
                    spans.append('<span class="w" id="%s_%d">%s </span>' % (rid, k, esc(w)))
                    if t <= c["t"] + c["dur"]:
                        anim.append(["word", "%s_%d" % (rid, k), t])
                    k += 1
            # chunks never read (after a cut) stay dim
            for c in split_rest(e["text"], sum(len(c["text"].split()) for c in mine)):
                spans.append('<span class="w" id="%s_%d">%s </span>' % (rid, k, esc(c)))
                k += 1
            add("claude", e["t"], '<div class="said">%s</div>' % "".join(spans))
            anim.append(["think", e["think_from"], e["t"]])
        elif e["kind"] == "cut":
            anim.append(["cut", e["t"]])
        elif e["kind"] == "mute":
            anim.append(["mute", e["t"]])

    pw = int(round(pm["w"] * PANEL_SCALE))
    ph = int(round(pm["h"] * PANEL_SCALE))
    page = TEMPLATE.replace("__DUR__", "%.3f" % dur) \
        .replace("__MSGS__", "\n".join(msgs)) \
        .replace("__SUBS__", "\n".join(subs)) \
        .replace("__ANIM__", json.dumps(anim)) \
        .replace("__SCENE0__", "%.3f" % scene0).replace("__SCENE1__", "%.3f" % scene1) \
        .replace("__PANEL_TOP__", str(PANEL_Y + ph - int(pm["margin"] * PANEL_SCALE) + 22)) \
        .replace("__PANEL_SLOT__", "left:%dpx;top:%dpx;width:%dpx;height:%dpx" % ((W - pw) // 2, PANEL_Y, pw, ph))
    out = BUILD / "hf"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "overlay.json").write_text(json.dumps({"x": (W - pw) // 2, "y": PANEL_Y, "w": pw, "h": ph,
                                                  "scene": [scene0, scene1]}), encoding="utf-8")
    print("composition: %s (%d messages, %.1f s)" % (out / "index.html", len(msgs), dur))


def split_rest(text, n_done):
    return text.split()[n_done:]


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root {
    --bg: #0b0b0d; --pane: #121215; --line: #24242a; --text: #ececf1; --muted: #9a9aa4; --faint: #8a8a94;
    --human: #4ddbe6; --robot: #fa8f5c; --add: #7fdca0;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 1920px; height: 1080px; overflow: hidden; background: var(--bg); }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: 1920px; height: 1080px; overflow: hidden;
          background: radial-gradient(1200px 700px at 50% 0%, #16161b 0%, var(--bg) 70%); }
  .card { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .card h1 { font-size: 128px; font-weight: 600; letter-spacing: -0.04em; }
  .card p { margin-top: 22px; font-size: 42px; color: #a6a6b0; letter-spacing: -0.01em; }
  .card .url { margin-top: 30px; font-size: 40px; color: var(--text); font-weight: 500; }
  .card .fine { margin-top: 64px; font-size: 25px; line-height: 1.6; color: var(--muted); text-align: center; }
  #scene { position: absolute; inset: 0; opacity: 0; }
  #pane { position: absolute; left: 400px; right: 400px; top: __PANEL_TOP__px; bottom: 132px; background: var(--pane);
          border: 1px solid var(--line); border-radius: 20px; overflow: hidden; }
  #pane .head { position: absolute; left: 0; right: 0; top: 0; height: 64px; display: flex; align-items: center;
                padding: 0 30px; gap: 12px; font-size: 22px; color: var(--muted); border-bottom: 1px solid var(--line);
                background: var(--pane); z-index: 2; }
  #pane .head b { color: var(--text); font-weight: 600; }
  #pane .head .sep { width: 1px; height: 18px; background: var(--line); }
  #stream { position: absolute; left: 0; right: 0; top: 64px; bottom: 0; padding: 30px 40px 74px; display: flex;
            flex-direction: column; justify-content: flex-end; gap: 22px;
            -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 90px); }
  .msg { display: none; }
  .msg.you { align-self: flex-end; max-width: 78%; background: #1b1b20; border: 1px solid var(--line);
             border-radius: 16px; padding: 18px 24px; font-size: 30px; line-height: 1.4; }
  .msg.you .note { margin-top: 12px; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 20px; line-height: 1.45; color: var(--muted); }
  .msg.toolrow { font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 23px; line-height: 1.4; color: var(--muted); }
  .tool { display: flex; align-items: center; gap: 12px; }
  .tool b { color: var(--text); font-weight: 600; }
  .tool .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--robot); }
  .diff { margin-top: 12px; border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; font-size: 20px;
          line-height: 1.55; color: var(--faint); background: #0e0e11; white-space: pre; }
  .diff .add { color: var(--add); }
  .diff .gap { color: #8a8a94; }
  .msg.claude { font-size: 31px; line-height: 1.45; letter-spacing: -0.005em; }
  .msg.claude .w { opacity: 0.32; }
  #think { position: absolute; left: 440px; bottom: 156px; display: flex; align-items: center; gap: 12px;
           font-size: 21px; color: var(--muted); opacity: 0; }
  #think .pulse { width: 10px; height: 10px; border-radius: 50%; background: #9d8cff; }
  #think i { font-style: normal; color: var(--faint); }
  .sub { position: absolute; left: 0; right: 0; bottom: 34px; display: flex; flex-direction: column; align-items: center;
         gap: 8px; opacity: 0; }
  .sub .who { font-size: 20px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--human); font-weight: 600; }
  .sub .who i { font-style: normal; color: var(--faint); font-weight: 500; letter-spacing: 0.04em; margin-left: 10px; }
  .sub .said { font-size: 38px; font-weight: 500; }
  .sub .w { opacity: 0; }
  #tag { position: absolute; right: 40px; top: 40px; font-size: 19px; color: var(--faint); text-align: right; line-height: 1.5; }
  #slot { position: absolute; __PANEL_SLOT__; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1920" data-height="1080">
  <div class="card" id="title">
    <h1>Talkover</h1>
    <p>Hands-free, two-way voice for Claude Code on Windows</p>
  </div>
  <div id="scene">
    <div id="tag">Synthetic voices<br>Waits shortened</div>
    <div id="slot"></div>
    <div id="pane">
      <div class="head"><b>Claude Code</b><span class="sep"></span><span>talkover</span></div>
      <div id="stream">
__MSGS__
      </div>
    </div>
    <div id="think"><span class="pulse"></span>Claude is working <i>sped up</i></div>
__SUBS__
  </div>
  <div class="card" id="end" style="opacity:0">
    <h1>Talkover</h1>
    <div class="url">github.com/VyasSathya/talkover</div>
    <div class="fine">Both voices are synthetic (Kokoro). Claude's replies and the edit are real output<br>
      of a Claude Code agent working in a copy of this repo. Waits for Claude are shortened.</div>
  </div>
</div>
<script>
  const A = __ANIM__;
  const S0 = __SCENE0__, S1 = __SCENE1__;
  const tl = gsap.timeline({ paused: true });
  tl.set("#title", { opacity: 1 }, 0);
  tl.fromTo("#title h1", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.7, ease: "power2.out" }, 0.15);
  tl.fromTo("#title p", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.7, ease: "power2.out" }, 0.45);
  tl.to("#title", { opacity: 0, duration: 0.45, ease: "power1.in" }, S0 - 0.45);
  tl.to("#scene", { opacity: 1, duration: 0.5, ease: "power1.out" }, S0 - 0.1);
  tl.to("#scene", { opacity: 0, duration: 0.5, ease: "power1.in" }, S1);
  tl.to("#end", { opacity: 1, duration: 0.6, ease: "power1.out" }, S1 + 0.35);
  for (const a of A) {
    const k = a[0];
    if (k === "show") {
      tl.set("#" + a[1], { display: "block" }, a[2]);
      tl.fromTo("#" + a[1], { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, a[2]);
    } else if (k === "word") {
      tl.to("#" + a[1], { opacity: 1, duration: 0.12, ease: "none" }, a[2]);
    } else if (k === "sub") {
      tl.to("#" + a[1], { opacity: 1, duration: 0.2 }, a[2]);
      tl.to("#" + a[1], { opacity: 0, duration: 0.3 }, a[3]);
    } else if (k === "think") {
      tl.to("#think", { opacity: 1, duration: 0.25 }, a[1] + 0.15);
      tl.to("#think", { opacity: 0, duration: 0.25 }, a[2] - 0.1);
      tl.fromTo("#think .pulse", { scale: 0.7 }, { scale: 1.25, duration: 0.45, repeat: Math.max(1, Math.floor((a[2] - a[1]) / 0.45) - 1),
                yoyo: true, ease: "sine.inOut" }, a[1] + 0.15);
    }
  }
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
