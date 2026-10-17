import unittest

from studio import edit, overlay


def W(spec):
    """'word@start-end ...' -> word list."""
    out = []
    for tok in spec.split():
        text, _, t = tok.rpartition("@")
        s, e = t.split("-")
        out.append({"text": text, "start": float(s), "end": float(e)})
    return out


def why(cut):
    return [(r["why"], r["text"]) for r in cut["removed"]]


class Plan(unittest.TestCase):
    def test_dead_air_and_edges(self):
        w = W("hello@1.0-1.4 there@3.0-3.4")
        cut = edit.plan(w, 5.0)
        self.assertIn(("dead air", "1.6 s"), why(cut))
        self.assertEqual(cut["keep"][0]["start"], 0.88)
        self.assertAlmostEqual(cut["keep"][-1]["end"], 3.52)

    def test_stutter_cut_but_emphasis_kept(self):
        w = W("the@0.0-0.2 the@0.3-0.5 really,@0.6-0.9 really@1.0-1.3 long@1.4-1.8")
        cut = edit.plan(w, 1.8)
        self.assertEqual(why(cut), [("stutter", "the")])

    def test_restart_keeps_last_take(self):
        w = W("we@0.0-0.2 went@0.2-0.4 to@0.4-0.5 the,@0.5-0.7 um@0.8-1.0 we@1.1-1.3 went@1.3-1.5 to@1.5-1.6 "
              "the@1.6-1.7 store@1.7-2.1")
        cut = edit.plan(w, 2.1)
        kinds = [k for k, _ in why(cut)]
        self.assertIn("restart", kinds)
        new = edit.retime(w, cut["keep"])
        self.assertEqual(" ".join(x["text"] for x in new), "we went to the store")

    def test_retake_after_pause(self):
        w = W("the@0.0-0.2 rover@0.2-0.5 landed@0.5-0.8 on@0.8-0.9 mars@0.9-1.2 "
              "the@2.0-2.2 rover@2.2-2.5 landed@2.5-2.8 safely@2.8-3.1 on@3.1-3.2 mars.@3.2-3.6")
        cut = edit.plan(w, 3.6, max_gap=5)
        self.assertIn("retake", [k for k, _ in why(cut)])
        self.assertEqual(" ".join(x["text"] for x in edit.retime(w, cut["keep"])),
                         "the rover landed safely on mars.")

    def test_rhetorical_repeat_kept(self):
        w = W("great@0.0-0.3 to@0.3-0.4 be@0.4-0.5 here.@0.5-0.8 great@0.9-1.2 to@1.2-1.3 be@1.3-1.4 home@1.4-1.8")
        self.assertEqual(edit.plan(w, 1.8)["removed"], [])

    def test_retime_and_map(self):
        keep = [{"start": 0.0, "end": 1.0}, {"start": 2.0, "end": 3.0}]
        w = W("a@0.2-0.5 b@1.4-1.6 c@2.2-2.6")
        self.assertEqual([(x["text"], x["start"]) for x in edit.retime(w, keep)], [("a", 0.2), ("c", 1.2)])
        self.assertEqual(edit.map_time(2.5, keep), 1.5)
        self.assertIsNone(edit.map_time(1.5, keep))


class Numbers(unittest.TestCase):
    def test_number_must_count_the_same_thing(self):
        from studio import picks
        src = "We stayed for 340 days and spent six months with Gennady, nearly 400 experiments."
        self.assertEqual(picks.unsupported_numbers("He stayed 340 days and ran 400 experiments.", src), [])
        self.assertEqual(picks.unsupported_numbers("He did six spacewalks.", src), ["6 space"])
        self.assertEqual(picks.unsupported_numbers("It took 430 days.", src), ["430 days"])

    def test_posts_voice(self):
        from studio import picks
        res = {"linkedin": " ".join(["word"] * 120), "x_thread": ["I spent a year up there."] * 4,
               "carousel": [{"head": "h", "body": "b"}] * 5}
        self.assertIn("written in the first person as someone in the video", picks.check_posts(res, "text"))
        self.assertEqual(picks.check_posts(res, "text", voice="first"), [])


class CaptionTiming(unittest.TestCase):
    def test_groups_never_overlap(self):
        import json
        import re
        import tempfile
        from pathlib import Path
        from unittest import mock
        from studio import shortform
        words = W("one@0.0-0.3 two@0.31-0.6 three@0.61-0.9 four@0.91-1.2 five@1.21-1.5 six.@1.51-1.8 "
                  "seven@1.85-2.1 eight@2.1-2.4")
        with tempfile.TemporaryDirectory() as d:
            beats = [{"start": 0.0, "dur": 2.4, "say": "x", "visual": {"type": "kinetic", "text": "x"}}]
            shortform.build(d, "t", beats, words, 3.0, [])
            page = (Path(d) / "index.html").read_text(encoding="utf-8")
            anim = json.loads(re.search(r"const A = (\[.*?\]), SC", page).group(1))
            with mock.patch("studio.media.duration", return_value=3.0):
                overlay.build(d, Path(d) / "index.html", words, size=(1080, 1920))
            page2 = (Path(d) / "index.html").read_text(encoding="utf-8")
            anim2 = json.loads(re.search(r"const A = (\[.*?\]);", page2).group(1))
        for a in (anim, anim2):
            caps = [x for x in a if x[0] == "cap"]
            for p, q in zip(caps, caps[1:]):
                self.assertLessEqual(p[3], q[2] + 1e-9)


class Groups(unittest.TestCase):
    def test_breaks_at_sentence_and_pause(self):
        w = W("One.@0.0-0.2 two@0.3-0.5 three@0.5-0.7 four@2.0-2.2")
        self.assertEqual([[x["text"] for x in g] for g in overlay.groups(w)], [["One."], ["two", "three"], ["four"]])


if __name__ == "__main__":
    unittest.main()
