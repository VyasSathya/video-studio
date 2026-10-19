"""A warmer, arranged 100 BPM overview score, derived from the original Talkover score.

No samples, vocals, paid models or downloads. The original Talkover composition's
major-nine harmony is retained; its short film-specific stop is removed. The new
arrangement opens with electric-piano tones, adds a soft bass/drum pocket, strips
back at the middle, then resolves for the existing overview end card.
"""
import argparse
import hashlib
import json
from pathlib import Path
import wave

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 100
BEAT = 60 / BPM


def score(seconds, output):
    n = round(seconds * SR)
    rng = np.random.default_rng(71)
    mix = np.zeros((n, 2), dtype=np.float64)
    wet = np.zeros_like(mix)
    chords = [[50, 57, 61, 64, 66], [47, 54, 57, 61, 62],
              [43, 50, 54, 57, 59], [45, 52, 54, 57, 61]]

    def add(note, start, level, pan=.5, reverb=True):
        start = round(start * SR)
        length = min(len(note), n - start)
        if length <= 0:
            return
        stereo = note[:length, None] * np.array([np.sqrt(1 - pan), np.sqrt(pan)]) * level
        mix[start:start + length] += stereo
        if reverb:
            wet[start:start + length] += stereo

    def hz(midi):
        return 440 * 2 ** ((midi - 69) / 12)

    def keys(midi, duration=3.2):
        t = np.arange(round(duration * SR)) / SR
        f = hz(midi)
        body = np.sin(2 * np.pi * f * t + .7 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 5))
        body += .11 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t * 6)
        return body * (1 - np.exp(-t * 180)) * np.exp(-t / 1.0)

    # Two bars per chord; changes align with the unchanged film's 6-second chapters.
    end = seconds - 3.5
    for index, start in enumerate(np.arange(0, end, 6)):
        chord = chords[index % 4]
        for beat_index in (0, 1.5, 3, 4.5, 7, 8.5):
            at = start + beat_index * BEAT
            if at >= end:
                break
            for voice, midi in enumerate(chord[1:]):
                add(keys(midi), at + voice * .008, .115 if beat_index % 3 == 0 else .075,
                    .22 + voice * .18)
        for offset, midi in [(1.2, chord[2] + 12), (3.6, chord[3] + 12), (4.8, chord[1] + 12)]:
            add(keys(midi, 2.4), start + offset, .033, .3 if index % 2 else .7)
        for offset in np.arange(0, 6, BEAT):
            at = start + offset
            if at < 6 or at >= end or 30 <= at < 36:
                continue
            t = np.arange(round(.45 * SR)) / SR
            bass = np.sin(2 * np.pi * hz(chord[0] - 12) * t)
            add(bass * (1 - np.exp(-t * 120)) * np.exp(-t * 7), at, .16, reverb=False)

    for beat_index, at in enumerate(np.arange(6, end, BEAT)):
        if 30 <= at < 36:
            continue
        t = np.arange(round(.28 * SR)) / SR
        phase = 2 * np.pi * (48 * t + 1.05 * (1 - np.exp(-t * 36)))
        if beat_index % 4 in (0, 2):
            add(np.sin(phase) * np.exp(-t * 17), at, .18, reverb=False)
        if beat_index % 4 in (1, 3):
            noise = rng.standard_normal(len(t))
            snare = sosfilt(butter(2, [600, 6500], fs=SR, btype='bandpass', output='sos'), noise)
            add(snare * np.exp(-t * 40), at, .035, reverb=False)
        t = np.arange(round(.08 * SR)) / SR
        hat = sosfilt(butter(2, 7500, fs=SR, btype='highpass', output='sos'), rng.standard_normal(len(t)))
        add(hat * np.exp(-t * 65), at + BEAT / 2, .012, .65, reverb=False)

    for voice, midi in enumerate([50, 57, 61, 64, 69]):
        add(keys(midi, 4), end + voice * .012, .12, .2 + voice * .15)
    ir_t = np.arange(round(1.4 * SR)) / SR
    for channel in range(2):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .28)
        ir = sosfilt(butter(2, 3800, fs=SR, output='sos'), ir)
        ir /= np.sqrt(np.square(ir).sum())
        mix[:, channel] += fftconvolve(wet[:, channel], ir)[:n] * .17
    fade = np.minimum(np.arange(n) / (SR * .07), 1) * np.clip((seconds - np.arange(n) / SR) / 1.3, 0, 1)
    mix *= fade[:, None]
    mix = np.tanh(mix * 1.2)
    mix *= .84 / np.abs(mix).max()
    with wave.open(str(output), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes((mix * 32767).astype('<i2').tobytes())
    return dict(file=output.name, seconds=seconds, bpm=BPM,
                producer='projects/portfolio-landscape/score-overview.py; local NumPy/SciPy composition',
                source='Original Talkover launch score harmony, projects/talkover-launch/music.py',
                licence='Original locally synthesized composition; no samples or third-party audio',
                sha256=hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=60.906667)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = score(args.seconds, args.out)
    args.out.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
