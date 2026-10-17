"""video-studio command line.

    python -m studio health                         engines and tools this machine has
    python -m studio tts "text" out.wav [--voice af_heart] [--speed 1.0]
    python -m studio stt in.wav [--json]            transcript (with word times as JSON)
    python -m studio render <hyperframes dir> out.mp4 [--quality high]
    python -m studio gif in.mp4 out.gif [--start 0] [--length 15] [--width 960] [--fps 15] [--max-mb 8]
    python -m studio frames in.mp4 out_dir 1.5 7 12  one PNG per time, to look at
    python -m studio sheet in.mp4 out.png [--every 3]  contact sheet of a whole video
    python -m studio rawcut take.mp4 [--name N --role R --credit C --start s --end s]   raw footage to 16:9 + 9:16
    python -m studio short --topic "..." [--facts facts.txt --seconds 40 --voice am_michael --mood calm]
    python -m studio short --script script.json        a script you wrote (same shape script_from_topic returns)
    python -m studio repurpose talk.mp4 [--clips 3 --credit C]   long video to clips + post drafts
    python -m studio review run_dir [run_dir ...]       rebuild review.html (one dir) or review-all.html
    python -m studio cost [--seconds 30]               what each paid piece would cost for one short
Work files go to STUDIO_WORK (default D:/video-studio-work when D: exists); --out picks the run folder.
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


def run_pipeline(a):
    from pathlib import Path
    from . import paid, rawcut, repurpose, review, shortform
    stamp = __import__("time").strftime("%Y%m%d-%H%M%S")
    if a.cmd == "cost":
        print(json.dumps(paid.estimate_short(a.seconds), indent=1))
        return 0
    if a.cmd == "review":
        if len(a.dirs) == 1:
            print(review.page(a.dirs[0]))
        else:
            print(review.index(a.dirs, Path(a.dirs[0]).parent / "review-all.html"))
        return 0
    out = Path(a.out) if a.out else media.work_dir("%s-%s" % (a.cmd, stamp))
    if a.cmd == "rawcut":
        rawcut.run(a.src, out, name=a.name, role=a.role, credit=a.credit, start=a.start, end=a.end, title=a.title,
                   aspects=tuple(a.aspects.split(",")))
    elif a.cmd == "short":
        if a.script:
            script = json.loads(Path(a.script).read_text(encoding="utf-8"))
        elif a.topic:
            facts = Path(a.facts).read_text(encoding="utf-8") if a.facts else ""
            script = shortform.script_from_topic(a.topic, facts=facts, seconds=a.seconds)
            out.mkdir(parents=True, exist_ok=True)
            (out / "script.json").write_text(json.dumps(script, indent=1), encoding="utf-8")
        else:
            print("short needs --topic or --script")
            return 2
        shortform.run(script, out, voice=a.voice, mood=a.mood)
    elif a.cmd == "repurpose":
        repurpose.run(a.src, out, n=a.clips, credit=a.credit)
    print(review.page(out))
    return 0


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
    p = sub.add_parser("rawcut")
    p.add_argument("src")
    p.add_argument("--out")
    for k in ("name", "role", "credit", "title"):
        p.add_argument("--" + k)
    p.add_argument("--start", type=float)
    p.add_argument("--end", type=float)
    p.add_argument("--aspects", default="16:9,9:16")
    p = sub.add_parser("short")
    p.add_argument("--topic")
    p.add_argument("--facts")
    p.add_argument("--script")
    p.add_argument("--seconds", type=float, default=40)
    p.add_argument("--voice", default="am_michael")
    p.add_argument("--mood", default="calm")
    p.add_argument("--out")
    p = sub.add_parser("repurpose")
    p.add_argument("src")
    p.add_argument("--clips", type=int, default=3)
    p.add_argument("--credit")
    p.add_argument("--out")
    p = sub.add_parser("review")
    p.add_argument("dirs", nargs="+")
    p = sub.add_parser("cost")
    p.add_argument("--seconds", type=float, default=30)
    a = ap.parse_args(argv)
    if a.cmd in ("rawcut", "short", "repurpose", "review", "cost"):
        return run_pipeline(a)
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
