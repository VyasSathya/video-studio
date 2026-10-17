"""A music bed made on this machine: soft chord pads, a plucked arpeggio and a light pulse, from numpy.

No samples, no model weights, no licence question: the output is ours. It is a bed, not a song; it sits under
narration (see duck()). For real music, see the paid adapters (studio/paid) or bring a licensed track.

    bed(seconds, out_wav, mood="calm" | "bright" | "focus", seed=1)
"""
import wave

import numpy as np

from . import media

RATE = 48000
MOODS = {
    # key root (Hz), chord degrees as semitones from root, tempo
    "calm": (174.61, [(0, 4, 7, 11), (-3, 0, 4, 7), (-7, -3, 0, 4), (-5, -1, 2, 7)], 84),
    "bright": (196.00, [(0, 4, 7, 12), (7, 11, 14, 19), (9, 12, 16, 21), (5, 9, 12, 17)], 104),
    "focus": (164.81, [(0, 3, 7, 10), (-4, 0, 3, 8), (-7, -4, 0, 5), (-2, 2, 5, 10)], 92),
}


def _note(f, n, kind="pad"):
    t = np.arange(n) / RATE
    if kind == "pad":
        x = sum(np.sin(2 * np.pi * f * k * t + k) / k ** 1.6 for k in range(1, 6))
        x *= 1 + 0.15 * np.sin(2 * np.pi * 0.21 * t)
        a = min(n, int(RATE * 0.9))
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a) ** 2
        env[-a:] *= np.linspace(1, 0, a) ** 2
    else:
        x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
        env = np.exp(-t * 6.0) * (1 - np.exp(-t * 400))
    return x * env


def bed(seconds, out, mood="calm", seed=1):
    root, chords, bpm = MOODS.get(mood, MOODS["calm"])
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    beat = 60.0 / bpm
    bar = beat * 4
    L = np.zeros(n + int(RATE * (3 * bar + 2)))   # room for the last bar's tails
    R = np.zeros_like(L)
    i, t = 0, 0.0
    while t < seconds + bar:
        ch = chords[i % len(chords)]
        s = int(t * RATE)
        m = int(bar * RATE * 1.15)
        for k, semi in enumerate(ch):
            f = root * 2 ** (semi / 12.0)
            x = _note(f / 2, m) * 0.085
            pan = 0.35 + 0.3 * (k / 3.0)
            L[s:s + m] += x * (1 - pan)
            R[s:s + m] += x * pan
        arp = list(ch) + [ch[1] + 12, ch[2] + 12]
        for b in range(8):
            if rng.random() < 0.82:
                semi = arp[(b * 3 + i) % len(arp)]
                f = root * 2 ** (semi / 12.0) * 2
                ss = s + int(b * beat / 2 * RATE)
                mm = int(beat * 1.5 * RATE)
                x = _note(f, mm, "pluck") * 0.05
                pan = 0.25 + 0.5 * rng.random()
                L[ss:ss + mm] += x * (1 - pan)
                R[ss:ss + mm] += x * pan
        for b in range(4):  # soft low pulse on each beat
            ss = s + int(b * beat * RATE)
            mm = int(0.25 * RATE)
            tt = np.arange(mm) / RATE
            x = np.sin(2 * np.pi * (55 + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * 0.09
            L[ss:ss + mm] += x
            R[ss:ss + mm] += x
        i += 1
        t += bar
    # a short feedback delay for space, then fades
    d = int(beat * 0.75 * RATE)
    for ch_ in (L, R):
        ch_[d:] += 0.28 * ch_[:-d]
    L, R = L[:n], R[:n]
    f = int(RATE * 2.0)
    fade = np.ones(n)
    fade[:f] = np.linspace(0, 1, f)
    fade[-f:] = np.linspace(1, 0, f)
    st = np.stack([L * fade, R * fade], axis=1)
    st = st / (np.abs(st).max() or 1) * 0.7
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    return out


def duck(voice, music, out, music_db=-18):
    """Narration over the bed: the bed sits music_db under, and dips further whenever someone speaks."""
    media.run(["-i", voice, "-i", music, "-filter_complex",
               "[0:a]aformat=channel_layouts=stereo,aresample=48000,asplit=2[v][sc];"
               "[1:a]aresample=48000,volume=%gdB[m];"
               "[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
               "[v][md]amix=inputs=2:normalize=0:duration=first[out]" % music_db,
               "-map", "[out]", "-ar", 48000, out])
    return out
