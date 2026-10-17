"""Raw-footage edit: cut dead air, fillers, stutters and restarts from a talking-head take.

    words = words_from(engines.stt(wav))
    cut = plan(words, duration, silences=silences(wav))     # {"keep": [...], "removed": [...]}
    apply(src, cut["keep"], out)                            # re-encoded, 30 ms audio fades at every splice
    new_words = retime(words, cut["keep"])                  # word times on the edited timeline

What counts as a flub, so a deliberate repeat ("really, really long") survives:
- fillers: um, uh, er, erm, ah, hmm (Whisper keeps them when prompted with disfluent text, see engines.stt)
- stutters: the same word twice in a row ("the the", "different, different kind"), except words people
  repeat on purpose (EMPHATIC: "really, really", "very, very")
- restarts: a phrase of 2 to 5 words said again within a few words ("we went to the, we went to the store");
  the earlier take goes, the last one stays
- dead air: gaps between words longer than max_gap, and stretches the audio itself says are silent (a word
  Whisper stretched over a pause does not hide it)
"""
import re
import subprocess

from . import media

FILLERS = {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "hmm", "mm", "mhm"}
# Said twice on purpose ("really, really long", "very, very proud"): never treated as a stutter.
EMPHATIC = {"really", "very", "so", "incredibly", "much", "many", "too", "way", "far", "more", "long", "no", "yes",
            "yeah", "never", "always", "again", "over", "round", "bye", "ha", "go", "thank", "please", "hard", "big"}
MIN_KEEP = 0.25


def bare(t):
    return re.sub(r"^[^\w']+|[^\w']+$", "", str(t).lower())


def words_from(stt_result):
    out = []
    for w in stt_result.get("words", []):
        text = (w.get("word") or w.get("text") or "").strip()
        if text:
            out.append({"text": text, "start": float(w["start"]), "end": float(w["end"])})
    return out


def silences(wav, noise_db=-35, min_dur=0.5):
    """[(start, end)] where the audio is below noise_db for at least min_dur (ffmpeg silencedetect)."""
    p = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(wav), "-af",
                        "silencedetect=noise=%ddB:d=%g" % (noise_db, min_dur), "-f", "null", "-"],
                       capture_output=True, text=True)
    out, start = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    return out


def plan(words, duration, max_gap=0.5, pad=0.12, silence=None, fillers=True, stutters=True, restarts=True):
    """Decide what to cut. Returns {"keep": [{"start","end"}], "removed": [{"start","end","why","text"}]}."""
    rem = []
    b = [bare(w["text"]) for w in words]

    def cut(s, e, why, text=""):
        if e - s > 0.04:
            rem.append({"start": round(max(0.0, s), 3), "end": round(min(duration, e), 3), "why": why, "text": text})

    if words:
        cut(0, words[0]["start"] - pad, "lead-in silence")
        cut(words[-1]["end"] + pad, duration, "tail silence")
    for a, c in zip(words, words[1:]):
        if c["start"] - a["end"] > max_gap:
            cut(a["end"] + pad, c["start"] - pad, "dead air", "%.1f s" % (c["start"] - a["end"]))
    starts = [w["start"] for w in words]
    for s, e in silence or []:
        if e - s > max_gap + 2 * pad and not any(s + pad < t < e - pad for t in starts):
            cut(s + pad, e - pad, "dead air", "%.1f s quiet" % (e - s))
    if fillers:
        for i, w in enumerate(words):
            if b[i] in FILLERS:
                cut(w["start"] - 0.03, w["end"] + 0.03, "filler", w["text"])
    if stutters:
        for i in range(len(words) - 1):
            if b[i] and b[i] == b[i + 1] and b[i] not in EMPHATIC and words[i + 1]["start"] - words[i]["end"] < 0.8:
                cut(words[i]["start"], words[i + 1]["start"], "stutter", words[i]["text"])
    if restarts:
        i = 0
        while i < len(words):
            hit = None
            for n in (5, 4, 3, 2):
                if i + 2 * n > len(words):
                    continue
                phrase = b[i:i + n]
                if not all(phrase):
                    continue
                for j in range(i + n, min(i + n + 3, len(words) - n + 1)):
                    between = b[i + n:j]
                    if b[j:j + n] == phrase and all(x in FILLERS for x in between):
                        hit = (n, j)
                        break
                if hit:
                    break
            if hit:
                n, j = hit
                cut(words[i]["start"], words[j]["start"], "restart", " ".join(w["text"] for w in words[i:j]))
                i = j
            else:
                i += 1
    if restarts:
        for a, c in retakes(words):
            cut(words[a[0]]["start"], words[c[0]]["start"], "retake", " ".join(w["text"] for w in words[a[0]:a[1]]))
    merged = merge(rem)
    keep, cur = [], 0.0
    for r in merged:
        if r["start"] > cur:
            keep.append({"start": round(cur, 3), "end": r["start"]})
        cur = max(cur, r["end"])
    if cur < duration:
        keep.append({"start": round(cur, 3), "end": round(duration, 3)})
    keep = [k for k in keep if k["end"] - k["start"] >= MIN_KEEP]
    return {"keep": keep, "removed": sorted(rem, key=lambda r: r["start"])}


