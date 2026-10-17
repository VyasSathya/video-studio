"""Synthesize the film's score locally (numpy only, no samples, no third-party audio). 120 BPM, 23 s, 48 kHz stereo.

Arrangement follows the cut list in build/storyboard.json: pad alone on the wide shot, kick and bass pulse from the
first cut, hats and a plucked arpeggio from the first reply. When the reading is cut off in the film
the music stops too, leaving only the reverb tail; it comes back when Claude answers. The last chord
rings under the end card. Writes music/score.wav (pre-loudness) and music/stems/*.wav.
"""
import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

HERE = Path(__file__).resolve().parent
SR = 48000
sb = json.loads((HERE / "build" / "storyboard.json").read_text(encoding="utf-8"))
DUR = sb["duration"]
BEAT = 60.0 / sb["bpm"]
N = int(DUR * SR)
rng = np.random.default_rng(7)
STOP, BACK = sb["music"]["stop"], sb["music"]["back"]
FIRST = sb["shots"][1]["t"]          # first cut: drums come in
TALK = sb["type"]["talk"]["t"]       # first reply: hats and arpeggio come in


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, d, s, r, sustain_n):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel_start = sustain_n / SR
    e = np.where(t > rel_start, e * np.exp(-(t - rel_start) / max(r, 1e-4)), e)
    return e


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


# Chords (MIDI), one per 2 bars (4 s): Dmaj9, Bm9, Gmaj9, A6/9 ... ; voiced in the middle register.
END = sb["type"]["end"]["t"]
LOCAL = sb["type"]["local"]["t"]
CHORDS = [(0.0, [50, 57, 61, 64, 66]), (4.0, [47, 54, 57, 61, 62]), (8.0, [43, 50, 54, 57, 59]),
          (BACK, [45, 52, 54, 57, 61]), (LOCAL, [47, 54, 57, 61, 62]), (END, [50, 57, 61, 64, 69])]


def chord_at(t):
    c = CHORDS[0][1]
    for s, notes in CHORDS:
        if t >= s:
            c = notes
    return c


def stopped(t):
    return STOP <= t < BACK


# ---- pad: detuned saws, low-passed, slow attack; L/R detune spread
padL, padR = np.zeros(N), np.zeros(N)
for k, (s, notes) in enumerate(CHORDS):
    e_ = CHORDS[k + 1][0] if k + 1 < len(CHORDS) else DUR
    if s <= STOP < e_:          # the pad is cut at the stop and re-enters on the answer
        segs = [(s, STOP), (BACK, e_)] if e_ > BACK else [(s, STOP)]
    else:
        segs = [(s, e_)]
    for a, b in segs:
        n = int((b - a + (2.5 if b >= DUR - 0.01 else 0.6)) * SR)
        sus = int((b - a) * SR)
        env = env_adsr(n, 0.35 if a > 0 else 1.2, 1.0, 0.85, 0.5 if b < DUR - 0.01 else 2.0, sus)
        for m in notes:
            for side, det in ((padL, -6), (padR, 6)):
                x = sum(saw(hz(m) * 2 ** ((det + d2) / 1200), n, rng.random()) for d2 in (-3, 3)) / 2
                place(side, x * env * 0.15, a)
cut = int(DUR * SR)
padL, padR = padL[:cut], padR[:cut]
t_all = np.arange(N) / SR
# filter opens across the film: darker at the start, brightest on the end card
padL = lp(padL, 900) * 0.55 + lp(padL, 2600) * 0.45 * np.clip((t_all - FIRST) / (END - FIRST), 0, 1)
padR = lp(padR, 900) * 0.55 + lp(padR, 2600) * 0.45 * np.clip((t_all - FIRST) / (END - FIRST), 0, 1)

# ---- kick: on every beat from the first cut, half-time feel (beats 1 and 3) until the first reply
kick = np.zeros(N)
kn = int(0.45 * SR)
kt = np.arange(kn) / SR
kx = np.sin(2 * np.pi * (48 * kt + (110 - 48) * 0.035 * (1 - np.exp(-kt / 0.035)))) * np.exp(-kt / 0.16)
kx += 0.25 * np.exp(-kt / 0.004) * rng.standard_normal(kn) * 0.3
t = FIRST
while t < END:
    if not stopped(t) and not (STOP - 0.01 < t < BACK):
        if t >= TALK or abs(((t - FIRST) / BEAT) % 2) < 1e-6:
            place(kick, kx * (1.0 if abs((t / BEAT) % 4) < 1e-6 else 0.8), t)
    t = round(t + BEAT, 6)
