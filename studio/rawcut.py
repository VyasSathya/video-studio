"""Raw footage in, finished cuts out: python -m studio rawcut take.mp4 --name "..." --role "..." --credit "...".

1. transcribe verbatim (fillers kept) with word times     4. reframe to 9:16 shot by shot (face crop or fit)
2. plan cuts: dead air, fillers, stutters, restarts,       5. title and callouts from a text model, anchored to
   retakes (studio.edit), drawn on a timeline for review      words actually said (studio.picks)
3. apply the cut once, 30 ms fades at every splice         6. captions + lower third + callouts in HyperFrames,
                                                              render 16:9 and 9:16, audio at -14 LUFS, QC
Everything is written to the run folder, with manifest.json for the review page.
"""
import json
import time
from pathlib import Path

from . import edit, engines, media, overlay, picks, qc, reframe, timeline

VERBATIM = "Umm, uh, so, like, I I think, you know, we we went there."


def run(src, out_dir, name=None, role=None, credit=None, start=None, end=None, aspects=("16:9", "9:16"),
        max_gap=0.5, title=None, use_model=True, quality="high"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def step(msg):
        log.append({"t": time.strftime("%H:%M:%S"), "step": msg})
        print("[rawcut]", msg, flush=True)

    raw = out / "raw.mp4"
    clip = []
    if start is not None:
        clip += ["-ss", start]
    if end is not None:
        clip += ["-to", end]
    step("normalise source")
    media.run(clip + ["-i", src, "-c:v", "libx264", "-crf", 16, "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a",
                      "aac", "-b:a", "192k", raw])
    wav = out / "raw.wav"
    media.run(["-i", raw, "-vn", "-ac", 1, "-ar", 16000, wav])
    step("transcribe")
    words = edit.words_from(engines.stt(wav, prompt=VERBATIM))
    (out / "words.json").write_text(json.dumps(words), encoding="utf-8")
    dur = media.duration(raw)
    step("plan cuts")
    cut = edit.plan(words, dur, max_gap=max_gap, silence=edit.silences(wav))
    (out / "cut.json").write_text(json.dumps(cut, indent=1), encoding="utf-8")
    timeline.render(raw, wav, cut, out / "timeline.png")
    step("apply cut (%.1f s kept of %.1f s)" % (edit.kept_seconds(cut["keep"]), dur))
    cut_mp4 = edit.apply(raw, cut["keep"], out / "cut.mp4")
    cut_wav = out / "cut.wav"
    media.run(["-i", cut_mp4, "-vn", "-ac", 2, "-ar", 48000, cut_wav])
    new_words = edit.retime(words, cut["keep"])
    (out / "cut.words.json").write_text(json.dumps(new_words), encoding="utf-8")
    calls = {"title": title or "", "callouts": [], "backend": None}
    if use_model:
        step("title and callouts")
        try:
            calls = picks.callouts(new_words)
            if title:
                calls["title"] = title
        except Exception as e:
            step("no text model answered (%s); no callouts" % e)
    (out / "callouts.json").write_text(json.dumps(calls, indent=1), encoding="utf-8")
    outputs = []
    for asp in aspects:
        tag = asp.replace(":", "x")
        if asp == "9:16":
            step("reframe 9:16")
            plan = reframe.plan(cut_mp4)
            (out / "shots.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
            video, size = reframe.render(cut_mp4, plan, out / "cut-9x16.mp4"), (1080, 1920)
        else:
            w, h = reframe.probe_size(cut_mp4)
            video, size = cut_mp4, (1920, 1080)
        comp = out / ("comp-" + tag)
        overlay.build(comp, video, new_words, size=size, name=name if asp == "9:16" else None, role=role,
                      callouts=calls["callouts"], credit=credit, title=calls.get("title") or None)
        step("render %s" % asp)
        final = overlay.finish(comp, cut_wav, out / ("final-%s.mp4" % tag), quality=quality)
        res = qc.check(final, new_words)
        outputs.append({"label": "Edited cut %s" % asp, "file": final.name, "kind": "video", "aspect": asp,
                        "qc": res})
    removed = [r for r in cut["removed"]]
    manifest = {
        "kind": "rawcut", "title": calls.get("title") or Path(src).stem, "created": time.strftime("%Y-%m-%d %H:%M"),
        "source": {"file": Path(src).name, "start": start, "end": end, "seconds": round(dur, 2), "credit": credit},
        "summary": {"kept": round(edit.kept_seconds(cut["keep"]), 2), "cuts": len(removed),
                    "by_reason": {k: sum(1 for r in removed if r["why"] == k) for k in sorted({r["why"] for r in removed})}},
        "outputs": outputs, "images": [{"label": "Cuts on the source timeline", "file": "timeline.png"}],
        "decisions": removed, "callouts": calls, "log": log,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    step("done")
    return manifest
