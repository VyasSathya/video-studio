"""agent-brain launch film, end to end, no human step:

    python render.py [--capture] [--only wide|tall]

(capture.py: the README tour, run for real in a throwaway copy -> data/) -> storyboard.py -> music.py (local
synthesis) -> loudness -> build.py (HyperFrames) -> hyperframes render -> mux -> WORK/out:
  agent-brain-launch-16x9.mp4, agent-brain-launch-9x16.mp4, agent-brain-launch.gif (960 px, < 8 MB).
WORK is STUDIO_WORK/runs/agent-brain-film (default C:/video-studio-work/runs/agent-brain-film).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(HERE))
from studio import hf, media  # noqa: E402
from storyboard import BUILD, WORK  # noqa: E402

OUT = WORK / "out"
NAMES = {"wide": "agent-brain-launch-16x9.mp4", "tall": "agent-brain-launch-9x16.mp4"}


def step(name, args):
    print("==>", name, flush=True)
    subprocess.run([str(a) for a in args], check=True)


def loudnorm(src, dst, I=-16.0, TP=-1.5, LRA=11.0):
    """Two-pass EBU R128 normalisation with ffmpeg's loudnorm (the Talkover reference sits at -16 LUFS)."""
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
    """README GIF of the feature section at 960 px: grain removed before the palette, ordered dither; the frame
    rate steps down until it fits under the cap."""
    for fps, colors in ((15, 128), (12, 128), (12, 96), (10, 96), (10, 64), (10, 48), (8, 64), (8, 48)):
        vf = ("fps=%d,scale=%d:-2:flags=lanczos,hqdn3d=4:3:6:6,split[a][b];[a]palettegen=max_colors=%d:stats_mode=diff[p];"
              "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" % (fps, width, colors))
        media.run(["-t", "%.3f" % length, "-i", src, "-vf", vf, "-loop", 0, out])
        print("gif try %d fps %d colours: %.2f MB" % (fps, colors, out.stat().st_size / 1048576))
        if out.stat().st_size <= cap_mb * 1048576:
            return out
    raise SystemExit("GIF over %s MB even at 10 fps, 64 colours" % cap_mb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true", help="re-run the tour (new handoff id) before building")
    ap.add_argument("--only", choices=["wide", "tall"])
    ap.add_argument("--gif-only", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    if a.gif_only:
        sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
        g = gif(OUT / NAMES["wide"], OUT / "agent-brain-launch.gif", length=sb["type"]["end"]["t"])
        print("gif  %.2f MB" % (g.stat().st_size / 1048576))
        return
    if a.capture:
        step("tour, run for real in a throwaway copy", [py, HERE / "capture.py"])
    step("storyboard", [py, HERE / "storyboard.py"])
    sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
    step("score (local synthesis)", [py, HERE / "music.py"])
    loudnorm(WORK / "music" / "score.wav", WORK / "music" / "score-norm.wav")
    step("compositions", [py, HERE / "build.py"])
    for fmt in ([a.only] if a.only else ["wide", "tall"]):
        print("==> hyperframes render", fmt, flush=True)
        silent = BUILD / ("scene-%s.mp4" % fmt)
        hf.render(BUILD / ("hf-" + fmt), silent, fps=sb["fps"], quality="high")
        final = OUT / NAMES[fmt]
        media.run(["-i", silent, "-i", WORK / "music" / "score-norm.wav", "-map", "0:v", "-map", "1:a",
                   "-c:v", "libx264", "-preset", "slow", "-crf", 16, "-pix_fmt", "yuv420p", "-profile:v", "high",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", "%.3f" % sb["duration"], final])
        print("%s  %.2f MB" % (final, final.stat().st_size / 1048576))
    if not a.only or a.only == "wide":
        g = gif(OUT / NAMES["wide"], OUT / "agent-brain-launch.gif", length=sb["type"]["end"]["t"])
        print("gif  %.2f MB" % (g.stat().st_size / 1048576))


if __name__ == "__main__":
    main()
