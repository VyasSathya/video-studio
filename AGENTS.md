# Rules for agents making videos here

- Real over mocked. Use the product's own code, demo data and real command output. If a part cannot run for
  real (a live mic, a login), compose it from the real pieces and say so on screen and in the README.
- Never put words in a real person's mouth. A synthetic voice is labeled synthetic in the video itself and in
  any README that shows it. Never present a synthetic voice as the project's author.
- Model-written words are checked before they are used: narration is a third-person narrator, every scripted
  beat quotes its facts and every number is in that quote, every callout or title shown over footage uses only
  words said at that moment, every clip boundary is a real sentence boundary. What fails is dropped, never
  "fixed" by hand into a claim nobody made.
- Footage edits keep what the speaker said: cut silence, fillers, stutters, restarts and retakes, never words
  that change the meaning. Every cut is listed in the run's manifest and review page.
- Nothing is posted from here. Output goes to the run folder and its review page; posting is a separate
  pipeline with an approval queue.
- Paid adapters (studio/paid.py) stay dry runs unless the owner has said yes to that spend.
- Do not edit captured output. Filter it in the command you show (e.g. `| select a, b`) instead.
- No personal data in frames or files: no home-folder paths, user names, emails, real chats or private work.
  Run a demo from example data or a throwaway copy; check the frames before shipping.
- Look at your own output before anyone else does: snapshot the composition, read a contact sheet of the
  render, pull full-size frames at the key moments, and transcribe the final audio once.
- Design floor: one sans (Inter) plus one mono (JetBrains Mono), neutral palette with one or two accents,
  hairline borders, no banner text or legends, contrast that passes `npx hyperframes validate`.
- Sizes: GIF under 8 MB at 960 to 1000 px wide; mp4 1080p H.264 with `+faststart`, shipped as a release asset.
- Keep each video reproducible: one `render.py` per project that goes from its inputs to `out/`.
- Downloads beyond npm, pip and GitHub releases of well-known projects need the owner's OK first.
