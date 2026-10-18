"""Synthesize the film's score locally (numpy + scipy only: oscillators, noise, filters; no samples, no third-party
audio). 120 BPM, 48 kHz stereo, the film's length. Writes <work>/build/score.wav (before loudness).

Arrangement follows build/storyboard.json: a pad alone on the opening tilt; kick and a bass pulse from the first cut;
hats and a plucked arpeggio from the session shot; a soft wooden tick on each page event inside a shot (the agent's
command, both answers); the drums drop for one beat before the end card and a low hit with a bell lands on it; the
last chord rings under the end card.
"""
import json
import wave

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

import storyboard as SBM

SR = 48000
sb = json.loads((SBM.BUILD / "storyboard.json").read_text(encoding="utf-8"))
DUR = sb["duration"]
BEAT = 60.0 / sb["bpm"]
N = int(DUR * SR)
rng = np.random.default_rng(11)
shots = {s["id"]: s for s in sb["shots"]}
FIRST = shots["s2"]["t"]          # first cut: kick and bass
GROOVE = shots["s4"]["t"]         # session shot: hats and arpeggio
DROP, END = sb["music"]["drop"], sb["music"]["end"]
TICKS = sb["music"]["ticks"]


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


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def place(buf, x, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]


# Chords (MIDI), voiced in the middle register: Fmaj9, Dm9, Bbmaj9, C6/9 ... resolving to Fmaj9 (add 6) on the end.
CHORDS = [(0.0, [53, 60, 64, 67, 69]), (4.0, [50, 57, 60, 64, 65]), (8.0, [46, 53, 57, 60, 62]),
          (12.0, [48, 55, 57, 62, 64]), (END, [53, 60, 64, 67, 74])]


def chord_at(t):
    c = CHORDS[0][1]
    for s, notes in CHORDS:
        if t >= s:
            c = notes
    return c


def drums_on(t):
    return FIRST <= t < END and not (DROP <= t < END)


# ---- pad: detuned saws, low-passed, slow attack, the filter opening across the film
padL, padR = np.zeros(N), np.zeros(N)
for k, (s, notes) in enumerate(CHORDS):
    e_ = CHORDS[k + 1][0] if k + 1 < len(CHORDS) else DUR
    last = e_ >= DUR - 0.01
    n = int((e_ - s + (2.5 if last else 0.6)) * SR)
    env = env_adsr(n, 1.4 if s == 0 else 0.35, 1.0, 0.85, 2.0 if last else 0.5, int((e_ - s) * SR))
    for m in notes:
        for side, det in ((padL, -7), (padR, 7)):
            x = sum(saw(hz(m) * 2 ** ((det + d2) / 1200), n, rng.random()) for d2 in (-3, 3)) / 2
            place(side, x * env * 0.15, s)
padL, padR = padL[:N], padR[:N]
t_all = np.arange(N) / SR
op = np.clip((t_all - FIRST) / (END - FIRST), 0, 1)
padL = lp(padL, 850) * 0.55 + lp(padL, 2600) * 0.45 * op
padR = lp(padR, 850) * 0.55 + lp(padR, 2600) * 0.45 * op

# ---- kick: half-time (beats 1 and 3 of the bar) from the first cut, every beat from the groove
kick = np.zeros(N)
kn = int(0.45 * SR)
kt = np.arange(kn) / SR
kx = np.sin(2 * np.pi * (46 * kt + (105 - 46) * 0.035 * (1 - np.exp(-kt / 0.035)))) * np.exp(-kt / 0.16)
kx += 0.25 * np.exp(-kt / 0.004) * rng.standard_normal(kn) * 0.3
t = FIRST
while t < END:
    if drums_on(t) and (t >= GROOVE or abs(((t - FIRST) / BEAT) % 2) < 1e-6):
        place(kick, kx * (1.0 if abs((t / BEAT) % 4) < 1e-6 else 0.8), t)
    t = round(t + BEAT, 6)

# ---- bass pulse: eighths on the chord root
bass = np.zeros(N)
bn = int(BEAT / 2 * SR)
bt = np.arange(bn) / SR
t = FIRST
while t < END:
    if drums_on(t):
        f = hz(chord_at(t)[0] - 12)
        x = (np.sin(2 * np.pi * f * bt) + 0.35 * np.sin(2 * np.pi * 2 * f * bt)) * np.minimum(1, bt / 0.01) * np.exp(-bt / 0.12)
        place(bass, x * 0.32, t)
    t = round(t + BEAT / 2, 6)
