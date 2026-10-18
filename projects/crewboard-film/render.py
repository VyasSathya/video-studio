"""crewboard launch film, end to end, no human step:

    python render.py [--skip-ui] [--rects-only] [--only wide|tall] [--stills]

storyboard.py -> `python -m crewboard serve --demo` on a free port (example data, temp copy) -> ui_render.mjs
(crewboard's real page, frame by frame at 2x on the film clock, plus rects.json) -> page.mp4 -> music.py (local
synthesis) -> loudness -> build.py (HyperFrames) -> hyperframes render -> mux -> out/:
  crewboard-launch-16x9.mp4, crewboard-launch-9x16.mp4, crewboard-launch.gif (< 8 MB at 960 px).
All work and output go to C:\\video-studio-work\\runs\\crewboard-film (C: only; D: is full).
--stills writes composition snapshots at every beat (no full render) for a fast look.
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("STUDIO_WORK", r"C:\video-studio-work")
sys.path.insert(0, str(HERE.parents[1]))
from studio import hf, media  # noqa: E402

import storyboard as SBM  # noqa: E402

WORK = SBM.WORK
BUILD, OUT = WORK / "build", WORK / "out"
CREWBOARD = Path(os.environ.get("CREWBOARD_REPO", r"C:\Dev\crewboard"))
NAMES = {"wide": "crewboard-launch-16x9.mp4", "tall": "crewboard-launch-9x16.mp4"}


def step(name, args, **kw):
    print("==>", name, flush=True)
    subprocess.run([str(a) for a in args], check=True, **kw)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def record_ui(rects_only=False):
    """Start crewboard's demo server (read-only use of the repo), record the page, stop the server."""
    port = free_port()
    log = BUILD / "crewboard-serve.log"
    fh = open(log, "w", encoding="utf-8")
    srv = subprocess.Popen([sys.executable, "-u", "-m", "crewboard", "serve", "--demo", "--port", str(port)],
                           cwd=str(CREWBOARD), stdout=fh, stderr=subprocess.STDOUT)
    try:
        url = "http://127.0.0.1:%d/" % port
        for _ in range(80):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        time.sleep(0.3)
        m = re.search(r"task list\s+(.+progress\.json)", log.read_text(encoding="utf-8"))
        if not m:
            raise SystemExit("demo server did not report its task list: %s" % log.read_text(encoding="utf-8"))
        ev = json.loads((BUILD / "ui_events.json").read_text(encoding="utf-8"))
        cfg = {"url": url, "width": ev["page"][0], "height": ev["page"][1], "scale": ev["scale"], "fps": ev["fps"],
               "t_end": ev["t_end"], "events": ev["events"], "repo": str(CREWBOARD), "python": sys.executable,
               "data": m.group(1).strip()}
        (BUILD / "ui_config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        frames = BUILD / "ui"
        frames.mkdir(exist_ok=True)
        for f in frames.glob("f*.png"):
            f.unlink()
        step("crewboard page, frame by frame (ui_render.mjs)",
             ["node", HERE / "ui_render.mjs", BUILD / "ui_config.json", frames] + (["--rects-only"] if rects_only else []))
        (BUILD / "rects.json").write_bytes((frames / "rects.json").read_bytes())
    finally:
        srv.terminate()
        fh.close()
    if rects_only:
        return
    n = int(round(SBM.UI_END * SBM.FPS))
    media.run(["-framerate", SBM.FPS, "-i", frames / "f%05d.png", "-frames:v", n, "-c:v", "libx264",
               "-preset", "slow", "-crf", 10, "-pix_fmt", "yuv420p", "-g", 15, "-movflags", "+faststart",
               BUILD / "page.mp4"])
    for f in frames.glob("f*.png"):
        f.unlink()


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
    """README GIF of the feature section at 960 px: grain removed first, ordered dither; frame rate steps down
    until it fits under the cap."""
    for fps, colors in ((15, 160), (12, 160), (12, 128), (10, 128)):
        vf = ("fps=%d,scale=%d:-2:flags=lanczos,hqdn3d=4:3:6:6,split[a][b];[a]palettegen=max_colors=%d:"
              "stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" % (fps, width, colors))
        media.run(["-t", "%.3f" % length, "-i", src, "-vf", vf, out])
        if out.stat().st_size <= cap_mb * 1048576:
            return out
    raise SystemExit("GIF over %s MB even at 10 fps" % cap_mb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ui", action="store_true")
    ap.add_argument("--rects-only", action="store_true")
    ap.add_argument("--only", choices=["wide", "tall"])
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    for d in (BUILD, OUT, WORK / "review"):
        d.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    step("storyboard", [py, HERE / "storyboard.py"])
    if a.rects_only:
        record_ui(rects_only=True)
        return
    if not a.skip_ui:
        record_ui()
    sb = json.loads((BUILD / "storyboard.json").read_text(encoding="utf-8"))
    step("score (local synthesis)", [py, HERE / "music.py"])
    loudnorm(BUILD / "score.wav", BUILD / "score-norm.wav")
    fmts = [a.only] if a.only else ["wide", "tall"]
    step("compositions", [py, HERE / "build.py"] + fmts)
    if a.stills:
        for fmt in fmts:
            times = [round(i * 0.5 + 0.25, 3) for i in range(int(sb["duration"] / 0.5))]
            hf.snapshot(BUILD / ("hf-" + fmt), times, BUILD / ("snap-" + fmt))
        return
    for fmt in fmts:
        print("==> hyperframes render", fmt, flush=True)
        silent = BUILD / ("scene-%s.mp4" % fmt)
        hf.render(BUILD / ("hf-" + fmt), silent, fps=sb["fps"], quality="high")
        final = OUT / NAMES[fmt]
        media.run(["-i", silent, "-i", BUILD / "score-norm.wav", "-map", "0:v", "-map", "1:a",
                   "-c:v", "libx264", "-preset", "slow", "-crf", 16, "-pix_fmt", "yuv420p", "-profile:v", "high",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", "%.3f" % sb["duration"], final])
        print("%s  %.2f MB" % (final, final.stat().st_size / 1048576))
    if "wide" in fmts:
        gif(OUT / NAMES["wide"], OUT / "crewboard-launch.gif", length=sb["type"]["end"]["t"])
        print("gif  %.2f MB" % ((OUT / "crewboard-launch.gif").stat().st_size / 1048576))


if __name__ == "__main__":
    main()
