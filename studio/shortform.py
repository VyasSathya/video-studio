"""Short-form vertical video from a script or a topic: python -m studio short --topic "..." --facts facts.txt

    script = script_from_topic(topic, facts)    # a text model writes beats, from the facts given and nothing else
    run(script, out_dir)                         # narration, visuals, captions, music bed, 1080x1920 render, QC

A script is {"title", "beats": [{"say": "...", "visual": {...}}]}; visual types:
    title  {"text"}            kinetic {"text"}             stat {"value", "label"}
    list   {"items": [...]}     image  {"query"} (public-domain still from Wikimedia Commons, studio.stock)
The narration is a synthetic voice (Kokoro) and the video says so on screen.
"""
import html
import json
import math
import re
import shutil
import time
from pathlib import Path

from . import edit, engines, hf, llm, media, music, overlay, qc, sound, stock

W, H = 1080, 1920
GAP = 0.28
BPM = 120
BEAT = 60.0 / BPM
TYPES = {"title", "kinetic", "stat", "list", "image"}


def esc(s):
    return html.escape(str(s), quote=True)


FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself|we|we're|our|us)\b", re.I)


def _norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", str(s).lower().replace(",", "")).split())


def _numbers(s):
    return set(re.findall(r"\d+(?:\.\d+)?", str(s).replace(",", "")))


def check_beat(b, facts_norm):
    """Why a beat cannot be used, or None. With facts given, every beat must quote them and every number in it
    must be in its quote; narration is always a third-person narrator (a synthetic voice never speaks as a
    real person)."""
    say, v = b["say"], b["visual"]
    if FIRST_PERSON.search(say):
        return "first person"
    if facts_norm is None:
        return None
    src = _norm(b.get("source", ""))
    if len(src.split()) < 4 or src not in facts_norm:
        return "source quote not found in the facts"
    nums = _numbers(say) | _numbers(json.dumps(v))
    if not nums <= _numbers(src):
        return "number not in its source: %s" % ", ".join(sorted(nums - _numbers(src)))
    return None


def tidy_visual(v, say, facts_norm):
    """On-screen words follow the same rule as narration: a stat must be a number, and with facts given, the
    content words shown must be words the facts (or this beat's narration) use."""
    v = dict(v)
    known = set((facts_norm or "").split()) | set(_norm(say).split())

    def ok(text):
        return facts_norm is None or all(w in known for w in _norm(text).split() if len(w) > 3)

    if v.get("type") == "stat" and not _numbers(v.get("value", "")):
        v = {"type": "kinetic", "text": v.get("label") or " ".join(say.split()[:4])}
    if v.get("type") == "list":
        v["items"] = [x for x in v.get("items", []) if ok(x)][:4]
        if len(v["items"]) < 2:
            v = {"type": "kinetic", "text": " ".join(say.split()[:4])}
    if v.get("type") == "kinetic" and not ok(v.get("text", "")):
        v["text"] = " ".join(say.split()[:4])
    if v.get("type") == "stat" and not ok(v.get("label", "")):
        v["label"] = ""
    return v


def script_from_topic(topic, facts="", seconds=45, voice_wpm=165, tries=3):
    words = int(seconds * voice_wpm / 60)
    facts_norm = _norm(facts) if facts else None
    prompt = (
        "Write a vertical short video script about: " + topic + "\n\n" +
        ("Use only these facts, nothing else, no numbers that are not in them:\n" + facts[:12000] + "\n\n"
         if facts else "") +
        "The narrator is an unnamed third-person voice-over. Never write as any person in the facts: no I, me, "
        "my, we, our. Return JSON only: {\"title\": at most 6 words, \"beats\": [6 to 8 beats, each {\"say\": "
        "narration of 8 to 22 words, plain spoken English, " +
        ("\"source\": 6 to 15 consecutive words copied exactly from the facts that support this beat, "
         if facts else "") +
        "\"visual\": one of {\"type\": \"title\", \"text\": at most 5 words} | "
        "{\"type\": \"kinetic\", \"text\": the 2 to 5 key words of that beat} | {\"type\": \"stat\", \"value\": a "
        "number from the facts, \"label\": at most 5 words} | {\"type\": \"list\", \"items\": 2 to 4 items of at most "
        "4 words} | {\"type\": \"image\", \"query\": 2 to 4 words to search a photo archive}}]}. "
        "About %d words of narration in total. Beat 1 is a hook with a title visual; the last beat is a clear "
        "takeaway. Use at least two image beats and at least one stat beat." % words)
    best, rejected = None, []
    for _ in range(tries):
        s = llm.complete(prompt, want_json=True)
        beats = []
        for b in s.get("beats", []):
            say = re.sub(r"\s+", " ", str(b.get("say", ""))).strip()
            v = b.get("visual") or {}
            if not say:
                continue
            if v.get("type") not in TYPES:
                v = {"type": "kinetic", "text": " ".join(say.split()[:4])}
            beat = {"say": say, "visual": tidy_visual(v, say, facts_norm), "source": str(b.get("source", ""))}
            why = check_beat(beat, facts_norm)
            if why:
                rejected.append({"say": say, "why": why})
            else:
                beats.append(beat)
        if best is None or len(beats) > len(best["beats"]):
            best = {"title": str(s.get("title", topic))[:60], "beats": beats}
        if len(beats) >= 5:
            break
    for b in best["beats"]:                   # a title card is a label: it always shows the script's title
        if b["visual"].get("type") == "title":
            b["visual"] = {"type": "kinetic", "text": " ".join(b["say"].split()[:4])}
    if best["beats"]:
        best["beats"][0]["visual"] = {"type": "title", "text": best["title"]}
    return dict(best, topic=topic, backend=llm.backend(), rejected=rejected)


