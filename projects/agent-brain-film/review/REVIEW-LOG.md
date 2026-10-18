# Review log: agent-brain launch film

Order (from the rulebook and the Talkover film): storyboard and copy lint, provenance (every card row traced to the
captured output), `hyperframes lint` and `check --strict`, then render and technical QC (ffprobe, blackdetect,
freezedetect, silencedetect, ebur128, GIF size), the blank-frame gate on the beat strips, then blind judges. Every
check run is a JSON line in `checks.jsonl`.

Judges are fresh Opus subagents that see only a packet folder (`judge.py` builds them under
`C:\video-studio-work\runs\agent-brain-film\review\judge\<round>\`): frame strips, a short brief and the rubric
(`skills/product-launch/rubric.md`). Never this log, the plan, the storyboard or a checker verdict. Prompts are in
`judge-prompts.md`.

- The gate is pairwise against the approved Talkover reference (`projects/talkover-launch/review/strip-wide.png`
  and `strip-tall.png`), both orders, a fresh judge per order. pair-1 shows agent-brain as X; pair-2 shows Talkover
  as X. The agent-brain film should win both orders.
- The absolute rubric (14 items, overall 1 to 10) is advisory.
- At most 5 judged rounds. Fixes target what more than one judge raised.

## Round 1 (r1)

Self-review before judging (not judged): the opener was blank in HyperFrames renders (a timeline `set` at t=0 is
dropped by HyperFrames' seek, so the first card stayed at opacity 0; the first card is now visible in its own CSS);
an id and a long path were wrapped mid-token in 9:16; the cite card lost its accent across a wrap; a stray glyph
showed at each cut (title words started 0.12 s late); titles of 6 words were cut to at most 5 (a lesson passed on
from the crewboard film's judges).

Deterministic: 25/25 PASS.

Pairwise against Talkover: **lost both orders** (pair-1: Y = Talkover; pair-2: X = Talkover).
Rubric: **6/10**, FAIL on 12 (9:16 card near the edge, bottom third empty), 13 (dark card on dark ground, no tilt
or rim light), 14 (same flat card layout every shot).

| Raised by | Finding | Change for r2 |
|---|---|---|
| both pairwise, rubric | Each beat is a whole card of text; push in on the one line that proves the title | Commands filtered to their proof (`jq '.tasks[0].evidence_changed'` prints `false` / `true`; `jq -r` prints `9: Fixed: ...`; `grep -o "Project handoffs: ..."`), one card per proof, cards sized to their output |
| both pairwise | The blurred opener reads as an intro card | Opener is a real card, sharp, showing the cold start (`Project handoffs: 0 active task(s)`, captured before any handoff) |
| both pairwise | The 5-line refusal cannot be read in the hold | Error lines kept, the how-to-fix lines dimmed |
| pair-1, rubric | Card never feels lit or separated; flat | Lighter surface, rim highlight, deeper shadow, a light behind each card; held camera angles on three shots |
| pair-2, rubric | Card small, off-centre, right half empty | Cards centred in the free part of the frame |

## Round 2 (r2)

Deterministic: 25/25 PASS after two fixes (GIF over 8 MB with the new glow: the GIF now steps down to 10 fps and
96 colours; the `$` prompt and line numbers failed WCAG AA contrast, now lighter).

Pairwise: **lost both orders** again. Rubric: **6/10**, FAIL on 3 (route card small, nothing singled out) and 14
(same layout every shot, reads as a template).

| Raised by | Finding | Change for r3 |
|---|---|---|
| all three | Same slide every shot: same scale, same glow, same title slot | Every shot pushes hard onto its proof rows (they end at up to 82 percent of the frame width), so scale changes shot to shot; titles alternate top and bottom on one left margin |
| both pairwise, rubric | Push onto the proving line, not the whole card | Camera ends on the proof rows; every other row goes out of focus (dim and blurred, a depth-of-field pull, real text still there); rows that would pass under a title scroll out of the shot |
| pair-1 | jq/grep scaffolding is noise | Commands stay (they are what printed the output) but sit out of focus wherever they are not the proof |
| pair-2, rubric | The coloured glow is decoration, a muddy brown halo | Light is neutral and cooler, weaker; it warms only when evidence_changed turns true |
| both pairwise | The refusal still reads as a paragraph | Only the error line is in focus |

## Round 3 (r3)

Deterministic: 24/25 on the first run (`hyperframes check --strict` wide: a runtime failure at t=0 while another
job loaded the machine); re-run alone: lint 0/0 and check ok on both formats. GIF needed 10 fps and 64 colours.

Pairwise: **lost both orders** a third time. Rubric: **6/10**, FAIL on 8 (orange bloom), 12 (9:16 card bleeds,
command cut at the right edge), 13 (opener small and flat), 14 (template).

| Raised by | Finding | Change for r4 |
|---|---|---|
| both pairwise (and pair-1 in r2) | The heroes are test-harness pipes (`grep -o`, `jq`, `echo >>`), not the product | Only the README's own commands, unfiltered (`brain startup`, `brain route`, `brain handoff`, `brain current`). Each card is a window onto the real output (consecutive rows, the running command in the title bar when its prompt has scrolled away); the stored handoff file and NOTES.md (before and after the change) as editor windows |
| all three | One readable payoff per shot at full contrast; the rest reads murky | The proof rows are sharp and carry a tinted band with an accent rule (blue for what it answers, orange for evidence); the rest is softer focus, lighter than r3 (38 percent, 1.3 px) |
| pair-2, rubric | The window chrome drops out; framing breaks | Every shot keeps its window in frame on the title's side; 9:16 never bleeds off the sides |
| rubric (r2, r3) | Orange halo fights the palette | The light is neutral; it warms only for evidence_changed true |
| self (r4 build) | Windows onto unfiltered output need a stronger gate | `checks.py` provenance rewritten: every card row must equal a consecutive row of the display wrap of the captured output, and that wrap must re-join to the printed text exactly; a tampered row fails it (tested) |

## Round 4 (r4)

Deterministic: 20/25 on the run that produced the judged strips. Failures: `hyperframes lint` and `check --strict`
both formats (`composition_heavy_overlay_count_high`: nine cards stacked at opacity 0; a runtime failure under
machine load), one WCAG AA failure (a line number on the blue band in 9:16), GIF 9.04 MB. Fixed before r5: cards
are `display: none` until their shot, line numbers take the band colour, the GIF steps further down (to 8 fps / 48
colours if needed). The judged pixels were unaffected by these fixes.

Pairwise: **lost both orders** a fourth time. Rubric: **6/10**, FAIL on 8 (orange glow carried into the blue shot;
the error line in the evidence colour), 13 (opener flat, dark on dark), 14 (dim, same layout; title jumps between
top and bottom).

| Raised by | Finding | Change for r5 |
|---|---|---|
| all three | Raw local work paths (`C:\video-studio-work\runs\agent-brain-film\tour\...`) read as a leaked dev machine | The tour now runs where a developer would clone it, `C:\code\agent-brain` (removed again after the capture), so the paths the tool prints are short and ordinary |
| pair-1, rubric | Crops start or end mid-line, mid-path | Every terminal window now shows whole output lines only (from a line start to a line end) |
| rubric | Title jumps between top and bottom | Every 16:9 title on the top-left margin |
| rubric | Orange where it is not evidence; glow carrying across a cut | The refusal is on a blue band with no orange; the light changes on the cut, not across it |
| rubric | Scene too dark; window not separated; unfocused lines too faint | Lifted background gradient and key light, brighter window surface, out-of-focus rows at 50 percent and 1 px |
| pair-2 | 9:16 text too small | 9:16 windows at 28 columns (larger type); the long `current` JSON runs full width and off the bottom of the frame |

## Round 5 (r5) - fifth and last judged round

Deterministic: 21/25 on the judged build. `hyperframes lint` and `check --strict` failed on both formats with one
warning, `composition_heavy_overlay_count_high` (86 elements carrying blur: every out-of-focus row had its own
filter). The GIF needed 8 fps and 48 colours (7.74 MB). Everything else passed: provenance, privacy, copy lint,
beats, holds, ffprobe, black, freeze, silence, -15.9 LUFS / -1.8 dBTP, blank frames.

Pairwise: **lost both orders** a fifth time. Rubric: **6/10**, FAIL on 8 (orange spill around the evidence_changed
window) and 14 (same dim window under a top-left title in every shot; reads as a template).

What every pairwise judge said, in all five rounds: Talkover's panel shows the product working without reading (the
orb's colour is the state; the caption line is the conversation), while this film asks the viewer to read code to
see each claim. Its own push-ins and highlight bands were noted as tidy, and the absolute rubric moved from 3 to 2
failed items, but the pairwise verdict never moved.

After the cap (not judged again; deterministic gates only): the out-of-focus rows are grouped into one blurred layer
per run of rows (lint 0/0), and the delivered cut was re-rendered from that build.

| Raised by | Finding | Not done (cap reached) |
|---|---|---|
| both pairwise | Crop hard to the two or three lines that prove each title, set large; no raw JSON walls | Tighter windows (one or two whole lines) conflict with r4's "whole lines, no fragments"; the JSON output of `route` and `current` is one long line |
| pair-1, rubric | Vary scale and framing shot to shot; the film is one composition repeated | Not attempted |
| rubric (r2 to r5) | Orange spill behind the evidence_changed window | The warm light on that shot should go |
| rubric | 9:16 lower half empty | Not attempted |

## Verdict

The film did not beat the Talkover reference pairwise in any of the five judged rounds (0 of 10 orders). By the
rulebook a film that loses pairwise is dropped, not shipped. It is delivered only so Vyas can judge it; nothing was
committed, pushed or posted, and `C:\Dev\agent-brain` was not modified (the tour ran in throwaway copies).

What the five rounds show:
- The pairwise judges were stable and agreed on one cause: a text-output product loses to a product whose state is a
  colour. Better lighting, focus and framing moved the absolute rubric (FAIL items 3, 2, 4, 3, 2) but not the pair.
- Two judge demands pulled against each other across rounds: r3 judges rejected filtered commands (`jq`, `grep -o`)
  as test-harness plumbing; r4 judges rejected the unfiltered output for its long local paths and mid-line crops.
  r5 ran the tour from an ordinary clone path and showed whole lines; the judges then asked for tighter crops.
- Deterministic gates caught what judges never mention: a blank opener (HyperFrames drops timeline sets at t=0), a
  GIF over 8 MB, WCAG contrast on a prompt glyph, and HyperFrames' blur-count warning.
- A visual subject the viewer understands without reading (for example the README's own how-it-works diagram, or a
  file visibly changing next to the flag flipping) is the likely missing piece; it was not tried within the cap.

## Delivered cut (final, not judged)

Deterministic: **25/25 PASS** (`checks.jsonl` round `final`): storyboard, beats, holds, 42-character lines,
provenance (every row a consecutive row of the captured output), no personal data, copy lint, `hyperframes lint`
0/0 and `check --strict` ok on both formats, ffprobe 1920x1080 and 1080x1920 at 30 fps 20.5 s with audio, no
undeclared black or freeze (the only freeze is the end-card hold), no silence, -15.9 LUFS / -1.8 dBTP, GIF 7.98 MB
at 960 px (8 fps, 48 colours), no blank beat frames. Its strips are copied to `review/strip-wide.png` and
`strip-tall.png`.
