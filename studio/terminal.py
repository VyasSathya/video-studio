"""Terminal replay: a HyperFrames composition that types real commands and prints their real output.

    python -m studio.terminal session.json out_dir [--title "agent-brain"] [--prompt "PS> "]

session.json: [{"cmd": "...", "out": "...", "label": "optional step name"}, ...] -- capture it by running the
commands for real (see projects/agent-brain-terminal/capture.ps1); this only replays text, it never makes any up.
Highlight rules (optional key "highlight" per step): [["regex", "red"|"amber"|"green"], ...].
Writes out_dir/index.html; render it with studio.hf.render(out_dir, "x.mp4").
"""
import argparse
import html
import json
import re
from pathlib import Path

CPS = 38.0          # typing speed, characters per second
PRE = 0.5           # before typing starts
AFTER_TYPE = 0.35   # Enter -> output
READ_S = 2.2        # output on screen before the next command (plus a bit per line)


def esc(s):
    return html.escape(s, quote=False)


def colorize(line, rules):
    out = esc(line)
    for pat, color in rules:
        out = re.sub("(%s)" % pat, r'<span class="%s">\1</span>' % color, out)
    return out


def build(steps, title, prompt, w=1280, h=760):
    blocks, anim, t = [], [], 0.8
    for i, st in enumerate(steps):
        cmd, out = st["cmd"], st.get("out", "")
        n = len(cmd)
        rules = st.get("highlight", [])
        lines = out.split("\n") if out else []
        body = "".join('<div class="ol">%s</div>' % (colorize(l, rules) or "&nbsp;") for l in lines)
        blocks.append('<div class="blk" id="b%d"><div class="cl"><span class="pr">%s</span>'
                      '<span class="cmd" id="c%d" style="--n:%d">%s</span><span class="cur" id="k%d"></span></div>'
                      '<div class="out" id="o%d">%s</div></div>' % (i, esc(prompt), i, n, esc(cmd), i, i, body))
        type_s = n / CPS
        anim.append({"i": i, "show": round(t, 3), "type": round(t + PRE, 3), "dur": round(type_s, 3),
                     "out": round(t + PRE + type_s + AFTER_TYPE, 3), "label": st.get("label", "")})
        t += PRE + type_s + AFTER_TYPE + READ_S + 0.12 * len(lines)
    total = round(t + 0.8, 3)
    labels = "".join('<span class="lab" id="l%d">%s</span>' % (a["i"], esc(a["label"])) for a in anim if a["label"])
    return PAGE.replace("__W__", str(w)).replace("__H__", str(h)).replace("__DUR__", str(total)) \
        .replace("__TITLE__", esc(title)).replace("__BLOCKS__", "\n".join(blocks)).replace("__LABELS__", labels) \
        .replace("__ANIM__", json.dumps(anim)), total


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=__W__, height=__H__" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: __W__px; height: __H__px; overflow: hidden; background: #0b0b0d; }
  #root { position: relative; width: __W__px; height: __H__px; font-family: Inter, sans-serif; color: #e7e7ea;
          background: radial-gradient(900px 500px at 50% 0%, #16161b 0%, #0b0b0d 70%); }
  #win { position: absolute; left: 48px; right: 48px; top: 44px; bottom: 44px; background: #111114; border: 1px solid #26262c;
         border-radius: 16px; overflow: hidden; }
  #bar { height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
         border-bottom: 1px solid #222227; font-size: 17px; color: #9a9aa4; }
  #bar b { color: #e7e7ea; font-weight: 600; }
  #labs { position: relative; height: 24px; width: 640px; }
  .lab { position: absolute; right: 0; top: 0; opacity: 0; white-space: nowrap; }
  #scr { position: absolute; left: 0; right: 0; top: 52px; bottom: 0; padding: 22px 28px; display: flex; flex-direction: column;
         justify-content: flex-end; gap: 18px; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 17px; line-height: 1.5;
         -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 60px); }
  .blk { display: none; }
  .cl { white-space: nowrap; }
  .pr { color: #7d9bff; }
  .cmd { display: inline-block; vertical-align: bottom; overflow: hidden; white-space: pre; width: 0; color: #f2f2f4; }
  .cur { display: inline-block; width: 10px; height: 21px; vertical-align: -4px; background: #e7e7ea; margin-left: 2px; opacity: 0; }
  .out { opacity: 0; color: #b4b4bd; white-space: pre-wrap; word-break: break-word; margin-top: 4px; }
  .red { color: #ff7a7a; } .amber { color: #fbbf5a; } .green { color: #7fdca0; }
</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="__W__" data-height="__H__">
  <div id="win">
    <div id="bar"><span><b>__TITLE__</b></span><span id="labs">__LABELS__</span></div>
    <div id="scr">
__BLOCKS__
    </div>
  </div>
</div>
<script>
  const A = __ANIM__;
  const tl = gsap.timeline({ paused: true });
  let prevLab = null;
  for (const a of A) {
    const b = "#b" + a.i, c = "#c" + a.i, k = "#k" + a.i, o = "#o" + a.i, l = "#l" + a.i;
    tl.set(b, { display: "block" }, a.show);
    tl.set(k, { opacity: 1 }, a.show);
    const n = parseInt(getComputedStyle(document.querySelector(c)).getPropertyValue("--n"));
    tl.to(c, { width: n + "ch", duration: a.dur, ease: "steps(" + n + ")" }, a.type);
    tl.set(k, { opacity: 0 }, a.out - 0.05);
    tl.to(o, { opacity: 1, duration: 0.15 }, a.out);
    if (document.querySelector(l)) {
      if (prevLab) tl.to(prevLab, { opacity: 0, duration: 0.2 }, a.show);
      tl.to(l, { opacity: 1, duration: 0.25 }, a.show);
      prevLab = l;
    }
  }
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("out_dir")
    ap.add_argument("--title", default="Terminal")
    ap.add_argument("--prompt", default="PS> ")
    a = ap.parse_args()
    steps = json.loads(Path(a.session).read_text(encoding="utf-8-sig"))
    page, total = build(steps, a.title, a.prompt)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("terminal: %d steps, %.1f s -> %s" % (len(steps), total, out / "index.html"))


if __name__ == "__main__":
    main()
