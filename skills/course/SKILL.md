---
name: course
description: Course or lesson style over a talk: the speaker full screen, then a rounded crop beside big, short takeaways (a number, bullets, a key idea, a picture) on liquid-glass cards. Use when asked for a course, tutorial, lesson or "takeaways" style.
---

# Course style

Run the five steps in skills/edit-video, with `styles.build(..., style="course")`.

- Default: the speaker full frame. For each beat the speaker glides (0.55 s, ease in-out) into a rounded crop on
  the left (44 percent wide, radius 28, deep soft shadow) and the takeaway builds on the right.
- Takeaways stay short: a number ("1 year"), 2 or 3 bullets of 1 to 3 words, a key idea of at most 6 words, or a
  public-domain picture whose file title names what was asked for (`stock.find` checks it).
- Takeovers shrink the speaker to a corner card and give the key idea the frame.
- Ground: a dark field lit with the accent; cards are liquid glass (translucent, blurred backdrop, light top
  edge) so text reads over anything.
- The card leaves before the speaker returns; the film ends on the speaker.
Sample: `projects/style-samples` (course).
