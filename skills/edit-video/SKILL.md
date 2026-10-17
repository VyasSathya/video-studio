---
name: edit-video
description: Edit a talking video end to end with the five-step method (transcribe, cut mistakes and dead space, plan overlay beats from a plain-language brief, compose in HyperFrames, verify in a logged loop). Use for any raw take, talk or interview that needs cuts, captions and graphics, and as the base of the whiteboard and course styles.
---

# Edit a video: the five steps

1. Transcribe, verbatim. `engines.stt(wav, prompt=rawcut.VERBATIM)` on the local Whisper server; the disfluent
   prompt keeps "um" and repeats so they can be cut. (ElevenLabs Scribe is better at fillers and is paid: see
   docs/PAID.md; only with a yes.)
2. Cut mistakes and dead space. `edit.plan(words, duration, silence=edit.silences(wav))`: dead air, fillers,
   stutters (not emphasis like "really, really"), restarts and retakes; `timeline.render` draws every cut on the
   waveform; `edit.apply` cuts once with 30 ms fades. Read the timeline before going on.
3. Plan the beats from plain language, the way you would brief an editor: "when he says X, bring Y in on the
   right; highlight the key words at the bottom". `beats.parse(prompt, words)` turns it into rules;
   `beats.place(rules, words, duration)` puts each one where its trigger words were actually said (a trigger
   never said places nothing and is reported in `not_said`). `beats.keywords(words)` picks the emphasis words.
4. Compose. `styles.build(comp, footage, words, beats, style="whiteboard" | "course")`, or `overlay.build` for
   captions, a name tag and callouts only. Overlays sit on liquid-glass cards (translucent, blurred backdrop)
   so text reads over any frame.
5. Verify, in a loop, logged. This is the step that makes it good:
   - stills at every beat (`verify.stills(comp, [], out, times=[...])`), after each build has finished and
     after each return to the speaker; look at the sheet
   - deterministic gates: `verify.hf_check_json(comp)` (lint, runtime, layout, contrast), `verify.copy_lint`
   - render (`overlay.finish`), then `qc.check` and `verify.technical` (loudness, black, freeze, silence)
   - critique against the style's rules; fix; repeat; write each round with `verify.log(run, round, kind,
     findings, fixes)` to `critiques.jsonl`. At most 5 rounds; for anything shown outside, finish with a blind
     judge (see skills/product-launch: a fresh agent sees only frames, brief and rubric).

Worked examples: `projects/raw-edit-sample` (steps 1, 2, 4, 5), `projects/style-samples` (all five).
Never change what a speaker said: cut, never rewrite. Captions are the transcript's words.