place(kick, kx * 1.1, END)

# ---- bass pulse: eighth notes on the chord root, sidechain-style ducking from the kick
bass = np.zeros(N)
bn = int(BEAT / 2 * SR)
bt = np.arange(bn) / SR
t = FIRST
while t < END:
    if not stopped(t):
        f = hz(chord_at(t)[0] - 12)
        x = (np.sin(2 * np.pi * f * bt) + 0.35 * np.sin(2 * np.pi * 2 * f * bt)) * np.minimum(1, bt / 0.01) * np.exp(-bt / 0.12)
        place(bass, x * 0.32, t)
    t = round(t + BEAT / 2, 6)
bass = lp(bass, 600)

# ---- hats: 16ths, quiet, accent on off-beats, from the first reply
hats = np.zeros(N)
hn = int(0.06 * SR)
t = TALK
while t < END:
    if not stopped(t):
        acc = 1.0 if abs(((t / BEAT) % 1) - 0.5) < 1e-6 else 0.45
        place(hats, hp(rng.standard_normal(hn), 7000) * np.exp(-np.arange(hn) / SR / 0.018) * 0.05 * acc, t)
    t = round(t + BEAT / 4, 6)

# ---- arpeggio pluck: chord tones up an octave, 8ths, from the first reply; returns on the answer
arpL, arpR = np.zeros(N), np.zeros(N)
an = int(0.5 * SR)
at = np.arange(an) / SR
t, i = TALK, 0
while t < END:
    if not stopped(t):
        notes = chord_at(t)[1:]
        m = notes[[0, 2, 1, 3, 2, 1, 3, 0][i % 8]] + 12
        f = hz(m)
        x = (np.sin(2 * np.pi * f * at) + 0.3 * np.sin(2 * np.pi * 3 * f * at) * np.exp(-at / 0.03)) * np.exp(-at / 0.14)
        pan = 0.5 + 0.35 * np.sin(i * 0.9)
        place(arpL, x * 0.09 * (1 - pan) * 2, t)
        place(arpR, x * 0.09 * pan * 2, t)
    t, i = round(t + BEAT / 2, 6), i + 1

# ---- end hit: low boom + bright bell partials on the end card downbeat
hitL, hitR = np.zeros(N), np.zeros(N)
hn2 = int(4.0 * SR)
ht = np.arange(hn2) / SR
bell = sum(a * np.sin(2 * np.pi * hz(m) * ht) for a, m in ((0.5, 74), (0.35, 81), (0.25, 86))) * np.exp(-ht / 1.4) * 0.12
place(hitL, bell, END)
place(hitR, bell, END)

# ---- reverb: exponentially decaying noise IR, 2.2 s, on pad, arp and hit
irn = int(2.2 * SR)
irt = np.arange(irn) / SR
irL = rng.standard_normal(irn) * np.exp(-irt / 0.55)
irR = rng.standard_normal(irn) * np.exp(-irt / 0.55)
irL, irR = lp(irL, 5000) / np.sqrt((irL ** 2).sum()), lp(irR, 5000) / np.sqrt((irR ** 2).sum())
sendL = padL * 0.5 + arpL + hitL
sendR = padR * 0.5 + arpR + hitR
revL = fftconvolve(sendL, irL)[:N] * 0.9
revR = fftconvolve(sendR, irR)[:N] * 0.9

# ---- duck everything but the kick under the kick (gentle pump)
duck = np.ones(N)
dn = int(0.22 * SR)
dshape = 1 - 0.35 * np.exp(-np.arange(dn) / SR / 0.06)
for k in np.nonzero(np.abs(np.diff(np.concatenate([[0], (kick != 0).astype(int)]))) > 0)[0][::2]:
    m = min(dn, N - k)
    duck[k:k + m] = np.minimum(duck[k:k + m], dshape[:m])
mono = bass + hats
L = (padL + arpL + hitL + revL + mono) * duck + kick * 0.42
R = (padR + arpR + hitR + revR + mono) * duck + kick * 0.42
# fade the very end
fade = np.clip((DUR - t_all) / 1.2, 0, 1) ** 1.5
L, R = L * fade, R * fade
mix = np.stack([L, R], axis=1)
mix /= np.max(np.abs(mix)) / 0.89

out = HERE / "music"
(out / "stems").mkdir(parents=True, exist_ok=True)


def write(p, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


write(out / "score.wav", mix)
print("score: %.1f s -> %s" % (DUR, out / "score.wav"))
