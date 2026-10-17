import unittest

from studio import beats, launch, verify


def W(text, start=0.0, step=0.3):
    out, t = [], start
    for w in text.split():
        out.append({"text": w, "start": round(t, 3), "end": round(t + step * 0.9, 3)})
        t += step
    return out


class Beats(unittest.TestCase):
    def test_trigger_must_be_said(self):
        words = W("so we will go to Mars one day and then come back home safely", start=1.0)
        r = beats.place([{"when": "go to Mars", "show": "card", "text": "Mars", "hold": 2},
                         {"when": "the Moon", "show": "card", "text": "Moon", "hold": 2}], words, 20.0)
        self.assertEqual([b["when"] for b in r["beats"]], ["go to Mars"])
        self.assertEqual(r["not_said"], ["the Moon"])
        self.assertAlmostEqual(r["beats"][0]["t"], 1.9 - 0.15, places=2)

    def test_late_takeover_becomes_side_beat_and_film_ends_on_speaker(self):
        words = W("and that is why we go to Mars", start=7.5)
        b = beats.place([{"when": "go to Mars", "show": "takeover", "text": "Mars", "hold": 3}], words, 10.5)["beats"][0]
        self.assertEqual(b["show"], "card")
        self.assertLessEqual(b["end"], 10.5 - 0.2)

    def test_beats_never_overlap(self):
        words = W("one two three four five six seven eight nine ten")
        r = beats.place([{"when": "two", "show": "card", "text": "a", "hold": 3},
                         {"when": "four", "show": "card", "text": "b", "hold": 3}], words, 30)["beats"]
        self.assertGreaterEqual(r[1]["t"], r[0]["end"])


class Launch(unittest.TestCase):
    def test_shots_on_the_beat_and_long_enough_to_read(self):
        brief = {"features": [{"title": "Every session, live", "asset": "a.png"},
                              {"title": "What each one is doing", "asset": "b.png"},
                              {"title": "Answer what's waiting", "asset": "c.png", "cursor": [0, 0, 1, 1]}],
                 "end": {"title": "crewboard", "sub": "python -m crewboard --open"}}
        shots, total = launch.plan(brief, 0.5)
        self.assertEqual([s["kind"] for s in shots], ["establish", "feature", "feature", "feature", "end"])
        self.assertEqual(verify.on_beat([s["start"] for s in shots], 0.5), [])
        for s, f in zip(shots[1:4], brief["features"]):
            self.assertGreaterEqual(s["end"] - s["start"], 0.9 + len(f["title"]) / 20.0)
        self.assertGreaterEqual(shots[-1]["end"] - shots[-1]["start"], 2.5)


class Blank(unittest.TestCase):
    def test_bare_background_is_caught(self):
        import tempfile
        from pathlib import Path
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as d:
            empty = Path(d) / "empty.png"
            Image.new("RGB", (960, 540), (12, 12, 14)).save(empty)
            full = Path(d) / "full.png"
            im = Image.new("RGB", (960, 540), (12, 12, 14))
            ImageDraw.Draw(im).rectangle([100, 100, 800, 400], outline=(240, 240, 240), width=4)
            ImageDraw.Draw(im).text((140, 200), "Every session, live", fill=(250, 250, 250))
            im.save(full)
            self.assertEqual(verify.blank_frames([empty, full]), [str(empty)])


class Copy(unittest.TestCase):
    def test_title_rules(self):
        self.assertEqual(verify.copy_lint(["Every session, live"], max_words=5), [])
        self.assertTrue(verify.copy_lint(["See what each one is doing"], max_words=5))
        self.assertTrue(verify.copy_lint(["A seamless way to work"]))
        self.assertEqual(verify.on_beat([1.1, 1.02], 0.5), [1.1])   # one frame of slack


if __name__ == "__main__":
    unittest.main()
