"""agent-brain terminal GIF: replay session.json (real output, from capture.ps1) and render mp4 + gif.

    python projects/agent-brain-terminal/render.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from studio import hf, media, terminal   # noqa: E402


def main():
    steps = json.loads((HERE / "session.json").read_text(encoding="utf-8-sig"))
    page, total = terminal.build(steps, "agent-brain", "PS> ")
    comp = HERE / "build" / "hf"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "index.html").write_text(page, encoding="utf-8")
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    mp4 = hf.render(comp, out / "agent-brain-tour.mp4", quality="high")
    media.gif(mp4, out / "agent-brain-tour.gif", width=960, fps=12, colors=96)
    media.contact_sheet(mp4, out / "contact-sheet.png", every=3.0, cols=3)
    for p in (mp4, out / "agent-brain-tour.gif"):
        print("%s  %.2f MB" % (p, p.stat().st_size / 1048576))


if __name__ == "__main__":
    main()
