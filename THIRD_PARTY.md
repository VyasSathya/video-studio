# Third-party code and ideas

Used as dependencies (not copied into this repo):
- HyperFrames, Apache-2.0, HeyGen: https://github.com/heygen-com/hyperframes (npm, pinned in package.json).
  Telemetry is turned off for every call this repo makes (HYPERFRAMES_NO_TELEMETRY=1, DO_NOT_TRACK=1).
- GSAP, loaded from jsDelivr inside compositions: https://gsap.com (standard no-charge licence).
- puppeteer-core, Apache-2.0. Pillow, numpy, OpenCV (Apache-2.0, the stock Haar face cascade).
- ffmpeg (GPL build from BtbN/FFmpeg-Builds), downloaded by setup.ps1, not redistributed.
- Kokoro-FastAPI and speaches (Whisper) run as local servers; Ollama for the local text model.

- Fonts from Fontsource (npm): Geist and Geist Mono (SIL Open Font License, The Geist Project Authors), Caveat
  (SIL Open Font License); embedded into compositions as woff2.
- Sound effects: the set bundled with HyperFrames media-use, from Pixabay under the Pixabay Content License (free
  use in rendered videos, no attribution required; not redistributed by this repo as files).

Ideas we re-implemented in our own code (no code copied), with thanks:
- video-use, MIT, Copyright (c) 2026 Browser Use (https://github.com/browser-use/video-use): verbatim
  word-level transcripts for editing, 30 ms fades at every splice, and the filmstrip-over-waveform view of an
  edit (studio/timeline.py).
- herk-edit-kit, MIT, Copyright (c) 2026 Nate Herk (https://github.com/nateherkai/herk-edit-kit): a
  deterministic silence pass followed by a mistake pass, and retakes found by word-set (Jaccard) similarity
  (studio/edit.py retakes()).
- claude-code-video-toolkit, MIT, Copyright (c) 2024 Digital Samba
  (https://github.com/digitalsamba/claude-code-video-toolkit): QC targets of -14 LUFS and -1 dBTP and a
  speaking-pace check (studio/qc.py); captions that spell what the script says, timed by the recogniser
  (studio/shortform.py _align()).
- OpenShorts, MIT, Copyright (c) 2024 OpenShorts (https://github.com/mutonby/openshorts): scoring
  sentence-aligned candidate windows with a text model and snapping clips to real word boundaries
  (studio/picks.py clips()). Its main app is not used (it depends on AGPL-3.0 ultralytics).

- Product launch rules (skills/product-launch): measured from six official launch films (Linear, Framer, The
  Browser Company, Raycast, Apple) for reference only; their files were deleted after measuring and nothing of
  theirs (footage, music, branding, words) is used.

Optional, not included (need an account): Nate Herk's free HyperFrames skills and Scrollcraft are behind his
Skool community and an email opt-in; the owner can add them by hand.

Not used: Remotion (source-available, company licence above three people), Blotato's skills (no licence),
voice or avatar clones of anyone.

Sample media (fetched on first run, never committed): NASA video and photos, public domain, via Wikimedia
Commons; each file's page and credit is recorded in the run's manifest.json.
