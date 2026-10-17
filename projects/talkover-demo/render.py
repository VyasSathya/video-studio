"""Make the Talkover demo end to end, no human step:

    python projects/talkover-demo/render.py [--talkover C:\\Dev\\talkover] [--skip-panel]

session.json -> timeline.py (Kokoro clips, Whisper word times, mix.wav) -> panel_render.py (Talkover's real panel,
offscreen) -> build.py (HyperFrames composition) -> hyperframes render -> panel laid over + audio -> out/:
  talkover-demo.mp4    the full video (about 60 s, 1080p, with sound)
  talkover-demo.gif    the README loop (the cut-in and the answer, no sound, under 8 MB)
  contact-sheet.png    one frame every 3 s, to look at before shipping
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from studio import hf, media   # noqa: E402

BUILD = HERE / "build"
OUT = HERE / "out"


def step(name, args):
    print("==>", name, flush=True)
    subprocess.run(args, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--talkover", default=r"C:\Dev\talkover")
    ap.add_argument("--skip-panel", action="store_true", help="reuse build/panel (timing unchanged)")
    ap.add_argument("--gif-from", type=float, default=None, help="GIF start (default: just before the cut-in)")
    ap.add_argument("--gif-len", type=float, default=16.0)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    py = sys.executable
    tpy = str(Path(a.talkover) / ".venv" / "Scripts" / "python.exe")
    step("timeline (Kokoro + Whisper)", [py, str(HERE / "timeline.py")])
    if not a.skip_panel:
        step("Talkover panel, offscreen", [tpy, str(HERE / "panel_render.py"), "--talkover", a.talkover])
    step("composition", [py, str(HERE / "build.py")])
    print("==> hyperframes render", flush=True)
    scene = BUILD / "scene.mp4"
    hf.render(BUILD / "hf", scene, quality="high")

    tl = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
    pm = json.loads((BUILD / "panel.json").read_text(encoding="utf-8"))
    ov = json.loads((BUILD / "hf" / "overlay.json").read_text(encoding="utf-8"))
    s0, s1 = ov["scene"]
    final = OUT / "talkover-demo.mp4"
    print("==> panel over the scene, audio", flush=True)
    graph = ("[1:v]setpts=PTS+%.3f/TB,scale=%d:%d:flags=lanczos,format=rgba,"
             "fade=t=in:st=%.3f:d=0.5:alpha=1,fade=t=out:st=%.3f:d=0.5:alpha=1[p];"
             "[0:v][p]overlay=%d:%d:eof_action=pass:format=auto,format=yuv420p[v]" %
             (pm["t0"], ov["w"], ov["h"], s0 - 0.1, s1, ov["x"], ov["y"]))
    media.run(["-i", scene, "-framerate", pm["fps"], "-i", BUILD / "panel" / "f%05d.png", "-i", BUILD / "mix.wav",
               "-filter_complex", graph, "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "slow",
               "-crf", 20, "-tune", "animation", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
               "-t", "%.3f" % tl["duration"], final])
    cut = next((e for e in tl["events"] if e["kind"] == "cut"), None)
    start = a.gif_from if a.gif_from is not None else max(0.0, (cut["you_t"] if cut else s0) - 6.0)
    media.gif(final, OUT / "talkover-demo.gif", start=start, length=a.gif_len, width=960, fps=15)
    media.contact_sheet(final, OUT / "contact-sheet.png", every=3.0)
    for p in (final, OUT / "talkover-demo.gif"):
        print("%s  %.2f MB" % (p, p.stat().st_size / 1048576))


if __name__ == "__main__":
    main()
