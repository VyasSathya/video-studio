import os
import unittest
from unittest import mock

from studio import paid


class Gate(unittest.TestCase):
    def test_dry_run_without_all_three(self):
        with mock.patch.dict(os.environ, {"FAL_KEY": "x", "STUDIO_ALLOW_SPEND": "1"}):
            with mock.patch.object(paid, "_http", side_effect=AssertionError("must not call")):
                r = paid.broll_clip("a rocket on the pad", seconds=5)            # confirm missing
                self.assertTrue(r["dry_run"])
                self.assertAlmostEqual(r["estimated_usd"], 0.56)
        with mock.patch.dict(os.environ, {"FAL_KEY": "x"}, clear=True):
            with mock.patch.object(paid, "_http", side_effect=AssertionError("must not call")):
                self.assertTrue(paid.broll_clip("x", confirm=True)["dry_run"])  # spend not allowed
        with mock.patch.dict(os.environ, {"STUDIO_ALLOW_SPEND": "1"}, clear=True):
            with mock.patch.object(paid, "_http", side_effect=AssertionError("must not call")):
                self.assertTrue(paid.elevenlabs_tts("hi", "v", "o.mp3", confirm=True)["dry_run"])  # no key

    def test_heygen_body_is_v3(self):
        r = paid.heygen_avatar_video("Hello there.", "av", "vo", 30)
        self.assertEqual(r["url"], "https://api.heygen.com/v3/videos")
        self.assertEqual(r["body"]["script"], "Hello there.")
        self.assertAlmostEqual(r["estimated_usd"], 1.16, places=2)


if __name__ == "__main__":
    unittest.main()
