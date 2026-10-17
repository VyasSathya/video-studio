# Credits and sources: Talkover launch film

Every picture, sound and word in the film, where it came from, and the licence on file.

## Picture

| Element | Source | Licence |
|---|---|---|
| The floating panel (orb, buttons, caption line) | Drawn frame by frame by Talkover's own `src/voice_panel.py` (repo HEAD eb5429f), unchanged, offscreen with a virtual clock (`panel_render.py`) at 10x scale | MIT (Talkover) |
| Panel caption text, "You:" lines | What Whisper heard from the earlier demo's synthetic "you" audio (`video-studio/projects/talkover-demo/session.json`) | own work |
| Panel caption text, Claude lines | Chunks of the real reply a Claude Code agent (Opus 5.5) wrote in a throwaway copy of the talkover repo, split by Talkover's Split-Chunks. Chunks c1_1, c1_2, c2_1 are skipped and waits are shortened | own work |
| Engine lines (whisper / kokoro, 127.0.0.1:2022 / :8880) | Default ports and service comments in `talkover/docker-compose.yml` | MIT (Talkover) |
| Type, backdrop, camera | Written in `build.py`, rendered by HyperFrames 0.8.167 | Apache-2.0 (HyperFrames) |
| Fonts | Inter and JetBrains Mono, embedded by HyperFrames | SIL OFL 1.1 |
| Animation runtime | GSAP 3.14.2 (jsDelivr) | GSAP standard licence (free, including commercial use) |

No stock footage, no generated images, no people.

## Sound

| Element | Source | Licence |
|---|---|---|
| Score (pad, kick, bass pulse, hats, plucked arpeggio, end bell, reverb) | Synthesized from scratch by `music.py` (numpy + scipy oscillators, noise and filters). No samples, loops or third-party audio | own work |
| Loudness | ffmpeg `loudnorm`, two pass, -16 LUFS integrated, -1.5 dBTP (measured -15.8 LUFS) | n/a |

No voiceover. The "you" and Claude voices of the earlier demo are not in this film; their audio was used only to
drive the panel's mic and speaking levels.