def phrases(words, gap=0.5):
    """[(first, end)] word-index ranges split at pauses of at least `gap` seconds."""
    out, s = [], 0
    for i in range(1, len(words) + 1):
        if i == len(words) or words[i]["start"] - words[i - 1]["end"] >= gap:
            out.append((s, i))
            s = i
    return out


def retakes(words, min_words=4, sim=0.6, window=12.0):
    """A phrase said again, reworded, right after a pause: the later take is kept. Two phrases count as takes of
    one line when their word sets overlap (Jaccard) by at least `sim` and the first one is not finished
    (no sentence end) or the second starts with the same two words. The idea of a Jaccard retake pass comes
    from herk-edit-kit (MIT, Nate Herk); this is our own implementation."""
    ph = phrases(words)
    out = []
    for p, q in zip(ph, ph[1:]):
        a = [bare(w["text"]) for w in words[p[0]:p[1]]]
        c = [bare(w["text"]) for w in words[q[0]:q[1]]]
        if len(a) < min_words or len(c) < min_words or words[q[0]]["start"] - words[p[1] - 1]["end"] > window:
            continue
        j = len(set(a) & set(c)) / float(len(set(a) | set(c)))
        unfinished = not words[p[1] - 1]["text"].rstrip().endswith((".", "?", "!"))
        if j >= sim and (unfinished or a[:2] == c[:2]) and len(a) <= len(c) + 3:
            out.append((p, q))
    return out


def merge(ranges):
    out = []
    for r in sorted(ranges, key=lambda r: (r["start"], r["end"])):
        if out and r["start"] <= out[-1]["end"]:
            out[-1] = {"start": out[-1]["start"], "end": max(out[-1]["end"], r["end"])}
        else:
            out.append({"start": r["start"], "end": r["end"]})
    return out


def kept_seconds(keep):
    return sum(k["end"] - k["start"] for k in keep)


def apply(src, keep, out, fps=30, crf=18, audio_only=False):
    """Cut src down to the kept ranges in one ffmpeg pass, with 30 ms fades at each splice."""
    parts, labels = [], []
    for i, k in enumerate(keep):
        d = k["end"] - k["start"]
        f = min(0.03, d / 4)
        if not audio_only:
            parts.append("[0:v]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS[v%d]" % (k["start"], k["end"], i))
        parts.append("[0:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=%.3f,"
                     "afade=t=out:st=%.3f:d=%.3f[a%d]" % (k["start"], k["end"], f, d - f, f, i))
        labels.append(("" if audio_only else "[v%d]" % i) + "[a%d]" % i)
    n = len(keep)
    if audio_only:
        graph = ";".join(parts) + ";" + "".join(labels) + "concat=n=%d:v=0:a=1[a]" % n
        media.run(["-i", src, "-filter_complex", graph, "-map", "[a]", out])
    else:
        graph = ";".join(parts) + ";" + "".join(labels) + "concat=n=%d:v=1:a=1[vc][a];[vc]fps=%d[v]" % (n, fps)
        media.run(["-i", src, "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", crf,
                   "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags",
                   "+faststart", out])
    return out


def retime(words, keep):
    """Word times on the edited timeline. Words cut away are dropped; a word split by a cut keeps its kept part."""
    out, offset = [], 0.0
    for k in keep:
        for w in words:
            s, e = max(w["start"], k["start"]), min(w["end"], k["end"])
            if e - s > 0.02 and (e - s) >= 0.5 * (w["end"] - w["start"]):
                out.append({"text": w["text"], "start": round(s - k["start"] + offset, 3),
                            "end": round(e - k["start"] + offset, 3)})
        offset += k["end"] - k["start"]
    out = [w for w in out if bare(w["text"]) not in FILLERS]
    return out


def map_time(t, keep):
    """Where a source time lands on the edited timeline (None if it was cut)."""
    offset = 0.0
    for k in keep:
        if k["start"] <= t <= k["end"]:
            return offset + t - k["start"]
        offset += k["end"] - k["start"]
    return None