bass = lp(bass, 600)

# ---- hats: sixteenths, accent on the off-beat, from the groove
hats = np.zeros(N)
hn = int(0.06 * SR)
t = GROOVE
while t < END:
    if drums_on(t):
        acc = 1.0 if abs(((t / BEAT) % 1) - 0.5) < 1e-6 else 0.45
        place(hats, hp(rng.standard_normal(hn), 7000) * np.exp(-np.arange(hn) / SR / 0.018) * 0.05 * acc, t)
    t = round(t + BEAT / 4, 6)

# ---- arpeggio pluck: chord tones an octave up, eighths, from the groove
arpL, arpR = np.zeros(N), np.zeros(N)
an = int(0.5 * SR)
at = np.arange(an) / SR
t, i = GROOVE, 0
while t < END:
    if drums_on(t):
        notes = chord_at(t)[1:]
        f = hz(notes[[0, 2, 1, 3, 2, 1, 3, 0][i % 8]] + 12)
        x = (np.sin(2 * np.pi * f * at) + 0.3 * np.sin(2 * np.pi * 3 * f * at) * np.exp(-at / 0.03)) * np.exp(-at / 0.14)
        pan = 0.5 + 0.35 * np.sin(i * 0.9)
        place(arpL, x * 0.085 * (1 - pan) * 2, t)
        place(arpR, x * 0.085 * pan * 2, t)
    t, i = round(t + BEAT / 2, 6), i + 1

# ---- ticks: a short band-passed wooden click on each page event (a click, an agent's write)
tick = np.zeros(N)
tn = int(0.08 * SR)
tt = np.arange(tn) / SR
tx = bp(rng.standard_normal(tn), 1800, 4200) * np.exp(-tt / 0.012) + 0.6 * np.sin(2 * np.pi * 1320 * tt) * np.exp(-tt / 0.02)
for t in TICKS:
    place(tick, tx * 0.16, t)

# ---- end: low boom and bell partials on the end card downbeat
hitL, hitR = np.zeros(N), np.zeros(N)
hn2 = int(4.0 * SR)
ht = np.arange(hn2) / SR
boom = np.sin(2 * np.pi * (41 * ht + 30 * 0.05 * (1 - np.exp(-ht / 0.05)))) * np.exp(-ht / 0.55) * 0.55
bell = sum(a * np.sin(2 * np.pi * hz(m) * ht) for a, m in ((0.5, 77), (0.35, 84), (0.25, 89))) * np.exp(-ht / 1.4) * 0.11
place(hitL, boom + bell, END)
place(hitR, boom + bell, END)

# ---- reverb: decaying noise IR on pad, arp, ticks and the hit
irn = int(2.2 * SR)
irt = np.arange(irn) / SR
irL = rng.standard_normal(irn) * np.exp(-irt / 0.55)
irR = rng.standard_normal(irn) * np.exp(-irt / 0.55)
irL, irR = lp(irL, 5000) / np.sqrt((irL ** 2).sum()), lp(irR, 5000) / np.sqrt((irR ** 2).sum())
revL = fftconvolve(padL * 0.5 + arpL + hitL * 0.5 + tick, irL)[:N] * 0.9
revR = fftconvolve(padR * 0.5 + arpR + hitR * 0.5 + tick, irR)[:N] * 0.9

# ---- gentle pump under the kick
duck = np.ones(N)
dn = int(0.22 * SR)
dshape = 1 - 0.35 * np.exp(-np.arange(dn) / SR / 0.06)
for k in np.nonzero(np.diff(np.concatenate([[0], (kick != 0).astype(int)])) > 0)[0]:
    m = min(dn, N - k)
    duck[k:k + m] = np.minimum(duck[k:k + m], dshape[:m])
mono = bass + hats
L = (padL + arpL + revL + mono) * duck + kick * 0.42 + hitL + tick
R = (padR + arpR + revR + mono) * duck + kick * 0.42 + hitR + tick
fade = np.clip((DUR - t_all) / 1.2, 0, 1) ** 1.5
mix = np.stack([L * fade, R * fade], axis=1)
mix /= np.max(np.abs(mix)) / 0.89

out = SBM.BUILD / "score.wav"
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
print("score: %.1f s -> %s" % (DUR, out))
