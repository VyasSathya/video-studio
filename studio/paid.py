"""Adapters for paid generation, wired but never spending on their own.

Every call is a dry run that returns the exact request and its estimated cost, unless all three hold:
  1. the provider key is set (HEYGEN_API_KEY, ELEVENLABS_API_KEY, FAL_KEY)
  2. STUDIO_ALLOW_SPEND=1 in the environment
  3. the call passes confirm=True
Nothing in the sample pipelines calls these. Prices were read from the official pages on 2026-10-17 (see
docs/PAID.md for sources); re-check them before approving a spend.

Avatars and voice clones: only of a person who has agreed to it, never of anyone else (AGENTS.md).
"""
import json
import os
import time
import urllib.request

PRICES = {  # USD, read 2026-10-17
    "heygen.avatar_iii": 0.99 / 60, "heygen.avatar_iv": 2.31 / 60, "heygen.avatar_v": 7.20 / 60,  # per second
    "heygen.photo_avatar_create": 1.32,                                                        # per avatar
    "elevenlabs.tts.eleven_multilingual_v2": 0.08 / 1000, "elevenlabs.tts.eleven_flash_v2_5": 0.04 / 1000,  # /char
    "elevenlabs.music": 0.15 / 60, "elevenlabs.sfx": 0.12 / 60,                                # per second
    "fal.kling3pro": 0.112, "fal.kling3pro.audio": 0.168,                                      # per second
    "fal.veo31": 0.20, "fal.veo31.audio": 0.40, "fal.veo31fast": 0.10, "fal.veo31fast.audio": 0.15,
    "fal.seedance25.480p": 0.2205, "fal.seedance25.720p": 0.4730,
    "fal.minimax_music3": 0.002, "fal.lyria2_per30s": 0.10, "fal.stable_audio25": 0.20,
}

FAL_MODELS = {
    "kling-i2v": "fal-ai/kling-video/v3/pro/image-to-video", "kling-t2v": "fal-ai/kling-video/v3/pro/text-to-video",
    "veo-t2v": "fal-ai/veo3.1", "veo-i2v": "fal-ai/veo3.1/image-to-video", "veo-fast-i2v": "fal-ai/veo3.1/fast/image-to-video",
    "seedance-i2v": "bytedance/seedance-2.5/image-to-video", "seedance-t2v": "bytedance/seedance-2.5/text-to-video",
    "minimax-music": "minimax/music-3", "lyria2": "fal-ai/lyria2", "stable-audio": "fal-ai/stable-audio-25/text-to-audio",
}


class SpendBlocked(Exception):
    pass


def _gate(key_env, confirm):
    key = os.getenv(key_env)
    live = bool(key) and os.getenv("STUDIO_ALLOW_SPEND") == "1" and confirm
    return key, live


