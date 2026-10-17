"""Run the pinned HyperFrames CLI from video-studio (read-only use) with its libx264 ffmpeg on PATH."""
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import hf, media  # noqa: E402,F401

if __name__ == "__main__":
    import subprocess
    from pathlib import Path
    proj = Path(sys.argv[1])
    r = hf.hyperframes(sys.argv[2:], proj, check=False)
    sys.exit(r.returncode)
