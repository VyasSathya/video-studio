"""video-studio command line.

    python -m studio health                         engines and tools this machine has
    python -m studio tts "text" out.wav [--voice af_heart] [--speed 1.0]
    python -m studio stt in.wav [--json]            transcript (with word times as JSON)
    python -m studio render <hyperframes dir> out.mp4 [--quality high]
    python -m studio gif in.mp4 out.gif [--start 0] [--length 15] [--width 960] [--fps 15] [--max-mb 8]
    python -m studio frames in.mp4 out_dir 1.5 7 12  one PNG per time, to look at
    python -m studio sheet in.mp4 out.png [--every 3]  contact sheet of a whole video
"""
import argparse
import json
import shutil
import subprocess
import sys

from . import engines, hf, media


def cmd_health():
    out = {"engines": engines.health(), "ffmpeg": media.ffmpeg_bin()}
    try:
        enc = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        out["libx264"] = "libx264" in enc
    except OSError:
        out["libx264"] = False
    out["node"] = shutil.which("node")
    print(json.dumps(out, indent=1))
    return 0 if out["libx264"] and out["node"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    p = sub.add_parser("tts")
    p.add_argument("text")
    p.add_argument("out")
    p.add_argument("--voice", default="af_heart")
    p.add_argument("--speed", type=float, default=1.0)
    p = sub.add_parser("stt")
    p.add_argument("wav")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("render")
    p.add_argument("dir")
    p.add_argument("out")
    p.add_argument("--quality", default="high")
    p = sub.add_parser("gif")
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--length", type=float)
    p.add_argument("--width", type=int, default=960)
    p.add_argument("--fps", type=int, default=15)
    p.add_argument("--max-mb", type=float, default=8.0)
    p = sub.add_parser("frames")
    p.add_argument("src")
    p.add_argument("out_dir")
    p.add_argument("times", nargs="+", type=float)
    p = sub.add_parser("sheet")
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--every", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.cmd == "health":
        return cmd_health()
    if a.cmd == "tts":
        print("%.2f s -> %s" % (engines.tts(a.text, a.out, a.voice, a.speed), a.out))
    elif a.cmd == "stt":
        r = engines.stt(a.wav)
        print(json.dumps(r, indent=1) if a.json else r["text"])
    elif a.cmd == "render":
        hf.render(a.dir, a.out, quality=a.quality)
    elif a.cmd == "gif":
        p = media.gif(a.src, a.out, a.start, a.length, a.width, a.fps, max_mb=a.max_mb)
        print("%s %.2f MB" % (p, p.stat().st_size / 1048576))
    elif a.cmd == "frames":
        for p in media.frames(a.src, a.out_dir, a.times):
            print(p)
    elif a.cmd == "sheet":
        print(media.contact_sheet(a.src, a.out, a.every))
    return 0


if __name__ == "__main__":
    sys.exit(main())
