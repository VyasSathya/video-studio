"""Checks a render must pass before anyone sees it: loudness, true peak, speaking pace, black frames, size.

The targets follow claude-code-video-toolkit's QC (MIT, Digital Samba): -14 LUFS integrated and -1 dBTP true
peak for social and YouTube; 130 to 175 words a minute is comfortable speech. Our own implementation.
"""
import re
import subprocess
from pathlib import Path

from . import media


def loudness(path):
    p = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp else None)


def black_frames(path, min_d=0.3):
    p = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
                        "blackdetect=d=%g:pic_th=0.98:pix_th=0.02" % min_d, "-f", "null", "-"],
                       capture_output=True, text=True)
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", p.stderr)]


def wpm(words):
    if len(words) < 2:
        return 0.0
    span = words[-1]["end"] - words[0]["start"]
    return round(len(words) / span * 60, 1) if span > 0 else 0.0


def check(path, words=None, target=-14.0, max_mb=None):
    path = Path(path)
    lufs, peak = loudness(path)
    res = {"file": path.name, "seconds": round(media.duration(path), 2),
           "mb": round(path.stat().st_size / 1048576, 2), "lufs": lufs, "true_peak": peak,
           "black": black_frames(path)}
    problems = []
    if lufs is None or abs(lufs - target) > 1.5:
        problems.append("loudness %s LUFS, want %g" % (lufs, target))
    if peak is not None and peak > -0.9:
        problems.append("true peak %.1f dBTP, want -1 or lower" % peak)
    if [b for b in res["black"] if b[0] > 0.5 and b[1] < res["seconds"] - 0.5]:
        problems.append("black frames mid-video")
    if words:
        res["wpm"] = wpm(words)
        if not 110 <= res["wpm"] <= 200:
            problems.append("pace %.0f words/min" % res["wpm"])
    if max_mb and res["mb"] > max_mb:
        problems.append("%.1f MB, over %g" % (res["mb"], max_mb))
    res["problems"] = problems
    res["ok"] = not problems
    return res
