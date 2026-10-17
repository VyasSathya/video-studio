"""Story from a folder sample: four recordings (a public-domain NASA event split in four, see projects/samples.py)
in one folder; the best moments are found, ordered into a story by a local text model, cut and captioned."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import media, media as _m, review, storyreel  # noqa: E402
from projects.samples import sample  # noqa: E402


def folder():
    d = media.work_root() / "samples" / "folder"
    if not d.exists() or not list(d.glob("*.webm")):
        d.mkdir(parents=True, exist_ok=True)
        src = sample("kelly")
        for i in range(4):
            _m.run(["-ss", i * 300, "-t", 300, "-i", src, "-c", "copy", d / ("recording-%d.webm" % (i + 1))])
    return d


if __name__ == "__main__":
    out = media.work_dir("story-sample")
    storyreel.run(folder(), out, credit="Footage: NASA (public domain)")
    review.page(out)
    print("review:", out / "review.html")
