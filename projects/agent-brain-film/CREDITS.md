# Credits and sources: agent-brain launch film

Every picture, sound and word in the film, where it came from, and the licence on file.

## Picture

| Element | Source | Licence |
|---|---|---|
| Terminal windows (commands and what they printed) | The agent-brain README tour, run for real by `capture.py` in a throwaway copy of the committed tree (`git archive` of agent-brain HEAD 4da9843, extracted to `C:\video-studio-work\runs\agent-brain-film\tour\agent-brain`) against its own `examples/` folder, bash with the README alias `brain`, the README's own commands with no filters. Saved verbatim in `data/session.json`. Each window shows consecutive rows of one output, with the running command in its title bar once the prompt has scrolled out of view | MIT (agent-brain) |
| Editor windows | The handoff file the tool wrote (`examples/tiny-brain/handoffs/todo-api/<id>.json`, lines 20 to 26) and `examples/todo-api/NOTES.md` as it was when the handoff was saved (lines 7 to 10, line 9 cited) and after one line was appended (lines 7 to 11), read by `capture.py` into `data/files.json` | MIT (agent-brain) |
| Display wrapping | Long lines soft-wrapped at spaces (a long path at the column) to the window width, and a tab shown as spaces to the next 8-column stop, as a terminal or editor does; the handoff file in 16:9 is not wrapped, so its long path line runs past the window edge. No character added, dropped or retyped: `checks.py` requires every row to equal a consecutive row of the wrapped capture, and the wrap to re-join to the printed text exactly | n/a |
| Focus | The rows that prove each title are sharp, on a tinted band; the rest of the window is out of focus (38 percent, 1.3 px blur). The absolute paths the tool prints (they name only the throwaway copy) sit in those out-of-focus rows | n/a |
| Colours | agent-brain's own diagram tokens (`docs/how-it-works-dark.png`, from `projects/agent-brain-diagram/diagram.html`): bg #0d0d10, card #141418, hairline #27272d, text #ececf0, muted #9a9aa4, blue #7d9bff, orange #fb923c, highlight #2a1c10 | MIT (agent-brain) |
| Type, cards, light, camera | Written in `build.py`, rendered by HyperFrames 0.8.167 | Apache-2.0 (HyperFrames) |
| Fonts | Inter and JetBrains Mono, embedded by HyperFrames | SIL OFL 1.1 |
| Animation runtime | GSAP 3.14.2 (jsDelivr) | GSAP standard licence (free, including commercial use) |

The handoff id on screen is the random id the tool gave the example handoff in that run. No stock footage, no
generated images, no people, no personal data (no user name, home folder or real project; `checks.py` scans both
compositions for them).

## Sound

| Element | Source | Licence |
|---|---|---|
| Score (pad, kick, refusal thud, bass pulse, hats, plucked arpeggio, bells, reverb) | Synthesized from scratch by `music.py` (numpy + scipy oscillators, noise and filters) at 120 BPM. No samples, loops or third-party audio | own work (made for this film; free to use with it) |
| Loudness | ffmpeg `loudnorm`, two pass, -16 LUFS integrated, -1.5 dBTP (the Talkover reference's target) | n/a |

No voiceover.
