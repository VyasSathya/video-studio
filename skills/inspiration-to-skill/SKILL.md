---
name: inspiration-to-skill
description: Turn a video you like into a reusable style skill - measure why it works, write that into a skill, run it, and fold feedback into the skill after every run. Use when someone shares a reference video and says "make ours like this", or wants a new style.
---

# Inspiration to skill

1. Gather references: 1 to 6 videos in the style, from their makers' own official pages. They are for
   measuring only: never reuse their footage, music, branding or words, and delete the files after measuring.
2. Measure: `python -m studio inspire ref.mp4` writes study.json (shot lengths, tempo and how many cuts land on
   beats, palette, dark share, motion, busyness) and two contact sheets (one frame a second; the frame after
   each cut). Look at the sheets and write down what the numbers cannot show: framing, depth, camera moves,
   transitions, type (size as a share of frame height, words per title, hold), cursor, end card, voice or not.
3. Write the skill: `skills/<name>/SKILL.md` with numbered, measurable rules (seconds, percentages, easings)
   and a "Where these numbers come from" section naming the references and where they disagree with our own
   rules (our rules win: real product only, no invented UI, no generated people, one motion at a time).
   Add `rubric.md`: yes/no items a blind judge can check from frames alone.
4. Run it on real material, with the loop in skills/edit-video step 5 and a blind judge at the end.
5. Fold feedback in: after every run, add the lessons to the skill's "Feedback folded in" list (what broke, the
   rule that fixes it) and, when a fix is mechanical, a check in code. A rule changes only with evidence: a
   judge finding that recurs, or the owner's reaction.

The worked example is skills/product-launch: made from six official launch films (Linear, Framer, Arc,
Raycast, Apple) and refined over five blind-judge rounds on the crewboard film.
