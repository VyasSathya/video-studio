"""10 s launch film for crewboard from its real --demo screens, 16:9 and 9:16, no human step.

    python projects/crewboard-launch/render.py [--repo C:/Dev/crewboard] [--stills]

Starts `python -m crewboard serve --demo` on a free port, captures the states in capture.json with
studio/capture.mjs (screens and where each feature sits, read from the DOM), fills brief.json from them, and
renders with studio.launch. --stills only writes the composition and frame stills (for the critique loop).
"""
import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from studio import launch, media, review, verify  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def capture(repo, out):
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "crewboard", "serve", "--demo", "--port", str(port)], cwd=repo,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = "http://127.0.0.1:%d/" % port
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        cfg = json.loads((HERE / "capture.json").read_text(encoding="utf-8"))
        cfg["url"] = url
        (out / "capture.json").write_text(json.dumps(cfg), encoding="utf-8")
        subprocess.run(["node", str(ROOT / "studio" / "capture.mjs"), str(out / "capture.json"), str(out / "assets")],
                       check=True, cwd=str(ROOT))
    finally:
        srv.terminate()
    return json.loads((out / "assets" / "shots.json").read_text(encoding="utf-8"))


def fill(brief, caps):
    by = {s["name"]: s for s in caps["shots"]}
    for f in brief["features"]:
        c = by[f.pop("shot")]
        f["asset"] = c["file"]
        f["asset_size"] = [caps["width"], caps["height"]]
        if f.pop("focus_from", None):
            f["focus"] = c["focus"]
        if f.pop("cursor_from", None):
            f["cursor"] = c["cursor"]
    return brief


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Dev\crewboard")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    out = media.work_dir("crewboard-launch")
    caps = capture(a.repo, out)
    brief = fill(json.loads((HERE / "brief.json").read_text(encoding="utf-8")), caps)
    (out / "brief.filled.json").write_text(json.dumps(brief, indent=1), encoding="utf-8")
    for w, h in ((1920, 1080), (1080, 1920)):
        tag = "%dx%d" % (w, h)
        if a.stills:
            shots, total = launch.build(brief, out / ("comp-" + tag), w, h, 60.0 / launch.BPM)
            verify.stills(out / ("comp-" + tag), shots, out / ("stills-" + tag))
            continue
        m = launch.render(brief, out / ("crewboard-launch-%s.mp4" % tag), w, h, work=out)
        (out / ("manifest-%s.json" % tag)).write_text(json.dumps(m, indent=1), encoding="utf-8")
        print(tag, json.dumps(verify.technical(out / ("crewboard-launch-%s.mp4" % tag), m)))


if __name__ == "__main__":
    main()
