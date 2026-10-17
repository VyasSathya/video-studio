"""One picture of an edit: the source waveform, every cut shaded with its reason, and a filmstrip of the source.

Looking at this before the render is how an agent (or a person) checks that no cut lands mid-word and nothing
worth keeping went. The filmstrip-over-waveform view is an idea from video-use (MIT, Browser Use); this is our
own implementation with PIL and numpy.
"""
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import media

COLORS = {"dead air": (120, 120, 132), "lead-in silence": (120, 120, 132), "tail silence": (120, 120, 132),
          "filler": (230, 160, 40), "stutter": (220, 80, 80), "restart": (200, 70, 160), "retake": (150, 90, 220)}


def _font(size):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/SFNS.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def render(src, wav, cut, out, width=2400, row=150, strip_h=110):
    with wave.open(str(wav)) as w:
        rate = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    dur = len(a) / rate
    per = max(1, len(a) // width)
    env = np.abs(a[:per * width]).reshape(width, per).max(axis=1)
    env = env / (env.max() or 1)
    H = strip_h + row + 70
    img = Image.new("RGB", (width, H), (18, 18, 21))
    d = ImageDraw.Draw(img)
    # filmstrip: one frame per strip cell, read straight from the source
    n = width // int(strip_h * 16 / 9)
    cw = width // n
    tmp = Path(out).with_suffix(".strip.png")
    media.run(["-i", src, "-vf", "fps=%f,scale=%d:%d,tile=%dx1" % (n / dur, cw, strip_h, n), "-frames:v", 1, tmp])
    img.paste(Image.open(tmp), (0, 0))
    tmp.unlink()
    top = strip_h + 10
    mid = top + row // 2
    for r in cut["removed"]:
        x0, x1 = int(r["start"] / dur * width), max(int(r["end"] / dur * width), int(r["start"] / dur * width) + 1)
        d.rectangle([x0, top, x1, top + row], fill=tuple(int(c * 0.45) for c in COLORS.get(r["why"], (90, 90, 90))))
    for x, v in enumerate(env):
        h = int(v * row * 0.46)
        d.line([x, mid - h, x, mid + h], fill=(210, 210, 220))
    f = _font(20)
    for t in range(0, int(dur) + 1, 10):
        x = int(t / dur * width)
        d.line([x, top + row, x, top + row + 8], fill=(120, 120, 130))
        d.text((x + 3, top + row + 8), "%d:%02d" % (t // 60, t % 60), font=f, fill=(150, 150, 160))
    # flubs are named where they sit; silences are just the grey bands
    last_x = -1000
    for r in cut["removed"]:
        if r["why"] in ("dead air", "lead-in silence", "tail silence"):
            continue
        x = int(r["start"] / dur * width)
        y = top + 4 if x - last_x > 260 else top + 30
        d.text((x + 3, y), "%s: %s" % (r["why"], r["text"][:28]), font=f, fill=COLORS.get(r["why"], (220, 220, 220)))
        last_x = x
    img.save(out)
    return Path(out)
