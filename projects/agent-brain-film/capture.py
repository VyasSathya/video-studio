"""Run the agent-brain README tour for real, in a fresh throwaway copy, and save every command with its exact output.

    python capture.py [--repo C:/Dev/agent-brain]

The repo is only read (git ls-files + git archive of HEAD); the tour runs in a copy under the run folder
(STUDIO_WORK/runs/agent-brain-film/tour/<stamp>), against the repo's own examples folder. Commands are the README's
bash quickstart (alias brain="python -m agent_brain --brain examples/tiny-brain"); where the raw JSON carries absolute
paths, the command itself filters it (jq / grep), so what is shown is exactly what that command printed. Nothing
is typed in by hand. Writes data/session.json and data/files.json (the real file contents the film shows).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("STUDIO_WORK") or "C:/video-studio-work") / "runs" / "agent-brain-film"
BASH = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash")
TOUR = Path(os.environ.get("AGENT_BRAIN_TOUR") or "C:/code/agent-brain")
ALIAS ='brain() { python -m agent_brain --brain examples/tiny-brain "$@"; }'

# Order matters: this is the order they ran in. Cards in the film group only steps that ran back to back.
STEPS = [
    ("start0", "brain startup --cwd examples/todo-api"),
    ("route", "brain route --cwd examples/todo-api/src"),
    ("save", "brain handoff --file examples/handoff.example.json"),
    ("startup", "brain startup --cwd examples/todo-api"),
    ("refuse", "brain handoff --file examples/handoff.example.json"),
    ("cur1", "brain current --project todo-api"),
    ("append", "echo \"Staging deploy started.\" >> examples/todo-api/NOTES.md"),
    ("cur2", "brain current --project todo-api"),
    ("ls", "ls -C examples/tiny-brain"),
    ("deps", "grep dependencies pyproject.toml"),
]
# Never let a user name or home folder into a frame. (The tour runs in WORK/tour/agent-brain, so the absolute paths
# the tool prints name only that throwaway copy.)
def _private_terms():
    """What must never appear on screen: this machine's user and home folder names, generic home and mail
    patterns, and anything listed in STUDIO_PRIVATE_TERMS (comma separated; keep private names out of the code)."""
    import getpass
    import os
    terms = [r"/users/", r"\\users\\", r"/home/", r"appdata", r"onedrive", r"@gmail", r"@icloud"]
    for t in [getpass.getuser(), os.path.basename(os.path.expanduser("~"))] + \
            [x.strip() for x in os.environ.get("STUDIO_PRIVATE_TERMS", "").split(",")]:
        if t and len(t) > 2:
            terms.append(re.escape(t))
    return terms


PRIVATE = re.compile("(?i)(" + "|".join(_private_terms() + [r"desktop"]) + ")")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="C:/Dev/agent-brain")
    a = ap.parse_args()
    repo = Path(a.repo)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    # The tour runs where a developer would clone it (the tool prints absolute paths, so the copy's location is on
    # screen); the copy is removed again after the capture, and C:\code with it if this script made it.
    dst = TOUR
    made_parent = not dst.parent.exists()
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    # git archive of HEAD: the committed tree only, nothing from the working copy, nothing written to the repo
    arc = WORK / "tour" / "head.tar"
    subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "-o", str(arc), "HEAD"], check=True)
    with tarfile.open(arc) as tf:
        tf.extractall(dst, filter="data")
    arc.unlink()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""))
    steps, files = [], {}
    for sid, cmd in STEPS:
        p = subprocess.run([BASH, "-c", ALIAS + "\n" + cmd + " 2>&1"], cwd=str(dst), env=env, capture_output=True,
                           text=True, encoding="utf-8")
        out = p.stdout.replace("\r\n", "\n").rstrip("\n")
        if PRIVATE.search(out) or PRIVATE.search(cmd):
            raise SystemExit("private path in step %s: %r" % (sid, out[:200]))
        steps.append({"id": sid, "cmd": cmd, "out": out, "exit": p.returncode})
        print("%-8s exit %d  %s" % (sid, p.returncode, out.replace("\n", " | ")[:110]))
        if sid == "save":     # the cited file as it was when the handoff was saved, and the handoff it wrote
            files["NOTES.md"] = (dst / "examples/todo-api/NOTES.md").read_text(encoding="utf-8").split("\n")
            hid = json.loads(out)["id"]
            files["handoff"] = {"name": "examples/tiny-brain/handoffs/todo-api/%s.json" % hid,
                                "lines": (dst / "examples/tiny-brain/handoffs/todo-api" / ("%s.json" % hid))
                                .read_text(encoding="utf-8").split("\n")}
        if sid == "cur2":
            files["NOTES.md@after"] = (dst / "examples/todo-api/NOTES.md").read_text(encoding="utf-8").split("\n")
    files["handoff.example.json"] = (dst / "examples/handoff.example.json").read_text(encoding="utf-8").split("\n")
    (HERE / "data").mkdir(exist_ok=True)
    meta = {"repo": "github.com/VyasSathya/agent-brain", "head": head, "captured": time.strftime("%Y-%m-%d %H:%M"),
            "alias": ALIAS, "shell": "bash"}
    (HERE / "data" / "session.json").write_text(json.dumps({"meta": meta, "steps": steps}, indent=1, ensure_ascii=True),
                                                encoding="utf-8")
    (HERE / "data" / "files.json").write_text(json.dumps(files, indent=1, ensure_ascii=True), encoding="utf-8")
    shutil.rmtree(dst)
    if made_parent:
        dst.parent.rmdir()
    print("captured %d steps at %s -> data/session.json (tour copy %s, removed)" % (len(steps), head, dst))


if __name__ == "__main__":
    sys.exit(main())

