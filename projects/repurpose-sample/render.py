"""Repurposing sample: 20 minutes of a public-domain NASA event in; three 9:16 clips, a LinkedIn post, an X
thread and carousel slides out, picked and written by a local text model, with no human step. Nothing is posted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import media, repurpose, review  # noqa: E402
from projects.samples import sample  # noqa: E402

if __name__ == "__main__":
    out = media.work_dir("repurpose-sample")
    repurpose.run(sample("kelly"), out, n=3, credit="Footage: NASA (public domain)")
    review.page(out)
    print("review:", out / "review.html")
