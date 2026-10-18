"""Deterministic gates for the agent-brain launch film, in the rulebook's order. Fails closed.

    python checks.py [round-label]

1. storyboard: every shot has a contract, focal object, both framings; shot lengths vary; every cut sits on the beat
   grid; reading hold (characters / 20 per second) fits inside each type block; caption lines at most 42 characters.
2. provenance: every character on every card is the captured output (data/session.json, data/files.json) with only
   display wrapping; no machine path, user name or home folder anywhere in the compositions.
3. copy lint: banned vocabulary and structures (studio.verify plus the Talkover list), ASCII only, titles at most 5
   words.
4. composition: hyperframes lint and hyperframes check --strict, both formats.
5. technical QC on the final mp4s: ffprobe, blackdetect, freezedetect, silencedetect, ebur128 loudness and true peak;
   GIF size and width.
6. frame strips at every beat (what the blind judge sees) and the blank-frame gate on them.
Appends one JSON line per run to review/checks.jsonl (project) and prints a summary.
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
sys.path.insert(0, str(HERE))
from studio import media, verify  # noqa: E402
from storyboard import BUILD, WORK, STEP, FILES as SRC_FILES, wrap  # noqa: E402

OUT, REV, PREV = WORK / "out", WORK / "review", HERE / "review"
SB = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
FILES = {"wide": OUT / "agent-brain-launch-16x9.mp4", "tall": OUT / "agent-brain-launch-9x16.mp4"}
GIF = OUT / "agent-brain-launch.gif"
SIZE = {"wide": (1920, 1080), "tall": (1080, 1920)}
BANNED_WORDS = ["delve", "crucial", "robust", "pivotal", "tapestry", "testament", "vibrant", "intricate", "interplay",
                "landscape", "showcase", "underscore", "highlight", "garner", "bolster", "meticulously", "additionally",
                "boasts", "nestled", "groundbreaking", "renowned", "seamless", "effortless", "revolutionize",
                "unleash", "elevate", "game-changer", "supercharge", "magic", "powerful", "blazing"]
BANNED_RE = [r"\bserves as\b", r"\bstands as\b", r"\bnot just\b.*\bbut\b", r"\bit'?s not\b.*\bit'?s\b",
             r"\bno \w+, no \w+, just\b", r"!", r"\u2014", r"[\u2018\u2019\u201c\u201d\u2026]"]
# Personal data: user names, home folders, mail, private projects. (Absolute paths the tool prints are allowed: they
# name only the throwaway tour copy under the run folder, and they sit out of focus.)
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


PRIVATE = re.compile("(?i)(" + "|".join(_private_terms()) + ")")


def fail(results, name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print("%-30s %s  %s" % (name, "PASS" if ok else "FAIL", str(detail)[:220]))


def texts():
    out = []
    for ty in SB["type"].values():
        for k in ("head", "head_tall", "sub", "sub_tall", "url"):
            if ty.get(k):
                out.append(ty[k])
    return out


def storyboard(results):
    shots = SB["shots"]
    beat = 60.0 / SB["bpm"]
    missing = [s["id"] for s in shots if not (s.get("contract") and s.get("focal") and s.get("wide") and s.get("tall"))]
    fail(results, "storyboard fields", not missing, missing or "%d shots" % len(shots))
    cuts = [s["t"] for s in shots] + list(SB["music"].values())
    off = verify.on_beat(cuts, beat, SB["fps"])
    fail(results, "cuts and cues on beat", not off, off or "%d cuts and cues on the %.2f s grid" % (len(cuts), beat))
    lens = sorted({round(s["end"] - s["t"], 3) for s in shots})
    fail(results, "shot lengths vary", len(lens) >= 3, "lengths %s" % lens)
    holds, bad = [], []
    for k, ty in SB["type"].items():
        chars = len(ty["head"]) + len(ty.get("sub") or "") + len(ty.get("url") or "")
        need, have = chars / 20.0, ty["end"] - ty["t"]
        holds.append("%s %.1f/%.1fs" % (k, need, have))
        if need > have:
            bad.append(k)
    fail(results, "reading holds", not bad, (bad and "short: %s" % bad) or ", ".join(holds))
    long_lines = [l for t in texts() for l in t.split("\n") if len(l) > 42]
    fail(results, "caption lines <= 42 chars", not long_lines, long_lines or "longest %d" %
         max(len(l) for t in texts() for l in t.split("\n")))


def provenance(results):
    """Every card is a window onto real output: (a) the display wrap of each captured output re-joins to exactly
    what was printed (a soft break drops one space, or nothing after a slash or at the column); (b) each card's rows
    are consecutive rows of that wrap, character for character."""
    problems = []
    for fmt in SIZE:
        for cid, c in SB["cards"][fmt].items():
            src = c["src"]
            if "file" in src:
                f = SRC_FILES[src["file"]]
                lines = f["lines"] if isinstance(f, dict) else f
                prev = None
                for r in c["rows"]:
                    _, n, i = r["src"]
                    line = lines[n - 1].expandtabs(8)
                    parts = wrap(line, src["cols"]) if src["wrap"] else [line]
                    if not joins_to(parts, line) or parts[i] != r["text"]:
                        problems.append("%s/%s line %d" % (fmt, cid, n))
                    if prev and (n, i) not in ((prev[0], prev[1] + 1), (prev[0] + 1, 0)):
                        problems.append("%s/%s rows not consecutive at line %d" % (fmt, cid, n))
                    prev = (n, i)
                continue
            order = []
            for r in c["rows"]:
                sid, kind, i = r["src"]
                full = STEP[sid][kind].expandtabs(8)
                parts = wrap(full, src["cols"] - 2 if kind == "cmd" else src["cols"])
                if r["text"] != parts[i]:
                    problems.append("%s/%s %s %s row %d" % (fmt, cid, sid, kind, i))
                order.append((src["steps"].index(sid), 0 if kind == "cmd" else 1, i))
                # (a) the whole wrap of this output re-joins to the printed text, line by line
                rows = list(parts)
                for ln in full.split("\n"):
                    take = []
                    while rows and not joins_to(take, ln):
                        take.append(rows.pop(0))
                    if not joins_to(take, ln):
                        problems.append("%s/%s %s %s does not re-join: %r" % (fmt, cid, sid, kind, ln[:40]))
                        break
            seq = sorted(order)
            if order != seq or any(b[2] != a[2] + 1 for a, b in zip(seq, seq[1:]) if a[:2] == b[:2]):
                problems.append("%s/%s rows not consecutive" % (fmt, cid))
    fail(results, "cards = captured output", not problems, sorted(set(problems))[:6] or
         "every card row is a consecutive row of the captured output")
    leaks = []
    for fmt in SIZE:
        page = (BUILD / ("hf-" + fmt) / "index.html").read_text(encoding="utf-8")
        body = re.sub(r"https://cdn\.jsdelivr\.net/\S+", "", page)
        leaks += ["%s: %s" % (fmt, m.group(0)) for m in PRIVATE.finditer(body)]
    fail(results, "no personal data in frames", not leaks, leaks[:5] or "no user names, home folders or private projects")


def joins_to(parts, line):
    if not parts:
        return line == ""
    s = parts[0]
    for p in parts[1:]:
        if line.startswith(s + " " + p):
            s = s + " " + p
        else:
            s = s + p
    return s == line


def copy_lint(results):
    ts = texts()
    hits = verify.copy_lint(ts)
    for t in ts:
        low = t.lower()
        hits += ["%r: %s" % (t, w) for w in BANNED_WORDS if re.search(r"\b%s\b" % re.escape(w), low)]
        hits += ["%r: /%s/" % (t, r) for r in BANNED_RE if re.search(r, t, re.I)]
    heads = [ty["head"] for k, ty in SB["type"].items() if k != "end"]
    hits += ["%r: %d words" % (h, len(h.split())) for h in heads if len(h.split()) > 5]
    hits += ["%r: not a sentence with a period" % h for h in heads if not (h[0].isupper() and h.endswith("."))]
    fail(results, "copy lint", not hits, hits or "%d strings clean" % len(ts))


def composition(results):
    env = media.env_with_ffmpeg()
    env.update(HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")
    npx = ["npx.cmd" if os.name == "nt" else "npx", "--prefix", str(Path(__file__).resolve().parents[2]), "hyperframes"]
    for fmt in SIZE:
        d = BUILD / ("hf-" + fmt)
        p = subprocess.run(npx + ["lint"], cwd=d, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        m = re.search(r"(\d+) errors?, (\d+) warnings?", p.stdout + p.stderr)
        ok = p.returncode == 0 and m and m.group(1) == "0" and m.group(2) == "0"
        fail(results, "hyperframes lint " + fmt, ok, m.group(0) if m else (p.stdout + p.stderr)[-300:])
        p = subprocess.run(npx + ["check", "--strict", "--json"], cwd=d, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        (REV / ("check-%s.json" % fmt)).write_text(p.stdout, encoding="utf-8")
        try:
            j = json.loads(p.stdout[p.stdout.index("{"):])
            ok = bool(j.get("ok"))
            errs = []

            def walk(o):
                if isinstance(o, dict):
                    if o.get("severity") in ("error", "warning"):
                        errs.append("%s %s %s @%s" % (o.get("severity"), o.get("code"), o.get("selector"), o.get("time")))
                        return
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(j)
            detail = "ok" if ok else (errs[:6] or json.dumps({k: j.get(k) for k in ("lint", "runtime", "layout")})[:500])
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
            fail(results, "file " + fmt, False, "missing %s" % f.name)
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
        ss = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
        se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
        sil = list(zip(ss, se + [D] * (len(ss) - len(se))))
        bad = [s for s in sil if not (s[0] < 0.3) and not (s[0] > D - 1.5)]
        fail(results, "silencedetect " + fmt, not bad, "silences %s, undeclared %s" % (sil, bad))
        log = ffilter(f, af="ebur128=peak=true")
        tail = log[log.rfind("Summary:"):]
        I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
        tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))
        fail(results, "ebur128 " + fmt, -17.0 <= I <= -15.0 and tp <= -1.0, "I=%.1f LUFS, true peak %.1f dBTP" % (I, tp))
    if GIF.exists():
        w = Image.open(GIF).size[0]
        fail(results, "gif size", GIF.stat().st_size < 8 * 1048576 and w == 960,
             "%.2f MB, %d px wide" % (GIF.stat().st_size / 1048576, w))
    else:
        fail(results, "gif size", False, "missing")


def strip(fmt):
    """Frames at every beat (0.5 s), labelled with time, tiled like the Talkover reference strips."""
    f = FILES[fmt]
    beat = 60.0 / SB["bpm"]
    times = [round(i * beat + beat / 2 - 0.05, 3) for i in range(int(SB["duration"] / beat))]
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
        d.text((x + 2, y + 3), "%.1fs" % (t + 0.05), fill=(200, 200, 205), font=font)
        sheet.paste(im, (x, y + lab))
    out = REV / ("strip-%s.png" % fmt)
    sheet.save(out)
    return out, times


def blank_frames(results, times):
    for fmt in FILES:
        frames = sorted((BUILD / ("strip-" + fmt)).glob("t*.png"))
        keep = [f for f, t in zip(frames, times[fmt]) if 0.4 < t < SB["duration"] - 0.7]
        bad = verify.blank_frames(keep)
        fail(results, "frames not blank " + fmt, not bad, [Path(b).name for b in bad] or
             "%d beat frames have content" % len(keep))


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%H%M")
    REV.mkdir(parents=True, exist_ok=True)
    PREV.mkdir(parents=True, exist_ok=True)
    results = []
    storyboard(results)
    provenance(results)
    copy_lint(results)
    composition(results)
    technical(results)
    strips, times = [], {}
    for fmt in FILES:
        if FILES[fmt].exists():
            p, times[fmt] = strip(fmt)
            strips.append(str(p))
    if times:
        blank_frames(results, times)
    rec = {"round": label, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "pass": all(r["pass"] for r in results),
           "results": results, "strips": [Path(s).name for s in strips]}
    with open(PREV / "checks.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
    n = sum(r["pass"] for r in results)
    print("%d/%d PASS" % (n, len(results)) + ("" if rec["pass"] else "  FAILURES: %d" % (len(results) - n)))


if __name__ == "__main__":
    main()
