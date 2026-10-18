"""Synthesize the agent-brain film's score locally (numpy + scipy only: oscillators, noise, filters; no samples, loops
or third-party audio). 120 BPM, 48 kHz stereo, as long as the film. Writes WORK/music/score.wav (pre-loudness).

Arrangement follows the cues in BUILD/storyboard.json ("music"):
- open: until the session remembers, the pad is muffled (low-passed hard, like the out-of-focus card); it opens on the
  cut to "It remembers." and the kick and bass pulse come in
- full: hats and a plucked arpeggio from "Every note cites the line."
- refuse: the refusal lands on a low thud; drums, bass and arpeggio drop out for one beat-pair while the pad holds,
  then come back
- true: a two-note bell when evidence_changed turns true
- end: the last chord, a low hit and a bell ring under the end card, then fade
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storyboard import BUILD, WORK  # noqa: E402

SR = 48000
sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
DUR = sb["duration"]
BEAT = 60.0 / sb["bpm"]
N = int(DUR * SR)
rng = np.random.default_rng(11)
MU = sb["music"]
OPEN, FULL, REF, BACK, TRUE, END = MU["open"], MU["full"], MU["refuse"], MU["back"], MU["true"], MU["end"]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, d, s, r, sustain_n):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = sustain_n / SR
    return np.where(t > rel, e * np.exp(-(t - rel) / max(r, 1e-4)), e)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def place(buf, x, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]


# Chords (MIDI), changing on cuts: Cmaj9, Am9, Fmaj9 on the refusal, G6/9 when evidence_changed turns true, Am9, and
# Cmaj9 with a high ninth on the end card.
CHORDS = [(0.0, [48, 55, 59, 62, 64]), (4.0, [45, 52, 55, 59, 60]), (REF, [41, 48, 52, 55, 57]),
          (TRUE, [43, 50, 52, 55, 57]), (13.0, [45, 52, 55, 59, 60]), (END, [48, 55, 59, 62, 64, 74])]


def chord_at(t):
    c = CHORDS[0][1]
    for s, notes in CHORDS:
        if t >= s - 1e-6:
            c = notes
    return c


def dropped(t):
    return REF + 1e-6 < t < BACK - 1e-6


t_all = np.arange(N) / SR

# ---- pad: detuned saws, slow attack, L/R detune spread
padL, padR = np.zeros(N), np.zeros(N)
for k, (s, notes) in enumerate(CHORDS):
    e_ = CHORDS[k + 1][0] if k + 1 < len(CHORDS) else DUR
    n = int((e_ - s + (2.5 if e_ >= DUR - 0.01 else 0.5)) * SR)
    env = env_adsr(n, 1.2 if s == 0 else 0.25, 1.0, 0.85, 0.45 if e_ < DUR - 0.01 else 2.0, int((e_ - s) * SR))
    for m in notes:
        for side, det in ((padL, -7), (padR, 7)):
            x = sum(saw(hz(m) * 2 ** ((det + d2) / 1200), n, rng.random()) for d2 in (-3, 3)) / 2
            place(side, x * env * 0.14, s)
padL, padR = padL[:N], padR[:N]
# muffled until it remembers (450 Hz), then open, brightest on the end card
bright = np.clip((t_all - OPEN) / 0.35, 0, 1) * (0.55 + 0.45 * np.clip((t_all - OPEN) / (END - OPEN), 0, 1))
padL = lp(padL, 450) * (1 - bright) + (lp(padL, 1000) * 0.6 + lp(padL, 2800) * 0.4) * bright
padR = lp(padR, 450) * (1 - bright) + (lp(padR, 1000) * 0.6 + lp(padR, 2800) * 0.4) * bright

# ---- kick: every beat from the open, beats 1 and 3 only until full
kick = np.zeros(N)
kn = int(0.45 * SR)
kt = np.arange(kn) / SR
kx = np.sin(2 * np.pi * (46 * kt + (115 - 46) * 0.035 * (1 - np.exp(-kt / 0.035)))) * np.exp(-kt / 0.16)
kx += 0.25 * np.exp(-kt / 0.004) * rng.standard_normal(kn) * 0.3
t = OPEN
while t < END - 1e-6:
    if not dropped(t) and abs(t - REF) > 1e-6:
        if t >= FULL - 1e-6 or abs(((t - OPEN) / BEAT) % 2) < 1e-6:
            place(kick, kx * (1.0 if abs((t / BEAT) % 4) < 1e-6 else 0.8), t)
    t = round(t + BEAT, 6)
place(kick, kx * 1.1, END)

# ---- refusal thud: a low, short, filtered hit with a sub drop
thn = int(0.9 * SR)
tht = np.arange(thn) / SR
thud = np.sin(2 * np.pi * (38 * tht + (90 - 38) * 0.05 * (1 - np.exp(-tht / 0.05)))) * np.exp(-tht / 0.28) * 0.9
thud += lp(rng.standard_normal(thn), 400) * np.exp(-tht / 0.05) * 0.5
place(kick, thud, REF)

# ---- bass pulse: eighths on the chord root, from the open
bass = np.zeros(N)
bn = int(BEAT / 2 * SR)
bt = np.arange(bn) / SR
t = OPEN
while t < END - 1e-6:
    if not dropped(t) and abs(t - REF) > 1e-6:
        f = hz(chord_at(t)[0] - 12)
        x = (np.sin(2 * np.pi * f * bt) + 0.35 * np.sin(2 * np.pi * 2 * f * bt)) * np.minimum(1, bt / 0.01) * np.exp(-bt / 0.12)
        place(bass, x * 0.32, t)
    t = round(t + BEAT / 2, 6)
bass = lp(bass, 600)

# ---- hats: quiet 16ths from full, accent on the off-beat
hats = np.zeros(N)
hn = int(0.06 * SR)
t = FULL
while t < END - 1e-6:
    if not dropped(t) and abs(t - REF) > 1e-6:
        acc = 1.0 if abs(((t / BEAT) % 1) - 0.5) < 1e-6 else 0.45
        place(hats, hp(rng.standard_normal(hn), 7000) * np.exp(-np.arange(hn) / SR / 0.018) * 0.05 * acc, t)
    t = round(t + BEAT / 4, 6)

# ---- arpeggio pluck: chord tones an octave up, eighths, from full
arpL, arpR = np.zeros(N), np.zeros(N)
an = int(0.5 * SR)
at = np.arange(an) / SR
t, i = FULL, 0
while t < END - 1e-6:
    if not dropped(t) and abs(t - REF) > 1e-6:
        notes = chord_at(t)[1:5]
        m = notes[[0, 2, 1, 3, 2, 1, 3, 0][i % 8]] + 12
        f = hz(m)
        x = (np.sin(2 * np.pi * f * at) + 0.3 * np.sin(2 * np.pi * 3 * f * at) * np.exp(-at / 0.03)) * np.exp(-at / 0.14)
        pan = 0.5 + 0.35 * np.sin(i * 0.9)
        place(arpL, x * 0.085 * (1 - pan) * 2, t)
        place(arpR, x * 0.085 * pan * 2, t)
    t, i = round(t + BEAT / 2, 6), i + 1

# ---- bells: two notes when evidence_changed turns true; the end chord's bell
hitL, hitR = np.zeros(N), np.zeros(N)


def bell(notes, dur, gain):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * hz(m) * tt) * (1 + 0.15 * np.sin(2 * np.pi * 2.76 * hz(m) * tt))
               for a, m in notes) * np.exp(-tt / (dur / 3)) * gain


b1 = bell([(0.5, 79), (0.3, 86)], 1.8, 0.11)
b2 = bell([(0.45, 83), (0.3, 91)], 1.6, 0.09)
place(hitL, b1, TRUE)
place(hitR, b1 * 0.8, TRUE)
place(hitL, b2 * 0.8, TRUE + BEAT / 2)
place(hitR, b2, TRUE + BEAT / 2)
be = bell([(0.5, 72), (0.35, 79), (0.25, 86)], 4.0, 0.12)
place(hitL, be, END)
place(hitR, be, END)

# ---- reverb: decaying noise IR, 2.2 s, on pad, arp and bells
irn = int(2.2 * SR)
irt = np.arange(irn) / SR
irL = lp(rng.standard_normal(irn) * np.exp(-irt / 0.55), 5000)
irR = lp(rng.standard_normal(irn) * np.exp(-irt / 0.55), 5000)
irL, irR = irL / np.sqrt((irL ** 2).sum()), irR / np.sqrt((irR ** 2).sum())
revL = fftconvolve(padL * 0.5 + arpL + hitL, irL)[:N] * 0.9
revR = fftconvolve(padR * 0.5 + arpR + hitR, irR)[:N] * 0.9

# ---- gentle pump: everything but the kick ducks under it
duck = np.ones(N)
dn = int(0.22 * SR)
dshape = 1 - 0.35 * np.exp(-np.arange(dn) / SR / 0.06)
starts = np.nonzero(np.diff(np.concatenate([[0], (np.abs(kick) > 1e-9).astype(int)])) > 0)[0]
for k in starts:
    m = min(dn, N - k)
    duck[k:k + m] = np.minimum(duck[k:k + m], dshape[:m])
mono = bass + hats
L = (padL + arpL + hitL + revL + mono) * duck + kick * 0.42
R = (padR + arpR + hitR + revR + mono) * duck + kick * 0.42
fade = np.clip((DUR - t_all) / 1.2, 0, 1) ** 1.5
L, R = L * fade, R * fade
mix = np.stack([L, R], axis=1)
mix /= np.max(np.abs(mix)) / 0.89

out = WORK / "music"
out.mkdir(parents=True, exist_ok=True)
with wave.open(str(out / "score.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
print("score: %.1f s -> %s" % (DUR, out / "score.wav"))
