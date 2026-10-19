# Portfolio landscape films

Local production using the existing video-studio capture, HyperFrames, music, ffmpeg and verification pipeline.
No paid generation or model calls. Working inputs live outside the repository in `PORTFOLIO_FILM_WORK`.
Its `films.json` records real captures, original clips, source provenance, timing and composition. The checked-in
`production-plan.json` is the final task plan and a fallback when that working config is absent. Source media
paths refer to existing local material; source assets and owner downloads are not vendored in this recipe folder.

```
python projects/portfolio-landscape/render.py --film marquee --stills
python projects/portfolio-landscape/render.py --film marquee
```

Each film starts on the product. Landscape has its own composition, typography and camera. Default shots
hold for four seconds; the overview gives each product six seconds. Source recordings remain unchanged.
There is no dialogue. Performance editing requires its own verified source boundaries and is not routed
through this faceless product compositor. File hashes, source times and technical receipts are recorded.
Outputs remain review candidates until visual QA is recorded. Existing approved films are retained.

The production scripts also include:

- `render-kpop.py`: genuine landscape composition from the existing approved SingStan performer assets,
  the real app catalog, and the original local music-video score. It does not demonstrate live karaoke.
- `render-standup.py`: two uninterrupted excerpts from the owner's public performance. The source is an
  unchanged normal YouTube Studio owner download. Camera-follow reframing preserves face and microphone;
  original performance audio is mastered without internal time edits or added audience response.
- `render-overview.py`: readable six-second project chapters from existing landscape films. Gameplay has
  additional time. Stand-up speech is not cut into the montage.
- `render-current-games.py`: continuous current-source bot gameplay, captured by the existing Unity capture
  runner. Hook Wars replaces the duplicate dodgeball chapter; it remains truthfully identified as another mode
  in Brainrot Brawl. Captures are camera presentations, not game changes or phone-performance acceptance.
- `score-overview.py`: original local electric-piano, bass and drum arrangement. Accepts any overview duration.
- `replace-overview-score.py`: masters replacement audio and copies the encoded picture stream unchanged.
  It verifies the picture hash, duration, integrated loudness and true peak after muxing.
- `turntable.py`: Blender inspection render of the original repaired game prop, with no model/game edits.
- `render-launch.py`: earlier interface-camera treatment, retained as production history rather than selected output.

The run directory contains source hashes, exact crop rectangles, pinned public source excerpts, render
manifests, HyperFrames preflight results, encoded technical checks, audio audits and blind review packets.
Source code panels are explicitly historical public-source studies; they are not screenshots of a runtime.
Specific reading holds are declared only after inspecting the source and encoded frames. Moving gameplay
is never exempted wholesale from freeze checks.

Rejected cuts remain outside the website draft while specific visual findings are revised.
Blind contact-sheet reviews establish sampled composition, not audio, continuous motion or joke quality.

## Current portfolio overview

`render-overview.py` now builds all sixteen selected case chapters in 103.4 seconds. Set PORTFOLIO_SITE_ROOT to the reviewed website checkout. `--resume` reuses cached encoded chapters with matching duration; delete a changed chapter before resuming. The video-studio chapter introduces the Talkover input and complete whiteboard output; Mad Balls is explicitly identified as inside Brainrot Brawl. Flower Girls and source-study labels sit below their navigation/content. Technical holds remain specific, never a blanket gameplay exemption. Audio is an original local instrumental score; all source dialogue is excluded from this montage.

The website autoplays the overview muted with native player controls only. Reduced motion keeps manual playback. The current overview run is `overview-native-mic`; its stand-up chapter uses the unchanged original recording at435-440.5s with crop x130,y545,w480,h270 for a closer face/microphone shot. Other chapters retain the prior all-sixteen cut. The separate `standup-after-zipper` run starts at source16s after the zipper joke, then retains source16-81.2s and408-469s without interior speech edits, for126.2s. Older runs remain intact. R1 and R2 review findings are retained; new close framing won both swapped comparisons against the prior chapter. Sampled visual comparisons do not certify continuous motion or subjective owner approval.