def _http(method, url, headers, body=None, raw=False, timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=dict(headers, **({"Content-Type": "application/json"} if data else {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b if raw else json.loads(b.decode("utf-8"))


def dry(provider, method, url, body, est):
    return {"dry_run": True, "provider": provider, "method": method, "url": url, "body": body,
            "estimated_usd": round(est, 2),
            "to_run": "set the key, STUDIO_ALLOW_SPEND=1, and call again with confirm=True"}


# HeyGen v3 (v1/v2 retire 2026-11-01)
def heygen_avatar_video(script, avatar_id, voice_id, seconds_est, aspect="9:16", engine="avatar_iv", confirm=False,
                        out=None, poll=10):
    url = "https://api.heygen.com/v3/videos"
    body = {"type": "avatar", "avatar_id": avatar_id, "voice_id": voice_id, "script": script, "resolution": "1080p",
            "aspect_ratio": aspect, "engine": {"type": engine}, "caption": {"file_format": "srt"}}
    est = PRICES["heygen." + engine] * seconds_est
    key, live = _gate("HEYGEN_API_KEY", confirm)
    if not live:
        return dry("heygen", "POST", url, body, est)
    h = {"X-Api-Key": key}
    vid = _http("POST", url, h, body)["data"]["video_id"]
    while True:
        st = _http("GET", url + "/" + vid, h)["data"]
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(poll)
    if st["status"] == "completed" and out:
        open(out, "wb").write(_http("GET", st["video_url"], {}, raw=True))
    return st


# ElevenLabs (synchronous: the response is the audio)
def elevenlabs_tts(text, voice_id, out, model="eleven_flash_v2_5", confirm=False):
    url = "https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % voice_id
    body = {"text": text, "model_id": model}
    est = PRICES["elevenlabs.tts." + model] * len(text)
    key, live = _gate("ELEVENLABS_API_KEY", confirm)
    if not live:
        return dry("elevenlabs", "POST", url, body, est)
    open(out, "wb").write(_http("POST", url, {"xi-api-key": key}, body, raw=True))
    return {"file": str(out), "estimated_usd": round(est, 2)}


def elevenlabs_music(prompt, seconds, out, confirm=False):
    url = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128"
    body = {"prompt": prompt, "music_length_ms": int(seconds * 1000), "model_id": "music_v2_5", "force_instrumental": True}
    est = PRICES["elevenlabs.music"] * seconds
    key, live = _gate("ELEVENLABS_API_KEY", confirm)
    if not live:
        return dry("elevenlabs", "POST", url, body, est)
    open(out, "wb").write(_http("POST", url, {"xi-api-key": key}, body, raw=True, timeout=900))
    return {"file": str(out), "estimated_usd": round(est, 2)}


# fal queue API: submit, then follow the status_url / response_url it returns
def fal_run(model, inputs, price_key, units, out=None, confirm=False, poll=5):
    model_id = FAL_MODELS.get(model, model)
    url = "https://queue.fal.run/" + model_id
    est = PRICES[price_key] * units
    key, live = _gate("FAL_KEY", confirm)
    if not live:
        return dry("fal", "POST", url, inputs, est)
    h = {"Authorization": "Key " + key}
    sub = _http("POST", url, h, inputs)
    while _http("GET", sub["status_url"], h)["status"] != "COMPLETED":
        time.sleep(poll)
    res = _http("GET", sub["response_url"], h)
    media = res.get("video") or res.get("audio") or {}
    if out and media.get("url"):
        open(out, "wb").write(_http("GET", media["url"], {}, raw=True, timeout=900))
    return res


def broll_clip(prompt, seconds=5, image_url=None, model="kling", aspect="9:16", audio=False, out=None, confirm=False):
    """Generated B-roll. Kling i2v follows the image's aspect, so give it a 9:16 still."""
    if model == "kling":
        m = "kling-i2v" if image_url else "kling-t2v"
        inp = {"prompt": prompt, "duration": str(int(min(15, max(3, seconds)))), "generate_audio": audio}
        inp.update({"start_image_url": image_url} if image_url else {"aspect_ratio": aspect})
        return fal_run(m, inp, "fal.kling3pro" + (".audio" if audio else ""), seconds, out, confirm)
    if model == "veo-fast":
        inp = {"prompt": prompt, "aspect_ratio": aspect, "duration": "%ds" % min(8, max(4, int(seconds) // 2 * 2)),
               "resolution": "1080p", "generate_audio": audio}
        if image_url:
            inp["image_url"] = image_url
        return fal_run("veo-fast-i2v" if image_url else "veo-t2v", inp,
                       "fal.veo31fast" + (".audio" if audio else ""), seconds, out, confirm)
    if model == "seedance":
        inp = {"prompt": prompt, "duration": int(seconds), "resolution": "480p", "generate_audio": audio}
        if image_url:
            inp["image_url"] = image_url
        else:
            inp["aspect_ratio"] = aspect
        return fal_run("seedance-i2v" if image_url else "seedance-t2v", inp, "fal.seedance25.480p", seconds, out,
                       confirm)
    raise ValueError("model: kling | veo-fast | seedance")


def estimate_short(seconds=30, chars=450):
    """What one 30 s vertical short would cost with each paid piece, for a yes/no."""
    return {
        "HeyGen Avatar IV presenter": round(PRICES["heygen.avatar_iv"] * seconds, 2),
        "HeyGen Avatar III presenter": round(PRICES["heygen.avatar_iii"] * seconds, 2),
        "ElevenLabs voice (flash)": round(PRICES["elevenlabs.tts.eleven_flash_v2_5"] * chars, 2),
        "ElevenLabs music bed": round(PRICES["elevenlabs.music"] * seconds, 2),
        "Kling 3 Pro B-roll, all 30 s": round(PRICES["fal.kling3pro"] * seconds, 2),
        "Veo 3.1 Fast B-roll, all 30 s": round(PRICES["fal.veo31fast"] * seconds, 2),
        "Seedance 2.5 480p, all 30 s": round(PRICES["fal.seedance25.480p"] * seconds, 2),
        "MiniMax Music 3 (needs lyrics)": round(PRICES["fal.minimax_music3"] * seconds, 2),
    }
