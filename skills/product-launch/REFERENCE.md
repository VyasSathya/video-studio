# Approved reference: the Talkover launch film

Approved by Vyas on 2026-10-17 after watching the 16:9, 9:16 and GIF cuts. His words: "Holy shit, this is
amazing ... This is so good" and, asked whether to write anything down to keep this quality, "Yeah, I mean, you
do do whatever you need. I mean, this is so fantastic."

This is the bar. Every new launch film is judged pairwise against it (both orders, a fresh judge each order,
`verify.packet_pair`): the new film must be at least as good. A new product's own films become its references
once he approves them.

- Source, re-renders from the repo: `projects/talkover-launch` (render.py; storyboard.py is the single source of
  the shot list; checks.py runs the deterministic gates; CREDITS.md lists every picture and sound and its licence).
- Frames for the pairwise judge: `projects/talkover-launch/review/strip-wide.png` and `strip-tall.png`.
- How it was reached: `projects/talkover-launch/review/REVIEW-LOG.md` (7 rounds; it lost the absolute rubric with
  fresh judges and won pairwise 8 of 8 against the old README GIF).

What the film does (our description, not his words):
- the product's real UI is the hero and fills the frame: Talkover's floating panel, drawn by its own
  `voice_panel.py` at 10x and lit like an object, not a screen recording in a window
- the story is the product's states, in order: listening (teal orb), it types what you say, it talks back
  (orange), "wait" stops it, it picks up where you cut in, fully local, end card
- the state colours carry the story, and the room light takes about a third of the orb's colour as it changes
- one short sentence per shot ("Always listening." "It talks back." "Say "wait." It stops."), sentence case with
  a period, one left margin in 16:9, sometimes a small second line ("Into Claude Code.")
- the camera does the work: an opening that settles from perspective, close-ups that push in on the orb and the
  buttons, frame edges never cutting through a control, a blurred out-of-focus shot under "Fully local."
- the panel's own captions are the evidence: real lines from the demo session ("You: Hey Claude, what does the
  install script do?", Claude's reply chunks), each held at least 1.4 s
- no voice: a score made locally at 120 bpm that stops when the reading is cut off and comes back with the answer
- an end card with the name, one line ("Hands-free, two-way voice for Claude Code.") and the repo, about 2.3 s
- about 20 s; GIF of the feature section at 960 px under 8 MB
