"""Deterministic gates for the Talkover launch film, in the rulebook's order. Fails closed.

    python checks.py [round-label]

1. storyboard: every shot has a contract, focal object, both framings; shot lengths are not uniform; every cut sits
   on the beat grid; reading hold (chars / 20 cps) fits inside each type block.
2. copy lint: banned vocabulary and structures, ASCII only.
3. composition: hyperframes lint, hyperframes check --strict (both formats).
4. technical QC on the final mp4s: ffprobe (duration, fps, size, audio), blackdetect, freezedetect, silencedetect,
   ebur128 integrated loudness and true peak; GIF size.
5. frame strips at every beat (what the blind judge sees).
Appends a JSON line per run to review/checks.jsonl and prints a summary.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import hf, media  # noqa: E402

BUILD, OUT, REV = HERE / "build", HERE / "out", HERE / "review"
SB = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
FILES = {"wide": OUT / "talkover-launch-16x9.mp4", "tall": OUT / "talkover-launch-9x16.mp4"}
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}
# declared quiet: the music stops when the reading is cut off and comes back with the answer
DECLARED_SILENCE = [(SB["music"]["stop"] - 0.1, SB["music"]["back"] + 0.1)]
BANNED_WORDS = ["delve", "crucial", "robust", "pivotal", "tapestry", "testament", "vibrant", "intricate", "interplay",
                "landscape", "showcase", "underscore", "highlight", "garner", "bolster", "meticulously", "additionally",
                "align with", "valuable insights", "resonate with", "boasts", "nestled", "groundbreaking", "renowned",
                "diverse array", "evolving landscape", "indelible mark", "seamless", "effortless", "revolutionize",
                "unleash", "elevate", "game-changer", "supercharge"]
BANNED_RE = [r"\bserves as\b", r"\bstands as\b", r"\bnot just\b.*\bbut\b", r"\bit'?s not\b.*\bit'?s\b",
             r"\bno \w+, no \w+, just\b", r"\u2014", r"[\u2018\u2019\u201c\u201d\u2026]"]


def fail(results, name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print("%-28s %s  %s" % (name, "PASS" if ok else "FAIL", detail))


def storyboard(results):
    shots = SB["shots"]
    beat = 60.0 / SB["bpm"]
    missing = [s["id"] for s in shots if not (s.get("contract") and s.get("focal") and s.get("wide") and s.get("tall"))]
    fail(results, "storyboard fields", not missing, missing or "%d shots" % len(shots))
    off = [s["id"] for s in shots if abs((s["t"] / beat) - round(s["t"] / beat)) > 1e-6]
    fail(results, "cuts on beat", not off, off or "all %d cuts on the %.2f s grid" % (len(shots), beat))
    lens = sorted({round(s["end"] - s["t"], 3) for s in shots})
    fail(results, "shot lengths vary", len(lens) >= 3, "lengths %s" % lens)
    holds = []
    for k, ty in SB["type"].items():
        chars = len(ty["head"]) + len(ty.get("sub") or "") + len(ty.get("url") or "")
        need, have = chars / 20.0, ty["end"] - ty["t"]
        holds.append("%s %.1f/%.1fs" % (k, need, have))
        if need > have:
            fail(results, "reading hold " + k, False, "needs %.1f s, has %.1f s" % (need, have))
    fail(results, "reading holds", True, ", ".join(holds))


def copy_lint(results):
    texts = []
    for ty in SB["type"].values():
        texts += [ty["head"], ty.get("sub") or "", ty.get("url") or ""]
    for ty in SB["type"].values():
        texts += [ty[k] for k in ("head_tall", "sub_tall") if ty.get(k)]
    hits = []
    for t in texts:
        low = t.lower()
        hits += ["%r: %s" % (t, w) for w in BANNED_WORDS if re.search(r"\b%s\b" % re.escape(w), low)]
        hits += ["%r: /%s/" % (t, r) for r in BANNED_RE if re.search(r, t, re.I)]
        if any(ord(c) > 127 for c in t):
            hits.append("%r: non-ASCII" % t)
    fail(results, "copy lint", not hits, hits or "%d strings clean" % len([t for t in texts if t]))


def composition(results):
    for fmt in ("wide", "tall"):
        d = BUILD / ("hf-" + fmt)
        p = subprocess.run(["npx.cmd" if os.name == "nt" else "npx", "--prefix", str(Path(__file__).resolve().parents[2]), "hyperframes", "lint"], cwd=d,
                           env=media.env_with_ffmpeg(), capture_output=True, text=True)
        m = re.search(r"(\d+) errors?, (\d+) warnings?", p.stdout + p.stderr)
        ok = p.returncode == 0 and m and m.group(1) == "0" and m.group(2) == "0"
        fail(results, "hyperframes lint " + fmt, ok, m.group(0) if m else (p.stdout + p.stderr)[-300:])
        p = subprocess.run(["npx.cmd" if os.name == "nt" else "npx", "--prefix", str(Path(__file__).resolve().parents[2]), "hyperframes", "check", "--strict",
                            "--json"], cwd=d, env=media.env_with_ffmpeg(), capture_output=True, text=True)
        (REV / ("check-%s.json" % fmt)).write_text(p.stdout, encoding="utf-8")
        try:
            j = json.loads(p.stdout[p.stdout.index("{"):])
            ok = bool(j.get("ok"))
            detail = "ok" if ok else json.dumps({k: j.get(k) for k in ("lint", "runtime", "layout", "motion",
                                                                       "contrast")})[:600]
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
    for fmt, f in FILES.items():
        if not f.exists():
            fail(results, "file " + fmt, False, "missing %s" % f)
            continue
        j = probe(f)
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        a = [s for s in j["streams"] if s["codec_type"] == "audio"]
        dur = float(j["format"]["duration"])
        ok = ((v["width"], v["height"]) == SIZE[fmt] and v["r_frame_rate"] == "30/1" and a and
              abs(dur - SB["duration"]) < 0.1 and v["codec_name"] == "h264")
        fail(results, "ffprobe " + fmt, ok, "%dx%d %s %s %.2fs audio=%s %.1f MB" % (
            v["width"], v["height"], v["r_frame_rate"], v["codec_name"], dur, bool(a), f.stat().st_size / 1048576))
        log = ffilter(f, vf="blackdetect=d=0.1:pix_th=0.06")
        blacks = [(float(x), float(y)) for x, y in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
        # allowed: the fade up from black (first 0.3 s) and the fade out (last 0.6 s)
        bad = [b for b in blacks if not (b[0] < 0.05 and b[1] < 0.4) and not (b[0] > SB["duration"] - 0.8)]
        fail(results, "blackdetect " + fmt, not bad, "segments %s, undeclared %s" % (blacks, bad))
        log = ffilter(f, vf="freezedetect=n=0.0005:d=1.2")
        fr = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
        frd = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", log)]
        # the end card holds after its last line lands (title + one line + url need ~4 s of reading)
        bad = [(s, d) for s, d in zip(fr, frd) if s < SB["type"]["end"]["t"]]
        fail(results, "freezedetect " + fmt, not bad, "freezes %s, before end card %s" % (list(zip(fr, frd)), bad))
        log = ffilter(f, af="silencedetect=n=-50dB:d=0.4")
        ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
        se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
        sil = list(zip(ss, se + [SB["duration"]] * (len(ss) - len(se))))
        bad = [s for s in sil if not any(a0 <= s[0] and s[1] <= a1 for a0, a1 in DECLARED_SILENCE)
               and not (s[0] < 0.3) and not (s[0] > SB["duration"] - 1.5)]
        fail(results, "silencedetect " + fmt, not bad, "silences %s, undeclared %s" % (sil, bad))
        log = ffilter(f, af="ebur128=peak=true")
        I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
        tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)[-1])
        fail(results, "ebur128 " + fmt, -17.0 <= I <= -15.0 and tp <= -1.0, "I=%.1f LUFS, true peak %.1f dBTP" % (I, tp))
    g = OUT / "talkover-launch.gif"
    if g.exists():
        fail(results, "gif size", g.stat().st_size < 8 * 1048576, "%.2f MB" % (g.stat().st_size / 1048576))


def strip(fmt, every_beats=1, tile_w=None, cols=None):
    """Frames at every beat, labelled with time, tiled. This (and the brief and rubric) is all the judge sees."""
    f = FILES[fmt]
    beat = 60.0 / SB["bpm"] * every_beats
    times = [round(i * beat + beat / 2, 3) for i in range(int(SB["duration"] / beat))]
    tile_w = tile_w or (480 if fmt == "wide" else 270)
    cols = cols or (6 if fmt == "wide" else 10)
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
    out = REV / ("strip-%s.png" % fmt)
    sheet.save(out)
    return out


def blank_frames(results):
    """hyperframes check passed a composition whose script failed to parse (every frame was the bare backdrop), so
    look at the beat frames themselves: a frame with almost no luminance spread has nothing on it."""
    import numpy as np
    beat = 60.0 / SB["bpm"]
    for fmt in FILES:
        d = BUILD / ("strip-" + fmt)
        blank = []
        for i, f in enumerate(sorted(d.glob("t*.png"))):
            t = i * beat + beat / 2
            if t < 0.4 or t > SB["duration"] - 0.7:
                continue
            g = np.asarray(Image.open(f).convert("L"), np.float32)
            if g.std() < 6.0 or (g > 140).mean() < 0.002:
                blank.append(round(t, 2))
        fail(results, "frames not blank " + fmt, not blank, blank or "every beat frame has content")


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%H%M")
    REV.mkdir(exist_ok=True)
    results = []
    storyboard(results)
    copy_lint(results)
    composition(results)
    technical(results)
    strips = [str(strip(f)) for f in FILES if FILES[f].exists()]
    blank_frames(results)
    rec = {"round": label, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "pass": all(r["pass"] for r in results),
           "results": results, "strips": strips}
    with open(REV / "checks.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print("ALL PASS" if rec["pass"] else "FAILURES: %d" % sum(not r["pass"] for r in results))


if __name__ == "__main__":
    main()
