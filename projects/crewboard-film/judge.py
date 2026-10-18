"""Build the blind judge packets for one round (the judges themselves are fresh subagents, run by the maker):

    python judge.py r2

<work>/review/<round>/pair/order-1 and order-2: crewboard strips and the approved Talkover reference strips as X
and Y (swapped between orders), the pairwise brief and question, the rubric. <work>/review/<round>/rubric: the
crewboard strips, the crewboard brief, the rubric. Nothing else goes in: no plan, no log, no verdict, no names.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from studio import verify  # noqa: E402
import storyboard as SBM  # noqa: E402

REF = HERE.parents[0] / "talkover-launch" / "review"
QUESTION = ("Which film would a design-literate viewer judge as more professional, studio-made, and clearer about "
            "what its product does? Judge the craft of the film, not which product you prefer.")


def main():
    rnd = sys.argv[1]
    rev = SBM.WORK / "review"
    out = rev / rnd
    new = [rev / "strip-wide.png", rev / "strip-tall.png"]
    ref = [REF / "strip-wide.png", REF / "strip-tall.png"]
    brief = (HERE / "review" / "judge-brief-pair.md").read_text(encoding="utf-8")
    rubric = HERE / "review" / "judge-rubric.md"
    dirs = verify.packet_pair(out / "pair", new, ref, brief, QUESTION)
    for d in dirs:
        shutil.copyfile(rubric, d / "rubric.md")
    verify.packet(out / "rubric", new, (HERE / "review" / "judge-brief.md").read_text(encoding="utf-8"), rubric)
    print("order-1: X = crewboard, Y = reference; order-2: X = reference, Y = crewboard")
    for d in dirs + [out / "rubric"]:
        print(d, sorted(p.name for p in d.iterdir()))


if __name__ == "__main__":
    main()
