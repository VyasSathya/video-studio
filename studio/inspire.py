"""Inspiration to skill, step 1: measure a reference video you like, so a style skill can be written from numbers.

    python -m studio inspire ref.mp4 --out study_dir

Writes study.json and two contact sheets (one frame a second; the frame right after each cut) for an agent to
look at. Measures: shot lengths, music tempo and whether cuts land on beats, palette (k-means over sampled
frames), share of dark frames, how much of each frame changes between samples (motion), and how busy the
frames are (edge density). The skill written from it says what to copy (pacing, palette shape, framing) and
never copies the reference's footage, music or branding. The reference file itself is deleted after measuring
unless keep=True.
"""
import json
import wave
from pathlib import Path

import numpy as np

from . import media, reframe, verify


def tempo(wav, lo=70, hi=180):
    """Rough beats per minute and beat times from onset strength (numpy only)."""
    with wave.open(str(wav)) as w:
        rate = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    hop = rate // 100
    n = len(a) // hop
    env = np.sqrt(np.mean(a[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-9)
    onset = np.maximum(0, np.diff(np.log(env)))
    onset -= onset.mean()
    ac = np.correlate(onset, onset, mode="full")[len(onset) - 1:]
    lags = np.arange(len(ac))
    ok = (lags >= 6000 / hi) & (lags <= 6000 / lo)
    if not ok.any():
        return None, []
    lag = lags[ok][np.argmax(ac[ok])]
    bpm = 6000.0 / lag
    period = lag
    best, phase = -1, 0
    for p in range(int(period)):
        s = onset[p::int(period)].sum()
        if s > best:
            best, phase = s, p
    beats = [round((phase + k * period) / 100.0, 3) for k in range(int((n - phase) / period) + 1)]
    return round(bpm, 1), beats


def palette(frames, k=6):
    from PIL import Image
    px = []
    for f in frames:
        im = Image.open(f).convert("RGB").resize((96, 54))
        px.append(np.asarray(im).reshape(-1, 3))
    x = np.concatenate(px).astype(np.float32)
    rng = np.random.default_rng(0)
    c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(12):
        lab = np.argmin(((x[:, None] - c[None]) ** 2).sum(-1), axis=1)
        c = np.array([x[lab == i].mean(0) if (lab == i).any() else c[i] for i in range(k)])
    share = np.bincount(lab, minlength=k) / len(lab)
    order = np.argsort(-share)
    return [{"hex": "#%02x%02x%02x" % tuple(int(v) for v in c[i]), "share": round(float(share[i]), 3)} for i in order]


def busy_and_motion(frames):
    import cv2
    edges, motion, dark, prev = [], [], 0, None
    for f in frames:
        g = cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (480, 270))
        edges.append(float((cv2.Canny(g, 80, 160) > 0).mean()))
        dark += int(g.mean() < 60)
        if prev is not None:
            motion.append(float((cv2.absdiff(g, prev) > 25).mean()))
        prev = g
    return {"edge_density_median": round(float(np.median(edges)), 4),
            "motion_median": round(float(np.median(motion)), 4) if motion else 0.0,
            "dark_frame_share": round(dark / max(1, len(frames)), 3)}


def study(src, out_dir, keep=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dur = media.duration(src)
    cuts = reframe.shots(src, threshold=0.25, min_len=0.25)
    lengths = [round(b - a, 3) for a, b in zip(cuts, cuts[1:])]
    per_s = media.frames(src, out / "sec", [t + 0.5 for t in range(int(dur))])
    after = media.frames(src, out / "cut", [c + 0.1 for c in cuts[:-1]][:40])
    verify.tile(per_s, out / "sheet-seconds.png", cols=6, width=360, labels=["%d s" % t for t in range(len(per_s))])
    verify.tile(after, out / "sheet-cuts.png", cols=6, width=360, labels=["cut %.2f" % c for c in cuts])
    wav = out / "audio.wav"
    res = {"file": Path(src).name, "seconds": round(dur, 2), "shots": len(lengths),
           "shot_seconds": {"median": round(float(np.median(lengths)), 2) if lengths else None,
                            "min": min(lengths) if lengths else None, "max": max(lengths) if lengths else None},
           "cuts": cuts[1:-1]}
    try:
        media.run(["-i", src, "-vn", "-ac", 1, "-ar", 22050, wav])
        bpm, beats = tempo(wav)
        res["bpm"] = bpm
        if beats:
            beat = 60.0 / bpm
            near = [min(abs(c - b) for b in beats) for c in res["cuts"]]
            res["cuts_on_beat_share"] = round(sum(1 for d in near if d <= 0.08 or abs(d - beat / 2) <= 0.08)
                                              / max(1, len(near)), 2)
        wav.unlink()
    except Exception as e:  # no audio stream
        res["bpm"] = None
        res["audio_error"] = str(e)[:120]
    res["palette"] = palette(per_s)
    res.update(busy_and_motion(per_s))
    (out / "study.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for d in ("sec", "cut"):
        for p in (out / d).glob("*.png"):
            p.unlink()
    if not keep:
        Path(src).unlink(missing_ok=True)
    return res
