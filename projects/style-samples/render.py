"""Whiteboard and course style samples on a public-domain talk, made with the five-step method, no human step:

  1. transcribe and 2. cut: reuse the raw-edit sample's verbatim words and cut (projects/raw-edit-sample)
  3. plan beats from a plain-language prompt (studio.beats: a text model reads the prompt; triggers are matched
     to words actually said)
  4. compose (studio.styles) and render 5. verify: stills at every beat, deterministic gates, QC, log

    python projects/style-samples/render.py [--stills]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from studio import beats, edit, media, overlay, qc, review, styles, verify  # noqa: E402

START, END = 27.0, 58.4
PROMPTS = {
    "whiteboard": ("When he says spending a year in space, take over the screen and draw a clock with the words "
                   "'A year in space'. When he says why spend a year, put the question 'Why a year?' on the board "
                   "beside him. When he says push our boundaries, list on the board: learn, push our limits, run the "
                   "station. When he says go to Mars, take over and draw Mars with the words 'Next: Mars'. "
                   "Highlight the key words at the bottom."),
    "course": ("When he says spending a year in space, move him to the side and show the big number '1 year'. "
               "When he says why spend a year, show the takeaway 'Why a year in space?'. When he says push our "
               "boundaries, show bullets: to learn, push our limits, run the station. When he says go to Mars, "
               "show a picture of Mars. Highlight the key words at the bottom."),
}
ACCENT = {"whiteboard": "#e8590c", "course": "#7c6cff"}


def clip(src_dir, out):
    """The stretch START..END of the edited cut, with its words on the new clock."""
    words = json.loads((src_dir / "cut.words.json").read_text(encoding="utf-8"))
    mp4 = out / "clip.mp4"
    media.run(["-ss", START, "-to", END, "-i", src_dir / "cut.mp4", "-c:v", "libx264", "-crf", 16, "-preset", "fast",
               "-c:a", "aac", "-b:a", "192k", mp4])
    wav = out / "clip.wav"
    media.run(["-i", mp4, "-vn", "-ac", 2, "-ar", 48000, wav])
    cw = [{"text": w["text"], "start": round(w["start"] - START, 3), "end": round(w["end"] - START, 3)}
          for w in words if w["start"] >= START and w["end"] <= END]
    return mp4, wav, cw


def main():
    only_stills = "--stills" in sys.argv
    src = media.work_dir("raw-edit-sample")
    out = media.work_dir("style-samples")
    mp4, wav, words = clip(src, out)
    dur = media.duration(mp4)
    outputs = []
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for style, prompt in PROMPTS.items():
        if only and style != only:              # keep the other style's last render
            prev = out / ("%s-16x9.mp4" % style)
            if prev.exists():
                outputs.append({"label": "%s style" % style.capitalize(), "file": prev.name, "kind": "video",
                                "aspect": "16:9", "qc": qc.check(prev, words), "why": prompt})
            continue
        plan_f = out / ("beats-%s.json" % style)
        if not plan_f.exists():
            parsed = beats.parse(prompt, words)
            placed = beats.place(parsed["rules"], words, dur)
            plan_f.write_text(json.dumps(dict(parsed, **placed), indent=1), encoding="utf-8")
        plan = json.loads(plan_f.read_text(encoding="utf-8"))
        keys = beats.keywords(words) if plan.get("highlight_keywords", True) else []
        comp = out / ("comp-" + style)
        info = styles.build(comp, mp4, words, plan["beats"], style=style, accent=ACCENT[style],
                            credit="Footage: NASA (public domain)", key_times=keys)
        times = [0.5] + [x for b in plan["beats"] for x in (round(b["t"] + 0.3, 2), round(b["t"] + 1.9, 2), round(b["end"] - 0.45, 2), round(b["end"] + 0.7, 2))]
        verify.stills(comp, [], out / ("stills-" + style), times=sorted(t for t in times if t < dur - 0.1))
        gate = verify.hf_check_json(comp)
        verify.log(out, 1, "gates " + style, [gate["result"].get("lint", {}).get("findings", [])[:3],
                                               "not said: %s" % plan.get("not_said")])
        if only_stills:
            continue
        final = overlay.finish(comp, wav, out / ("%s-16x9.mp4" % style))
        outputs.append({"label": "%s style" % style.capitalize(), "file": final.name, "kind": "video",
                        "aspect": "16:9", "qc": qc.check(final, words), "why": prompt})
    if not only_stills:
        m = {"kind": "styles", "title": "Whiteboard and course styles", "source": {"credit": "Footage: NASA (public domain)"},
             "outputs": outputs, "images": [{"label": "%s frames at every beat" % s.capitalize(),
                                             "file": "stills-%s/sheet.png" % s} for s in PROMPTS]}
        (out / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        review.page(out)


if __name__ == "__main__":
    main()
