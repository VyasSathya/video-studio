# Review log: Talkover launch film

Order (from the rulebook): storyboard and copy lint, then `hyperframes lint` and `check --strict`, then render and
technical QC (ffprobe, blackdetect, freezedetect, silencedetect, ebur128), then a blind judge. The judge is a fresh
Opus subagent per round that sees only the beat strips, `judge-brief.md` and `judge-rubric.md` (prompts in
`judge-prompts.md`), never this log, the plan or a checker verdict. Pairwise runs against the current README
`docs/demo.gif` in both orders, each order in a fresh agent. Every check run is a JSON line in `checks.jsonl`.

## Round 1 (r1)

Deterministic: all 20 checks PASS (lint 0/0 both formats, check --strict ok both, 1920x1080 and 1080x1920 at 30 fps,
23.5 s, no undeclared black, freeze only on the end card, -15.8 LUFS, -2.7 dBTP, GIF 5.5 MB).

Self-review before the judge found one defect: at 15 s a long caption ran off the right edge (fixed in r2 by moving
that line under the wide shot).

Blind judge: **FAIL, 10 of 15 NO** (items 1, 2, 4, 6, 8, 9, 10, 11, 14, 15). What it said, and what changed for r3:

| Item | Judge finding | Change |
|---|---|---|
| 1, 11 | 2 s static idle open is dead air | 1.5 s opener that pushes in while the orb turns teal |
| 2 | Bulleted engines readout under the panel reads as invented UI | Removed. "Fully local." is type, panel blurred behind |
| 4 | "Fully local" pulls back until nothing is readable | Panel out of focus, type is the subject |
| 6 | Second lines too small; panel caption competes with the headline | Subs 46 px (16:9) / 52 px (9:16); orb shots frame the caption row out, type moves to the opposite side |
| 8 | Orb close-ups read as glowing balls; room light cycles four colours | Close-ups capped (z 11 to 7.6); one neutral room light |
| 9 | Caption cut mid-word at 15.2 s | Long line now plays only under the out-of-focus shot |
| 10 | Orange reply under "It stops"; "Always listening" over a thinking orb; state runs backwards in the local shot | Reply starts on the next cut; new "It types what you say." block owns the thinking state; reading runs through the local shot |
| 14 | 9:16 margins tight, orphan "cut in." | Explicit 9:16 line breaks, orb margins >= 40 px, panel shots full width |

Round 2 (r2) was r1 plus the 15 s caption fix only; it was not judged.

## Round 3 (r3)

Deterministic: 20/20 PASS. Not sent to the judge: my own look at the strips found a 0.5 s gap between two reply chunks
where the panel's caption fell back to the old "You:" line (14.8 s), and a long line that would touch the frame edge.
Both fixed for r4. (D: filled to 0 bytes during this round from another job's temp archive; the GIF and strips were
redone after space came back. Nothing of mine was lost.)

## Round 4 (r4)

Deterministic: 20/20 PASS.

Pairwise against the current README GIF: the new film won in **both orders** (fresh agent each order). Reasons given:
the GIF reads as a screen recording of a transcript with the panel as a small strip; the film follows the brief,
uses the orb colours as story, has kinetic type and an end card.

Blind judge: **FAIL, 6 of 15 NO** (items 1, 6, 9, 11, 14, 15).

| Item | Judge finding | Change for r5 |
|---|---|---|
| 1 | Reads as an app-zoom recording: flat 2D moves, type only fades, "Fully local" is a blur card | Opening hero move (panel tilts in perspective and settles flat), word-by-word masked type, wordmark mask reveal, deeper contact shadow, "Fully local" pushes in instead of holding |
| 6 | 16:9 second lines too faint for a phone | 50 px, brighter, heavier |
| 9 | Long caption cut mid-word at 14.8 s | The shot ends at 14.5 s; that line only plays under the out-of-focus shot |
| 11 | "Fully local" holds 3 s with nothing moving | 2.0 s with a push |
| 14 | 9:16 caption shots too small, half the frame empty, no push-in on the "wait" orb | 9:16 type always on top, panel shots at 2.8 to 3.5x (was 2.45), orb push-in for "wait" with the panel's lower half fading into the dark so no caption is cut |
| 10 (yes, minor) | Orb looks blue at 9.8 s | Not changed: it is the real panel's own colour blend from teal to violet |

New gate added after r5's first build: `hyperframes check --strict` passed a composition whose script failed to parse
(every frame was bare backdrop). `checks.py` now also fails any beat frame with no content.

## Round 5 (r5)

Deterministic: 22/22 PASS after one fix. The new blank-frame gate caught an empty beat at 16.75 s (the wordmark started
0.2 s after the cut); it now starts on the cut. The score was measured: -15 dB before the cut-in, -60 dB at 11.25 s,
back to -16 dB at 11.5 s when Claude answers.

Pairwise against the current README GIF: new film won in **both orders** again.

