# video-studio

Demo videos and README GIFs that an agent makes end to end: script, capture, compose, captions, render mp4 and
gif, look at its own frames, ship. No step needs a person.

Everything runs locally on Windows: [HyperFrames](https://github.com/heygen-com/hyperframes) (Apache-2.0,
HTML compositions rendered in headless Chrome) for composing, ffmpeg for capture and encoding, headless Chrome
for driving web UIs, Kokoro for voices and Whisper for word-level captions.

## What it made

| Project | Output | How |
|---|---|---|
| [`projects/talkover-demo`](projects/talkover-demo) | 60 s video with sound + 16 s GIF for [Talkover](https://github.com/VyasSathya/talkover) | Talkover's real panel code rendered offscreen, its own chunking and cut-off rules, real Claude Code replies, Kokoro voices, Whisper word times |
| [`projects/session-hub-tour`](projects/session-hub-tour) | 19 s GIF for [session-hub](https://github.com/VyasSathya/session-hub) | the real app in `--demo` mode, clicked through in headless Chrome |
| [`projects/agent-brain-diagram`](projects/agent-brain-diagram) | light and dark PNG for [agent-brain](https://github.com/VyasSathya/agent-brain) | one HTML page, rendered twice |
| [`projects/agent-brain-terminal`](projects/agent-brain-terminal) | 33 s terminal GIF | the README tour run for real, then replayed |

Synthetic voices are labeled as synthetic in every video that uses them.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

That installs the pinned HyperFrames CLI and puppeteer-core from npm, has HyperFrames fetch its headless Chrome,
and puts an ffmpeg build with libx264 in `tools\` (BtbN FFmpeg-Builds from GitHub, checksum checked). Many
Windows ffmpeg installs are LGPL builds without libx264, which HyperFrames needs.

Voices and captions need two OpenAI-compatible speech servers on this machine: Kokoro-FastAPI on port 8880 and
a Whisper server such as speaches on port 2022 (Talkover's `docker-compose.yml` starts both). Point elsewhere
with `STUDIO_TTS_BASE` / `STUDIO_STT_BASE`.

`python -m studio health` says what is there.

## The pieces

| File | Does |
|---|---|
| `studio/engines.py` | `tts(text, wav, voice, speed)` and `stt(wav)` with word timestamps |
| `studio/media.py` | finds ffmpeg, `mix()` timed clips into one track, `gif()` under a size cap, `frames()` and `contact_sheet()` for looking |
| `studio/hf.py` | runs the pinned HyperFrames CLI with this ffmpeg on PATH: `render()`, `snapshot()` |
| `studio/webrec.mjs` | records a scripted walk through a web page (click, type, scroll, with a drawn cursor) from Chrome's screencast |
| `studio/still.mjs` | HTML to PNG, once per color scheme |
| `studio/terminal.py` | a HyperFrames terminal that types real commands and prints their real output |
| `python -m studio ...` | the same as commands: `health`, `tts`, `stt`, `render`, `gif`, `frames`, `sheet` |

Each project has one `render.py` that does the whole thing:

```powershell
python projects\talkover-demo\render.py         # about 4 minutes
python projects\session-hub-tour\render.py      # about 40 seconds
python projects\agent-brain-terminal\render.py  # about 2 minutes
node studio\still.mjs projects\agent-brain-diagram\diagram.html projects\agent-brain-diagram\out\agent-brain.png --width 1600 --height 780 --scale 1.5 --scheme light,dark --sel "#frame"
```

Output lands in each project's `out\` (git-ignored); copy what ships into the target repo.

## Driving it from Claude Code

Open Claude Code in this folder and ask for the video. `AGENTS.md` (imported by `CLAUDE.md`) holds the rules it
follows. The loop that worked for the four projects above:

1. **Find what is real.** Read the target repo first. Prefer the product's own code and data over a mockup:
   session-hub has a `--demo` mode; Talkover's panel draws itself with PIL, so its own code renders the frames.
2. **Script from real output.** Run the commands, ask the real agent, transcribe the real audio. Save it as
   `session.json` and never edit what it says. Shorten waits if you must, and say so on screen.
3. **Compose in HTML.** One HyperFrames `index.html` per video, written by a `build.py` from the session data.
   GSAP timeline, Inter and JetBrains Mono (HyperFrames embeds both; name fonts with `font-family`, not the
   `font` shorthand, or they fall back).
4. **Check before rendering.** `npx hyperframes validate` (contrast and JS errors) and
   `npx hyperframes snapshot --at 1,5,9 --no-end` give stills in seconds.
5. **Render, then look.** `render.py`, then `python -m studio sheet out\x.mp4 sheet.png` and read the sheet;
   pull full-size frames at the moments that matter. Transcribe the final audio once to check it lines up.
6. **Ship small.** GIFs under 8 MB (`gif()` steps the size down until they fit), the full mp4 as a release
   asset. Scan frames and files for paths, names and private text before pushing.

HyperFrames also ships its own agent skills (`npx hyperframes skills`); they are bundled in
`node_modules/hyperframes/dist/skills` and worth reading for anything beyond these patterns.

## Limits

- Windows-first: paths, the ffmpeg download and the Talkover panel renderer assume Windows.
- The Talkover demo is composed from real parts, not a screen recording of the live loop: playing audio through
  the speakers on a machine whose own always-on mic is listening would feed the demo into a real session.
- Text in GIFs is only as readable as the GIF width allows; 960 to 1000 px wide is the floor used here.

## License

MIT. HyperFrames is Apache-2.0; ffmpeg builds in `tools\` are GPL and are not redistributed here.