def _align(script_text, asr):
    """Captions spell what the script says, timed by what the recogniser heard (when the counts agree)."""
    toks = script_text.split()
    if len(toks) == len(asr):
        return [dict(w, text=t) for w, t in zip(asr, toks)]
    return asr


def run(script, out_dir, voice="am_michael", mood="calm", quality="high", end_card=2.6, pace="calm"):
    """pace="fast": every beat starts on the beat grid of a 120 bpm launch track, a whoosh on each cut, the
    drums drop before the end card and land on it."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    comp = out / "comp"
    (comp / "img").mkdir(parents=True, exist_ok=True)
    log, credits, used = [], [], []

    def step(msg):
        log.append({"t": time.strftime("%H:%M:%S"), "step": msg})
        print("[short]", msg, flush=True)

    step("narrate %d beats" % len(script["beats"]))
    t, clips, words, beats = 0.35, [], [], []
    for i, b in enumerate(script["beats"]):
        wav = out / ("beat%02d.wav" % i)
        d = engines.tts(b["say"], wav, voice=voice)
        asr = edit.words_from(engines.stt(wav))
        for w in _align(b["say"], asr):
            words.append({"text": w["text"], "start": round(w["start"] + t, 3), "end": round(w["end"] + t, 3)})
        v = dict(b["visual"])
        if v.get("type") == "image":
            hit = stock.find(v.get("query", ""), out / "stock", avoid=used)
            if hit:
                used.append(hit["title"])
                name = "img/%02d%s" % (i, Path(hit["file"]).suffix)
                shutil.copyfile(hit["file"], comp / name)
                v["src"] = name
                credits.append(hit)
            else:
                v = {"type": "kinetic", "text": " ".join(b["say"].split()[:4])}
        beats.append({"start": round(t, 3), "dur": round(d, 3), "say": b["say"], "visual": v})
        clips.append((str(wav), t, None))
        t += d + GAP
        if pace == "fast":                     # the next beat starts on the next beat of the music
            t = math.ceil(t / BEAT) * BEAT
    if pace == "fast":
        t = math.ceil(t / BEAT) * BEAT
    total = round(t + end_card, 3)
    (out / "beats.json").write_text(json.dumps(beats, indent=1), encoding="utf-8")
    (out / "words.json").write_text(json.dumps(words), encoding="utf-8")
    step("voice track and music bed (%.1f s)" % total)
    media.mix(clips, total, out / "voice.wav")
    licences = ["music: generated by studio/music.py, owned by the project"]
    if pace == "fast":
        end_at = round(t, 3)
        music.launch_track(total, out / "bed.wav", bpm=BPM, hit_at=end_at)
        fx = sound.sfx_track([(max(0.0, b["start"] - 0.18), "whoosh-short", -12) for b in beats[1:]] +
                             [(end_at, "impact-bass-1", -10)], total, out / "sfx.wav")
        licences += fx["licences"]
        sound.add(out / "voice.wav", out / "sfx.wav", out / "voicefx.wav")
        music.duck(out / "voicefx.wav", out / "bed.wav", out / "mix.wav", music_db=-14)
    else:
        music.bed(total, out / "bed.wav", mood=mood)
        music.duck(out / "voice.wav", out / "bed.wav", out / "mix.wav")
    step("compose")
    build(comp, script["title"], beats, words, total, credits)
    step("render 9:16")
    silent = comp / "render.mp4"
    hf.render(comp, silent, quality=quality)
    final = out / "final-9x16.mp4"
    media.mux_loud(silent, out / "mix.wav", final)
    res = qc.check(final, words)
    manifest = {
        "kind": "short", "title": script["title"], "created": time.strftime("%Y-%m-%d %H:%M"),
        "source": {"topic": script.get("topic"), "credit": "Synthetic voice (Kokoro %s); music made locally" % voice},
        "script": script, "outputs": [{"label": "Short 9:16", "file": final.name, "kind": "video", "aspect": "9:16",
                                       "qc": res}],
        "credits": credits, "sound_licences": licences, "pace": pace, "log": log,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    step("done")
    return manifest


def _scene(i, b):
    v = b["visual"]
    k = v.get("type")
    if k == "title":
        inner = '<div class="t-title">%s</div><div class="rule"></div>' % esc(v.get("text", ""))
    elif k == "stat":
        inner = '<div class="t-stat" data-to="%s">%s</div><div class="t-label">%s</div>' % (
            esc(re.sub(r"[^\d.]", "", str(v.get("value", ""))) or ""), esc(v.get("value", "")), esc(v.get("label", "")))
    elif k == "list":
        inner = '<div class="t-list">%s</div>' % "".join('<div class="li"><span></span>%s</div>' % esc(x)
                                                         for x in v.get("items", [])[:4])
    elif k == "image":
        inner = '<div class="ph"><img src="%s" alt=""></div><div class="shade"></div>' % esc(v["src"])
    else:
        inner = '<div class="t-kin">%s</div>' % " ".join('<span>%s</span>' % esc(w) for w in v.get("text", "").split())
    return '<div class="scene %s" id="s%d">%s</div>' % (k, i, inner)


def build(comp, title, beats, words, total, credits):
    scenes = "\n".join(_scene(i, b) for i, b in enumerate(beats))
    gs = overlay.groups(words, 3, 18)
    caps, anim = [], []
    for gi, g in enumerate(gs):
        gid = "g%d" % gi
        caps.append('<div class="cap" id="%s"><span class="in">%s</span></div>' % (gid, "".join(
            '<span class="w" id="%s_%d">%s</span> ' % (gid, k, esc(w["text"])) for k, w in enumerate(g))))
        nxt = gs[gi + 1][0]["start"] - 0.05 if gi + 1 < len(gs) else total  # when the next group appears
        anim.append(["cap", gid, max(0, g[0]["start"] - 0.05), min(nxt, g[-1]["end"] + 0.4)])
        for k, w in enumerate(g):
            anim.append(["word", "%s_%d" % (gid, k), w["start"]])
    sc = []
    for i, b in enumerate(beats):
        end = beats[i + 1]["start"] if i + 1 < len(beats) else b["start"] + b["dur"] + GAP
        sc.append([i, b["start"], end, b["visual"].get("type")])
    credit = "Images: " + "; ".join(sorted({c["credit"] for c in credits})) if credits else ""
    page = (TEMPLATE.replace("__DUR__", "%.3f" % total).replace("__SCENES__", scenes)
            .replace("__CAPS__", "\n".join(caps)).replace("__ANIM__", json.dumps(anim))
            .replace("__SC__", json.dumps(sc)).replace("__TITLE__", esc(title))
            .replace("__CREDIT__", esc(credit)).replace("__ENDAT__", "%.3f" % (sc[-1][2] if sc else 0)))
    (Path(comp) / "index.html").write_text(page, encoding="utf-8")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root { --bg: #0b0b0d; --text: #f4f4f6; --muted: #a4a4ae; --accent: #ffd84d; --line: #2a2a30; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--bg); }
  body { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: var(--text); -webkit-font-smoothing: antialiased; }
  #root { position: relative; width: 1080px; height: 1920px; overflow: hidden;
          background: radial-gradient(900px 1100px at 50% 30%, #17171c 0%, var(--bg) 70%); }
  .scene { position: absolute; inset: 0; opacity: 0; display: flex; flex-direction: column; align-items: center;
           justify-content: center; padding: 0 90px 520px; }
  .t-title { font-size: 112px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.02; text-align: center; }
  .rule { width: 160px; height: 10px; border-radius: 5px; background: var(--accent); margin-top: 40px; }
  .t-kin { font-size: 104px; font-weight: 800; letter-spacing: -0.035em; line-height: 1.05; text-align: center; }
  .t-kin span { display: inline-block; margin: 0 14px; }
  .t-kin span:last-child { color: var(--accent); }
  .t-stat { font-size: 260px; font-weight: 800; letter-spacing: -0.05em; color: var(--accent); line-height: 1; }
  .t-label { font-size: 56px; font-weight: 600; color: var(--text); margin-top: 18px; text-align: center; }
  .t-list { display: flex; flex-direction: column; gap: 34px; width: 100%; }
  .li { display: flex; align-items: center; gap: 30px; font-size: 64px; font-weight: 700; letter-spacing: -0.02em;
        opacity: 0; border-bottom: 1px solid var(--line); padding-bottom: 30px; }
  .li span { width: 22px; height: 22px; border-radius: 50%; background: var(--accent); flex: none; }
  .scene.image { padding: 0; }
  .ph { position: absolute; inset: 0; overflow: hidden; }
  .ph img { width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 40%; }
  .shade { position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(0,0,0,0) 40%, rgba(0,0,0,.72) 100%); }
  .cap { position: absolute; left: 0; right: 0; top: 1320px; display: flex; justify-content: center; opacity: 0; padding: 0 70px; }
  .cap .in { font-weight: 800; font-size: 80px; line-height: 1.08; letter-spacing: -0.02em; text-align: center;
             text-shadow: 0 0 2px #000, 0 3px 0 #000, 0 -2px 0 #000, 3px 0 0 #000, -3px 0 0 #000, 0 8px 28px rgba(0,0,0,.6); }
  .cap .w { opacity: 0.5; }
  #prog { position: absolute; left: 0; top: 0; height: 8px; width: 0; background: var(--accent); }
  #tag { position: absolute; right: 40px; top: 36px; font-size: 26px; font-weight: 500; color: rgba(255,255,255,.78);
         text-shadow: 0 1px 4px rgba(0,0,0,.7); }
  #end { position: absolute; inset: 0; opacity: 0; display: flex; flex-direction: column; align-items: center;
         justify-content: center; padding: 0 90px; background: var(--bg); }
  #end h1 { font-size: 92px; font-weight: 800; letter-spacing: -0.04em; text-align: center; line-height: 1.05; }
  #end .rule { margin: 36px 0; }
  #end p { font-size: 30px; line-height: 1.5; color: var(--muted); text-align: center; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1080" data-height="1920">
__SCENES__
__CAPS__
  <div id="prog"></div>
  <div id="tag">Synthetic voice</div>
  <div id="end"><h1>__TITLE__</h1><div class="rule"></div><p>Narration is a synthetic voice (Kokoro).<br>__CREDIT__</p></div>
</div>
<script>
  const A = __ANIM__, SC = __SC__, D = __DUR__, ENDAT = __ENDAT__;
  const tl = gsap.timeline({ paused: true });
  tl.to("#prog", { width: "100%", duration: D, ease: "none" }, 0);
  for (const [i, s, e, k] of SC) {
    const id = "#s" + i;
    tl.fromTo(id, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power1.out" }, Math.max(0, s - 0.25));
    tl.to(id, { opacity: 0, duration: 0.3, ease: "power1.in" }, e - 0.15);
    if (k === "title") {
      tl.fromTo(id + " .t-title", { y: 40, scale: 0.94 }, { y: 0, scale: 1, duration: 0.6, ease: "power3.out" }, s - 0.2);
      tl.fromTo(id + " .rule", { width: 0 }, { width: 160, duration: 0.5, ease: "power2.out" }, s + 0.2);
    } else if (k === "kinetic") {
      tl.fromTo(id + " .t-kin span", { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.35, stagger: 0.16, ease: "back.out(1.6)" }, s - 0.1);
    } else if (k === "stat") {
      const el = document.querySelector(id + " .t-stat");
      const to = parseFloat(el.dataset.to);
      const label = el.textContent;
      if (!isNaN(to) && /^[\d.]+$/.test(label.trim())) {
        tl.fromTo(el, { textContent: 0 }, { textContent: to, snap: { textContent: 1 },
                  duration: Math.min(1.2, e - s - 0.3), ease: "power2.out" }, s);
      }
      tl.fromTo(id + " .t-stat", { scale: 0.8 }, { scale: 1, duration: 0.5, ease: "back.out(1.7)" }, s - 0.1);
      tl.fromTo(id + " .t-label", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.4 }, s + 0.3);
    } else if (k === "list") {
      const n = document.querySelectorAll(id + " .li").length;
      tl.fromTo(id + " .li", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out",
                stagger: Math.min(0.9, Math.max(0.3, (e - s - 0.6) / Math.max(1, n))) }, s - 0.2);
    } else if (k === "image") {
      tl.fromTo(id + " img", { scale: 1.0 }, { scale: 1.12, duration: e - s + 0.6, ease: "none" }, s - 0.3);
    }
  }
  for (const a of A) {
    if (a[0] === "cap") {
      tl.set("#" + a[1], { opacity: 1 }, a[2]);
      tl.fromTo("#" + a[1] + " .in", { scale: 0.92 }, { scale: 1, duration: 0.18, ease: "back.out(2)" }, a[2]);
      tl.set("#" + a[1], { opacity: 0 }, a[3]);
    } else if (a[0] === "word") {
      tl.to("#" + a[1], { opacity: 1, color: "#ffd84d", duration: 0.06, ease: "none" }, a[2]);
      tl.to("#" + a[1], { color: "#ffffff", duration: 0.2, ease: "none" }, a[2] + 0.32);
    }
  }
  tl.to("#end", { opacity: 1, duration: 0.45, ease: "power1.out" }, ENDAT);
  tl.to("#tag", { opacity: 0, duration: 0.3 }, ENDAT);
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""
