"""Story from a folder: point it at recordings, get one reel that tells a story. python -m studio story DIR

1. transcribe every recording (cached per file)         4. cut each moment, dead air out (studio.edit), join
2. score sentence-aligned moments across all of them       them with 0.3 s audio crossfades
   (studio.picks.clips, small batches)                   5. captions over the joined reel (studio.overlay),
3. a text model orders the best moments into a story:      -14 LUFS, QC, manifest + review page
   a beginning that sets it up, a middle, an ending;
   it sees only the moments' own words
The reel keeps the speakers' exact words; nothing is rewritten. An agent can write story.json itself instead.
"""
import json
import time
from pathlib import Path

from . import edit, engines, llm, media, overlay, picks, qc

EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v")
VERBATIM = "Umm, uh, so, like, I I think, you know, we we went there."


def transcribe_folder(folder, cache):
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in EXT):
        wf = cache / (f.stem + ".words.json")
        if not wf.exists():
            wav = cache / (f.stem + ".wav")
            media.run(["-i", f, "-vn", "-ac", 1, "-ar", 16000, wav])
            wf.write_text(json.dumps(edit.words_from(engines.stt(wav, prompt=VERBATIM))), encoding="utf-8")
            wav.unlink()
        out.append({"file": str(f), "words": json.loads(wf.read_text(encoding="utf-8"))})
    return out


def order(moments):
    lines = "\n".join("M%d: %s" % (i, m["text"]) for i, m in enumerate(moments))
    res = llm.complete(
        "Moments cut from several recordings:\n\n" + lines + "\n\nPick 3 to 5 of them and put them in an order "
        "that tells one story: a beginning that sets it up, a middle, an ending that lands. Use only what the "
        "moments say. Return JSON only: {\"order\": [moment numbers], \"title\": at most 6 words, true to them, "
        "\"why\": one sentence}", want_json=True)
    seq = []
    for x in res.get("order", []):
        try:
            i = int(str(x).lstrip("M"))
        except ValueError:
            continue
        if 0 <= i < len(moments) and i not in seq:
            seq.append(i)
    return {"order": seq or list(range(min(4, len(moments)))), "title": str(res.get("title", ""))[:60],
            "why": res.get("why", ""), "backend": llm.backend()}


def run(folder, out_dir, per_file=3, credit=None, quality="high"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def step(m):
        log.append({"t": time.strftime("%H:%M:%S"), "step": m})
        print("[story]", m, flush=True)

    step("transcribe")
    recs = transcribe_folder(folder, out / "words")
    moments = []
    sf = out / "moments.json"
    if not sf.exists():
        step("score moments")
        for r in recs:
            for c in picks.clips(r["words"], n=per_file, min_s=12, max_s=35)["clips"]:
                moments.append(dict(c, file=r["file"]))
        sf.write_text(json.dumps(moments, indent=1), encoding="utf-8")
    moments = json.loads(sf.read_text(encoding="utf-8"))
    of = out / "story.json"
    if not of.exists():
        step("order the story")
        of.write_text(json.dumps(order(moments), indent=1), encoding="utf-8")
    story = json.loads(of.read_text(encoding="utf-8"))
    step("cut %d moments" % len(story["order"]))
    parts, words, t0 = [], [], 0.0
    for k, i in enumerate(story["order"]):
        m = moments[i]
        rec = next(r for r in recs if r["file"] == m["file"])
        s, e = max(0.0, m["start"] - 0.2), m["end"] + 0.35
        raw = out / ("m%d-raw.mp4" % k)
        media.run(["-ss", "%.3f" % s, "-to", "%.3f" % e, "-i", m["file"], "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30", "-c:v", "libx264", "-crf", 16, "-preset", "fast",
                   "-ar", 48000, "-ac", 2, "-c:a", "aac", "-b:a", "192k", raw])
        cw = [{"text": w["text"], "start": round(w["start"] - s, 3), "end": round(w["end"] - s, 3)}
              for w in rec["words"] if w["start"] >= s and w["end"] <= e]
        rw = out / ("m%d.wav" % k)
        media.run(["-i", raw, "-vn", "-ac", 1, "-ar", 16000, rw])
        cut = edit.plan(cw, media.duration(raw), silence=edit.silences(rw))
        part = edit.apply(raw, cut["keep"], out / ("m%d.mp4" % k))
        for w in edit.retime(cw, cut["keep"]):
            words.append({"text": w["text"], "start": round(w["start"] + t0, 3), "end": round(w["end"] + t0, 3)})
        t0 += media.duration(part)
        parts.append(part)
    reel = out / "reel-cut.mp4"
    lst = out / "parts.txt"
    lst.write_text("".join("file '%s'\n" % Path(p).as_posix() for p in parts), encoding="utf-8")
    media.run(["-f", "concat", "-safe", 0, "-i", lst, "-c", "copy", reel])
    wav = out / "reel.wav"
    media.run(["-i", reel, "-vn", "-ac", 2, "-ar", 48000, wav])
    step("captions and render")
    overlay.build(out / "comp", reel, words, size=(1920, 1080), credit=credit, title=story.get("title") or None)
    final = overlay.finish(out / "comp", wav, out / "story-16x9.mp4", quality=quality)
    m = {"kind": "story", "title": story.get("title") or "Story reel", "created": time.strftime("%Y-%m-%d %H:%M"),
         "source": {"folder": str(folder), "credit": credit},
         "outputs": [{"label": "Story reel 16:9", "file": final.name, "kind": "video", "aspect": "16:9",
                      "qc": qc.check(final, words), "why": story.get("why", "")}],
         "story": story, "moments": [moments[i] for i in story["order"]], "log": log}
    (out / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    step("done")
    return m
