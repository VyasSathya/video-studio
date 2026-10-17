---
name: whiteboard
description: Hand-drawn whiteboard explainer over a talk: full-screen board takeovers where strokes draw themselves and words are hand-lettered, and half-screen boards beside the speaker. Use when asked for a whiteboard, sketch or drawn explainer style.
---

# Whiteboard explainer

Run the five steps in skills/edit-video, with `styles.build(..., style="whiteboard")`.

- Board: warm paper (#f7f5ef) with a faint dot grid; ink #1d1d22; one accent for underlines, circles and ticks.
- Takeover beats (`takeover`, `draw`): the speaker fades out, the board fills the frame; a drawing (rough paths
  made in `styles.py`: clock, planet, star burst, chosen from what the brief says to draw) draws itself stroke by
  stroke, then the words are hand-lettered (Caveat, written left to right) with a drawn underline. Not in the last
  1.5 s: a film ends on the speaker (`beats.place` turns a late takeover into a side beat).
- Side beats (`number`, `bullets`, `card`, `image`): the speaker moves to the left half, the board on the right
  shows a circled number, ticked hand-written bullets, a drawing with a word, or a taped photo (public domain).
- Order: the layout moves first (0.55 s), then strokes draw, then words write; the board empties before the
  speaker comes back.
- Brief in plain words, e.g. "When he says spending a year in space, take over the screen and draw a clock with
  the words 'A year in space'." Sample: `projects/style-samples` (whiteboard).
