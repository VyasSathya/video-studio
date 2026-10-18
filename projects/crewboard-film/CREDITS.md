# Credits and sources: crewboard launch film

Every picture, sound and word in the film, where it came from, and the licence on file.

## Picture

| Element | Source | Licence |
|---|---|---|
| The page (sessions, agents, task list, session view, Now page) | crewboard's own `web/index.html` and `app.js` (repo HEAD 012fd6b, unchanged, read only), served by `python -m crewboard serve --demo` on a free port and recorded frame by frame at 2x (2880x1800) in headless Chrome by `ui_render.mjs` | MIT (crewboard) |
| Every word and number in the page | crewboard's demo data, `crewboard/examples/progress.json` and `sessions.json` (example tasks and sessions, served from a temp copy) | MIT (crewboard) |
| Page events | Real: two clicks (open the session, open Now), crewboard's own command line run against the demo task list (`python -m crewboard status py313 doing`, what an agent does), two real answer clicks (Yes, No). Dark theme throughout | n/a |
| Capture harness | The page's clock and polling timers are frozen during capture (relative times such as "now" and "25m" would otherwise drift over the minute the capture takes) and every CSS animation (the live pulse) is set to the film time before each screenshot. Nothing else on the page is touched | own work |
| Colours | Read by `build.py` from crewboard's theme in `web/index.html` (oklch tokens converted to sRGB): bg, card, muted, fg, mfg, ring (the studio backdrop), border, pfg; the status dots before the titles and the URL use its doing, waiting and done tokens | MIT (crewboard) |
| Type, backdrop, camera, light | Written in `build.py`, rendered by HyperFrames 0.8.167 | Apache-2.0 (HyperFrames) |
| Fonts | Geist and Geist Mono (crewboard's own fonts), from `@fontsource/geist` and `@fontsource/geist-mono` 5.3.0 | SIL OFL 1.1 |
| Animation runtime | GSAP 3.14.2 (jsDelivr) | GSAP standard licence (free, including commercial use) |
| Terminal lines | `python -m crewboard` (crewboard's README) and the line it prints, `crewboard on http://localhost:7788/` (`cmd_serve` in `crewboard/__main__.py`, default port 7788) | MIT (crewboard) |

No stock footage, no generated images, no people. No personal data: the page shows demo data only (checked by
`checks.py`, privacy gate).

## Sound

| Element | Source | Licence |
|---|---|---|
| Score (pad, kick, bass pulse, hats, plucked arpeggio, event ticks, end boom and bell, reverb) | Synthesized from scratch by `music.py` (numpy and scipy oscillators, noise and filters), 120 BPM. No samples, loops or third-party audio | own work, free to use with the film |
| Loudness | ffmpeg `loudnorm`, two pass, -16 LUFS integrated, -1.5 dBTP target (measured -16.0 LUFS, -2.2 dBTP) | n/a |

No voiceover.
