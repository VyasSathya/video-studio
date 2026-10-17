"""The fast 9:16 short: the same grounded script as render.py (run that first), cut to a 120 bpm launch track,
every beat on the beat grid, a whoosh on each cut, the drums landing on the end card. No human step."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import media, review, shortform  # noqa: E402

if __name__ == "__main__":
    src = media.work_dir("short-sample")
    out = media.work_dir("short-fast")
    script = json.loads((src / "script.json").read_text(encoding="utf-8"))
    m = shortform.run(script, out, voice="am_michael", pace="fast")
    review.page(out)
    print("review:", out / "review.html")
