# Judge prompts (sent verbatim to fresh Opus subagents; they see nothing else)

## Rubric judge

You are judging a short product-launch video from frame strips only. Read three files and nothing else:

- <project>/review/judge-brief.md (what the video was supposed to be)
- <project>/review/judge-rubric.md (15 yes/no items)
- <project>/review/strip-wide.png (16:9 version: one frame at every beat, 0.5 s apart, time on each tile)
- <project>/review/strip-tall.png (9:16 version, same beats)

Do not open any other file or folder. Be strict: a professional motion designer reviewing for a client. For each
rubric item answer YES or NO, give the tile time(s) that decide it, and for every NO say exactly what is wrong and
what change would fix it. End with one line: PASS (all 15 YES) or FAIL (n items NO). Plain ASCII only.

## Pairwise judge (run twice, fresh agent each time, order swapped)

Two candidate launch videos for the same product, Talkover (hands-free two-way voice for Claude Code on Windows).
Each is shown as a strip of frames taken every 0.5 s. Read only these files:

- <project>/review/judge-brief.md
- Video A: <path>
- Video B: <path>

Which video would a design-literate viewer judge as more professional, studio-made, and clearer about what the
product does? Answer "A" or "B" on the first line, then up to five short reasons. Plain ASCII only. Do not open any
other file.
