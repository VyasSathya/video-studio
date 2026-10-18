"""Build the blind-judge packets for one round: folders that hold ONLY frame strips, a short brief and the rubric.

    python judge.py r1

WORK/review/judge/<round>/pair-1  X = agent-brain film, Y = Talkover reference (strip-wide, strip-tall)
WORK/review/judge/<round>/pair-2  X = Talkover reference, Y = agent-brain film
WORK/review/judge/<round>/rubric  agent-brain strips, the brief, skills/product-launch/rubric.md
Each folder goes to its own fresh judge (prompts in review/judge-prompts.md).
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from studio import verify  # noqa: E402
from storyboard import WORK  # noqa: E402

REF = ROOT / "projects" / "talkover-launch" / "review"
RUBRIC = ROOT / "skills" / "product-launch" / "rubric.md"
QUESTION = ("Judged purely as a launch film, which one is better made: more professional and studio-made, and "
            "clearer about what its product does?")


def main():
    rnd = sys.argv[1]
    d = WORK / "review" / "judge" / rnd
    if d.exists():
        shutil.rmtree(d)
    ours = [WORK / "review" / "strip-wide.png", WORK / "review" / "strip-tall.png"]
    ref = [REF / "strip-wide.png", REF / "strip-tall.png"]
    pair = (HERE / "review" / "pair-brief.md").read_text(encoding="utf-8").strip()
    p1, p2 = verify.packet_pair(d / "pair", ours, ref, pair, QUESTION)
    for src, dst in ((p1, d / "pair-1"), (p2, d / "pair-2")):
        shutil.move(str(src), str(dst))
        shutil.copy(RUBRIC, dst / "rubric.md")
    (d / "pair").rmdir()
    brief = (HERE / "review" / "judge-brief.md").read_text(encoding="utf-8")
    verify.packet(d / "rubric", ours, brief, RUBRIC)
    for p in sorted(d.iterdir()):
        print(p, sorted(x.name for x in p.iterdir()))


if __name__ == "__main__":
    main()
