# Judge prompts (sent verbatim to fresh Opus subagents; they see nothing else)

Each judge is a new subagent (model opus) per round and per order. It gets a folder path and nothing else: no plan,
no log, no earlier verdict, no word about which film is the reference.

## Pairwise judge (run twice per round, fresh agent each time, order swapped)

Read only the files in <packet> (X-1.png and X-2.png are film X, 16:9 then 9:16; Y-1.png and Y-2.png are film Y;
brief.txt; rubric.md). Do not open any other file or folder. Be strict, a professional motion designer reviewing
for a client. Which film would a design-literate viewer judge as more professional, studio-made, and clearer about
what its product does? Judge the craft of the film, not which product you prefer. Answer "X" or "Y" on the first
line, then up to five short reasons, each naming a frame (film and time). Then list the three most important
changes that would improve the film you did not pick, and the three for the one you picked. Plain ASCII only.

## Rubric judge (advisory, one fresh agent per round)

Read only the files in <packet> (frames-1.png is the 16:9 strip, frames-2.png the 9:16 strip, one frame every
0.5 s with the time on each tile; brief.txt; rubric.md). Do not open any other file or folder. Be strict, a
professional motion designer reviewing for a client. Answer in the rubric's reply format. Plain ASCII only.
