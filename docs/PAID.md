# Paid options (wired, not used)

Everything in the samples runs free on this machine. These adapters (`studio/paid.py`) add what local tools
cannot do. Each call is a dry run that prints the exact request and its cost until the provider key is set,
`STUDIO_ALLOW_SPEND=1` is set, and the call passes `confirm=True`. `python -m studio cost` prints the table
below for any length.

Prices read from the official pages on 2026-10-17. One short = 30 s, 9:16, about 450 characters of narration.

| Service | What it adds | Price | One 30 s short | Free tier |
|---|---|---|---|---|
| HeyGen Avatar III photo avatar | a lip-synced presenter from one photo, lower fidelity | $0.99/min | $0.50 | none |
| HeyGen Avatar IV photo avatar | the same, much better motion and lip sync | $2.31/min, plus $1.32 once per avatar | $1.16 | none |
| HeyGen Avatar V digital twin | highest-fidelity presenter from a trained twin | $7.20/min | $3.60 | none |
| ElevenLabs TTS (flash v2.5) | more expressive voices than Kokoro, 70+ languages | $0.04 per 1K chars | $0.02 | 10K chars a month |
| ElevenLabs TTS (multilingual v2) | their best general voice | $0.08 per 1K chars | $0.04 | 10K chars a month |
| ElevenLabs Music | a real composed bed or song instead of our synth bed | $0.15/min | $0.08 | no (free plan cannot run music) |
| fal Kling 3.0 Pro | generated B-roll footage from a prompt or a still | $0.112/s ($0.168/s with sound) | $3.36 | not stated |
| fal Veo 3.1 Fast | top-tier generated footage with sound | $0.10/s ($0.15/s with sound) | $3.00 | not stated |
| fal Seedance 2.5 (480p) | a whole 30 s generated clip in one call | about $0.22/s | $6.62 | not stated |
| fal MiniMax Music 3 | a song with vocals (needs lyrics) | $0.002/s | $0.06 | not stated |
| Blotato (posting, reference) | scheduling and posting to social sites | $29/month minimum for the API | flat | trial has no API |

Notes that matter before saying yes:
- HeyGen's v1/v2 API stops on 2026-11-01; the adapter uses v3 (`POST /v3/videos`, `GET /v3/videos/{id}`).
- fal says its Veo 3.1 endpoints will be removed on 2026-11-17.
- Kling image-to-video takes its shape from the image: give it a 9:16 still.
- Suno has no official public API. Unofficial wrappers are not used.
- An avatar or a voice clone is only ever of a person who has agreed to it.

Sources: help.heygen.com/en/articles/10060327-heygen-api-pricing-explained, developers.heygen.com,
elevenlabs.io/pricing/api, elevenlabs.io/docs, fal.ai/pricing, fal.ai/models (per model pages),
blotato.com/pricing.
