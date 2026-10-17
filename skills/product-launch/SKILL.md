---
name: product-launch
description: Make a short, faceless product launch film (20 to 30 s, or a 10 s cut) from the product's real screens in the look of Linear, Raycast, Arc, Vercel and Apple feature films; 16:9 and 9:16. Use when asked for a launch video, a feature promo, a "professional" demo video or GIF, or anything that should not look like a raw screen recording.
---

# Product launch film

Code: `studio/launch.py` (`render(brief, out_mp4, width, height) -> manifest`), screens from
`studio/capture.mjs`, checks from `studio/verify.py`, music from `studio/music.launch_track`.
Worked example: `projects/crewboard-launch` (capture.json, brief.json, render.py).

## The rules (why it reads as made by a company, not generated)

Source of truth
- Every screen, number and word on screen comes from the real product: capture it from a real build or its demo
  mode with `studio/capture.mjs` (stills at 2x, plus where each feature sits, read from the DOM). A missing
  screen means capture it or ask, never draw it.
- Colors, fonts and radius come only from the product's own theme (`tokens` in the brief: bg, fg, accent, font,
  mono, radius). Fonts HyperFrames cannot fetch come from `@fontsource/<name>` in node_modules.
- Generated pixels: none in a launch film. No stock footage, no generated people, hands or faces, no abstract 3D
  shapes, no particles, no glowing halos, no brains or robots for "AI".

Shape
- No intro card. Shot 1 is the app itself in a plain window (hairline border, three neutral dots, lit top edge,
  deep soft shadow) on a background made from the tokens (bg, a lifted gradient, the accent at low strength,
  fine grain), settling from a 3D tilt (rotateX 22, rotateY -16) to flat. In 9:16 it settles on a wide view of
  the first feature's region, because a wide app cannot be shown whole in a tall frame.
- Then one shot per feature (3 for 10 s, 4 to 6 for 20 to 30 s), each 1.5 to 2 s: long enough to read the title
  (0.9 s + characters / 20 per second), cut on the music beat.
- End card: the product name large in its own font, the install or visit line in its mono font in a hairline
  pill; it holds at least 2.5 s. Nothing else.
- No voiceover. Music is a launch track made here (`music.launch_track`: 120 bpm, drums drop for one beat
  before the end card, a low hit on it) or a supplied track whose licence is on file. The track's licence goes
  in the manifest.

Motion
- The camera does the transitions: each feature shot opens with the camera already moving, pushing into the
  feature's focus rect so the screen bleeds off frame (`expo.out`, nearly the whole shot), with a 0.3 s rack
  focus (blur 10 px to 0). Straight cuts between shots, never wipes or whips without a reason.
- One motion at a time, every move eased: camera first; at +0.28 s a soft spotlight (everything outside the
  focus dimmed, a thin accent outline); at +0.36 s the title rises in word by word (stagger 0.06 s,
  `power3.out`). A cursor and click ring only when the brief gives a real target (`cursor`), after the title.
- Titles: 2 to 5 plain words naming what the user gets ("Every session, live"), weight 650, tight tracking,
  bottom left over a scrim made from bg (16:9) or the bottom third (9:16). Max 42 characters per line.
  Banned words and phrases: `studio/verify.BANNED` and `BANNED_PHRASES`.

## Where these numbers come from (inspiration to skill)

Measured on 2026-10-17 from six official launch films on the companies' own channels (Linear Releases, Linear
Code Intelligence, Framer Skills, Arc Live Folders, Raycast for Windows, Apple HomeView): frames only, for
reference; the files were deleted after measuring and nothing of theirs is reused. What they agree on and we
follow:
- open on the product in motion, never a title card; one neutral ground plus one accent used only on the thing
  being chosen or clicked; brand color on cards, never tinted over product shots
- zoom into a UI region by 1.8 to 3x so it fills most of the frame; crop the rest, never shrink UI to fit;
  dim the non-subject area to 40 to 60 percent rather than redraw anything
- depth from tilt and focus falloff; on a dark ground a hairline edge does more than a shadow
- titles 2 to 5 words, sentence case, one typeface, rising 8 to 16 px with ease-out, held about 2 s
- a pointer only when the click is the point, with one ring
- moves end in a hold before the next event; cut on bar lines or beats where music leads (Arc cuts every 2
  beats in its closing run)
- 9:16 (not in the sample, chosen): reframe, never letterbox; titles near 13 to 30 percent from the top; keep
  the top 10 percent and bottom 20 percent clear of titles for platform UI
Where they disagree with us: their product shots run 2.5 to 5 s (Vyas asked for 1 to 2 s per feature, and his
word wins for short films; use 2.5 s and up for 20 to 30 s films with 2 or 3 features); Linear and Framer redraw
their UI as motion graphics with invented data (we never do; we crop, focus and dim real captures instead);
Apple opens with a name card (we do not). `python -m studio inspire ref.mp4` measures a new reference the same
way (shot lengths, tempo and cuts on beat, palette, motion, busyness, two contact sheets).

## The loop (do every step, log every round)

1. Brief: `features` in story order, each a real capture with a focus rect from the DOM or measured on the
   capture. Write where each value came from in `_sources`.
