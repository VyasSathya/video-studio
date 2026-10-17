"""session-hub README GIF, no human step:

    python projects/session-hub-tour/render.py [--repo C:\\Dev\\session-hub]

Starts `python -m sessionhub serve --demo` (example data only, from a temp copy) on a free port, walks through it with
studio/webrec.mjs (open a session, one of its agents, a task, then the Now page and answer a question), and writes
out/session-hub.mp4 and out/session-hub.gif.
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
from studio import media   # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Dev\session-hub")
    a = ap.parse_args()
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "sessionhub", "serve", "--demo", "--port", str(port)], cwd=a.repo,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = "http://127.0.0.1:%d/" % port
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        shot = json.loads((HERE / "shot.json").read_text(encoding="utf-8"))
        shot["url"] = url
        tmp = out / "shot.run.json"
        tmp.write_text(json.dumps(shot), encoding="utf-8")
        mp4 = out / "session-hub.mp4"
        subprocess.run(["node", str(ROOT / "studio" / "webrec.mjs"), str(tmp), str(mp4)], check=True)
        tmp.unlink()
    finally:
        srv.terminate()
    media.gif(mp4, out / "session-hub.gif", width=1000, fps=15, colors=128)
    media.contact_sheet(mp4, out / "contact-sheet.png", every=2.0, cols=4)
    for p in (mp4, out / "session-hub.gif"):
        print("%s  %.2f MB" % (p, p.stat().st_size / 1048576))


if __name__ == "__main__":
    main()
