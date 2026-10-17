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

| [`projects/raw-edit-sample`](projects/raw-edit-sample) | 16:9 and 9:16 cuts of a live, unedited talk | `rawcut`: dead air, stutters, restarts and retakes cut; face-aware 9:16 reframe; word captions, name tag, callouts |
| [`projects/short-sample`](projects/short-sample) | 25 s narrated vertical short | `short`: a local model writes the script from a facts file, every beat checked against it; Kokoro, public-domain stills, local music bed |
| [`projects/repurpose-sample`](projects/repurpose-sample) | 3 vertical clips, a LinkedIn post, an X thread, carousel slides | `repurpose`: candidate windows scored by a local model, clips cut and captioned, drafts written from the transcript |

Synthetic voices are labeled as synthetic in every video that uses them. The last three samples use a
public-domain NASA event (Scott Kelly's year in space) from Wikimedia Commons, fetched on first run.

## Three pipelines, no human step

Every run writes its work to `D:\video-studio-work\runs\<run>` (or `STUDIO_WORK`), a `manifest.json` of what
was made and decided, and a `review.html` to look at before anything is used. Nothing here posts anywhere;
posting is a separate pipeline with its own approval queue.

```powershell
python -m studio rawcut take.mp4 --name "Your Name" --role "Your role" --credit "Footage: ..."
python -m studio short --topic "How the ISS stays in orbit" --facts notes.txt --seconds 40
python -m studio repurpose talk.mp4 --clips 3
python -m studio cost                     # what the paid options would cost for one 30 s short
```

**Raw footage** (`studio/rawcut.py`). Verbatim word-level transcript, then a cut plan (`studio/edit.py`):
dead air from word gaps and from the audio itself, fillers, stutters ("different, different kind") but not
emphasis ("really, really long"), restarts, and retakes said again after a pause. The plan is drawn on the
source waveform and filmstrip (`timeline.png`) and listed cut by cut in the review page. One ffmpeg pass
applies it with 30 ms fades at every splice. For 9:16, each shot is either cropped on the speaker's face or
fitted over a blurred copy of itself. A text model suggests the title and callouts; a callout is only kept
if its words were said, at the moment they were said.

**Short-form** (`studio/shortform.py`). From a topic and a facts file a text model writes beats (narration
plus a visual: title, kinetic text, stat, list, or a public-domain still). Each beat must quote the facts,
every number must be in its quote, and narration is a third-person narrator; beats that fail are dropped and
the script is regenerated. Kokoro narrates, Whisper times the words, captions spell the script's words, a
music bed is synthesised locally (`studio/music.py`) and ducked under the voice.

**Repurposing** (`studio/repurpose.py`). One transcript; sentence-aligned candidate windows of 20 to 55 s
are scored in small batches (the model only sees each window's own words, so titles stay true), the best
non-overlapping ones are cut, cleaned, reframed and captioned. Drafts for LinkedIn, X and a 4:5 carousel
are written from the transcript and the slides rendered to PNG.

Every render goes through `studio/qc.py`: -14 LUFS and -1 dBTP (two-pass loudnorm), speaking pace, black
frames, size. The text model is `claude -p` when signed in, else `ANTHROPIC_API_KEY`, else local Ollama
(`mistral-nemo` by default); see `studio/llm.py`.

Paid generation (HeyGen avatars, ElevenLabs voice and music, Kling, Veo and Seedance via fal) is wired in
`studio/paid.py` and never spends on its own: [docs/PAID.md](docs/PAID.md) has each option, its price and
what it adds. Ideas borrowed from video-use, herk-edit-kit, claude-code-video-toolkit and OpenShorts are
credited in [THIRD_PARTY.md](THIRD_PARTY.md).

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
| `studio/edit.py`, `reframe.py`, `overlay.py` | cut planning and applying, 9:16 reframing, captions and motion graphics over footage |
| `studio/picks.py`, `llm.py` | judgment steps (callouts, clips, drafts), always checked against the transcript |
| `studio/shortform.py`, `stock.py`, `music.py` | scripted shorts, public-domain stills, a local music bed |
| `studio/repurpose.py`, `review.py`, `qc.py`, `timeline.py` | long-to-short, review pages, render checks, the cut timeline |
| `studio/paid.py` | dry-run-by-default adapters for HeyGen, ElevenLabs and fal |
| `python -m studio ...` | the same as commands: `health`, `tts`, `stt`, `render`, `gif`, `frames`, `sheet`, `rawcut`, `short`, `repurpose`, `review`, `cost` |

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
- The local text model (a 12B model in Ollama) picks and writes adequately, not brilliantly; the checks
  stop it inventing, but they cannot make it witty. With Claude signed in, `studio/llm.py` uses it instead.
- Whisper tends to drop "um" and "uh"; a verbatim prompt keeps most of them, but filler detection is only as
  good as the transcript.
- 9:16 crops of 720p sources are upscaled and soft. Face finding is OpenCV's stock cascade, one crop per shot.
- A two-minute 1080p render with footage takes about 10 minutes per aspect on this machine (HyperFrames
  seeks the footage frame by frame); a 25 s short takes about 2.

## License

MIT. HyperFrames is Apache-2.0; ffmpeg builds in `tools\` are GPL and are not redistributed here.
