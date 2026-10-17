"""The verification loop, in the order that holds up (see skills/product-launch/SKILL.md):

  1. gates()      deterministic checks before any judgment: hyperframes check --strict, copy lint (banned words,
                  ASCII, caption length), cuts on the beat grid
  2. stills()     frames at every cut and once each title has landed, plus a contact sheet
  3. packet()     a folder holding ONLY the contact sheet, the brief and the rubric, for a blind judge (a separate
                  model call that never sees plans, logs, or earlier verdicts)
  4. technical()  after the full render: ffprobe, blackdetect, freezedetect, silencedetect, ebur128; fail closed
  5. log()        every round's findings and fixes go to critiques.jsonl next to the run (at most 5 rounds;
                  a piece that still fails is dropped, not shipped)
"""
import json
import re
import subprocess
import time
from pathlib import Path

from . import hf, media

BANNED = ("delve crucial robust pivotal tapestry testament vibrant intricate interplay showcase underscore garner "
          "bolster meticulously additionally boasts nestled groundbreaking renowned seamless seamlessly unleash "
          "elevate revolutionize game-changer supercharge effortless effortlessly").split()
BANNED_PHRASES = ("serves as", "stands as", "not just", "valuable insights", "diverse array", "evolving landscape",
                  "align with", "resonate with", "it's not", "no x, no y")


def copy_lint(texts, max_line=42, max_words=None):
    problems = []
    for t in texts:
        low = t.lower()
        if max_words and len(t.split()) > max_words:
            problems.append("%d words, at most %d: %r" % (len(t.split()), max_words, t))
        for w in BANNED:
            if re.search(r"\b%s\b" % re.escape(w), low):
                problems.append("banned word %r in %r" % (w, t))
        for p in BANNED_PHRASES:
            if p in low:
                problems.append("banned phrase %r in %r" % (p, t))
        if any(ord(c) > 127 for c in t):
            problems.append("non-ASCII in %r" % t)
        if any(len(line) > max_line for line in t.split("\n")):
            problems.append("line over %d characters: %r" % (max_line, t))
    return problems


def hf_check(comp_dir):
    """hyperframes check --strict, sampling every transition. Returns (ok, issues)."""
    p = hf.hyperframes(["check", "--strict", "--at-transitions", "--json"], comp_dir, check=False)
    return p.returncode == 0, p.returncode