2. Stills first: `launch.build(...)` then `verify.stills(comp, shots, out)` writes frames at every cut, after
   each title lands and before each next cut, tiled to `sheet.png`. Look at the sheet. Fix, rebuild, repeat.
3. Deterministic gates: `verify.gates(comp, texts, cuts, beat)` runs `hyperframes check --strict
   --at-transitions` (lint, runtime, layout, contrast), the copy lint and the beat check. Every warning is a
   defect, unless the snapshot shows it is the intended camera bleed; mark only those elements
   `data-layout-allow-overflow`.
4. Full render: `launch.render(...)`, then `verify.technical(mp4, manifest)`: ffprobe, blackdetect, freezedetect
   (the end card hold is declared in the manifest), silencedetect, loudness -14 LUFS and true peak at most -1.
5. Blind judge: `verify.packet(dir, [sheets], brief_text, rubric.md)` makes a folder with ONLY the frame sheets,
   the brief and `rubric.md`. A separate agent call (a fresh subagent; ideally also a non-Claude model) gets that
   folder path and nothing else: no plan, no log, no earlier verdict. Judges that see the maker's log pass
   failed clips most of the time.
   Also run `verify.blank_frames(stills)`: a composition whose script fails renders bare background, and
   `hyperframes check --strict` can still pass it.
6. Gate, in this order of trust:
   - pairwise first: `verify.packet_pair(dir, new_sheets, reference_sheets, brief, question)` against the
     asset it would replace (the current README GIF, or the last approved film), each order to its own fresh
     judge; the new film must win both orders. This was stable in practice (8 of 8 on the Talkover film).
   - the absolute rubric (every item PASS, overall at least 8) is advisory until a judge agrees with Vyas's own
     approve/reject labels (kappa 0.6 or more on 30 to 50 past items). Fresh judges on near-identical cuts
     scored 5 to 8 failures and asked for opposite fixes, so a rubric FAIL is a list of things to look at, not
     proof. Fix what more than one judge raises.
   At most 5 rounds either way; a film that loses pairwise is dropped, not shipped. Vyas makes the last call.
7. Every round goes to `critiques.jsonl` with `verify.log(run_dir, round, kind, findings, fixes)`.
8. Once a product has an approved film, new films are compared to it pairwise, both orders; a win counts only
   if it survives the swap.

## Feedback folded in (newest last)

- 2026-10-17 crewboard: GSAP `fromTo` renders its start state at time 0, so a rack-focus blur on a later shot
  blurred the opening; every later tween uses `immediateRender: false`.
- 2026-10-17 crewboard: a dark app on a dark background vanishes; lift the background with token gradients and
  light the window edge.
- 2026-10-17 crewboard: wide focus rects give shallow pushes and unreadable UI; aim the focus at the one block
  that proves the title (a list, a question and its buttons), about a third of the screen wide or less.
- 2026-10-17 crewboard: in 9:16 the window's bottom edge showed mid-frame; the vertical scrim is 62 percent tall
  and solid at the bottom.
- 2026-10-17 crewboard, blind judge rounds 1 to 5 (6, 7, 7, 7, 7 of 10; not passed, so not shipped):
  - titles over the pushed-in UI collide: in 16:9 the title has its own column on the left over an opaque
    scrim and the screen sits right; in 9:16 the title band is the top (solid to about 35 percent), the focal
    UI below it, and the bottom 20 percent stays clear for platform UI
  - a cursor scaled with the camera grows to 80 px and covers words: keep it about 34 px on screen, tip resting
    beside its target, the click ring on the target's centre, short travel
  - drawn outline boxes read as template: dim the rest instead; the camera sets the focus
  - long, strong rack focus reads murky: 6 px for 0.18 s
  - a dark app on a dark ground needs closer framing, a backlight larger than the window, and a lit rim
  - screens bleeding off frame slice text at the edges ("Decic"): version 2 fades the stage into the ground over
    the outer 6 to 7 percent of the frame (not yet judged; judge it on the next film)
  - word count is a gate in code (`verify.gates(..., titles=...)`, at most 5 words)
  - a staggered reveal with immediateRender:false shows not-yet-started words at full opacity: everything that
    animates in starts hidden in CSS (fixed in launch version 3, found by content-studio's judge)
- 2026-10-17 Talkover film (launch-example session, 7 rounds, 5 judged; lost the rubric, won pairwise 8 of 8):
  - one text focus per shot; close-ups about 1.0 s, shots where the viewer reads UI 2.0 to 2.5 s; any UI caption
    line that appears holds at least 1.4 s
  - all 16:9 feature titles on one left margin; only the end card is centred; words fade as they rise
  - frame edges must not cut through buttons at any moment of a push: measure the controls and nudge each
    close-up so both edges fall in gaps (or let the edge falloff hide them)
  - the end card holds about 2.3 s after its last line lands, then fades; a wordmark reveal starts on the cut
  - a lit environment beats one dark field: let the room light take some of the product's state colour
  - what every judge raised is likely real: small UI captions in 9:16, a feature with no visual subject beyond
    type, a look that reads as a polished app zoom rather than art-directed
  - GIFs with grain: denoise before the palette and cut the GIF to the feature section at 960 px
