"""Run the pinned HyperFrames CLI (node_modules) with our ffmpeg first on PATH."""
import os
import subprocess
from pathlib import Path

from . import media

ROOT = Path(__file__).resolve().parents[1]


def npx():
    return "npx.cmd" if os.name == "nt" else "npx"


def hyperframes(args, cwd, check=True):
    env = media.env_with_ffmpeg()
    env.setdefault("HYPERFRAMES_SKIP_SKILLS", "1")
    env.setdefault("HYPERFRAMES_NO_TELEMETRY", "1")
    env.setdefault("DO_NOT_TRACK", "1")
    cmd = [npx(), "--prefix", str(ROOT), "hyperframes"] + [str(a) for a in args]
    return subprocess.run(cmd, cwd=str(cwd), env=env, check=check)


def render(project_dir, out, fps=30, quality="high", workers=None):
    """Render a HyperFrames project folder (it holds index.html) to an mp4."""
    args = ["render", "-o", Path(out).resolve(), "-f", fps, "-q", quality]
    if workers:
        args += ["-w", workers]
    hyperframes(args, project_dir)
    return Path(out)


def snapshot(project_dir, times, out_dir):
    """PNG of the composition at given times, without a full render (fast visual check)."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return hyperframes(["snapshot", "--at", ",".join("%g" % t for t in times), "-o", out_dir], project_dir,
                       check=False)
