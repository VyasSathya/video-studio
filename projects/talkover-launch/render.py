"""Talkover launch film, end to end, no human step:

    python render.py [--skip-panel] [--only wide|tall]

storyboard.py -> panel_render.py (Talkover's real panel, offscreen, its own code) -> panel.webm (VP9 alpha)
-> music.py (local synthesis) -> loudness -> build.py (HyperFrames) -> hyperframes render -> mux -> out/:
  talkover-launch-16x9.mp4, talkover-launch-9x16.mp4, talkover-launch.gif (< 8 MB), frame strips.
"""
import argparse
import os
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import hf, media  # noqa: E402

BUILD, OUT = HERE / "build", HERE / "out"
TALKOVER = Path(os.environ.get("TALKOVER_REPO") or Path(__file__).resolve().parents[3] / "talkover")
TPY = str(TALKOVER / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))


def step(name, args):
    print("==>", name, flush=True)
    subprocess.run([str(a) for a in args], check=True)


def loudnorm(src, dst, I=-16.0, TP=-1.5, LRA=11.0):
    """Two-pass EBU R128 normalisation with ffmpeg's loudnorm."""
    ff = media.ffmpeg_bin()
    p = subprocess.run([ff, "-hide_banner", "-i", str(src), "-af",
                        "loudnorm=I=%g:TP=%g:LRA=%g:print_format=json" % (I, TP, LRA), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]+\}", p.stderr)[-1])
    af = ("loudnorm=I=%g:TP=%g:LRA=%g:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
          "offset=%s:linear=true" % (I, TP, LRA, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"],
                                     m["target_offset"]))
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", "48000",
                    str(dst)], check=True)


def gif(src, out, length, width=960, cap_mb=8.0):
    """README GIF of the feature section at 960 px: grain removed first (it is what makes GIF frames expensive),
    ordered dither; frame rate steps down until it fits under the cap."""
    for fps in (15, 12, 10):
        vf = ("fps=%d,scale=%d:-2:flags=lanczos,hqdn3d=4:3:6:6,split[a][b];[a]palettegen=max_colors=160:stats_mode=diff[p];"
              "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" % (fps, width))
        media.run(["-t", "%.3f" % length, "-i", src, "-vf", vf, out])
        if out.stat().st_size <= cap_mb * 1048576:
            return out
    raise SystemExit("GIF over %s MB even at 10 fps" % cap_mb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-panel", action="store_true")
    ap.add_argument("--only", choices=["wide", "tall"])
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    py = sys.executable
    step("storyboard", [py, HERE / "storyboard.py"])
    sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
    if not a.skip_panel:
        step("Talkover panel, offscreen (its own voice_panel.py)", [TPY, HERE / "panel_render.py", "--scale", 10, "--talkover", TALKOVER])
        n = int(round(sb["duration"] * sb["fps"]))
        media.run(["-framerate", sb["fps"], "-start_number", sb["fps"], "-i", BUILD / "panel" / "f%05d.png",
                   "-frames:v", n, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", 16, "-b:v", 0,
                   "-row-mt", 1, "-deadline", "good", "-cpu-used", 2, BUILD / "panel.webm"])
        for f in (BUILD / "panel").glob("f*.png"):   # D: is tight; panel.webm is the asset
            f.unlink()
    step("score (local synthesis)", [py, HERE / "music.py"])
    loudnorm(HERE / "music" / "score.wav", HERE / "music" / "score-norm.wav")
    step("compositions", [py, HERE / "build.py"])
    names = {"wide": "talkover-launch-16x9.mp4", "tall": "talkover-launch-9x16.mp4"}
    for fmt in ([a.only] if a.only else ["wide", "tall"]):
        print("==> hyperframes render", fmt, flush=True)
        silent = BUILD / ("scene-%s.mp4" % fmt)
        hf.render(BUILD / ("hf-" + fmt), silent, fps=sb["fps"], quality="high")
        final = OUT / names[fmt]
        media.run(["-i", silent, "-i", HERE / "music" / "score-norm.wav", "-map", "0:v", "-map", "1:a",
                   "-c:v", "libx264", "-preset", "slow", "-crf", 16, "-pix_fmt", "yuv420p", "-profile:v", "high",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", "%.3f" % sb["duration"], final])
        print("%s  %.2f MB" % (final, final.stat().st_size / 1048576))
    if not a.only or a.only == "wide":
        gif(OUT / names["wide"], OUT / "talkover-launch.gif", length=sb["type"]["end"]["t"])
        print("gif  %.2f MB" % ((OUT / "talkover-launch.gif").stat().st_size / 1048576))


if __name__ == "__main__":
    main()
