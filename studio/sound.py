"""Sound for edits: effects on transitions, a music bed on the beat grid, ducking under speech, licences on file.

    sfx_track([(t, "whoosh-short", -10), (8.0, "pop", -8)], total, out_wav) -> {"file", "licences"}

Effects come from HyperFrames' bundled set (node_modules/hyperframes/.../media-use/audio/assets/sfx): Pixabay
sounds under the Pixabay Content License, free to use in rendered videos without attribution (not to be handed
out as a pack). Music comes from studio.music (made here) or a track whose licence is supplied. Every run records
which sound came from where in its manifest.
"""
from pathlib import Path

from . import media

ROOT = Path(__file__).resolve().parents[1]
SFX_DIR = ROOT / "node_modules" / "hyperframes" / "dist" / "skills" / "media-use" / "audio" / "assets" / "sfx"
SFX_LICENCE = "Pixabay Content License (bundled with HyperFrames media-use; free use in rendered videos)"


def sfx(name):
    p = SFX_DIR / (name + ".mp3")
    if not p.exists():
        raise FileNotFoundError("no bundled sound effect %r (see %s)" % (name, SFX_DIR))
    return p


def sfx_track(events, total, out, rate=48000):
    """events: (time_s, name, gain_db). One stereo wav of `total` seconds."""
    if not events:
        media.run(["-f", "lavfi", "-i", "anullsrc=r=%d:cl=stereo" % rate, "-t", "%.3f" % total, out])
        return {"file": str(out), "licences": []}
    args, parts = [], []
    for i, (t, name, gain) in enumerate(events):
        args += ["-i", sfx(name)]
        parts.append("[%d:a]aresample=%d,aformat=channel_layouts=stereo,volume=%gdB,adelay=%d:all=1[s%d]"
                     % (i, rate, gain, int(round(t * 1000)), i))
    n = len(events)
    graph = ";".join(parts) + ";" + "".join("[s%d]" % i for i in range(n)) + \
        "amix=inputs=%d:normalize=0:duration=longest,apad,atrim=0:%.3f[out]" % (n, total)
    media.run(args + ["-filter_complex", graph, "-map", "[out]", "-ar", rate, out])
    return {"file": str(out), "licences": sorted({"%s.mp3: %s" % (name, SFX_LICENCE) for _, name, _ in events})}


def add(a, b, out):
    """Sum two tracks (for voice plus effects before ducking the music under both)."""
    media.run(["-i", a, "-i", b, "-filter_complex",
               "[0:a]aformat=channel_layouts=stereo,aresample=48000[x];[1:a]aformat=channel_layouts=stereo,"
               "aresample=48000[y];[x][y]amix=inputs=2:normalize=0:duration=first[out]", "-map", "[out]", out])
    return out
