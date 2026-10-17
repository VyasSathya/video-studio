---
name: gather-assets
description: Collect what an edit needs - stills of real sites, scripted screen recordings, public-domain B-roll, and (paid, gated) AI image-to-video accent clips - with the source and licence of each. Use before composing any video that needs visuals beyond the footage.
---

# Gather assets

`assets.gather(specs, out_dir)` writes the files and `assets.json` (source and licence per asset).

Free first, in this order:
1. The real product: `capture.mjs` stills (2x, with where each feature sits from the DOM) and `webrec.mjs`
   scripted recordings (click, type, scroll, drawn cursor). A missing screen is captured or asked for, never drawn.
2. Public-domain or CC0 stills from Wikimedia Commons (`stock.find`): the file's own title must name the subject;
   the credit goes on screen or on the end card.
3. Sound: `studio/sound.py` (bundled Pixabay effects), `studio/music.py` (made here). The research for more free
   sources (Commons CC0 audio, Kenney CC0 packs, OpenGameArt CC0, Freesound CC0 with a free key) is in the work
   folder notes; wire one only with its licence recorded per file.
Paid, behind the spend gate (key + `STUDIO_ALLOW_SPEND=1` + `confirm: true`; prices in docs/PAID.md):
4. AI image-to-video (`ai_clip`: Kling 3.0 through kie.ai, about $0.45 per 5 s silent clip; fal as the
   alternative). Accent shots only: no people, hands, faces or text, never a shot that makes a product claim,
   graded to match the real footage.