Blind judge: **FAIL, 5 of 15 NO** (items 1, 7, 11, 14, 15).

| Item | Judge finding | Change for r6 |
|---|---|---|
| 1 | Same layout every feature; wide shots read like a cleaned-up recording; orb colour lights nothing | Room light takes 35 % of the orb's colour as it changes; 9:16 rebuilt with tighter shots |
| 7 | 16:9 titles mix left, right and centre alignment | Every 16:9 feature title on one left margin; only the end card is centred |
| 11 | End card holds about 4 s after the URL lands | Film 21.0 s, about 2.3 s hold, then fade |
| 12 (yes) | Tagline and URL small | Both about 15 % larger |
| 14 | 9:16 still shows the whole panel width with about 20 px captions; bottom 35-40 % empty | No full-width panel shots in 9:16: close crops in the lower third; where a caption cannot fit whole, the panel fades into the dark under the orb |

GIF: the studio's GIF helper stepped down to 720 px to fit 8 MB because film grain makes GIF frames expensive.
render.py now denoises before palette generation and cuts the GIF to the feature section (0 to 16.5 s) at 960 px.

## Round 6 (r6)

Deterministic: 22/22 PASS. Pairwise: new film won in **both orders** (third round running).

Blind judge: **FAIL, 6 of 15 NO** (items 1, 6, 7, 11, 14, 15).

The judge contradicted round 5 on 9:16: r5 asked for no full-width panel shots; r6 asked for the full width with
margins so captions show. Different fresh judges weigh legibility of the UI caption against frame fill differently.
Round 7 takes the middle: full width with margins only for caption shots, orb close-ups everywhere else.

| Item | Judge finding | Change for r7 (last allowed round) |
|---|---|---|
| 1 | Frame edges cut through buttons; same field every shot | Measured the button extents; a solver nudges each close-up so neither edge crosses a button at any moment of the push (8 framings moved 1.5 to 17.5 px of panel) |
| 6 | Stray period visible during word reveal; 16:9 sublines small | Words fade as they rise; sublines dropped wherever the panel's own caption is the evidence |
| 7 | 9:16 "Fully local." 30 % larger and mid-frame | Same size and top position as every other title |
| 11 | Every shot 1.3-2 s and carries three text blocks | Orb close-ups 1.0 s, caption shots 2.0-2.5 s; one text focus per shot; the extra "types" beat folded into "Always listening" |
| 14 | 9:16 captions missing, one shot pans the orb out | 9:16 caption shots back at full width in the lower middle; every orb shot keeps the orb in frame |
| 5 (yes, nit) | Resumed sentence never appears | Not changed: that line is longer than the panel's caption box and scrolls; showing it means a clipped caption (the r4 judge failed that) |

## Round 7 (r7) - fifth and last judged round

Deterministic: 22/22 PASS. Pairwise against the current README GIF: new film won in **both orders** (four rounds out
of four).

Blind judge: **FAIL, 8 of 15 NO** (items 1, 4, 6, 9, 10, 11, 14, 15), worse than r5 (5 NO) on mostly the same picture.

Two of its findings were real regressions introduced in r7, and are fixed in the delivered cut (r7b, deterministic
checks only, not judged again because the cap is reached):

- 16:9 at 11.2 s: the title sat on top of the panel (s7 reused a framing that puts the panel where that title goes).
  s7 is back to the r6 framing with the edge kept in a gap between buttons.
- "Always listening." ran over the violet (thinking) orb, and two caption lines flashed for under 0.6 s. The listen
  beat is split again ("Always listening." on teal, "It types what you say." on the thinking orb), and the reply
  chunks are rescheduled so every caption line holds at least 1.4 s.

## Verdict

The piece did not pass the blind rubric within the five-round cap. By the rulebook it would be dropped, not shipped.
It is delivered here only because the point is for Vyas to judge it; nothing was posted or pushed.

What the five rounds show about the loop itself:

- Pairwise against the current GIF was stable: 8 of 8 comparisons (4 rounds, both orders) prefer the new film.
- The absolute rubric was not stable. Fresh judges on near-identical cuts scored 6, 5, 6, 8 NO and asked for
  opposite things (r5: never show the full panel in 9:16; r6: show the full panel with margins; r7: crop in again).
  Items flipped between YES and NO without a matching change. This is what the rulebook's calibration gate is for:
  a judge has to agree with Vyas's own labels (kappa 0.6+ on 30-50 items) before its verdicts gate anything. That
  set does not exist yet.
- Deterministic gates caught real defects the judge never mentioned (an empty frame on the end-card cut, a 0 byte
  disk) and missed one the judge would have (`hyperframes check --strict` passed a composition whose script did not
  run; the blank-frame gate now covers it).
- Items every judge raised, so likely real: 9:16 caption legibility (the panel's caption is small next to a phone
  frame), "Fully local" having no visual subject beyond type, and an overall look that reads as a polished app-zoom
  rather than an art-directed film (one dark field throughout, no lit environment).
