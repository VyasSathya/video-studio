---
name: fast-short
description: Fast 9:16 short from a topic and a facts file (or a script): narration, kinetic text, stats, lists and public-domain stills cut on a 120 bpm beat with a whoosh on each cut. Use for TikTok, Reels or Shorts style explainers.
---

# Fast short-form (9:16)

`shortform.script_from_topic(topic, facts)` then `shortform.run(script, out, pace="fast")`, or
`python -m studio short --topic ... --facts ...` (calm pace) and `projects/short-sample/render_fast.py`.

- Script rules (checked in code): every beat quotes the facts and every number is in its quote; narration is an
  unnamed third-person narrator (a synthetic voice never speaks as a real person); on-screen words are words the
  facts use. Beats that fail are dropped and the script is regenerated.
- Pace: each beat starts on the next beat of a 120 bpm launch track (`music.launch_track`), so every cut lands
  on the music; a short whoosh 0.18 s before each cut and a low hit on the end card (HyperFrames' bundled
  Pixabay effects, free in rendered videos; the licence of every sound is in the manifest).
- Voice: Kokoro, labelled "Synthetic voice" on screen and on the end card.
- Captions 3 words at a time, bold, the spoken word lit; titles stay clear of the top 10 and bottom 20 percent.
- Checks: `verify.on_beat(cuts, 0.5)` must be empty; `qc.check` for loudness and black frames.
