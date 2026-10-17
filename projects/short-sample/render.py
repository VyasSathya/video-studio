"""Short-form sample: a topic and a facts file go in, a 9:16 narrated short comes out with no human step.

The facts are the transcript of a public-domain NASA event (see projects/samples.py). A local text model writes
the script; every beat must quote the facts and every number must come from its quote (shortform.check_beat),
narration is a third-person synthetic voice, images are public domain from Wikimedia Commons, music is made
locally.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import edit, engines, media, picks, review, shortform  # noqa: E402
from projects.samples import sample  # noqa: E402

TOPIC = "What Scott Kelly learned from nearly a year in space"

if __name__ == "__main__":
    out = media.work_dir("short-sample")
    facts_f = out / "facts.txt"
    if not facts_f.exists():
        src = sample("kelly")
        wav = out / "source.wav"
        media.run(["-i", src, "-vn", "-ac", 1, "-ar", 16000, wav])
        facts_f.write_text(picks.transcript_text(edit.words_from(engines.stt(wav))), encoding="utf-8")
    script_f = out / "script.json"
    if not script_f.exists():
        script = shortform.script_from_topic(TOPIC, facts=facts_f.read_text(encoding="utf-8"), seconds=40)
        script_f.write_text(json.dumps(script, indent=1), encoding="utf-8")
    script = json.loads(script_f.read_text(encoding="utf-8"))
    shortform.run(script, out, voice="am_michael", mood="calm")
    review.page(out)
    print("review:", out / "review.html")