def hf_check_json(comp_dir):
    env = media.env_with_ffmpeg()
    env.update(HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")
    p = subprocess.run([hf.npx(), "--prefix", str(hf.ROOT), "hyperframes", "check", "--strict", "--at-transitions",
                        "--json"], cwd=str(comp_dir), env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    txt = p.stdout
    try:
        res = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except ValueError:
        res = {"raw": txt[-2000:] + p.stderr[-1000:]}
    return {"ok": p.returncode == 0, "exit": p.returncode, "result": res}


def on_beat(cuts, beat, fps=30):
    """Cuts that miss the beat grid by more than one frame."""
    return [c for c in cuts if abs(c / beat - round(c / beat)) * beat > 1.0 / fps + 1e-6]


def gates(comp_dir, texts, cuts, beat, titles=()):
    res = {"hyperframes_check": hf_check_json(comp_dir),
           "copy": copy_lint(texts) + copy_lint(titles, max_words=5), "off_beat": on_beat(cuts, beat)}
    res["ok"] = res["hyperframes_check"]["ok"] and not res["copy"] and not res["off_beat"]
    return res


def still_times(shots):
    ts = []
    for s in shots:
        if s["kind"] == "establish":
            ts += [round(s["start"] + 0.2, 2), round(s["end"] - 0.1, 2)]
        elif s["kind"] == "feature":
            # the cut itself (before any title starts), the title landed, the last frame before the next cut
            ts += [round(s["start"] + 0.04, 2), round(s["start"] + 1.0, 2), round(s["end"] - 0.08, 2)]
        else:
            ts += [round(s["start"] + 0.2, 2), round(s["end"] - 0.15, 2)]
    return ts


def stills(comp_dir, shots, out_dir, cols=4, times=None):
    """Frames at every cut, once each title has landed and before the next cut (or at `times`); tiled into
    sheet.png."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        for p in out_dir.glob("*.png"):
            p.unlink()
    ts = times or still_times(shots)
    hf.snapshot(comp_dir, ts, out_dir)
    frames = sorted(out_dir.glob("frame-*.png"))
    return tile(frames, out_dir / "sheet.png", cols, labels=["%.2f s" % t for t in ts] + ["end"] * 10)


def tile(frames, out, cols=4, width=640, labels=None):
    from PIL import Image, ImageDraw
    ims = [Image.open(f).convert("RGB") for f in frames]
    if not ims:
        return None
    w = width
    h = int(ims[0].height * w / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 8) + 8, rows * (h + 30) + 8), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = 8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 30)
        sheet.paste(im.resize((w, h)), (x, y + 22))
        if labels and i < len(labels):
            d.text((x, y + 4), "%d  %s" % (i + 1, labels[i]), fill=(200, 200, 210))
    sheet.save(out)
    return Path(out)


def blank_frames(frames, min_std=6.0, min_edges=0.002):
    """Frames with nothing on them (a composition whose script failed renders bare background, and
    `hyperframes check --strict` can still pass it). Returns the paths that look empty."""
    import numpy as np
    from PIL import Image, ImageFilter
    bad = []
    for f in frames:
        g = Image.open(f).convert("L").resize((480, 270))
        a = np.asarray(g, dtype=np.float32)
        e = np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        if a.std() < min_std or (e > 40).mean() < min_edges:
            bad.append(str(f))
    return bad


def packet_pair(out_dir, sheets_a, sheets_b, brief_text, question):
    """Two packets for a pairwise blind judgment, one per order (A first, then B first); each order goes to its
    own fresh judge. A win counts only if it survives the swap."""
    out = []
    for k, (first, second) in enumerate(((sheets_a, sheets_b), (sheets_b, sheets_a)), 1):
        d = Path(out_dir) / ("order-%d" % k)
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("*"):
            p.unlink()
        for i, s in enumerate(first):
            (d / ("X-%d.png" % (i + 1))).write_bytes(Path(s).read_bytes())
        for i, s in enumerate(second):
            (d / ("Y-%d.png" % (i + 1))).write_bytes(Path(s).read_bytes())
        (d / "brief.txt").write_text(brief_text + "\n\nQuestion: " + question +
                                     "\nAnswer X or Y, then three reasons, each with a frame.", encoding="utf-8")
        out.append(d)
    return out


def packet(out_dir, sheets, brief_text, rubric_path):
    """Everything a blind judge may see, and nothing else."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    for p in d.glob("*"):
        p.unlink()
    for i, s in enumerate(sheets):
        (d / ("frames-%d.png" % (i + 1))).write_bytes(Path(s).read_bytes())
    (d / "brief.txt").write_text(brief_text, encoding="utf-8")
    (d / "rubric.md").write_text(Path(rubric_path).read_text(encoding="utf-8"), encoding="utf-8")
    return d


def technical(mp4, manifest=None, lufs=-14.0):
    """Fail-closed checks on the encoded file."""
    mp4 = Path(mp4)
    probe = subprocess.run([media.ffprobe_bin(), "-v", "error", "-show_entries",
                            "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(mp4)],
                           capture_output=True, text=True)
    res = {"file": mp4.name, "problems": []}
    try:
        pj = json.loads(probe.stdout)
        v = [s for s in pj["streams"] if s["codec_type"] == "video"][0]
        res.update(width=v["width"], height=v["height"], fps=v["r_frame_rate"],
                   seconds=round(float(pj["format"]["duration"]), 2),
                   audio=any(s["codec_type"] == "audio" for s in pj["streams"]))
    except Exception as e:
        res["problems"].append("ffprobe failed: %s" % e)
        res["ok"] = False
        return res
    if not res["audio"]:
        res["problems"].append("no audio stream")

    def scan(vf=None, af=None):
        args = [media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(mp4)]
        args += (["-vf", vf, "-an"] if vf else ["-af", af, "-vn"])
        p = subprocess.run(args + ["-f", "null", "-"], capture_output=True, text=True)
        if p.returncode != 0:
            res["problems"].append("filter failed: %s" % (vf or af))
        return p.stderr

    blk = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", scan(vf="blackdetect=d=0.2:pic_th=0.98:pix_th=0.02"))
    frz = re.findall(r"freeze_start: ([\d.]+)", scan(vf="freezedetect=n=0.002:d=1.2"))
    sil = re.findall(r"silence_start: (-?[\d.]+)", scan(af="silencedetect=noise=-50dB:d=1.0"))
    loud = scan(af="ebur128=peak=true")
    tail = loud[loud.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    res.update(black=blk, freeze=frz, silence=sil, lufs=float(i.group(1)) if i else None,
               true_peak=float(tp.group(1)) if tp else None)
    if blk:
        res["problems"].append("black frames %s" % blk)
    held = manifest.get("holds", []) if manifest else []
    if [f for f in frz if not any(a <= float(f) <= b for a, b in held)]:
        res["problems"].append("frozen frames at %s" % frz)
    if sil:
        res["problems"].append("silence at %s" % sil)
    if res["lufs"] is None or abs(res["lufs"] - lufs) > 1.5:
        res["problems"].append("loudness %s LUFS" % res["lufs"])
    if res["true_peak"] is not None and res["true_peak"] > -0.9:
        res["problems"].append("true peak %.1f" % res["true_peak"])
    res["ok"] = not res["problems"]
    return res


def log(run_dir, round_no, kind, findings, fixes=None):
    """Append one critique round to critiques.jsonl."""
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "round": round_no, "kind": kind, "findings": findings,
           "fixes": fixes or []}
    with open(Path(run_dir) / "critiques.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    return rec
