# Review log: crewboard launch film

Order (from the rulebook): storyboard and copy lint, framing, tokens and privacy, then `hyperframes lint` and
`check --strict`, then render and technical QC (ffprobe, blackdetect, freezedetect, silencedetect, ebur128, GIF),
then the beat strips and the blank-frame check, then blind judges. Every check run is a JSON line in `checks.jsonl`.

Judges are fresh Opus subagents per round and per order. They see only a packet folder built by `judge.py`: the
beat strips, a short brief and the rubric (`judge-brief.md` / `judge-brief-pair.md`, `judge-rubric.md`, prompts in
`judge-prompts.md`), never this log, the plan, a checker verdict or which film is the reference. The gate is
pairwise against the approved Talkover film's strips (`projects/talkover-launch/review/strip-*.png`), both orders,
one fresh judge per order. The absolute rubric (skills/product-launch/rubric.md without its paragraph naming the
reference) is advisory.

How the product pixels were made: `ui_render.mjs` (this project) records crewboard's real page frame by frame on a
virtual clock instead of `studio/webrec.mjs` (Chrome's screencast, frames at paint times, a drawn cursor), so every
frame lands on the film clock and the page events land on beats; it also writes `rects.json` (where every line of text
and every control sits, from the DOM), which `studio/capture.mjs` would give per still. Cameras are solved from those
rects, never typed in.

## Round 1 (r1) - not judged

Deterministic: 20/25. Real failures: none in the film. Gate bugs fixed: the hex-colour scan read the id `#fadeB` as a
colour, the font scan matched a space, the privacy scan matched the public repo URL. `hyperframes check --strict`
warned `escaped_container` on `#cam`: the intended camera bleed, marked `data-layout-allow-overflow`.

Own look at the strips before any judge: the bottom type scrim covered the lower half of the frame, so the "No" answer
read grey (the page frame itself was right, checked at 12.4 s in page.mp4); a 7-word title ran over the light panel;
the 9:16 opening was a small page in a tall frame; list shots left half the 16:9 frame empty. Fixed for r2: shorter
scrim, focal blocks above it, two-line title, camera anchors that hold one page point still during a push.

## Round 2 (r2)

Deterministic: 25/25 PASS (storyboard, beats, holds, copy, frame edges, tokens, privacy, lint 0/0, check --strict
ok, 1920x1080 and 1080x1920 at 30 fps, no black, freeze only on the end card, no silence, -15.7 LUFS, -1.8 dBTP, GIF
7.39 MB at 960 px, no blank beat frame).

Pairwise vs Talkover: **split**. Order 1 (crewboard = X): Talkover. Order 2 (crewboard = Y): crewboard.
Rubric (advisory): overall 5, FAIL 3, 4, 5, 8, 10, 12, 13, 14.

Raised by more than one judge, and the change for r3:

| Finding | Change |
|---|---|
| White light-mode panel fading to black breaks the palette (both pairwise, rubric) | Dropped the light theme; the list shot is dark |
| Opening is a small, under-lit window (both pairwise, rubric) | Larger start, lifted backdrop, key light on the page |
| Titles over dimmed UI text (pairwise 2, rubric) | Scrims solid behind every title (16:9 bottom, 9:16 top) and the edge gate uses those bands |
| "Its agents too." reads as a typo, says nothing (both pairwise) | "Every agent, under its session." |
| "Runs on your machine" has no subject (pairwise 2, rubric) | The command and the line it prints, `crewboard on http://localhost:7788/` (crewboard's own print) |
| Titles over 5 words (rubric) | "One list, shared with agents." Gate back to 5 words |
| Dim list on the right, empty glow on the left (pairwise 1) | List shots pushed in and centred; the rest of the page out of focus (dimmed and blurred) |

## Round 3 (r3)

Deterministic: 25/25 PASS after two fixes the gates found: freezedetect caught a 1.2 to 1.4 s hold in the local shot
(now a slow push), and the GIF went over 8 MB (palette steps down; 7.27 MB). Own look found the list focus covered
only the group headers (rows half blurred) and the terminal card off centre; both fixed before judging.

Pairwise vs Talkover: **split again**. Order 1 (crewboard = X): Talkover. Order 2 (crewboard = Y): crewboard. In both
judged rounds the film shown second won, so these are position-bias ties, not wins.
Rubric (advisory): overall 6, FAIL 1, 8, 12, 13, 14.

Raised by more than one judge, and the change for r4:

| Finding | Change |
|---|---|
| Opening still murky; 9:16 opening has an empty bright top and the page cut at the left (pairwise 1, 2, rubric) | Less tilt, a lit rim, a coloured backlight hugging the page; 9:16 shows the whole page with margins |
| Blurred colour blobs in the room and a grey halo behind the end card (pairwise 1, 2, rubric) | Room light cut to a faint neutral; the state colour now lights the page from behind (a glow at its edges) |
| Empty terminal box, then a typewriter (pairwise 1, 2, rubric) | The card enters with the command on it; the printed line follows |
| The out-of-focus column at the right edge reads as clipped text ("Dec") (pairwise 1, 2) | Surround blur doubled and darker |
| "What each one is doing" mostly empty (pairwise 2) | 16:9 pushes into the session's own to-do list |

## Round 4 (r4)

Deterministic: 24/25 on the first run: `hyperframes check --strict` 9:16 hit a 10 s navigation timeout (the
machine was busy); the rerun was 25/25 (both runs are in `checks.jsonl`). GIF 7.80 MB.

Pairwise vs Talkover: **split a third time**. Order 1 (crewboard = X): crewboard. Order 2 (crewboard = Y): Talkover.
This time the film shown first won both orders. Three judged rounds, six verdicts, three for each film, and every
verdict went to the same position within a round: on these strips the judges cannot separate the two films.
Rubric (advisory): overall 6, FAIL 1, 8, 12, 13, 14.

What the order-1 judge preferred in crewboard: every push lands on one readable block that the title names, a real
9:16 recomposition, one title position, the answer being clicked. What the order-2 judge preferred in Talkover: one
hero object whose colour carries the story.

Raised by more than one judge, and the change for r5:

| Finding | Change |
|---|---|
| Opening dim, no separation or visible shadow (both pairwise, rubric; every round) | Lighter neutral studio backdrop from the theme's ring grey, deeper contact shadow, brighter hairline |
| Brown smear left of the list shots (pairwise 1, rubric) | Coloured backlight removed; room light almost off |
| Terminal card small and floating on blur (both pairwise, rubric) | A larger terminal window in front of the whole page, both sharp: the command, its line, and the page it serves |
| All grey until the amber URL; Talkover's colour carries its story (both pairwise) | Each title starts with the status dot of its state, in crewboard's own style (amber with the live pulse, green, violet) |
| 9:16 lower half empty, establishing window small (pairwise 2, rubric) | 9:16 list shots pushed in to fill the middle; the 9:16 opening turns the whole page toward the camera in perspective so it fills the width |

## Round 5 (r5)

Deterministic: 24/25 on the first run (`hyperframes lint` 9:16 returned no output under load; run by hand it was
0 errors, 0 warnings); the rerun was 25/25.

Pairwise vs Talkover: **split a fourth time**. Order 1 (crewboard = X): Talkover. Order 2 (crewboard = Y): crewboard.
The film shown second won both orders again. Running total: 4 verdicts each.
Rubric (advisory): overall 6, FAIL only 12, 13, 14 (down from 8 fails in r2): 1 (terminal "invented overlay") and 8
(colour blobs) now pass.

The order-2 judge, picking crewboard: titles always in one place with a status dot in the UI's own colour, a real
9:16 recomposition, push-ins that land on one whole region, the command and the localhost line as proof.

Raised by more than one judge, and the change for r6 (the last judged round):

| Finding | Change |
|---|---|
| Opening dim, flat (pairwise 1, rubric); 9:16 opening clipped at the right (pairwise 1, rubric) | Brighter studio backdrop and rim, stronger key light and sheen; 9:16 opening turns less and sits inside margins |
| A blurred dead third of the frame, lopsided crops, empty dark halves in 16:9 (both pairwise, rubric) | 16:9 recomposed as two columns: the title in its own left column on a solid scrim, the UI centred in the right column |
| Rows sliced at the top or bottom of a push (pairwise 1) | The edge gate no longer excuses out-of-focus lines at the top and bottom edges, only at the sides |
| Middle shots look alike (both pairwise) | The agents shot frames the parent session and its two agents as one group; the session shot is its own to-do list (progress circles, not rows) |
| The page under the terminal shrunk unreadable, terminal pasted on (pairwise 2, pairwise 1 for 9:16) | The terminal alone is the subject, larger, lit like the page and turning flat in perspective |

## Round 6 (r6) - fifth and last judged round

Deterministic: 25/25 PASS. GIF 7.13 MB.

Pairwise vs Talkover: **split a fifth time**. Order 1 (crewboard = X): Talkover. Order 2 (crewboard = Y): crewboard.
Rubric (advisory): overall 6, FAIL 8 (an empty grey glow frame at 12.8 s), 13 (opening murky), 14 (every feature
shot uses the same title-left, UI-right layout).

The order-2 judge, picking crewboard: one designed system (title left, UI right, a status dot that matches the UI it
points at), a real state change on the answer shot, deliberate out-of-focus crops, a real 9:16 recomposition. The
order-1 judge, picking Talkover: a lit hero object whose colour carries the state, titles that name visible actions,
crewboard's dim UI and small 9:16 type.

Two findings more than one judge raised were fixed in the delivered cut (r6b, deterministic checks only, not judged
again because the cap is reached):

- the empty glow frame at the start of the local shot: the terminal now enters on the cut
- the grey halo behind the end card (pairwise 2) and the bright room behind later shots: the studio backdrop is
  brightest for the opening and settles lower from the first cut

## Verdict

Pairwise against the approved Talkover reference, five judged rounds, both orders, a fresh Opus judge per order:

| Round | Order 1 (crewboard = X) | Order 2 (crewboard = Y) | Result |
|---|---|---|---|
| r2 | Talkover | crewboard | split (second shown won) |
| r3 | Talkover | crewboard | split (second shown won) |
| r4 | crewboard | Talkover | split (first shown won) |
| r5 | Talkover | crewboard | split (second shown won) |
| r6 | Talkover | crewboard | split (second shown won) |

Ten verdicts, five each, and in every round both judges picked the same position. On these strips the judges cannot
separate the two films; the position decides. By the rulebook's strict reading ("must win both orders") the new film
did not win; by the brief's ("at least as good") it tied. It is delivered for Vyas to judge; nothing was posted,
pushed or committed.

Advisory rubric over the rounds: 5, 6, 6, 6, 6 overall; failures 8, 5, 5, 3, 3. What it still fails on, every round:
the establishing shot reads dim (a near-black page on a dark ground) and the film reads as one repeated layout.

What the rounds show about this product: Talkover has one hero object whose colour is the state; crewboard is a page
of lists whose state colours are 8 px dots. The judges reward the colour story; the dots before each title and the
amber URL were the closest honest equivalent, since nothing on crewboard's page is larger than a dot in a state
colour, and drawing one would be inventing UI.
