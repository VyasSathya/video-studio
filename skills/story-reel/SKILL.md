---
name: story-reel
description: Point at a folder of recordings and get one story reel - find the best moments across all of them, order them into a beginning, middle and end, cut and caption. Use when asked to make a story, recap or highlight reel from many clips.
---

# Story from a folder

`python -m studio story DIR --credit "..."` (studio/storyreel.py).

- Every recording is transcribed once (cached); sentence-aligned moments of 12 to 35 s are scored in small
  batches by the text model, which sees only each moment's own words (so titles stay true).
- The model orders 3 to 5 moments into a story; an agent can write `story.json` itself instead.
- Each moment keeps the speaker's exact words: dead air, fillers and stutters are cut (studio.edit), nothing is
  rewritten; moments join with straight cuts; captions are the transcript.
- Never use recordings of real people who did not agree to be filmed for this; never mix a person's words from
  different moments into a sentence they did not say.
Sample: `projects/story-sample` (a public-domain NASA event split into four recordings).
