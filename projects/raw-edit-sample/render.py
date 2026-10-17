"""Raw-footage edit sample: a live, unedited stretch of a public-domain NASA event goes in; 16:9 and 9:16 cuts
come out with dead air, stutters and restarts removed, word-level captions, a name tag and callouts.

Source: "Scott Kelly Talks About His Year in Space", NASA, public domain, from Wikimedia Commons
https://commons.wikimedia.org/wiki/File:Scott_Kelly_Talks_About_His_Year_in_Space.webm
Fetched once by projects/samples.py into the work folder; this script uses 6:26 to 9:17 of it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import media, rawcut, review  # noqa: E402
from projects.samples import sample  # noqa: E402

if __name__ == "__main__":
    src = sample("kelly")
    out = media.work_dir("raw-edit-sample")
    m = rawcut.run(src, out, name="Scott Kelly", role="NASA astronaut", credit="Footage: NASA (public domain)",
                   start=386, end=557)
    review.page(out)
    print("review:", out / "review.html")
