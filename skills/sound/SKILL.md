---
name: sound
description: Sound for an edit - a music bed on the beat grid, effects on transitions, ducking under speech, one loudness target, and the licence of every sound on file. Use whenever a video gets music or sound effects.
---

# Sound

- Music: `music.launch_track(seconds, out, bpm=120, hit_at=end)` for launch films and fast shorts (beats exactly on
  k * 60 / bpm, drums drop a beat before `hit_at`, a low hit on it); `music.bed(seconds, out, mood)` for calm
  explainers. Both are synthesised here, so the licence is ours. A supplied track needs its licence in the brief.
- Cuts on the beat: plan shot starts on the grid and check with `verify.on_beat(cuts, beat)`.
- Effects: `sound.sfx_track([(t, "whoosh-short", -12), ...], total, out)` from HyperFrames' bundled Pixabay set
  (free in rendered videos, not to be redistributed as files). Whoosh 0.15 to 0.2 s before a cut, a soft click on
  a real click, a hit on the end card; never more than one effect per cut.
- Ducking: `music.duck(voice, music, out, music_db=-14 to -18)`: the bed sits under the voice and dips further
  while anyone speaks (sidechain).
- Master: two-pass loudnorm to -14 LUFS, true peak at most -1 dBTP (`media.mux_loud`); `verify.technical` fails
  closed on silence, loudness or peak.
- Every manifest lists each sound and its licence (`sound_licences` / `music.licence`).
