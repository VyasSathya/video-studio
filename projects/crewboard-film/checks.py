"""Deterministic gates for the crewboard launch film, in the rulebook's order. Fails closed.

    python checks.py [round-label]

1. storyboard: every shot has a contract, focal object and both framings; shot lengths vary; every cut and every
   page event sits on the beat grid; reading hold (characters / 20 per second) fits each type block.
2. copy lint: Talkover's banned vocabulary and structures plus studio/verify.copy_lint (banned words, ASCII,
   at most 42 characters per line), titles at most 5 words.
3. framing: re-reads build/cameras.json and rects.json; no frame edge cuts a line of text or a visible control at
   any moment of any push (outside the opaque type bands).
4. tokens: every colour literal in the compositions is a crewboard theme token, black or white light, or a light
   mixed from a status token.
5. privacy: no home folder, user name or email anywhere in the page text the film shows.
6. composition: hyperframes lint and hyperframes check --strict (both formats).
7. technical QC on the final mp4s: ffprobe, blackdetect, freezedetect, silencedetect, ebur128 loudness and true
   peak; GIF size and width.
8. frame strips at every beat (what the blind judges see) and the blank-frame check on them.
Appends one JSON line per run to review/checks.jsonl (project) and prints a summary.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from studio import hf, media, verify  # noqa: E402
import storyboard as SBM  # noqa: E402

WORK = SBM.WORK
BUILD, OUT, RREV = WORK / "build", WORK / "out", WORK / "review"
PREV = HERE / "review"
SB = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
FILES = {"wide": OUT / "crewboard-launch-16x9.mp4", "tall": OUT / "crewboard-launch-9x16.mp4"}
GIF = OUT / "crewboard-launch.gif"
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}
BANNED_WORDS = ["delve", "crucial", "robust", "pivotal", "tapestry", "testament", "vibrant", "intricate", "interplay",
                "landscape", "showcase", "underscore", "highlight", "garner", "bolster", "meticulously", "additionally",
                "align with", "valuable insights", "resonate with", "boasts", "nestled", "groundbreaking", "renowned",
                "diverse array", "evolving landscape", "indelible mark", "seamless", "effortless", "revolutionize",
                "unleash", "elevate", "game-changer", "supercharge"]
BANNED_RE = [r"\bserves as\b", r"\bstands as\b", r"\bnot just\b.*\bbut\b", r"\bit'?s not\b.*\bit'?s\b",
             r"\bno \w+, no \w+, just\b", r"\u2014", r"[\u2018\u2019\u201c\u201d\u2026]", r"!"]
def _private_terms():
    """What must never appear on screen: this machine's user and home folder names, generic home and mail
    patterns, and anything listed in STUDIO_PRIVATE_TERMS (comma separated; keep private names out of the code)."""
    import getpass
    import os
    terms = [r"/users/", r"\\users\\", r"/home/", r"appdata", r"onedrive", r"@gmail", r"@icloud"]
    for t in [getpass.getuser(), os.path.basename(os.path.expanduser("~"))] + \
            [x.strip() for x in os.environ.get("STUDIO_PRIVATE_TERMS", "").split(",")]:
        if t and len(t) > 2:
            terms.append(re.escape(t))
    return terms


PRIVATE = _private_terms() + [r"C:\\\\Users", r"C:/Users"]


def fail(results, name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print("%-30s %s  %s" % (name, "PASS" if ok else "FAIL", detail))


def storyboard(results):
    shots = SB["shots"]
    beat = 60.0 / SB["bpm"]
    missing = [s["id"] for s in shots if not (s.get("contract") and s.get("focal") and s.get("wide") and s.get("tall"))]
    fail(results, "storyboard fields", not missing, missing or "%d shots" % len(shots))
    off = [s["id"] for s in shots if abs((s["t"] / beat) - round(s["t"] / beat)) > 1e-6]
    off += ["event %s" % e["t"] for e in SB["events"] if abs((e["t"] / beat) - round(e["t"] / beat)) > 1e-6]
    off += ["tick %s" % t for t in SB["music"]["ticks"] if abs((t / beat) - round(t / beat)) > 1e-6]
    fail(results, "cuts and events on beat", not off, off or "%d cuts, %d events on the %.2f s grid" % (
        len(shots), len(SB["events"]), beat))
    lens = sorted({round(s["end"] - s["t"], 3) for s in shots})
    fail(results, "shot lengths vary", len(lens) >= 3, "lengths %s" % lens)
    holds, bad = [], []
    for k, ty in SB["type"].items():
        chars = len(ty["head"]) + len(ty.get("sub") or "") + len(ty.get("url") or "") + sum(len(x) for x in ty.get("term") or [])
        need, have = chars / 20.0, ty["end"] - ty["t"]
        holds.append("%s %.1f/%.1fs" % (k, need, have))
        if need > have:
            bad.append(k)
    fail(results, "reading holds", not bad, ", ".join(holds) + (" short: %s" % bad if bad else ""))


def texts():
    out = []
    for ty in SB["type"].values():
        for k in ("head", "head_tall", "head_two", "sub", "sub_tall", "url"):
            if ty.get(k):
                out.append(ty[k])
        out += ty.get("term") or []
    return out


def copy_lint(results):
    hits = []
    for t in texts():
        low = t.lower()
        hits += ["%r: %s" % (t, w) for w in BANNED_WORDS if re.search(r"\b%s\b" % re.escape(w), low)]
        hits += ["%r: /%s/" % (t, r) for r in BANNED_RE if re.search(r, t, re.I)]
    hits += verify.copy_lint(texts(), max_line=42)
    heads = [ty["head"].replace("\n", " ") for k, ty in SB["type"].items() if k != "end"]
    hits += verify.copy_lint(heads, max_line=42, max_words=5)
    caseok = [h for h in heads if not (h[0].isupper() and h.endswith("."))]
    hits += ["not sentence case with a period: %r" % h for h in caseok]
    fail(results, "copy lint", not hits, hits or "%d strings clean, titles <= 5 words" % len(texts()))


def framing(results):
    import build as B
    cams = json.loads((BUILD / "cameras.json").read_text(encoding="utf-8"))
    bad = []
    for fmt in ("wide", "tall"):
        for s in SB["shots"]:
            if s.get("hero") or s.get("dof") or s.get("hide_page") or s.get("whole"):
                continue
            cam = cams[fmt][s["id"]]["cam"]
            cut = B.edge_cuts(cam, fmt, B.states_in(s["t"], s["end"]), labels=True)
            if cut:
                bad.append("%s %s: %s" % (fmt, s["id"], sorted(set(cut))[:4]))
    fail(results, "frame edges clear of text", not bad, bad or "no edge cuts a line or control in %d framings" % (
        2 * sum(1 for s in SB["shots"] if not (s.get("hero") or s.get("dof") or s.get("hide_page") or s.get("whole")))))


def tokens(results):
    import build as B
    tok = B.tokens()
    allowed = {(0, 0, 0), (255, 255, 255)}
    for theme in ("dark", "light"):
        allowed |= {v[:3] for v in tok[theme].values()}
    neutral = (138, 140, 146)
    allowed |= {neutral, (196, 196, 200)} | {B.mix(tok["dark"][k], neutral, 0.38) for k in ("doing", "waiting", "done")}
    bad = []
    for fmt in ("wide", "tall"):
        html = (BUILD / ("hf-" + fmt) / "index.html").read_text(encoding="utf-8")
        for m in re.finditer(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", html):
            c = tuple(int(x) for x in m.groups())
            if c not in allowed:
                bad.append("%s %s" % (fmt, c))
        ids = set(re.findall(r'id="([^"]+)"', html)) | {"fadeB"}
        for m in re.finditer(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", html):
            if m.group(1) in ids:
                continue
            if m.group(0).lower() not in ("#000", "#000000", "#fff", "#ffffff"):
                bad.append("%s %s" % (fmt, m.group(0)))
        for m in re.finditer(r"font-family:\s*[\"']?([A-Za-z][A-Za-z ]*)", html):
            if m.group(1).strip() not in (tok["font"], tok["mono"]):
                bad.append("%s font %s" % (fmt, m.group(1)))
    fail(results, "tokens from crewboard theme", not bad, sorted(set(bad))[:8] or
         "colours and fonts all from web/index.html (%s, %s)" % (tok["font"], tok["mono"]))


def privacy(results):
    rects = json.loads((BUILD / "rects.json").read_text(encoding="utf-8"))
    words = set()
    for st in rects["states"]:
        words |= {r[4] for r in st["text"]}
    # the film's own type (titles, the public repo URL on the end card) is covered by copy lint; this is the UI
    blob = "\n".join(sorted(words))
    hits = [p for p in PRIVATE if re.search(p, blob, re.I)]
    fail(results, "no personal data in frames", not hits, hits or "%d distinct UI strings, demo data only" % len(words))


def composition(results):
    for fmt in ("wide", "tall"):
        d = BUILD / ("hf-" + fmt)
        env = media.env_with_ffmpeg()
        env.update(HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")
        p = subprocess.run([hf.npx(), "--prefix", str(hf.ROOT), "hyperframes", "lint"], cwd=d, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.search(r"(\d+) errors?, (\d+) warnings?", p.stdout + p.stderr)
        ok = p.returncode == 0 and m and m.group(1) == "0" and m.group(2) == "0"
        fail(results, "hyperframes lint " + fmt, ok, m.group(0) if m else (p.stdout + p.stderr)[-300:])
        p = subprocess.run([hf.npx(), "--prefix", str(hf.ROOT), "hyperframes", "check", "--strict", "--json"], cwd=d,
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (RREV / ("check-%s.json" % fmt)).write_text(p.stdout, encoding="utf-8")
        try:
            j = json.loads(p.stdout[p.stdout.index("{"):p.stdout.rindex("}") + 1])
            ok = bool(j.get("ok"))
            detail = "ok" if ok else json.dumps({k: j.get(k) for k in ("lint", "runtime", "layout", "motion",
                                                                       "contrast")})[:700]
        except Exception as e:  # noqa: BLE001
            ok, detail = False, "unparsed: %s %s" % (e, (p.stdout + p.stderr)[-300:])
        fail(results, "hyperframes check --strict " + fmt, ok and p.returncode == 0, detail)


def probe(path):
    out = subprocess.run([media.ffprobe_bin(), "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def ffilter(path, vf=None, af=None):
    args = [media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path)]
    args += (["-vf", vf] if vf else ["-vn"]) + (["-af", af] if af else ["-an"]) + ["-f", "null", "-"]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("filter failed: %s" % p.stderr[-400:])
    return p.stderr


def technical(results):
    D = SB["duration"]
    for fmt, f in FILES.items():
        if not f.exists():
            fail(results, "file " + fmt, False, "missing %s" % f)
            continue
        j = probe(f)
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        a = [s for s in j["streams"] if s["codec_type"] == "audio"]
        dur = float(j["format"]["duration"])
        ok = ((v["width"], v["height"]) == SIZE[fmt] and v["r_frame_rate"] == "30/1" and a and abs(dur - D) < 0.1
              and v["codec_name"] == "h264")
        fail(results, "ffprobe " + fmt, ok, "%dx%d %s %s %.2fs audio=%s %.1f MB" % (
            v["width"], v["height"], v["r_frame_rate"], v["codec_name"], dur, bool(a), f.stat().st_size / 1048576))
        log = ffilter(f, vf="blackdetect=d=0.1:pix_th=0.06")
        blacks = [(float(x), float(y)) for x, y in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
        bad = [b for b in blacks if not (b[0] < 0.05 and b[1] < 0.4) and not (b[0] > D - 0.8)]
        fail(results, "blackdetect " + fmt, not bad, "segments %s, undeclared %s" % (blacks, bad))
        log = ffilter(f, vf="freezedetect=n=0.0005:d=1.2")
        fr = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
        frd = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", log)]
        bad = [(s, d) for s, d in zip(fr, frd) if s < SB["type"]["end"]["t"]]
        fail(results, "freezedetect " + fmt, not bad, "freezes %s, before end card %s" % (list(zip(fr, frd)), bad))
        log = ffilter(f, af="silencedetect=n=-50dB:d=0.4")
        ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
        se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
        sil = list(zip(ss, se + [D] * (len(ss) - len(se))))
        bad = [s for s in sil if not (s[0] < 0.3) and not (s[0] > D - 1.5)]
        fail(results, "silencedetect " + fmt, not bad, "silences %s, undeclared %s" % (sil, bad))
        log = ffilter(f, af="ebur128=peak=true")
        I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
        tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)[-1])
        fail(results, "ebur128 " + fmt, -17.0 <= I <= -15.0 and tp <= -1.0, "I=%.1f LUFS, true peak %.1f dBTP" % (I, tp))
    if GIF.exists():
        w = Image.open(GIF).size[0]
        mb = GIF.stat().st_size / 1048576
        fail(results, "gif size", mb < 8 and w == 960, "%.2f MB at %d px" % (mb, w))
    else:
        fail(results, "gif size", False, "missing")


def strip(fmt):
    """Frames at every beat (0.25 s after it), labelled with time, tiled: what the judges see."""
    f = FILES[fmt]
    beat = 60.0 / SB["bpm"]
    times = [round(i * beat + beat / 2, 3) for i in range(int(SB["duration"] / beat))]
    tile_w, cols = (480, 6) if fmt == "wide" else (270, 10)
    tmp = BUILD / ("strip-" + fmt)
    tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    for i, t in enumerate(times):
        media.run(["-ss", "%.3f" % t, "-i", f, "-frames:v", 1, "-vf", "scale=%d:-2:flags=lanczos" % tile_w,
                   tmp / ("t%03d.png" % i)])
    ims = [Image.open(tmp / ("t%03d.png" % i)) for i in range(len(times))]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    pad, lab = 6, 22
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + lab + pad) + pad), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for i, (im, t) in enumerate(zip(ims, times)):
        x, y = pad + (i % cols) * (w + pad), pad + (i // cols) * (h + lab + pad)
        d.text((x + 2, y + 3), "%.1fs" % t, fill=(200, 200, 205), font=font)
        sheet.paste(im, (x, y + lab))
    out = RREV / ("strip-%s.png" % fmt)
    sheet.save(out)
    shutil.copyfile(out, PREV / out.name)
    return out


def blank_frames(results):
    beat = 60.0 / SB["bpm"]
    for fmt in FILES:
        frames = sorted((BUILD / ("strip-" + fmt)).glob("t*.png"))
        keep = [f for i, f in enumerate(frames) if 0.4 < i * beat + beat / 2 < SB["duration"] - 0.7]
        bad = verify.blank_frames(keep)
        fail(results, "frames not blank " + fmt, not bad, [Path(b).name for b in bad] or
             "%d beat frames have content" % len(keep))


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%H%M")
    RREV.mkdir(parents=True, exist_ok=True)
    PREV.mkdir(parents=True, exist_ok=True)
    results = []
    storyboard(results)
    copy_lint(results)
    framing(results)
    tokens(results)
    privacy(results)
    composition(results)
    technical(results)
    strips = [str(strip(f)) for f in FILES if FILES[f].exists()]
    blank_frames(results)
    rec = {"round": label, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "pass": all(r["pass"] for r in results),
           "results": results, "strips": strips}
    with open(PREV / "checks.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
    n = sum(r["pass"] for r in results)
    print("ALL PASS (%d/%d)" % (n, len(results)) if rec["pass"] else "FAILURES: %d of %d" % (len(results) - n, len(results)))


if __name__ == "__main__":
    main()
