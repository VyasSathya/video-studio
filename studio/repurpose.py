"""One long video in, short vertical clips and post drafts out: python -m studio repurpose talk.mp4 --clips 3

1. transcribe once (cached next to the run)            4. drafts: LinkedIn post, X thread, carousel slide
2. a text model picks stand-alone moments; each            copy, all from the transcript; slides rendered as
   boundary must be words actually said (studio.picks)     1080x1350 PNGs (studio/still.mjs)
3. each clip: dead air out, 9:16 reframe, captions,     5. manifest.json + review page; nothing is posted
   title, -14 LUFS, QC                                     (posting is a separate pipeline with approval)

An agent driving this can write picks.json itself (same shape as picks.clips()) instead of using a model.
The windowing-and-snap idea follows OpenShorts' clip_selection.py (MIT, OpenShorts); our own implementation.
"""
import html
import json
import subprocess
import time
from pathlib import Path

from . import edit, engines, media, overlay, picks, qc, reframe

ROOT = Path(__file__).resolve().parents[1]
VERBATIM = "Umm, uh, so, like, I I think, you know, we we went there."


def run(src, out_dir, n=3, credit=None, quality="high", min_s=20, max_s=55):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def step(msg):
        log.append({"t": time.strftime("%H:%M:%S"), "step": msg})
        print("[repurpose]", msg, flush=True)

    wav = out / "source.wav"
    words_f = out / "words.json"
    if not words_f.exists():
        step("transcribe")
        media.run(["-i", src, "-vn", "-ac", 1, "-ar", 16000, wav])
        words_f.write_text(json.dumps(edit.words_from(engines.stt(wav, prompt=VERBATIM))), encoding="utf-8")
    words = json.loads(words_f.read_text(encoding="utf-8"))
    picks_f = out / "picks.json"
    if not picks_f.exists():
        step("pick clips")
        picks_f.write_text(json.dumps(picks.clips(words, n=n, min_s=min_s, max_s=max_s), indent=1), encoding="utf-8")
    chosen = json.loads(picks_f.read_text(encoding="utf-8"))
    outputs = []
    for i, c in enumerate(chosen["clips"]):
        d = out / ("clip%d" % (i + 1))
        d.mkdir(exist_ok=True)
        s, e = max(0.0, c["start"] - 0.2), c["end"] + 0.35
        step("clip %d: %.1f-%.1f %s" % (i + 1, s, e, c["title"]))
        raw = d / "raw.mp4"
        media.run(["-ss", "%.3f" % s, "-to", "%.3f" % e, "-i", src, "-c:v", "libx264", "-crf", 16, "-preset",
                   "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", raw])
        cw = [{"text": w["text"], "start": round(w["start"] - s, 3), "end": round(w["end"] - s, 3)}
              for w in words if w["start"] >= s and w["end"] <= e]
        rwav = d / "raw.wav"
        media.run(["-i", raw, "-vn", "-ac", 1, "-ar", 16000, rwav])
        cut = edit.plan(cw, media.duration(raw), silence=edit.silences(rwav))
        (d / "cut.json").write_text(json.dumps(cut, indent=1), encoding="utf-8")
        cut_mp4 = edit.apply(raw, cut["keep"], d / "cut.mp4")
        cut_wav = d / "cut.wav"
        media.run(["-i", cut_mp4, "-vn", "-ac", 2, "-ar", 48000, cut_wav])
        nw = edit.retime(cw, cut["keep"])
        plan = reframe.plan(cut_mp4)
        v916 = reframe.render(cut_mp4, plan, d / "cut-9x16.mp4")
        try:
            calls = picks.callouts(nw, max_n=2)["callouts"]
        except Exception:
            calls = []
        overlay.build(d / "comp", v916, nw, size=(1080, 1920), callouts=calls, credit=credit, title=c["title"])
        final = overlay.finish(d / "comp", cut_wav, out / ("clip%d-9x16.mp4" % (i + 1)), quality=quality)
        outputs.append({"label": "Clip %d: %s" % (i + 1, c["title"]), "file": final.name, "kind": "video",
                        "aspect": "9:16", "why": c.get("why", ""), "source_range": [round(s, 2), round(e, 2)],
                        "qc": qc.check(final, nw)})
    step("post drafts")
    text = picks.transcript_text(words)
    title = chosen["clips"][0]["title"] if chosen["clips"] else Path(src).stem
    drafts_f = out / "drafts.json"
    if not drafts_f.exists():
        drafts_f.write_text(json.dumps(picks.posts(text, title), indent=1), encoding="utf-8")
    drafts = json.loads(drafts_f.read_text(encoding="utf-8"))
    drafts["slides"] = slides(drafts.get("carousel", []), out / "slides", credit)
    drafts["slides"] = [str(Path(p).relative_to(out)) for p in drafts["slides"]]
    manifest = {"kind": "repurpose", "title": "Repurposed: " + Path(src).stem, "created": time.strftime("%Y-%m-%d %H:%M"),
                "source": {"file": Path(src).name, "credit": credit}, "outputs": outputs, "drafts": drafts,
                "picks": chosen, "log": log}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    step("done")
    return manifest


def slides(carousel, out_dir, credit=None):
    """Render carousel slides (4:5, 1080x1350) to PNG with studio/still.mjs."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    n = len(carousel)
    for i, s in enumerate(carousel):
        page = out_dir / ("slide%d.html" % (i + 1))
        page.write_text(SLIDE.replace("__HEAD__", html.escape(str(s.get("head", ""))))
                        .replace("__BODY__", html.escape(str(s.get("body", ""))))
                        .replace("__N__", "%d / %d" % (i + 1, n))
                        .replace("__CREDIT__", html.escape(credit or "")), encoding="utf-8")
        png = out_dir / ("slide%d.png" % (i + 1))
        subprocess.run(["node", str(ROOT / "studio" / "still.mjs"), str(page), str(png), "--width", "1080",
                        "--height", "1350", "--scale", "1", "--sel", "#s"], check=True, cwd=str(ROOT))
        paths.append(png)
    return paths


SLIDE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<style>
* { margin: 0; box-sizing: border-box; }
body { width: 1080px; height: 1350px; background: #0b0b0d; }
#s { width: 1080px; height: 1350px; padding: 110px 96px; display: flex; flex-direction: column; color: #f4f4f6;
     font-family: Inter, system-ui, sans-serif; background: radial-gradient(900px 900px at 30% 10%, #1a1a20, #0b0b0d 70%); }
.n { font-size: 30px; font-weight: 500; color: #a4a4ae; }
.mid { margin: auto 0; }
.rule { width: 120px; height: 10px; border-radius: 5px; background: #ffd84d; margin-bottom: 52px; }
h1 { font-size: 112px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.02; }
p { margin-top: 48px; font-size: 56px; font-weight: 500; line-height: 1.32; color: #d6d6dc; letter-spacing: -0.01em; }
.f { font-size: 26px; color: #8c8c96; }
</style></head><body><div id="s"><div class="n">__N__</div><div class="mid"><div class="rule"></div>
<h1>__HEAD__</h1><p>__BODY__</p></div><div class="f">__CREDIT__</div></div></body></html>"""
