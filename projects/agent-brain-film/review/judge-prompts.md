# Judge prompts (sent verbatim to fresh Opus subagents; they see nothing else)

Each judge gets a packet folder under C:\video-studio-work\runs\agent-brain-film\review\judge\<round>\ holding only
frame strips, a brief and the rubric. Never this log, the plan, the storyboard or a checker verdict.

## Pairwise judge (the gate; run twice per round, a fresh agent per order)

You are judging two short product-launch films from frame strips only. Read every file in <packet> and nothing
else: X-1.png and X-2.png are film X (16:9 strip, then 9:16 strip), Y-1.png and Y-2.png are film Y, brief.txt says
what they are and asks the question, rubric.md lists what a good launch film does. Do not open any other file or
folder. Be strict: a professional motion designer reviewing for a client. Answer X or Y on the first line, then three
reasons, each with a frame time and which film, then the single most important thing the losing film should change
and the single most important thing the winning film should change. Plain ASCII only.

## Absolute rubric judge (advisory; one fresh agent per round)

You are judging a short product-launch film from frame strips only. Read every file in <packet> and nothing else:
frames-1.png (16:9 strip, one frame every 0.5 s, time on each tile), frames-2.png (9:16 strip, same beats),
brief.txt (what it was supposed to be) and rubric.md. Do not open any other file or folder. Be strict: a
professional motion designer reviewing for a client. Follow the reply format in rubric.md exactly. Plain ASCII only.
